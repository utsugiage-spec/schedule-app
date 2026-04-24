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

def format_dt(dt):
    return datetime.fromisoformat(dt).strftime("%Y/%m/%d %H:%M")

def in_range(s, target):
    sd = datetime.fromisoformat(s["start"]).date()
    ed = datetime.fromisoformat(s["end"]).date()
    return sd <= target <= ed

# =========================================================
# auth
# =========================================================
def register(u, p):
    try:
        c.execute("INSERT INTO users VALUES (?, ?, ?)", (str(uuid.uuid4()), u, hash_pw(p)))
        conn.commit()
        return True
    except:
        return False

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

def load_schedules(uid):
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

def mark_done(i):
    c.execute("UPDATE schedules SET done=1 WHERE id=?", (i,))
    conn.commit()

def mark_undone(i):
    c.execute("UPDATE schedules SET done=0 WHERE id=?", (i,))
    conn.commit()

def delete_schedule(i):
    c.execute("DELETE FROM schedules WHERE id=?", (i,))
    conn.commit()

# =========================================================
# session
# =========================================================
if "user_id" not in st.session_state:
    st.session_state.user_id = None

if "selected_date" not in st.session_state:
    st.session_state.selected_date = date.today()

if "selected_schedule_id" not in st.session_state:
    st.session_state.selected_schedule_id = None

# =========================================================
# LOGIN
# =========================================================
if st.session_state.user_id is None:

    st.title("📅 スケジュール管理")

    mode = st.radio("選択", ["ログイン", "新規登録"])

    u = st.text_input("ユーザー名")
    p = st.text_input("パスワード", type="password")

    if mode == "ログイン":
        if st.button("ログイン"):
            uid = login(u, p)
            if uid:
                st.session_state.user_id = uid
                st.rerun()
            else:
                st.error("失敗")

    else:
        if st.button("登録"):
            if register(u, p):
                st.success("登録完了")

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
schedules = load_schedules(uid)

# =========================================================
# LAYOUT
# =========================================================
col_cal, col_list = st.columns([3.5, 1.5])

# =========================================================
# カレンダー
# =========================================================
with col_cal:

    st.subheader("📅 カレンダー")

    events = []

    for s in schedules:
        color = "#999999" if s["done"] else "#3788d8"

        events.append({
            "id": s["id"],
            "title": f"[{s['category']}] {s['title']}",
            "start": s["start"],
            "end": s["end"],
            "color": color
        })

    # 祝日
    base = st.session_state.selected_date.replace(day=1)

    for i in range(31):
        try:
            d = base.replace(day=i + 1)
        except:
            break

        if jpholiday.is_holiday(d):
            events.append({
                "title": f"🎌{jpholiday.is_holiday_name(d)}",
                "start": str(d),
                "allDay": True,
                "color": "#ffcccc"
            })

    # 選択日
    events.append({
        "id": "selected",
        "title": "📍選択中",
        "start": str(st.session_state.selected_date),
        "allDay": True,
        "color": "#ffd54f"
    })

    cal = calendar(
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
            },
            "buttonText": {
                "month": "月",
                "week": "週",
                "day": "日",
                "list": "一覧"
            }
        }
    )

    # =====================================================
    # ⭐ 修正ポイント（1日ズレ解消）
    # =====================================================
    if cal and isinstance(cal, dict):
        if "dateClick" in cal:
            clicked = cal["dateClick"]["date"]

            # ← ここ重要：文字列をそのままdateへ
            st.session_state.selected_date = datetime.strptime(clicked, "%Y-%m-%d").date()

            st.session_state.selected_schedule_id = None
            st.rerun()

# =========================================================
# スケジュール一覧
# =========================================================
with col_list:

    st.subheader("📋 スケジュール一覧")

    selected = st.date_input("日付", st.session_state.selected_date)

    if selected != st.session_state.selected_date:
        st.session_state.selected_date = selected
        st.session_state.selected_schedule_id = None

    filtered = [s for s in schedules if in_range(s, selected)]

    for s in filtered:

        c1, c2, c3 = st.columns([6, 2, 2])

        with c1:
            if st.button(f"{'✅' if s['done'] else ''}{s['title']}", key=s["id"]):
                st.session_state.selected_schedule_id = s["id"]

        with c2:
            if not s["done"]:
                if st.button("✔", key=f"d{s['id']}"):
                    mark_done(s["id"])
                    st.rerun()
            else:
                if st.button("↩", key=f"u{s['id']}"):
                    mark_undone(s["id"])
                    st.rerun()

        with c3:
            if st.button("🗑", key=f"x{s['id']}"):
                delete_schedule(s["id"])
                st.session_state.selected_schedule_id = None
                st.rerun()

# =========================================================
# 詳細
# =========================================================
st.divider()
st.subheader("詳細")

sel = next((x for x in schedules if x["id"] == st.session_state.selected_schedule_id), None)

if sel:
    st.write(sel["title"])
    st.write(sel["category"])
    st.write(sel["memo"])
    st.write(format_dt(sel["start"]))
    st.write(format_dt(sel["end"]))

# =========================================================
# 追加
# =========================================================
st.divider()
st.subheader("➕ スケジュール追加")

with st.form("add"):

    title = st.text_input("タイトル")

    c1, c2 = st.columns(2)
    with c1:
        sd = st.date_input("開始日", st.session_state.selected_date)
    with c2:
        stt = st.time_input("開始時間", time(9))

    c3, c4 = st.columns(2)
    with c3:
        ed = st.date_input("終了日", st.session_state.selected_date)
    with c4:
        ett = st.time_input("終了時間", time(10))

    base = ["仕事", "学校", "趣味"]
    category = st.selectbox("カテゴリ", base)

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
