# NotMoodle AI Assistant Setup Guide

## Overview

NotMoodle AI Assistant is a free local AI chatbot powered by Ollama + RAG (Retrieval-Augmented Generation). It helps students get answers to course-related questions using their lesson content.

**Key Features:**
- 🤖 Local LLM (no API costs, privacy-friendly)
- 📚 RAG-based answers grounded in course content
- 🎯 Vector similarity search with pgvector
- 🚦 Built-in rate limiting (100 queries/day per user)
- 📊 Usage tracking and analytics

## Prerequisites

### 1. PostgreSQL 14+ with pgvector Extension

**Install PostgreSQL:**

**Windows:**
```powershell
# Download from https://www.postgresql.org/download/windows/
# Or use Chocolatey
choco install postgresql14
```

**Mac:**
```bash
brew install postgresql@14
brew services start postgresql@14
```

**Linux:**
```bash
sudo apt-get update
sudo apt-get install postgresql-14 postgresql-contrib-14
```

**Install pgvector Extension:**

**Option A: Pre-built packages (recommended)**
```bash
# Mac
brew install pgvector

# Ubuntu/Debian
sudo apt install postgresql-14-pgvector

# Windows - download from https://github.com/pgvector/pgvector/releases
```

**Option B: Build from source**
```bash
git clone --branch v0.5.1 https://github.com/pgvector/pgvector.git
cd pgvector
make
sudo make install  # (use 'make install' on Windows)
```

**Verify pgvector is available:**
```bash
psql -U postgres -c "SELECT * FROM pg_available_extensions WHERE name = 'vector';"
```

### 2. Update Django Database Settings

Update `NotMoodle/settings.py` to use PostgreSQL instead of SQLite:

```python
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DB_NAME", "notmoodle_db"),
        "USER": os.getenv("DB_USER", "postgres"),
        "PASSWORD": os.getenv("DB_PASSWORD", "your_password"),
        "HOST": os.getenv("DB_HOST", "localhost"),
        "PORT": os.getenv("DB_PORT", "5432"),
    }
}
```

**Create the database:**
```bash
psql -U postgres -c "CREATE DATABASE notmoodle_db;"
```

### 3. Ollama Installation

**Download and install Ollama:**

- **Mac/Linux:** https://ollama.ai/download
- **Windows:** Download from https://ollama.ai/download

**Verify installation:**
```bash
ollama --version
```

**Pull required models:**
```bash
# Embedding model (768-dimensional vectors)
ollama pull nomic-embed-text

# Chat model (8B parameter instruct-tuned)
ollama pull llama3.1:8b-instruct
```

**Start Ollama server:**
```bash
ollama serve
```

This will start Ollama on `http://localhost:11434` (default).

### 4. Python Dependencies

Install required packages:

```bash
cd NotMoodle
pip install -r ../requirements.txt
```

Required packages:
- `psycopg2-binary>=2.9.0` - PostgreSQL adapter
- `pgvector>=0.2.0` - pgvector Django integration
- `httpx>=0.25.0` - HTTP client for Ollama

## Configuration

### Environment Variables

Create or update `.env` file in the NotMoodle root directory:

```bash
# Database (PostgreSQL)
DB_NAME=notmoodle_db
DB_USER=postgres
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432

# Ollama Configuration
OLLAMA_BASE_URL=http://localhost:11434
AI_CHAT_MODEL=llama3.1:8b-instruct
AI_EMBED_MODEL=nomic-embed-text
AI_DAILY_QUESTION_LIMIT=100

# Google OAuth (existing)
GOOGLE_OAUTH2_CLIENT_ID=your_client_id
GOOGLE_OAUTH2_CLIENT_SECRET=your_client_secret
```

## Setup Instructions

### 1. Run Migrations

```bash
cd NotMoodle

# Apply migrations (this will enable pgvector extension)
python manage.py migrate
```

The migrations will:
1. Enable the `vector` extension in PostgreSQL
2. Create `assist_documentchunk` table with vector field
3. Create `assist_studentquestion` table for logging
4. Add IVFFlat index for fast similarity search

### 2. Index Lesson Content

Before the AI assistant can answer questions, you need to index your published lessons:

