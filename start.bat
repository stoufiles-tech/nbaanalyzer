@echo off
echo Starting NBA Salary Cap Analyzer...

echo.
echo [1/2] Starting FastAPI backend (port 8000)...
start "NBA Backend" cmd /k "cd /d %~dp0backend && pip install -r requirements.txt -q && python -m uvicorn app.main:app --reload --port 8000"

timeout /t 3 /nobreak > nul

echo [2/2] Starting React frontend (port 5173)...
start "NBA Frontend" cmd /k "cd /d %~dp0frontend && npm install --silent && npm run dev"

echo.
echo Backend: http://localhost:8000
echo Frontend: http://localhost:5173
echo API Docs: http://localhost:8000/docs
echo.
pause
