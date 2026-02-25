# NotMoodle AI Assistant - Complete Guide

## 🎉 Setup Complete!

Your AI Assistant is now fully functional with local, AI powered by Ollama.

---

## 🚀 What's Working

### Infrastructure
- ✅ **PostgreSQL 16 with pgvector** running in Docker (port 5433)
- ✅ **Ollama** running locally with models:
  - `nomic-embed-text` (768-dim embeddings)
  - `llama3.1:latest` (8B parameter chat model)
- ✅ **Django** configured with assist app enabled
- ✅ **Vector search** with IVFFlat index for fast similarity

### Features
- ✅ **AI Chat Widget** - Visible floating button on student dashboard
- ✅ **RAG System** - Retrieves relevant lesson content automatically
- ✅ **Personalized Responses** - AI knows your profile, grades, assignments, and progress
- ✅ **Rate Limiting** - 100 questions per day per student
- ✅ **Usage Tracking** - All questions logged in database
- ✅ **Contextual Answers** - Uses enrolled course content
- ✅ **Multi-User Support** - Each student gets personalized answers based on their own data

---

## 📍 How to Access

1. **Login as Student**: http://127.0.0.1:8000/students/login/
2. **Go to Dashboard**: Navigate to student dashboard
3. **Open AI Assistant**: Click the purple gradient button (bottom-right)
4. **Ask Questions**: Type and submit your questions

---

## 🎯 Personalized AI Assistant

**NEW FEATURE!** The AI Assistant now provides personalized responses based on YOUR specific profile and data.

### What the AI Knows About You

When you ask a question, the AI has access to:

1. **Your Profile Information**
   - Username, full name, email
   - Enrollment number
   - Year of study, GPA, student status

2. **Your Enrollments**
   - All courses you're enrolled in
   - All lessons you're taking
   - When you enrolled and how (self-enrollment vs. teacher)

3. **Your Academic Progress**
   - Video watch status for each lesson
   - Reading list completion progress
   - Overall lesson grades (percentage and pass/fail)
   - Number of graded assignments

4. **Your Assignments**
   - **Upcoming assignments** (next 10 due)
   - **Recent past assignments** (last 5)
   - Submission status (submitted or not)
   - Grades and teacher feedback

5. **Your Credits**
   - Total credits earned
   - Credits required for your course

### How It's Personalized

- ✅ **AI addresses you by name** when appropriate
- ✅ **References YOUR specific enrollments** when you ask about courses
- ✅ **Shows YOUR grades and progress** when you ask about performance
- ✅ **Lists YOUR assignments** when you ask about deadlines
- ✅ **Tracks YOUR submissions** when you ask about assignment status
- ✅ **Each student gets different answers** based on their own data

### Example: Same Question, Different Answers

**Student A asks:** "What are my upcoming assignments?"  
**AI responds:** "Hi Alex! You have 3 upcoming assignments: Assignment 1 for FIT2101 due Oct 25..."

**Student B asks:** "What are my upcoming assignments?"  
**AI responds:** "Hi Jordan! You have 1 upcoming assignment: Final Project for FIT3171 due Nov 5..."

---

## 💡 Example Questions to Try

### Personal Profile Questions
- "What's my enrollment number?"
- "What's my current GPA?"
- "How many credits do I have?"
- "What year of study am I in?"
- "What's my student status?"

### Your Enrollments
- "What courses am I enrolled in?"
- "What lessons am I taking?"
- "When did I enroll in FIT2101?"
- "Tell me about my enrolled courses"

### Your Progress
- "Which lessons have I passed?"
- "What's my grade in FIT2101?"
- "Have I watched the video for lesson X?"
- "How many readings have I completed?"
- "Show me my lesson progress"

### Your Assignments
- "What are my upcoming assignments?"
- "When is my next assignment due?"
- "Have I submitted assignment X?"
- "What's my grade on assignment Y?"
- "What feedback did I get on my last assignment?"
- "Do I have any overdue assignments?"

### Content Questions (With Your Context)
- "What is software engineering?" *(Uses content from YOUR enrolled lessons)*
- "Explain the scrum methodology" *(Prioritizes YOUR course materials)*
- "How do sprints work in agile development?" *(Answers based on YOUR curriculum)*

