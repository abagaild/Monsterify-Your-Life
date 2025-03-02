import asyncio
import time
import logging
import gspread
from google.oauth2.service_account import Credentials
from gspread.exceptions import APIError
import core.config  # Assumes a config.py with RATE_LIMIT and RATE_PERIOD settings

# Define the required Google API scopes.
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive"
]

# Authorize using the service account credentials.
creds = Credentials.from_service_account_file("Credentials.json", scopes=SCOPES)
gc = gspread.authorize(creds)

# Rate limiting globals.
_request_count = 0
_last_reset = time.monotonic()

async def safe_request(func, *args, **kwargs):
    """
    Wraps a gspread call in asyncio.to_thread with rate limiting and retries.
    """
    global _request_count, _last_reset
    while True:
        now = time.monotonic()
        if now - _last_reset >= core.config.RATE_PERIOD:
            _last_reset = now
            _request_count = 0
        if _request_count >= core.config.RATE_LIMIT:
            sleep_time = core.config.RATE_PERIOD - (now - _last_reset)
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
            _last_reset = time.monotonic()
            _request_count = 0
        try:
            result = await asyncio.to_thread(func, *args, **kwargs)
            _request_count += 1
            return result
        except APIError as e:
            if "429" in str(e):
                logging.warning("Rate limit hit. Sleeping before retrying...")
                await asyncio.sleep(10)
            else:
                raise

async def update_character_sheet_item(trainer_name: str, item_name: str, quantity: int) -> bool:
    """
    Finds an empty row in the 'Log' worksheet of the trainer's sheet and updates it with the item and quantity.
    """
    try:
        ss = gc.open(trainer_name)
    except Exception as e:
        logging.error(f"Error opening spreadsheet for '{trainer_name}': {e}")
        return False
    try:
        ws = ss.worksheet("Log")
    except Exception as e:
        logging.error(f"Error opening worksheet 'Log' for '{trainer_name}': {e}")
        return False

    rows = ws.get_all_values()
    target_row = None

    def cell_blank(row, col):
        return (len(row) < col) or (row[col-1].strip() == "")

    for idx, row in enumerate(rows, start=1):
        if (cell_blank(row, 2) and cell_blank(row, 3) and cell_blank(row, 4) and
            cell_blank(row, 9) and cell_blank(row, 10) and cell_blank(row, 11) and cell_blank(row, 12)):
            target_row = idx
            break

    if target_row is None:
        blank_row = ["" for _ in range(15)]
        ws.append_row(blank_row, value_input_option="USER_ENTERED")
        rows = ws.get_all_values()
        target_row = len(rows)

    try:
        ws.update_cell(target_row, 9, item_name)   # Column I
        ws.update_cell(target_row, 10, str(quantity))  # Column J
    except Exception as e:
        logging.error(f"Error updating cells in row {target_row}: {e}")
        return False
    return True

async def update_character_sheet_level(trainer_name: str, target_name: str, level_amount: int) -> bool:
    """
    Finds an empty row in the 'Log' worksheet and updates it with the target name and level amount.
    """
    try:
        ss = gc.open(trainer_name)
    except Exception as e:
        logging.error(f"Error opening spreadsheet for trainer '{trainer_name}': {e}")
        return False
    try:
        ws = ss.worksheet("Log")
    except Exception as e:
        logging.error(f"Error opening worksheet 'Log' for '{trainer_name}': {e}")
        return False

    rows = ws.get_all_values()

    def cell_blank(row, col):
        return (len(row) < col) or (row[col-1].strip() == "")

    target_row = None
    for idx, row in enumerate(rows, start=1):
        if (cell_blank(row, 2) and cell_blank(row, 3) and cell_blank(row, 4) and
            cell_blank(row, 9) and cell_blank(row, 10) and cell_blank(row, 11) and cell_blank(row, 12)):
            target_row = idx
            break

    if target_row is None:
        blank_row = ["" for _ in range(15)]
        ws.append_row(blank_row, value_input_option="USER_ENTERED")
        rows = ws.get_all_values()
        target_row = len(rows)

    try:
        ws.update_cell(target_row, 2, target_name)      # Column B: target name
        ws.update_cell(target_row, 3, str(level_amount))  # Column C: level amount
    except Exception as e:
        logging.error(f"Error updating level in row {target_row}: {e}")
        return False
    return True

