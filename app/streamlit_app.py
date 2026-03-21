"""
streamlit_app.py  ——  UMKC PolicyPulse (Full Extended Version)
=========================================
Extensions Covered:
  ✅ [Data]    Additional dataset ingestion     → Sidebar manual CSV upload / scheduler call
  ✅ [Data]    Auto feature engineering pipeline → extract_keywords + write to FEATURE_STORE
  ✅ [Data]    Feature Store / Version management → feature_store.py
  ✅ [Model]   LLM Answer Generation            → Groq (llama-3.1-8b-instant)
  ✅ [Model]   Evaluation metrics logging       → evaluator.py
  ✅ [Model]   Evaluation Comparison Dashboard   → "📊 Eval Comparison" Tab
  ✅ [Model]   What-if Scenario Simulation      → "🔮 What-if Simulation" Tab
  ✅ [System]  Interactive Analytics Dashboard   → "📈 Analytics Dashboard" Tab
  ✅ [System]  Scheduled data ingestion workflow → scheduler.py (can run in background)
  ✅ [System]  Query optimization/Materialized view → Snowflake RESULT_SCAN + Cache
  ✅ [System]  Pipeline Monitoring Dashboard     → "🔧 Pipeline Monitoring" Tab
"""
import os
import re
import time
import csv
import hashlib
import sys
import logging
from datetime import datetime

import pandas as pd
import streamlit as st

st.set_page_config(page_title="UMKC PolicyPulse", layout="wide", page_icon="🎓")

import snowflake.connector
from dotenv import load_dotenv
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from groq import Groq

# Add project root to Python path so imports like `core`, `app`, etc. work
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.features import feature_store as fs
from core.modeling import evaluator as ev
from core.ingestion import scheduler as sc
from app import core_services as cs
from app.weekly_schedule_tab import render_weekly_schedule_tab
from agent.agent_runner import run_agent
from core.config import SETTINGS
from core.logger import get_logger
from streamlit_mic_recorder import speech_to_text

logger = get_logger("app")

# ── Base Configuration ──────────────────────────────────────────
load_dotenv()
LOG_PATH = os.path.join(PROJECT_ROOT, "artifacts", "pipeline_logs.csv")
APP_VERSION = st.sidebar.selectbox("Model Version", ["v1", "v2", "v3"], index=0)

@st.cache_resource
def init_db_tables():
    try:
        fs.ensure_table()
        ev.ensure_table()
        logger.info("Database tables initialized successfully.")
    except Exception as e:
        logger.warning(f"DB initialization warning: {e}")

init_db_tables()

