# Database Setup Guide - NotMoodle

## 📚 Overview

NotMoodle automatically detects your database setup and configures itself accordingly:

- **PostgreSQL Available** → Full functionality including AI Assistant with personalized responses
- **PostgreSQL Not Available** → Automatic SQLite fallback, all features work except AI Assistant

## ✅ Feature Availability

### Works with SQLite (All Core Features)
✅ User authentication (Google OAuth, email/password)  
✅ Student management (profiles, enrollments)  
✅ Teacher management (profiles, classrooms)  
✅ Course management (create, edit, enroll)  
✅ Lesson management (create, edit, view)  
✅ Assignment management (create, submit, grade)  
✅ Reading lists and video tracking  
✅ Credits and GPA tracking  
✅ Classroom management  
✅ Grading system  
✅ File uploads (PDFs, submissions)  

### Requires PostgreSQL (AI Features Only)
🤖 AI Assistant with personalized responses  
🔍 Semantic search using pgvector  
📊 Document embeddings  

## 🚀 Quick Start

### Option 1: Use SQLite (No Setup Required)

The app will automatically use SQLite if PostgreSQL is not available. Just run:

```bash
cd NotMoodle
python manage.py migrate
python manage.py runserver
```

**Note:** The AI Assistant widget will show a message that PostgreSQL is required.

### Option 2: Enable AI Assistant with PostgreSQL + Docker

#### Step 1: Install Docker

