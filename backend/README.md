# Project Fusion 2.0 — Backend

AML/KYB Intelligence Graph | Hackfest 2026 | Team: technorev | NMAMIT

---

## Architecture at a Glance

```
Frontend (5173) → FastAPI Orchestrator (8001) → MCP Data Broker (8002)
                                              ↘ NetworkX Math Engine (local)
                                              ↘ Gemini Vision PDF Extractor
```

---

## Quick Start

### 1. Create virtual environment
```bash
cd backend
python -m venv venv

# Activate — Linux/Mac:
source venv/bin/activate

# Activate — Windows:
venv\Scripts\activate
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure environment
```bash
cp .env.example .env
# Open .env and fill in:
#   COMPANIES_HOUSE_API_KEY  → from https://developer.company-information.service.gov.uk/
#   GEMINI_API_KEY           → from https://aistudio.google.com/app/apikey
```

### 4. Load OFAC sanctions database (one-time)
```bash
python load_ofac.py
# Output: ✅ Loaded XXXX SDN entries to data/sanctions.db
```

### 5. Start the MCP data broker (separate terminal)
```bash
python mcp_server.py
# Running on http://localhost:8002
```

### 6. Start the FastAPI backend
```bash
uvicorn main:app --port 8001 --reload
# Docs: http://localhost:8001/docs
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Liveness check |
| `POST` | `/investigate` | Start new investigation (API or document mode) |
| `POST` | `/approve/{thread_id}` | Resume a paused offshore investigation |

### POST /investigate — API mode
```json
{
  "mode": "api",
  "crn": "09446231"
}
```

### POST /investigate — Document mode
```
Content-Type: multipart/form-data
mode=document
file=<pdf_upload>
```

### POST /approve/{thread_id}
```
Content-Type: multipart/form-data
file=<offshore_pdf>
```

---

## Build Phases

| Phase | Files | Status |
|-------|-------|--------|
| 1 | `main.py`, `requirements.txt` | ✅ Done |
| 2 | `mcp_server.py`, `load_ofac.py` | ⬜ Next |
| 3 | `graph_engine.py` | ⬜ Pending |
| 4 | `pdf_extractor.py` | ⬜ Pending |
| 5 | `agent.py` | ⬜ Pending |
| 6 | Routes wired in `main.py` | ⬜ Pending |

---

## Demo Test CRNs

| Company | CRN | Expected Result |
|---------|-----|-----------------|
| Monzo Bank | `09446231` | ✅ AUTO-APPROVE, score < 30 |
| IBS Management | `01683457` | ⏸ PAUSED — offshore dead-end |
| Seabon Limited | `06026625` | 🔴 AUTO-REJECT, CRITICAL score |

---

## Non-Negotiables

- CORS origin: `http://localhost:5173` — never change
- FastAPI port: `8001` — never change
- MCP port: `8002` — never change
- `graph_engine.py` — zero I/O, zero API calls, pure math only
- API keys — live **only** in `.env` (gitignored)
