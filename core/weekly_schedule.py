"""
weekly_schedule.py — UMKC Weekly Schedule Engine
=================================================
Handles:
  - PDF syllabus parsing via Claude API
  - RooGroups event scraping (session-based login, with mock fallback)
  - Weekly schedule assembly + free-gap detection
  - Google Maps navigation link generation
"""

import json
import re
import base64
from datetime import datetime, timedelta
from typing import Optional
import requests
from bs4 import BeautifulSoup

# ── Lazy Claude client ─────────────────────────────────────────
def get_claude_client():
    import os
    import anthropic
    return anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))


# ══════════════════════════════════════════════════════════════
# SYLLABUS PARSING VIA CLAUDE API
# ══════════════════════════════════════════════════════════════

SYLLABUS_PROMPT = """You are a course schedule extraction assistant for UMKC students.

Analyze this course syllabus PDF and extract ALL structured information into JSON.

Return ONLY valid JSON (no markdown fences, no explanation) with this exact structure:
{
  "course_name": "string",
  "course_code": "string  e.g. CS 101",
  "instructor": "string",
  "location": "string  e.g. Flarsheim Hall 320",
  "meeting_times": [
    {"day": "Monday", "start": "10:00", "end": "11:15", "location": "Flarsheim Hall 320"}
  ],
  "semester_start": "YYYY-MM-DD or null",
  "semester_end": "YYYY-MM-DD or null",
  "assignments": [
    {
      "title": "string",
      "due_date": "YYYY-MM-DD or null",
      "due_time": "HH:MM or null",
      "type": "homework|exam|quiz|project|reading|other",
      "description": "brief description max 80 chars"
    }
  ],
  "exams": [
    {
      "title": "string",
      "date": "YYYY-MM-DD or null",
      "time": "HH:MM or null",
      "location": "string or null",
      "type": "midterm|final|quiz"
    }
  ],
  "weekly_topics": [
    {"week": 1, "dates": "Jan 13-17", "topic": "string"}
  ]
}

Be thorough — extract every single deadline, exam, assignment, and meeting time.
Dates must be YYYY-MM-DD. If a year is missing assume 2026.
If a field is unknown, use null.
"""


