"""
core_services.py
----------------
Non-UI business logic extracted from `streamlit_app.py`.
This allows the Agent to use tools (like retrieval and LLM) without triggering Streamlit caching or UI logic side effects.
"""

import os, re, time
import pandas as pd
import snowflake.connector
import logging
from dotenv import load_dotenv
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from groq import Groq

# Add project root to python path to import core correctly
import sys
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.config import SETTINGS
from core.logger import get_logger

logger = get_logger("core_services")

load_dotenv()

STOPWORDS = {
    "a","an","the","and","or","but","if","then","else","so",
    "is","are","was","were","be","been","being",
    "do","does","did","to","of","in","on","for","with","at","by","from","as",
    "how","much","many","what","when","where","who","whom","why",
    "i","me","my","you","your","we","our","they","their",
    "can","could","should","would","may","might","will","shall"
}

# ── Feature Engineering ─────────────────────────────────────────
def extract_keywords(query: str, max_terms: int = 6):
    tokens = re.findall(r"[a-zA-Z0-9]+", (query or "").lower())
    terms  = [t for t in tokens if t not in STOPWORDS and len(t) >= 3]
    seen, uniq = set(), []
    for t in terms:
        if t not in seen:
            uniq.append(t); seen.add(t)
    return uniq[:max_terms]

# ── Groq LLM Generation ─────────────────────────────────────────
def get_groq_client():
    key = os.getenv("GROQ_API_KEY")
    if not key:
        logger.warning("GROQ_API_KEY is not set in your .env file. AI answers are disabled.")
        return None
    return Groq(api_key=key)

def generate_answer(question: str, chunks_df: pd.DataFrame, model: str = "llama-3.1-8b-instant") -> tuple[str, int]:
    """Concatenates retrieved Chunks into Context and calls Groq to generate a natural language response"""
    if chunks_df is None or chunks_df.empty:
        return "⚠️ No relevant documents found. Unable to generate an answer.", 0

    # Take top 5 chunks to build context (preventing token limit overflow)
    context_parts = []
    for i, row in chunks_df.head(5).iterrows():
        context_parts.append(
            f"[Source: {row.get('DOC_NAME', 'Unknown')} Page {row.get('PAGE_NUM', '?')}]\n{row.get('CHUNK_TEXT', '')}"
        )
    context = "\n\n---\n\n".join(context_parts)

    prompt = f"""You are a helpful assistant for UMKC (University of Missouri-Kansas City) students and staff.
Answer the question based ONLY on the provided context from official UMKC documents.
If the context doesn't contain enough information, say so clearly.
Answer in the same language as the question.

Context:
{context}

Question: {question}

Answer:"""

    client = get_groq_client()
    if not client:
        return "⚠️ Groq API client not initialized.", 0
        
    t0 = time.time()
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=512,
            temperature=0.2,
        )
        ms = int((time.time() - t0) * 1000)
        answer = response.choices[0].message.content.strip()
        return answer, ms
    except Exception as e:
        logger.error(f"Error during Groq generation: {e}")
        return f"⚠️ Error generating answer: {e}", int((time.time() - t0) * 1000)

# ── Snowflake Connection ────────────────────────────────────────
def get_sf_engine():
    key_path = os.getenv("SNOWFLAKE_PRIVATE_KEY_PATH")
    if not key_path:
        logger.error("Missing environment variable: SNOWFLAKE_PRIVATE_KEY_PATH")
        raise ValueError("Missing environment variable: SNOWFLAKE_PRIVATE_KEY_PATH")
    if not os.path.exists(key_path):
        logger.error(f"Missing RSA key file at configured path: {key_path}")
        raise FileNotFoundError(f"Missing RSA key file at configured path: {key_path}")

    with open(key_path, "rb") as f:
        pk = serialization.load_pem_private_key(
            f.read(), password=None, backend=default_backend()
        )
    pkb = pk.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    return dict(
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        user=os.getenv("SNOWFLAKE_USER"),
        private_key=pkb,
        role=os.getenv("SNOWFLAKE_ROLE"),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
        database=os.getenv("SNOWFLAKE_DATABASE"),
        schema=os.getenv("SNOWFLAKE_SCHEMA"),
    )

def sf_connect():
    return snowflake.connector.connect(**get_sf_engine())

# ── Core Retrieval (No Streamlit Caching in Core) ───────────────────
def run_retrieval(user_query: str, topk: int):
    terms = extract_keywords(user_query)
    if not terms:
        return pd.DataFrame(), terms

    where_parts = ["CHUNK_TEXT ILIKE %s" for _ in terms]
    score_parts = ["IFF(CHUNK_TEXT ILIKE %s, 1, 0)" for _ in terms]
    
    table_name = SETTINGS.get("snowflake", {}).get("doc_chunks_table", "DOC_CHUNKS_FEATURED")
    
    sql = f"""
    SELECT DOC_NAME, PAGE_NUM, CHUNK_ID, CHUNK_TEXT, TEXT_LENGTH,
           ({" + ".join(score_parts)}) AS SCORE
    FROM {table_name}
    WHERE {" OR ".join(where_parts)}
    ORDER BY SCORE DESC, TEXT_LENGTH DESC
    LIMIT {int(topk)};
    """
    score_params = [f"%{t}%" for t in terms]  # for IFF() expressions in SELECT
    where_params  = [f"%{t}%" for t in terms]  # for ILIKE clauses in WHERE
    params = score_params + where_params

    conn = sf_connect()
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        rows = cur.fetchall()
        cols = [c[0] for c in cur.description]
        return pd.DataFrame(rows, columns=cols), terms
    except Exception as e:
        logger.error(f"Retrieval error: {e}")
        return pd.DataFrame(), terms
    finally:
        try: cur.close()
        except Exception: pass
        conn.close()
