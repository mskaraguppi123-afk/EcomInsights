# EcomInsights

EcomInsights is a college major project prototype for exploring product prices and, in later stages, estimating price trends from historical observations. This foundation keeps each part understandable and independently explainable:

```text
React + Vite  →  FastAPI  →  PostgreSQL
                         ↘ Python ML module
```

The current version is a starter foundation. It does not connect to online stores or scrape prices. Development uses a small, clearly labeled synthetic dataset.

## Project layout

```text
EcomInsights/
├── backend/                 FastAPI application and database layer
│   ├── app/api/             HTTP routes
│   ├── app/core/            Environment settings
│   ├── app/db/              SQLAlchemy engine and session
│   ├── app/models/          Database models
│   └── app/schemas/         API response schemas
├── frontend/                React + Vite interface
├── ml/                      Synthetic sample data and ML scaffolding
├── .env.example             Local configuration template
└── docker-compose.yml       Optional local PostgreSQL service
```

## Requirements

- Python 3.11 or newer
- Node.js 20 or newer and npm
- SQLite (included out-of-the-box by default) or optional PostgreSQL 16 via Docker Desktop

## Run locally

### 1. Backend (FastAPI + SQLite/PostgreSQL)
In your first terminal:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000
```

> **Interactive API Docs:** <http://127.0.0.1:8000/docs>  
> **Embedded Web Dashboard:** <http://127.0.0.1:8000/>  
> **API Health Check:** <http://127.0.0.1:8000/api/v1/health>

To reload sample products anytime:
```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m app.scripts.seed_sample_data
```

### 2. Frontend (React 18 + Vite)
In your second terminal:

```powershell
cd frontend
$env:PATH = "C:\Program Files\nodejs;" + $env:PATH
npm run dev
```

Open <http://localhost:5173> in your browser.

## Features Implemented

1. **Interactive Price Observation Ingestion (`POST /api/v1/products/{id}/observations`):**
   - Allows users/examiners to record a simulated test price in real time.
2. **Explainable ML Trend Forecaster (`ecominsights_ml`):**
   - Weighted ensemble of Exponential Moving Average (EMA, $\alpha=0.5$ at 60%) and Ordinary Least Squares (OLS) Linear Regression (40%).
   - Range-spread ratio analysis providing `BUY_NOW`, `WAIT`, or `NEUTRAL` recommendations with confidence scoring.
3. **Pure SVG Trajectory & Forecast Visualization:**
   - Visualizes price checkpoints and dotted forecast projections without external heavy charting libraries.
4. **Complete Unit Test Coverage:**
   - 7 automated tests in `backend/tests/test_api.py` validating endpoints and ML integration.

## Viva Defense Guide & Project Documentation

For viva preparation, architecture diagrams, mathematical equations, and the top 15 examiner questions with answers, see:
- [VIVA_DEFENSE_REPORT.md](./VIVA_DEFENSE_REPORT.md)

