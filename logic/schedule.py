import datetime
from logic.habits import get_habits  # updated habits module
from logic.tasks import get_tasks   # updated tasks module

def build_schedule_message(user_id: str) -> str:
    habits = get_habits(user_id)
    tasks = get_tasks(user_id)
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
    from logic.tasks import reset_tasks
    from logic.habits import reset_habits
    from core.database import fetch_all
    users = fetch_all("SELECT DISTINCT player_user_id AS user_id FROM trainers")
    for user in users:
        reset_habits(user["user_id"])
        reset_tasks(user["user_id"])
