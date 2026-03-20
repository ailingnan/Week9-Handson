"""
feature_store.py
----------------
Feature Store + Feature Version Management
- Writes keyword features extracted from each query into the Snowflake FEATURE_STORE table.
- Supports versioning to enable comparison of feature distributions across different versions.
"""

import os, time
from datetime import datetime
import pandas as pd
from dotenv import load_dotenv
import snowflake.connector
import logging
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

import sys
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.config import SETTINGS
from core.logger import get_logger

logger = get_logger("feature_store")

load_dotenv()

TABLE_NAME = SETTINGS.get("snowflake", {}).get("feature_store_table", "FEATURE_STORE")

# SQL for creating the Feature Store table
DDL = f"""
CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
    FEATURE_ID      VARCHAR(64)   NOT NULL,
    RUN_ID          VARCHAR(64),
    VERSION         VARCHAR(16)   DEFAULT 'v1',
    QUERY_RAW       VARCHAR(2000),
    KEYWORDS        VARCHAR(1000),
    NUM_KEYWORDS    INTEGER,
    TOPK            INTEGER,
    CREATED_AT      TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (FEATURE_ID)
);
"""

def sf_connect():
    """Establishes a connection to Snowflake using RSA key authentication."""
    key_path = os.getenv("SNOWFLAKE_PRIVATE_KEY_PATH")
    if not key_path:
        logger.error("Missing environment variable: SNOWFLAKE_PRIVATE_KEY_PATH")
        raise ValueError("Missing environment variable: SNOWFLAKE_PRIVATE_KEY_PATH")
    if not os.path.exists(key_path):
        logger.error(f"Missing RSA key file at configured path: {key_path}")
        raise FileNotFoundError(f"Missing RSA key file at configured path: {key_path}")
        
    with open(key_path, "rb") as f:
        pk = serialization.load_pem_private_key(f.read(), password=None, backend=default_backend())
    pkb = pk.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    return snowflake.connector.connect(
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        user=os.getenv("SNOWFLAKE_USER"),
        private_key=pkb,
        role=os.getenv("SNOWFLAKE_ROLE"),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
        database=os.getenv("SNOWFLAKE_DATABASE"),
        schema=os.getenv("SNOWFLAKE_SCHEMA"),
    )

def ensure_table():
    """Ensure the FEATURE_STORE table exists in Snowflake."""
    conn = sf_connect()
    try:
        conn.cursor().execute(DDL)
        conn.commit()
    except Exception as e:
        logger.error(f"Failed to ensure table {TABLE_NAME}: {e}")
    finally:
        conn.close()

def save_features(run_id: str, query: str, keywords: list, topk: int, version: str = "v1"):
    """Writes the features of the current query to the Feature Store table."""
    ensure_table()
    feature_id = f"{run_id}-{int(time.time())}"
    sql = f"""
    INSERT INTO {TABLE_NAME}
      (FEATURE_ID, RUN_ID, VERSION, QUERY_RAW, KEYWORDS, NUM_KEYWORDS, TOPK)
    VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    conn = sf_connect()
    try:
        conn.cursor().execute(sql, (
            feature_id, run_id, version, query,
            ",".join(keywords), len(keywords), topk
        ))
        conn.commit()
    except Exception as e:
        logger.error(f"Failed to save features: {e}")
    finally:
        conn.close()

def load_feature_versions() -> pd.DataFrame:
    """Retrieves feature statistics for all versions for version comparison."""
    ensure_table()
    sql = f"""
    SELECT
        VERSION,
        COUNT(*)            AS TOTAL_QUERIES,
        AVG(NUM_KEYWORDS)   AS AVG_KEYWORDS,
        AVG(TOPK)           AS AVG_TOPK,
        MIN(CREATED_AT)     AS FIRST_SEEN,
        MAX(CREATED_AT)     AS LAST_SEEN
    FROM {TABLE_NAME}
    GROUP BY VERSION
    ORDER BY VERSION
    """
    conn = sf_connect()
    try:
        cur = conn.cursor()
        cur.execute(sql)
        rows = cur.fetchall()
        cols = [c[0] for c in cur.description]
        return pd.DataFrame(rows, columns=cols)
    except Exception as e:
        logger.error(f"Failed to load feature versions: {e}")
        return pd.DataFrame()
    finally:
        conn.close()

def load_feature_history(limit: int = 100) -> pd.DataFrame:
    """Retrieves the most recent feature records."""
    ensure_table()
    sql = f"""
    SELECT FEATURE_ID, RUN_ID, VERSION, QUERY_RAW, KEYWORDS, NUM_KEYWORDS, TOPK, CREATED_AT
    FROM {TABLE_NAME}
    ORDER BY CREATED_AT DESC
    LIMIT {limit}
    """
    conn = sf_connect()
    try:
        cur = conn.cursor()
        cur.execute(sql)
        rows = cur.fetchall()
        cols = [c[0] for c in cur.description]
        return pd.DataFrame(rows, columns=cols)
    except Exception as e:
        logger.error(f"Failed to load feature history: {e}")
        return pd.DataFrame()
    finally:
        conn.close()
