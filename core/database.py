import sqlite3
import asyncio
import json
import logging
from datetime import date, datetime

import redis
import discord  # Used for interactions and type hints

# Setup database connection and Redis client
db = sqlite3.connect("../dawn_and_dusk.db")
cursor = db.cursor()
redis_client = redis.Redis(host='localhost', port=6379, db=0)

def create_tables():
    cursor.executescript(
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
            mon_trainer_number INTEGER,
            trainer_name TEXT,
            trainer_id INTEGER,
            player_user_id TEXT,
            img_link TEXT,
            box_img_link TEXT,
            species1 TEXT,
            species2 TEXT,
            species3 TEXT,
            type1 TEXT,
            type2 TEXT,
            type3 TEXT,
            type4 TEXT,
            type5 TEXT,
            attribute TEXT,
            level INTEGER,
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
            ability TEXT,
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
        );CREATE TABLE IF NOT EXISTS habits (
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

        """
    )
    db.commit()

#create_tables()

# --- Generic Database Helpers ---
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

# --- Messaging Integration ---
def notify_sheet_update(entity, entity_id, update_type, payload):
    """
    Inserts a new update request into the sheet_update_requests table
    and publishes a JSON message on the 'sheet_update' Redis channel.
    """
    query = """
        INSERT INTO sheet_update_requests (entity, entity_id, update_type, payload)
        VALUES (?, ?, ?, ?)
    """
    execute_query(query, (entity, entity_id, update_type, json.dumps(payload)))
    message = json.dumps({
        "entity": entity,
        "entity_id": entity_id,
        "update_type": update_type,
        "payload": payload
    })
    redis_client.publish("sheet_update", message)
    logging.info("Notified sheet update: " + message)

# --- Trainer Update Functions ---
def fetch_trainer_by_name(trainer_name: str) -> dict:
    """
    Fetch a trainer's record by name (case-insensitive).
    Returns a dictionary with keys: id, user_id, name, level, inventory, and img_link.
    """
    query = """
        SELECT id, player_user_id, name, level, inventory, img_link
        FROM trainers
        WHERE LOWER(name) = ?
    """
    row = fetch_one(query, (trainer_name.lower(),))
    if row:
        return {
            "id": row[0],
            "user_id": row[1],
            "name": row[2],
            "level": row[3],
            "inventory": row[4] if row[4] is not None else "{}",
            "img_link": row[5]
        }
    return None

def update_trainer_field(trainer_id: int, field: str, new_value):
    """
    Updates a single field for a trainer record and notifies the sheet updater.
    """
    query = f"UPDATE trainers SET {field} = ? WHERE id = ?"
    execute_query(query, (new_value, trainer_id))
    notify_sheet_update("trainer", trainer_id, f"trainer_{field}", {field: new_value})

def update_trainer_level(trainer_id: int, new_level: int):
    return update_trainer_field(trainer_id, "level", new_level)

def update_trainer_currency(trainer_id: int, new_currency: int):
    return update_trainer_field(trainer_id, "currency_amount", new_currency)

def update_trainer_mon_amount(trainer_id: int, new_mon_amount: int):
    return update_trainer_field(trainer_id, "mon_amount", new_mon_amount)

def update_trainer_reference_amount(trainer_id: int, new_reference_amount: int):
    return update_trainer_field(trainer_id, "reference_amount", new_reference_amount)

# --- Mon Update Functions ---
def fetch_mon_by_name(trainer_name: str, name: str) -> dict:
    """
    Fetch a mon's record given the trainer's name and the mon's name (case-insensitive).
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
            "id": row[0],
            "name": row[1],
            "level": row[2],
            "player_user_id": row[3],
            "img_link": row[4]
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
    Updates the mon's display name. Adjust the column name if you have a dedicated mon name column.
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
    query = """
    INSERT INTO mons (
        trainer_id, player_user_id, name, level, 
        species1, species2, species3,
        type1, type2, type3, type4, type5,
        attribute, img_link
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    execute_query(query, (trainer_id, player, name, level,
                           species1, species2, species3,
                           type1, type2, type3, type4, type5,
                           attribute, img_link))
    return cursor.lastrowid

def remove_mon(mon_id: int) -> bool:
    """
    Removes a mon record from the database by its ID.
    """
    try:
        execute_query("DELETE FROM mons WHERE mon_id = ?", (mon_id,))
        return True
    except Exception as e:
        logging.error("Error removing mon (ID %s): %s", mon_id, e)
        return False

# --- Currency Helpers ---
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

# --- Log Sheet Helpers ---
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
        return True
    except Exception as e:
        logging.error(f"Inventory update failed for trainer '{trainer_name}': {e}")
        return False

# Alias for modules that reference "add_item"
add_item = update_character_sheet_item

async def update_character_sheet_level(trainer_name: str, target_name: str, level_amount: int) -> bool:
    """
    Adjusts levels for a trainer or one of their mons.
    If target_name matches the trainer, the trainer's level is increased.
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

async def append_mon_to_sheet(trainer_name: str, mon_data: list) -> str:
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
        return ""
    except Exception as e:
        logging.error(f"Error finalizing new mon for trainer '{trainer_name}': {e}")
        return f"Error updating trainer's mon count: {e}"

# Habits
def add_habit(user_id: str, habit_name: str, time: str = None, difficulty: str = "medium"):
    query = "INSERT INTO habits (user_id, habit_name, time, difficulty) VALUES (?, ?, ?, ?)"
    execute_query(query, (user_id, habit_name, time, difficulty))
    return cursor.lastrowid

def fetch_habits(user_id: str) -> list:
    query = "SELECT habit_name, time, difficulty, streak, last_completed FROM habits WHERE user_id = ?"
    cursor.execute(query, (user_id,))
    rows = cursor.fetchall()
    habits = []
    for row in rows:
        habits.append({
            "name": row[0],
            "time": row[1],
            "difficulty": row[2],
            "streak": row[3],
            "last_completed": row[4]
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
    current_streak, last_completed = row
    today_str = date.today().isoformat()
    if last_completed and last_completed.startswith(today_str):
        return None
    new_streak = (current_streak or 0) + 1
    update_query = "UPDATE habits SET streak = ?, last_completed = ? WHERE user_id = ? AND habit_name = ?"
    execute_query(update_query, (new_streak, datetime.now().isoformat(), user_id, habit_name))
    return new_streak

# Tasks
def add_task(user_id: str, task_name: str, time: str = None, carryover: bool = False, difficulty: str = "medium"):
    query = "INSERT INTO tasks (user_id, task_name, time, carryover, difficulty) VALUES (?, ?, ?, ?, ?)"
    carryover_int = 1 if carryover else 0
    execute_query(query, (user_id, task_name, time, carryover_int, difficulty))
    return cursor.lastrowid

def fetch_tasks(user_id: str) -> list:
    query = "SELECT task_name, time, carryover, difficulty, completed FROM tasks WHERE user_id = ? AND completed = 0"
    cursor.execute(query, (user_id,))
    rows = cursor.fetchall()
    tasks = []
    for row in rows:
        tasks.append({
            "name": row[0],
            "time": row[1],
            "carryover": bool(row[2]),
            "difficulty": row[3],
            "completed": bool(row[4])
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
        return (row and row[0] == 1)
    except Exception as e:
        logging.error(f"Error marking task '{task_name}' complete for user {user_id}: {e}")
        return False

# Schedules
def add_schedule_entry(user_id: str, entry_text: str, schedule_date: str = None):
    if schedule_date is None:
        schedule_date = date.today().isoformat()
    query = "INSERT INTO schedules (user_id, entry_text, schedule_date) VALUES (?, ?, ?)"
    execute_query(query, (user_id, entry_text, schedule_date))
    return cursor.lastrowid

def fetch_schedule(user_id: str, schedule_date: str = None) -> list:
    if schedule_date is None:
        schedule_date = date.today().isoformat()
    query = "SELECT entry_text, schedule_date, created_at FROM schedules WHERE user_id = ? AND schedule_date = ?"
    cursor.execute(query, (user_id, schedule_date))
    rows = cursor.fetchall()
    schedule = []
    for row in rows:
        schedule.append({
            "entry_text": row[0],
            "schedule_date": row[1],
            "created_at": row[2]
        })
    return schedule

def increment_garden_harvest(user_id: str, count: int = 1) -> None:
    query = "SELECT amount FROM garden_harvest WHERE user_id = ?"
    row = fetch_one(query, (user_id,))
    now = datetime.now().isoformat()
    if row is None:
        execute_query("INSERT INTO garden_harvest (user_id, amount, last_claimed) VALUES (?, ?, ?)", (user_id, count, now))
    else:
        new_amount = row[0] + count
        execute_query("UPDATE garden_harvest SET amount = ? WHERE user_id = ?", (new_amount, user_id))

# ----- Fetch mons for trainer -----
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
            "id": row[0],
            "name": row[1],
            "level": row[2],
            "img_link": row[3]
        })
    return mons

# ----- Update mon data -----
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
        return True
    except Exception as e:
        logging.error("Error updating mon data: %s", e)
        return False

# ----- Fetch all trainers -----
def fetch_all_trainers() -> list:
    """
    Retrieves all trainer records from the database.
    Returns a list of dictionaries with basic trainer info.
    """
    query = "SELECT id, player_user_id, name, level, inventory, img_link FROM trainers"
    rows = fetch_all(query)
    trainers = []
    for row in rows:
        trainers.append({
            "id": row[0],
            "user_id": row[1],
            "name": row[2],
            "level": row[3],
            "inventory": row[4],
            "img_link": row[5]
        })
    return trainers

# ----- Update mon img link -----
async def update_mon_img_link(trainer_name: str, name: str, new_img_link: str) -> bool:
    """
    Updates the img_link column for a mon (identified by trainer and mon name).
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

# ----- Adventure Session Functionality -----
# Create the adventure_sessions table if it doesn't exist:
def create_adventure_session_table():
    query = """
    CREATE TABLE IF NOT EXISTS adventure_sessions (
        channel_id INTEGER PRIMARY KEY,
        data TEXT
    )
    """
    execute_query(query)

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
            "id": row[0],
            "name": row[1],
            "level": row[2],
            "img_link": row[3],
            "trainer_id": row[4]
        })
    return mons