- **Windows/Mac:** Download and install [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- **Linux:** Follow [Docker installation guide](https://docs.docker.com/engine/install/)

#### Step 2: Start PostgreSQL with pgvector

From the project root (where `docker-compose.yml` is located):

```bash
docker-compose up -d
```

This starts PostgreSQL with the pgvector extension enabled.

#### Step 3: Run Migrations

```bash
cd NotMoodle
python manage.py migrate
```

#### Step 4: Start Django

```bash
python manage.py runserver
```

You should see: `🐘 Database: PostgreSQL (AI assistant enabled with pgvector)`

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the `NotMoodle/` directory:

```env
# PostgreSQL Connection (if using Docker, these are the defaults)
DB_NAME=notmoodle_db
DB_USER=postgres
DB_PASSWORD=superuser
DB_HOST=localhost
DB_PORT=5432

# Force SQLite (optional - overrides PostgreSQL detection)
USE_SQLITE=false

# Ollama AI Settings (required for AI Assistant)
OLLAMA_BASE_URL=http://localhost:11434
AI_CHAT_MODEL=llama3.1:latest
AI_EMBED_MODEL=nomic-embed-text
AI_DAILY_QUESTION_LIMIT=100
```

### Force SQLite Mode

If you want to temporarily use SQLite even when PostgreSQL is available:

```env
USE_SQLITE=true
```

## 🤖 AI Assistant Personalization Features

When PostgreSQL is enabled, the AI Assistant provides **personalized responses** for each logged-in user:

### What the AI Knows About You

1. **Your Profile**
   - Username, full name, email
   - Enrollment number
   - Year of study, GPA, status

2. **Your Enrollments**
   - All courses you're enrolled in
   - All lessons you're taking
   - Enrollment dates and methods

3. **Your Progress**
   - Video watch status for each lesson
   - Reading list completion progress
   - Overall lesson grades and pass/fail status

4. **Your Assignments**
   - Upcoming assignments (next 10)
   - Recent past assignments (last 5)
   - Submission status
   - Grades and feedback

5. **Your Credits**
   - Total credits earned
   - Credits required for your course

### Example Personalized Questions

The AI can answer questions like:

- "What are my upcoming assignments?"
- "What's my current GPA?"
- "Which lessons have I passed?"
- "How many credits do I have?"
- "What's my grade in FIT2101?"
- "Have I watched the video for lesson X?"
- "When is my next assignment due?"
- "What feedback did I get on assignment Y?"

The AI will **address you by name** and refer to **your specific data** when answering!

## 📊 Database Detection

The app automatically detects PostgreSQL availability at startup:

### Success Messages

```
🐘 Database: PostgreSQL (AI assistant enabled with pgvector)
```
→ Full functionality enabled

```
🗄️  Database: SQLite (forced by USE_SQLITE environment variable)
```
→ SQLite forced via .env file

```
⚠️  PostgreSQL not available (connection error details...)
🗄️  Database: SQLite fallback (all features work except AI assistant)
```
→ PostgreSQL not available, automatic fallback

## 🔄 Switching Databases

### From SQLite to PostgreSQL

1. Start Docker PostgreSQL:
   ```bash
   docker-compose up -d
   ```

2. Run migrations:
   ```bash
   cd NotMoodle
   python manage.py migrate
   ```

3. (Optional) Copy data from SQLite to PostgreSQL:
   ```bash
   # Export from SQLite
   python manage.py dumpdata --natural-foreign --natural-primary > data.json
   
   # Stop Django, start PostgreSQL, then import
   python manage.py loaddata data.json
   ```

4. Restart Django server

### From PostgreSQL to SQLite

1. Set in `.env`:
   ```env
   USE_SQLITE=true
   ```

2. Restart Django server

## 🐛 Troubleshooting

### "AI Assistant requires PostgreSQL" Error

**Cause:** Using SQLite database  
**Solution:** Follow "Option 2: Enable AI Assistant" above

### PostgreSQL Connection Refused

**Symptoms:**
```
⚠️  PostgreSQL not available (connection refused)
🗄️  Database: SQLite fallback
```

**Solutions:**
1. Check Docker is running: `docker ps`
2. Start PostgreSQL: `docker-compose up -d`
3. Check PostgreSQL logs: `docker-compose logs postgres`
4. Verify connection settings in `.env`

### Import Error: No module named 'psycopg2'

**Solution:**
```bash
pip install psycopg2-binary
```

### Import Error: No module named 'pgvector'

**Solution:**
```bash
pip install pgvector
```

### AI Assistant Returns Empty Responses

**Possible causes:**
1. Ollama not running
2. No document chunks indexed
3. Wrong model specified

**Solutions:**
1. Start Ollama: See `AI_ASSISTANT_GUIDE.md`
2. Index lesson documents:
   ```bash
   python manage.py index_lessons
   ```
3. Check `OLLAMA_BASE_URL` in settings

## 📦 Docker Commands

```bash
# Start PostgreSQL
docker-compose up -d

# Stop PostgreSQL
docker-compose down

# View logs
docker-compose logs -f postgres

# Reset database (⚠️ deletes all data)
docker-compose down -v
docker-compose up -d
python manage.py migrate
```

## 🔐 Production Considerations

### Security

1. Change default PostgreSQL password in `docker-compose.yml`
2. Use strong `SECRET_KEY` in settings.py
3. Set `DEBUG = False` in production
4. Configure proper `ALLOWED_HOSTS`

### Database Backup

```bash
# Backup PostgreSQL
docker exec -t notmoodle-postgres pg_dump -U postgres notmoodle_db > backup.sql

# Restore PostgreSQL
cat backup.sql | docker exec -i notmoodle-postgres psql -U postgres notmoodle_db

# Backup SQLite
cp NotMoodle/db.sqlite3 backup_$(date +%Y%m%d).sqlite3
```

## 📚 Additional Resources

- [AI_ASSISTANT_GUIDE.md](./AI_ASSISTANT_GUIDE.md) - AI Assistant setup and usage
- [CI_CD_GUIDE.md](./CI_CD_GUIDE.md) - Testing and deployment
- [IMPLEMENTATION_SUMMARY.md](./IMPLEMENTATION_SUMMARY.md) - Project overview
- [Docker Compose Docs](https://docs.docker.com/compose/)
- [PostgreSQL Docs](https://www.postgresql.org/docs/)
- [pgvector Extension](https://github.com/pgvector/pgvector)

## 🆘 Getting Help

If you encounter issues:

1. Check this guide first
2. Review error messages in the terminal
3. Check Docker logs: `docker-compose logs`
4. Verify all dependencies are installed: `pip install -r requirements.txt`
5. Check `.env` file configuration

---

**Remember:** All core NotMoodle features work with SQLite. PostgreSQL is only required for the AI Assistant feature!

