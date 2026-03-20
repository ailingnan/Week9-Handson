# System Architecture Reference

## High-Level Pipeline
The capstone project is an intelligent retrieval-augmented generation (RAG) system with a multi-step agent workflow.
1. **Frontend:** User interacts with standard multi-tab UI built using Streamlit (`app/streamlit_app.py`).
2. **AI Engine:** A Groq LLM-powered Agent (`agent/agent_runner.py`) handles user input, parses intents, and chooses tools.
3. **Tools & Retrieval:** Agent triggers specific Snowflake SQL retrievals via `app/core_services.py` and `agent/tools.py`.
4. **Data Modeling & Storage:** User queries flow into `FEATURE_STORE` while the Agent interactions log usage tracking metrics directly against `EVAL_METRICS` via `core/modeling/evaluator.py`.

## Code Organization (Refactored)
We transitioned from a flattened MVP script into a structured Python engineering workspace:

- `app/`: Streamlit UI entry points.
- `core/`: Agnostic business logic (no UI dependencies).
    - `features/`: Feature store operations.
    - `modeling/`: Evaluation metric logging logic.
    - `ingestion/`: Standalone CSV data ingestion scheduler.
    - `config.py`: Loads the standardized parameters.
    - `logger.py`: Instantiates structured application logs.
- `agent/`: Tool schemas, tools logic mappings, and the primary Langchain-eque loop execution.
- `config/`: Centralized `.yaml` values for fast runtime iteration.
- `scripts/`: Production startup bash routines wrapper.
- `logs/` & `artifacts/`: System output persistence layer.

## Snowflake Tables DDL Strategy
Each core module (`feature_store.py`, `evaluator.py`, `scheduler.py`) retains control over its primary table schema creation:
1. `DOC_CHUNKS_FEATURED`: Retains standard RAG chunk knowledge.
2. `FEATURE_STORE`: Retains query/keyword behavior arrays for AI version drifts.
3. `EVAL_METRICS`: Retains specific request latencies and response outcomes.
4. `INGEST_LOG`: Ensures no duplicate CSV paths get re-uploaded accidentally into Snowflake.
