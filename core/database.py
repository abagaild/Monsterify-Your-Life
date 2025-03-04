import asyncio
import json
import logging
import sqlite3
import time

# Open (or create) the SQLite database.
db = sqlite3.connect("bot_data.db", check_same_thread=False)
cursor = db.cursor()


def create_tables():
    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS prompts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        Prompt TEXT,
        Difficulty TEXT,
        Bonus TEXT
    );

    CREATE TABLE IF NOT EXISTS users (
        user_id TEXT PRIMARY KEY,
        currency INTEGER DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS garden_harvest (
        user_id TEXT,
        amount INTEGER DEFAULT 0,
        last_claimed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (user_id)
    );

    CREATE TABLE IF NOT EXISTS boss (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        max_health INTEGER,
        current_health INTEGER,
        image_link TEXT,
        flavor_text TEXT,
        is_active INTEGER DEFAULT 1
    );

    CREATE TABLE IF NOT EXISTS boss_damage (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        boss_id INTEGER,
        user_id TEXT,
        damage INTEGER
    );

    CREATE TABLE IF NOT EXISTS missions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        flavor TEXT,
        requirements TEXT,
        item_rewards TEXT,
        mon_rewards BOOLEAN,
        mon_rewards_params TEXT,
        on_success TEXT,
        on_fail TEXT,
        difficulty INTEGER,
        ephemeral BOOLEAN,
        max_mons INTEGER
    );

    CREATE TABLE IF NOT EXISTS active_missions (
        user_id TEXT PRIMARY KEY,
        data TEXT
    );

    CREATE TABLE IF NOT EXISTS boss_rewards (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        boss_id INTEGER,
        user_id TEXT,
        levels INTEGER,
        coins INTEGER,
        claimed INTEGER DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS habits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        name TEXT NOT NULL,
        time TEXT DEFAULT NULL,
        difficulty TEXT DEFAULT 'medium',
        completed INTEGER DEFAULT 0,
        streak INTEGER DEFAULT 0,
        last_reset TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (user_id)
    );

    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        name TEXT NOT NULL,
        time TEXT DEFAULT NULL,
        difficulty TEXT DEFAULT 'medium',
        carryover INTEGER DEFAULT 0,
        completed INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (user_id)
    );

    CREATE TABLE IF NOT EXISTS trainers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        name TEXT,
        level INTEGER,
        img_link TEXT
    );

    CREATE TABLE IF NOT EXISTS mons (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        trainer_id INTEGER,
        player TEXT,
        mon_name TEXT,
        level INTEGER,
        species1 TEXT,
        species2 TEXT,
        species3 TEXT,
        type1 TEXT,
        type2 TEXT,
        type3 TEXT,
        type4 TEXT,
        type5 TEXT,
        attribute TEXT,
        img_link TEXT,
        FOREIGN KEY(trainer_id) REFERENCES trainers(id)
    );

    CREATE TABLE IF NOT EXISTS adventure_sessions (
        channel_id TEXT PRIMARY KEY,
        area_data TEXT,
        progress INTEGER DEFAULT 0,
        encounters_triggered INTEGER DEFAULT 0,
        hard_mode INTEGER DEFAULT 0,
        last_message_timestamp INTEGER,
        active INTEGER DEFAULT 1
    );
    """)
    db.commit()


create_tables()


# --- Generic Helpers ---
def execute_query(query, params=()):
    cursor.execute(query, params)
    db.commit()
    return cursor


def fetch_one(query, params=()):
    cursor.execute(query, params)
    return cursor.fetchone()


def fetch_all(query, params=()):
    cursor.execute(query, params)
    return cursor.fetchall()


# --- User Functions ---
def get_currency(user_id: str) -> int:
    row = fetch_one("SELECT currency FROM users WHERE user_id = ?", (user_id,))
    if row is None:
        execute_query("INSERT INTO users (user_id, currency) VALUES (?, ?)", (user_id, 0))
        return 0
    return row[0]


def add_currency(user_id: str, amount: int) -> int:
    current = get_currency(user_id)
    new_balance = current + amount
    execute_query("UPDATE users SET currency = ? WHERE user_id = ?", (new_balance, user_id))
    return new_balance


# --- Habit Functions ---
def add_habit_to_db(user_id: str, habit):
    """
    Expects 'habit' to have attributes: name, time, difficulty, streak.
    """
    execute_query(
        "INSERT INTO habits (user_id, name, time, difficulty, completed, streak) VALUES (?, ?, ?, ?, 0, ?)",
        (user_id, habit.name, habit.time, habit.difficulty, habit.streak)
    )


def get_habits_from_db(user_id: str):
    rows = fetch_all("SELECT name, time, difficulty, completed, streak FROM habits WHERE user_id = ?", (user_id,))
    return [{"name": row[0], "time": row[1], "difficulty": row[2], "completed": bool(row[3]), "streak": row[4]} for row
            in rows]


def delete_habit_from_db(user_id: str, habit_name: str):
    execute_query("DELETE FROM habits WHERE user_id = ? AND LOWER(name) = ?", (user_id, habit_name.lower()))


def complete_habit_in_db(user_id: str, habit_name: str):
    row = fetch_one("SELECT id, streak, completed FROM habits WHERE user_id = ? AND LOWER(name) = ?",
                    (user_id, habit_name.lower()))
    if row and not row[2]:
        new_streak = row[1] + 1
        execute_query("UPDATE habits SET completed = 1, streak = ? WHERE id = ?", (new_streak, row[0]))
        increment_task_habit_count(user_id)
        return new_streak
    return None


def reset_habits_for_user(user_id: str):
    execute_query("UPDATE habits SET completed = 0 WHERE user_id = ?", (user_id,))


# --- Task Functions ---
def add_task_to_db(user_id: str, task):
    """
    Expects 'task' to have attributes: name, time, difficulty, carryover.
    """
    execute_query(
        "INSERT INTO tasks (user_id, name, time, difficulty, carryover, completed) VALUES (?, ?, ?, ?, ?, 0)",
        (user_id, task.name, task.time, task.difficulty, int(task.carryover))
    )


def get_tasks_from_db(user_id: str):
    rows = fetch_all("SELECT name, time, difficulty, carryover, completed FROM tasks WHERE user_id = ?", (user_id,))
    return [{"name": row[0], "time": row[1], "difficulty": row[2], "carryover": bool(row[3]), "completed": bool(row[4])}
            for row in rows]


def delete_task_from_db(user_id: str, task_name: str):
    execute_query("DELETE FROM tasks WHERE user_id = ? AND LOWER(name) = ?", (user_id, task_name.lower()))


def complete_task_in_db(user_id: str, task_name: str) -> bool:
    row = fetch_one("SELECT id FROM tasks WHERE user_id = ? AND LOWER(name) = ?", (user_id, task_name.lower()))
    if row:
        execute_query("UPDATE tasks SET completed = 1 WHERE id = ?", (row[0],))
        return True
    return False


def reset_tasks_for_user(user_id: str):
    execute_query("DELETE FROM tasks WHERE user_id = ? AND carryover = 0", (user_id,))
    execute_query("UPDATE tasks SET completed = 0 WHERE user_id = ? AND carryover = 1", (user_id,))


def increment_task_habit_count(user_id: str):
    try:
        cursor.execute(
            "INSERT INTO garden_harvest (user_id, amount) VALUES (?, 1) ON CONFLICT(user_id) DO UPDATE SET amount = amount + 1",
            (user_id,)
        )
        db.commit()
    except Exception as e:
        print("Error incrementing task habit count:", e)


# --- Trainer Functions ---
def add_trainer_to_db(user_id: str, name: str, level: int, img_link: str):
    execute_query("INSERT INTO trainers (user_id, name, level, img_link) VALUES (?, ?, ?, ?)",
                  (user_id, name, level, img_link))


def get_trainers_from_db(user_id: str):
    rows = fetch_all("SELECT id, name, level, img_link FROM trainers WHERE user_id = ?", (user_id,))
    return [{"id": row[0], "name": row[1], "level": row[2], "img_link": row[3]} for row in rows]


def delete_trainer_from_db(user_id: str, trainer_name: str):
    execute_query("DELETE FROM trainers WHERE user_id = ? AND LOWER(name) = ?", (user_id, trainer_name.lower()))


def update_trainer_data(trainer_id: int, **kwargs):
    if not kwargs:
        return
    fields = []
    values = []
    for key, value in kwargs.items():
        fields.append(f"{key} = ?")
        values.append(value)
    values.append(trainer_id)
    query = "UPDATE trainers SET " + ", ".join(fields) + " WHERE id = ?"
    execute_query(query, tuple(values))


# --- Mon Functions ---
def add_mon_to_db(trainer_id: int, player: str, mon_name: str, level: int,
                  species1: str, species2: str, species3: str,
                  type1: str, type2: str, type3: str, type4: str, type5: str,
                  attribute: str, img_link: str = ""):
    execute_query(
        """
        INSERT INTO mons (
            trainer_id, player, mon_name, level, species1, species2, species3,
            type1, type2, type3, type4, type5, attribute, img_link
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (trainer_id, player, mon_name, level, species1, species2, species3,
         type1, type2, type3, type4, type5, attribute, img_link)
    )


