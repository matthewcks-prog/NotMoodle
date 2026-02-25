# NotMoodle AI Assistant - Implementation Summary

## ✅ Completed Features

### Backend Implementation

#### 1. Django App: `assist`
- ✅ Created new Django app with proper structure
- ✅ Registered in `INSTALLED_APPS`
- ✅ Admin interface configured for models

#### 2. Models
- ✅ **DocumentChunk**: Stores lesson content chunks with 768-dim vector embeddings
  - Fields: `lesson` (FK), `content`, `embedding` (VectorField), `token_count`, `created_at`
  - Indexed on `lesson` and `created_at`
- ✅ **StudentQuestion**: Logs all student queries for analytics/rate limiting
  - Fields: `user` (FK), `question`, `answer`, `tokens_in`, `tokens_out`, `created_at`
  - Indexed on `user` and `created_at`

#### 3. Database Migrations
- ✅ `0001_enable_pgvector.py`: Enables PostgreSQL vector extension
- ✅ `0002_initial_models.py`: Creates tables for DocumentChunk and StudentQuestion
- ✅ `0003_vector_index.py`: Adds IVFFlat index for fast vector similarity search

#### 4. Ollama Client (`assist/ollama.py`)
- ✅ `embed_texts()`: Generates embeddings via Ollama API
- ✅ `chat()`: OpenAI-compatible chat completions
- ✅ `estimate_tokens()`: Rough token count estimation
- ✅ Typed functions with docstrings
- ✅ Error handling with httpx

#### 5. Indexing Pipeline
- ✅ Management command: `python manage.py index_lessons_for_rag`
- ✅ Chunks lesson content (~800-1200 chars with 200 char overlap)
- ✅ Generates embeddings for all chunks
- ✅ Upserts chunks to database
- ✅ Idempotent with `--force` flag
- ✅ Supports `--lesson-id` for selective indexing

#### 6. Retrieval System
- ✅ `retrieve_context()` function in views
- ✅ Vector similarity search using pgvector cosine distance
- ✅ Top-K retrieval (default: 5 chunks)
- ✅ Optional lesson_id biasing for context-aware retrieval

#### 7. API Endpoints
- ✅ **POST `/api/notmoodle/ask/`**: Main chat endpoint
  - Authentication required
  - Rate limiting (100/day per user)
  - JSON request/response
  - Returns answer + sources + usage stats
  - Error handling (400, 429, 500)
- ✅ **GET `/api/notmoodle/usage/`**: Usage statistics
  - Returns questions_today and daily_limit

#### 8. Rate Limiting
- ✅ Per-user daily cap (100 queries default)
- ✅ Configurable via `AI_DAILY_QUESTION_LIMIT` setting
- ✅ Returns HTTP 429 when exceeded

### Frontend Implementation

#### 9. UI Components
- ✅ Floating "AI Assistant" button (bottom-right)
- ✅ Expandable chat panel (420px wide, 600px max height)
- ✅ Welcome message with usage instructions
- ✅ Question textarea with submit button
- ✅ Loading indicator (animated dots)
- ✅ Message display (user + assistant bubbles)
- ✅ Collapsible sources section
- ✅ Usage counter display
- ✅ Error messages display
- ✅ Mobile-responsive design

#### 10. JavaScript Functionality
- ✅ `toggleAIAssistant()`: Show/hide panel
- ✅ `askAssistant()`: Send question via fetch API
- ✅ `loadUsageStats()`: Get current usage
- ✅ CSRF token handling
- ✅ Auto-scroll to latest message
- ✅ Form disable during loading
- ✅ HTML escaping for security

#### 11. Styling
- ✅ Custom CSS (no external framework)
- ✅ Consistent with existing design system
- ✅ Smooth animations (fade-in, bounce)
- ✅ Accessible (ARIA labels, keyboard navigation)

### Configuration

#### 12. Settings
- ✅ `OLLAMA_BASE_URL` environment variable
- ✅ `AI_CHAT_MODEL` configuration
- ✅ `AI_EMBED_MODEL` configuration
- ✅ `AI_DAILY_QUESTION_LIMIT` setting
- ✅ All configurable via `.env` file

#### 13. Dependencies
- ✅ Added to `requirements.txt`:
  - `psycopg2-binary>=2.9.0`
  - `pgvector>=0.2.0`
  - `httpx>=0.25.0`

### Testing

#### 14. Unit Tests (`assist/tests.py`)
- ✅ **OllamaClientTests**: Test embedding and chat functions (with mocks)
- ✅ **DocumentChunkTests**: Test model creation and retrieval
- ✅ **AskAssistantViewTests**: Test API authentication, validation, rate limiting
- ✅ **StudentQuestionModelTests**: Test logging and ordering
- ✅ **UsageViewTests**: Test usage stats endpoint
- ✅ Total: 15+ test cases covering core functionality

### Documentation

#### 15. README_NOTMOODLE_AI.md
- ✅ Prerequisites (PostgreSQL, pgvector, Ollama)
- ✅ Installation instructions (step-by-step)
- ✅ Configuration guide
- ✅ Setup instructions (migrations, indexing)
- ✅ Usage examples
- ✅ Customization guide (models, chunk size, top_k, prompts)
- ✅ API reference
- ✅ Troubleshooting section
- ✅ Performance optimization tips
- ✅ Architecture notes

