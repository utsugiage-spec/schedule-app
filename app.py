import streamlit as st
import sqlite3
import hashlib
import uuid
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

def in_range(task, target_date):
    s = datetime.fromisoformat(task["start"]).date()
    e = datetime.fromisoformat(task["end"]).date()
    return s <= target_date <= e

def format_dt(dt):
    return datetime.fromisoformat(dt).strftime("%Y/%m/%d %H:%M")

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
# session
# =========================================================
if "user_id" not in st.session_state:
    st.session_state.user_id = None

if "selected_task_id" not in st.session_state:
    st.session_state.selected_task_id = None

if "custom_categories" not in st.session_state:
    st.session_state.custom_categories = []

if "memo_cache" not in st.session_state:
    st.session_state.memo_cache = ""

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
# タスク管理
# =========================================================
with col_task:
    st.subheader("📋 タスク管理")

    selected_date = st.date_input("日付選択", date.today())

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
# タスク追加（カテゴリ永続＋新規作成対応）
# =========================================================
st.divider()
st.subheader("➕ タスク追加（期間対応）")

with st.form("add"):

    # タイトル + ボタン
    col1, col2 = st.columns([4, 1])

    with col1:
        title = st.text_input("タイトル")

    with col2:
        submit = st.form_submit_button("追加")

    # 開始
    st.markdown("### 開始")
    col3, col4 = st.columns(2)

    with col3:
        sd = st.date_input("開始日", date.today())

    with col4:
        stt = st.time_input("開始時間", time(9, 0))

    # 終了
    st.markdown("### 終了")
    col5, col6 = st.columns(2)

    with col5:
        ed = st.date_input("終了日", date.today())

    with col6:
        ett = st.time_input("終了時間", time(10, 0))


st.markdown("### カテゴリ")

# ===============================
# 初期カテゴリ
# ===============================
base_categories = ["仕事", "学校", "趣味"]

# ===============================
# カスタムカテゴリ保存領域
# ===============================
if "custom_categories" not in st.session_state:
    st.session_state.custom_categories = []

if "new_category_input" not in st.session_state:
    st.session_state.new_category_input = ""

# ===============================
# 全カテゴリ
# ===============================
all_categories = base_categories + st.session_state.custom_categories
options = all_categories + ["＋新規作成"]

# ===============================
# セレクトボックス
# ===============================
category_mode = st.selectbox(
    "カテゴリ選択",
    options,
    key="category_select"
)

# ===============================
# 新規作成UI（ここが重要）
# ===============================
if category_mode == "＋新規作成":

    st.info("新しいカテゴリを入力してください")

    new_category = st.text_input(
        "カテゴリ名",
        key="new_category_input"
    )

    # まだ空なら仮置き
    category = new_category if new_category else "未分類"

    # 保存ボタン（明示的に確定させる）
    if st.button("カテゴリを追加"):
        if new_category and new_category not in st.session_state.custom_categories:
            st.session_state.custom_categories.append(new_category)
            st.success(f"カテゴリ「{new_category}」を追加しました")
            st.rerun()

else:
    category = category_mode

    # メモ（重要：保持）
    st.markdown("### メモ")
    memo = st.text_area("メモ", value=st.session_state.memo_cache)
    st.session_state.memo_cache = memo

    # submit
    if submit:

        # 新カテゴリ保存
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
