@echo off
title EcomInsights Launcher
echo ========================================================
echo  Launching EcomInsights (Backend + Frontend)
echo ========================================================
echo.
echo Starting FastAPI Backend on port 8000...
start "EcomInsights Backend (FastAPI)" cmd /k "cd /d %~dp0backend && call .venv\Scripts\activate.bat && uvicorn app.main:app --reload --port 8000"

echo Starting React + Vite Frontend on port 5173...
start "EcomInsights Frontend (React + Vite)" cmd /k "cd /d %~dp0frontend && npm run dev"

echo.
echo ========================================================
echo  Both services launched in separate windows!
echo.
echo  - React Web Dashboard:      http://localhost:5173
echo  - FastAPI Backend API:       http://127.0.0.1:8000
echo  - Interactive Swagger Docs:  http://127.0.0.1:8000/docs
echo ========================================================
echo.
