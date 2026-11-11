# PrioritySuite Testing Guide

## 1. Testing Philosophy & Standards

- **Target Coverage:** We maintain **85%+ automated test coverage** across all core models, services, views, forms, and security boundaries.
- **Framework:** `pytest`, `pytest-django`, and `coverage.py`.
- **Fast & Isolated:** The test suite runs in an isolated in-memory or temporary database, completely decoupled from external LLM APIs via mocking.

---

## 2. Running Tests

### 2.1 Basic Test Execution
To run the full test suite:

```bash
pytest
```

To run with verbose output:

```bash
pytest -v
```

To run a specific test:

```bash
pytest -k "test_decisions_workflow"
```

### 2.2 Generating Coverage Reports
To measure coverage and view a detailed terminal report:

```bash
coverage run -m pytest
coverage report
```

To generate an interactive HTML coverage report:

```bash
coverage html
# Open htmlcov/index.html in your browser
```

---

## 3. Test Suite Structure (`tests/test_prioritysuite.py`)

The test suite is organized into 5 core domains:

1. **Crypto & Accounts Tests:**
   - Verifies Fernet encryption and decryption round-trips.
   - Tests user registration, password confirmation mismatches, profile updates, and settings changes.
   - Tests complete account and data deletion cascading across frameworks and decisions.

2. **Frameworks & Sample Seeding Tests:**
   - Tests `Framework`, `Domain`, `Why`, `Objective`, and `Goal` models, string representations, and foreign key / M2M relationships.
   - Verifies that `seed_sample_framework()` populates all four levels with `is_sample=True` flags.
   - Verifies that `remove_sample_frameworks()` cleans up all sample items for the user without affecting real priorities.
   - Tests workspace rendering and full CRUD workflows for Domains, Whys, Objectives, and Goals.
   - Tests Periodic Review views, status filtering, and HTMX `mark_reviewed` endpoints.

3. **Cross-Domain Decisions Tests:**
   - Tests creation of a `DecisionRecord` with affected domains, relevant whys, and supporting vs. conflicting objectives.
   - Verifies the 7-step decision form, detail view, editing, and deletion.

4. **Exports & LLM Integration Tests:**
   - Verifies Markdown generation for frameworks and decisions, ensuring facilitator instructions are properly embedded.
   - Tests `.md` file downloads and clipboard preview views.
   - Mocks `litellm.completion` to verify that structured reflection responses parse correctly and log into `LLMReflectionLog`.
   - Tests behavior when LLM is unconfigured, disabled, or when user consent is withheld.

5. **Security & Strict Tenant Isolation Tests:**
   - Verifies that a user attempting to view, edit, or delete another user's framework, domain, or decision receives an HTTP 404 response.

---

## 4. Writing New Tests

When adding new models, views, or endpoints:
- Use the standard `client` fixture with `client.force_login(user)`.
- Always verify tenant isolation: assert that User B cannot access resources created by User A.
- Always mock external network calls using `unittest.mock.patch("litellm.completion")`.
