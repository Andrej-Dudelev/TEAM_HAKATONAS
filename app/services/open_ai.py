from typing import List, Dict, Optional, AsyncGenerator
from openai import AsyncOpenAI, APIError, APIConnectionError, RateLimitError
from app.core.config import settings

client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

async def stream_rag_response(
    query: str, 
    context_chunks: List[str], 
    lesson_context: Optional[str] = None
) -> AsyncGenerator[str, None]:
    if not settings.OPENAI_API_KEY:
        yield "OpenAI API key is not configured."
        return

    context = "\n---\n".join(context_chunks)
    system_prompt = f"""You are a helpful assistant for students. Your primary role is to answer the user's question based ONLY on the DOCUMENT CONTEXT provided below. Be concise and direct.

### DOCUMENT CONTEXT
{context}
"""

    if lesson_context:
        system_prompt += f"""
### ADDITIONAL LESSON CONTEXT
The user is also working on a specific lesson. You can use this for additional context if it helps clarify their question, but prioritize the DOCUMENT CONTEXT for the main answer.
{lesson_context}
"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": query}
    ]

    try:
        stream = await client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=messages,
            max_tokens=2000,
            stream=True
        )
        async for chunk in stream:
            content = chunk.choices[0].delta.content
            if content:
                yield content
    except (APIError, APIConnectionError, RateLimitError) as e:
        yield f"An error occurred while contacting the AI model: {e}"
    except Exception as e:
        yield f"An unexpected error occurred: {e}"

async def get_rag_response(query: str, context_chunks: List[str]) -> str:
    full_response = ""
    async for chunk in stream_rag_response(query, context_chunks):
        full_response += chunk
    return full_response.strip()

async def stream_general_knowledge_response(
    query: str, 
    history: Optional[List[Dict[str, str]]] = None, 
    lesson_context: Optional[str] = None
) -> AsyncGenerator[str, None]:
    if not settings.OPENAI_API_KEY:
        yield "OpenAI API key is not configured. Please check your environment variables."
        return
        
    system_prompt = "You are a helpful coding tutor for students learning Python. Your role is to guide them, not to give them answers directly. Provide hints, ask leading questions, and explain concepts to help them solve problems on their own. Never write full code solutions for them. Keep your tone encouraging and supportive."
    
    if lesson_context:
        system_prompt = f"""{system_prompt}

The user is currently working on a specific lesson. Use the following context to provide the most relevant guidance.

### LESSON CONTEXT
{lesson_context}
"""

    messages: List[Dict[str, str]] = [{"role": "system", "content": system_prompt}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": query})
    
    try:
        stream = await client.chat.completions.create(model=settings.OPENAI_MODEL, messages=messages, max_tokens=2000, stream=True)
        async for chunk in stream:
            content = chunk.choices[0].delta.content
            if content:
                yield content
    except (APIError, APIConnectionError, RateLimitError) as e:
        yield f"An error occurred while contacting the AI model: {e}"
    except Exception as e:
        yield f"An unexpected error occurred: {e}"