# Quick Start: Running Tests

## Prerequisites

```bash
# Ensure you're in the project root directory
cd CL_Friday4pm_Team8

# Install development dependencies
pip install -r requirements-dev.txt
```

## Running Tests

### Basic Test Run

```bash
cd NotMoodle
pytest
```

This will:
- Run all tests
- Display coverage report in terminal
- Generate HTML coverage report in `htmlcov/`
- Create `coverage.xml` (Cobertura format for GitLab)
- Create `report.xml` (JUnit format for test reporting)

### View Coverage Report

After running tests, open the HTML coverage report:

```bash
# Windows
start htmlcov/index.html

# Mac/Linux
open htmlcov/index.html
# or
xdg-open htmlcov/index.html
```

### Run Specific Tests

```bash
# Run tests for a specific app
pytest assist/tests/

# Run a specific test file
pytest assist/tests/test_models.py

# Run a specific test class
pytest assist/tests/test_models.py::TestDocumentChunk

# Run a specific test method
pytest assist/tests/test_models.py::TestDocumentChunk::test_create_document_chunk
```

### Run Tests in Parallel (Faster)

```bash
pytest -n auto
```

### Run Tests with Less Verbose Output

```bash
pytest -q  # Quiet mode
pytest --tb=short  # Shorter tracebacks
```

### Run Tests and Stop on First Failure

```bash
pytest -x
```

## Troubleshooting

### Missing Dependencies

If you see `ModuleNotFoundError`, install dev dependencies:

```bash
pip install -r requirements-dev.txt
```

### Database Issues

Tests use SQLite in-memory database automatically. If you see database errors:

```bash
# Ensure USE_SQLITE environment variable is set
export USE_SQLITE=true  # Linux/Mac
$env:USE_SQLITE="true"  # Windows PowerShell
```

### Coverage Not Generating

Make sure `pytest-cov` is installed:

```bash
pip install pytest-cov
```

## Expected Output

After running tests, you should see:

```
================================ test session starts =================================
platform win32 -- Python 3.12.7, pytest-7.4.4, pluggy-1.5.0
configfile: pytest.ini
plugins: django-4.9.0, cov-6.0.0, xdist-3.6.1
collected 150 items

assist/tests/test_models.py ........                                          [  5%]
assist/tests/test_ollama.py ..........                                        [ 12%]
assist/tests/test_views.py ....................                               [ 25%]
classroom_and_grading/tests/test_models.py ................                   [ 36%]
classroom_and_grading/tests/test_views.py ...........                         [ 43%]
classroom_and_grading/tests/test_forms.py .........                           [ 49%]
... (more tests)

================================ 150 passed in 5.23s =================================

---------- coverage: platform win32, python 3.12.7-final-0 ----------
Name                                    Stmts   Miss Branch BrPart  Cover   Missing
-------------------------------------------------------------------------------------
assist/models.py                           25      0      4      0   100%
assist/ollama.py                           35      0      8      0   100%
assist/views.py                           120      2     28      2    97%   245-246
classroom_and_grading/models.py            45      0     10      0   100%
... (more files)
-------------------------------------------------------------------------------------
TOTAL                                    2850     52    420     12    96%

Coverage HTML written to htmlcov/index.html
Coverage XML written to coverage.xml
```

## Next Steps

1. **View Coverage Report:** Open `htmlcov/index.html` to see detailed coverage
2. **Fix Failing Tests:** If any tests fail, read the error messages and fix issues
3. **Add New Tests:** When adding features, write tests first (TDD)
4. **Run Tests in CI:** Push to GitLab and view automated test results

## GitLab CI/CD

Tests run automatically on:
- Every push to any branch
- Every merge request

View results:
- **Pipeline page:** See test status and coverage percentage
- **MR widget:** Coverage diff vs target branch
- **Artifacts:** Download HTML coverage report

## Getting Help

- Check `TEST_SETUP_SUMMARY.md` for comprehensive documentation
- Review `conftest.py` for available fixtures
- Read individual test files for examples
- See [pytest documentation](https://docs.pytest.org/)

