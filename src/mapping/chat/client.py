"""Ollama cloud chat client."""
import os
from ollama import Client


def get_client() -> Client:
    """Create an Ollama client pointing to the cloud service."""
    api_key = os.getenv("OLLAMA_API_KEY", "")
    return Client(
        host="https://ollama.com",
        headers={"Authorization": f"Bearer {api_key}"} if api_key else {},
    )


def chat_completion(client: Client, model: str, system_prompt: str, user_prompt: str) -> str:
    """Send a chat completion request and return the assistant's response text."""
    resp = client.chat(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        options={"temperature": float(os.getenv("LLM_TEMPERATURE", "0.1"))},
    )
    return resp["message"]["content"]
