from core.database import fetch_one, fetch_all, insert_record, update_record, remove_record, execute_query
from datetime import datetime

def add_habit(user_id: str, name: str, time: str = None, difficulty: str = "medium") -> int:
    habit = {
        "user_id": user_id,
        "habit_name": name,
        "time": time,
        "difficulty": difficulty,
        "streak": 0,
        "last_completed": None
    }
    return insert_record("habits", habit)

def get_habits(user_id: str) -> list:
    rows = fetch_all(
        "SELECT id, habit_name, time, difficulty, streak, last_completed FROM habits WHERE user_id = ?",
        (user_id,)
    )
    return [
        {
            "id": row["id"],
            "name": row["habit_name"],
            "time": row["time"],
            "difficulty": row["difficulty"],
            "streak": row["streak"],
            "last_completed": row["last_completed"]
        } for row in rows
    ]

def delete_habit(user_id: str, habit_name: str) -> bool:
    row = fetch_one(
        "SELECT id FROM habits WHERE user_id = ? AND LOWER(habit_name) = ?",
        (user_id, habit_name.lower())
    )
    if row:
        return remove_record("habits", row["id"])
    return False

def complete_habit(user_id: str, habit_name: str) -> int:
    row = fetch_one(
        "SELECT id, streak FROM habits WHERE user_id = ? AND LOWER(habit_name) = ?",
        (user_id, habit_name.lower())
    )
    if row:
        new_streak = (row["streak"] or 0) + 1
        update_record("habits", row["id"], {
            "streak": new_streak,
            "last_completed": datetime.now().isoformat()
        })
        return new_streak
    return None

def reset_habits(user_id: str) -> None:
    # Using the direct execute_query here is acceptable since this is a one-off update.
    execute_query("UPDATE habits SET last_completed = NULL WHERE user_id = ?", (user_id,))

def increment_habit(user_id: str, habit_name: str) -> int:
    row = fetch_one(
        "SELECT id, streak FROM habits WHERE user_id = ? AND habit_name = ?",
        (user_id, habit_name)
    )
    if not row:
        return None
    new_streak = (row["streak"] or 0) + 1
    update_record("habits", row["id"], {
        "streak": new_streak,
        "last_completed": datetime.now().isoformat()
    })
    return new_streak
