import streamlit as st
import sqlite3
import hashlib
import uuid
import jpholiday
from datetime import datetime, date, time
from streamlit_calendar import calendar

st.set_page_config(page_title="スケジュール管理", layout="wide")

# =========================================================
# DB
# =========================================================
conn = sqlite3.connect("app.db", check_same_thread=False)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    username TEXT UNIQUE,
    password_hash TEXT
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS schedules (
    id TEXT PRIMARY KEY,
    user_id TEXT,
    title TEXT,
    memo TEXT,
    category TEXT,
    start TEXT,
    end TEXT,
    done INTEGER
)
""")

conn.commit()

# =========================================================
# utils
# =========================================================
def hash_pw(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def parse_date(d):
    return datetime.fromisoformat(d).date()

def in_range(s, target):
    sd = datetime.fromisoformat(s["start"]).date()
    ed = datetime.fromisoformat(s["end"]).date()
    return sd <= target <= ed

# =========================================================
# auth
# =========================================================
def login(u, p):
    c.execute("SELECT id, password_hash FROM users WHERE username=?", (u,))
    r = c.fetchone()
    return r[0] if r and r[1] == hash_pw(p) else None

# =========================================================
# schedules
# =========================================================
def add_schedule(s):
    c.execute("INSERT INTO schedules VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (
        s["id"], s["user_id"], s["title"],
        s["memo"], s["category"],
        s["start"], s["end"], int(s["done"])
    ))
    conn.commit()

def load(uid):
    c.execute("SELECT * FROM schedules WHERE user_id=?", (uid,))
    rows = c.fetchall()

    return [
        {
            "id": r[0],
            "user_id": r[1],
            "title": r[2],
            "memo": r[3],
            "category": r[4],
            "start": r[5],
            "end": r[6],
            "done": bool(r[7])
        }
        for r in rows
    ]

# =========================================================
# session
# =========================================================
if "user_id" not in st.session_state:
    st.session_state.user_id = None

if "selected_date" not in st.session_state:
    st.session_state.selected_date = date.today()

if "selected_schedule_id" not in st.session_state:
    st.session_state.selected_schedule_id = None

if "custom_categories" not in st.session_state:
    st.session_state.custom_categories = []

# =========================================================
# LOGIN
# =========================================================
if st.session_state.user_id is None:

    st.title("ログイン")

    u = st.text_input("ユーザー")
    p = st.text_input("パスワード", type="password")

    if st.button("ログイン"):
        uid = login(u, p)
        if uid:
            st.session_state.user_id = uid
            st.rerun()

    st.stop()

# =========================================================
# HEADER
# =========================================================
col1, col2 = st.columns([8, 1])

with col1:
    st.title("📅 スケジュール管理")

with col2:
    if st.button("ログアウト"):
        st.session_state.user_id = None
        st.rerun()

# =========================================================
# DATA
# =========================================================
uid = st.session_state.user_id
schedules = load(uid)

# =========================================================
# LAYOUT
# =========================================================
col_cal, col_list = st.columns([3.5, 1.5])

# =========================================================
# カレンダー
# =========================================================
with col_cal:

    events = []

    for s in schedules:
        events.append({
            "id": s["id"],
            "title": f"[{s['category']}] {s['title']}",
            "start": s["start"],
            "end": s["end"],
            "color": "#999999" if s["done"] else "#3788d8"
        })

    events.append({
        "id": "selected",
        "title": "📍選択中",
        "start": str(st.session_state.selected_date),
        "allDay": True,
        "color": "#ffd54f"
    })

    calendar(
        events=events,
        key="cal",
        options={
            "locale": "ja",
            "initialView": "dayGridMonth",
            "height": 650,
            "headerToolbar": {
                "left": "prev,next",
                "center": "title",
                "right": "dayGridMonth,timeGridWeek,timeGridDay,listWeek"
            }
        }
    )

# =========================================================
# 一覧
# =========================================================
with col_list:

    st.subheader("一覧")

    selected = st.date_input("日付", st.session_state.selected_date)

    if selected != st.session_state.selected_date:
        st.session_state.selected_date = selected

    filtered = [s for s in schedules if in_range(s, selected)]

    for s in filtered:
        st.write(f"{s['title']} ({s['category']})")

# =========================================================
# 追加
# =========================================================
st.divider()
st.subheader("➕ スケジュール追加")

with st.form("add"):

    title = st.text_input("タイトル")

    sd = st.date_input("開始日", st.session_state.selected_date)
    stt = st.time_input("開始時間", time(9))

    ed = st.date_input("終了日", st.session_state.selected_date)
    ett = st.time_input("終了時間", time(10))

    base = ["仕事", "学校", "趣味"]
    options = base + st.session_state.custom_categories

    category = st.selectbox("カテゴリ", options)

    memo = st.text_area("メモ")

    submit = st.form_submit_button("追加")

    if submit:

        add_schedule({
            "id": str(uuid.uuid4()),
            "user_id": uid,
            "title": title,
            "memo": memo,
            "category": category,
            "start": datetime.combine(sd, stt).isoformat(),
            "end": datetime.combine(ed, ett).isoformat(),
            "done": False
        })

        st.rerun()