# ── Logging Utilities ──────────────────────────────────────────
def ensure_log_header():
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    if os.path.exists(LOG_PATH):
        return
    with open(LOG_PATH, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([
            "timestamp","run_id","stage","status",
            "rows_in","rows_out","latency_ms","error_message"
        ])

def log_event(run_id, stage, status, rows_out=None, latency_ms=None, error_message=""):
    ensure_log_header()
    with open(LOG_PATH, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([
            datetime.utcnow().isoformat(), run_id, stage, status,
            "", rows_out or "", latency_ms or "", error_message or ""
        ])
    if status == "success":
        logger.info(f"[{run_id}] Stage: {stage} - Status: {status} - Latency: {latency_ms}ms")
    else:
        logger.error(f"[{run_id}] Stage: {stage} - Status: {status} - Error: {error_message}")

# ── Feature Engineering ─────────────────────────────────────────
def extract_keywords(query: str, max_terms: int = 6):
    return cs.extract_keywords(query, max_terms)

# ── Groq LLM Generation ─────────────────────────────────────────
@st.cache_resource
def get_groq_client():
    return cs.get_groq_client()

def generate_answer(question: str, chunks_df: pd.DataFrame, model: str = "llama-3.1-8b-instant") -> str:
    return cs.generate_answer(question, chunks_df, model)

# ── Snowflake Connection ────────────────────────────────────────
def sf_connect():
    return cs.sf_connect()

# ── Core Retrieval (With Caching) ───────────────────────────────
@st.cache_data(ttl=120, show_spinner=False)
def cached_retrieval(query: str, topk: int):
    return cs.run_retrieval(query, topk)

# ── What-if Scenario Simulation ─────────────────────────────────
def run_whatif(base_query: str, scenarios: list[str], topk: int):
    """Retrieves multiple scenarios in parallel and returns a comparison DataFrame"""
    records = []
    for s in scenarios:
        t0 = time.time()
        df, terms = cached_retrieval(s, topk)
        ms = int((time.time() - t0) * 1000)
        avg_score = float(df["SCORE"].mean()) if not df.empty and "SCORE" in df.columns else 0
        records.append({
            "Scenario Query": s,
            "Keyword Count":  len(terms),
            "Returned Chunks": len(df),
            "Average Score":  round(avg_score, 3),
            "Latency (ms)":   ms,
            "Keywords":       ", ".join(terms),
        })
    return pd.DataFrame(records)

# ════════════════════════════════════════════════════════════════
#  UI LAYOUT
# ════════════════════════════════════════════════════════════════
st.title("🎓 UMKC PolicyPulse — Snowflake RAG (Full Extended Version)")



tabs = st.tabs([
    "🤖 Agent Chat",
    "🔍 Retrieval",
    "📅 Weekly Schedule",
    "📈 Analytics Dashboard",
    "📊 Eval Comparison",
    "🔮 What-if Simulation",
    "📥 Data Ingestion",
    "🔧 Pipeline Monitoring",
])

# ─────────────────────────────────────────────────────────────
# TAB 0 · Agent Chat
# ─────────────────────────────────────────────────────────────
with tabs[0]:
    st.header("🤖 PolicyPulse Smart Agent")
    st.markdown("Ask me anything about UMKC policies, what-if scenarios, or pipeline analytics!")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "voice_prompt" not in st.session_state:
        st.session_state.voice_prompt = ""

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if "trace" in msg and msg["trace"]:
                with st.expander("🛠️ Agent Reasoning Trace"):
                    for t in msg["trace"]:
                        st.json(t)
            if "evidence" in msg and msg["evidence"]:
                with st.expander("📄 Retrieved Evidence"):
                    for evidence_item in msg["evidence"]:
                        st.markdown(
                            f"**{evidence_item['doc']} (Page {evidence_item['page']})** "
                            f"- Score: {evidence_item['score']}\n\n> {evidence_item['text']}"
                        )

    st.subheader("🎤 Voice Input")

    voice_t0 = time.time()

    try:
        spoken_text = speech_to_text(
            language="en",
            start_prompt="Start recording",
            stop_prompt="Stop recording",
            just_once=True,
            use_container_width=True,
            key="voice_input",
        )
        voice_latency_ms = int((time.time() - voice_t0) * 1000)

    except Exception as e:
        voice_latency_ms = int((time.time() - voice_t0) * 1000)
        log_event(
            run_id=f"voice-{int(time.time())}",
            stage="speech_to_text",
            status="fail",
            latency_ms=voice_latency_ms,
            error_message=str(e)
        )
        st.error(f"Voice input failed: {e}")
        spoken_text = None

    if spoken_text:
        st.session_state.voice_prompt = spoken_text
        log_event(
            run_id=f"voice-{int(time.time())}",
            stage="speech_to_text",
            status="success",
            rows_out=len(spoken_text),
            latency_ms=voice_latency_ms
        )
        st.success("Voice captured successfully.")

    prompt = st.chat_input("Type your question here...")

    if st.session_state.voice_prompt:
        st.text_area(
            "Transcribed voice message",
            value=st.session_state.voice_prompt,
            height=100,
            key="voice_preview",
        )

    send_voice = st.button("Send voice message", use_container_width=True)

    final_prompt = None
    if prompt:
        final_prompt = prompt
    elif send_voice and not st.session_state.voice_prompt.strip():
    log_event(
        run_id=f"voice-send-{int(time.time())}",
        stage="voice_message_sent",
        status="warning",
        rows_out=0,
        latency_ms=0,
        error_message="Send voice message clicked with empty transcription"
    )
    st.warning("No transcribed voice message to send.")
      
    elif send_voice and st.session_state.voice_prompt.strip():
        final_prompt = st.session_state.voice_prompt.strip()
        log_event(
            run_id=f"voice-send-{int(time.time())}",
            stage="voice_message_sent",
            status="success",
            rows_out=len(final_prompt),
            latency_ms=0
        )

    if final_prompt:
        st.session_state.messages.append({"role": "user", "content": final_prompt})

        with st.chat_message("user"):
            st.markdown(final_prompt)

        with st.chat_message("assistant"):
            with st.spinner("🤖 Agent is thinking..."):
                response_data = run_agent(final_prompt)

            answer = response_data.get("answer", "No answer generated.")
            trace = response_data.get("trace", [])
            evidence = response_data.get("evidence", [])

            st.markdown(answer)

            if trace:
                with st.expander("🛠️ Agent Reasoning Trace"):
                    for t in trace:
                        st.json(t)

            if evidence:
                with st.expander("📄 Retrieved Evidence"):
                    for evidence_item in evidence:
                        st.markdown(
                            f"**{evidence_item['doc']} (Page {evidence_item['page']})** "
                            f"- Score: {evidence_item['score']}\n\n> {evidence_item['text']}"
                        )

        st.session_state.messages.append({
            "role": "assistant",
            "content": answer,
            "trace": trace,
            "evidence": evidence
        })

        st.session_state.voice_prompt = ""
# ─────────────────────────────────────────────────────────────
# TAB 1 · Retrieval
# ─────────────────────────────────────────────────────────────
with tabs[1]:
    st.header("🔍 Document Retrieval + AI Answer")

    q    = st.text_input("Enter your question", value="How much is a parking permit?")
    topk = st.slider("Top-K", 3, 20, 8)

    # LLM Settings
    with st.expander("⚙️ LLM Settings", expanded=False):
        llm_model = st.selectbox(
            "Groq Model",
            [
                SETTINGS.get("llm_model", "llama-3.1-8b-instant"),
                "gemma2-9b-it",
                "llama-3.3-70b-versatile",
                "llama-guard-3-8b"
            ],
            index=0
        )
        use_llm = st.toggle("Enable AI Generated Answer", value=True)

    if st.button("🔎 Search", type="primary"):
        run_id = f"search-{int(time.time())}"
        t0 = time.time()
        try:
            # ── Step 1: Retrieval ─────────────────────────────
            with st.spinner("🔍 Retrieving documents..."):
                df, terms = cached_retrieval(q, topk)
            retrieval_ms = int((time.time() - t0) * 1000)

            # ── Step 2: LLM Generation ────────────────────────
            if use_llm and not df.empty:
                with st.spinner("🤖 AI generating answer..."):
                    answer, llm_ms = cs.generate_answer(q, df, model=llm_model)
                log_event(run_id, "llm_generate", "success", latency_ms=llm_ms)
            else:
                answer = None
                llm_ms = 0

            total_ms = int((time.time() - t0) * 1000)

            # ── Logs & Metrics ────────────────────────────────
            log_event(run_id, "search", "success", rows_out=len(df), latency_ms=retrieval_ms)
            fs.save_features(run_id, q, terms, topk, version=APP_VERSION)
            ev.log_eval(run_id, q, df, retrieval_ms, len(terms), topk, version=APP_VERSION)

            # ── Display AI Answer ─────────────────────────────
            if answer:
                st.markdown("### 🤖 AI Answer")
                st.info(answer)
                st.caption(f"Retrieval: {retrieval_ms} ms · LLM Gen: {llm_ms} ms · Total: {total_ms} ms · Model: {llm_model}")
            else:
                st.success(f"✅ Returned {len(df)} results in {retrieval_ms} ms (AI Answer Disabled)")

            # ── Display Raw Chunks ────────────────────────────
            st.markdown("### 📄 Retrieved Raw Document Fragments")
            st.write("Extracted Keywords:", terms)
            st.dataframe(
                df[["DOC_NAME","PAGE_NUM","CHUNK_ID","SCORE","TEXT_LENGTH"]],
                use_container_width=True
            )
            for i, r in df.iterrows():
                with st.expander(
                    f"{i+1}. {r['DOC_NAME']}  p{r['PAGE_NUM']}  "
                    f"chunk={r['CHUNK_ID']}  score={r['SCORE']}"
                ):
                    st.write(r["CHUNK_TEXT"])

        except Exception as e:
            ms = int((time.time() - t0) * 1000)
            log_event(run_id, "search", "fail", rows_out=0, latency_ms=ms, error_message=str(e))
            st.error(f"Query Failed: {e}")

# ─────────────────────────────────────────────────────────────
# TAB 2 · Weekly Schedule  (NEW)
# ─────────────────────────────────────────────────────────────
with tabs[2]:
    render_weekly_schedule_tab()

# ─────────────────────────────────────────────────────────────
# TAB 3 · Analytics Dashboard
# ─────────────────────────────────────────────────────────────
with tabs[3]:
    st.header("📈 Interactive Analytics Dashboard")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Feature Version Distribution")
        try:
            fv = fs.load_feature_versions()
            if fv.empty:
                st.info("No feature data. Please perform a retrieval first.")
            else:
                st.dataframe(fv, use_container_width=True)
                st.bar_chart(fv.set_index("VERSION")["TOTAL_QUERIES"])
        except Exception as e:
            st.warning(f"Failed to load feature versions: {e}")

    with col2:
        st.subheader("Evaluation Metric Trends")
        try:
            hist = ev.load_metrics_history(200)
            if hist.empty:
                st.info("No evaluation data. Please perform a retrieval first.")
            else:
                hist["CREATED_AT"] = pd.to_datetime(hist["CREATED_AT"])
                st.line_chart(
                    hist.sort_values("CREATED_AT").set_index("CREATED_AT")[["AVG_SCORE","LATENCY_MS"]]
                )
        except Exception as e:
            st.warning(f"Failed to load evaluation history: {e}")

    st.subheader("Recent Feature Logs")
    try:
        fh = fs.load_feature_history(50)
        st.dataframe(fh, use_container_width=True)
    except Exception as e:
        st.warning(f"Failed to load feature history: {e}")

# ─────────────────────────────────────────────────────────────
# TAB 4 · Eval Comparison Dashboard
# ─────────────────────────────────────────────────────────────
with tabs[4]:
    st.header("📊 Evaluation Comparison Dashboard")

    try:
        summary = ev.load_metrics_summary()
        if summary.empty:
            st.info("No evaluation data yet. Please perform a few searches in the Retrieval tab.")
        else:
            st.subheader("Summary by Version")
            st.dataframe(summary, use_container_width=True)

            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("Total Versions",  len(summary))
            with c2:
                st.metric("Total Runs", int(summary["TOTAL_RUNS"].sum()))
            with c3:
                best = summary.loc[summary["MEAN_AVG_SCORE"].idxmax(), "VERSION"]
                st.metric("Highest Avg Score Version", best)

            st.subheader("Average Score Comparison")
            st.bar_chart(summary.set_index("VERSION")["MEAN_AVG_SCORE"])

            st.subheader("Average Latency Comparison (ms)")
            st.bar_chart(summary.set_index("VERSION")["MEAN_LATENCY_MS"])

            st.subheader("Individual Eval Records (Recent 200)")
            detail = ev.load_metrics_history(200)
            st.dataframe(detail, use_container_width=True)

    except Exception as e:
        st.error(f"Failed to load evaluation data: {e}")

# ─────────────────────────────────────────────────────────────
# TAB 5 · What-if Simulation
# ─────────────────────────────────────────────────────────────
with tabs[5]:
    st.header("🔮 What-if Scenario Simulation")
    st.markdown(
        "Enter multiple query variations. The system retrieves them in parallel and compares results—"
        "helping you find the optimal phrasing or evaluate the impact of keyword changes."
    )

    default_scenarios = (
        "How much is a parking permit?\n"
        "What is the cost of student parking?\n"
        "Parking fees for faculty\n"
        "Campus parking regulations"
    )
    raw = st.text_area("Scenario List (One query per line)", value=default_scenarios, height=140)
    wi_topk = st.slider("Top-K per Scenario", 3, 15, 5, key="wi_topk")

    if st.button("▶ Run Simulation", type="primary"):
        scenarios = [s.strip() for s in raw.splitlines() if s.strip()]
        if not scenarios:
            st.warning("Please enter at least one scenario")
        else:
            with st.spinner(f"Simulating {len(scenarios)} scenarios..."):
                cmp = run_whatif("", scenarios, wi_topk)

            st.success("Simulation Complete!")
            st.dataframe(cmp, use_container_width=True)

            st.subheader("Returned Chunks Count Comparison")
            st.bar_chart(cmp.set_index("Scenario Query")["Returned Chunks"])

            st.subheader("Average Score Comparison")
            st.bar_chart(cmp.set_index("Scenario Query")["Average Score"])

            st.subheader("Latency Comparison (ms)")
            st.bar_chart(cmp.set_index("Scenario Query")["Latency (ms)"])

            best_row = cmp.loc[cmp["Average Score"].idxmax()]
            st.info(f"🏆 Best Scenario: **{best_row['Scenario Query']}** "
                    f"Avg Score={best_row['Average Score']}  "
                    f"Keywords: {best_row['Keywords']}")

# ─────────────────────────────────────────────────────────────
# TAB 6 · Data Ingestion
# ─────────────────────────────────────────────────────────────
with tabs[6]:
    st.header("📥 Additional Dataset Ingestion")

    st.markdown("""
    Upload CSV files. The system will parse and append them to the Snowflake `DOC_CHUNKS_FEATURED` table.
    
    **CSV must contain these columns:**
    `DOC_NAME`, `PAGE_NUM`, `CHUNK_ID`, `CHUNK_TEXT`, `TEXT_LENGTH`
    """)

    uploaded = st.file_uploader("Select CSV files (supports multiple)", type="csv", accept_multiple_files=True)

    if uploaded and st.button("⬆ Start Ingestion", type="primary"):
        sc.ensure_dirs()
        for uf in uploaded:
            save_path = os.path.join(sc.INBOX_DIR, uf.name)
            with open(save_path, "wb") as f:
                f.write(uf.getbuffer())

        results = sc.run_once()
        for r in results:
            if r["status"] == "success":
                st.success(f"✅ {r['file']} — Ingested {r['rows']} rows")
            elif r["status"] == "skipped":
                st.info(f"⏭ {r['file']} — Already ingested, skipped")
            else:
                st.error(f"❌ {r['file']} — Failed: {r.get('error')}")

    st.subheader("Ingestion Logs")
    try:
        ilog = sc.load_ingest_log(50)
        st.dataframe(ilog, use_container_width=True)
    except Exception as e:
        st.warning(f"Ingestion log failed to load (Upload a file first): {e}")

    st.divider()
    st.subheader("⏰ Scheduled Auto-Ingestion Instructions")
    st.code(
        "# Run the scheduler independently in the background (scans ingest_inbox/ every 60s)\n"
        "python scheduler.py\n\n"
        "# Custom interval (seconds)\n"
        "SCHEDULER_INTERVAL_SEC=30 python scheduler.py",
        language="bash"
    )

# ─────────────────────────────────────────────────────────────
# TAB 7 · Pipeline Monitoring
# ─────────────────────────────────────────────────────────────
with tabs[7]:
    st.header("🔧 Pipeline Monitoring Dashboard")

    if os.path.exists(LOG_PATH):
        log_df = pd.read_csv(LOG_PATH)

        total  = len(log_df)
        ok     = (log_df["status"] == "success").sum()
        fail   = (log_df["status"] == "fail").sum()
        avg_ms = log_df["latency_ms"].dropna().astype(float).mean()

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Runs",  total)
        c2.metric("Success",     int(ok))
        c3.metric("Failure",     int(fail))
        c4.metric("Avg Latency (ms)", f"{avg_ms:.0f}" if not pd.isna(avg_ms) else "—")

        st.subheader("Success / Failure Distribution")
        status_counts = log_df["status"].value_counts()
        st.bar_chart(status_counts)

        st.subheader("Latency Trend")
        lat = log_df[["timestamp","latency_ms"]].dropna()
        lat["latency_ms"] = lat["latency_ms"].astype(float)
        lat = lat.set_index("timestamp")
        st.line_chart(lat)

        st.subheader("Recent 50 Logs")
        st.dataframe(log_df.tail(50), use_container_width=True)
    else:
        st.info("No logs found. Perform a search in the Retrieval tab first.")
