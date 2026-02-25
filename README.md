This repository is a **portfolio edition** of a team project completed for **Monash University FIT2101 (Software Engineering Process and Management)**.

The original NotMoodle LMS was developed collaboratively by the **CL_Friday4pm_Team8** group with shared ownership across multiple team members.  
This repo exists to showcase the **system concept, architecture, engineering process, and my individual contributions** in a way that’s appropriate for a public portfolio.

---

## Engineering process (FIT2101)

This unit emphasised **software engineering process and management** even more than the actual coding to provide a working final product.

Our team practised:

- Scrum‑inspired workflow (sprint planning, reviews, retrospectives)
- Definition of Done and explicit quality gates (tests, linting, code review)
- Task and time tracking as required by the unit on Jira
- Risk identification and mitigation planning (e.g. AI stack, database changes)
- Analysis of alternatives for the AI stack, database, and deployment approach
- Git feature‑branch workflow with merge requests, code reviews and good practices

Within that framework I often played the **“integrator” role** – making sure features, tests, and infrastructure changes could be merged safely and everything still worked together.

## Project overview

**Problem:** Build a Learning Management System (LMS) for a teaching start‑up focused on flexible, self‑paced learning.

**Core capabilities delivered:**
- Multi‑role access (students, teachers/admin)
- Course and lesson management (create/edit/assign content)
- Classroom tracking (learning groups progressing through lessons)
- Student management and reporting (enrolment, progress tracking, activity stats)
- NotMoodle AI assistant (chat‑style help grounded in course content and student data)

> The exact scope was negotiated with the unit “client” (teaching associate) as part of the FIT2101 process.

---

## Demo

You can **watch a short demo of the NotMoodle LMS** here:

- [Project demo (mp4, root of this repo)](demo_NotMoodle.mp4)

---

## Tech stack

- **Frontend:** Django server‑rendered templates, vanilla JavaScript, custom CSS
- **Backend:** Python 3.x, Django 5.x
- **Database:**
  - SQLite for fast local testing (`settings_test.py`)
  - PostgreSQL 14+ with `pgvector` for AI assistant features
- **AI / ML:** Ollama (`llama3.1` chat model, `nomic-embed-text` embeddings)
- **Testing:** `pytest`, `pytest-django`, `pytest-xdist`, `model-bakery`, `freezegun`, `responses`
- **CI/CD:** GitLab CI pipeline for tests, linting, and coverage publishing
- **Tooling:** `pyproject.toml` for black, isort, mypy, coverage and pytest configuration

---
## My contributions

I focused on integrating and hardening the following parts(among others) of the system:

- **NotMoodle AI assistant (`assist` app)**  
  - Designed and implemented the RAG pipeline (lesson chunking, embeddings, and vector similarity search using `pgvector`).  
  - Added `DocumentChunk` and `StudentQuestion` models plus migrations (including enabling `pgvector` and creating an IVFFlat index).  
  - Exposed `/api/notmoodle/ask/` and `/api/notmoodle/usage/` endpoints with authentication, rate limiting, error handling, and usage tracking.  
  - Implemented the floating chat widget UI (HTML/JS/CSS) embedded in the student dashboard.

- **Core lessons and classroom logic**  
  - Introduced a pytest‑based test infrastructure: `.coveragerc`, `pytest.ini`, `requirements-dev.txt`, `NotMoodle/settings_test.py`, and a shared `conftest.py`.  
  - Worked through the core lessons and classroom logic with the team (lesson sequencing, visibility rules, classroom tracking) and ensured it was properly exercised by the test suite.  
  - Added tests across all major Django apps (models, views, forms, admin, pipelines), totalling ~150+ test cases and targeting ~95–100% line and branch coverage.  
  - Optimised for fast feedback: in‑memory SQLite DB, parallel execution via `pytest-xdist`, and clear markers for unit/integration/API tests.

- **CI/CD and developer experience**  
  - Configured `.gitlab-ci.yml` to run tests and linters on every push, publish coverage and JUnit reports, and surface quality gates in merge requests.  