### Combined Questions
- "What do I need to study for my upcoming assignments?"
- "Am I on track to pass FIT2101?"
- "What should I focus on this week?"
- "Help me understand this lesson" *(AI knows which lessons YOU'RE in)*
- "What should I study first?"
- "Explain [specific topic from lesson]"

---

## 🔧 Technical Details

### Database
```
Host: localhost
Port: 5433 (Docker container)
Database: notmoodle_db
User: postgres
Password: superuser
```

### Ollama
```
Service: http://localhost:11434
Chat Model: llama3.1:latest
Embedding Model: nomic-embed-text
```

### Django Commands
```bash
# Index lessons when new content is added
python manage.py index_lessons_for_rag

# Check current indexed lessons
python manage.py shell
>>> from assist.models import DocumentChunk
>>> DocumentChunk.objects.count()
```

---

## 🔄 Workflow for Adding New Content

1. **Teacher creates/publishes lesson** via Django admin
2. **Run indexing command**: `python manage.py index_lessons_for_rag`
3. **Lesson chunks** automatically embedded and stored in vector DB
4. **Students can now ask questions** about the new content

---
### Better Responses
- **Improved system prompt** with clear role definition
- **Contextual awareness** of enrolled courses
- **Step-by-step explanations** for complex topics
- **Markdown formatting** support

---

## 🛠️ Maintenance

### Docker Container
```powershell
# Check if container is running
docker ps

# Stop container
docker stop postgres-pgvector

# Start container
docker start postgres-pgvector

# View logs
docker logs postgres-pgvector
```

### Ollama Service
```powershell
# Check if Ollama is running
curl http://localhost:11434/api/tags

# List downloaded models
ollama list

# Pull new models
ollama pull [model-name]
```

### Django Server
```powershell
# Start server
cd C:\Users\matth\OneDrive\Documents\Monash\SEM22025\NotMoodle\CL_Friday4pm_Team8\NotMoodle
python manage.py runserver

# Create superuser
python manage.py createsuperuser

# Run migrations
python manage.py migrate
```

---

## 📊 Current System Status

### Indexed Content
- **1 lesson**: Software engineering process and management (FIT2101)
- **1 chunk**: Embedded and searchable

### Models Performance
- **Embedding**: ~1-2 seconds per query
- **Chat Response**: ~5-10 seconds (depends on question complexity)
- **All local**: No API costs, no internet required

---

## 🐛 Troubleshooting

### "Failed to generate response"
1. Check Ollama is running: `curl http://localhost:11434/api/tags`
2. Check model name matches: Should be `llama3.1:latest`
3. Check server logs for detailed error

### "No relevant content found"
1. Run: `python manage.py index_lessons_for_rag`
2. Verify lessons are published (not draft)
3. Check DocumentChunk count in database

### Vector Query Errors
1. Ensure pgvector extension enabled: `CREATE EXTENSION IF NOT EXISTS vector;`
2. Check Django migrations applied
3. Use `CosineDistance` not `.cosine_distance()` method

### Docker Container Not Running
1. Start Docker Desktop
2. Start container: `docker start postgres-pgvector`
3. Verify port 5433 available

---

## 🎯 Next Steps

1. **Add more lessons** via teacher interface
2. **Test with diverse questions** to improve prompts
3. **Monitor usage** via Django admin → Student Questions
4. **Adjust rate limits** if needed (AI_DAILY_QUESTION_LIMIT in settings.py)
5. **Consider fine-tuning** prompts based on student feedback

---

## 📝 Configuration Files

### Key Files Modified
- `NotMoodle/settings.py` - Database and Ollama config
- `assist/views.py` - System prompt and RAG logic
- `assist/templates/assist/ai_assistant_widget.html` - UI styling
- `assist/migrations/0001_enable_pgvector.py` - Vector extension
- `assist/migrations/0003_vector_index.py` - IVFFlat index

### Environment Variables (.env)
```env
# PostgreSQL
DB_PASSWORD=superuser

# Ollama
OLLAMA_BASE_URL=http://localhost:11434
AI_CHAT_MODEL=llama3.1:latest
AI_EMBED_MODEL=nomic-embed-text
AI_DAILY_QUESTION_LIMIT=100
```

---

## ✨ Features for Future Enhancement

- [ ] Multi-turn conversations (chat history)
- [ ] File upload support (PDFs, documents)
- [ ] Code syntax highlighting in responses
- [ ] Voice input/output
- [ ] Student feedback buttons (👍/👎)
- [ ] Admin analytics dashboard
- [ ] Export chat history
- [ ] Suggested follow-up questions

---

**Created**: October 11, 2025  
**Version**: 1.0  
**Status**: ✅ Production Ready (Development)
