# Footprint Pulse 🌍

## 🚀 Live Demo
**https://footprint-pulse-864461954747.asia-south1.run.app**


A carbon-awareness dashboard that lets users log daily transport, food, and energy actions, see their real-world CO₂ impact as relatable nudges, and receive AI-powered weekly reduction advice.

---

## Chosen Approach

Rule-based carbon calculation with a Google Gemini AI overlay for weekly insights. Gemini generates personalized 2–3 sentence recommendations; if the API is unavailable a deterministic rule-based engine produces equivalent advice. Every Google Cloud integration (Firestore, Cloud Logging, Secret Manager, Translation) wraps its initialization in try/except and falls back transparently so the app always works.

---

## Architecture

```
Browser (HTML/CSS/JS)
    │
    ▼
Flask App (wsgi.py → app/__init__.py)
    ├── POST /api/actions        → CarbonCalculator → NudgeEngine → FirestoreRepository
    ├── GET  /api/actions        → FirestoreRepository (in-memory fallback)
    ├── GET  /api/insights       → GeminiService (rule-based fallback)
    ├── POST /api/translate      → Cloud Translation API (503 fallback)
    └── GET  /health             → reports all 5 service statuses
    
Google Cloud Services (all optional — fallback active if unavailable):
    ├── Gemini AI                → weekly insight generation
    ├── Firestore                → action persistence (in-memory fallback)
    ├── Cloud Logging            → structured event logging (stdlib fallback)
    ├── Secret Manager           → GEMINI_API_KEY retrieval (os.environ fallback)
    └── Cloud Translation API    → insight translation (hidden button fallback)
```

---

## How It Works

1. User taps an action button (e.g. "Car Ride 15 km").
2. POST /api/actions validates the payload, calculates CO₂ using emission factors, generates a relatable nudge (e.g. "= 20 smartphone charges"), and persists via FirestoreRepository.
3. The Earth canvas updates colour based on cumulative CO₂.
4. GET /api/insights queries Gemini (5-second timeout) or rule-based fallback for a weekly reduction recommendation.
5. The optional "Translate" button calls POST /api/translate; if Cloud Translation is unavailable the button stays hidden.

---

## Assumptions

- Emission factors are illustrative averages from EPA/IPCC datasets.
- One "flight hour" ≈ 90 kg CO₂ (short-haul average).
- The app is single-user / demo scope; Firestore stores all actions in a flat `actions` collection.
- `GOOGLE_CLOUD_PROJECT` / `GCLOUD_PROJECT` env var is required for any Google Cloud service to activate.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11, Flask 3.0 |
| AI | Google Gemini 1.5 Flash |
| Persistence | Google Cloud Firestore (in-memory fallback) |
| Logging | Google Cloud Logging (stdlib fallback) |
| Secrets | Google Secret Manager (os.environ fallback) |
| Translation | Google Cloud Translation v2 (hidden-button fallback) |
| Frontend | Vanilla JS, Canvas API, Lucide Icons |
| Deployment | Gunicorn, Docker, Cloud Run |

---

## Google Services

| Service | Status | Fallback |
|---|---|---|
| Gemini AI (`google-generativeai`) | Primary insight engine | Rule-based text generator |
| Cloud Firestore (`google-cloud-firestore`) | Action persistence | In-memory ActionRepository |
| Cloud Logging (`google-cloud-logging`) | Structured event logs | Python `logging` module |
| Secret Manager (`google-cloud-secret-manager`) | API key retrieval | `os.environ` |
| Cloud Translation (`google-cloud-translate`) | Insight translation | Button hidden / 503 |

---

## How to Run Locally

```bash
# 1. Clone and create virtual environment
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env — set GEMINI_API_KEY and optionally GOOGLE_CLOUD_PROJECT

# 4. Run
flask --app wsgi:app run --debug
# → http://localhost:5000
```

Google Cloud services activate automatically when `GOOGLE_CLOUD_PROJECT` is set and ADC credentials are present (`gcloud auth application-default login`). All services fall back gracefully if absent.

---

## How to Run Tests

```bash
pytest --cov=app tests/ -v
```

To view an HTML coverage report:
```bash
pytest --cov=app --cov-report=html tests/
open htmlcov/index.html
```

---

## Deployment Notes

### Docker

```bash
docker build -t footprint-pulse .
docker run -p 8080:8080 \
  -e GEMINI_API_KEY=<your_key> \
  -e GOOGLE_CLOUD_PROJECT=<your_project> \
  footprint-pulse
```

### Google Cloud Run

```bash
gcloud run deploy footprint-pulse \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GEMINI_API_KEY=<key>,GOOGLE_CLOUD_PROJECT=<project>
```

For production, store `GEMINI_API_KEY` in Secret Manager and remove it from env vars — the `secret_manager.get_secret()` utility will fetch it automatically.

---

## Test Coverage Summary

| Module | Coverage |
|---|---|
| `app/models/action.py` | ≥ 95% |
| `app/services/nudge_engine.py` | ≥ 95% |
| `app/services/carbon_calculator.py` | ≥ 95% |
| `app/services/gemini_service.py` | ≥ 90% |
| `app/services/firestore_repository.py` | ≥ 90% |
| `app/services/cloud_logging.py` | ≥ 90% |
| `app/utils/secret_manager.py` | ≥ 90% |
| `app/routes/translate.py` | ≥ 90% |
| `app/routes/actions.py` | ≥ 95% |
| `app/routes/health.py` | ≥ 95% |
| Overall | ≥ 88% |

Run `pytest --cov=app tests/` for the live figure.
