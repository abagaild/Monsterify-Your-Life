from core.database import fetch_all, fetch_one, insert_record, update_record, remove_record, execute_query
from core.database import increment_garden_harvest
from datetime import datetime

def add_task(user_id: str, name: str, time: str = None, carryover: bool = False, difficulty: str = "medium") -> int:
    task = {
        "user_id": user_id,
        "task_name": name,
        "time": time,
        "difficulty": difficulty,
        "carryover": 1 if carryover else 0,
        "completed": 0,
        # The table uses default timestamps so these can be omitted if desired.
        "date_created": None,
        "date_completed": None
    }
    return insert_record("tasks", task)

def get_tasks(user_id: str) -> list:
    rows = fetch_all(
        "SELECT id, task_name, time, difficulty, carryover, completed FROM tasks WHERE user_id = ?",
        (user_id,)
    )
    return [
        {
            "id": row["id"],
            "name": row["task_name"],
            "time": row["time"],
            "difficulty": row["difficulty"],
            "carryover": bool(row["carryover"]),
            "completed": bool(row["completed"])
        } for row in rows
    ]

def delete_task(user_id: str, task_name: str) -> bool:
    row = fetch_one(
        "SELECT id FROM tasks WHERE user_id = ? AND LOWER(task_name) = ?",
        (user_id, task_name.lower())
    )
    if row:
        return remove_record("tasks", row["id"])
    return False

def complete_task(user_id: str, task_name: str) -> bool:
    row = fetch_one(
        "SELECT id, carryover FROM tasks WHERE user_id = ? AND LOWER(task_name) = ?",
        (user_id, task_name.lower())
    )
    if row:
        task_id = row["id"]
        if row["carryover"]:
            update_record("tasks", task_id, {
                "completed": 1,
                "date_completed": datetime.now().isoformat()
            })
        else:
            remove_record("tasks", task_id)
        increment_garden_harvest(user_id)
        return True
    return False

def reset_tasks(user_id: str) -> None:
    # For non-carryover tasks, delete them; for carryover tasks, reset their completed status.
    execute_query("DELETE FROM tasks WHERE user_id = ? AND carryover = 0", (user_id,))
    execute_query("UPDATE tasks SET completed = 0, date_completed = NULL WHERE user_id = ? AND carryover = 1", (user_id,))
