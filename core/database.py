import sqlite3
import asyncio
import json
import logging
import queue
from datetime import date, datetime

import redis
import discord  # Used for interactions and type hints

# ----------------------------
# Setup Logging Configuration
# ----------------------------
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s [%(levelname)s] %(message)s')

# ----------------------------
# SQLite Connection Pool
# ----------------------------
class SQLitePool:
    def __init__(self, database, pool_size=5):
        self._pool = queue.Queue(maxsize=pool_size)
        self.database = database
        for _ in range(pool_size):
            conn = sqlite3.connect(self.database, check_same_thread=False)
            self._pool.put(conn)

    def get_connection(self):
        return self._pool.get()

    def return_connection(self, conn):
        self._pool.put(conn)

    def close_all(self):
        while not self._pool.empty():
            conn = self._pool.get()
            conn.close()

db = SQLitePool("dawn_and_dusk.db")
cursor = db.get_connection().cursor()

pool = SQLitePool("dawn_and_dusk.db", pool_size=5)

def notify_sheet_update(entity, entity_id, update_type, payload):
    try:
        query = """
            INSERT INTO sheet_update_requests (entity, entity_id, update_type, payload)
            VALUES (?, ?, ?, ?)
        """
        # Execute the query and capture the cursor to retrieve the update ID.
        cur = execute_query(query, (entity, entity_id, update_type, json.dumps(payload)))
        update_id = cur.lastrowid

        # Construct an update dictionary that mimics the redis message.
        update = {
            "id": update_id,
            "entity": entity,
            "entity_id": entity_id,
            "update_type": update_type,
            "payload": payload
        }

        # Directly process the update in a background thread.
        import threading
        from Google_Sheets.google_sheets_authentication import process_update_request, mark_update_processed

        def process_and_mark():
            process_update_request(update)
            mark_update_processed(update_id)

        threading.Thread(target=process_and_mark).start()
        logging.info("Directly processed sheet update: " + json.dumps(update))
    except Exception as e:
        logging.error(f"Error notifying sheet update: {e}")


