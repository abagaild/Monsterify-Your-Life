import json
import logging

import discord

from core.database import fetch_trainer_by_name

def get_temp_inventory(trainer_name: str) -> dict:
    """
    Retrieves the trainer's inventory (stored as JSON) and returns it as a dictionary.
    """
    trainer = fetch_trainer_by_name(trainer_name)
    if not trainer:
        logging.error(f"Trainer {trainer_name} not found in get_temp_inventory.")
        return {}
    inv_str = trainer.get("inventory", "{}")
    try:
        inventory = json.loads(inv_str) if inv_str else {}
    except Exception as e:
        logging.error(f"Error parsing inventory for {trainer_name}: {e}")
        inventory = {}
    return inventory

async def collect_nursery_options(interaction: discord.Interaction, trainer_name: str, temp_inventory: dict) -> list:
    """
    Based on the trainer's inventory, this function collects eligible nursery options.
    For demonstration, we assume that any item whose name contains "nursery" is a valid option.
    If none are found, returns a default list.
    """
    options = [item for item in temp_inventory.keys() if "nursery" in item.lower()]
    if not options:
        options = ["Standard Hatch", "Advanced Hatch"]
    return options
