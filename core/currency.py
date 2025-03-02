from core.database import db

from core.database import fetch_one, execute_query

def get_currency(user_id: str) -> int:
    row = fetch_one("SELECT currency FROM users WHERE user_id = ?", (user_id,))
    if row is None:
        execute_query("INSERT INTO users (user_id, currency) VALUES (?, ?)", (user_id, 0))
        return 0
    return row[0]

def add_currency(user_id: str, amount: int) -> int:
    current = get_currency(user_id)
    new_balance = current + amount
    db.execute("UPDATE users SET currency = ? WHERE user_id = ?", (new_balance, user_id))
    return new_balance
