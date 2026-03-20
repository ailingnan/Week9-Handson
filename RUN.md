# Running the Application

The system exposes two primary execution paths: The frontend Streamlit UI, and the background Data Ingestion Scheduler.

## Option 1: Running the UI Agent (Streamlit)
To start the user interface and interact with the AI assistant:

**Mac/Linux:**
```bash
bash scripts/run.sh
```

**Windows:**
```cmd
scripts\run.bat
```

This script will:
1. Ensure your Python virtual environment exists.
2. Ensure dependencies are installed via `requirements.txt`.
3. Check for the `.env` configuration file and validate required configuration values (`SNOWFLAKE_PRIVATE_KEY_PATH` & `GROQ_API_KEY`).
4. Execute `tests/smoke_test.py` to assert configurations are sound.
5. Launch the Streamlit application on `http://localhost:8501`.

## Option 2: Running the Automated Ingestion Pipeline
To process new CSV documents located in `ingest_inbox/` into Snowflake chunks:
```bash
bash scripts/run_ingestion.sh
```
This runs `core/ingestion/scheduler.py` in a headless polling state.
- It scans the inbox folder every 60 seconds (configurable via `config/config.yaml`).
- Processes and uploads hashed deduplicated CSV rows into Snowflake `DOC_CHUNKS_FEATURED`.
- Writes logs to `logs/system.log` and the Snowflake `INGEST_LOG` table.
- Moves processed files to `ingest_done/`.

## Running the Tests
To quickly sanity check the configuration setup:
```bash
python3 -m unittest tests/smoke_test.py
```