```bash
# Index all published lessons
python manage.py index_lessons_for_rag

# Index specific lesson
python manage.py index_lessons_for_rag --lesson-id 1

# Re-index (overwrite existing chunks)
python manage.py index_lessons_for_rag --force
```

**What this does:**
1. Extracts content from published lessons (title, description, objectives, readings)
2. Splits content into ~800-1200 character chunks with overlap
3. Generates 768-dim embeddings using `nomic-embed-text`
4. Stores chunks with embeddings in the database

**Output example:**
```
Processing TEST101: Introduction to Testing
  Created 5 chunks
  Saved 5 chunks

Indexing complete: 1 lessons, 5 total chunks
```

### 3. Start Services

**Terminal 1 - Ollama:**
```bash
ollama serve
```

**Terminal 2 - Django:**
```bash
cd NotMoodle
python manage.py runserver
```

### 4. Test the AI Assistant

1. Log in as a student
2. Go to the student dashboard
3. Look for the "AI Assistant" button in the bottom-right corner
4. Click to open the chat panel
5. Ask a question about your course content

**Example questions:**
- "What are the learning objectives for TEST101?"
- "Explain the main concepts covered in this lesson"
- "What prerequisites do I need for this course?"

## Usage

### For Students

The AI assistant appears as a floating button on the student dashboard. Students can:

- Ask questions about course content
- View sources for each answer
- Track their daily usage (100 queries/day limit)
- Get answers instantly without leaving the page

### For Teachers/Admins

**View indexed content:**
```bash
# Django admin: /admin/assist/documentchunk/
```

**View student questions:**
```bash
# Django admin: /admin/assist/studentquestion/
```

**Re-index after updating lessons:**
```bash
python manage.py index_lessons_for_rag --force
```

## Customization

### Change Models

Edit `.env`:
```bash
# Use a different chat model
AI_CHAT_MODEL=llama3.2:7b-instruct

# Use a different embedding model (must be 768-dim or update models.py)
AI_EMBED_MODEL=mxbai-embed-large
```

After changing models, pull the new model:
```bash
ollama pull llama3.2:7b-instruct
```

### Adjust Chunk Size

Edit `assist/management/commands/index_lessons_for_rag.py`:

```python
def _chunk_text(self, text: str, target_chars: int = 1200, overlap: int = 200)
```

Change `target_chars` (800-1500 recommended) and `overlap` (100-300 recommended).

### Adjust Retrieval

Edit `assist/views.py`:

```python
def retrieve_context(question: str, lesson_id: Optional[int] = None, top_k: int = 5)
```

Change `top_k` to retrieve more/fewer chunks (3-10 recommended).

### Change Rate Limit

Edit `.env`:
```bash
AI_DAILY_QUESTION_LIMIT=50  # Default: 100
```

Or in `settings.py`:
```python
AI_DAILY_QUESTION_LIMIT = int(os.getenv("AI_DAILY_QUESTION_LIMIT", "100"))
```

### Customize System Prompt

Edit `assist/views.py` in the `ask_assistant` function:

```python
system_prompt = f"""You are NotMoodle AI, a helpful tutor for our Learning Management System.

Constraints:
- Only answer using the provided context below.
- If the context is insufficient, explain what information is missing.
- Keep explanations concise and step-by-step.
- [Add your custom instructions here]

Context:
{context_text}
"""
```

## Testing

Run the test suite:

```bash
cd NotMoodle
python manage.py test assist
```

**Tests include:**
- Ollama client (embedding + chat)
- Document chunk creation and retrieval
- API endpoints (authentication, rate limiting)
- Model creation and queries

**Manual testing:**
1. Create a published lesson with content
2. Run `python manage.py index_lessons_for_rag`
3. Log in as a student
4. Open AI assistant and ask about the lesson
5. Verify answer references the lesson content

## Troubleshooting

### "No module named 'pgvector'"

```bash
pip install pgvector
```

### "Extension 'vector' does not exist"

Install pgvector extension (see Prerequisites section), then:
```bash
psql -U postgres -d notmoodle_db -c "CREATE EXTENSION vector;"
```

### "Connection refused" (Ollama)

Ensure Ollama is running:
```bash
ollama serve
```

