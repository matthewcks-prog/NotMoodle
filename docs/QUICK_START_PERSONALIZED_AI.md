# Quick Start - Personalized AI Assistant

## 🎯 New Features Implemented

### 1. ✨ Fully Personalized AI Responses
The AI Assistant now knows **everything about each logged-in user** and provides personalized answers!

### 2. 🔄 Automatic Database Fallback
The app automatically uses SQLite if PostgreSQL is not available. No configuration needed!

---

## 🚀 Quick Start (Choose Your Path)

### Path A: Quick Testing (SQLite - No Setup)

Just run the app - it will automatically use SQLite:

```bash
cd NotMoodle
python manage.py migrate
python manage.py runserver
```

✅ **What works:** ALL features except AI Assistant  
❌ **What doesn't:** AI Assistant (requires PostgreSQL)

---

### Path B: Full Features (PostgreSQL + AI)

#### Step 1: Start PostgreSQL

```bash
# From project root
docker-compose up -d
```

#### Step 2: Verify PostgreSQL is Running

```bash
docker ps
# Should show "notmoodle-postgres" running
```

#### Step 3: Run Django

```bash
cd NotMoodle
python manage.py migrate
python manage.py runserver
```

You should see:
```
🐘 Database: PostgreSQL (AI assistant enabled with pgvector)
```

#### Step 4: Start Ollama (for AI features)

```bash
# In a separate terminal
ollama serve

# Pull required models (if not already downloaded)
ollama pull llama3.1:latest
ollama pull nomic-embed-text
```

#### Step 5: Index Lesson Documents

```bash
cd NotMoodle
python manage.py index_lessons
```

✅ **What works:** EVERYTHING including personalized AI Assistant!

---

## 💡 Test the Personalization

### 1. Create Test Students

Login as admin or teacher and create two students with different enrollments.

### 2. Enroll in Different Courses

- Student A: Enroll in "Software Engineering"
- Student B: Enroll in "Database Design"

### 3. Create and Grade Assignments

Add some assignments and grade them differently for each student.

### 4. Test AI Assistant

Login as **Student A**:
- Open AI Assistant widget (bottom-right button)
- Ask: "What are my upcoming assignments?"
- Ask: "What's my current GPA?"
- Ask: "What courses am I enrolled in?"

Login as **Student B**:
- Open AI Assistant widget
- Ask the **same questions**
- Notice: **Different answers** based on their data!

### 5. Try Personalized Questions

- "What's my enrollment number?"
- "Have I submitted Assignment 1?"
- "What grade did I get on my last assignment?"
- "What feedback did my teacher give me?"
- "Am I passing FIT2101?"
- "What should I study for my next assignment?"

---

## 🔍 What the AI Knows About Each User

When you ask a question, the AI has access to:

✅ Your profile (name, enrollment #, GPA, year, status)  
✅ Your credits earned  
✅ Your enrolled courses  
✅ Your enrolled lessons  
✅ Your video watch progress  
✅ Your reading list progress  
✅ Your upcoming assignments (next 10)  
✅ Your past assignments (last 5)  
✅ Your grades and feedback  
✅ Your submission status  

**And the AI addresses you by name!** 🎉

---

## 📊 Console Messages

### When PostgreSQL is Available:
```
🐘 Database: PostgreSQL (AI assistant enabled with pgvector)
```

### When PostgreSQL is Not Available:
```
⚠️  PostgreSQL not available (could not connect to server...)
🗄️  Database: SQLite fallback (all features work except AI assistant)
```

### When Forcing SQLite:
```
🗄️  Database: SQLite (forced by USE_SQLITE environment variable)
```

---

## ⚙️ Configuration

### Force SQLite Mode (Optional)

Create `.env` file in `NotMoodle/` directory:

```env
USE_SQLITE=true
```

This forces SQLite even if PostgreSQL is available.

### PostgreSQL Configuration (Optional)

```env
DB_NAME=notmoodle_db
DB_USER=postgres
DB_PASSWORD=superuser
DB_HOST=localhost
DB_PORT=5432
```

---

## 🐛 Troubleshooting

### AI Assistant Shows "Requires PostgreSQL" Error

**Solution:** Follow "Path B" above to start PostgreSQL.

### Can't Connect to PostgreSQL

**Check Docker:**
```bash
docker ps
docker-compose logs postgres
```

**Restart Docker:**
```bash
docker-compose down
docker-compose up -d
```

### AI Doesn't Know My Information

**Check:**
1. Are you logged in as a student (not teacher)?
2. Do you have a Student profile in the database?
3. Are you enrolled in any courses/lessons?

**Fix:** Make sure your User account has an associated Student profile.

### AI Gives Generic Answers

**Possible causes:**
1. No enrollments/assignments in the system
2. Student profile incomplete

**Solution:** Add enrollments, lessons, and assignments through the admin or teacher interface.

---

## 📚 Full Documentation

- **`DATABASE_SETUP_GUIDE.md`** - Complete database setup
- **`AI_ASSISTANT_GUIDE.md`** - AI features and usage
- **`PERSONALIZED_AI_SUMMARY.md`** - Implementation details
- **`IMPLEMENTATION_SUMMARY.md`** - Project overview

---

## 🎉 What's Different Now?

### Before:
❌ AI gave same answer to all users  
❌ Couldn't answer "What's MY grade?"  
❌ Didn't know about YOUR assignments  
❌ Generic responses only  

### After:
✅ AI knows each user personally  
✅ Answers "What's MY grade?" accurately  
✅ Lists YOUR specific assignments  
✅ Addresses you by name  
✅ Each user gets different answers  

---

## ✨ Example Interaction

**You:** "What are my upcoming assignments?"

**AI:** 
> Hi John Doe! You have **3 upcoming assignments**:
> 
> 1. **Assignment 1 - Requirements Gathering**  
>    📚 FIT2101 - Software Engineering  
>    📅 Due: October 25, 2025 at 23:59  
>    📊 Worth: 20 marks (30% of lesson grade)  
>    ⚠️ Status: Not yet submitted
> 
> 2. **Project Proposal**  
>    📚 FIT3171 - Database Design  
>    📅 Due: October 30, 2025 at 23:59  
>    📊 Worth: 30 marks (25% of lesson grade)  
>    Status: Not yet submitted
> 
> The first one is due soonest - make sure you start working on it! 🎯

---

## 🚀 Get Started Now!

Choose your path above and start testing the personalized AI assistant! 🎉

