from core.database import execute_query, fetch_one
from datetime import datetime

def add_habit(user_id: str, name: str, time: str = None, difficulty: str = "medium") -> None:
    execute_query(
        "INSERT INTO habits (user_id, habit_name, time, difficulty) VALUES (?, ?, ?, ?)",
        (user_id, name, time, difficulty)
    )

def get_habits(user_id: str) -> list:
    rows = execute_query("SELECT habit_name, time, difficulty, streak, last_completed FROM habits WHERE user_id = ?", (user_id,)).fetchall()
    return [{"name": row["habit_name"], "time": row["time"], "difficulty": row["difficulty"], "streak": row["streak"], "last_completed": row["last_completed"]} for row in rows]

def delete_habit(user_id: str, habit_name: str) -> None:
    execute_query("DELETE FROM habits WHERE user_id = ? AND LOWER(habit_name) = ?", (user_id, habit_name.lower()))

def complete_habit(user_id: str, habit_name: str) -> int:
    row = fetch_one("SELECT id, streak, last_completed FROM habits WHERE user_id = ? AND LOWER(habit_name) = ?", (user_id, habit_name.lower()))
    if row:
        new_streak = (row["streak"] or 0) + 1
        execute_query("UPDATE habits SET streak = ?, last_completed = ? WHERE id = ?", (new_streak, datetime.now().isoformat(), row["id"]))
        return new_streak
    return None

def reset_habits(user_id: str) -> None:
    execute_query("UPDATE habits SET last_completed = NULL WHERE user_id = ?", (user_id,))

def increment_habit(user_id: str, habit_name: str) -> int:
    row = fetch_one("SELECT streak FROM habits WHERE user_id = ? AND habit_name = ?", (user_id, habit_name))
    if row is None:
        return None
    current_streak = row["streak"] or 0
    new_streak = current_streak + 1
    execute_query("UPDATE habits SET streak = ?, last_completed = ? WHERE user_id = ? AND habit_name = ?",
                   (new_streak, datetime.now().isoformat(), user_id, habit_name))
    return new_streak
