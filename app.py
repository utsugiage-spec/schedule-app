import streamlit as st
from datetime import datetime, date, timedelta
import sqlite3
import uuid
from streamlit_calendar import calendar

st.set_page_config(page_title="スケジュール管理", layout="wide")

st.title("📅 スケジュール管理アプリ（SQLite版）")

# =========================================================
# DB接続
# =========================================================
conn = sqlite3.connect("tasks.db", check_same_thread=False)
c = conn.cursor()

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
# ユーザー識別
# =========================================================
user_id = st.text_input("ユーザーIDを入力してください", value="guest")

# =========================================================
# DB操作関数
# =========================================================
def add_task(task):
    c.execute("""
        INSERT INTO tasks VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        task["id"],
        task["user_id"],
        task["title"],
        task["memo"],
        task["category"],
        task["start"],
        task["end"],
        int(task["done"])
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
# データ取得
# =========================================================
tasks = load_tasks(user_id)

# =========================================================
# カテゴリ色
# =========================================================
base_categories = ["仕事", "勉強", "プライベート", "未分類"]
all_categories = list(set(base_categories + [t["category"] for t in tasks]))

colors = ["#3788d8", "#e74c3c", "#2ecc71", "#f1c40f", "#9b59b6", "#1abc9c"]
category_color = {cat: colors[i % len(colors)] for i, cat in enumerate(all_categories)}

# =========================================================
# カレンダー
# =========================================================
events = []
for t in tasks:
    color = "#999999" if t["done"] else category_color.get(t["category"], "#3788d8")

    events.append({
        "id": t["id"],
        "title": f"[{t['category']}] {t['title']}",
        "start": t["start"],
        "end": t["end"],
        "color": color
    })

calendar(
    events=events,
    options={
        "locale": "ja",
        "headerToolbar": {
            "left": "prev,next",
            "center": "title",
            "right": "dayGridMonth,timeGridWeek,timeGridDay"
        }
    },
    key="calendar"
)

# =========================================================
# タスク一覧
# =========================================================
st.subheader("タスク一覧")

selected_date = st.date_input("日付選択", date.today())

day_tasks = [
    t for t in tasks
    if datetime.fromisoformat(t["start"]).date() == selected_date
]

active = [t for t in day_tasks if not t["done"]]
done = [t for t in day_tasks if t["done"]]

# ---------------- 未完了 ----------------
st.markdown("### 🟢 未完了")
for t in active:
    st.markdown(f"""
    **{t['title']}**  
    📂 {t['category']}  
    📝 {t['memo']}
    """)

    col1, col2 = st.columns(2)

    with col1:
        if st.button("✅ 完了", key=f"done_{t['id']}"):
            mark_done(t["id"])
            st.rerun()

    with col2:
        if st.button("🗑 削除", key=f"del_{t['id']}"):
            delete_task(t["id"])
            st.rerun()

    st.divider()

# ---------------- 完了（折りたたみ） ----------------
with st.expander("✅ 完了済みタスク"):
    for t in done:
        st.markdown(f"""
        **{t['title']}**  
        📂 {t['category']}
        """)

        col1, col2 = st.columns(2)

        with col1:
            if st.button("↩ 戻す", key=f"undo_{t['id']}"):
                mark_undone(t["id"])
                st.rerun()

        with col2:
            if st.button("🗑 削除", key=f"del2_{t['id']}"):
                delete_task(t["id"])
                st.rerun()

        st.divider()

# =========================================================
# タスク追加
# =========================================================
st.subheader("タスク追加")

with st.form("add_form"):
    title = st.text_input("タスク名")
    memo = st.text_area("メモ")

    category = st.text_input("カテゴリ", value="未分類")

    task_date = st.date_input("日付", date.today())
    start_time = st.time_input("開始時間", datetime.now().time())
    end_time = st.time_input("終了時間", (datetime.now() + timedelta(hours=1)).time())

    submitted = st.form_submit_button("追加")

    if submitted and title:
        task = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "title": title,
            "memo": memo,
            "category": category,
            "start": datetime.combine(task_date, start_time).isoformat(),
            "end": datetime.combine(task_date, end_time).isoformat(),
            "done": False
        }

        add_task(task)
        st.success("追加しました")
        st.rerun()
