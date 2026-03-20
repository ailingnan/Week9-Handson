# UMKC Smart Campus AI Pipeline

A production-ready data science capstone project that incorporates data ingestion, feature generation, retrieval augmentation, and AI evaluation metrics.

## Overview
This repository contains a Streamlit-based AI assistant for UMKC, powered by Snowflake and Groq LLMs. It has been hardened for production environments, featuring configuration management, automated data ingress, and structured logging.

## Core Modules
- **`app/`**: Contains the Streamlit frontend.
- **`core/`**: Centralized non-UI business logic:
    - **`features/`**: Feature store and versioning logic.
    - **`modeling/`**: AI evaluation and metric logging.
    - **`ingestion/`**: Automated CSV-to-Snowflake ingress pipeline.
    - **`config.py`**: Central YAML parameter loader.
    - **`logger.py`**: Structured Python logging utility.
- **`agent/`**: The system runner and tool definitions for the Groq LLM logic processing.

## Quick Start
1. Ensure Python 3.9+ is installed.
2. Review the detailed directions in [SETUP.md](SETUP.md).
3. Review execution commands in [RUN.md](RUN.md).

Run the application:
```bash
# Mac / Linux
bash scripts/run.sh

# Windows
scripts\run.bat
```

## Team Contributions

| Team Member | Role | Key Contributions |
|-------------|------|------------------|
| Ailing Nan | Project Lead & AI Systems Architect | Designed overall system architecture, implemented reproducible deployment pipeline, built agent orchestration system, integrated Snowflake RAG pipeline, implemented configuration management, logging, and startup automation scripts, conducted engineering audit and system debugging |
| Gia Huynh | Data & Testing Support | Assisted with dataset preparation, performed testing on system modules, and helped verify system functionality during development |
| Lyza Iamrache | Reproducibility & Deployment Support | Assisted with environment setup, system startup validation, and contributed to documentation and reproducibility testing. |
