# Engineering Maturity Report
UMKC PolicyPulse – CS 5588 Capstone

## 1. Introduction

The goal of this engineering maturity exercise was to transform the UMKC PolicyPulse prototype into a reproducible, deployable, and stable AI system. The project originally began as a functional prototype integrating a Streamlit interface, Snowflake-based retrieval, and a large language model for question answering.

However, the system initially lacked reproducibility guarantees and structured deployment procedures. The purpose of this exercise was to strengthen the engineering quality of the system to meet production-level expectations.

---

## 2. System Architecture

The UMKC PolicyPulse system consists of several major components:

- **User Interface Layer** – A Streamlit-based web interface for interacting with the system.
- **Agent Layer** – A reasoning module that processes user queries and decides which tools to invoke.
- **Core Services Layer** – Modules responsible for configuration management, logging, and shared utilities.
- **Data Retrieval Layer** – Integration with Snowflake for document retrieval and feature storage.
- **Evaluation Layer** – Logging and evaluation modules that record system outputs and performance metrics.
- **Data Ingestion Pipeline** – Automated pipeline that processes new datasets and loads them into the Snowflake database.

This modular architecture separates concerns and improves maintainability.

---

## 3. Reproducibility Improvements

Several engineering improvements were implemented to ensure reproducibility:

### Configuration Management

All system parameters were moved into configuration files and environment variables. This eliminated hardcoded credentials and paths from the source code.

A `.env.example` template file was created to document all required environment variables.

### Environment Reproducibility

A pinned `requirements.txt` file was added to ensure consistent dependency versions across systems. The startup script automatically installs these dependencies during system initialization.

### Automated Startup Pipeline

A startup script (`scripts/run.sh`) was implemented to automate the full system startup process, including:

- Python environment verification
- Virtual environment creation
- Dependency installation
- Environment validation
- Smoke test execution
- Launching the Streamlit application

This allows the entire system to be started with a single command.

---

## 4. Logging and Monitoring

Structured logging was introduced using Python’s logging module. Each major system component writes logs that record runtime activity, errors, and system state.

This improves system observability and simplifies debugging.

---

## 5. Engineering Audit Results

During the engineering audit, the system was tested by recreating the environment from scratch. The audit process included deleting the virtual environment and reinstalling all dependencies.

The following issues were discovered:

- Missing environment variable documentation
- Circular imports in certain modules
- Missing RSA key configuration
- Dependency version inconsistencies

All issues were subsequently fixed through improved configuration management, refactoring of module imports, and additional documentation.

---

## 6. System Stability Improvements

The engineering improvements significantly increased system stability. The addition of smoke tests ensures that critical components are verified before launching the system.

The system can now be deployed on a clean machine with minimal setup effort.

---

## 7. Conclusion

This engineering maturity exercise transformed the UMKC PolicyPulse project from a prototype into a reproducible AI application. By implementing structured configuration, automated startup pipelines, and clear documentation, the system now meets key requirements for deployment-ready software.

These improvements demonstrate the importance of strong engineering practices when building production-level AI systems.
