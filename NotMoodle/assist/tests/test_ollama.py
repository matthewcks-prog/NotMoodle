"""
Tests for Ollama client (assist.ollama).
"""
import pytest
import httpx
import responses
from assist.ollama import embed_texts, chat, estimate_tokens


@pytest.mark.unit
class TestEmbedTexts:
    """Test embed_texts function."""
    
    @responses.activate
    def test_embed_texts_success(self, settings):
        """Test successful embedding generation."""
        settings.OLLAMA_BASE_URL = "http://localhost:11434"
        settings.AI_EMBED_MODEL = "nomic-embed-text"
        
        # Mock Ollama embeddings API
        responses.add(
            responses.POST,
            "http://localhost:11434/api/embeddings",
            json={"embedding": [0.1, 0.2, 0.3]},
            status=200,
        )
        
        texts = ["Hello world"]
        result = embed_texts(texts)
        
        assert len(result) == 1
        assert result[0] == [0.1, 0.2, 0.3]
        assert len(responses.calls) == 1
    
    @responses.activate
    def test_embed_texts_multiple(self, settings):
        """Test embedding multiple texts."""
        settings.OLLAMA_BASE_URL = "http://localhost:11434"
        settings.AI_EMBED_MODEL = "nomic-embed-text"
        
        # Mock multiple calls
        responses.add(
            responses.POST,
            "http://localhost:11434/api/embeddings",
            json={"embedding": [0.1] * 768},
            status=200,
        )
        responses.add(
            responses.POST,
            "http://localhost:11434/api/embeddings",
            json={"embedding": [0.2] * 768},
            status=200,
        )
        responses.add(
            responses.POST,
            "http://localhost:11434/api/embeddings",
            json={"embedding": [0.3] * 768},
            status=200,
        )
        
        texts = ["First text", "Second text", "Third text"]
        result = embed_texts(texts)
        
        assert len(result) == 3
        assert len(result[0]) == 768
        assert result[0][0] == 0.1
        assert result[1][0] == 0.2
        assert result[2][0] == 0.3
    
    def test_embed_texts_empty_list(self):
        """Test with empty text list."""
        result = embed_texts([])
        assert result == []
    
    @responses.activate
    def test_embed_texts_http_error(self, settings):
        """Test handling of HTTP errors."""
        settings.OLLAMA_BASE_URL = "http://localhost:11434"
        
        responses.add(
            responses.POST,
            "http://localhost:11434/api/embeddings",
            json={"error": "Model not found"},
            status=404,
        )
        
        texts = ["Test"]
        with pytest.raises(httpx.HTTPStatusError):
            embed_texts(texts)
    
    @responses.activate
    def test_embed_texts_custom_model(self, settings):
        """Test with custom model parameter."""
        settings.OLLAMA_BASE_URL = "http://localhost:11434"
        
        responses.add(
            responses.POST,
            "http://localhost:11434/api/embeddings",
            json={"embedding": [0.5] * 384},
            status=200,
        )
        
        texts = ["Test"]
        result = embed_texts(texts, model="custom-model")
        
        assert len(result) == 1
        assert len(result[0]) == 384


@pytest.mark.unit
class TestChat:
    """Test chat function."""
    
    @responses.activate
    def test_chat_success(self, settings):
        """Test successful chat completion."""
        settings.OLLAMA_BASE_URL = "http://localhost:11434"
        settings.AI_CHAT_MODEL = "llama3.1:latest"
        
        # Mock Ollama chat API (OpenAI-compatible)
        responses.add(
            responses.POST,
            "http://localhost:11434/v1/chat/completions",
            json={
                "choices": [
                    {
                        "message": {
                            "content": "Hello! How can I help you?"
                        }
                    }
                ]
            },
            status=200,
        )
        
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello!"}
        ]
        result = chat(messages)
        
        assert result == "Hello! How can I help you?"
        assert len(responses.calls) == 1
    
    @responses.activate
    def test_chat_with_context(self, settings):
        """Test chat with system and user messages."""
        settings.OLLAMA_BASE_URL = "http://localhost:11434"
        
        responses.add(
            responses.POST,
            "http://localhost:11434/v1/chat/completions",
            json={
                "choices": [
                    {"message": {"content": "Python is a programming language."}}
                ]
            },
            status=200,
        )
        
        messages = [
            {"role": "system", "content": "You are a CS tutor."},
            {"role": "user", "content": "What is Python?"}
        ]
        result = chat(messages)
        
        assert "Python" in result
        assert "programming language" in result
    
    @responses.activate
    def test_chat_http_error(self, settings):
        """Test handling of HTTP errors."""
        settings.OLLAMA_BASE_URL = "http://localhost:11434"
        
        responses.add(
            responses.POST,
            "http://localhost:11434/v1/chat/completions",
            json={"error": "Server error"},
            status=500,
        )
        
        messages = [{"role": "user", "content": "Test"}]
        with pytest.raises(httpx.HTTPStatusError):
            chat(messages)
    
    @responses.activate
    def test_chat_custom_model(self, settings):
        """Test with custom model parameter."""
        settings.OLLAMA_BASE_URL = "http://localhost:11434"
        
        responses.add(
            responses.POST,
            "http://localhost:11434/v1/chat/completions",
            json={
                "choices": [{"message": {"content": "Response from custom model"}}]
            },
            status=200,
        )
        
        messages = [{"role": "user", "content": "Test"}]
        result = chat(messages, model="custom-llama")
        
        assert result == "Response from custom model"


@pytest.mark.unit
class TestEstimateTokens:
    """Test estimate_tokens function."""
    
    def test_estimate_tokens_empty_string(self):
        """Test with empty string."""
        result = estimate_tokens("")
        assert result == 0
    
    def test_estimate_tokens_short_text(self):
        """Test with short text."""
        text = "Hello"
        result = estimate_tokens(text)
        assert result == len(text) // 4
    
    def test_estimate_tokens_long_text(self):
        """Test with longer text."""
        text = "This is a longer piece of text that should be tokenized."
        result = estimate_tokens(text)
        assert result == len(text) // 4
    
    def test_estimate_tokens_very_long_text(self):
        """Test with very long text."""
        text = "A" * 10000
        result = estimate_tokens(text)
        assert result == 2500  # 10000 / 4
    
    def test_estimate_tokens_with_unicode(self):
        """Test with unicode characters."""
        text = "Hello 你好 مرحبا"
        result = estimate_tokens(text)
        assert result >= 0
        assert isinstance(result, int)

