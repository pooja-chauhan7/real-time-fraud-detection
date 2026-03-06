@echo off
echo ========================================
echo   Starting Fraud Detection Backend
echo ========================================
echo.
echo Starting API server on http://localhost:5000
echo.

REM Activate virtual environment if exists
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

REM Install dependencies if needed
pip install -r requirements.txt -q

REM Start the backend
python main.py

pause

