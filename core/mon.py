import random
import asyncio
import discord
from typing import Tuple, Any
import logging
from core.database import cursor, db, update_mon_row, add_mon
from core.currency import add_currency
from core.database import append_mon_to_sheet, update_character_sheet_level, update_character_sheet_item
from data.lists import no_evolution, mythical_list, legendary_list

def should_ignore_column(index: int) -> bool:
    # Helper to filter out columns not needed from sheet data (if syncing sheets)
    if index == 1:  # Skip display name column for sheet parsing
        return True
    if index in (3, 4):  # Skip unused columns C, D
        return True
    if 16 <= index <= 47:  # Skip stats columns (if not needed)
        return True
    if 56 <= index <= 95:  # Skip moves or extra columns
        return True
    if 97 <= index <= 129:  # Skip more extra columns
        return True
    if index in (140, 141):
        return True
    if 143 <= index <= 149:
        return True
    return False

def get_mon(player_id: str, name: str) -> dict:
    """
    Retrieves a mon record from the database by name and player (Discord user ID).
    Returns a dict with mon details or None if not found.
    """
    cursor.execute(
        "SELECT id, species1, species2, species3, type1, type2, type3, type4, type5, attribute FROM mons WHERE name = ? AND player = ?",
        (name, player_id)
    )
    row = cursor.fetchone()
    if row:
        mon = {
            "id": row[0],
            "species1": row[1],
            "species2": row[2],
            "species3": row[3],
            "types": [row[4], row[5], row[6], row[7], row[8]],
            "attribute": row[9],
            "name": name
        }
        mon["types"] = [t for t in mon["types"] if t]
        return mon
    return None

def randomize_mon(mon: dict, force_min_types: int = None) -> dict:
    """
    Randomizes the mon's types and attribute (used for certain item effects).
    """
    POSSIBLE_TYPES = [
        "Normal", "Fire", "Water", "Grass", "Electric", "Ice", "Fighting",
        "Psychic", "Bug", "Rock", "Ghost", "Dragon", "Dark", "Steel", "Fairy"
    ]
    RANDOM_ATTRIBUTES = ["Free", "Virus", "Data", "Variable"]
    new_mon = mon.copy()
    num_types = random.randint(force_min_types if force_min_types else 1, 3)
    new_mon["types"] = random.sample(POSSIBLE_TYPES, num_types)
    new_mon["attribute"] = random.choice(RANDOM_ATTRIBUTES)
    return new_mon

