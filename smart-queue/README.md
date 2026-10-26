# AI-Powered Universal Smart Queue, Appointment & Waiting Management Platform

This is the STEP 1 — PROJECT FOUNDATION implementation.

## Project Purpose
A scalable full-stack platform to handle smart queues, appointment booking, and waiting management with AI prediction capabilities. 

## Technology Stack
- **Frontend**: React, Vite, Tailwind CSS, React Router, Axios
- **Backend**: FastAPI, Python, SQLAlchemy, Uvicorn
- **Database**: PostgreSQL (Supabase)

## Folder Structure
- `frontend/` - React frontend application.
- `backend/` - FastAPI backend application.
- `database/` - Database documentation and schemas (to be added in later steps).

## Current Implementation Status
- **STEP 1 — PROJECT FOUNDATION**: Full-stack repository setup & connection checks.
- **STEP 2 — DATABASE ARCHITECTURE**: Supabase PostgreSQL schemas, relationships, constraints, and sector seeds.
- **STEP 3 — AUTHENTICATION & ACCESS CONTROL**: Role-based access (USER, ADMIN, STAFF), Supabase Auth & JWT.
- **STEP 4 — SECTOR EXPLORATION**: Dynamic multi-sector discovery (Hospital, Bank, Restaurant, Gov, Retail, Supermarket).
- **STEP 5 — APPOINTMENTS ENGINE**: Real-time slot generation, conflict prevention, and booking workflow.
- **STEP 6 — TOKEN ISSUANCE & QR VERIFICATION**: Concurrent-safe sequential token numbers and secure QR tokens.
- **STEP 7 — ADMIN & STAFF MANAGEMENT**: Role-separated portals, branch dashboards, counters, and appointments management.
- **STEP 8 — REAL QUEUE OPERATION ENGINE**: Atomic state transitions (`CALLED`, `SERVING`, `COMPLETED`, `SKIPPED`, `NO_SHOW`), counter double-call lockouts, and deterministic ordering.
- **STEP 9 — REAL-TIME NOTIFICATIONS & AI WAIT PREDICTION**:
  - **AI Dynamic Wait Prediction Engine**: Historical handling velocity, parallel open counter capacity, peak traffic adjustments, and confidence scoring.
  - **Automated Queue Notifications**: Real-time alerts for token issuance, turn proximity, staff calling, service start, and completion.
  - **Live Pub-Sub & Server-Sent Events (SSE)**: Instant real-time updates for citizen passes, staff dashboards, and branch displays.
  - **Frontend Experience**: Dedicated Notifications Center, live bell badges, audio arrival chimes, and AI wait-time analytics card.

## Local Setup Instructions

### Environment Variables
1. Copy `.env.example` to `.env` in the root (if needed) and in both `frontend` and `backend` directories.
2. Fill in the required environment variables (e.g., Supabase keys) inside `backend/.env` and `frontend/.env`.

### Backend Setup
```bash
cd backend
python -m venv .venv
# Activate the virtual environment
# Windows: .venv\Scripts\activate
# Mac/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

### Backend Run Command
```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Setup
```bash
cd frontend
npm install
```

### Frontend Run Command
```bash
cd frontend
npm run dev
```
