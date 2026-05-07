# ReVoltz — Backend API

> Giving second-life batteries a verified future.

ReVoltz is a battery lifecycle management platform built for EV workshops across Indonesia. We help workshops scan, grade, and resell used EV battery packs — backed by AI-powered State-of-Health analysis and a peer-to-peer marketplace that connects verified sellers with buyers who need affordable, trusted power.

This repository contains the backend REST API that powers the entire platform.

**Developed by Team SSB** — Built for Hackathon

---

## The Problem We're Solving

Millions of EV battery packs are retired each year — not because they're dead, but because most workshops have no reliable way to assess their remaining value. Without data, batteries get discarded. With ReVoltz, workshops can scan a pack, get an AI-backed health score, and list it for resale within minutes.

---

## What This Backend Does

- Issues JWT tokens for two roles: **workshop operators** and **customers**
- Persists battery pack scan results from a separate AI model service
- Manages per-workshop inventory with full pack and cell-level analysis data
- Runs a marketplace where any active listing is publicly browsable and shareable via QR
- Computes live workshop stats: battery count, average SoH, revenue, and estimated CO₂ saved

---

## Tech Stack

| | |
|---|---|
| Framework | FastAPI 0.111 |
| Database | SQLite via SQLAlchemy 2.0 |
| Auth | JWT — python-jose + passlib/bcrypt |
| Validation | Pydantic v2 |
| HTTP Client | httpx (model service proxy) |
| Server | Uvicorn |

---

## Architecture

```
                    ┌─────────────────────┐
  Frontend ────────▶│  ReVoltz Backend    │◀──── Public / QR Links
  (port 5173)       │  FastAPI · port 8000│
                    └────────┬────────────┘
                             │
                    ┌────────▼────────────┐
                    │  AI Model Service   │
                    │  SoH Prediction     │
                    │  port 8001          │
                    └─────────────────────┘
                             │
                    ┌────────▼────────────┐
                    │  SQLite Database    │
                    │  revoltz.db         │
                    └─────────────────────┘
```

---

## Project Structure

```
revoltz-backend/
├── app.py              # Entry point — all routes, middleware, response serializers
├── auth_utils.py       # JWT signing, password hashing
├── database.py         # SQLAlchemy engine and session
├── models.py           # ORM: User · InventoryBattery · MarketplaceListing
├── routers/
│   └── auth.py         # /auth/register · /auth/login
├── requirements.txt
└── .env
```

---

## Data Models

### User

| Field | Type | Notes |
|---|---|---|
| `id` | Integer | Primary key |
| `email` | String | Unique |
| `role` | String | `customer` or `workshop` |
| `workshop_name` | String | Required for workshop accounts |
| `address` | String | Shown as seller location on marketplace |

### InventoryBattery

| Field | Type | Notes |
|---|---|---|
| `id` | String | e.g. `bat_a3f9c12b` |
| `chemistry` | String | `LFP`, `NMC`, etc. |
| `ocv_v` | Float | Open-circuit voltage |
| `capacity_ah` | Float | Capacity in amp-hours |
| `soh` | Float | State of Health — 0 to 1 |
| `confidence_score` | Float | Model confidence |
| `recommended_action` | String | `reuse`, `recycle`, etc. |
| `pack_analysis_json` | Text | Full AI model output |
| `cell_analysis_json` | Text | Cell-level analysis result |

### MarketplaceListing

| Field | Type | Notes |
|---|---|---|
| `id` | String | e.g. `mkt_d7e4a001` |
| `price` | Integer | In IDR |
| `warranty_months` | Integer | Default: 6 |
| `status` | String | `active` or `sold` |

---

## API Reference

### Authentication

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/auth/register` | No | Register as customer or workshop |
| POST | `/auth/login` | No | Login — returns JWT |

**Register**
```json
{
  "email": "workshop@example.com",
  "full_name": "Budi Santoso",
  "password": "secret",
  "role": "workshop",
  "workshop_name": "Budi EV Workshop",
  "address": "Bandung, Jawa Barat"
}
```

**Login response**
```json
{
  "access_token": "<jwt>",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "email": "workshop@example.com",
    "role": "workshop",
    "workshop_name": "Budi EV Workshop"
  }
}
```

All protected routes require:
```
Authorization: Bearer <access_token>
```

---

### Inventory

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/inventory/pack-scan` | Yes | Save a pack scan + AI result |
| GET | `/inventory` | Yes | List workshop's batteries |
| GET | `/inventory/{id}` | Yes | Get single battery detail |
| POST | `/inventory/{id}/cell-analysis` | Yes | Attach cell-level analysis |

**POST /inventory/pack-scan**
```json
{
  "pack_data": {
    "pack_id": "pack_001",
    "source": "Grab Fleet",
    "chemistry": "LFP",
    "ocv_v": 48.2,
    "capacity_ah": 40,
    "cycle_count": 820,
    "temperature_c": 27.5,
    "age_days": 730,
    "condition": "good"
  },
  "pack_result": {
    "predicted_soh": 0.82,
    "confidence_score": 0.91,
    "recommended_action": "reuse",
    "notes": ["Capacity within range", "Low degradation rate"]
  }
}
```

---

### Marketplace

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/marketplace` | No | Browse all active listings |
| POST | `/inventory/{id}/marketplace-listing` | Yes | Publish or update a listing |
| GET | `/inventory/{id}/marketplace-listing` | Yes | Get listing for a battery |
| GET | `/battery-profiles/{id}` | No | Public shareable battery profile |

**POST /inventory/{id}/marketplace-listing**
```json
{
  "price": 3500000,
  "model_name": "LFP Pack — Grade A",
  "warranty_months": 12
}
```

---

### Workshop Dashboard

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/workshop/stats` | Yes | Total batteries, avg SoH, revenue, CO₂ saved |
| GET | `/workshop/analytics/revenue` | Yes | Revenue time-series |
| GET | `/workshop/analytics/soh-distribution` | Yes | SoH histogram |

---

### System

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/health` | No | Backend status |
| GET | `/model-health` | No | AI model service probe |

---

## Running Locally

### Prerequisites

- Python 3.10+
- AI model service running on port 8001

### Steps

```bash
# 1. Clone and enter directory
git clone <repo-url>
cd revoltz-backend

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env   # then fill in your values

# 5. Start the server
uvicorn app:app --reload --port 8000
```

Interactive API docs will be available at:
```
http://localhost:8000/docs
```

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | — | JWT signing secret. Must be set in production |
| `ALGORITHM` | `HS256` | JWT algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Token lifetime |
| `DATABASE_URL` | `sqlite:///./revoltz.db` | SQLAlchemy connection string |
| `MODEL_API_URL` | `http://localhost:8001` | AI model service base URL |
| `ALLOWED_ORIGINS` | `http://localhost:5173` | Comma-separated CORS origins |

---

## Key Behaviors

- **Database auto-init** — tables are created on first startup, no migrations needed for local dev
- **One listing per battery** — each battery can have at most one marketplace listing; re-publishing updates the existing record
- **Public battery profiles** — `/battery-profiles/{id}` is unauthenticated, designed for QR code sharing so buyers can verify a battery's full history before purchasing
- **Live stats** — workshop stats (SoH, CO₂ saved, revenue) are computed from live inventory data on every request

---

## Team

**Team SSB** — Hackathon IYREF 2026