class RegisterMonModal(discord.ui.Modal, title="Register Mon"):
    """
    A modal that prompts the user for:
      - Trainer Name
      - Custom Mon Name (type 'default' to keep the rolled name)
    Upon submission, it inserts the mon into the database and updates relevant data.
    """
    trainer_name = discord.ui.TextInput(label="Trainer Name", placeholder="Enter the trainer's name", required=True)
    custom_name = discord.ui.TextInput(label="Custom Mon Name", placeholder="Enter a custom name (or type 'default' to keep the rolled name)", required=True)

    def __init__(self, mon_data: dict):
        super().__init__()
        self.mon_data = mon_data

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        trainer = self.trainer_name.value.strip()
        custom_name_input = self.custom_name.value.strip()
        # Use default rolled name if user inputs 'default'
        final_name = self.mon_data["display_name"] if custom_name_input.lower() == "default" else custom_name_input

        # Find trainer record
        cursor.execute("SELECT id, player_user_id FROM trainers WHERE name = ?", (trainer,))
        trainer_row = cursor.fetchone()
        if not trainer_row:
            await interaction.followup.send(f"Trainer '{trainer}' not found.", ephemeral=True)
            return
        trainer_id, user_id = trainer_row[0], trainer_row[1]

        # Determine initial level and species/types for the new mon
        level = int(self.mon_data.get("level", 1))
        species1 = self.mon_data.get("species1", "")
        species2 = self.mon_data.get("species2", "")
        species3 = self.mon_data.get("species3", "")
        types = self.mon_data.get("types", [])
        types += [""] * (5 - len(types))  # pad types list to length 5

        # Insert mon record into the database
        try:
            cursor.execute(
                """
                INSERT INTO mons (trainer_id, player, name, level, species1, species2, species3,
                                   type1, type2, type3, type4, type5, attribute, img_link)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    trainer_id, user_id, final_name, level,
                    species1, species2, species3,
                    types[0], types[1], types[2], types[3], types[4],
                    self.mon_data.get("attribute", ""), self.mon_data.get("img_link", "")
                )
            )
            db.commit()
        except Exception as e:
            logging.error(f"Error inserting mon into database: {e}")
            await interaction.followup.send("Failed to register mon in the database.", ephemeral=True)
            return

        # Finalize registration (update mon count) and attempt to update Google Sheet (if sync is enabled)
        error = await append_mon_to_sheet(trainer, [])
        if error:
            await interaction.followup.send(f"Mon added to database but failed to update sheet: {error}", ephemeral=True)
        else:
            await interaction.followup.send(f"Registered mon **{final_name}** to trainer **{trainer}** successfully.", ephemeral=True)
            # Deduct one Pokéball from inventory
            await update_character_sheet_item(trainer, "Pokeball", -1)

async def assign_levels_to_mon(interaction: discord.Interaction, name: str, levels: int):
    """
    Assigns a number of levels to a mon (or removes levels if negative).
    If the mon's level exceeds 100, extra levels are converted to currency for the trainer.
    """
    user_id = str(interaction.user.id)
    cursor.execute("SELECT trainer_id, level FROM mons WHERE name = ? AND player = ?", (name, user_id))
    res = cursor.fetchone()
    if not res:
        await interaction.response.send_message(f"Mon '{name}' not found or does not belong to you.", ephemeral=True)
        return
    trainer_id, current_level = res
    cursor.execute("SELECT name FROM trainers WHERE id = ?", (trainer_id,))
    t_res = cursor.fetchone()
    if not t_res:
        await interaction.response.send_message("Trainer not found for that mon.", ephemeral=True)
        return
    trainer_name = t_res[0]
    # Determine how many levels can be applied and how many convert to currency
    if current_level >= 100:
        extra_coins = levels * 25
        # Mon is already maxed; just convert all intended levels to currency
        cursor.execute("UPDATE trainers SET currency_amount = currency_amount + ? WHERE id = ?", (extra_coins, trainer_id))
        db.commit()
        await interaction.response.send_message(
            f"Mon '{name}' is already at level 100. Converted {levels} level(s) into {extra_coins} coins.",
            ephemeral=True
        )
    elif current_level + levels > 100:
        effective_levels = 100 - current_level
        excess = levels - effective_levels
        success = await update_character_sheet_level(trainer_name, name, effective_levels)
        if success:
            # Mon reached level 100; convert remaining levels to currency
            extra_coins = excess * 25
            cursor.execute("UPDATE trainers SET currency_amount = currency_amount + ? WHERE id = ?", (extra_coins, trainer_id))
            db.commit()
            await interaction.response.send_message(
                f"Mon '{name}' reached level 100. Added {effective_levels} level(s) and converted {excess} extra level(s) into {extra_coins} coins.",
                ephemeral=True
            )
        else:
            await interaction.response.send_message("Failed to update the mon's level in the database.", ephemeral=True)
    else:
        success = await update_character_sheet_level(trainer_name, name, levels)
        if success:
            await interaction.response.send_message(
                f"Added {levels} level(s) to mon '{name}' (Trainer: {trainer_name}).",
                ephemeral=True
            )
        else:
            await interaction.response.send_message("Failed to update the mon's level in the database.", ephemeral=True)

def get_mon(trainer_id: str, name: str) -> dict:
    """
    Retrieves a mon record for the given trainer and mon name.
    """
    cursor.execute(
        "SELECT mon_id, species1, species2, species3, type1, type2, type3, type4, type5, attribute FROM mons WHERE name = ? AND player = ?",
        (name, trainer_id)
    )
    row = cursor.fetchone()
    if row:
        mon = {
            "id": row[0],
            "species1": row[1],
            "species2": row[2],
            "species3": row[3],
            "types": [row[4], row[5], row[6], row[7], row[8]],
            "attribute": row[9],
            "name": name
        }
        mon["types"] = [t for t in mon["types"] if t]
        return mon
    return None

def randomize_mon(mon: dict, force_min_types: int = None) -> dict:
    """
    Randomizes a mon's types and attribute.
    """
    POSSIBLE_TYPES = [
        "Normal", "Fire", "Water", "Grass", "Electric", "Ice", "Fighting",
        "Psychic", "Bug", "Rock", "Ghost", "Dragon", "Dark", "Steel", "Fairy"
    ]
    RANDOM_ATTRIBUTES = ["Free", "Virus", "Data", "Variable"]
    new_mon = mon.copy()
    num_types = random.randint(force_min_types if force_min_types else 1, 3)
    new_mon["types"] = random.sample(POSSIBLE_TYPES, num_types)
    new_mon["attribute"] = random.choice(RANDOM_ATTRIBUTES)
    return new_mon

class RegisterMonModal(discord.ui.Modal, title="Register Mon"):
    """
    Modal that prompts for trainer and custom mon name.
    Upon submission, it looks up the trainer and inserts a new mon record.
    """
    trainer_name = discord.ui.TextInput(
        label="Trainer Name",
        placeholder="Enter trainer's name",
        required=True
    )
    custom_name = discord.ui.TextInput(
        label="Custom Mon Name",
        placeholder="Enter a custom name (or type 'default' to keep the rolled name)",
        required=True
    )

    def __init__(self, mon_data):
        super().__init__()
        self.mon_data = mon_data

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        if asyncio.iscoroutine(self.mon_data):
            self.mon_data = await self.mon_data

        user_id = str(interaction.user.id)
        trainer = self.trainer_name.value.strip()
        custom_name = self.custom_name.value.strip()
        rolled_name = self.mon_data.get("name", "Unknown")
        final_name = rolled_name if custom_name.lower() == "default" else custom_name
        self.mon_data["display_name"] = final_name
        level = 1
        # For simplicity, assume species1 equals the rolled name.
        species1, species2, species3 = rolled_name, "", ""
        types = self.mon_data.get("types", [])
        if not isinstance(types, list):
            types = [types]
        while len(types) < 5:
            types.append("")
        types = types[:5]
        cursor.execute("SELECT id FROM trainers WHERE user_id = ? AND LOWER(name)=?", (user_id, trainer.lower()))
        row = cursor.fetchone()
        if not row:
            await interaction.followup.send(f"Trainer '{trainer}' not found. Please add the trainer first.", ephemeral=True)
            return
        trainer_id = row[0]
        mon_id = add_mon(
            trainer_id, user_id, final_name, level,
            species1, species2, species3,
            types[0], types[1], types[2], types[3], types[4],
            self.mon_data.get("attribute", ""), self.mon_data.get("img_link", "")
        )
        db.commit()
        await interaction.followup.send(f"Registered mon **{final_name}** to trainer **{trainer}** successfully.", ephemeral=True)

async def register_mon(interaction, mon_data):
    """
    Launches the registration modal for a new mon.
    """
    modal = RegisterMonModal(mon_data)
    if hasattr(interaction, "response"):
        await interaction.response.send_modal(modal)
    else:
        await interaction.send_modal(modal)

async def assign_levels_to_mon(interaction, name: str, levels: int):
    """
    Assigns levels to a mon. If the new total level exceeds 100, the extra levels are
    converted into coins for the associated trainer. Currency is updated on a per-trainer basis.
    """
    user_id = str(interaction.user.id)
    # Retrieve the mon record (includes trainer_id, current level, and mon_id)
    cursor.execute("SELECT trainer_id, level, mon_id FROM mons WHERE name = ? AND player = ?", (name, user_id))
    res = cursor.fetchone()
    if not res:
        await interaction.response.send_message(f"Mon '{name}' not found or does not belong to you.", ephemeral=True)
        return
    trainer_id, current_level, mon_id = res
    cursor.execute("SELECT name FROM trainers WHERE id = ?", (trainer_id,))
    t_res = cursor.fetchone()
    if not t_res:
        await interaction.response.send_message("Trainer not found for that mon.", ephemeral=True)
        return
    trainer_name = t_res[0]
    # If the mon is already at or above level 100, all additional levels are converted to coins.
    if current_level >= 100:
        extra_coins = levels * 25
        add_currency(trainer_id, extra_coins)
        await interaction.response.send_message(
            f"Mon '{name}' is at level 100. Converted {levels} level(s) into {extra_coins} coins for trainer '{trainer_name}'.",
            ephemeral=True
        )
    # If the added levels would push the mon past level 100, split the levels.
    elif current_level + levels > 100:
        effective_levels = 100 - current_level
        excess = levels - effective_levels
        update_mon_row(mon_id, {"level": current_level + effective_levels})
        extra_coins = excess * 25
        add_currency(trainer_id, extra_coins)
        await interaction.response.send_message(
            f"Mon '{name}' reached level 100. Added {effective_levels} level(s) and converted {excess} extra level(s) into {extra_coins} coins for trainer '{trainer_name}'.",
            ephemeral=True
        )
    else:
        update_mon_row(mon_id, {"level": current_level + levels})
        await interaction.response.send_message(
            f"Added {levels} level(s) to mon '{name}'.",
            ephemeral=True
        )

def get_mons_for_trainer(trainer_id: int) -> list:
    """
    Retrieves all mons for the specified trainer.
    """
    cursor.execute("SELECT mon_id, name, level, img_link FROM mons WHERE trainer_id = ?", (trainer_id,))
    rows = cursor.fetchall()
    return [{"id": row[0], "name": row[1], "level": row[2], "img_link": row[3]} for row in rows]