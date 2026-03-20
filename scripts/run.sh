#!/bin/bash
set -e

echo "========================================="
echo " Starting UMKC Capstone App"
echo "========================================="

# 1. Check Python version (3.9+ recommended)
if ! command -v python3 &> /dev/null; then
    echo "Python3 not found. Please install Python 3.9+."
    exit 1
fi

# 2. Setup Virtual Environment
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

echo "Activating virtual environment..."
source venv/bin/activate

# 3. Install Requirements
echo "Installing dependencies..."
pip install --upgrade pip -q
pip install -r requirements.txt -q

# 4. Check Environment Variables
if [ ! -f ".env" ]; then
    echo "Warning: .env file not found. Copying from .env.example..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "Please fill in the .env file with your credentials, then re-run this script."
        exit 1
    else
        echo "Error: .env.example missing. Cannot auto-setup .env."
        exit 1
    fi
fi

echo "Validating environment variables..."
source .env
if [ -z "$SNOWFLAKE_PRIVATE_KEY_PATH" ] || [ -z "$GROQ_API_KEY" ]; then
    echo "Error: Missing required environment variables in .env (SNOWFLAKE_PRIVATE_KEY_PATH or GROQ_API_KEY)"
    exit 1
fi

# 5. Run Smoke Tests
echo "Running system smoke tests..."
export PYTHONPATH=$(pwd)
if ! python3 -m unittest tests/smoke_test.py; then
    echo "Error: Smoke tests failed. Please check the configuration or logs and try again."
    exit 1
fi

# 6. Run Streamlit App
echo "Starting Streamlit App..."
export PYTHONPATH=$(pwd)
streamlit run app/streamlit_app.py