Check if models are pulled:
```bash
ollama list
```

### "Failed to generate embeddings"

1. Check Ollama is running: `curl http://localhost:11434/api/tags`
2. Verify model is available: `ollama list`
3. Check logs: Look for error messages in Django console

### Slow embedding generation

- Embeddings are generated sequentially. For large lessons, indexing takes time.
- Consider running indexing in background with Celery (future enhancement).
- On first run, models are loaded into memory (30s-1min).

### "Daily question limit reached"

Wait until the next day (midnight UTC), or increase the limit in settings:
```python
AI_DAILY_QUESTION_LIMIT = 200
```

### Vector search returns no results

1. Check chunks exist: `python manage.py shell`
   ```python
   from assist.models import DocumentChunk
   print(DocumentChunk.objects.count())
   ```
2. Re-index: `python manage.py index_lessons_for_rag --force`
3. Verify index exists:
   ```sql
   \d+ assist_documentchunk
   -- Should show ivfflat index on embedding column
   ```

## Performance Optimization

### For Large Datasets (1000+ lessons)

1. **Increase IVFFlat lists:**
   Edit `assist/migrations/0003_vector_index.py`:
   ```sql
   WITH (lists = 500);  -- Default: 100
   ```

2. **Batch indexing:**
   Index lessons in smaller batches:
   ```bash
   python manage.py index_lessons_for_rag --lesson-id 1
   python manage.py index_lessons_for_rag --lesson-id 2
   # ... etc
   ```

3. **Connection pooling:**
   Add to `settings.py`:
   ```python
   DATABASES['default']['CONN_MAX_AGE'] = 600
   ```

### For Faster Responses

1. **Use smaller chat model:**
   ```bash
   ollama pull llama3.1:3b  # Faster, less accurate
   ```

2. **Reduce top_k:**
   Retrieve fewer chunks (3 instead of 5) in `assist/views.py`.

3. **Keep Ollama warm:**
   Ollama caches loaded models. First query is slower.

## Architecture Notes

**Data Flow:**
1. Student asks question → API endpoint (`/api/notmoodle/ask/`)
2. Question is embedded → `nomic-embed-text`
3. Vector similarity search → PostgreSQL + pgvector
4. Top-K chunks retrieved → Context for LLM
5. LLM generates answer → `llama3.1:8b-instruct`
6. Answer + sources returned → Frontend

**Storage:**
- **DocumentChunk**: ~5-10 chunks per lesson (depends on content length)
- **StudentQuestion**: 1 row per query (for logging/analytics)
- **Vector index**: IVFFlat for fast approximate nearest neighbor search

**Models:**
- `nomic-embed-text`: 768-dim embeddings, optimized for semantic search
- `llama3.1:8b-instruct`: 8B parameter model, good balance of speed/quality

## API Reference

### POST /api/notmoodle/ask/

Ask the AI assistant a question.

**Request:**
```json
{
  "message": "What is RAG?",
  "lesson_id": 1  // Optional: bias toward this lesson
}
```

**Response (200 OK):**
```json
{
  "reply": "RAG stands for Retrieval-Augmented Generation...",
  "sources": [
    {
      "lesson": "TEST101 - Introduction",
      "excerpt": "Retrieval-Augmented Generation (RAG)..."
    }
  ],
  "usage_today": 5
}
```

**Error (429 Too Many Requests):**
```json
{
  "error": "Daily question limit reached (100). Please try again tomorrow."
}
```

### GET /api/notmoodle/usage/

Get current user's usage stats.

**Response (200 OK):**
```json
{
  "questions_today": 15,
  "daily_limit": 100
}
```

## Future Enhancements

- [ ] Streaming responses for better UX
- [ ] Conversation history (multi-turn chat)
- [ ] File upload (PDF, DOCX) for additional context
- [ ] Teacher analytics dashboard
- [ ] Celery for background indexing
- [ ] Caching frequent questions
- [ ] Multi-language support
- [ ] Voice input/output

## Support

For issues or questions:
1. Check logs: Django console + Ollama logs
2. Review test suite: `python manage.py test assist`
3. Verify environment variables: `.env` file
4. Check PostgreSQL + pgvector installation

## License

Part of NotMoodle LMS project.
