from core.database import cursor, db
from datetime import datetime

def add_habit(user_id: str, name: str, time: str = None, difficulty: str = "medium") -> None:
    cursor.execute(
        "INSERT INTO habits (user_id, habit_name, time, difficulty) VALUES (?, ?, ?, ?)",
        (user_id, name, time, difficulty)
    )
    db.commit()

def get_habits(user_id: str) -> list:
    cursor.execute("SELECT habit_name, time, difficulty, streak, last_completed FROM habits WHERE user_id = ?", (user_id,))
    rows = cursor.fetchall()
    return [{"name": row[0], "time": row[1], "difficulty": row[2], "streak": row[3], "last_completed": row[4]} for row in rows]

def delete_habit(user_id: str, habit_name: str) -> None:
    cursor.execute("DELETE FROM habits WHERE user_id = ? AND LOWER(habit_name) = ?", (user_id, habit_name.lower()))
    db.commit()

def complete_habit(user_id: str, habit_name: str) -> int:
    cursor.execute("SELECT id, streak, last_completed FROM habits WHERE user_id = ? AND LOWER(habit_name) = ?", (user_id, habit_name.lower()))
    row = cursor.fetchone()
    if row:
        new_streak = (row[1] or 0) + 1
        cursor.execute("UPDATE habits SET streak = ?, last_completed = ? WHERE id = ?", (new_streak, datetime.now().isoformat(), row[0]))
        db.commit()
        return new_streak
    return None

def reset_habits(user_id: str) -> None:
    cursor.execute("UPDATE habits SET last_completed = NULL WHERE user_id = ?", (user_id,))
    db.commit()

def increment_habit(user_id: str, habit_name: str) -> int:
    cursor.execute("SELECT streak FROM habits WHERE user_id = ? AND habit_name = ?", (user_id, habit_name))
    row = cursor.fetchone()
    if row is None:
        return None
    current_streak = row[0] or 0
    new_streak = current_streak + 1
    cursor.execute("UPDATE habits SET streak = ?, last_completed = ? WHERE user_id = ? AND habit_name = ?",
                   (new_streak, datetime.now().isoformat(), user_id, habit_name))
    db.commit()
    return new_streak
