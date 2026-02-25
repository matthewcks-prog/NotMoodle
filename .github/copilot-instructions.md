# NotMoodle AI Coding Assistant Guide

## Project Overview
Django-based Learning Management System (LMS) with RAG-powered AI assistant. Multi-tenant architecture supporting students, teachers, and course management with local LLM integration via Ollama.

## Architecture

### Core Apps & Responsibilities
- **student_management**: User/Student models, enrollment, credit tracking
- **teachersManagement**: TeacherProfile, teacher views/authentication
- **lesson_management**: Lesson content, assignments, submissions, prerequisites
- **course_management**: Course/Enrollment models, course-lesson relationships via `CourseLesson`
- **classroom_and_grading**: Classroom scheduling, student rosters, grading
- **assist**: AI chatbot with RAG (DocumentChunk, StudentQuestion models)
- **welcome_page**: Landing page, error handlers (404/500/403/400)

### Key Model Relationships
```python
# User roles via OneToOne
User → Student (student_management.models)
User → TeacherProfile (teachersManagement.models)

# Course structure
Course ←→ Lesson (M2M through CourseLesson)
Lesson.prerequisites → Lesson (self M2M, tracks unlocks)

# Enrollment & Classroom
Student → Enrollment → Course
Classroom → (Course, Lesson, Teacher, start/end dates)
ClassroomStudent → (Classroom, Student) # roster

# AI/RAG
Lesson → DocumentChunk (vector embeddings, 768-dim nomic-embed-text)
User → StudentQuestion (usage tracking, rate limiting)
```

### Database: PostgreSQL + pgvector
- **NOT SQLite** – project requires pgvector extension for semantic search
- Default connection: `localhost:5432` (or Docker on 5433)
- Configure via env vars: `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`
- Migrations enable pgvector: `assist/migrations/0001_enable_pgvector.py`

## Critical Workflows

### Setup (PowerShell/Windows)
```powershell
# 1. Create venv and install deps
python -m venv venv
venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt

# 2. Setup PostgreSQL (Docker recommended)
docker-compose up -d  # starts postgres-pgvector on port 5433

# 3. Run migrations
cd NotMoodle
python manage.py migrate

# 4. Create superuser and start server
python manage.py createsuperuser
python manage.py runserver
```

### AI Assistant Setup (One-time)
```powershell
# 1. Install Ollama (https://ollama.ai/download)
ollama --version

# 2. Pull models (~5GB download)
ollama pull nomic-embed-text      # 768-dim embeddings
ollama pull llama3.1:latest       # 8B chat model

# 3. Index lesson content for RAG
python manage.py index_lessons_for_rag
```

### Re-indexing Lessons
After creating/updating lesson content, re-index for AI:
```powershell
python manage.py index_lessons_for_rag --force  # re-index all
python manage.py index_lessons_for_rag --lesson-id 42  # single lesson
```

### Running Tests
```powershell
python manage.py test                    # all tests
python manage.py test student_management # single app

# With coverage
pip install coverage
coverage run --source='.' manage.py test
coverage report
```

### GitLab CI/CD
Tests run automatically on every push via `.gitlab-ci.yml`:
- **Full test suite**: Runs all Django tests with PostgreSQL
- **Per-app tests**: Run in parallel when specific app code changes
- **Code linting**: Flake8 checks (warnings only, won't block)
- **Coverage reporting**: Displays test coverage percentage

Pipeline uses `fit2101` runner tag and Python 3.11 image.

## Project-Specific Conventions

### URL Namespaces (CRITICAL for reverse())
- Teacher URLs: `teachersManagement:teacher_home`, `teachersManagement:teacher_login`
- Student URLs: `student_management:student_dashboard`, `student_management:student_login`
- Lessons (student-facing): `lessons:lesson_detail`
- Teacher courses: `teacher_courses:course_list`
- Classrooms: `classroom_and_grading:classroom_list`
- AI API: `assist:ask_assistant`

### Authentication Patterns
- Django's built-in User model for auth
- Student/Teacher profiles via OneToOne relationships
- Social auth via Google OAuth (`social-auth-app-django`)
- Custom pipeline: `student_management.pipeline.create_student_profile`

### Service Layer Pattern
When editing course operations, check `course_management/services.py`:
```python
# Example: Always use service functions for business logic
from course_management.services import enrol_student_in_course
enrollment, created = enrol_student_in_course(request, student, course_id)
```

### AI/RAG Integration
- **Vector search**: Uses `pgvector.django.CosineDistance` for similarity
- **Rate limiting**: 100 questions/day/user (see `AI_DAILY_QUESTION_LIMIT`)
- **Context retrieval**: `assist/views.py::retrieve_context()` fetches top-k chunks
- **Ollama client**: `assist/ollama.py` wraps embedding/chat APIs
- **System prompt**: Defined in `assist/views.py::ask_assistant` view

### Model Status Fields
- **Lesson.status**: `draft`, `published`, `archived` (only `published` indexed)
- **Course.status**: `active`, `inactive`
- **Student.status**: `active`, `dropout`, `reactive`

### Environment Configuration
Uses `python-dotenv` to load `.env` from `NotMoodle/` directory:
```env
# Database
DB_NAME=notmoodle_db
DB_USER=postgres
DB_PASSWORD=superuser
DB_HOST=localhost
DB_PORT=5433

# Ollama
OLLAMA_BASE_URL=http://localhost:11434
AI_CHAT_MODEL=llama3.1:latest
AI_EMBED_MODEL=nomic-embed-text
AI_DAILY_QUESTION_LIMIT=100

# OAuth (optional)
GOOGLE_OAUTH2_CLIENT_ID=...
GOOGLE_OAUTH2_CLIENT_SECRET=...
```

## Common Pitfalls

1. **Forgotten migrations**: Run `python manage.py migrate` after model changes
2. **SQLite database**: Project uses PostgreSQL – don't revert to SQLite
3. **Lesson indexing**: AI won't see new content until `index_lessons_for_rag` runs
4. **URL namespace errors**: Always use full namespace (e.g., `student_management:student_dashboard`)
5. **Docker port conflict**: If 5432 is taken, docker-compose uses 5433 – update `DB_PORT`
6. **Ollama not running**: Check `http://localhost:11434/api/tags` before testing AI

## Key Files for Reference

- **Settings**: `NotMoodle/NotMoodle/settings.py` (DB, AI config, installed apps)
- **URL routing**: `NotMoodle/NotMoodle/urls.py` (central URL config)
- **AI views**: `NotMoodle/assist/views.py` (RAG retrieval, chat endpoint)
- **AI models**: `NotMoodle/assist/models.py` (DocumentChunk, StudentQuestion)
- **Management command**: `NotMoodle/assist/management/commands/index_lessons_for_rag.py`
- **Docker setup**: `NotMoodle/docker-compose.yml` (PostgreSQL + pgvector)

## Documentation References
- Setup guides: `README.md`, `AI_ASSISTANT_GUIDE.md`, `QUICKSTART_AI.md`
- Comprehensive AI setup: `README_NOTMOODLE_AI.md`