# ----------------------------
# Create Tables
# ----------------------------
def create_tables():
    conn = pool.get_connection()
    try:
        cur = conn.cursor()
        cur.executescript(
            """
            CREATE TABLE IF NOT EXISTS trainers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player TEXT,
                player_user_id TEXT,
                character_name TEXT,
                nickname TEXT,
                species TEXT,
                faction TEXT,
                title TEXT,
                ribbon TEXT,
                species1 TEXT,
                species2 TEXT,
                species3 TEXT,
                type1 TEXT,
                type2 TEXT,
                type3 TEXT,
                type4 TEXT,
                type5 TEXT,
                type6 TEXT,
                alteration_level INTEGER,
                shiny INTEGER,        
                alpha INTEGER,        
                paradox INTEGER,      
                ability TEXT,
                nature TEXT,
                characteristic TEXT,
                fav_berry TEXT,
                fav_type1 TEXT,
                fav_type2 TEXT,
                fav_type3 TEXT,
                fav_type4 TEXT,
                fav_type5 TEXT,
                fav_type6 TEXT,
                gender TEXT,
                pronouns TEXT,
                sexuality TEXT,
                age INTEGER,
                birthday DATE,      
                height_cm REAL,
                height_ft INTEGER,
                height_in INTEGER,
                birthplace TEXT,
                residence TEXT,
                job TEXT,
                theme_song TEXT,
                label TEXT,
                other_profile TEXT,
                label2 TEXT,
                google_sheets_link TEXT,
                main_ref TEXT,
                main_ref_artist TEXT,
                tldr TEXT,
                long_bio TEXT,
                mega_evo TEXT,
                mega_main_reference TEXT,
                mega_artist TEXT,
                mega_type1 TEXT,
                mega_type2 TEXT,
                mega_type3 TEXT,
                mega_type4 TEXT,
                mega_type5 TEXT,
                mega_type6 TEXT,
                mega_ability TEXT,
                additional_ref1 TEXT,
                additional_ref1_artist TEXT,
                additional_ref2 TEXT,
                additional_ref2_artist TEXT,
                currency_amount INTEGER,
                level INTEGER,
                level_modifier INTEGER,
                badges_earned TEXT,             
                badge_amount INTEGER,
                frontier_badges_earned TEXT,    
                frontier_badges_amount INTEGER,
                contest_ribbons_earned TEXT,    
                mon_amount INTEGER,
                reference_amount INTEGER,
                reference_percent REAL,         
                inventory TEXT,                 
                achievements TEXT,              
                prompts TEXT,                   
                trainer_progression TEXT,
                img_link TEXT
            );
            CREATE TABLE IF NOT EXISTS mons (
                mon_id INTEGER PRIMARY KEY AUTOINCREMENT,
                trainer_id INTEGER,
                player_user_id TEXT,
                name TEXT,
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
                box_img_link TEXT,
                mon_trainer_number INTEGER,
                hp_total INTEGER,
                hp_ev INTEGER,
                hp_iv INTEGER,
                atk_total INTEGER,
                atk_ev INTEGER,
                atk_iv INTEGER,
                def_total INTEGER,
                def_ev INTEGER,
                def_iv INTEGER,
                spa_total INTEGER,
                spa_ev INTEGER,
                spa_iv INTEGER,
                spd_total INTEGER,
                spd_ev INTEGER,
                spd_iv INTEGER,
                spe_total INTEGER,
                spe_ev INTEGER,
                spe_iv INTEGER,
                acquired TEXT,
                poke_ball TEXT,
                talk TEXT,
                shiny INTEGER,
                alpha INTEGER,
                shadow INTEGER,
                paradox INTEGER,
                paradox_type TEXT,
                fused INTEGER,
                pokerus INTEGER,
                moveset TEXT,
                mega_stone TEXT,
                mega_image TEXT,
                mega_type1 TEXT,
                mega_type2 TEXT,
                mega_type3 TEXT,
                mega_type4 TEXT,
                mega_type5 TEXT,
                mega_type6 TEXT,
                mega_ability TEXT,
                mega_stat_bonus INTEGER,
                friendship INTEGER,
                gender TEXT,
                pronouns TEXT,
                nature TEXT,
                characteristic TEXT,
                fav_berry TEXT,
                held_item TEXT,
                seal TEXT,
                mark TEXT,
                date_met TEXT,
                where_met TEXT,
                talking TEXT,
                height_m REAL,
                height_imperial TEXT,
                tldr TEXT,
                bio TEXT,
                og_trainer_id INTEGER,
                og_trainer_name TEXT,
                box_number INTEGER
            );
            CREATE TABLE IF NOT EXISTS sheet_update_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT NOT NULL,
                payload TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                attempts INTEGER NOT NULL DEFAULT 0,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                processed_at TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS sheet_update_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity TEXT NOT NULL,
                entity_id INTEGER NOT NULL,
                update_type TEXT NOT NULL,
                payload TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                attempts INTEGER NOT NULL DEFAULT 0,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                processed_at TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS habits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                habit_name TEXT NOT NULL,
                time TEXT,
                difficulty TEXT DEFAULT 'medium',
                streak INTEGER DEFAULT 0,
                last_completed DATETIME
            );
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                task_name TEXT NOT NULL,
                time TEXT,
                carryover INTEGER DEFAULT 0,
                difficulty TEXT DEFAULT 'medium',
                completed INTEGER DEFAULT 0,
                date_created DATETIME DEFAULT CURRENT_TIMESTAMP,
                date_completed DATETIME
            );
            CREATE TABLE IF NOT EXISTS schedules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                entry_text TEXT NOT NULL,
                schedule_date DATE DEFAULT CURRENT_DATE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS garden_harvest (
                user_id TEXT PRIMARY KEY,
                amount INTEGER DEFAULT 0,
                last_claimed TEXT
            );
            """
        )
        conn.commit()
        logging.info("Tables created successfully.")
    except Exception as e:
        logging.exception("Error creating tables")
        conn.rollback()
        raise
    finally:
        pool.return_connection(conn)


# ----------------------------
# Generic Database Helpers
# ----------------------------
def execute_query(query, params=()):
    conn = pool.get_connection()
    try:
        cur = conn.cursor()
        cur.execute(query, params)
        conn.commit()
        return cur
    except Exception as e:
        conn.rollback()
        logging.exception("Error executing query: %s", query)
        raise
    finally:
        pool.return_connection(conn)


