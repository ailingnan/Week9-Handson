"""
tools.py
--------
Python tool definitions wrapping non-UI business logic for the Agent to use.
"""

import sys
import os

# Append the parent directory to sys.path so we can import from `app/`
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import app.core_services as cs
from core.modeling.evaluator import load_metrics_summary, load_metrics_history

def search_policy(query: str, top_k: int = 5) -> dict:
    """Retrieves policy chunks using Snowflake without Streamlit side-effects."""
    df, terms = cs.run_retrieval(query, top_k)
    if df.empty:
        return {"status": "success", "results": "No policy documents found matching the keywords.", "chunks": []}
    
    # Extract only the necessary info
    chunks = []
    for _, row in df.iterrows():
        chunks.append({
            "doc": str(row.get("DOC_NAME", "Unknown")),
            "page": str(row.get("PAGE_NUM", "?")),
            "text": str(row.get("CHUNK_TEXT", "")),
            "score": str(row.get("SCORE", "0"))
        })
    
    return {"status": "success", "keywords_matched": terms, "chunks": chunks}

def simulate_whatif(scenarios: list[str], top_k: int = 5) -> dict:
    """Runs a parallel what-if simulation on multiple scenario queries."""
    results = []
    for s in scenarios:
        df, terms = cs.run_retrieval(s, top_k)
        avg_s = float(df["SCORE"].mean()) if not df.empty and "SCORE" in df.columns else 0.0
        results.append({
            "scenario": s,
            "keywords": terms,
            "chunks_returned": len(df),
            "average_score": round(avg_s, 3)
        })
    return {"status": "success", "simulations": results}

def get_eval_metrics(summary: bool = True) -> dict:
    """Retrieves evaluation metrics summaries."""
    try:
        if summary:
            df = load_metrics_summary()
            if df.empty:
                return {"status": "success", "data": "No eval summary data found."}
            return {"status": "success", "data": df.to_dict(orient="records")}
        else:
            df = load_metrics_history(10) # last 10 entries for brevity in tool log
            if df.empty:
                return {"status": "success", "data": "No eval history data found."}
            return {"status": "success", "data": df.to_dict(orient="records")}
    except Exception as e:
        return {"status": "error", "error": f"Failed to get eval metrics: {e}"}

# Dispatch mapping mapping schema tool name to python function
TOOL_MAP = {
    "search_policy": search_policy,
    "simulate_whatif": simulate_whatif,
    "get_eval_metrics": get_eval_metrics
}
