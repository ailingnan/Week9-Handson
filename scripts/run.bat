@echo off
setlocal
echo =========================================
echo  Starting UMKC Capstone App (Windows)
echo =========================================

:: 1. Check Python version
python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Python not found. Please install Python 3.9+.
    exit /b 1
)

:: 2. Setup Virtual Environment
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

echo Activating virtual environment...
call venv\Scripts\activate.bat

:: 3. Install Requirements
echo Installing dependencies...
python -m pip install --upgrade pip -q
pip install -r requirements.txt -q

:: 4. Check Environment Variables
if not exist ".env" (
    echo Warning: .env file not found. Copying from .env.example...
    if exist ".env.example" (
        copy .env.example .env
        echo Please fill in the .env file with your credentials, then re-run this script.
        exit /b 1
    ) else (
        echo Error: .env.example missing. Cannot auto-setup .env.
        exit /b 1
    )
)

:: Validate environment variables (rudimentary check in batch)
findstr /C:"SNOWFLAKE_PRIVATE_KEY_PATH" .env >nul
if %ERRORLEVEL% neq 0 (
    echo Error: Missing SNOWFLAKE_PRIVATE_KEY_PATH in .env
    exit /b 1
)

:: 5. Run Smoke Tests
echo Running system smoke tests...
set PYTHONPATH=%cd%
python -m unittest tests/smoke_test.py
if %ERRORLEVEL% neq 0 (
    echo Error: Smoke tests failed. Please check the configuration or logs and try again.
    exit /b 1
)

:: 6. Run Streamlit App
echo Starting Streamlit App...
streamlit run app/streamlit_app.py
