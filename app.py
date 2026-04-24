import streamlit as st
import sqlite3
import hashlib
import uuid
from datetime import datetime, date, timedelta
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
def hash_pw(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def is_in_range(task, target_date):
    start = datetime.fromisoformat(task["start"]).date()
    end = datetime.fromisoformat(task["end"]).date()
    return start <= target_date <= end

def format_range(t):
    s = datetime.fromisoformat(t["start"]).strftime("%Y/%m/%d %H:%M")
    e = datetime.fromisoformat(t["end"]).strftime("%Y/%m/%d %H:%M")
    return f"{s} → {e}"

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
# session
# =========================================================
if "user_id" not in st.session_state:
    st.session_state.user_id = None

if "selected_task_id" not in st.session_state:
    st.session_state.selected_task_id = None

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
                st.error("失敗")

    st.stop()

# =========================================================
# HEADER
# =========================================================
col_title, col_logout = st.columns([8, 1])

with col_title:
    st.title("📅 スケジュール管理")

with col_logout:
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
# カレンダー（左・複数日対応）
# =========================================================
with col_cal:
    st.subheader("📅 カレンダー")

    events = []
    for t in tasks:
        color = "#999999" if t["done"] else "#3788d8"

        events.append({
            "id": t["id"],
            "title": f"[{t['category']}] {t['title']}",
            "start": t["start"],
            "end": t["end"],
            "color": color
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
            },
            "buttonText": {
                "month": "月",
                "week": "週",
                "day": "日",
                "list": "一覧"
            }
        }
    )

# =========================================================
# タスク管理（右）
# =========================================================
with col_task:
    st.subheader("📋 タスク管理")

    selected_date = st.date_input("日付選択", date.today())

    filtered = [
        t for t in tasks
        if is_in_range(t, selected_date)
    ]

    st.markdown("### タスク一覧")

    for t in filtered:
        label = f"{'✅ ' if t['done'] else ''}{t['title']} ({format_range(t)})"

        col_name, col_done, col_del = st.columns([6, 2, 2])

        with col_name:
            if st.button(label, key=f"sel_{t['id']}"):
                st.session_state.selected_task_id = t["id"]

        with col_done:
            if not t["done"]:
                if st.button("✔", key=f"done_{t['id']}"):
                    mark_done(t["id"])
                    st.rerun()
            else:
                if st.button("↩", key=f"undo_{t['id']}"):
                    mark_undone(t["id"])
                    st.rerun()

        with col_del:
            if st.button("🗑", key=f"del_{t['id']}"):
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
    memo = st.text_area("メモ")
    category = st.text_input("カテゴリ", "未分類")

    d = st.date_input("日付", date.today())
    stime = st.time_input("開始", datetime.now().time())
    etime = st.time_input("終了", (datetime.now() + timedelta(hours=1)).time())

    if st.form_submit_button("追加"):
        task = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "title": title,
            "memo": memo,
            "category": category,
            "start": datetime.combine(d, stime).isoformat(),
            "end": datetime.combine(d, etime).isoformat(),
            "done": False
        }

        add_task(task)
        st.rerun()
