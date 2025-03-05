from core.database import execute_query, fetch_all
from core.database import increment_garden_harvest

def add_task(user_id: str, name: str, time: str = None, carryover: bool = False, difficulty: str = "medium") -> None:
    execute_query(
        "INSERT INTO tasks (user_id, task_name, time, difficulty, carryover, completed) VALUES (?, ?, ?, ?, ?, 0)",
        (user_id, name, time, difficulty, int(carryover))
    )

def get_tasks(user_id: str) -> list:
    rows = fetch_all(
        "SELECT task_name, time, difficulty, carryover, completed FROM tasks WHERE user_id = ?",
        (user_id,)
    )
    return [
        {
            "name": row["task_name"],
            "time": row["time"],
            "difficulty": row["difficulty"],
            "carryover": bool(row["carryover"]),
            "completed": bool(row["completed"])
        } for row in rows
    ]

def delete_task(user_id: str, task_name: str) -> None:
    execute_query(
        "DELETE FROM tasks WHERE user_id = ? AND LOWER(task_name) = ?",
        (user_id, task_name.lower())
    )

def complete_task(user_id: str, task_name: str) -> bool:
    rows = fetch_all(
        "SELECT id, carryover FROM tasks WHERE user_id = ? AND LOWER(task_name) = ?",
        (user_id, task_name.lower())
    )
    if rows:
        task_id = rows[0]["id"]
        carryover = rows[0]["carryover"]
        if carryover:
            execute_query("UPDATE tasks SET completed = 1 WHERE id = ?", (task_id,))
        else:
            execute_query("DELETE FROM tasks WHERE id = ?", (task_id,))
        increment_garden_harvest(user_id)
        return True
    return False

def reset_tasks(user_id: str) -> None:
    execute_query("DELETE FROM tasks WHERE user_id = ? AND carryover = 0", (user_id,))
    execute_query("UPDATE tasks SET completed = 0 WHERE user_id = ? AND carryover = 1", (user_id,))
