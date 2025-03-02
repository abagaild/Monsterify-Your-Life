import random
from core.database import cursor, db, add_currency
from core.google_sheets import append_mon_to_sheet, update_character_sheet_level, update_character_sheet_item
import discord

from data.lists import no_evolution, mythical_list, legendary_list
from logic.market.farm import get_species_from_parent, fetch_mon_from_db


import random
import asyncio
import discord
from core.database import cursor, db, add_currency
from core.google_sheets import append_mon_to_sheet, update_character_sheet_level, update_character_sheet_item

def should_ignore_column(index: int) -> bool:
    if index == 1:
        return True
    if index in (3, 4):
        return True
    if 16 <= index <= 47:
        return True
    if 56 <= index <= 95:
        return True
    if 97 <= index <= 129:
        return True
    if index in (140, 141):
        return True
    if 143 <= index <= 149:
        return True
    if 152 <= index <= 172:
        return True
    return False

def get_mon(trainer_id: str, mon_name: str) -> dict:
    cursor.execute(
        "SELECT id, species1, species2, species3, type1, type2, type3, type4, type5, attribute FROM mons WHERE mon_name = ? AND player = ?",
        (mon_name, trainer_id)
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
            "mon_name": mon_name
        }
        mon["types"] = [t for t in mon["types"] if t]
        return mon
    return None

def randomize_mon(mon: dict, force_min_types: int = None) -> dict:
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
    Upon submission, it performs the full registration:
      * Looks up the trainer record.
      * Inserts the mon into the database.
      * Updates the trainer’s Google Sheet.
    """
    trainer_name = discord.ui.TextInput(
        label="Trainer Name",
        placeholder="Enter the trainer's name",
        required=True
    )
    custom_mon_name = discord.ui.TextInput(
        label="Custom Mon Name",
        placeholder="Enter a custom name (or type 'default' to keep the rolled name)",
        required=True
    )

    def __init__(self, mon_data):
        super().__init__()
        self.mon_data = mon_data

    async def on_submit(self, interaction: discord.Interaction):
        # Defer the response to avoid the 3‑second timeout.
        await interaction.response.defer(ephemeral=True)
        # If mon_data is a coroutine, await it.
        if asyncio.iscoroutine(self.mon_data):
            self.mon_data = await self.mon_data

        user_id = str(interaction.user.id)
        trainer = self.trainer_name.value.strip()
        custom_name = self.custom_mon_name.value.strip()
        rolled_name = self.mon_data.get("name", "Unknown")
        final_name = rolled_name if custom_name.lower() == "default" else custom_name
        self.mon_data["display_name"] = final_name
        level = 1
        # For simplicity, assume species1 equals the rolled name.
        species1, species2, species3 = rolled_name, "", ""
        # Ensure types list is 5 elements long.
        types = self.mon_data.get("types", [])
        if not isinstance(types, list):
            types = [types]
        while len(types) < 5:
            types.append("")
        types = types[:5]
        # Look up trainer in the database.
        cursor.execute("SELECT id FROM trainers WHERE user_id = ? AND LOWER(name)=?", (user_id, trainer.lower()))
        row = cursor.fetchone()
        if not row:
            await interaction.followup.send(f"Trainer '{trainer}' not found. Please add the trainer first.", ephemeral=True)
            return
        trainer_id = row[0]
        # Insert mon record.
        cursor.execute(
            """
            INSERT INTO mons (trainer_id, player, mon_name, level, species1, species2, species3,
                              type1, type2, type3, type4, type5, attribute, img_link)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (trainer_id, user_id, final_name, level, species1, species2, species3,
             types[0], types[1], types[2], types[3], types[4],
             self.mon_data.get("attribute", ""), self.mon_data.get("img_link", ""))
        )
        db.commit()
        # Prepare sheet row.
        sheet_row = ["", final_name, "", species1, species2, species3] + types + [self.mon_data.get("attribute", ""), "", self.mon_data.get("img_link", "")]
        error = await append_mon_to_sheet(trainer, sheet_row)
        if error:
            await interaction.followup.send(f"Mon added to database but failed to update sheet: {error}", ephemeral=True)
        else:
            await interaction.followup.send(f"Registered mon **{final_name}** to trainer **{trainer}** successfully.", ephemeral=True)
            await update_character_sheet_item(trainer, "Pokeball", -1)

