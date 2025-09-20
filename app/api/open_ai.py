
from openai import AsyncOpenAI, OpenAIError
from app.core.config import settings
from typing import List, Dict, Optional
client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
async def get_rag_response(query: str, context_chunks: List[str]) -> str:
    if not settings.OPENAI_API_KEY:
        return “OpenAI API key is not configured.”
    context = “\n---\n”.join(context_chunks)
    system_prompt = f”“”
Ideti konteksta ka daryti su turiniu ir kokios taisykles
CONTEXT:
{context}
“”"
    try:
        response = await client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {“role”: “system”, “content”: system_prompt},
                {“role”: “user”, “content”: query}
            ],
            seed=12345,
            max_tokens=400
        )
        return response.choices[0].message.content.strip()
    except OpenAIError as e:
        return f”An error occurred while contacting the AI model: {str(e)}”
    except Exception as e:
        return f”An unexpected error occurred: {str(e)}”
async def stream_general_knowledge_response(query: str, history: Optional[List[Dict]] = None):
    if not settings.OPENAI_API_KEY:
        yield “OpenAI API key is not configured. Please check your environment variables.”
        return
    system_prompt = “”"
Other contextt for full answer
“”"
    messages = [{“role”: “system”, “content”: system_prompt}]
    if history:
        messages.extend(history)
    messages.append({“role”: “user”, “content”: query})
    try:
        stream = await client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=messages,
            seed=12345,
            max_tokens=300,
            stream=True
        )
        async for chunk in stream:
            content = chunk.choices[0].delta.content
            if content:
                yield content
    except OpenAIError as e:
        yield f”An error occurred while contacting the AI model: {str(e)}”
    except Exception as e:
        yield f”An unexpected error occurred: {str(e)}”
async def get_general_knowledge_response(query: str, history: Optional[List[Dict]] = None) -> str:
    full_response = “”
    async for chunk in stream_general_knowledge_response(query, history):
        full_response += chunk
    return full_response
