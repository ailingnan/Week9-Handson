# UMKC PolicyPulse — Week 9 Enhancement Report

### Enhancement 1: Application Workflow / User Experience

We added a new **📅 Weekly Schedule** tab to the Streamlit application. This feature helps UMKC students consolidate their academic schedule, campus events, and personal commitments into one unified weekly view.

**What was built:**

- **Syllabus PDF parsing** — students upload their course syllabi and the system uses the Claude API to automatically extract all class meeting times, room locations, assignment due dates, exam dates, and semester bounds. No manual entry required.
- **RooGroups campus event integration** — the system connects to UMKC's RooGroups platform using the student's credentials to pull live campus activities for the week. A demo mode with realistic mock events is available for offline use.
- **Personal event input (English)** — students can type any personal event in natural language (e.g. "dentist tomorrow 3PM" or "April 10 team meeting at 2pm") and the Claude API parses it into a structured schedule entry automatically.
- **Free-gap detection** — the system automatically identifies free time slots between classes (minimum 30 minutes) and highlights which campus events fall within those gaps, so students can actually attend them.
- **Google Maps navigation** — each event card with a building name generates a directions link using the student's GPS coordinates as the origin. Clicking opens turn-by-turn navigation in Google Maps at no API cost.
- **Week navigation** — students can browse forward and backward by week using Prev / Today / Next buttons. Today's column is highlighted.

**Files added:**
- `app/weekly_schedule_tab.py` — Streamlit UI for the new tab
- `core/weekly_schedule.py` — schedule engine, Claude API calls, RooGroups scraper, navigation links
<img width="877" height="538" alt="image" src="https://github.com/user-attachments/assets/b4cd246b-f761-4d11-a8f3-a1f32d4a7535" />

---

### Enhancement 2: Logging and Debugging Support

We extended the existing pipeline monitoring infrastructure to cover the new Weekly Schedule features, creating a consistent and observable logging system across the full application.

**What was built:**

- **New log file** `artifacts/schedule_logs.csv` — records every significant schedule operation with the same schema as the existing `pipeline_logs.csv`: timestamp, action type, detail, latency in milliseconds, and status (success / error / warning).
- **Three operation types are logged:**
  - `syllabus_parse` — records the filename, extracted course code, and Claude API latency for each uploaded PDF
  - `personal_event_add` — records the parsed event title, target date, and end-to-end Claude API latency
  - `roogroups_login` — records login outcome and network latency
- **System log integration** — all schedule events are also written to `logs/system.log` via the shared `get_logger()` utility, giving a consolidated view alongside the existing RAG pipeline and LLM generation logs.

**Files modified:**
- `app/weekly_schedule_tab.py` — added `log_schedule_event()` calls at all key actions
- `artifacts/schedule_logs.csv` — new log file created automatically on first use
<img width="967" height="533" alt="image" src="https://github.com/user-attachments/assets/01a78685-17b9-49ad-a263-5f20bae90a59" />

---

## How to Run

```bash
pip install -r requirements.txt
streamlit run app/streamlit_app.py
```

Set `ANTHROPIC_API_KEY` in your `.env` file to enable syllabus parsing and personal event input.

---

## Team Contributions

| Member | Contributions |
|---|---|
| **Ailing Nan** | Designed and implemented the full Weekly Schedule feature including syllabus PDF parsing via Claude API, RooGroups scraper and mock data, personal event NLP input (Chinese + English), free-gap detection algorithm, Google Maps navigation links, Streamlit UI layout, schedule logging system, and integration into the main app |
| **Lyza Iamrache** | Assisted with testing the weekly schedule feature, verified demo mode behavior across different syllabus formats, and contributed to the Week 9 group report write-up |
| **Gia Huynh** | Assisted with requirements.txt dependency updates, README documentation, and supported integration testing of the new tab with the existing Snowflake pipeline |

---

*CS 5588 · UMKC · Spring 2026*
