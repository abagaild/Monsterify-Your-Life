import json
import logging
import os
import asyncio
from datetime import datetime
from google.oauth2.service_account import Credentials
import gspread

# Import updated helper functions from your database module
from core.database import get_record, fetch_all, execute_query
from core.mon import get_mons_for_trainer

# --- Google Sheets Setup ---
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive"
]
# Adjust the path to your credentials file as needed.
creds = Credentials.from_service_account_file(
    r"D:\Dawn And Dusk\Code\Google_Sheets\Credentials.json", scopes=SCOPES
)
gc = gspread.authorize(creds)

# --- Pending Update Functions using database helpers ---
def get_pending_updates():
    query = "SELECT * FROM sheet_update_requests WHERE status = 'pending'"
    rows = fetch_all(query)
    return [dict(row) for row in rows] if rows else []

def mark_update_processed(update_id):
    query = """
        UPDATE sheet_update_requests 
        SET status = 'processed', processed_at = CURRENT_TIMESTAMP 
        WHERE id = ?
    """
    execute_query(query, (update_id,))

import sqlite3
import os

current_dir = os.path.dirname(__file__)
db_path = os.path.join(current_dir, "..", "dawn_and_dusk.db")
conn = sqlite3.connect(db_path, check_same_thread=False)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# --- Worksheet Update Functions ---
def get_trainer_columns():
    """
    Retrieves the full list of column names from the trainers table,
    in the order defined in the database schema.
    """
    cursor.execute("PRAGMA table_info(trainers)")
    rows = cursor.fetchall()
    return [row["name"] for row in rows]


def update_trainer_information(ws, trainer_or_id):
    """
    Clears the worksheet and writes every column from the trainer record.
    Accepts either a trainer ID (int) or a full trainer dictionary.
    It fetches the full record directly from the database to ensure all columns are present.
    The first row will be the header (all column names in order),
    and the second row the corresponding values.
    """
    # Determine the trainer ID from the argument.
    if isinstance(trainer_or_id, dict):
        trainer_id = trainer_or_id.get("id")
    else:
        trainer_id = trainer_or_id

    if trainer_id is None:
        raise Exception("Trainer ID not provided.")

    # Direct query to get the full trainer record
    cursor.execute("SELECT * FROM trainers WHERE id = ?", (trainer_id,))
    row = cursor.fetchone()
    if not row:
        raise Exception(f"No trainer found with id {trainer_id}")

    trainer = dict(row)
    columns = get_trainer_columns()
    # Build a complete dictionary by ensuring every column is present.
    trainer_full = {col: (trainer[col] if col in trainer and trainer[col] is not None else "") for col in columns}
    headers = columns
    values = [str(trainer_full[col]) for col in columns]
    data = [headers, values]

    ws.clear()
    ws.update("A1", data, value_input_option="USER_ENTERED")


def safe_convert_qty(qty):
    if isinstance(qty, dict):
        return qty.get("number_value", 0)
    return qty