def get_mons_for_trainer(trainer_id: int) -> list:
    cursor.execute("SELECT id, mon_name, level, player, img_link FROM mons WHERE trainer_id = ?", (trainer_id,))
    rows = cursor.fetchall()
    return [{
        "id": row[0],
        "mon_name": row[1],
        "level": row[2],
        "player": row[3],
        "img_link": row[4]
    } for row in rows]



def get_mons_from_db(user_id: str):
    rows = fetch_all(
        """
        SELECT m.id, t.name, m.mon_name, m.level, m.species1, m.species2, m.species3,
               m.type1, m.type2, m.type3, m.type4, m.type5, m.attribute, m.img_link 
        FROM mons m JOIN trainers t ON m.trainer_id = t.id 
        WHERE m.player = ?
        """, (user_id,)
    )
    return [{
        "id": row[0],
        "trainer": row[1],
        "mon_name": row[2],
        "level": row[3],
        "species1": row[4],
        "species2": row[5],
        "species3": row[6],
        "type1": row[7],
        "type2": row[8],
        "type3": row[9],
        "type4": row[10],
        "type5": row[11],
        "attribute": row[12],
        "img_link": row[13]
    } for row in rows]


def update_mon_data(mon_id: int, **kwargs):
    if not kwargs:
        return
    fields = []
    values = []
    for key, value in kwargs.items():
        fields.append(f"{key} = ?")
        values.append(value)
    values.append(mon_id)
    query = "UPDATE mons SET " + ", ".join(fields) + " WHERE id = ?"
    execute_query(query, tuple(values))


