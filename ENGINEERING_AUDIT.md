# Engineering Audit Report

CS 5588 -- Data Science Capstone Week 7: Reproducible & Deployable AI
Systems

Project: UMKC PolicyPulse -- Snowflake RAG Smart Campus System

------------------------------------------------------------------------

# 1. Audit Objective

The goal of this engineering audit was to verify whether the capstone
system can be reliably deployed from a clean environment and executed by
another team member without manual debugging.

The audit evaluates:

-   environment reproducibility
-   dependency installation
-   configuration management
-   system startup reliability
-   runtime stability

------------------------------------------------------------------------

# 2. Clean Environment Test

The following steps were executed to simulate a fresh deployment.

1.  Deleted the existing virtual environment
2.  Reinstalled dependencies using the provided startup script
3.  Recreated environment configuration
4.  Executed the full system startup

Commands used:

rm -rf venv\
bash scripts/run.sh

Results:

-   Virtual environment recreated successfully
-   Dependencies installed automatically
-   Smoke tests passed
-   Streamlit application launched successfully

The system was accessible via:

http://localhost:8501

------------------------------------------------------------------------

# 3. Issues Discovered During Audit

During the clean deployment process, several issues were discovered.

## Issue 1: Circular Import in Streamlit Entry File

Problem:

The Streamlit entry file was originally named:

app/app.py

The file imported modules using:

from app import core_services

Because the file name matched the package name (`app`), Python created a
circular import during module initialization.

Error:

ImportError: cannot import name 'core_services' from partially
initialized module 'app'

Fix:

The entry file was renamed to:

app/streamlit_app.py

All startup scripts and documentation were updated accordingly.

------------------------------------------------------------------------

## Issue 2: Dependency Conflict (Groq + httpx)

Problem:

The application crashed when initializing the Groq client.

Error:

TypeError: **init**() got an unexpected keyword argument 'proxies'

Root Cause:

The installed version of httpx was incompatible with the Groq Python
SDK.

Fix:

Dependency versions were pinned in requirements.txt to ensure
compatibility.

------------------------------------------------------------------------

## Issue 3: Environment Configuration Path

Problem:

The `.env` file was initially placed inside the `app/` directory.

However, the startup script expected the configuration file at the
repository root.

Result:

Environment variables were not loaded correctly, causing runtime errors.

Fix:

The `.env` file was moved to the project root directory.

------------------------------------------------------------------------

## Issue 4: Missing Snowflake RSA Key Path

Problem:

The Snowflake authentication configuration used a placeholder value:

/path/to/your/rsa_key.p8

Result:

Database modules generated warnings during initialization.

Fix:

Updated the `.env` configuration to point to the correct local RSA key
path.

------------------------------------------------------------------------

## Issue 5: Invalid Groq API Key

Problem:

The initial API key used in testing was invalid.

Error:

401 - Invalid API Key

Fix:

A new Groq API key was generated and configured in `.env`.

------------------------------------------------------------------------

# 4. Improvements Implemented

Several improvements were implemented to strengthen system reliability.

### Startup Pipeline

The `run.sh` script now performs the following steps automatically:

1.  Verify Python installation
2.  Create a virtual environment
3.  Install dependencies
4.  Validate environment variables
5.  Execute smoke tests
6.  Launch the Streamlit application

This provides a single-command system startup.

------------------------------------------------------------------------

### Configuration Management

Sensitive configuration values are stored in `.env` files and excluded
from the repository using `.gitignore`.

An `.env.example` template is provided to document required environment
variables.

------------------------------------------------------------------------

### Smoke Testing

A basic smoke test suite verifies that:

-   critical modules import correctly
-   environment variables are available
-   core system components initialize successfully

Smoke tests run automatically during system startup.

------------------------------------------------------------------------

# 5. Final Deployment Status

After applying the fixes described above:

-   The system installs correctly from a clean environment
-   All dependencies resolve successfully
-   Smoke tests pass
-   The Streamlit application launches without errors
-   Core agent functionality executes successfully

The system can now be deployed using a single startup command:

bash scripts/run.sh

------------------------------------------------------------------------

# 6. Conclusion

The engineering audit successfully validated that the UMKC PolicyPulse
system is reproducible and deployable.

Key improvements included:

-   resolving circular imports
-   stabilizing dependency versions
-   improving configuration management
-   implementing automated startup validation

These changes significantly improved the reliability and maintainability
of the system and prepare the project for the final capstone
demonstration.