def update_inventory(ws, inventory_json):
    ws.clear()
    # If inventory_json is numeric, reset it to an empty JSON string.
    if isinstance(inventory_json, (int, float)):
        inventory_json = "{}"
    try:
        if isinstance(inventory_json, dict):
            inventory = inventory_json
        else:
            inventory = json.loads(inventory_json)
    except Exception as e:
        logging.error(f"Inventory JSON parse error: {e}")
        inventory = {}

    default_inventory = {
        "ITEMS": {
            "Fertalizer": 0,
            "Poké Puff": 0,
            "Charge Capsule": 0,
            "Scroll of Secrets": 0,
            "Shard": 0,
            "Bottle Cap": 0,
            "Gold Bottle Cap": 0,
            "Z-Crystal": 0,
            "Legacy Leeway": 0,
            "Daycare Daypass": 0
        },
        "BALLS": {
            "Poké Ball": 0,
            "Cygnus Ball": 0,
            "Ranger Ball": 0,
            "Premier Ball": 0,
            "Great Ball": 0,
            "Ultra Ball": 0,
            "Master Ball": 0,
            "Safari Ball": 0,
            "Fast Ball": 0,
            "Level Ball": 0,
            "Lure Ball": 0,
            "Heavy Ball": 0,
            "Love Ball": 0,
            "Friend Ball": 0,
            "Moon Ball": 0,
            "Sport Ball": 0,
            "Net Ball": 0,
            "Dive Ball": 0,
            "Nest Ball": 0,
            "Repeat Ball": 0,
            "Timer Ball": 0,
            "Luxury Ball": 0,
            "Dusk Ball": 0,
            "Heal Ball": 0,
            "Quick Ball": 0,
            "Marble Ball": 0,
            "Godly Ball": 0,
            "Rainbow Ball": 0,
            "Pumpkin Ball": 0,
            "Slime Ball": 0,
            "Bat Ball": 0,
            "Sweet Ball": 0,
            "Ghost Ball": 0,
            "Spider Ball": 0,
            "Eye Ball": 0,
            "Bloody Ball": 0,
            "Patched Ball": 0,
            "Snow Ball": 0,
            "Gift Ball": 0,
            "Ugly Christmas Ball": 0,
            "Snowflake Ball": 0,
            "Holly Ball": 0,
            "Candy Cane Ball": 0
        },
        "BERRIES": {
            "Mala Berry": 0,
            "Merco Berry": 0,
            "Lilan Berry": 0,
            "Kham Berry": 0,
            "Maizi Berry": 0,
            "Fani Berry": 0,
            "Miraca Berry": 0,
            "Cocon Berry": 0,
            "Durian Berry": 0,
            "Monel Berry": 0,
            "Perep Berry": 0,
            "Addish Berry": 0,
            "Sky Carrot Berry": 0,
            "Kembre Berry": 0,
            "Espara Berry": 0,
            "Patama Berry": 0,
            "Bluk Berry": 0,
            "Nuevo Berry": 0,
            "Azzuk Berry": 0,
            "Mangus Berry": 0,
            "Datei Berry": 0,
            "Forget-me-not": 0,
            "Edenweiss": 0
        },
        "PASTRIES": {
            "Miraca Pastry": 0,
            "Cocon Pastry": 0,
            "Durian Pastry": 0,
            "Monel Pastry": 0,
            "Perep Pastry": 0,
            "Addish Pastry": 0,
            "Sky Carrot Pastry": 0,
            "Kembre Pastry": 0,
            "Espara Pastry": 0,
            "Patama Pastry": 0,
            "Bluk Pastry": 0,
            "Nuevo Pastry": 0,
            "Azzuk Pastry": 0,
            "Mangus Pastry": 0,
            "Datei Pastry": 0
        },
        "EVOLUTION ITEMS": {
            "Normal Evolution Stone": 0,
            "Fire Evolution Stone": 0,
            "Fighting Evolution Stone": 0,
            "Water Evolution Stone": 0,
            "Flying Evolution Stone": 0,
            "Grass Evolution Stone": 0,
            "Poison Evolution Stone": 0,
            "Electric Evolution Stone": 0,
            "Ground Evolution Stone": 0,
            "Psychic Evolution Stone": 0,
            "Rock Evolution Stone": 0,
            "Ice Evolution Stone": 0,
            "Bug Evolution Stone": 0,
            "Dragon Evolution Stone": 0,
            "Ghost Evolution Stone": 0,
            "Dark Evolution Stone": 0,
            "Steel Evolution Stone": 0,
            "Fairy Evolution Stone": 0,
            "Void Evolution Stone": 0,
            "Aurora Evolution Stone": 0,
            "Digital Bytes": 0,
            "Digital Kilobytes": 0,
            "Digital Megabytes": 0,
            "Digital Gigabytes": 0,
            "Digital Petabytes": 0,
            "Digital Terabytes": 0,
            "Digital Repair Mode": 0
        },
        "EGGS": {
            "Standard Egg": 0,
            "Incubator": 0,
            "Fire Nurture Kit": 0,
            "Water Nurture Kit": 0,
            "Electric Nurture Kit": 0,
            "Grass Nurture Kit": 0,
            "Ice Nurture Kit": 0,
            "Fighting Nurture Kit": 0,
            "Poison Nurture Kit": 0,
            "Ground Nurture Kit": 0,
            "Flying Nurture Kit": 0,
            "Psychic Nurture Kit": 0,
            "Bug Nurture Kit": 0,
            "Rock Nurture Kit": 0,
            "Ghost Nurture Kit": 0,
            "Dragon Nurture Kit": 0,
            "Dark Nurture Kit": 0,
            "Steel Nurture Kit": 0,
            "Fairy Nurture Kit": 0,
            "Normal Nurture Kit": 0,
            "Corruption Code": 0,
            "Repair Code": 0,
            "Shiny New Code": 0,
            "E-Rank Incense": 0,
            "D-Rank Incense": 0,
            "C-Rank Incense": 0,
            "B-Rank Incense": 0,
            "A-Rank Incense": 0,
            "S-Rank Incense": 0,
            "Brave Color Incense": 0,
            "Mysterious Color Incense": 0,
            "Eerie Color Incense": 0,
            "Tough Color Incense": 0,
            "Charming Color Incense": 0,
            "Heartful Color Incense": 0,
            "Shady Color Incense": 0,
            "Slippery Color Incense": 0,
            "Wicked Color Incense": 0,
            "Fire Poffin": 0,
            "Water Poffin": 0,
            "Electric Poffin": 0,
            "Grass Poffin": 0,
            "Ice Poffin": 0,
            "Fighting Poffin": 0,
            "Poison Poffin": 0,
            "Ground Poffin": 0,
            "Flying Poffin": 0,
            "Psychic Poffin": 0,
            "Bug Poffin": 0,
            "Rock Poffin": 0,
            "Ghost Poffin": 0,
            "Dragon Poffin": 0,
            "Dark Poffin": 0,
            "Steel Poffin": 0,
            "Fairy Poffin": 0,
            "Spell Tag": 0,
            "Summoning Stone": 0,
            "DigiMeat": 0,
            "DigiTofu": 0,
            "Soothe Bell": 0,
            "Broken Bell": 0,
            "#Data Tag": 0,
            "#Vaccine Tag": 0,
            "#Virus Tag": 0,
            "#Free Tag": 0,
            "#Variable Tag": 0,
            "DNA Splicer": 0,
            "Hot Chocolate": 0,
            "Chocolate Milk": 0,
            "Strawberry Milk": 0,
            "Vanilla Ice Cream": 0,
            "Strawberry Ice Cream": 0,
            "Chocolate Ice Cream": 0,
            "Input Field": 0,
            "Drop Down": 0,
            "Radio Buttons": 0
        },
        "COLLECTION": {
            "Resolution Rocket": 0,
            "Love Velvet Cake": 0,
            "Lucky Leprechaun’s Loot": 0,
            "Can’t Believe It’s Not Butter": 0,
            "Bunny’s Basket Bonanza": 0,
            "Star-Spangled Sparkler": 0,
            "Fright Night Fudge": 0,
            "Turkey Trot Tonic": 0,
            "Jolly Holly Jamboree": 0,
            "Sweet Shofar Surprise": 0,
            "Day of Atonement Amulet": 0,
            "Harvest Haven Hummus": 0,
            "Latke Lightning in a Jar": 0,
            "Sectored Cookie": 0,
            "Matzah Marvel": 0,
            "Frosty Czar’s Confection": 0,
            "Snowflake Samovar": 0,
            "Brave Bear Barrel": 0,
            "Victory Vodka Vortex": 0,
            "Pancake Palooza": 0,
            "Diwali Dazzle Diyas": 0,
            "Color Carnival Concoction": 0,
            "Raksha Rhapsody": 0,
            "Ganesh’s Glorious Goodie": 0,
            "Tricolor Triumph Tonic": 0,
            "Lunar Lantern Loot": 0,
            "Dragon Dance Delight": 0,
            "Fortune Cookie Fusions": 0
        },
        "HELD ITEMS": {
            "Mega Stone": 0
        },
        "SEALS": {
            "White Smoke Sticker": 0,
            "Bolt Sticker": 0,
            "Blue Bubble Sticker": 0,
            "Fire Sticker": 0,
            "Red Ribbon Sticker": 0,
            "Wind-Blown Leaves Sticker": 0,
            "Misty Swirl Sticker": 0
        }
    }

    if not inventory:
        inventory = default_inventory

    # Update the worksheet using each inventory category
    requests = []
    col = 0
    for category, items in inventory.items():
        header_range = f"{chr(65 + col)}1"
        requests.append({
            "range": header_range,
            "values": [[category]]
        })
        rows = []
        if isinstance(items, dict):
            for item, qty in items.items():
                rows.append(f"{item}: {safe_convert_qty(qty)}")
        else:
            rows.append(str(items))
        value_range = f"{chr(65 + col)}2:{chr(65 + col)}{1 + len(rows)}"
        requests.append({
            "range": value_range,
            "values": [[r] for r in rows]
        })
        col += 1

    ws.batch_update(requests, value_input_option="USER_ENTERED")