async def update_mon_in_db(mon_name: str, field: str, new_value: str, user_id: str) -> bool:
    """
    Updates a field in the mons table for the specified mon record.

    It updates the record where:
      - mon_name matches the provided mon_name (case-sensitive), and
      - player equals the provided user_id.

    Returns:
      True if the update is successful; False otherwise.
    """

    def _update():
        try:
            query = f"UPDATE mons SET {field} = ? WHERE mon_name = ? AND player = ?"
            cursor.execute(query, (new_value, mon_name, user_id))
            db.commit()
            return True
        except Exception as e:
            logging.error(f"Database update error for mon '{mon_name}', field '{field}': {e}")
            return False

    return await asyncio.to_thread(_update)

def save_session(session) -> None:
    """
    Saves a new adventure session in the database. If a session for the channel already exists,
    it is replaced with the new data.

    Parameters:
      session: An adventure session object with attributes:
          - channel: discord.TextChannel (use its id as the key)
          - area_data: dict (will be stored as a JSON string)
          - progress: int
          - encounters_triggered: int
          - hard_mode: bool (stored as 1 for True, 0 for False)
    """
    channel_id = str(session.channel.id)
    area_data_json = json.dumps(session.area_data)
    progress = session.progress
    encounters_triggered = session.encounters_triggered
    hard_mode = 1 if session.hard_mode else 0
    last_message_timestamp = int(time.time())
    active = 1  # session is active
    query = """
    INSERT OR REPLACE INTO adventure_sessions 
    (channel_id, area_data, progress, encounters_triggered, hard_mode, last_message_timestamp, active)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """
    cursor.execute(query, (channel_id, area_data_json, progress, encounters_triggered, hard_mode, last_message_timestamp, active))
    db.commit()

def update_session(session) -> None:
    """
    Updates an existing adventure session in the database with the current progress,
    number of encounters, and last message timestamp.

    Parameters:
      session: An adventure session object as described in save_session.
    """
    channel_id = str(session.channel.id)
    progress = session.progress
    encounters_triggered = session.encounters_triggered
    last_message_timestamp = int(time.time())
    query = """
    UPDATE adventure_sessions 
    SET progress = ?, encounters_triggered = ?, last_message_timestamp = ?
    WHERE channel_id = ?
    """
    cursor.execute(query, (progress, encounters_triggered, last_message_timestamp, channel_id))
    db.commit()

def delete_session(channel_id: str) -> None:
    """
    Deletes the adventure session for the given channel ID.

    Parameters:
      channel_id: The Discord channel ID (as a string) where the session is stored.
    """
    query = "DELETE FROM adventure_sessions WHERE channel_id = ?"
    cursor.execute(query, (channel_id,))
    db.commit()

def get_all_users() -> list:
    """
    Retrieves all users from the database.

    Returns:
        A list of dictionaries, each with the key 'user_id'.
    """
    cursor.execute("SELECT user_id FROM users")
    rows = cursor.fetchall()
    return [{"user_id": row[0]} for row in rows]


from core.database import cursor


def fetch_mon_from_db(mon_id: int) -> dict:
    """
    Retrieves a mon record from the database given its ID and returns it as a dictionary.

    Parameters:
      mon_id (int): The unique identifier of the mon.

    Returns:
      dict: A dictionary with keys "id", "trainer_id", "player", "mon_name",
            "species1", "species2", "species3", "type1", "type2", "type3", "type4", "type5",
            "attribute", "img_link". If the mon is not found, returns an empty dict.
    """
    query = """
    SELECT id, trainer_id, player, mon_name, species1, species2, species3,
           type1, type2, type3, type4, type5, attribute, img_link
    FROM mons
    WHERE id = ?
    """
    cursor.execute(query, (mon_id,))
    row = cursor.fetchone()
    if row:
        keys = ["id", "trainer_id", "player", "mon_name", "species1", "species2", "species3",
                "type1", "type2", "type3", "type4", "type5", "attribute", "img_link"]
        return dict(zip(keys, row))
    else:
        return {}
