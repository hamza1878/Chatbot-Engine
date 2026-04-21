import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3"   # تنجم تبدلها: mistral, phi...

def generate_answer(question: str, context: str) -> str:
    prompt = f"""
You are a smart multilingual assistant (Arabic, French, English).

Answer clearly and naturally.

User question:
{question}

Context:
{context}

Rules:
- Answer in the same language as the user
- If context is not enough, still try to help
- Be concise

Answer:
"""

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL,
                "prompt": prompt,
                "stream": False
            },
            timeout=30
        )

        return response.json().get("response", "").strip()

    except Exception as e:
        return f"Error (Ollama): {str(e)}"