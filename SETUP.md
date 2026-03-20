# System Setup Guide

To ensure a reproducible environment, the system requires the following pre-requisite steps.

## 1. Prerequisites
- **Python:** 3.9, 3.10, or 3.11.
- **Git** installed on your terminal.

## 2. Environment Variables (.env)
The application expects certain API keys and connection parameters.
1. Copy the provided template: `cp .env.example .env`
2. Open `.env` and fill out your keys:
    - **`GROQ_API_KEY`**: Get this from your Groq dashboard.
    - **Snowflake Credentials**: Fill out your Snowflake account URL, username, database, schema, role, and warehouse.

## 3. Snowflake RSA Keypair
The application requires an RSA Private Key for Snowflake authentication.
1. Save your `rsa_key.p8` file in a secure location on your machine.
2. In your `.env` file, specify the exact absolute or relative path to this key under `SNOWFLAKE_PRIVATE_KEY_PATH`.
3. **DO NOT** commit this file to GitHub. The project `.gitignore` is configured to prevent accidental staging.

## 4. Install Dependencies
Dependencies are strictly pinned in `requirements.txt` to guarantee a reproducible build.
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Alternatively, you can just use `bash scripts/run.sh` to automatically install the environment the first time you run it.

## 5. Verify the Installation
Run the included smoke test to verify your configuration structure and imports load correctly.
```bash
python3 -m unittest tests/smoke_test.py
```
If this passes, you are ready to configure the database components and run the application.
