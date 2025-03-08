import asyncio
import logging
from core.database import (
    fetch_trainer_by_name, get_trainers_from_database, add_trainer, delete_trainer, update_trainer_field, get_all_trainers
)

def list_trainers(user_id: str) -> list:
    """
    Retrieves all trainer records for the given user.
    """
    return get_trainers_from_database(user_id)

def create_trainer(user_id: str, name: str, level: int = 1, main_ref: str = ""):
    """
    Adds a new trainer to the database.
    """
    return add_trainer(user_id, name, level, main_ref)

def remove_trainer(user_id: str, trainer_name: str):
    """
    Deletes a trainer by name.
    """
    return delete_trainer(user_id, trainer_name)

async def assign_levels_to_trainer(interaction, trainer_name: str, levels: int):
    """
    Assigns levels to a trainer.
    """
    user_id = str(interaction.user.id)
    trainer = fetch_trainer_by_name(trainer_name)

    if not trainer:
        await interaction.response.send_message(f"Trainer '{trainer_name}' not found.", ephemeral=True)
        return

    new_level = trainer["level"] + levels
    update_trainer_field(trainer["id"], "level", new_level)

    await interaction.response.send_message(
        f"Assigned {levels} levels to trainer '{trainer_name}'. New level: {new_level}.",
        ephemeral=True
    )

    trainer_id = trainer["id"]
    asyncio.create_task(level_up_check_trainer(trainer_id, new_level))

def list_all_trainers() -> list:
    """
    Retrieves all trainers in the database.
    """
    return get_all_trainers()


# Define prompt thresholds for trainers.
PROMPT_LEVELS = [10, 25, 50, 75, 100]


async def level_up_check_trainer(trainer_id: int, new_level: int):
    """
    Background function to check trainer level-ups.
    - Computes a new level modifier (new_level // 100)
    - If the new modifier is higher than the stored one, updates the trainer record and sends a message.
    - Checks if the trainer has passed any threshold levels and, if so, sends a prompt message.
    """
    # Retrieve the full trainer record.
    conn = pool.get_connection()
    try:
        conn.row_factory = lambda cursor, row: {col[0]: row[idx] for idx, col in enumerate(cursor.description)}
        cur = conn.cursor()
        cur.execute("SELECT * FROM trainers WHERE id = ?", (trainer_id,))
        trainer = cur.fetchone()
        if not trainer:
            return
    finally:
        pool.return_connection(conn)

    user_id = trainer.get("player_user_id", "unknown")
    # Calculate new level modifier.
    new_modifier = new_level // 100
    old_modifier = trainer.get("level_modifier", 0)
    if new_modifier > old_modifier:
        update_trainer_field(trainer_id, "level_modifier", new_modifier)
        await send_player_message(user_id, f"Congratulations! Your level modifier increased to {new_modifier}.")

    # Check prompt thresholds.
    # (Assuming the trainer record has a field 'last_prompt_level' to track the highest prompt given.)
    last_prompt = trainer.get("last_prompt_level", 0)
    for prompt_level in PROMPT_LEVELS:
        if last_prompt < prompt_level <= new_level:
            update_trainer_field(trainer_id, "last_prompt_level", prompt_level)
            await send_player_message(user_id,
                                      f"You've reached level {new_level} and unlocked a new prompt: 'Prompt for level {prompt_level}'.")
    # End of trainer level-up check.