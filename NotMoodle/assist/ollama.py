"""
Ollama client for embeddings and chat completion.

Provides typed interfaces to Ollama's API for:
- Generating text embeddings (nomic-embed-text)
- Chat completions (llama3.1:8b-instruct)
"""
import httpx
from typing import List, Dict, Optional
from django.conf import settings


def embed_texts(texts: List[str], model: Optional[str] = None) -> List[List[float]]:
    """
    Generate embeddings for a list of texts using Ollama.
    
    Args:
        texts: List of text strings to embed
        model: Embedding model name (defaults to settings.AI_EMBED_MODEL)
    
    Returns:
        List of embedding vectors (each is a list of floats)
    
    Raises:
        httpx.HTTPError: If the Ollama API request fails
    """
    if not texts:
        return []
    
    model = model or settings.AI_EMBED_MODEL
    url = f"{settings.OLLAMA_BASE_URL}/api/embeddings"
    
    embeddings = []
    
    # Process each text individually (Ollama embeddings endpoint expects single prompt)
    with httpx.Client(timeout=60.0) as client:
        for text in texts:
            payload = {
                "model": model,
                "prompt": text,
            }
            response = client.post(url, json=payload)
            response.raise_for_status()
            
            data = response.json()
            embeddings.append(data["embedding"])
    
    return embeddings


def chat(messages: List[Dict[str, str]], model: Optional[str] = None) -> str:
    """
    Generate a chat completion using Ollama's OpenAI-compatible API.
    
    Args:
        messages: List of message dicts with 'role' and 'content' keys
                  Example: [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}]
        model: Chat model name (defaults to settings.AI_CHAT_MODEL)
    
    Returns:
        Assistant's response text
    
    Raises:
        httpx.HTTPError: If the Ollama API request fails
    """
    model = model or settings.AI_CHAT_MODEL
    url = f"{settings.OLLAMA_BASE_URL}/v1/chat/completions"
    
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
    }
    
    with httpx.Client(timeout=120.0) as client:
        response = client.post(url, json=payload)
        response.raise_for_status()
        
        data = response.json()
        return data["choices"][0]["message"]["content"]


def estimate_tokens(text: str) -> int:
    """
    Estimate token count for a text string.
    
    Uses rough heuristic: ~4 characters per token (common for English).
    For production, consider using tiktoken or similar.
    
    Args:
        text: Text to estimate tokens for
    
    Returns:
        Estimated token count
    """
    return len(text) // 4