def parse_syllabus_pdf(pdf_bytes: bytes) -> dict:
    """Send PDF to Claude API, return structured schedule dict."""
    client = get_claude_client()
    pdf_b64 = base64.standard_b64encode(pdf_bytes).decode("utf-8")

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4000,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "document",
                    "source": {
                        "type": "base64",
                        "media_type": "application/pdf",
                        "data": pdf_b64,
                    },
                },
                {"type": "text", "text": SYLLABUS_PROMPT},
            ],
        }],
    )

    raw = response.content[0].text.strip()
    raw = re.sub(r"^```json\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    return json.loads(raw)


def get_demo_course() -> dict:
    """Demo course data used when no syllabus is uploaded."""
    today = datetime.now().date()
    monday = today - timedelta(days=today.weekday())

    def nd(offset):
        return (monday + timedelta(days=offset)).strftime("%Y-%m-%d")

    return {
        "course_name": "Introduction to Data Science",
        "course_code": "CS 5590",
        "instructor": "Dr. Sarah Chen",
        "location": "Flarsheim Hall 320",
        "meeting_times": [
            {"day": "Monday",    "start": "10:00", "end": "11:15", "location": "Flarsheim Hall 320"},
            {"day": "Wednesday", "start": "10:00", "end": "11:15", "location": "Flarsheim Hall 320"},
            {"day": "Friday",    "start": "14:00", "end": "15:15", "location": "Flarsheim Hall 460"},
        ],
        "semester_start": nd(0),
        "semester_end":   (monday + timedelta(weeks=16)).strftime("%Y-%m-%d"),
        "assignments": [
            {"title": "Homework 3 — Pandas DataFrames", "due_date": nd(1), "due_time": "23:59",
             "type": "homework", "description": "Chapters 4-5 exercises"},
            {"title": "Project Proposal Draft",         "due_date": nd(3), "due_time": "11:59",
             "type": "project",  "description": "1-page proposal for final project"},
            {"title": "Reading Quiz — Week 8",          "due_date": nd(4), "due_time": "10:00",
             "type": "quiz",     "description": "Online quiz on Canvas"},
        ],
        "exams": [
            {"title": "Midterm Exam", "date": nd(3), "time": "10:00",
             "location": "Flarsheim Hall 320", "type": "midterm"},
        ],
        "weekly_topics": [],
    }


# ══════════════════════════════════════════════════════════════
# MOCK ROOGROUPS EVENTS
# ══════════════════════════════════════════════════════════════

def get_mock_roogroups_events() -> list[dict]:
    """Realistic UMKC campus events for demo / offline use."""
    today  = datetime.now().date()
    monday = today - timedelta(days=today.weekday())

    def d(offset):
        return (monday + timedelta(days=offset)).strftime("%Y-%m-%d")

    return [
        {"title": "Roo's Den Coffee Hour",
         "date": d(0), "time_start": "09:00",
         "location": "Student Union, Room 204",
         "description": "Free coffee and networking. All majors welcome!", "source": "RooGroups"},
        {"title": "Resume Workshop — Career Services",
         "date": d(0), "time_start": "14:00",
         "location": "Haag Hall 114",
         "description": "Live resume feedback from career advisors. Walk-ins welcome.", "source": "RooGroups"},
        {"title": "International Student Lunch Mixer",
         "date": d(1), "time_start": "12:00",
         "location": "Student Union Ballroom",
         "description": "Meet international students and enjoy free lunch. Hosted by ISA.", "source": "RooGroups"},
        {"title": "UMKC Trivia Night",
         "date": d(1), "time_start": "19:00",
         "location": "The Roo Bar, Student Union",
         "description": "Team trivia with prizes. Form a team of up to 5 people.", "source": "RooGroups"},
        {"title": "Data Science Club — Weekly Meeting",
         "date": d(2), "time_start": "17:30",
         "location": "Flarsheim Hall 460",
         "description": "This week: intro to ML pipelines. All skill levels welcome.", "source": "RooGroups"},
        {"title": "Yoga & Mindfulness Session",
         "date": d(2), "time_start": "07:30",
         "location": "Recreation Center Studio B",
         "description": "Free morning yoga open to all students. Mats provided.", "source": "RooGroups"},
        {"title": "Spring Career Fair — Tech & Engineering",
         "date": d(3), "time_start": "10:00",
         "location": "Swinney Recreation Center",
         "description": "Meet 40+ employers. Bring resumes. Business casual attire.", "source": "RooGroups"},
        {"title": "Cooking Club: International Cuisine Night",
         "date": d(3), "time_start": "18:00",
         "location": "Student Union Kitchen, Room 110",
         "description": "Learn to cook dishes from around the world. Ingredients provided.", "source": "RooGroups"},
        {"title": "UMKC Symphony Orchestra — Open Rehearsal",
         "date": d(4), "time_start": "15:00",
         "location": "White Recital Hall",
         "description": "Free admission for students with UMKC ID.", "source": "RooGroups"},
        {"title": "Study Abroad Info Session",
         "date": d(4), "time_start": "13:00",
         "location": "Haag Hall 215",
         "description": "Learn about semester and summer study abroad opportunities.", "source": "RooGroups"},
        {"title": "Hackathon Kickoff — RooHacks 2026",
         "date": d(5), "time_start": "10:00",
         "location": "Flarsheim Hall Atrium",
         "description": "24-hour hackathon. Register online. Food and prizes provided.", "source": "RooGroups"},
        {"title": "UMKC Basketball — Go Roos!",
         "date": d(5), "time_start": "19:00",
         "location": "Municipal Auditorium",
         "description": "Free student tickets at the Athletic Office. Show UMKC ID.", "source": "RooGroups"},
    ]


# ══════════════════════════════════════════════════════════════
# ROOGROUPS LIVE SCRAPER
# ══════════════════════════════════════════════════════════════

ROOGROUPS_BASE = "https://roogroups.umkc.edu"
LOGIN_URL      = f"{ROOGROUPS_BASE}/home_login"
EVENTS_URL     = f"{ROOGROUPS_BASE}/web_app?id=24040&menu_id=56483&if=0&"


def roogroups_login(username: str, password: str) -> Optional[requests.Session]:
    """Attempt form-based login to RooGroups. Returns session or None."""
    session = requests.Session()
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
        )
    })
    try:
        resp = session.get(LOGIN_URL, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        form = soup.find("form")
        if not form:
            return None

        payload = {}
        for inp in form.find_all("input"):
            name = inp.get("name")
            if name:
                payload[name] = inp.get("value", "")

        for key in list(payload.keys()):
            kl = key.lower()
            if any(x in kl for x in ("user", "email", "login", "account")):
                payload[key] = username
            if "pass" in kl:
                payload[key] = password

        action = form.get("action", LOGIN_URL)
        if action.startswith("/"):
            action = ROOGROUPS_BASE + action

        login_resp = session.post(action, data=payload, timeout=10, allow_redirects=True)

        if (
            "logout"  in login_resp.text.lower()
            or "welcome" in login_resp.text.lower()
            or ("login" not in login_resp.url and login_resp.status_code == 200)
        ):
            return session
        return None
    except Exception:
        return None


def scrape_roogroups_events(session: requests.Session) -> list[dict]:
    """Scrape events from RooGroups after successful login."""
    try:
        resp = session.get(EVENTS_URL, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
    except Exception:
        return []

    events = []
    for card in soup.select(".event-card, .event-item, [class*='event']"):
        title_el = card.find(["h2", "h3", "h4"])
        if not title_el:
            continue
        date_el = card.find(class_=re.compile(r"date|time|when", re.I))
        loc_el  = card.find(class_=re.compile(r"location|venue|where", re.I))
        desc_el = card.find(class_=re.compile(r"desc|summary", re.I))
        raw     = date_el.get_text(strip=True) if date_el else ""
        events.append({
            "title":       title_el.get_text(strip=True),
            "date":        _parse_date(raw),
            "time_start":  _parse_time(raw),
            "location":    loc_el.get_text(strip=True) if loc_el else "",
            "description": desc_el.get_text(strip=True)[:200] if desc_el else "",
            "source":      "RooGroups",
        })
    return events


def _parse_date(text: str) -> Optional[str]:
    if not text:
        return None
    for fmt in ("%B %d, %Y", "%b %d, %Y", "%m/%d/%Y", "%Y-%m-%d", "%B %d %Y"):
        try:
            return datetime.strptime(text.strip()[:20], fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return None


def _parse_time(text: str) -> Optional[str]:
    m = re.search(r"\b(\d{1,2}):(\d{2})\s*(am|pm)?\b", text, re.I)
    if not m:
        return None
    h, mn = int(m.group(1)), int(m.group(2))
    mer = (m.group(3) or "").lower()
    if mer == "pm" and h != 12:
        h += 12
    if mer == "am" and h == 12:
        h = 0
    return f"{h:02d}:{mn:02d}"


# ══════════════════════════════════════════════════════════════
# SCHEDULE ASSEMBLY
# ══════════════════════════════════════════════════════════════

DAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def get_week_bounds(offset: int = 0):
    today  = datetime.now().date()
    monday = today - timedelta(days=today.weekday()) + timedelta(weeks=offset)
    sunday = monday + timedelta(days=6)
    return monday, sunday


def build_week_schedule(courses: list[dict], events: list[dict], week_offset: int = 0, personal_events: list[dict] = None) -> dict:
    monday, sunday = get_week_bounds(week_offset)
    schedule = {day: [] for day in DAY_ORDER}

    # 1. Recurring class meetings
    for course in courses:
        for mt in course.get("meeting_times", []):
            day = mt.get("day", "")
            if day not in schedule:
                continue
            day_idx      = DAY_ORDER.index(day)
            meeting_date = monday + timedelta(days=day_idx)
            s0 = course.get("semester_start")
            s1 = course.get("semester_end")
            try:
                if s0 and meeting_date < datetime.strptime(s0, "%Y-%m-%d").date():
                    continue
                if s1 and meeting_date > datetime.strptime(s1, "%Y-%m-%d").date():
                    continue
            except ValueError:
                pass
            schedule[day].append({
                "type":        "class",
                "title":       course.get("course_name", "Class"),
                "course_code": course.get("course_code", ""),
                "time_start":  mt.get("start", ""),
                "time_end":    mt.get("end", ""),
                "location":    mt.get("location") or course.get("location", ""),
                "date":        meeting_date.strftime("%Y-%m-%d"),
                "color":       "blue",
            })

    # 2. Assignments due this week
    for course in courses:
        for asgn in course.get("assignments", []):
            due = asgn.get("due_date")
            if not due:
                continue
            try:
                due_dt = datetime.strptime(due, "%Y-%m-%d").date()
            except ValueError:
                continue
            if not (monday <= due_dt <= sunday):
                continue
            day = DAY_ORDER[due_dt.weekday()]
            schedule[day].append({
                "type":        "deadline",
                "title":       asgn.get("title", "Assignment Due"),
                "course_code": course.get("course_code", ""),
                "time_start":  asgn.get("due_time") or "23:59",
                "time_end":    None,
                "location":    "",
                "date":        due,
                "description": asgn.get("description", ""),
                "color":       "amber",
            })

    # 3. Exams this week
    for course in courses:
        for exam in course.get("exams", []):
            edate = exam.get("date")
            if not edate:
                continue
            try:
                exam_dt = datetime.strptime(edate, "%Y-%m-%d").date()
            except ValueError:
                continue
            if not (monday <= exam_dt <= sunday):
                continue
            day = DAY_ORDER[exam_dt.weekday()]
            schedule[day].append({
                "type":        "exam",
                "title":       exam.get("title", "Exam"),
                "course_code": course.get("course_code", ""),
                "time_start":  exam.get("time") or "",
                "time_end":    None,
                "location":    exam.get("location") or course.get("location", ""),
                "date":        edate,
                "color":       "red",
            })

    # 4. Personal events this week (from user input)
    for event in (personal_events or []):
        edate = event.get("date")
        if not edate:
            continue
        try:
            evt_dt = datetime.strptime(edate, "%Y-%m-%d").date()
        except ValueError:
            continue
        if not (monday <= evt_dt <= sunday):
            continue
        day = DAY_ORDER[evt_dt.weekday()]
        schedule[day].append(event)

    # 5. Campus events this week
    for event in events:
        edate = event.get("date")
        if not edate:
            continue
        try:
            evt_dt = datetime.strptime(edate, "%Y-%m-%d").date()
        except ValueError:
            continue
        if not (monday <= evt_dt <= sunday):
            continue
        day = DAY_ORDER[evt_dt.weekday()]
        schedule[day].append({
            "type":        "campus_event",
            "title":       event.get("title", "Campus Event"),
            "time_start":  event.get("time_start", ""),
            "time_end":    None,
            "location":    event.get("location", ""),
            "date":        edate,
            "description": event.get("description", ""),
            "color":       "teal",
        })

    # Sort each day chronologically
    for day in schedule:
        schedule[day].sort(key=lambda x: x.get("time_start") or "99:99")

    return {
        "week_start": monday.strftime("%Y-%m-%d"),
        "week_end":   sunday.strftime("%Y-%m-%d"),
        "schedule":   schedule,
    }


def find_free_gaps(day_items: list[dict], min_gap_min: int = 30) -> list[dict]:
    """Return free time slots in a day within the 8am–8pm window."""
    blocks = []
    for item in day_items:
        ts = item.get("time_start")
        te = item.get("time_end")
        if ts:
            try:
                h, m  = map(int, ts.split(":"))
                start = h * 60 + m
                end   = start + 60
                if te:
                    h2, m2 = map(int, te.split(":"))
                    end = h2 * 60 + m2
                blocks.append((start, end))
            except ValueError:
                pass

    if not blocks:
        return []

    blocks.sort()
    gaps, prev = [], 8 * 60
    day_end = 20 * 60

    for start, end in blocks:
        if start - prev >= min_gap_min:
            gaps.append({
                "gap_start":    f"{prev // 60:02d}:{prev % 60:02d}",
                "gap_end":      f"{start // 60:02d}:{start % 60:02d}",
                "duration_min": start - prev,
            })
        prev = max(prev, end)

    if day_end - prev >= min_gap_min:
        gaps.append({
            "gap_start":    f"{prev // 60:02d}:{prev % 60:02d}",
            "gap_end":      f"{day_end // 60:02d}:{day_end % 60:02d}",
            "duration_min": day_end - prev,
        })

    return gaps


# ══════════════════════════════════════════════════════════════
# NAVIGATION — GOOGLE MAPS
# ══════════════════════════════════════════════════════════════

UMKC_BUILDINGS = {
    "flarsheim hall":            "5110 Rockhill Rd, Kansas City, MO 64110",
    "haag hall":                 "5120 Rockhill Rd, Kansas City, MO 64110",
    "student union":             "5235 Rockhill Rd, Kansas City, MO 64110",
    "miller nichols library":    "5100 Rockhill Rd, Kansas City, MO 64110",
    "scofield hall":             "5020 Rockhill Rd, Kansas City, MO 64110",
    "health sciences building":  "2464 Charlotte St, Kansas City, MO 64108",
    "white recital hall":        "4949 Cherry St, Kansas City, MO 64110",
    "swinney recreation center": "5030 Holmes St, Kansas City, MO 64110",
    "bloch school":              "5110 Cherry St, Kansas City, MO 64110",
    "municipal auditorium":      "301 W 13th St, Kansas City, MO 64105",
}


def make_google_maps_link(location: str, user_lat: float = None, user_lng: float = None) -> str:
    """Generate a Google Maps directions URL for a UMKC location."""
    if not location:
        return ""
    loc_lower = location.lower()
    resolved  = location
    for building, address in UMKC_BUILDINGS.items():
        if building in loc_lower:
            resolved = address
            break

    destination = requests.utils.quote(resolved)
    if user_lat and user_lng:
        return f"https://www.google.com/maps/dir/{user_lat},{user_lng}/{destination}"
    return f"https://www.google.com/maps/search/?api=1&query={destination}"


# ══════════════════════════════════════════════════════════════
# PERSONAL EVENT — NATURAL LANGUAGE PARSING
# ══════════════════════════════════════════════════════════════

PERSONAL_EVENT_PROMPT = """You are a calendar assistant. The user will describe a personal event in natural language (Chinese or English).

Extract the event details and return ONLY valid JSON (no markdown, no explanation):
{
  "title": "short event title (max 30 chars)",
  "date": "YYYY-MM-DD",
  "time_start": "HH:MM or null",
  "time_end": "HH:MM or null",
  "location": "location string or null",
  "description": "brief description or null",
  "type": "meeting|social|personal|reminder|other"
}

Rules:
- Today is """ + datetime.now().strftime("%Y-%m-%d") + """. Use this as reference for relative dates.
- If no year is mentioned, assume the closest upcoming date.
- If no time is mentioned, use null for time fields.
- For Chinese input: 明天=tomorrow, 后天=day after tomorrow, 上午=AM, 下午=PM, 晚上=evening(~19:00)
- title should be concise and descriptive, in the same language as the input
- Examples:
  Input: "4月5号有个会议" → {"title":"会议","date":"2026-04-05","time_start":null,...}
  Input: "March 21 going to Lee's place for dinner" → {"title":"Dinner at Lee's","date":"2026-03-21","time_start":"18:00",...}
  Input: "明天下午3点牙医预约" → {"title":"牙医预约","date":"...","time_start":"15:00",...}
"""


def parse_personal_event(user_input: str) -> dict:
    """
    Parse a natural language event description into a structured event dict.
    Supports both English and Chinese input.
    Returns a dict ready to be added to the schedule.
    """
    client = get_claude_client()

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=500,
        messages=[{
            "role": "user",
            "content": f"{PERSONAL_EVENT_PROMPT}\n\nUser input: {user_input}"
        }],
    )

    raw = response.content[0].text.strip()
    raw = re.sub(r"^```json\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    data = json.loads(raw)

    # Normalize into schedule item format
    return {
        "type":        "personal",
        "title":       data.get("title", user_input[:30]),
        "date":        data.get("date"),
        "time_start":  data.get("time_start"),
        "time_end":    data.get("time_end"),
        "location":    data.get("location") or "",
        "description": data.get("description") or "",
        "event_type":  data.get("type", "personal"),
        "color":       "purple",
        "source":      "personal",
    }