async def register_mon(interaction, mon_data):
    """
    Initiates mon registration by prompting the user with a modal that collects
    both the trainer name and custom mon name.
    """
    modal = RegisterMonModal(mon_data)
    if hasattr(interaction, "response"):
        await interaction.response.send_modal(modal)
    else:
        await interaction.send_modal(modal)

async def assign_levels_to_mon(interaction, mon_name: str, levels: int):
    user_id = str(interaction.user.id)
    cursor.execute("SELECT trainer_id, level FROM mons WHERE mon_name = ? AND player = ?", (mon_name, user_id))
    res = cursor.fetchone()
    if not res:
        await interaction.response.send_message(f"Mon '{mon_name}' not found or does not belong to you.", ephemeral=True)
        return
    trainer_id, current_level = res
    cursor.execute("SELECT name FROM trainers WHERE id = ?", (trainer_id,))
    t_res = cursor.fetchone()
    if not t_res:
        await interaction.response.send_message("Trainer not found for that mon.", ephemeral=True)
        return
    trainer_name = t_res[0]
    if current_level >= 100:
        extra_coins = levels * 25
        add_currency(user_id, extra_coins)
        await interaction.response.send_message(
            f"Mon '{mon_name}' is at level 100. Converted {levels} level(s) into {extra_coins} coins.",
            ephemeral=True
        )
    elif current_level + levels > 100:
        effective_levels = 100 - current_level
        excess = levels - effective_levels
        success = await update_character_sheet_level(trainer_name, mon_name, effective_levels)
        if success:
            extra_coins = excess * 25
            add_currency(user_id, extra_coins)
            await interaction.response.send_message(
                f"Mon '{mon_name}' reached level 100. Added {effective_levels} level(s) and converted {excess} extra level(s) into {extra_coins} coins.",
                ephemeral=True
            )
        else:
            await interaction.response.send_message("Failed to update the mon's sheet.", ephemeral=True)
    else:
        success = await update_character_sheet_level(trainer_name, mon_name, levels)
        if success:
            await interaction.response.send_message(
                f"Added {levels} level(s) to mon '{mon_name}' on trainer {trainer_name}'s sheet.",
                ephemeral=True
            )
        else:
            await interaction.response.send_message("Failed to update the mon's sheet.", ephemeral=True)

def get_mons_for_trainer(trainer_id: int) -> list:
    cursor.execute("SELECT id, mon_name, level, img_link FROM mons WHERE trainer_id = ?", (trainer_id,))
    rows = cursor.fetchall()
    return [{"id": row[0], "mon_name": row[1], "level": row[2], "img_link": row[3]} for row in rows]

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
    cursor.execute(query, tuple(values))
    db.commit()

def is_mon_viable_for_breeding(mon_id: int) -> bool:
    mon = fetch_mon_from_db(mon_id)
    if mon is None:
        return False

    species_list = get_species_from_parent(mon)
    if not species_list and len(mon) > 3 and mon[3]:
        species_list = [mon[3].strip()]
    if not species_list:
        return True

    for sp in species_list:
        sp_lower = sp.strip().lower()
        cursor.execute('SELECT "Name" FROM YoKai WHERE lower("Name") = ?', (sp_lower,))
        if cursor.fetchone():
            continue
        cursor.execute('SELECT "Name", "Stage" FROM Digimon WHERE lower("Name") = ?', (sp_lower,))
        digimon_row = cursor.fetchone()
        if digimon_row:
            stage = digimon_row[1].strip().lower() if digimon_row[1] else ""
            if stage in ["training 1", "training 2", "baby", "fresh"]:
                return False
            else:
                continue
        if sp_lower in [x.lower() for x in legendary_list] or sp_lower in [x.lower() for x in mythical_list]:
            return False
        if sp_lower in [x.lower() for x in no_evolution]:
            continue
        cursor.execute('SELECT "Stage" FROM Pokemon WHERE lower("Name") = ?', (sp_lower,))
        pokemon_row = cursor.fetchone()
        if pokemon_row:
            stage = pokemon_row[0].strip().lower() if pokemon_row[0] else ""
            if stage == "final stage":
                continue
            elif stage in ["base stage", "middle stage"]:
                return False
    return True
