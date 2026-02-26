#!/bin/bash
# MassMash AI Desktop Client - Start Script (Linux/macOS)
# Starts both backend and frontend in parallel.

set -e

echo "========================================="
echo "  MassMash AI Desktop Client"
echo "========================================="
echo ""

# Start backend
echo "[1/2] Starting backend (FastAPI)..."
cd backend
poetry install --no-interaction 2>/dev/null
poetry run fastapi dev app/main.py --port 8000 &
BACKEND_PID=$!
cd ..

# Wait for backend to be ready
echo "Waiting for backend to start..."
for i in $(seq 1 30); do
    if curl -s http://localhost:8000/healthz > /dev/null 2>&1; then
        echo "Backend is ready!"
        break
    fi
    sleep 1
done

# Start frontend
echo "[2/2] Starting frontend (Vite)..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "========================================="
echo "  App is running!"
echo "  Frontend: http://localhost:5173"
echo "  Backend:  http://localhost:8000"
echo "  API Docs: http://localhost:8000/docs"
echo "========================================="
echo ""
echo "Press Ctrl+C to stop all services."

# Trap to kill both processes
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" SIGINT SIGTERM

wait
