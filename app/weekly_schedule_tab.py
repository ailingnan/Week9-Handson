"""
weekly_schedule_tab.py
======================
Renders the 📅 Weekly Schedule tab inside the UMKC PolicyPulse Streamlit app.

Drop-in usage inside streamlit_app.py:

    from app.weekly_schedule_tab import render_weekly_schedule_tab
    with tabs[7]:          # or whichever index
        render_weekly_schedule_tab()
"""

import streamlit as st
from datetime import datetime
import time
import csv
import os

from core.logger import get_logger

logger = get_logger("weekly_schedule")

# ── Schedule-specific CSV log ──────────────────────────────────
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCHEDULE_LOG_PATH = os.path.join(_PROJECT_ROOT, "artifacts", "schedule_logs.csv")

def _ensure_schedule_log():
    os.makedirs(os.path.dirname(SCHEDULE_LOG_PATH), exist_ok=True)
    if not os.path.exists(SCHEDULE_LOG_PATH):
        with open(SCHEDULE_LOG_PATH, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow([
                "timestamp", "action", "detail", "latency_ms", "status"
            ])

def log_schedule_event(action: str, detail: str, latency_ms: int = 0, status: str = "success"):
    _ensure_schedule_log()
    with open(SCHEDULE_LOG_PATH, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([
            datetime.utcnow().isoformat(), action, detail, latency_ms, status
        ])
    logger.info(f"[schedule] {action} | {detail} | {latency_ms}ms | {status}")

# Lazy import so the rest of the app still works if deps are missing
from core.weekly_schedule import (
    parse_syllabus_pdf,
    get_demo_course,
    get_mock_roogroups_events,
    roogroups_login,
    scrape_roogroups_events,
    build_week_schedule,
    find_free_gaps,
    make_google_maps_link,
    parse_personal_event,
    DAY_ORDER,
)

# ── colour tokens per item type ────────────────────────────────
TYPE_META = {
    "class":        {"emoji": "📚", "label": "Class",         "bg": "#EBF3FF", "border": "#2563EB", "dark_bg": "#1E3A5F"},
    "deadline":     {"emoji": "📝", "label": "Assignment Due", "bg": "#FFFBEB", "border": "#D97706", "dark_bg": "#3B2A0D"},
    "exam":         {"emoji": "🎯", "label": "Exam",          "bg": "#FFF1F1", "border": "#DC2626", "dark_bg": "#3B1010"},
    "campus_event": {"emoji": "🎉", "label": "Campus Event",  "bg": "#EFFDF5", "border": "#16A34A", "dark_bg": "#0E2B16"},
    "personal":     {"emoji": "🗓", "label": "Personal",      "bg": "#F5F3FF", "border": "#7C3AED", "dark_bg": "#2D1B69"},
}

# ── CSS injected once ──────────────────────────────────────────
SCHEDULE_CSS = """
<style>
.sched-card {
    border-left: 4px solid var(--bc);
    background: var(--bg);
    border-radius: 8px;
    padding: 10px 14px;
    margin-bottom: 8px;
    position: relative;
}
.sched-card .sc-time  { font-size: 12px; color: #6B7280; margin-bottom: 2px; }
.sched-card .sc-title { font-weight: 600; font-size: 15px; margin-bottom: 2px; }
.sched-card .sc-meta  { font-size: 12px; color: #6B7280; }
.sched-card .sc-badge {
    display: inline-block;
    font-size: 10px;
    font-weight: 600;
    padding: 1px 7px;
    border-radius: 99px;
    border: 1px solid var(--bc);
    color: var(--bc);
    margin-right: 6px;
}
.gap-pill {
    background: #F0FDF4;
    border: 1px dashed #16A34A;
    border-radius: 6px;
    padding: 6px 12px;
    font-size: 12px;
    color: #15803D;
    margin-bottom: 6px;
}
.day-header {
    font-size: 18px;
    font-weight: 700;
    padding-bottom: 4px;
    border-bottom: 2px solid #E5E7EB;
    margin-bottom: 12px;
}
.today-marker { color: #2563EB; }
</style>
"""


def _card_html(item: dict, maps_url: str = "") -> str:
    meta   = TYPE_META.get(item["type"], TYPE_META["class"])
    time_s = item.get("time_start") or ""
    time_e = item.get("time_end")   or ""
    time_str = f"{time_s}–{time_e}" if time_e else time_s

    loc    = item.get("location", "")
    desc   = item.get("description", "")
    course = item.get("course_code", "")

    nav_btn = ""
    if maps_url and loc:
        nav_btn = (
            f'<a href="{maps_url}" target="_blank" style="'
            f'font-size:11px;margin-left:8px;color:#2563EB;text-decoration:none;">'
            f'🗺 Navigate</a>'
        )

    return f"""
<div class="sched-card" style="--bc:{meta['border']};--bg:{meta['bg']};">
  <div class="sc-time">{time_str}</div>
  <div class="sc-title">{meta['emoji']} {item['title']}</div>
  <div class="sc-meta">
    <span class="sc-badge">{meta['label']}</span>
    {f'<span style="margin-right:6px;">🏛 {loc}</span>' if loc else ''}
    {f'<span style="margin-right:6px;">📖 {course}</span>' if course else ''}
    {nav_btn}
  </div>
  {f'<div style="font-size:12px;color:#6B7280;margin-top:4px;">{desc}</div>' if desc else ''}
</div>
"""


def render_weekly_schedule_tab():
    st.markdown(SCHEDULE_CSS, unsafe_allow_html=True)
    st.header("📅 Weekly Schedule")
    st.markdown("Upload your syllabus, connect to RooGroups, and see your whole week in one place.")

    # ── Sidebar-style controls in expanders ───────────────────
    col_left, col_right = st.columns([1, 2], gap="large")

    # ════════════════════════════════════════════════════════
    # LEFT PANEL — setup controls
    # ════════════════════════════════════════════════════════
    with col_left:
        # ── 1. Syllabus upload ─────────────────────────────
        st.subheader("📂 Course Syllabi")
        uploaded_files = st.file_uploader(
            "Upload PDF syllabus (one per course)",
            type="pdf",
            accept_multiple_files=True,
            key="syllabus_upload",
        )

        if st.button("✨ Parse Syllabi with AI", type="primary", use_container_width=True):
            if not uploaded_files:
                st.info("No files uploaded — loading demo course instead.")
                st.session_state["parsed_courses"] = [get_demo_course()]
            else:
                courses = []
                for uf in uploaded_files:
                    with st.spinner(f"Reading {uf.name}…"):
                        t0 = time.time()
                        try:
                            data = parse_syllabus_pdf(uf.read())
                            ms = int((time.time() - t0) * 1000)
                            courses.append(data)
                            log_schedule_event("syllabus_parse", f"{uf.name} → {data.get('course_code','?')}", ms)
                            st.success(f"✅ {data.get('course_code','?')} — {data.get('course_name','?')}")
                        except Exception as e:
                            ms = int((time.time() - t0) * 1000)
                            log_schedule_event("syllabus_parse", uf.name, ms, status="error")
                            st.error(f"❌ {uf.name}: {e}")
                            courses.append(get_demo_course())
                st.session_state["parsed_courses"] = courses

        if st.button("🎓 Load Demo Course", use_container_width=True):
            st.session_state["parsed_courses"] = [get_demo_course()]
            st.success("Demo course loaded!")

        courses = st.session_state.get("parsed_courses", [])
        if courses:
            st.caption(f"{len(courses)} course(s) loaded")
            for c in courses:
                st.markdown(f"- **{c.get('course_code','')}** {c.get('course_name','')}")

        st.divider()

        # ── 2. RooGroups login ─────────────────────────────
        st.subheader("🦘 RooGroups Events")

        demo_events = st.toggle("Use demo events (offline)", value=True, key="use_demo_events")

        if not demo_events:
            with st.form("roogroups_login_form"):
                username = st.text_input("UMKC Email", placeholder="abc123@umsystem.edu")
                password = st.text_input("Password", type="password")
                login_btn = st.form_submit_button("🔑 Connect", use_container_width=True)

            if login_btn:
                with st.spinner("Connecting to RooGroups…"):
                    t0 = time.time()
                    session = roogroups_login(username, password)
                    ms = int((time.time() - t0) * 1000)
                if session:
                    events = scrape_roogroups_events(session)
                    if events:
                        st.session_state["campus_events"] = events
                        log_schedule_event("roogroups_login", f"success, {len(events)} events", ms)
                        st.success(f"✅ Loaded {len(events)} live events!")
                    else:
                        log_schedule_event("roogroups_login", "login ok but no events, using demo", ms, "warning")
                        st.warning("Logged in but no events found. Using demo events.")
                        st.session_state["campus_events"] = get_mock_roogroups_events()
                else:
                    log_schedule_event("roogroups_login", "login failed, using demo", ms, "error")
                    st.error("Login failed — using demo events.")
                    st.session_state["campus_events"] = get_mock_roogroups_events()
        else:
            if "campus_events" not in st.session_state or st.session_state.get("_events_source") != "demo":
                st.session_state["campus_events"] = get_mock_roogroups_events()
                st.session_state["_events_source"] = "demo"
            st.caption(f"📋 {len(st.session_state['campus_events'])} demo events loaded")

        st.divider()

        # ── 3. Location ────────────────────────────────────
        st.subheader("📍 Your Location")
        use_location = st.toggle("Enable navigation links", value=False, key="use_location")

        user_lat, user_lng = None, None
        if use_location:
            st.info("Enter your current location coordinates (or use your phone's GPS).")
            loc_col1, loc_col2 = st.columns(2)
            with loc_col1:
                user_lat = st.number_input("Latitude",  value=39.0379, format="%.4f")
            with loc_col2:
                user_lng = st.number_input("Longitude", value=-94.5784, format="%.4f")
            st.caption("Default: UMKC campus center")

        st.divider()

        # ── 4. Personal events ─────────────────────────────
        st.subheader("🗓 Add Personal Event")
        st.caption("Type anything — Chinese or English — and AI will parse it.")

        with st.form("personal_event_form", clear_on_submit=True):
            user_input = st.text_input(
                "Describe your event",
                placeholder="e.g. 4月5号有个会议 / March 21 dinner at Lee's",
            )
            add_btn = st.form_submit_button("➕ Add to Schedule", use_container_width=True)

        if add_btn and user_input.strip():
            with st.spinner("AI is parsing your event…"):
                t0 = time.time()
                try:
                    evt = parse_personal_event(user_input.strip())
                    ms = int((time.time() - t0) * 1000)
                    personal = st.session_state.get("personal_events", [])
                    personal.append(evt)
                    st.session_state["personal_events"] = personal
                    log_schedule_event("personal_event_add", f"{evt['title']} on {evt['date']}", ms)
                    st.success(
                        f"✅ Added: **{evt['title']}** on {evt['date']}"
                        + (f" at {evt['time_start']}" if evt.get('time_start') else "")
                    )
                except Exception as e:
                    ms = int((time.time() - t0) * 1000)
                    log_schedule_event("personal_event_add", user_input[:60], ms, status="error")
                    st.error(f"Could not parse event: {e}")

        # Show & manage existing personal events
        personal_events = st.session_state.get("personal_events", [])
        if personal_events:
            st.markdown(f"**{len(personal_events)} personal event(s):**")
            for i, evt in enumerate(personal_events):
                col_e, col_del = st.columns([5, 1])
                with col_e:
                    st.markdown(
                        f"<div style='font-size:13px;padding:2px 0;'>"
                        f"🗓 <strong>{evt['title']}</strong> — {evt['date']}"
                        f"{' @ ' + evt['time_start'] if evt.get('time_start') else ''}"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
                with col_del:
                    if st.button("✕", key=f"del_evt_{i}", help="Remove"):
                        st.session_state["personal_events"].pop(i)
                        st.rerun()

    # ════════════════════════════════════════════════════════
    # RIGHT PANEL — the actual weekly view
    # ════════════════════════════════════════════════════════
    with col_right:
        # Week navigation
        nav_col1, nav_col2, nav_col3 = st.columns([1, 2, 1])
        with nav_col1:
            if st.button("◀ Prev week"):
                st.session_state["week_offset"] = st.session_state.get("week_offset", 0) - 1
        with nav_col3:
            if st.button("Next week ▶"):
                st.session_state["week_offset"] = st.session_state.get("week_offset", 0) + 1
        with nav_col2:
            if st.button("Today", use_container_width=True):
                st.session_state["week_offset"] = 0

        week_offset = st.session_state.get("week_offset", 0)

        # Build schedule
        courses = st.session_state.get("parsed_courses", [get_demo_course()])
        events  = st.session_state.get("campus_events", get_mock_roogroups_events())
        personal_events = st.session_state.get("personal_events", [])

        week = build_week_schedule(courses, events, week_offset, personal_events=personal_events)

        with nav_col2:
            st.markdown(
                f"<div style='text-align:center;font-size:13px;color:#6B7280;'>"
                f"{week['week_start']} — {week['week_end']}</div>",
                unsafe_allow_html=True,
            )

        today_str = datetime.now().date().strftime("%Y-%m-%d")

        # ── Legend ─────────────────────────────────────────
        legend_cols = st.columns(5)
        for i, (t, m) in enumerate(TYPE_META.items()):
            with legend_cols[i]:
                st.markdown(
                    f"<span style='border-left:3px solid {m['border']};padding-left:6px;"
                    f"font-size:12px;'>{m['emoji']} {m['label']}</span>",
                    unsafe_allow_html=True,
                )

        st.markdown("---")

        # ── Day columns (Mon–Fri on one row, then Sat/Sun) ─
        weekday_cols = st.columns(5)
        for i, day in enumerate(DAY_ORDER[:5]):
            items    = week["schedule"][day]
            day_date = (
                datetime.strptime(week["week_start"], "%Y-%m-%d").date()
            )
            from datetime import timedelta
            day_date = day_date + timedelta(days=i)
            is_today = day_date.strftime("%Y-%m-%d") == today_str

            with weekday_cols[i]:
                header_class = "today-marker" if is_today else ""
                today_label  = " ★" if is_today else ""
                st.markdown(
                    f"<div class='day-header {header_class}'>"
                    f"{day[:3].upper()}{today_label}<br>"
                    f"<span style='font-size:12px;font-weight:400;color:#9CA3AF;'>"
                    f"{day_date.strftime('%b %d')}</span></div>",
                    unsafe_allow_html=True,
                )

                if not items:
                    st.markdown(
                        "<div style='font-size:12px;color:#9CA3AF;padding:8px 0;'>No events</div>",
                        unsafe_allow_html=True,
                    )
                else:
                    # Free-gap hints
                    gaps = find_free_gaps(items)
                    for item in items:
                        loc      = item.get("location", "")
                        maps_url = make_google_maps_link(loc, user_lat, user_lng) if use_location else ""
                        st.markdown(_card_html(item, maps_url), unsafe_allow_html=True)

                    # Show free gaps as suggestions
                    if gaps:
                        st.markdown(
                            "<div style='font-size:11px;font-weight:600;color:#16A34A;"
                            "margin-top:8px;margin-bottom:4px;'>🕐 Free slots</div>",
                            unsafe_allow_html=True,
                        )
                        for g in gaps:
                            dur = g["duration_min"]
                            st.markdown(
                                f"<div class='gap-pill'>"
                                f"{g['gap_start']}–{g['gap_end']} "
                                f"<span style='font-weight:700;'>({dur} min)</span>"
                                f"</div>",
                                unsafe_allow_html=True,
                            )

        # Weekend row
        if any(week["schedule"][d] for d in ["Saturday", "Sunday"]):
            st.markdown("**Weekend**")
            wk_cols = st.columns(2)
            for i, day in enumerate(["Saturday", "Sunday"]):
                items    = week["schedule"][day]
                day_date = (
                    datetime.strptime(week["week_start"], "%Y-%m-%d").date()
                    + timedelta(days=5 + i)
                )
                with wk_cols[i]:
                    st.markdown(
                        f"<div class='day-header'>{day}<br>"
                        f"<span style='font-size:12px;font-weight:400;color:#9CA3AF;'>"
                        f"{day_date.strftime('%b %d')}</span></div>",
                        unsafe_allow_html=True,
                    )
                    for item in items:
                        maps_url = make_google_maps_link(
                            item.get("location", ""), user_lat, user_lng
                        ) if use_location else ""
                        st.markdown(_card_html(item, maps_url), unsafe_allow_html=True)

        # ── Events available during your free gaps ─────────
        st.markdown("---")
        st.subheader("💡 Events you can attend between classes")

        today     = datetime.now().date()
        today_day = DAY_ORDER[today.weekday()] if today.weekday() < 7 else None

        if today_day and today_day in week["schedule"]:
            today_items = week["schedule"][today_day]
            today_gaps  = find_free_gaps(today_items)
            campus_today = [
                e for e in today_items if e["type"] == "campus_event"
            ]

            if today_gaps and campus_today:
                for gap in today_gaps:
                    matching = []
                    for evt in campus_today:
                        t = evt.get("time_start", "")
                        if t and gap["gap_start"] <= t <= gap["gap_end"]:
                            matching.append(evt)
                    if matching:
                        st.markdown(
                            f"**Free {gap['gap_start']}–{gap['gap_end']} "
                            f"({gap['duration_min']} min):**"
                        )
                        for evt in matching:
                            loc      = evt.get("location", "")
                            maps_url = make_google_maps_link(loc, user_lat, user_lng) if use_location and loc else ""
                            nav_html = (
                                f'<a href="{maps_url}" target="_blank" style="'
                                f'font-size:12px;margin-left:8px;color:#2563EB;text-decoration:none;">'
                                f'🗺 Navigate</a>'
                            ) if maps_url else ""
                            st.markdown(
                                f"<div style='padding:6px 0;font-size:14px;'>"
                                f"🎉 <strong>{evt['title']}</strong> "
                                f"@ {evt.get('time_start','')} "
                                f"{'— ' + loc if loc else ''}"
                                f"{nav_html}</div>",
                                unsafe_allow_html=True,
                            )
                            if evt.get("description"):
                                st.caption(evt["description"])
            elif not campus_today:
                st.info("No campus events today. Check another day using the week navigator above!")
            else:
                st.info("No campus events fall within your free gaps today.")
        else:
            # Show summary for whole week
            all_events = [
                (day, e)
                for day in DAY_ORDER
                for e in week["schedule"][day]
                if e["type"] == "campus_event"
            ]
            if all_events:
                st.markdown("Here are all campus events this week:")
                for day, evt in all_events[:8]:
                    loc      = evt.get("location", "")
                    maps_url = make_google_maps_link(loc, user_lat, user_lng) if use_location and loc else ""
                    nav_html = (
                        f'<a href="{maps_url}" target="_blank" style="'
                        f'font-size:12px;margin-left:8px;color:#2563EB;text-decoration:none;">'
                        f'🗺 Navigate</a>'
                    ) if maps_url else ""
                    st.markdown(
                        f"<div style='padding:5px 0;font-size:14px;'>"
                        f"<span style='color:#6B7280;font-size:12px;'>{day}</span> &nbsp;"
                        f"🎉 <strong>{evt['title']}</strong> "
                        f"@ {evt.get('time_start','')} "
                        f"{'— ' + loc if loc else ''}"
                        f"{nav_html}</div>",
                        unsafe_allow_html=True,
                    )
            else:
                st.info("No campus events found this week.")
