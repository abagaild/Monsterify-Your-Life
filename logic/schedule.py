# logic/schedule.py
import datetime

from core.database import get_tasks_from_db, get_habits_from_db


def build_schedule_message(user_id: str) -> str:
    """
    Aggregates tasks and habits for the user, sorts them by time (if provided),
    and returns a formatted schedule string.
    """
    habits = get_habits_from_db(user_id)
    tasks = get_tasks_from_db(user_id)
    combined = [("Habit", h) for h in habits] + [("Task", t) for t in tasks]

    def sort_key(item):
        time_str = item[1].get("time", "")
        if time_str and time_str.lower() != "none":
            try:
                return (0, datetime.datetime.strptime(time_str, "%H:%M").time())
            except:
                return (1, datetime.time.max)
        return (1, datetime.time.max)

    combined.sort(key=sort_key)
    if not combined:
        return "No tasks or habits in your schedule."
    lines = []
    for typ, entry in combined:
        time_val = entry.get("time", "No time")
        if typ == "Habit":
            lines.append(f"[Habit] {entry.get('name', 'Unnamed')} | Time: {time_val} | Streak: {entry.get('streak', 0)}")
        else:
            carry = "Yes" if entry.get("carryover") else "No"
            lines.append(f"[Task] {entry.get('name', 'Unnamed')} | Time: {time_val} | Carryover: {carry}")
    return "\n".join(lines)

def reset_daily_schedules() -> None:
    """
    Resets daily habits and tasks for all users (e.g., at midnight).
    """
    from core.database import reset_habits_for_user, reset_tasks_for_user, get_all_users
    users = get_all_users()
    for user in users:
        reset_habits_for_user(user["user_id"])
        reset_tasks_for_user(user["user_id"])
