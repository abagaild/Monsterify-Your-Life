# logic/writing_submissions.py
import math
import discord
from core.currency import add_currency
from core.database import db
from core.google_sheets import update_character_sheet_level

async def process_writing_submission(
    writing_type: str,
    word_count: int,
    bonus_options: dict,
    extra_bonus: int = 0,
    difficulty_value: int = 0,
    game_art_data: dict = None,
    recipient: str = None,
    interaction: discord.Interaction = None
) -> dict:
    base_bonus = 2 if writing_type.lower() == "professional" else 0
    bonus = base_bonus
    if bonus_options.get("poetry"):
        bonus += 4
    if bonus_options.get("world_building"):
        bonus += 3
    if bonus_options.get("foreign_language"):
        bonus += 4

    difficulty_val = bonus_options.get("difficulty", 0) + difficulty_value
    bonus += difficulty_val * 2
    if bonus_options.get("editing"):
        bonus //= 2

    total_bonus = bonus + extra_bonus
    levels_from_words = word_count // 100
    total_levels = levels_from_words + total_bonus
    coins = total_levels * 50
    num_rolls = total_levels // 5

    assigned_levels = {}
    if game_art_data:
        participants = game_art_data.get("trainers", []) + game_art_data.get("mons", [])
        if participants:
            levels_each = math.ceil(total_levels / len(participants))
            assigned_levels = {participant: levels_each for participant in participants}
            # For each trainer or mon, update their sheets accordingly…
        else:
            assigned_levels = {}
    else:
        if recipient:
            assigned_levels = {recipient: total_levels}
            if interaction:
                if recipient.lower().startswith("t:"):
                    trainer_name = recipient[2:].strip()
                    await update_character_sheet_level(trainer_name, trainer_name, total_levels)
                    assigned_levels = {}
                elif recipient.lower().startswith("m:"):
                    mon_name = recipient[2:].strip()
                    row = db.fetch_one("SELECT trainer_id FROM mons WHERE mon_name = ?", (mon_name,))
                    if row:
                        trainer_id = row[0]
                        trainer_row = db.fetch_one("SELECT name FROM trainers WHERE id = ?", (trainer_id,))
                        if trainer_row:
                            await update_character_sheet_level(trainer_row[0], mon_name, total_levels)
                    assigned_levels = {}
        else:
            assigned_levels = {}

    add_currency(str(interaction.user.id) if interaction else "unknown", coins)
    return {
        "total_levels": total_levels,
        "coins": coins,
        "num_rolls": num_rolls,
        "assigned_levels": assigned_levels
    }
