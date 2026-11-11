# PrioritySuite

**PrioritySuite** is an open-source, private, user-led application designed to help people:
- Articulate what matters to them and why.
- Organize their personal framework across domains of life (**Domains → Whys → Objectives → Goals**).
- Examine real opportunities, commitments, and decisions in the context of their wider priorities.
- Use an LLM as an optional thinking partner and sounding board to explore tensions and trade-offs.

---

## Key Features

- **Conceptual Model:** Structured around **Domains → Whys → Objectives → Goals** with optional qualitative **Non-Negotiable** markers.
- **Cross-Domain Decision Assessments:** 7-step guided assessment to explore the ripple effects and tensions of a proposed decision across multiple life areas.
- **Sample Framework & Onboarding:** One-click option on first use to explore with diverse sample domains and items, easily removable at any time.
- **Periodic Review:** Filter Whys, Objectives, and Goals by status (`Active`, `Paused`, `Completed`) and record review dates.
- **Vendor-Neutral LLM Partner (BYOK):** Seamless support for **Ollama** (local/offline) and **OpenRouter** (cloud access to Anthropic, OpenAI, Gemini, etc.) using `litellm`.
- **Markdown Export:** Export your complete framework or any decision assessment as a clean `.md` document with embedded LLM facilitator instructions.
- **Autumnal Light & Dark Mode:** Built with Bootstrap 5.3 and custom autumnal palette (warm parchment, terracotta, amber, sage, and deep woodland charcoal).
- **Comprehensive Documentation:** Full User, Developer, Testing, and Deployment guides in `docs/`.

---

## Quick Start (Development with SQLite)

```bash
# Clone the repository
git clone https://github.com/your-org/prioritysuite.git
cd prioritysuite

# Set up virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Start the dev server
python manage.py runserver
```

Visit [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser.

---

## Production Deployment (Docker Compose)

```bash
docker compose up -d --build
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
```

---

## Documentation

- [User Guide](docs/user-guide.md)
- [Developer Guide](docs/developer-guide.md)
- [Testing Guide](docs/testing-guide.md)
- [Deployment Guide](docs/deployment-guide.md)
- [Original Product Specification](Specification.md)

---

## Testing & Quality

Run the test suite with coverage:

```bash
coverage run -m pytest
coverage report
```

Current test suite coverage: **87%** across all modules.

---

## License

This project is licensed under the terms of the [LICENSE](LICENSE) file.
