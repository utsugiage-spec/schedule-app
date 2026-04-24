import streamlit as st
from datetime import datetime, date, timedelta
from utils import load_tasks, save_tasks
from streamlit_calendar import calendar
import uuid

st.set_page_config(page_title="スケジュール管理", layout="wide")

st.title("📅 スケジュール管理アプリ")

# ----------------------
# データ読み込み
# ----------------------
tasks = load_tasks()

updated = False
for t in tasks:
    if "id" not in t:
        t["id"] = str(uuid.uuid4())
        updated = True
    if "category" not in t:
        t["category"] = "未分類"
        updated = True
    if "done" not in t:
        t["done"] = False
        updated = True

if updated:
    save_tasks(tasks)

# ----------------------
# カテゴリ一覧
# ----------------------
base_categories = ["仕事", "勉強", "プライベート", "未分類"]
existing_categories = list(set([t["category"] for t in tasks]))
categories = list(set(base_categories + existing_categories))

# ----------------------
# カテゴリカラー
# ----------------------
color_palette = [
    "#3788d8", "#e74c3c", "#2ecc71",
    "#f1c40f", "#9b59b6", "#1abc9c"
]

category_colors = {}
for i, cat in enumerate(categories):
    category_colors[cat] = color_palette[i % len(color_palette)]

# ----------------------
# カレンダーイベント
# ----------------------
events = []
for t in tasks:
    if "start" in t:
        color = "#999999" if t["done"] else category_colors[t["category"]]

        events.append({
            "id": t["id"],
            "title": f"[{t['category']}] {t['title']}",
            "start": t["start"],
            "end": t["end"],
            "color": color
        })

# ----------------------
# レイアウト
# ----------------------
col1, col2 = st.columns([2,1])

# ----------------------
# カレンダー
# ----------------------
with col1:
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

# ----------------------
# 右：タスク表示
# ----------------------
with col2:
    st.subheader("タスク詳細")

    selected_date = st.date_input("日付を選択", date.today())

    active_tasks = []
    done_tasks = []

    for t in tasks:
        if "start" not in t:
            continue

        task_date = datetime.fromisoformat(t["start"]).date()

        if task_date == selected_date:
            if t["done"]:
                done_tasks.append(t)
            else:
                active_tasks.append(t)

    # ----------------------
    # 未完了タスク
    # ----------------------
    if active_tasks:
        st.markdown("### 🟢 未完了")

        for t in active_tasks:
            start = datetime.fromisoformat(t["start"])
            end = datetime.fromisoformat(t["end"])

            st.markdown(f"""
            ### {t['title']}
            📂 {t['category']}
            ⏰ {start.strftime('%H:%M')} - {end.strftime('%H:%M')}
            """)

            if st.button("✅ 完了", key=f"done_{t['id']}"):
                t["done"] = True
                save_tasks(tasks)
                st.rerun()

            # 編集
            with st.expander("編集"):
                new_title = st.text_input("タイトル", t["title"], key=f"title_{t['id']}")

                selected_cat = st.selectbox(
                    "カテゴリ選択",
                    categories,
                    index=categories.index(t["category"]),
                    key=f"cat_sel_{t['id']}"
                )

                new_cat = st.text_input("新しいカテゴリ", key=f"cat_new_{t['id']}")

                final_cat = new_cat if new_cat else selected_cat

                new_memo = st.text_area("メモ", t["memo"], key=f"memo_{t['id']}")

                if st.button("保存", key=f"save_{t['id']}"):
                    t["title"] = new_title
                    t["category"] = final_cat
                    t["memo"] = new_memo
                    save_tasks(tasks)
                    st.rerun()

            st.divider()
    else:
        st.info("未完了タスクはありません")

    # ----------------------
    # 完了タスク（折りたたみ）
    # ----------------------
    if done_tasks:
        with st.expander("✅ 完了済みタスク"):
            for t in done_tasks:
                start = datetime.fromisoformat(t["start"])
                end = datetime.fromisoformat(t["end"])

                st.markdown(f"""
                **{t['title']}**  
                📂 {t['category']}  
                ⏰ {start.strftime('%H:%M')} - {end.strftime('%H:%M')}
                """)

                if st.button("↩ 未完了に戻す", key=f"undo_{t['id']}"):
                    t["done"] = False
                    save_tasks(tasks)
                    st.rerun()

                st.divider()

# ----------------------
# タスク追加
# ----------------------
st.subheader("タスク追加")

if "start_time" not in st.session_state:
    now = datetime.now()
    st.session_state.start_time = (now + timedelta(minutes=30)).time()

if "end_time" not in st.session_state:
    now = datetime.now()
    st.session_state.end_time = (now + timedelta(hours=1)).time()

with st.form("task_form"):
    title = st.text_input("タスク名")
    task_date = st.date_input("日付", date.today())
    start_time = st.time_input("開始時間", key="start_time")
    end_time = st.time_input("終了時間", key="end_time")

    selected_cat = st.selectbox("カテゴリ選択", categories)
    new_cat = st.text_input("新しいカテゴリ")

    category = new_cat if new_cat else selected_cat

    memo = st.text_area("メモ")

    submitted = st.form_submit_button("追加")

    if submitted and title:
        tasks.append({
            "id": str(uuid.uuid4()),
            "title": title,
            "memo": memo,
            "category": category,
            "done": False,
            "start": datetime.combine(task_date, start_time).isoformat(),
            "end": datetime.combine(task_date, end_time).isoformat()
        })

        save_tasks(tasks)
        st.rerun()