def update_unlocks(ws, trainer):
    ws.clear()
    unlocks = {
        "Achievements": json.loads(trainer.get("achievements") or "{}"),
        "Badges Earned": json.loads(trainer.get("badges_earned") or "[]"),
        "Frontier Badges Earned": json.loads(trainer.get("frontier_badges_earned") or "[]"),
        "Contest Ribbons Earned": json.loads(trainer.get("contest_ribbons_earned") or "{}"),
        "Trainer Progression": json.loads(trainer.get("trainer_progression") or "{}"),
        "Prompts": json.loads(trainer.get("prompts") or "{}")
    }
    col = 1
    for title, data in unlocks.items():
        ws.update_cell(1, col, title)
        if isinstance(data, list):
            value = ", ".join(map(str, data))
        elif isinstance(data, dict):
            value = ", ".join([f"{k}:{v}" for k, v in data.items()])
        else:
            value = str(data)
        ws.update_cell(2, col, value)
        col += 1

def update_mon_data(ws, mons):
    ws.clear()
    if not mons:
        return
    headers = list(mons[0].keys())
    ws.insert_row(headers, index=1)
    row = 2
    for mon in mons:
        row_values = [str(mon.get(col, "")) for col in headers]
        ws.insert_row(row_values, index=row)
        row += 1

