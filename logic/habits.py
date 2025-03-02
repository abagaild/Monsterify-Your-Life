# logic/habits.py
from core.database import cursor, db, increment_task_habit_count

def add_habit(user_id: str, name: str, time: str = None, difficulty: str = "medium") -> None:
    """
    Adds a new habit for the user.
    """
    cursor.execute(
        "INSERT INTO habits (user_id, name, time, difficulty, completed, streak) VALUES (?, ?, ?, ?, 0, 0)",
        (user_id, name, time, difficulty)
    )
    db.commit()

def get_habits(user_id: str) -> list:
    """
    Retrieves all habits for a given user.
    """
    cursor.execute("SELECT name, time, difficulty, completed, streak FROM habits WHERE user_id = ?", (user_id,))
    rows = cursor.fetchall()
    return [{"name": row[0], "time": row[1], "difficulty": row[2], "completed": bool(row[3]), "streak": row[4]} for row in rows]

def delete_habit(user_id: str, habit_name: str) -> None:
    """
    Deletes a habit (case-insensitively) for the user.
    """
    cursor.execute("DELETE FROM habits WHERE user_id = ? AND LOWER(name) = ?", (user_id, habit_name.lower()))
    db.commit()

def complete_habit(user_id: str, habit_name: str) -> int:
    """
    Marks a habit as complete, increments its streak, and contributes to garden harvest progress.
    Returns the new streak if successful, otherwise returns None.
    """
    cursor.execute("SELECT id, streak, completed FROM habits WHERE user_id = ? AND LOWER(name) = ?", (user_id, habit_name.lower()))
    row = cursor.fetchone()
    if row and not row[2]:
        new_streak = row[1] + 1
        cursor.execute("UPDATE habits SET completed = 1, streak = ? WHERE id = ?", (new_streak, row[0]))
        db.commit()
        increment_task_habit_count(user_id)
        return new_streak
    return None

def reset_habits(user_id: str) -> None:
    """
    Resets all habits for the user (e.g. at midnight).
    """
    cursor.execute("UPDATE habits SET completed = 0 WHERE user_id = ?", (user_id,))
    db.commit()
