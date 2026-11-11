# PrioritySuite Developer Guide

## 1. Project Overview & Philosophy

PrioritySuite is built with Python 3.13+ and Django 5.x. It intentionally avoids complex frontend SPA build steps (React/Vue/Node build tooling) by pairing server-rendered Django templates with **HTMX** and **Bootstrap 5.3** customized with an autumnal theme.

### Core Architectural Decisions:
- **Clean Django Modular Architecture:** Apps are organized by functional boundaries: `accounts`, `frameworks`, `decisions`, `exports`, and `llm`.
- **Vendor-Neutral LLM Layer:** Uses `litellm` wrapped in `llm/service.py` to support any model provider with a unified API call shape.
- **Privacy by Design:** Strict tenant isolation where every view, form, and queryset scopes objects to `request.user`. User BYOK API keys are encrypted at rest using Fernet symmetric encryption.
- **Zero-Dependency Local Dev:** Out of the box, `manage.py runserver` uses SQLite with automatic path fallbacks for cross-platform and UNC environments.

---

## 2. Directory Structure

```text
priorityprobe/
├── config/                  # Django project configuration & settings
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── accounts/                # Authentication, UserLLMConfig, crypto, settings
├── frameworks/              # Framework, Domain, Why, Objective, Goal models & workspace
├── decisions/               # DecisionRecord, cross-domain assessment workflows
├── exports/                 # Markdown generator with embedded facilitator prompt
├── llm/                     # LiteLLM client adapter, prompt harness, and chat views
├── docs/                    # Complete user, dev, testing, and deployment documentation
├── templates/               # Django templates (base layout, apps, modals)
├── static/
│   ├── css/autumn-theme.css # Autumn light/dark CSS variables
│   └── js/theme.js          # Theme toggle script
├── tests/                   # Pytest test suite (>85% coverage)
├── Dockerfile               # Production container image
├── docker-compose.yml       # Production stack: Django + MariaDB + Nginx
├── requirements.txt         # Pinned production and test dependencies
└── pyproject.toml           # Pytest & coverage configuration
```

---

## 3. Local Development Setup

### 3.1 Prerequisites
- Python 3.13+ (or 3.11/3.12)
- Git

### 3.2 Setup Steps

```bash
# Clone the repository
git clone https://github.com/your-org/prioritysuite.git
cd prioritysuite

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows PowerShell: .\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Run migrations (defaults to SQLite)
python manage.py migrate

# Create a superuser for Django Admin
python manage.py createsuperuser

# Start the Django development server
python manage.py runserver
```

Open `http://127.0.0.1:8000` in your browser.

---

## 4. Key Subsystems

### 4.1 Encryption (`accounts/crypto.py`)
Fernet symmetric encryption (`cryptography.fernet.Fernet`) is used to encrypt user API keys. If `ENCRYPTION_KEY` is set in the environment, it is used; otherwise, a 32-byte URL-safe base64 key is deterministically derived from `DJANGO_SECRET_KEY` via SHA-256.

### 4.2 Data Models & Ownership
- `Framework`: Owned by `User`.
- `Domain`: Belongs to `Framework`.
- `Why`: Belongs to `Domain`. May have `is_non_negotiable=True`.
- `Objective`: Belongs to a primary `Domain`, links to `whys` (M2M), and links to `related_domains` (M2M).
- `Goal`: Belongs to a primary `Domain`, links to `objectives` (M2M), and links to `related_domains` (M2M).
- `DecisionRecord`: Belongs to `Framework`, links to `affected_domains`, `relevant_whys`, `supporting_objectives`, and `conflicting_objectives`.

### 4.3 LLM Adapter (`llm/service.py`)
The `generate_reflection` function accepts:
- `user_context_markdown`: Pre-rendered Markdown of the user's framework or decision assessment.
- `user_prompt`: The user's specific scenario or question.
- `provider`: `ollama` or `openrouter`.
- `model_name`: e.g. `ollama/llama3.1` or `openrouter/anthropic/claude-3.5-sonnet`.
- `api_key`: Decrypted API key (optional for Ollama).
- `api_base`: Base URL (e.g. `http://localhost:11434`).

Responses are logged in `decisions.models.LLMReflectionLog` and displayed in dedicated thinking partner cards without ever mutating the user's primary framework models.