def update_move_data(ws, mons):
    ws.clear()
    col = 1
    for mon in mons:
        mon_name = mon.get("name", "Unknown")
        ws.update_cell(1, col, mon_name)
        try:
            moves = json.loads(mon.get("moveset", '["tackle", "growl"]'))
        except Exception as e:
            logging.error(f"Error parsing moveset for mon {mon_name}: {e}")
            moves = ["tackle", "growl"]
        row = 2
        for move in moves:
            ws.update_cell(row, col, move)
            row += 1
        col += 1

def update_google_sheet_for_trainer(trainer):
    # Use the trainer's character name as the spreadsheet name
    sheet_name = trainer.get("character_name", "")
    try:
        ss = gc.open(sheet_name)
    except Exception as e:
        logging.error(f"Error opening spreadsheet '{sheet_name}': {e}")
        return

    try:
        ws_info = ss.worksheet("Trainer Data")
    except Exception:
        ws_info = ss.add_worksheet(title="Trainer Data", rows="100", cols="50")
    update_trainer_information(ws_info, trainer)

    try:
        ws_inv = ss.worksheet("Item Data")
    except Exception:
        ws_inv = ss.add_worksheet(title="Item Data", rows="100", cols="10")
    update_inventory(ws_inv, trainer.get("inventory", "{}"))

    try:
        ws_unlocks = ss.worksheet("Unlocks")
    except Exception:
        ws_unlocks = ss.add_worksheet(title="Unlocks", rows="10", cols="10")
    update_unlocks(ws_unlocks, trainer)

    mons = get_mons_for_trainer(trainer.get("id"))
    try:
        ws_mon_data = ss.worksheet("Mon Data")
    except Exception:
        ws_mon_data = ss.add_worksheet(title="Mon Data", rows="100", cols="50")
    update_mon_data(ws_mon_data, mons)

    try:
        ws_move_data = ss.worksheet("Move Data")
    except Exception:
        ws_move_data = ss.add_worksheet(title="Move Data", rows="100", cols="50")
    update_move_data(ws_move_data, mons)

# --- Update Processing ---
def process_update_request(update):
    entity = update.get("entity")
    entity_id = update.get("entity_id")
    logging.info(f"Processing update id {update.get('id')}: entity={entity}, entity_id={entity_id}")
    if entity == "trainer":
        trainer = get_record("trainers", entity_id)
        if trainer:
            update_google_sheet_for_trainer(trainer)
        else:
            logging.error(f"Trainer with id {entity_id} not found.")
    elif entity == "mon":
        mon = get_record("mons", entity_id, id_field="mon_id")
        if mon:
            trainer = get_record("trainers", mon.get("trainer_id"))
            if trainer:
                update_google_sheet_for_trainer(trainer)
            else:
                logging.error(f"Trainer for mon id {entity_id} not found.")
        else:
            logging.error(f"Mon with id {entity_id} not found.")
    else:
        logging.warning("Unknown entity type in update.")

# --- Asynchronous Polling Loop ---
async def poll_for_updates():
    while True:
        logging.info("Polling database for pending updates...")
        updates = await asyncio.to_thread(get_pending_updates)
        if updates:
            logging.info(f"Found {len(updates)} pending update(s).")
            for update in updates:
                try:
                    await asyncio.to_thread(process_update_request, update)
                    await asyncio.to_thread(mark_update_processed, update.get("id"))
                except Exception as e:
                    logging.error(f"Error processing update id {update.get('id')}: {e}")
        else:
            logging.info("No pending updates found.")
        await asyncio.sleep(300)  # Poll every 5 minutes

async def main():
    logging.info("Starting Google_Sheets sync service (database polling mode)...")
    await poll_for_updates()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
