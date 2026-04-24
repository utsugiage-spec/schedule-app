import streamlit as st
import sqlite3
import hashlib
import uuid
import jpholiday
from datetime import datetime, date, time, timezone, timedelta
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
CREATE TABLE IF NOT EXISTS tasks (
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
JST = timezone(timedelta(hours=9))

def hash_pw(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def parse_date(date_str):
    return datetime.fromisoformat(date_str).replace(
        tzinfo=timezone.utc
    ).astimezone(JST).date()

def format_dt(dt):
    return datetime.fromisoformat(dt).strftime("%Y/%m/%d %H:%M")

def in_range(task, target_date):
    s = datetime.fromisoformat(task["start"]).date()
    e = datetime.fromisoformat(task["end"]).date()
    return s <= target_date <= e

def is_holiday_or_weekend(d: date):
    return d.weekday() >= 5 or jpholiday.is_holiday(d)

# =========================================================
# auth
# =========================================================
def register(username, password):
    try:
        c.execute("INSERT INTO users VALUES (?, ?, ?)", (
            str(uuid.uuid4()),
            username,
            hash_pw(password)
        ))
        conn.commit()
        return True
    except:
        return False

def login(username, password):
    c.execute("SELECT id, password_hash FROM users WHERE username=?", (username,))
    u = c.fetchone()

    if u and u[1] == hash_pw(password):
        return u[0]
    return None

# =========================================================
# tasks
# =========================================================
def add_task(task):
    c.execute("INSERT INTO tasks VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (
        task["id"], task["user_id"], task["title"],
        task["memo"], task["category"],
        task["start"], task["end"], int(task["done"])
    ))
    conn.commit()

def load_tasks(user_id):
    c.execute("SELECT * FROM tasks WHERE user_id=?", (user_id,))
    rows = c.fetchall()

    tasks = [
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

    return sorted(tasks, key=lambda t: t["start"])

def mark_done(task_id):
    c.execute("UPDATE tasks SET done=1 WHERE id=?", (task_id,))
    conn.commit()

def mark_undone(task_id):
    c.execute("UPDATE tasks SET done=0 WHERE id=?", (task_id,))
    conn.commit()

def delete_task(task_id):
    c.execute("DELETE FROM tasks WHERE id=?", (task_id,))
    conn.commit()

# =========================================================
# session state
# =========================================================
if "user_id" not in st.session_state:
    st.session_state.user_id = None

if "selected_task_id" not in st.session_state:
    st.session_state.selected_task_id = None

if "selected_date" not in st.session_state:
    st.session_state.selected_date = date.today()

if "custom_categories" not in st.session_state:
    st.session_state.custom_categories = []

# =========================================================
# LOGIN
# =========================================================
if st.session_state.user_id is None:

    st.title("🔐 スケジュール管理")

    mode = st.radio("選択", ["ログイン", "新規登録"])

    username = st.text_input("ユーザー名")
    password = st.text_input("パスワード", type="password")

    if mode == "ログイン":
        if st.button("ログイン"):
            uid = login(username, password)
            if uid:
                st.session_state.user_id = uid
                st.rerun()
            else:
                st.error("ログイン失敗")

    else:
        if st.button("登録"):
            if register(username, password):
                st.success("登録成功")
            else:
                st.error("登録失敗")

    st.stop()

# =========================================================
# HEADER
# =========================================================
col1, col2 = st.columns([8, 1])

with col1:
    st.title("📅 スケジュール管理")

with col2:
    if st.button("🚪 ログアウト"):
        st.session_state.user_id = None
        st.session_state.selected_task_id = None
        st.rerun()

# =========================================================
# DATA
# =========================================================
user_id = st.session_state.user_id
tasks = load_tasks(user_id)

# =========================================================
# LAYOUT
# =========================================================
col_cal, col_task = st.columns([3.5, 1.5])

# =========================================================
# カレンダー
# =========================================================
with col_cal:
    st.subheader("📅 カレンダー")

    events = []

    # --------------------------
    # タスク
    # --------------------------
    for t in tasks:
        color = "#999999" if t["done"] else "#3788d8"

        events.append({
            "id": t["id"],
            "title": f"[{t['category']}] {t['title']}",
            "start": t["start"],
            "end": t["end"],
            "color": color
        })

    # --------------------------
    # 土日祝ハイライト
    # --------------------------
    base = st.session_state.selected_date.replace(day=1)

    for i in range(31):
        try:
            d = base.replace(day=i + 1)
        except:
            break

        if is_holiday_or_weekend(d):

            events.append({
                "title": "",
                "start": str(d),
                "allDay": True,
                "color": "#ffe5e5"
            })

            if jpholiday.is_holiday(d):
                events.append({
                    "title": "🎌祝日",
                    "start": str(d),
                    "allDay": True,
                    "color": "#ffcccc"
                })

    # --------------------------
    # 選択日ハイライト（強調）
    # --------------------------
    selected = st.session_state.selected_date

    events.append({
        "title": "📍選択中",
        "start": str(selected),
        "allDay": True,
        "color": "#ffd966"
    })

    # --------------------------
    # カレンダー描画
    # --------------------------
    cal_result = calendar(
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

    # --------------------------
    # クリック即反映（重要）
    # --------------------------
    if cal_result and isinstance(cal_result, dict):
        if "dateClick" in cal_result:
            st.session_state.selected_date = parse_date(
                cal_result["dateClick"]["date"]
            )
            st.rerun()

# =========================================================
# タスク管理
# =========================================================
with col_task:
    st.subheader("📋 タスク管理")

    selected_date = st.date_input("日付選択", st.session_state.selected_date)
    st.session_state.selected_date = selected_date

    filtered = [
        t for t in tasks
        if in_range(t, selected_date)
    ]

    st.markdown("### タスク一覧")

    for t in filtered:
        label = f"{'✅ ' if t['done'] else ''}{t['title']}"

        col_a, col_b, col_c = st.columns([6, 2, 2])

        with col_a:
            if st.button(label, key=f"sel_{t['id']}"):
                st.session_state.selected_task_id = t["id"]

        with col_b:
            if not t["done"]:
                if st.button("✔", key=f"d_{t['id']}"):
                    mark_done(t["id"])
                    st.rerun()
            else:
                if st.button("↩", key=f"u_{t['id']}"):
                    mark_undone(t["id"])
                    st.rerun()

        with col_c:
            if st.button("🗑", key=f"x_{t['id']}"):
                delete_task(t["id"])
                st.session_state.selected_task_id = None
                st.rerun()

    st.divider()

    st.markdown("### 詳細")

    task = next((x for x in tasks if x["id"] == st.session_state.selected_task_id), None)

    if task:
        st.write(f"**タイトル:** {task['title']}")
        st.write(f"**カテゴリ:** {task['category']}")
        st.write(f"**メモ:** {task['memo']}")
        st.write(f"**開始:** {format_dt(task['start'])}")
        st.write(f"**終了:** {format_dt(task['end'])}")
        st.write(f"**状態:** {'完了' if task['done'] else '未完了'}")

    else:
        st.info("タスクを選択してください")

# =========================================================
# タスク追加
# =========================================================
st.divider()
st.subheader("➕ タスク追加")

with st.form("add"):

    title = st.text_input("タイトル")

    st.markdown("### 開始")
    c1, c2 = st.columns(2)

    with c1:
        sd = st.date_input("開始日", st.session_state.selected_date)
    with c2:
        stt = st.time_input("開始時間", time(9, 0))

    st.markdown("### 終了")
    c3, c4 = st.columns(2)

    with c3:
        ed = st.date_input("終了日", st.session_state.selected_date)
    with c4:
        ett = st.time_input("終了時間", time(10, 0))

    st.markdown("### カテゴリ")

    base_categories = ["仕事", "学校", "趣味"]
    options = base_categories + st.session_state.custom_categories + ["＋新規作成"]

    category_mode = st.selectbox("カテゴリ", options)

    if category_mode == "＋新規作成":
        category = st.text_input("新規カテゴリ", "未分類")
    else:
        category = category_mode

    memo = st.text_area("メモ")

    submit = st.form_submit_button("追加")

    if submit:

        if category not in base_categories and category not in st.session_state.custom_categories:
            st.session_state.custom_categories.append(category)

        task = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "title": title,
            "memo": memo,
            "category": category,
            "start": datetime.combine(sd, stt).isoformat(),
            "end": datetime.combine(ed, ett).isoformat(),
            "done": False
        }

        add_task(task)
        st.rerun()
