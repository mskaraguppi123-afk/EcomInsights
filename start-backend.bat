@echo off
title EcomInsights Backend (FastAPI)
echo ========================================================
echo  Starting EcomInsights Backend on http://127.0.0.1:8000
echo ========================================================
cd backend
call .venv\Scripts\activate.bat
uvicorn app.main:app --reload --port 8000
pause
