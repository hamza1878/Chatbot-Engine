"""
Moviroo AI Chatbot - LLM Service
Mistral / Llama via Ollama with direct-match fallback.
"""
import httpx
import logging
from typing import List, Dict, Any

from config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Tu es un assistant support pour Moviroo, une application de transport.

RÈGLES STRICTES :
1. Réponds UNIQUEMENT à partir du contexte fourni.
2. Si la réponse n'est pas dans le contexte, dis exactement :
   "Je n'ai pas trouvé la réponse. Je vous mets en contact avec un agent."
3. Réponds dans la même langue que la question (français, anglais, arabe, franco-arabe).
4. Sois concis (max 3 phrases).
5. Ne mentionne jamais le contexte, les sources ou le système.
6. Tutoie l'utilisateur si la question est en français ou franco-arabe."""


def _build_context(chunks: List[Dict[str, Any]]) -> str:
    lines = []
    for i, c in enumerate(chunks[:4], 1):
        q = c.get("question", "")
        a = c.get("answer", "")
        cat = c.get("category", "")
        lines.append(f"[{i}][{cat}] Q: {q}\nR: {a}")
    return "\n\n".join(lines)


async def generate_answer(question: str, chunks: List[Dict[str, Any]]) -> str:
    """
    Generate answer via Ollama (Mistral/Llama).
    Falls back to best chunk answer if Ollama is unavailable.
    """
    if not chunks:
        return "Je n'ai pas trouvé la réponse. Contacte le support Moviroo."

    context = _build_context(chunks)
    prompt = (
        f"Contexte de support :\n{context}\n\n"
        f"Question : {question}\n\n"
        f"Réponse :"
    )

    try:
        async with httpx.AsyncClient(timeout=settings.llm_timeout) as client:
            resp = await client.post(
                settings.ollama_url,
                json={
                    "model": settings.ollama_model,
                    "prompt": prompt,
                    "system": SYSTEM_PROMPT,
                    "stream": False,
                    "options": {
                        "temperature": settings.llm_temperature,
                        "top_p": 0.9,
                        "num_predict": settings.llm_max_tokens,
                    },
                },
            )
            resp.raise_for_status()
            answer = resp.json().get("response", "").strip()
            if answer:
                logger.info(f"LLM answer generated ({len(answer)} chars)")
                return answer

    except httpx.ConnectError:
        logger.warning("Ollama not reachable — using direct chunk fallback")
    except httpx.HTTPStatusError as e:
        logger.error(f"Ollama HTTP error: {e.response.status_code}")
    except Exception as e:
        logger.error(f"LLM error: {e}")

    # Fallback: best matching chunk answer
    return chunks[0].get("answer", "Contacte le support Moviroo.")