def fetch_one(query, params=()):
    conn = pool.get_connection()
    try:
        conn.row_factory = sqlite3.Row  # Enable name-based access if needed
        cur = conn.cursor()
        cur.execute(query, params)
        return cur.fetchone()
    except Exception as e:
        logging.exception("Error fetching one: %s", query)
        raise
    finally:
        pool.return_connection(conn)


def fetch_all(query, params=()):
    conn = pool.get_connection()
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(query, params)
        return cur.fetchall()
    except Exception as e:
        logging.exception("Error fetching all: %s", query)
        raise
    finally:
        pool.return_connection(conn)


# ----------------------------
# Messaging Integration (Redis)
# ----------------------------
# (notify_sheet_update is defined above and used in update functions)

# ----------------------------
# Trainer Update Functions
# ----------------------------
def fetch_trainer_by_name(trainer_name: str) -> dict:
    """
    Fetch a trainer's record by character_name (case-insensitive).
    Returns a dictionary with keys: id, user_id, character_name, level, inventory, and img_link.
    """
    query = """
        SELECT id, player_user_id, character_name, level, inventory, img_link
        FROM trainers
        WHERE LOWER(character_name) = ?
    """
    row = fetch_one(query, (trainer_name.lower(),))
    if row:
        return {
            "id": row["id"],
            "user_id": row["player_user_id"],
            "character_name": row["character_name"],
            "level": row["level"],
            "inventory": row["inventory"] if row["inventory"] is not None else "{}",
            "img_link": row["img_link"]
        }
    return None


def update_trainer_field(trainer_id: int, field: str, new_value):
    """
    Updates a single field for a trainer record and notifies the sheet updater.
    """
    query = f"UPDATE trainers SET {field} = ? WHERE id = ?"
    execute_query(query, (new_value, trainer_id))
    notify_sheet_update("trainer", trainer_id, f"trainer_{field}_update", {field: new_value})


def update_trainer_level(trainer_id: int, new_level: int):
    return update_trainer_field(trainer_id, "level", new_level)


def update_trainer_currency(trainer_id: int, new_currency: int):
    return update_trainer_field(trainer_id, "currency_amount", new_currency)


def update_trainer_mon_amount(trainer_id: int, new_mon_amount: int):
    return update_trainer_field(trainer_id, "mon_amount", new_mon_amount)


def update_trainer_reference_amount(trainer_id: int, new_reference_amount: int):
    return update_trainer_field(trainer_id, "reference_amount", new_reference_amount)


# ----------------------------
# Mon Update Functions
# ----------------------------
def fetch_mon_by_name(trainer_name: str, name: str) -> dict:
    """
    Fetch a mon's record given the trainer's character_name and the mon's name (case-insensitive).
    """
    trainer = fetch_trainer_by_name(trainer_name)
    if trainer is None:
        return None
    query = """
        SELECT mon_id, name, level, player_user_id, img_link
        FROM mons
        WHERE trainer_id = ? AND LOWER(name) = ?
    """
    row = fetch_one(query, (trainer["id"], name.lower()))
    if row:
        return {
            "id": row["mon_id"],
            "name": row["name"],
            "level": row["level"],
            "player_user_id": row["player_user_id"],
            "img_link": row["img_link"]
        }
    return None


def update_mon_row(mon_id: int, updated_fields: dict):
    """
    Updates specified fields for a mon record and notifies the sheet updater.
    """
    if not updated_fields:
        return
    fields = []
    values = []
    for key, value in updated_fields.items():
        fields.append(f"{key} = ?")
        values.append(value)
    values.append(mon_id)
    query = "UPDATE mons SET " + ", ".join(fields) + " WHERE mon_id = ?"
    execute_query(query, tuple(values))
    notify_sheet_update("mon", mon_id, "mon_update", updated_fields)


def update_mon_level(mon_id: int, new_level: int):
    return update_mon_row(mon_id, {"level": new_level})


def update_name(mon_id: int, new_name: str):
    """
    Updates the mon's display name.
    """
    return update_mon_row(mon_id, {"name": new_name})


def update_mon_species_and_type(mon_id: int, new_species_list: list, new_types_list: list, new_attribute: str = None):
    """
    Updates a mon's species (up to three) and types (up to five). Optionally updates the attribute.
    """
    update_fields = {}
    for i in range(3):
        key = f"species{i + 1}"
        update_fields[key] = new_species_list[i] if i < len(new_species_list) else ""
    for i in range(5):
        key = f"type{i + 1}"
        update_fields[key] = new_types_list[i] if i < len(new_types_list) else ""
    if new_attribute is not None:
        update_fields["attribute"] = new_attribute
    return update_mon_row(mon_id, update_fields)


