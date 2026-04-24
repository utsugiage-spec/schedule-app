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
JST = timezone(timedelta(hours=9))

def hash_pw(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def parse_date(date_str):
    return datetime.fromisoformat(date_str).replace(
        tzinfo=timezone.utc
    ).astimezone(JST).date()

def format_dt(dt):
    return datetime.fromisoformat(dt).strftime("%Y/%m/%d %H:%M")

def in_range(sch, target_date):
    s = datetime.fromisoformat(sch["start"]).date()
    e = datetime.fromisoformat(sch["end"]).date()
    return s <= target_date <= e

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
# schedules
# =========================================================
def add_schedule(s):
    c.execute("INSERT INTO schedules VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (
        s["id"], s["user_id"], s["title"],
        s["memo"], s["category"],
        s["start"], s["end"], int(s["done"])
    ))
    conn.commit()

def load_schedules(user_id):
    c.execute("SELECT * FROM schedules WHERE user_id=?", (user_id,))
    rows = c.fetchall()

    schedules = [
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

    return sorted(schedules, key=lambda x: x["start"])

def mark_done(id_):
    c.execute("UPDATE schedules SET done=1 WHERE id=?", (id_,))
    conn.commit()

def mark_undone(id_):
    c.execute("UPDATE schedules SET done=0 WHERE id=?", (id_,))
    conn.commit()

def delete_schedule(id_):
    c.execute("DELETE FROM schedules WHERE id=?", (id_,))
    conn.commit()

# =========================================================
# session
# =========================================================
if "user_id" not in st.session_state:
    st.session_state.user_id = None

if "selected_schedule_id" not in st.session_state:
    st.session_state.selected_schedule_id = None

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
        st.session_state.selected_schedule_id = None
        st.rerun()

# =========================================================
# DATA
# =========================================================
user_id = st.session_state.user_id
schedules = load_schedules(user_id)

# =========================================================
# LAYOUT
# =========================================================
col_cal, col_list = st.columns([3.5, 1.5])

# =========================================================
# カレンダー
# =========================================================
with col_cal:
    st.subheader("📅 スケジュールカレンダー")

    events = []

    # -------------------------
    # スケジュール
    # -------------------------
    for s in schedules:
        color = "#999999" if s["done"] else "#3788d8"

        events.append({
            "id": s["id"],
            "title": f"[{s['category']}] {s['title']}",
            "start": s["start"],
            "end": s["end"],
            "color": color
        })

    # -------------------------
    # 祝日のみ
    # -------------------------
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

    # -------------------------
    # 選択日ハイライト（必ず残す）
    # -------------------------
    selected = st.session_state.selected_date

    events.append({
        "id": "selected",
        "title": "📍選択中",
        "start": str(selected),
        "allDay": True,
        "color": "#ffd54f"
    })

    # -------------------------
    # カレンダー
    # -------------------------
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

    # -------------------------
    # クリック同期
    # -------------------------
    if cal_result and isinstance(cal_result, dict):
        if "dateClick" in cal_result:
            st.session_state.selected_date = parse_date(
                cal_result["dateClick"]["date"]
            )
            st.session_state.selected_schedule_id = None
            st.rerun()

# =========================================================
# スケジュール一覧
# =========================================================
with col_list:
    st.subheader("📋 スケジュール一覧")

    selected_date = st.date_input("日付選択", st.session_state.selected_date)

    if selected_date != st.session_state.selected_date:
        st.session_state.selected_date = selected_date
        st.session_state.selected_schedule_id = None

    filtered = [
        s for s in schedules
        if in_range(s, st.session_state.selected_date)
    ]

    if filtered and st.session_state.selected_schedule_id is None:
        st.session_state.selected_schedule_id = filtered[0]["id"]

    for s in filtered:
        label = f"{'✅ ' if s['done'] else ''}{s['title']}"

        c1, c2, c3 = st.columns([6, 2, 2])

        with c1:
            if st.button(label, key=f"sel_{s['id']}"):
                st.session_state.selected_schedule_id = s["id"]

        with c2:
            if not s["done"]:
                if st.button("✔", key=f"d_{s['id']}"):
                    mark_done(s["id"])
                    st.rerun()
            else:
                if st.button("↩", key=f"u_{s['id']}"):
                    mark_undone(s["id"])
                    st.rerun()

        with c3:
            if st.button("🗑", key=f"x_{s['id']}"):
                delete_schedule(s["id"])
                st.session_state.selected_schedule_id = None
                st.rerun()

    st.divider()

    st.subheader("📄 詳細")

    sel = next((x for x in schedules if x["id"] == st.session_state.selected_schedule_id), None)

    if sel:
        st.write(f"**タイトル:** {sel['title']}")
        st.write(f"**カテゴリ:** {sel['category']}")
        st.write(f"**メモ:** {sel['memo']}")
        st.write(f"**開始:** {format_dt(sel['start'])}")
        st.write(f"**終了:** {format_dt(sel['end'])}")
        st.write(f"**状態:** {'完了' if sel['done'] else '未完了'}")
    else:
        st.info("スケジュールを選択してください")

# =========================================================
# 追加
# =========================================================
st.divider()
st.subheader("➕ スケジュール追加")

with st.form("add"):

    title = st.text_input("スケジュール名")

    c1, c2 = st.columns(2)

    with c1:
        sd = st.date_input("開始日", st.session_state.selected_date)
    with c2:
        stt = st.time_input("開始時間", time(9, 0))

    c3, c4 = st.columns(2)

    with c3:
        ed = st.date_input("終了日", st.session_state.selected_date)
    with c4:
        ett = st.time_input("終了時間", time(10, 0))

base_categories = ["仕事", "学校", "趣味"]
options = base_categories + st.session_state.custom_categories + ["＋新規作成"]

cat_mode = st.selectbox("カテゴリ", options)

# =========================
# 新規作成が選ばれた場合
# =========================
if cat_mode == "＋新規作成":

    # 入力欄を必ず表示
    new_cat = st.text_input("新しいカテゴリ名を入力")

    category = new_cat if new_cat else "未分類"

else:
    category = cat_mode

    memo = st.text_area("メモ")

    submit = st.form_submit_button("追加")

    if submit:

        if category not in base_categories and category not in st.session_state.custom_categories:
            st.session_state.custom_categories.append(category)

        s = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "title": title,
            "memo": memo,
            "category": category,
            "start": datetime.combine(sd, stt).isoformat(),
            "end": datetime.combine(ed, ett).isoformat(),
            "done": False
        }

        add_schedule(s)
        st.rerun()