async def append_mon_to_sheet(trainer_name: str, mon_data: list) -> str:
    """
    Appends mon data (a list of values) to the 'Pkm Data' worksheet in the trainer's spreadsheet.
    Returns an empty string on success or an error message.
    """
    try:
        ss = await asyncio.to_thread(gc.open, trainer_name)
        ws = await asyncio.to_thread(ss.worksheet, "Pkm Data")
    except Exception as e:
        return f"Error opening sheet for trainer {trainer_name}: {e}"

    try:
        rows = await asyncio.to_thread(ws.get_all_values)
    except Exception as e:
        return f"Error retrieving data from 'Pkm Data': {e}"

    target_row = None
    for idx, row in enumerate(rows, start=1):
        if len(row) < 2 or row[1].strip() == "":
            target_row = idx
            break
    if target_row is None:
        blank_row = ["" for _ in range(15)]
        await asyncio.to_thread(ws.append_row, blank_row, value_input_option="USER_ENTERED")
        rows = await asyncio.to_thread(ws.get_all_values)
        target_row = len(rows)

    try:
        await safe_request(ws.update_cell, target_row, 2, mon_data[1])  # Custom display name
        await safe_request(ws.update_cell, target_row, 5, mon_data[4])  # Species1
        await safe_request(ws.update_cell, target_row, 6, mon_data[5])  # Species2
        await safe_request(ws.update_cell, target_row, 7, mon_data[6])  # Species3
        for i in range(5):
            await safe_request(ws.update_cell, target_row, 8 + i, mon_data[7 + i])
        await safe_request(ws.update_cell, target_row, 13, mon_data[12])  # Attribute
        await safe_request(ws.update_cell, target_row, 15, mon_data[14])  # Image link
    except Exception as e:
        return f"Error updating row {target_row}: {e}"
    return ""

async def update_log_sheet(trainer_name: str, data: dict) -> bool:
    """
    Updates cells in the "Log" worksheet. 'data' maps cell addresses (e.g. "B3") to new values.
    """
    try:
        ss = gc.open(trainer_name)
        ws = ss.worksheet("Log")
    except Exception as e:
        logging.error(f"Error opening Log sheet for {trainer_name}: {e}")
        return False
    for cell, value in data.items():
        try:
            await safe_request(ws.update_acell, cell, str(value))
        except Exception as e:
            logging.error(f"Error updating cell {cell}: {e}")
            return False
    return True

async def update_mon_img_link(trainer_name: str, mon_name: str, link: str) -> str:
    """
    Updates the image link for a mon in the 'Pkm Data' worksheet.
    """
    if "format=webp" in link.lower():
        link = link.replace("format=webp", "format=png")
    try:
        ss = gc.open(trainer_name)
        ws = ss.worksheet("Pkm Data")
    except Exception as e:
        return f"Error opening sheet for trainer {trainer_name}: {e}"
    try:
        rows = ws.get_all_values()
    except Exception as e:
        return f"Error retrieving data: {e}"
    target_row = None
    for idx, row in enumerate(rows, start=1):
        if len(row) >= 2 and row[1].strip().lower() == mon_name.strip().lower():
            target_row = idx
            break
    if target_row is None:
        return f"Mon name '{mon_name}' not found in sheet."
    try:
        await safe_request(ws.update_cell, target_row, 15, link)
    except Exception as e:
        return f"Error updating image link in row {target_row}: {e}"
    return ""

async def update_mon_sheet_data(trainer_name: str, mon_name: str, data: dict) -> bool:
    """
    Updates a mon's row in the 'Pkm Data' worksheet.
    'data' is a dictionary mapping column numbers (as keys) to new values.
    """
    try:
        ss = gc.open(trainer_name)
        ws = ss.worksheet("Pkm Data")
        rows = ws.get_all_values()
    except Exception as e:
        logging.error(f"Error accessing Pkm Data for {trainer_name}: {e}")
        return False

    target_row = None
    for idx, row in enumerate(rows, start=1):
        if len(row) >= 2 and row[1].strip().lower() == mon_name.strip().lower():
            target_row = idx
            break
    if target_row is None:
        logging.error(f"Mon {mon_name} not found in sheet.")
        return False

    for col, value in data.items():
        try:
            await safe_request(ws.update_cell, target_row, int(col), str(value))
        except Exception as e:
            logging.error(f"Error updating column {col} for mon {mon_name}: {e}")
            return False
    return True