#### 16. Updated .github/copilot-instructions.md
- ✅ Added `assist` app to app structure
- ✅ New section on AI assistant architecture
- ✅ Workflows for setup and development
- ✅ Key customization points
- ✅ Updated dependencies list

## 📁 File Structure

```
NotMoodle/
├── assist/                          # New app
│   ├── __init__.py
│   ├── admin.py                     # Admin interfaces
│   ├── apps.py                      # App config
│   ├── models.py                    # DocumentChunk, StudentQuestion
│   ├── ollama.py                    # Ollama client functions
│   ├── tests.py                     # Unit tests
│   ├── urls.py                      # API routes
│   ├── views.py                     # retrieve_context(), ask_assistant()
│   ├── management/
│   │   └── commands/
│   │       └── index_lessons_for_rag.py
│   ├── migrations/
│   │   ├── 0001_enable_pgvector.py
│   │   ├── 0002_initial_models.py
│   │   └── 0003_vector_index.py
│   └── templates/
│       └── assist/
│           └── ai_assistant_widget.html  # Floating chat UI
├── NotMoodle/
│   ├── settings.py                  # Updated with Ollama config
│   └── urls.py                      # Added assist URLs
├── student_management/
│   └── templates/
│       └── student_management/
│           └── dashboard.html       # Includes AI widget
└── requirements.txt                 # Updated dependencies
```

## 🎯 Acceptance Criteria Met

✅ **Floating button**: "NotMoodle AI assistant" button in bottom-right  
✅ **Chat panel**: Expandable with context notice, textarea, lesson dropdown placeholder  
✅ **API endpoint**: `/api/notmoodle/ask/` returns grounded answers  
✅ **Insufficient context handling**: LLM says what's missing if context is poor  
✅ **Vector embeddings**: Chunks indexed with 768-dim vectors  
✅ **Vector similarity**: Retrieved by cosine distance via pgvector  
✅ **Rate limiting**: 100 queries/day per user enforced  
✅ **Usage counter**: Displays "X/100 queries today"  
✅ **Tests**: Unit tests for client, retrieval, views, rate limiting  
✅ **Code quality**: Typed, documented, small functions  
✅ **Production-ready**: Error handling, migrations, security (CSRF, auth)

## 🚀 Next Steps to Deploy

### 1. Install Prerequisites
```powershell
# Install PostgreSQL 14+ with pgvector
# Install Ollama from https://ollama.ai

# Pull models
ollama pull nomic-embed-text
ollama pull llama3.1:8b-instruct
```

### 2. Update Database Settings
Change `settings.py` from SQLite to PostgreSQL:
```python
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "notmoodle_db",
        "USER": "postgres",
        "PASSWORD": "your_password",
        "HOST": "localhost",
        "PORT": "5432",
    }
}
```

### 3. Create Database
```bash
psql -U postgres -c "CREATE DATABASE notmoodle_db;"
```

### 4. Run Migrations
```bash
cd NotMoodle
python manage.py migrate
```

### 5. Index Lessons
```bash
python manage.py index_lessons_for_rag
```

### 6. Start Services
```bash
# Terminal 1
ollama serve

# Terminal 2
python manage.py runserver
```

### 7. Test
- Log in as student
- Open dashboard
- Click "AI Assistant" button
- Ask: "What is this course about?"

## 📊 Metrics & Monitoring

Available via Django admin (`/admin/assist/`):
- **DocumentChunk**: View indexed content, token counts, lesson relationships
- **StudentQuestion**: View all queries, usage patterns, popular questions

Query statistics:
```python
from assist.models import StudentQuestion
from django.db.models import Count, Avg

# Daily usage
StudentQuestion.objects.filter(created_at__date=today).count()

# Average tokens
StudentQuestion.objects.aggregate(
    avg_in=Avg('tokens_in'),
    avg_out=Avg('tokens_out')
)

# Top users
StudentQuestion.objects.values('user__username').annotate(
    total=Count('id')
).order_by('-total')
```

## 🔧 Customization Examples

### Change chunk size
Edit `assist/management/commands/index_lessons_for_rag.py`:
```python
def _chunk_text(self, text: str, target_chars: int = 1000, overlap: int = 150)
```

### Adjust retrieval count
Edit `assist/views.py`:
```python
context_chunks = retrieve_context(message, lesson_id=lesson_id, top_k=3)
```

### Custom system prompt
Edit `assist/views.py` in `ask_assistant`:
```python
system_prompt = f"""You are a friendly tutor...
[your custom instructions]
"""
```

### Change rate limit
Edit `.env`:
```
AI_DAILY_QUESTION_LIMIT=50
```

## 🐛 Known Limitations

1. **Sequential embedding**: Indexing is single-threaded (consider Celery for large datasets)
2. **No streaming**: Responses appear all at once (could add SSE)
3. **No conversation history**: Each query is independent (could add session memory)
4. **Fixed dimensions**: Embeddings are 768-dim (changing model requires migration)
5. **PostgreSQL only**: Vector features require Postgres (can't use SQLite)

## 📝 License & Credits

Part of NotMoodle LMS project for FIT2101 at Monash University.

**Technologies:**
- Ollama (Meta's Llama models)
- pgvector (PostgreSQL vector extension)
- nomic-embed-text (Nomic AI)
- Django 5.x
