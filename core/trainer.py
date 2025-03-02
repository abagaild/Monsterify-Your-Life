import asyncio
import logging
from core.database import cursor, db
from core.google_sheets import gc, safe_request


def get_trainers(user_id: str) -> list:
    """
    Retrieves all trainer records for the given user.
    """
    cursor.execute("SELECT id, name, level, img_link FROM trainers WHERE user_id = ?", (user_id,))
    rows = cursor.fetchall()
    return [{"id": row[0], "name": row[1], "level": row[2], "img_link": row[3]} for row in rows]

def get_other_trainers_from_db(user_id: str) -> list:
    cursor.execute("SELECT id, name, level, img_link FROM trainers WHERE user_id != ?", (user_id,))
    rows = cursor.fetchall()
    return [{"id": row[0], "name": row[1], "level": row[2], "img_link": row[3]} for row in rows]


def add_trainer(user_id: str, name: str, level: int = 1, img_link: str = ""):
    cursor.execute("INSERT INTO trainers (user_id, name, level, img_link) VALUES (?, ?, ?, ?)", (user_id, name, level, img_link))
    db.commit()

def delete_trainer(user_id: str, trainer_name: str):
    cursor.execute("DELETE FROM trainers WHERE user_id = ? AND LOWER(name) = ?", (user_id, trainer_name.lower()))
    db.commit()

def update_trainer(trainer_id: int, **kwargs):
    if not kwargs:
        return
    fields = []
    values = []
    for key, value in kwargs.items():
        fields.append(f"{key} = ?")
        values.append(value)
    values.append(trainer_id)
    query = "UPDATE trainers SET " + ", ".join(fields) + " WHERE id = ?"
    cursor.execute(query, tuple(values))
    db.commit()

async def assign_levels_to_trainer(interaction, trainer_name: str, levels: int):
    user_id = str(interaction.user.id)
    cursor.execute("SELECT id, level FROM trainers WHERE user_id = ? AND LOWER(name)=?", (user_id, trainer_name.lower()))
    row = cursor.fetchone()
    if not row:
        await interaction.response.send_message(f"Trainer '{trainer_name}' not found. Please add the trainer first.", ephemeral=True)
        return
    trainer_id, current_level = row
    new_level = current_level + levels
    cursor.execute("UPDATE trainers SET level = ? WHERE id = ?", (new_level, trainer_id))
    db.commit()
    await interaction.response.send_message(
        f"Assigned {levels} levels to trainer '{trainer_name}'. New level: {new_level}.",
        ephemeral=True
    )

def get_temporary_inventory_columns(
    trainer_name: str,
    top_row: int = 1,
    start_row: int = 2,
    min_quantity: int = 1
) -> dict:
    """
    Reads a trainer's "Inventory" sheet, where each column is a distinct category header.
    The item names are below that header in the same column, and the item quantity is in the adjacent left column.

    For example, if column B has the header "BALLS", then from row 'start_row' downward:
      * Column B: item names ("Poké Ball", "Ranger Ball", etc.)
      * Column A: item quantities
    Only items with quantity >= min_quantity are included.

    Returns a dict of:
      {
        "BALLS": {
           "Poké Ball": 10,
           "Ranger Ball": 2,
           ...
        },
        "BERRIES": {
           "Maba Berry": 5,
           "Iapapa Berry": 1,
           ...
        },
        ...
      }
    """
    inventory = {}
    try:
        ss = gc.open(trainer_name)
        ws = ss.worksheet("Inventory")
    except Exception as e:
        logging.error(f"Error opening Inventory sheet for {trainer_name}: {e}")
        return inventory

    all_values = ws.get_all_values()
    if not all_values:
        return inventory

    # If top_row is 1, the row is all_values[0].
    # We'll interpret each non-empty cell in that row as a category.
    header_row_values = all_values[top_row - 1] if len(all_values) >= top_row else []
    num_columns = len(header_row_values)

    # For each column that has a non-empty header, parse items below it.
    for col_index in range(num_columns):
        category_header = header_row_values[col_index].strip()
        if category_header:  # Found a category
            # We'll gather items from row = start_row onward, reading item from (row, col_index),
            # and quantity from (row, col_index - 1).
            cat_dict = {}
            for row_idx in range(start_row - 1, len(all_values)):
                row_data = all_values[row_idx]
                if len(row_data) <= col_index:
                    continue
                item_name = row_data[col_index].strip()
                if not item_name:
                    continue
                qty_col = col_index - 1
                if qty_col < 0 or qty_col >= len(row_data):
                    # If there's no valid left column for quantity, skip
                    continue
                qty_str = row_data[qty_col].strip()
                try:
                    quantity = int(qty_str)
                except ValueError:
                    quantity = 0
                if quantity >= min_quantity:
                    cat_dict[item_name] = quantity
            if cat_dict:
                inventory[category_header] = cat_dict

    return inventory


