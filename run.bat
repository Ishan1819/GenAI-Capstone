@echo off
REM Starts the FastAPI backend (port 8000) and the Vite frontend (port 5173) in separate windows.
set ROOT=%~dp0

start "Backend" cmd /k "cd /d %ROOT%backend && uvicorn app.main:app --reload"
start "Frontend" cmd /k "cd /d %ROOT%frontend && npm run dev"

echo Backend:  http://localhost:8000/docs
echo Frontend: http://localhost:5173