async def update_trainer_sheet_data(trainer_name: str, data: dict) -> bool:
    """
    Updates the 'Trainer Data' worksheet.
    'data' should map cell addresses (e.g. "B3") to new values.
    """
    try:
        ss = gc.open(trainer_name)
        ws = ss.worksheet("Trainer Data")
    except Exception as e:
        logging.error(f"Error opening Trainer Data sheet for {trainer_name}: {e}")
        return False
    for cell, value in data.items():
        try:
            await safe_request(ws.update_acell, cell, str(value))
        except Exception as e:
            logging.error(f"Error updating cell {cell} in Trainer Data: {e}")
            return False
    return True

async def sync_sheets():
    """
    Synchronizes local trainer and mon data with their corresponding Google Sheets.
    This function loops through each trainer record from the database and updates
    both the 'Trainer Data' and 'Pkm Data' worksheets.
    """
    try:
        from core.database import cursor
    except Exception:
        logging.error("Failed to import database cursor.")
        return

    try:
        cursor.execute("SELECT id, user_id, name, level, img_link FROM trainers")
        trainers = cursor.fetchall()
    except Exception as e:
        logging.error(f"Error querying trainers: {e}")
        return

    for trainer in trainers:
        t_id, user_id, trainer_name, level, img_link = trainer
        try:
            ss = gc.open(trainer_name)
        except Exception as e:
            logging.error(f"Spreadsheet for trainer '{trainer_name}' not found: {e}")
            continue

        # Update Trainer Data worksheet
        try:
            ws_trainer = ss.worksheet("Trainer Data")
            await safe_request(ws_trainer.update_acell, "B3", trainer_name)
            await safe_request(ws_trainer.update_acell, "B8", str(t_id))
            await safe_request(ws_trainer.update_acell, "B52", img_link)
        except Exception as e:
            logging.error(f"Error updating Trainer Data for '{trainer_name}': {e}")

        # Update Pkm Data worksheet with each mon.
        try:
            ws_mon = ss.worksheet("Pkm Data")
            existing_values = await safe_request(ws_mon.get_all_values)
        except Exception as e:
            logging.error(f"Error accessing 'Pkm Data' for '{trainer_name}': {e}")
            continue

        used_rows = set()
        try:
            cursor.execute(
                "SELECT mon_name, level, species1, species2, species3, type1, type2, type3, type4, type5, attribute, img_link FROM mons WHERE trainer_id = ?",
                (t_id,)
            )
            mon_rows = cursor.fetchall()
        except Exception as e:
            logging.error(f"Error retrieving mons for trainer '{trainer_name}': {e}")
            continue

        for mon in mon_rows:
            mon_name, mon_level, species1, species2, species3, type1, type2, type3, type4, type5, attribute, mon_img_link = mon
            row_index = None
            for idx, row in enumerate(existing_values, start=1):
                if idx in used_rows:
                    continue
                if len(row) >= 2 and row[1].strip().lower() == mon_name.strip().lower():
                    row_index = idx
                    break
            if row_index is None:
                for idx, row in enumerate(existing_values, start=1):
                    if idx in used_rows:
                        continue
                    if len(row) < 2 or not row[1].strip():
                        row_index = idx
                        break
            if row_index is None:
                new_row = ["" for _ in range(15)]
                new_row[1] = mon_name
                new_row[4] = species1
                new_row[5] = species2 or ""
                new_row[6] = species3 or ""
                new_row[7] = type1
                new_row[8] = type2 or ""
                new_row[9] = type3 or ""
                new_row[10] = type4 or ""
                new_row[11] = type5 or ""
                new_row[12] = attribute
                new_row[14] = mon_img_link or ""
                await safe_request(ws_mon.append_row, new_row, value_input_option="USER_ENTERED")
                row_index = len(existing_values) + 1
                existing_values.append(new_row)
            else:
                await safe_request(ws_mon.update_cell, row_index, 2, mon_name)
                await safe_request(ws_mon.update_cell, row_index, 5, species1)
                await safe_request(ws_mon.update_cell, row_index, 6, species2 or "")
                await safe_request(ws_mon.update_cell, row_index, 7, species3 or "")
                await safe_request(ws_mon.update_cell, row_index, 8, type1)
                await safe_request(ws_mon.update_cell, row_index, 9, type2 or "")
                await safe_request(ws_mon.update_cell, row_index, 10, type3 or "")
                await safe_request(ws_mon.update_cell, row_index, 11, type4 or "")
                await safe_request(ws_mon.update_cell, row_index, 12, type5 or "")
                await safe_request(ws_mon.update_cell, row_index, 13, attribute)
                await safe_request(ws_mon.update_cell, row_index, 15, mon_img_link or "")
            # Mark this row as used so the next mon doesn't overwrite it.
            used_rows.add(row_index)

    logging.info("Sheets synchronization complete.")

