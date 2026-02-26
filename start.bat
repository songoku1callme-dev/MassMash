@echo off
REM MassMash AI Desktop Client - Start Script (Windows)
REM Starts both backend and frontend.

echo =========================================
echo   MassMash AI Desktop Client
echo =========================================
echo.

echo [1/2] Starting backend (FastAPI)...
cd backend
start "MassMash Backend" cmd /c "poetry run fastapi dev app/main.py --port 8000"
cd ..

echo Waiting for backend to start...
timeout /t 5 /nobreak > nul

echo [2/2] Starting frontend (Vite)...
cd frontend
start "MassMash Frontend" cmd /c "npm run dev"
cd ..

echo.
echo =========================================
echo   App is running!
echo   Frontend: http://localhost:5173
echo   Backend:  http://localhost:8000
echo   API Docs: http://localhost:8000/docs
echo =========================================
echo.
echo Close this window or press Ctrl+C to stop.
pause
