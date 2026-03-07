@echo off
echo ========================================
echo Real-Time Fraud Detection System
echo ========================================
echo.

echo Installing dependencies...
pip install -r requirements.txt

echo.
echo Starting Flask API...
echo The API will run on http://localhost:5000
echo.

cd /d "%~dp0"
python app.py