async def get_trainer_pages(trainer_name: str) -> list:
    """
    Asynchronously retrieves trainer details from the spreadsheet.
    The spreadsheet is named after the trainer (trainer_name) and the worksheet is "Trainer Data".
    Rows with a blank in Column A trigger a page break.
    Returns a list of pages, each a dict with keys:
      - "header": The header text for the page.
      - "items": A list of (key, value) tuples.
    """
    pages = []
    current_page = {"header": None, "items": []}
    try:
        ss = await asyncio.to_thread(gc.open, trainer_name)
        ws = await asyncio.to_thread(ss.worksheet, "Trainer Data")
        rows = await asyncio.to_thread(ws.get_all_values)
    except Exception as e:
        logging.error("Error opening trainer sheet: %s", e)
        return [{"header": "Error", "items": [("Error", str(e))]}]

    for i, row in enumerate(rows):
        key = row[0].strip() if len(row) >= 1 else ""
        value = row[1].strip() if len(row) >= 2 else ""
        # A blank key triggers a page break.
        if key == "":
            if i == 0:
                current_page["header"] = value  # For the very first row, use value as header.
            else:
                pages.append(current_page)
                current_page = {"header": value, "items": []}
        else:
            current_page["items"].append((key, value))
    if current_page["header"] or current_page["items"]:
        pages.append(current_page)

    logging.debug("Trainer pages retrieved: %s", pages)
    return pages


async def update_trainer_detail(trainer_name: str, key: str, new_value: str) -> bool:
    """
    Asynchronously updates a trainer detail in the "Trainer Data" worksheet.

    Opens the spreadsheet (named after the trainer), then searches for a row where Column A
    matches the provided key (case-insensitively) and updates Column B with new_value.

    Returns:
      True if the update was successful, False otherwise.
    """
    try:
        ss = await asyncio.to_thread(gc.open, trainer_name)
        ws = await asyncio.to_thread(ss.worksheet, "Trainer Data")
        rows = await asyncio.to_thread(ws.get_all_values)
        for i, row in enumerate(rows, start=1):
            if len(row) >= 1 and row[0].strip().lower() == key.lower():
                await safe_request(ws.update_cell, i, 2, new_value)
                return True
        return False
    except Exception as e:
        logging.error("Error updating trainer detail: %s", e)
        return False


def get_all_trainers() -> list:
    """
    Retrieves all trainers from the database.

    Returns:
        A list of dictionaries, each containing:
          - id: Trainer ID.
          - name: Trainer's name.
          - level: Trainer's level.
          - img_link: Trainer's image URL (if any).
    """
    cursor.execute("SELECT id, name, level, img_link FROM trainers")
    rows = cursor.fetchall()
    return [{"id": row[0], "name": row[1], "level": row[2], "img_link": row[3]} for row in rows]


def get_mons_for_trainer_dict(trainer_id: int) -> list:
    """
    Retrieves all mons for the given trainer as a list of dictionaries.

    The returned dictionary includes details such as:
      - id: Mon ID.
      - mon_name: Mon's display name.
      - level: Mon's level.
      - species1, species2, species3: Species fields.
      - img_link: URL to the mon's image.

    Args:
        trainer_id (int): The unique ID of the trainer.

    Returns:
        A list of dictionaries, each representing a mon.
    """
    query = """
        SELECT id, mon_name, level, species1, species2, species3, img_link 
        FROM mons 
        WHERE trainer_id = ?
    """
    cursor.execute(query, (trainer_id,))
    rows = cursor.fetchall()
    mons = []
    for row in rows:
        mon = {
            "id": row[0],
            "mon_name": row[1],
            "level": row[2],
            "species1": row[3] if row[3] is not None else "",
            "species2": row[4] if row[4] is not None else "",
            "species3": row[5] if row[5] is not None else "",
            "img_link": row[6] if row[6] is not None else ""
        }
        mons.append(mon)
    return mons