async def get_mon_sheet_row(trainer_name: str, mon_name: str):
    """
    Retrieves the row for the specified mon from the trainer's "Pkm Data" worksheet.

    Parameters:
      trainer_name (str): The name of the trainer, which is also the name of the spreadsheet.
      mon_name (str): The name of the mon to search for (matched against column B).

    Returns:
      tuple: (mon_details, header, row_number)
        - mon_details: A list of values representing the mon's row (or None if not found)
        - header: A list of header values (assumed to be the first row in the sheet)
        - row_number: The 1-indexed row number where the mon was found (or None if not found)
    """
    try:
        ss = await safe_request(gc.open, trainer_name)
        ws = await safe_request(ss.worksheet, "Pkm Data")
        rows = await safe_request(ws.get_all_values)
        if not rows:
            return None, None, None
        header = rows[0]
        mon_details = None
        row_number = None
        # Assume the first row is the header and start checking from the second row.
        for idx, row in enumerate(rows[1:], start=2):
            if len(row) >= 2 and row[1].strip().lower() == mon_name.strip().lower():
                mon_details = row
                row_number = idx
                break
        return mon_details, header, row_number
    except Exception as e:
        logging.error(f"Error in get_mon_sheet_row for trainer '{trainer_name}', mon '{mon_name}': {e}")
        return None, None, None

async def update_mon_sheet_value(trainer_name: str, mon_name: str, field: str, new_value: str) -> bool:
    """
    Updates a single field (cell) in the trainer's "Pkm Data" worksheet for the specified mon.

    Process:
      1. Opens the trainer's spreadsheet and selects the "Pkm Data" worksheet.
      2. Retrieves all rows (with the header assumed to be the first row).
      3. Finds the column where the header matches the provided field (case-insensitive).
      4. Locates the row where column B (mon name) matches the given mon_name (case-insensitive).
      5. Updates the cell at the found row and column with the new value.

    Returns:
      True if the cell was updated successfully; False otherwise.
    """
    try:
        # Open spreadsheet and get worksheet asynchronously.
        ss = await safe_request(gc.open, trainer_name)
        ws = await safe_request(ss.worksheet, "Pkm Data")
        rows = await safe_request(ws.get_all_values)
        if not rows or len(rows) < 2:
            logging.error("No data or header not found in the sheet.")
            return False
        header = rows[0]
        # Find the column index matching the given field (case-insensitive).
        column_index = None
        for idx, col_name in enumerate(header):
            if col_name.strip().lower() == field.strip().lower():
                column_index = idx + 1  # Google Sheets is 1-indexed.
                break
        if column_index is None:
            logging.error(f"Field '{field}' not found in header.")
            return False

        # Locate the row where column B matches the mon name (case-insensitive).
        target_row = None
        for idx, row in enumerate(rows[1:], start=2):
            if len(row) >= 2 and row[1].strip().lower() == mon_name.strip().lower():
                target_row = idx
                break
        if target_row is None:
            logging.error(f"Mon '{mon_name}' not found in sheet.")
            return False

        # Update the cell.
        await safe_request(ws.update_cell, target_row, column_index, new_value)
        return True

    except Exception as e:
        logging.error(f"Error updating sheet for trainer '{trainer_name}', mon '{mon_name}': {e}")
        return False
