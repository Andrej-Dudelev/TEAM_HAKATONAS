import chromadb
from sentence_transformers import SentenceTransformer, util
from typing import Optional, Dict, Any, List
from app.db.models import QAPair, QuestionVariation
import re
import torch
import uuid
# Global variable to store the service instance


class SemanticSearchService:
    def __init__(self):
        print("Initializing SemanticSearchService with Two-Phase Search...")
        self.model = SentenceTransformer('paraphrase-multilingual-mpnet-base-v2')
        self.client = chromadb.PersistentClient(path="./chroma_db")
        self.qa_collection = self.client.get_or_create_collection(name="anita_qa_pairs")
        self.document_collection = self.client.get_or_create_collection(name="anita_documents")

    def _get_stripped_text(self, text: str) -> str:
        stop_words = {
            'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from', 'has', 
            'he', 'in', 'is', 'it', 'its', 'of', 'on', 'that', 'the', 'to', 'was', 
            'were', 'will', 'with', 'what', 'when', 'where', 'who', 'whom', 'why',
            'how'
        }
        
        text = text.lower()
        text = re.sub(r'[^\w\s]', '', text)
        words = text.split()
        filtered_words = [word for word in words if word not in stop_words]
        text = " ".join(filtered_words)
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def _vectorize(self, text: str or List[str]):
        return self.model.encode(text, convert_to_tensor=True)

    def sync_index_from_db(self, all_pairs: List[QAPair]):
        print(f"Syncing {len(all_pairs)} pairs and their variations to ChromaDB...")
        self.qa_collection.delete(where={"qa_id": {"$ne": "dummy_id_to_avoid_error_on_empty_db"}})
        for qa_pair in all_pairs:
            self.add_qa_pair(qa_pair)
        print("Sync complete.")

    def add_qa_pair(self, qa_pair: QAPair):
        questions_to_index = []

        if qa_pair.question_lt:
            questions_to_index.append({
                "id": f"{qa_pair.qa_id}_en_main",
                "text": qa_pair.question_lt,
                "meta": {"qa_id": qa_pair.qa_id, "language": "lt", "original_question": qa_pair.question_lt}
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
            ids=f"var_{variation.id}",
            embeddings=self._vectorize(stripped_question).tolist(),
            metadatas={
                "qa_id": variation.qa_pair_id, 
                "language": variation.language, 
                "original_question": variation.variation_text
            }
        )

    def update_qa_pair(self, qa_pair: QAPair):
        self.delete_qa_pair(qa_pair.qa_id)
        self.add_qa_pair(qa_pair)

    def delete_qa_pair(self, qa_id: str):
        self.qa_collection.delete(where={"qa_id": qa_id})

    def find_best_match(self, query: str, language: str) -> Optional[Dict[str, Any]]:
        N_CANDIDATES = 5
        RE_RANKING_THRESHOLD = 0.70

        print(f"\n--- Starting Two-Phase Search for Q&A (Language: {language.upper()}) ---")
        print(f"Original Query: '{query}'")

        stripped_query = self._get_stripped_text(query)
        
        query_embedding = self._vectorize(stripped_query).tolist()
        
        results = self.qa_collection.query(
            query_embeddings=[query_embedding], 
            n_results=N_CANDIDATES,
            where={"language": language}
        )
        
        if not results or not results["ids"] or not results["ids"][0]:
            print("--- Phase 1: No candidates found for this language. Aborting search. ---")
            return None

        print(f"\n--- Phase 1 (Retrieval) Results ---")
        num_candidates = len(results["ids"][0])
        print(f"Found {num_candidates} potential candidates from vector search.")
        candidates = []
        for i in range(num_candidates):
            meta = results["metadatas"][0][i]
            dist = results["distances"][0][i]
            candidates.append(meta)
            print(f"  - L2 Dist: {dist:.4f} | Q: '{meta['original_question']}'")

        print("\n--- Phase 2 (Re-ranking) ---")
        
        original_candidate_questions = [c["original_question"] for c in candidates]
        query_vec = self._vectorize(query)
        candidate_vecs = self._vectorize(original_candidate_questions)
        cosine_scores = util.cos_sim(query_vec, candidate_vecs)[0]
        
        print(f"Comparing original query against candidates (Cosine Similarity):")
        
        best_score_idx = torch.argmax(cosine_scores).item()
        best_score = cosine_scores[best_score_idx].item()
        best_candidate = candidates[best_score_idx]

        for i, score in enumerate(cosine_scores):
            is_best = "<- BEST" if i == best_score_idx else ""
            print(f"  - Score: {score.item():.4f} | Q: '{original_candidate_questions[i]}' {is_best}")

        print("\n--- Final Decision ---")
        if best_score >= RE_RANKING_THRESHOLD:
            print(f":white_check_mark: Match Found! Best candidate score ({best_score:.4f}) is above threshold ({RE_RANKING_THRESHOLD}).")
            return {
                "qa_id": best_candidate["qa_id"],
                "language": best_candidate["language"],
                "distance": 1 - best_score
            }
        else:
            print(f":x: No confident match. Best score ({best_score:.4f}) is below threshold ({RE_RANKING_THRESHOLD}).")
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
        print(f"\n--- Searching Documents for query (Language: {language.upper()}): '{query}' ---")
        N_CHUNKS_TO_RETURN = 3
        SIMILARITY_THRESHOLD = 0.50

        query_embedding = self._vectorize(query)
        
        results = self.document_collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=N_CHUNKS_TO_RETURN,
            where={"language": language}
        )
        
        if not results or not results["ids"][0]:
            print("Phase 1 (Docs): No candidates found for this language.")
            return []

        candidate_chunks = [meta["chunk_text"] for meta in results["metadatas"][0]]
        
        candidate_embeddings = self._vectorize(candidate_chunks)
        cosine_scores = util.cos_sim(query_embedding, candidate_embeddings)[0]
        best_score = torch.max(cosine_scores).item()
        
        if best_score < SIMILARITY_THRESHOLD:
            print(":No confident document match. Best score is below threshold.")
            return []
        
        print(f"Confident match found. Returning {len(candidate_chunks)} chunks for RAG.")
        return candidate_chunks

search_service: SemanticSearchService = None