# Testing Framework

This directory contains tests for the backend API. We use pytest for testing.

## Setup

The test environment is configured in `conftest.py`, which sets up:
- A test SQLite database
- FastAPI test client
- Mock objects for services like the YOLO model

## Running Tests

### Using the run_tests.sh script

We've created a simple script to run tests:

```bash
# Run all tests
./run_tests.sh

# Run a specific test file
./run_tests.sh tests/test_stream_handler.py

# Generate HTML coverage report
./run_tests.sh coverage
```

### Using pytest directly

```bash
# Run all tests
python -m pytest

# Run a specific test file
python -m pytest tests/test_stream_handler.py

# Run tests with specific markers
python -m pytest -m "not slow"

# Show verbose output
python -m pytest -v

# Generate coverage report
python -m pytest --cov=core --cov=entities --cov=utils --cov-report=term
```

## Test Organization

Tests are organized by module:

- `test_stream_handler.py`: Tests for the StreamHandler service
- `test_auth_router.py`: Tests for authentication endpoints
- `test_yolo_model.py`: Tests for the YOLO model
- `test_database.py`: Tests for database connections

## Areas Needing Additional Test Coverage

Based on the coverage report, these areas still need additional tests:

1. **Core**:
   - `dependencies.py` (47% coverage) - Add tests for authentication dependencies
   - `middleware.py` (44% coverage) - Add tests for custom middleware
   - `security.py` (42% coverage) - Add tests for token creation/verification

2. **Routers**:
   - `entities/auth/router.py` (66% coverage) - Add tests for token refresh endpoint
   - `entities/stream_handler/router.py` (47% coverage) - Add tests for stream endpoints
   - `entities/yolo/router.py` (62% coverage) - Add tests for model endpoints

3. **Services**:
   - `entities/stream_handler/services.py` (43% coverage) - Add tests for stream processing
   - `entities/user/services.py` (78% coverage) - Add tests for user retrieval edge cases
   - `utils/dates.py` (60% coverage) - Add tests for date utility functions

## Writing New Tests

When writing new tests:

1. Create a new file in the `tests` directory with the naming pattern `test_*.py`
2. Use pytest fixtures in `conftest.py` for common setup
3. Use the `@pytest.mark.asyncio` decorator for async tests
4. Mock external dependencies to keep tests fast and isolated

## Best Practices

- Mock external dependencies (database, YOLO model, video streams)
- Test both success and failure scenarios
- Keep tests independent of each other
- Use descriptive test names that explain what you're testing
- Each test should test one specific behavior
