import chromadb
from sentence_transformers import SentenceTransformer, util
from typing import Optional, Dict, Any, List
from app.db.models.qa import QAPair, QuestionVariation
import re
import torch
import uuid

class SemanticSearchService:
    def __init__(self):
        print("Initializing SemanticSearchService with Two-Phase Search...")
        self.model = SentenceTransformer('paraphrase-multilingual-mpnet-base-v2')
        self.client = chromadb.PersistentClient(path="./chroma_db")
        self.qa_collection = self.client.get_or_create_collection(name="anita_qa_pairs")
        self.document_collection = self.client.get_or_create_collection(
            name="anita_documents",
            metadata={"hnsw:space": "cosine"}
        )

    def _get_stripped_text(self, text: str) -> str:
        text = text.lower()
        text = re.sub(r'[^\w\s]', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def _vectorize(self, text: str or List[str]):
        return self.model.encode(text, convert_to_tensor=True)

    def sync_index_from_db(self, all_pairs: List[QAPair]):
        print(f"Syncing {len(all_pairs)} pairs and their variations to ChromaDB...")
        if self.qa_collection.count() > 0:
            self.qa_collection.delete(where={"qa_id": {"$ne": "dummy_id_to_avoid_error_on_empty_db"}})
        
        for qa_pair in all_pairs:
            self.add_qa_pair(qa_pair)
        
        print("Sync complete.")

    def add_qa_pair(self, qa_pair: QAPair):
        questions_to_index = []

        if qa_pair.question:
            questions_to_index.append({
                "id": f"{qa_pair.qa_id}_main",
                "text": qa_pair.question,
                "meta": {"qa_id": qa_pair.qa_id, "language": "lt", "original_question": qa_pair.question}
            })

        if hasattr(qa_pair, 'variations') and qa_pair.variations:
            for variation in qa_pair.variations:
                questions_to_index.append({
                    "id": f"var_{variation.id}",
                    "text": variation.variation_text,
                    "meta": {"qa_id": qa_pair.qa_id, "language": variation.language, "original_question": variation.variation_text}
                })

        if not questions_to_index:
            return

        texts_to_vectorize = [self._get_stripped_text(q['text']) for q in questions_to_index]
        embeddings = self._vectorize(texts_to_vectorize).tolist()
        
        self.qa_collection.add(
            ids=[q['id'] for q in questions_to_index],
            embeddings=embeddings,
            metadatas=[q['meta'] for q in questions_to_index]
        )
    
    def add_question_variation(self, variation: QuestionVariation):
        print(f"Indexing new variation for qa_id: {variation.qa_pair_id}")
        stripped_question = self._get_stripped_text(variation.variation_text)
        self.qa_collection.add(
            ids=[f"var_{variation.id}"],
            embeddings=[self._vectorize(stripped_question).tolist()],
            metadatas=[{
                "qa_id": variation.qa_pair_id, 
                "language": variation.language, 
                "original_question": variation.variation_text
            }]
        )

    def update_qa_pair(self, qa_pair: QAPair):
        self.delete_qa_pair(qa_pair.qa_id)
        self.add_qa_pair(qa_pair)

    def delete_qa_pair(self, qa_id: str):
        self.qa_collection.delete(where={"qa_id": qa_id})

    def find_best_match(self, query: str, language: str) -> Optional[Dict[str, Any]]:
        N_CANDIDATES = 5
        RE_RANKING_THRESHOLD = 0.70

        stripped_query = self._get_stripped_text(query)
        query_embedding = self._vectorize(stripped_query).tolist()
        
        results = self.qa_collection.query(
            query_embeddings=[query_embedding], 
            n_results=N_CANDIDATES,
            where={"language": language}
        )
        
        if not results or not results["ids"] or not results["ids"][0]:
            return None

        num_candidates = len(results["ids"][0])
        candidates = [results["metadatas"][0][i] for i in range(num_candidates)]
        
        original_candidate_questions = [c["original_question"] for c in candidates]
        query_vec = self._vectorize(query)
        candidate_vecs = self._vectorize(original_candidate_questions)
        cosine_scores = util.cos_sim(query_vec, candidate_vecs)[0]
        
        best_score_idx = torch.argmax(cosine_scores).item()
        best_score = cosine_scores[best_score_idx].item()
        best_candidate = candidates[best_score_idx]

        if best_score >= RE_RANKING_THRESHOLD:
            return {
                "qa_id": best_candidate["qa_id"],
                "language": best_candidate["language"],
                "distance": 1 - best_score
            }
        else:
            return None

    def index_document_chunks(self, chunks: List[str], document_id: str, language: str):
        print(f"Indexing {len(chunks)} chunks for document {document_id} (Language: {language.upper()})...")
        chunk_embeddings = self._vectorize(chunks).tolist()
        chunk_ids = [str(uuid.uuid4()) for _ in chunks]
        metadatas = [{"document_id": document_id, "chunk_text": chunk, "language": language} for chunk in chunks]
        
        self.document_collection.add(
            ids=chunk_ids,
            embeddings=chunk_embeddings,
            metadatas=metadatas
        )
        print("Indexing complete.")

    def search_documents(self, query: str, language: str) -> List[str]:
        print(f"Searching Documents for query (Language: {language.upper()}): '{query}'")
        N_CHUNKS_TO_RETURN = 3
        COSINE_DISTANCE_THRESHOLD = 0.6 

        query_embedding = self._vectorize(query)
        
        results = self.document_collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=N_CHUNKS_TO_RETURN,
            where={"language": language}
        )
        
        if not results or not results["ids"][0]:
            return []

        relevant_chunks = []
        if results.get("distances") and results.get("metadatas"):
            for i, metadata in enumerate(results["metadatas"][0]):
                if results["distances"][0][i] < COSINE_DISTANCE_THRESHOLD:
                    relevant_chunks.append(metadata["chunk_text"])

        if relevant_chunks:
            print(f"Match found. Returning {len(relevant_chunks)} chunks for RAG.")
        
        return relevant_chunks


search_service: Optional[SemanticSearchService] = None

def get_service() -> SemanticSearchService:

    if search_service is None:
        raise RuntimeError("SemanticSearchService not initialized. Check application lifespan.")
    return search_service
