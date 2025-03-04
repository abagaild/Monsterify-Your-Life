from core.database import db, fetch_one, execute_query

def get_currency(user_id: str) -> int:
    # Fetch currency_amount for the first trainer linked to this user_id
    row = fetch_one("SELECT currency_amount FROM trainers WHERE player_user_id = ? ORDER BY id LIMIT 1", (user_id,))
    if row is None:
        # No trainer found for this user_id; return 0 as default currency.
        return 0
    return row[0]

def add_currency(user_id: str, amount: int) -> int:
    # Retrieve the current balance for the first trainer of this user.
    row = fetch_one("SELECT id, currency_amount FROM trainers WHERE player_user_id = ? ORDER BY id LIMIT 1", (user_id,))
    if row is None:
        # No trainer to update; return 0 (no currency added).
        return 0
    trainer_id, current_balance = row[0], row[1]
    new_balance = current_balance + amount
    # Update that trainer's currency_amount in the database.
    execute_query("UPDATE trainers SET currency_amount = ? WHERE id = ?", (new_balance, trainer_id))
    return new_balance
