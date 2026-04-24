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
# login
# =========================================================
if st.session_state.user_id is None:

    st.title("🔐 ログイン")

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
                st.error("失敗")

    else:
        if st.button("登録"):
            if register(username, password):
                st.success("登録成功")
            else:
                st.error("失敗")

    st.stop()

# =========================================================
# main
# =========================================================
user_id = st.session_state.user_id

st.title("📅 スケジュール管理")

if st.button("ログアウト"):
    st.session_state.user_id = None
    st.session_state.selected_task_id = None
    st.rerun()

tasks = load_tasks(user_id)

# =========================================================
# layout
# =========================================================
col_cal, col_task = st.columns([2, 3])

# =========================================================
# カレンダー（左）
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
            "headerToolbar": {
                "left": "prev,next today",
                "center": "title",
                "right": "dayGridMonth,timeGridWeek,timeGridDay,listWeek"
            },
            "buttonText": {
                "today": "今日",
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
        if datetime.fromisoformat(t["start"]).date() == selected_date
    ]

    st.markdown("### タスク一覧")

    for t in filtered:
        label = "✅ " + t["title"] if t["done"] else t["title"]

        if st.button(label, key=f"sel_{t['id']}"):
            st.session_state.selected_task_id = t["id"]

    st.divider()

    st.markdown("### 詳細")

    task = next((x for x in tasks if x["id"] == st.session_state.selected_task_id), None)

    if task:
        start = datetime.fromisoformat(task["start"]).strftime("%Y/%m/%d %H:%M")
        end = datetime.fromisoformat(task["end"]).strftime("%Y/%m/%d %H:%M")

        st.write(f"**タイトル:** {task['title']}")
        st.write(f"**カテゴリ:** {task['category']}")
        st.write(f"**メモ:** {task['memo']}")
        st.write(f"**開始:** {start}")
        st.write(f"**終了:** {end}")
        st.write(f"**状態:** {'完了' if task['done'] else '未完了'}")

        colA, colB = st.columns(2)

        with colA:
            if not task["done"]:
                if st.button("完了", key=f"d_{task['id']}"):
                    mark_done(task["id"])
                    st.rerun()
            else:
                if st.button("戻す", key=f"u_{task['id']}"):
                    mark_undone(task["id"])
                    st.rerun()

        with colB:
            if st.button("削除", key=f"x_{task['id']}"):
                delete_task(task["id"])
                st.session_state.selected_task_id = None
                st.rerun()

# =========================================================
# 追加
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
