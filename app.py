import streamlit as st
import sqlite3
import hashlib
import uuid
from datetime import datetime, date, time, timedelta
from streamlit_calendar import calendar

st.set_page_config(page_title="スケジュール管理", layout="wide")

# =========================================================
# DB接続
# =========================================================
conn = sqlite3.connect("app.db", check_same_thread=False)
c = conn.cursor()

# ユーザーテーブル
c.execute("""
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    username TEXT UNIQUE,
    password_hash TEXT
)
""")

# タスクテーブル
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
# セキュリティ（パスワードハッシュ）
# =========================================================
def hash_pw(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

# =========================================================
# ユーザー登録
# =========================================================
def register(username, password):
    try:
        c.execute(
            "INSERT INTO users VALUES (?, ?, ?)",
            (str(uuid.uuid4()), username, hash_pw(password))
        )
        conn.commit()
        return True
    except:
        return False

# =========================================================
# ログイン
# =========================================================
def login(username, password):
    c.execute(
        "SELECT id, password_hash FROM users WHERE username=?",
        (username,)
    )
    result = c.fetchone()

    if result and result[1] == hash_pw(password):
        return result[0]
    return None

# =========================================================
# タスク操作
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
# session_state（ログイン保持）
# =========================================================
if "user_id" not in st.session_state:
    st.session_state.user_id = None

# =========================================================
# ログイン画面
# =========================================================
if st.session_state.user_id is None:

    st.title("🔐 ログイン / 新規登録")

    mode = st.radio("選択", ["ログイン", "新規登録"])

    username = st.text_input("ユーザー名")
    password = st.text_input("パスワード", type="password")

    if mode == "ログイン":
        if st.button("ログイン"):
            uid = login(username, password)
            if uid:
                st.session_state.user_id = uid
                st.success("ログイン成功")
                st.rerun()
            else:
                st.error("ログイン失敗")

    else:
        if st.button("新規登録"):
            ok = register(username, password)
            if ok:
                st.success("登録成功 → ログインしてください")
            else:
                st.error("そのユーザー名は既に存在します")

    st.stop()

# =========================================================
# ログイン後
# =========================================================
user_id = st.session_state.user_id

st.title("📅 スケジュール管理アプリ")

if st.button("ログアウト"):
    st.session_state.user_id = None
    st.rerun()

tasks = load_tasks(user_id)

# =========================================================
# カレンダー
# =========================================================
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

calendar(events=events, key="cal")

# =========================================================
# タスク一覧
# =========================================================
st.subheader("タスク一覧")

for t in tasks:
    st.markdown(f"""
    **{t['title']}**  
    📂 {t['category']}  
    📝 {t['memo']}
    """)

    col1, col2, col3 = st.columns(3)

    with col1:
        if not t["done"]:
            if st.button("完了", key=f"done_{t['id']}"):
                mark_done(t["id"])
                st.rerun()
        else:
            if st.button("戻す", key=f"undo_{t['id']}"):
                mark_undone(t["id"])
                st.rerun()

    with col2:
        if st.button("削除", key=f"del_{t['id']}"):
            delete_task(t["id"])
            st.rerun()

# =========================================================
# タスク追加
# =========================================================
st.subheader("タスク追加")

with st.form("add"):
    title = st.text_input("タイトル")
    memo = st.text_area("メモ")
    category = st.text_input("カテゴリ", "未分類")

    d = st.date_input("日付", date.today())
    stime = st.time_input("開始", datetime.now().time())
    etime = st.time_input("終了", (datetime.now() + timedelta(hours=1)).time())

    submit = st.form_submit_button("追加")

    if submit and title:
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
        st.success("追加しました")
        st.rerun()

        add_task(task)
        st.success("追加しました")
        st.rerun()