- **Integration & “glue” work**  
  - Ensured database, AI stack, test configuration, and documentation all features/logic worked together end‑to‑end so the team could reliably run the app, the AI assistant, and the full test suite.

- **Credits**
This project was originally developed as a team submission for FIT2101.
I’m grateful to my teammates for their collaboration and contributions.

---


---

## Running this project locally

> These steps assume you have a local Python environment. For full AI assistant setup (PostgreSQL + Ollama), see the docs listed below.

### Prerequisites

- **Python:** 3.10+  
- **Database (basic setup):** SQLite (default Django configuration)  
- **Database (AI features):** PostgreSQL 14+ with `pgvector` extension  

### Quick start (app only)

```bash
# 1. Clone this repository
git clone <this-repo-url>
cd NotMoodle

# 2. Create and activate a virtual environment
python -m venv venv

# Windows (PowerShell)
venv\Scripts\activate

# macOS / Linux (bash/zsh)
source venv/bin/activate

# 3. Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 4. Run database migrations
cd NotMoodle
python manage.py migrate

# 5. Start the development server
python manage.py runserver
```

Then open `http://127.0.0.1:8000/` in your browser.

### Admin access

Create a superuser to access the Django admin:

```bash
python manage.py createsuperuser
```

Then visit `http://127.0.0.1:8000/admin/` and log in with your credentials.

---

## Running the test suite

This project uses **pytest** for comprehensive testing with near‑complete line and branch coverage.

### Running tests locally

1. **Install development dependencies:**
   ```bash
   pip install -r requirements-dev.txt
   ```

2. **Run all tests with coverage:**
   ```bash
   cd NotMoodle
   pytest
   ```

3. **Run tests in parallel (faster):**
   ```bash
   pytest -n auto
   ```

4. **Run specific test files or apps:**
   ```bash
   pytest assist/tests/test_models.py
   pytest classroom_and_grading/tests/
   ```

5. **View HTML coverage report:**
   ```bash
   pytest  # Generates htmlcov/ directory
   # Then open htmlcov/index.html in your browser
   ```

### Coverage reports and CI

After running tests, you can view coverage in multiple formats:

- **Terminal:** Coverage summary is displayed after the test run
- **HTML report:** Open `htmlcov/index.html` in your browser
- **XML report:** `coverage.xml` (for CI/CD integration)
- **JUnit XML:** `report.xml` (for test failure tracking)

In the original team repository, tests were run automatically on every push and merge request via GitLab CI. The pipeline surfaced:
- Coverage percentage and pass/fail status in the merge request widget
- HTML coverage reports and XML reports as build artifacts

Key configuration files:
- `pytest.ini` – pytest configuration and options
- `.coveragerc` – coverage measurement settings
- `NotMoodle/settings_test.py` – Django settings optimised for testing (SQLite in‑memory, fast password hasher)
- `conftest.py` – global pytest fixtures (users, students, teachers, courses, etc.)

---

## Documentation

Additional project documentation is available in the `docs/` directory:

- `AI_ASSISTANT_GUIDE.md` – NotMoodle AI assistant behaviour, usage, and troubleshooting
- `DATABASE_SETUP_GUIDE.md` – PostgreSQL/pgvector and database setup steps
- `DELIVERABLES_SUMMARY.md` – checklist of test‑suite deliverables and statistics
- `IMPLEMENTATION_SUMMARY.md` – detailed breakdown of the AI assistant implementation
- `PERSONALIZED_AI_SUMMARY.md` – how the assistant personalises responses to each student
- `QUICK_START_PERSONALIZED_AI.md` – quick start for the personalised AI features
- `README_NOTMOODLE_AI.md` – end‑to‑end AI feature README (architecture + setup)
- `TEST_COVERAGE_ANALYSIS.md` – notes on coverage results
- `TESTING_QUICK_START.md` – quick start for running and writing tests
- `TEST_SETUP_SUMMARY.md` – comprehensive test setup documentation
