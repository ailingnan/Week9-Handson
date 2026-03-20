#!/bin/bash
set -e

echo "========================================="
echo " Starting Data Ingestion Scheduler"
echo "========================================="

if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Please run scripts/run.sh first to set up the environment."
    exit 1
fi

echo "Activating virtual environment..."
source venv/bin/activate

# 4. Check Environment Variables
if [ ! -f ".env" ]; then
    echo "Error: .env file not found. Please run scripts/run.sh first or create it."
    exit 1
fi

# Set PYTHONPATH to root directory so `core.` modules load correctly
export PYTHONPATH=$(pwd)

echo "Starting Scheduler..."
python core/ingestion/scheduler.py