def add_mon(trainer_id: int, player: str, name: str, level: int,
            species1: str, species2: str, species3: str,
            type1: str, type2: str, type3: str, type4: str, type5: str,
            attribute: str, img_link: str = "") -> int:
    """
    Inserts a new mon into the database.
    Returns the newly created mon's ID.
    """
    conn = pool.get_connection()
    try:
        query = """
        INSERT INTO mons (
            trainer_id, player_user_id, name, level, 
            species1, species2, species3,
            type1, type2, type3, type4, type5,
            attribute, img_link
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        cur = conn.cursor()
        cur.execute(query, (trainer_id, player, name, level,
                            species1, species2, species3,
                            type1, type2, type3, type4, type5,
                            attribute, img_link))
        conn.commit()
        mon_id = cur.lastrowid
        notify_sheet_update("mon", mon_id, "mon_added", {
            "trainer_id": trainer_id,
            "player": player,
            "name": name,
            "level": level
        })
        return mon_id
    except Exception as e:
        conn.rollback()
        logging.exception("Error adding mon")
        raise
    finally:
        pool.return_connection(conn)


def remove_mon(mon_id: int) -> bool:
    """
    Removes a mon record from the database by its ID.
    """
    try:
        execute_query("DELETE FROM mons WHERE mon_id = ?", (mon_id,))
        notify_sheet_update("mon", mon_id, "mon_removed", {"mon_id": mon_id})
        return True
    except Exception as e:
        logging.error("Error removing mon (ID %s): %s", mon_id, e)
        return False


def update_mon_data(mon_id: int, **kwargs) -> bool:
    """
    Updates the specified fields for a mon record.
    Returns True if successful, False otherwise.
    """
    try:
        if not kwargs:
            return True
        fields = []
        values = []
        for key, value in kwargs.items():
            fields.append(f"{key} = ?")
            values.append(value)
        values.append(mon_id)
        query = "UPDATE mons SET " + ", ".join(fields) + " WHERE mon_id = ?"
        execute_query(query, tuple(values))
        notify_sheet_update("mon", mon_id, "mon_data_update", kwargs)
        return True
    except Exception as e:
        logging.error("Error updating mon data: %s", e)
        return False


async def update_mon_img_link(trainer_name: str, name: str, new_img_link: str) -> bool:
    """
    Updates the img_link column for a mon (identified by trainer's character_name and mon name).
    Returns True if the update is successful.
    """
    try:
        mon_record = fetch_mon_by_name(trainer_name, name)
        if mon_record is None:
            logging.error(f"Mon '{name}' for trainer '{trainer_name}' not found.")
            return False
        mon_id = mon_record["id"]
        update_mon_row(mon_id, {"img_link": new_img_link})
        return True
    except Exception as e:
        logging.error("Error updating mon image link: %s", e)
        return False


# ----------------------------
# Currency Helpers
# ----------------------------
from core.currency import get_currency, add_currency


def add_currency_to_player(user_id: str, amount: int) -> int:
    """
    Adds the given amount of currency to the player's balance.
    """
    return add_currency(user_id, amount)


def remove_currency_from_player(user_id: str, amount: int) -> int:
    """
    Removes the given amount of currency from the player's balance.
    """
    return add_currency(user_id, -amount)


# ----------------------------
# Log Sheet Helpers
# ----------------------------
async def update_character_sheet_item(trainer_name: str, item_name: str, quantity: int) -> bool:
    """
    Updates a trainer's inventory by adding (or removing) the specified item and quantity.
    Returns True if successful, False otherwise.
    """
    try:
        trainer = fetch_trainer_by_name(trainer_name)
        if trainer is None:
            logging.error(f"Trainer '{trainer_name}' not found for inventory update.")
            return False
        inv_str = trainer["inventory"] if trainer["inventory"] is not None else "{}"
        try:
            inventory = {} if inv_str == "" else json.loads(inv_str)
        except Exception as e:
            logging.error(f"Error parsing inventory JSON for '{trainer_name}': {e}")
            inventory = {}
        item_key = str(item_name)
        if quantity < 0:
            if item_key not in inventory:
                return False
            inventory[item_key] += quantity
            if inventory[item_key] <= 0:
                inventory.pop(item_key, None)
        else:
            inventory[item_key] = inventory.get(item_key, 0) + quantity
        new_inv_json = json.dumps(inventory)
        execute_query("UPDATE trainers SET inventory = ? WHERE id = ?", (new_inv_json, trainer["id"]))
        notify_sheet_update("trainer", trainer["id"], "inventory_update", {"inventory": new_inv_json})
        return True
    except Exception as e:
        logging.error(f"Inventory update failed for trainer '{trainer_name}': {e}")
        return False


# Alias for modules that reference "add_item"
add_item = update_character_sheet_item


async def update_character_level(trainer_name: str, target_name: str, level_amount: int) -> bool:
    """
    Adjusts levels for a trainer or one of their mons.
    If target_name matches the trainer (i.e. character_name), the trainer's level is increased.
    Otherwise, it updates the mon's level.
    """
    try:
        trainer = fetch_trainer_by_name(trainer_name)
        if trainer is None:
            return False
        if target_name.lower() == trainer_name.lower():
            new_level = max(trainer["level"] + level_amount, 0)
            update_trainer_level(trainer["id"], new_level)
            return True
        else:
            mon_record = fetch_mon_by_name(trainer_name, target_name)
            if mon_record is None:
                return False
            new_level = max(mon_record["level"] + level_amount, 0)
            update_mon_row(mon_record["id"], {"level": new_level})
            return True
    except Exception as e:
        logging.error(f"Level update failed for '{trainer_name}' target '{target_name}': {e}")
        return False


async def append_mon(trainer_name: str, mon_data: list) -> str:
    """
    Handles post-insertion steps for a new mon.
    Increments the trainer's mon count.
    Returns an empty string on success or an error message on failure.
    """
    try:
        trainer = fetch_trainer_by_name(trainer_name)
        if trainer is None:
            return f"Trainer '{trainer_name}' not found."
        execute_query("UPDATE trainers SET mon_amount = mon_amount + 1 WHERE id = ?", (trainer["id"],))
        notify_sheet_update("trainer", trainer["id"], "mon_count_increment", {"increment": 1})
        return ""
    except Exception as e:
        logging.error(f"Error finalizing new mon for trainer '{trainer_name}': {e}")
        return f"Error updating trainer's mon count: {e}"


# ----------------------------
# Habits
# ----------------------------
def add_habit(user_id: str, habit_name: str, time: str = None, difficulty: str = "medium"):
    query = "INSERT INTO habits (user_id, habit_name, time, difficulty) VALUES (?, ?, ?, ?)"
    cur = execute_query(query, (user_id, habit_name, time, difficulty))
    return cur.lastrowid


def fetch_habits(user_id: str) -> list:
    query = "SELECT habit_name, time, difficulty, streak, last_completed FROM habits WHERE user_id = ?"
    rows = fetch_all(query, (user_id,))
    habits = []
    for row in rows:
        habits.append({
            "name": row["habit_name"],
            "time": row["time"],
            "difficulty": row["difficulty"],
            "streak": row["streak"],
            "last_completed": row["last_completed"]
        })
    return habits


def remove_habit(user_id: str, habit_name: str) -> bool:
    try:
        execute_query("DELETE FROM habits WHERE user_id = ? AND habit_name = ?", (user_id, habit_name))
        return True
    except Exception as e:
        logging.error(f"Error removing habit '{habit_name}' for user {user_id}: {e}")
        return False


def mark_habit_complete(user_id: str, habit_name: str):
    query = "SELECT streak, last_completed FROM habits WHERE user_id = ? AND habit_name = ?"
    row = fetch_one(query, (user_id, habit_name))
    if not row:
        return None
    current_streak, last_completed = row["streak"], row["last_completed"]
    today_str = date.today().isoformat()
    if last_completed and last_completed.startswith(today_str):
        return None
    new_streak = (current_streak or 0) + 1
    update_query = "UPDATE habits SET streak = ?, last_completed = ? WHERE user_id = ? AND habit_name = ?"
    execute_query(update_query, (new_streak, datetime.now().isoformat(), user_id, habit_name))
    return new_streak

# ----------------------------
# Tasks
# ----------------------------
def add_task(user_id: str, task_name: str, time: str = None, carryover: bool = False, difficulty: str = "medium"):
    query = "INSERT INTO tasks (user_id, task_name, time, carryover, difficulty) VALUES (?, ?, ?, ?, ?)"
    carryover_int = 1 if carryover else 0
    cur = execute_query(query, (user_id, task_name, time, carryover_int, difficulty))
    return cur.lastrowid


def fetch_tasks(user_id: str) -> list:
    query = "SELECT task_name, time, carryover, difficulty, completed FROM tasks WHERE user_id = ? AND completed = 0"
    rows = fetch_all(query, (user_id,))
    tasks = []
    for row in rows:
        tasks.append({
            "name": row["task_name"],
            "time": row["time"],
            "carryover": bool(row["carryover"]),
            "difficulty": row["difficulty"],
            "completed": bool(row["completed"])
        })
    return tasks


def remove_task(user_id: str, task_name: str) -> bool:
    try:
        execute_query("DELETE FROM tasks WHERE user_id = ? AND task_name = ?", (user_id, task_name))
        return True
    except Exception as e:
        logging.error(f"Error removing task '{task_name}' for user {user_id}: {e}")
        return False


def mark_task_complete(user_id: str, task_name: str) -> bool:
    try:
        update_query = "UPDATE tasks SET completed = 1, date_completed = ? WHERE user_id = ? AND task_name = ? AND completed = 0"
        execute_query(update_query, (datetime.now().isoformat(), user_id, task_name))
        row = fetch_one("SELECT completed FROM tasks WHERE user_id = ? AND task_name = ?", (user_id, task_name))
        return (row and row["completed"] == 1)
    except Exception as e:
        logging.error(f"Error marking task '{task_name}' complete for user {user_id}: {e}")
        return False


# ----------------------------
# Schedules
# ----------------------------
def add_schedule_entry(user_id: str, entry_text: str, schedule_date: str = None):
    if schedule_date is None:
        schedule_date = date.today().isoformat()
    query = "INSERT INTO schedules (user_id, entry_text, schedule_date) VALUES (?, ?, ?)"
    cur = execute_query(query, (user_id, entry_text, schedule_date))
    return cur.lastrowid


def fetch_schedule(user_id: str, schedule_date: str = None) -> list:
    if schedule_date is None:
        schedule_date = date.today().isoformat()
    query = "SELECT entry_text, schedule_date, created_at FROM schedules WHERE user_id = ? AND schedule_date = ?"
    rows = fetch_all(query, (user_id, schedule_date))
    schedule = []
    for row in rows:
        schedule.append({
            "entry_text": row["entry_text"],
            "schedule_date": row["schedule_date"],
            "created_at": row["created_at"]
        })
    return schedule


def increment_garden_harvest(user_id: str, count: int = 1) -> None:
    query = "SELECT amount FROM garden_harvest WHERE user_id = ?"
    row = fetch_one(query, (user_id,))
    now = datetime.now().isoformat()
    if row is None:
        execute_query("INSERT INTO garden_harvest (user_id, amount, last_claimed) VALUES (?, ?, ?)",
                      (user_id, count, now))
    else:
        new_amount = row["amount"] + count
        execute_query("UPDATE garden_harvest SET amount = ? WHERE user_id = ?", (new_amount, user_id))


# ----------------------------
# Additional Mon/Trainer Fetch Functions
# ----------------------------
def get_mons_for_trainer(trainer_id: int) -> list:
    """
    Retrieves all mons for a given trainer from the database.
    Returns a list of dictionaries containing basic mon info.
    """
    query = "SELECT mon_id, name, level, img_link FROM mons WHERE trainer_id = ?"
    rows = fetch_all(query, (trainer_id,))
    mons = []
    for row in rows:
        mons.append({
            "id": row["mon_id"],
            "name": row["name"],
            "level": row["level"],
            "img_link": row["img_link"]
        })
    return mons


def fetch_all_trainers() -> list:
    """
    Retrieves all trainer records from the database.
    Returns a list of dictionaries with basic trainer info.
    """
    query = "SELECT id, player_user_id, character_name, level, inventory, img_link FROM trainers"
    rows = fetch_all(query)
    trainers = []
    for row in rows:
        trainers.append({
            "id": row["id"],
            "user_id": row["player_user_id"],
            "character_name": row["character_name"],
            "level": row["level"],
            "inventory": row["inventory"],
            "img_link": row["img_link"]
        })
    return trainers


# ----------------------------
# Adventure Session Functionality
# ----------------------------
def create_adventure_session_table():
    query = """
    CREATE TABLE IF NOT EXISTS adventure_sessions (
        channel_id INTEGER PRIMARY KEY,
        data TEXT
    )
    """
    execute_query(query)


from datetime import datetime

def increment_garden_harvest(user_id: str, count: int = 1) -> None:
    """
    Increments the garden harvest amount for the given user.
    If the record does not exist, it is created.
    After the update, a sheet update notification is posted.
    """
    now = datetime.now().isoformat()
    row = fetch_one("SELECT amount FROM garden_harvest WHERE user_id = ?", (user_id,))
    if row is None:
        # No record exists – insert a new one.
        execute_query(
            "INSERT INTO garden_harvest (user_id, amount, last_claimed) VALUES (?, ?, ?)",
            (user_id, count, now)
        )
        new_amount = count
    else:
        new_amount = row["amount"] + count
        execute_query(
            "UPDATE garden_harvest SET amount = ? WHERE user_id = ?",
            (new_amount, user_id)
        )
    # Post an update so that the helper can catch this change.
    notify_sheet_update("garden_harvest", user_id, "garden_harvest_update", {"new_amount": new_amount})




create_adventure_session_table()


def save_session(session) -> None:
    """
    Saves the current adventure session to the database.
    Expects session to have attributes: channel.id, area_data, hard_mode, progress, encounters_triggered, max_encounters, and players.
    """
    session_data = {
        "area_data": session.area_data,
        "hard_mode": session.hard_mode,
        "progress": session.progress,
        "encounters_triggered": session.encounters_triggered,
        "max_encounters": session.max_encounters,
        "players": list(session.players)
    }
    data = json.dumps(session_data)
    query = "INSERT OR REPLACE INTO adventure_sessions (channel_id, data) VALUES (?, ?)"
    execute_query(query, (session.channel.id, data))


def update_session(session) -> None:
    """
    Updates an existing adventure session in the database.
    """
    session_data = {
        "area_data": session.area_data,
        "hard_mode": session.hard_mode,
        "progress": session.progress,
        "encounters_triggered": session.encounters_triggered,
        "max_encounters": session.max_encounters,
        "players": list(session.players)
    }
    data = json.dumps(session_data)
    query = "UPDATE adventure_sessions SET data = ? WHERE channel_id = ?"
    execute_query(query, (data, session.channel.id))


def delete_session(channel_id: int) -> None:
    """
    Deletes an adventure session from the database using the channel ID.
    """
    query = "DELETE FROM adventure_sessions WHERE channel_id = ?"
    execute_query(query, (channel_id,))


def get_all_mons_for_user(user_id: str) -> list:
    """
    Retrieves all mon records for a given user from the database.
    Returns a list of dictionaries with basic mon information.
    """
    query = "SELECT mon_id, name, level, img_link, trainer_id FROM mons WHERE player_user_id = ?"
    rows = fetch_all(query, (user_id,))
    mons = []
    for row in rows:
        mons.append({
            "id": row["mon_id"],
            "name": row["name"],
            "level": row["level"],
            "img_link": row["img_link"],
            "trainer_id": row["trainer_id"]
        })
    return mons


def get_trainers_from_database(user_id: str) -> list:
    """
    Retrieves all trainer records from the database for the specified user.

    Args:
        user_id (str): The player's user ID.

    Returns:
        list: A list of dictionaries representing trainer records.
    """
    query = "SELECT * FROM trainers WHERE player_user_id = ?"
    rows = fetch_all(query, (user_id,))
    trainers = [dict(row) for row in rows]
    return trainers

def update_mon_sheet_value(trainer_name: str, mon_name: str, field: str, value):
    """
    Updates a specific field for a mon, given the trainer's character_name and the mon's name.
    This is a thin wrapper that fetches the mon and then calls update_mon_row.
    """
    mon = fetch_mon_by_name(trainer_name, mon_name)
    if mon:
        update_mon_row(mon["id"], {field: value})

