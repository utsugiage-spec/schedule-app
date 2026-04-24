import json
import os
from datetime import datetime

FILE_PATH = "data/tasks.json"

def load_tasks():
    if not os.path.exists(FILE_PATH):
        return []
    with open(FILE_PATH, "r") as f:
        return json.load(f)

def save_tasks(tasks):
    # フォルダがなければ作る
    os.makedirs(os.path.dirname(FILE_PATH), exist_ok=True)

    with open(FILE_PATH, "w") as f:
        json.dump(tasks, f, indent=2)

def sort_tasks(tasks):
    return sorted(tasks, key=lambda x: x["datetime"])

def get_urgency_color(deadline):
    today = datetime.today().date()
    d = datetime.strptime(deadline, "%Y-%m-%d").date()
    diff = (d - today).days

    if diff <= 1:
        return "red"
    elif diff <= 3:
        return "orange"
    else:
        return "green"