"""LangChain ChatOllama client for the mapping pipeline."""
import os

from langchain_ollama import ChatOllama


def get_llm() -> ChatOllama:
    """Create a ChatOllama instance configured from environment variables.

    Reads:
        LLM_MODEL         — Ollama model name (required)
        LLM_TEMPERATURE   — sampling temperature (default 0.0)
        OLLAMA_BASE_URL   — Ollama API base URL (default http://localhost:11434) || Ollama cloud model URL
        OLLAMA_API_KEY    — bearer token for authenticated endpoints
    """
    base_url = os.getenv("OLLAMA_BASE_URL", "https://ollama.com/v1")
    api_key = os.getenv("OLLAMA_API_KEY", "")

    return ChatOllama(
        model=os.getenv("LLM_MODEL", "llama3.1:8b"),
        temperature=float(os.getenv("LLM_TEMPERATURE", "0.0")),
        base_url=base_url,
        client_kwargs={"headers": {"Authorization": f"Bearer {api_key}"}} if api_key else {},
    )
