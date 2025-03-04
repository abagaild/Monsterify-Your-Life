from core.database import cursor, db, increment_garden_harvest

def add_task(user_id: str, name: str, time: str = None, carryover: bool = False, difficulty: str = "medium") -> None:
    cursor.execute(
        "INSERT INTO tasks (user_id, task_name, time, difficulty, carryover, completed) VALUES (?, ?, ?, ?, ?, 0)",
        (user_id, name, time, difficulty, int(carryover))
    )
    db.commit()

def get_tasks(user_id: str) -> list:
    cursor.execute("SELECT task_name, time, difficulty, carryover, completed FROM tasks WHERE user_id = ?", (user_id,))
    rows = cursor.fetchall()
    return [{"name": row[0], "time": row[1], "difficulty": row[2], "carryover": bool(row[3]), "completed": bool(row[4])} for row in rows]

def delete_task(user_id: str, task_name: str) -> None:
    cursor.execute("DELETE FROM tasks WHERE user_id = ? AND LOWER(task_name) = ?", (user_id, task_name.lower()))
    db.commit()

def complete_task(user_id: str, task_name: str) -> bool:
    cursor.execute("SELECT id, carryover FROM tasks WHERE user_id = ? AND LOWER(task_name) = ?", (user_id, task_name.lower()))
    row = cursor.fetchone()
    if row:
        if row[1]:
            cursor.execute("UPDATE tasks SET completed = 1 WHERE id = ?", (row[0],))
        else:
            cursor.execute("DELETE FROM tasks WHERE id = ?", (row[0],))
        db.commit()
        increment_garden_harvest(user_id)
        return True
    return False

def reset_tasks(user_id: str) -> None:
    cursor.execute("DELETE FROM tasks WHERE user_id = ? AND carryover = 0", (user_id,))
    cursor.execute("UPDATE tasks SET completed = 0 WHERE user_id = ? AND carryover = 1", (user_id,))
    db.commit()
