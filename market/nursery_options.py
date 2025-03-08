import json
import logging
import discord
from core.database import fetch_trainer_by_name

# Full list of valid EGGS category items.
EGGS_CATEGORY_ITEMS = {
    "standard egg", "incubator",
    "fire nurture kit", "water nurture kit", "electric nurture kit",
    "grass nurture kit", "ice nurture kit", "fighting nurture kit",
    "poison nurture kit", "ground nurture kit", "flying nurture kit",
    "psychic nurture kit", "bug nurture kit", "rock nurture kit",
    "ghost nurture kit", "dragon nurture kit", "dark nurture kit",
    "steel nurture kit", "fairy nurture kit", "normal nurture kit",
    "corruption code", "repair code", "shiny new code",
    "e-rank incense", "d-rank incense", "c-rank incense", "b-rank incense",
    "a-rank incense", "s-rank incense", "brave color incense", "mysterious color incense",
    "eerie color incense", "tough color incense", "charming color incense",
    "heartful color incense", "shady color incense", "slippery color incense",
    "wicked color incense", "fire poffin", "water poffin", "electric poffin",
    "grass poffin", "ice poffin", "fighting poffin", "poison poffin", "ground poffin",
    "flying poffin", "psychic poffin", "bug poffin", "rock poffin", "ghost poffin",
    "dragon poffin", "dark poffin", "steel poffin", "fairy poffin", "spell tag",
    "summoning stone", "digimeat", "digitofu", "soothe bell", "broken bell",
    "#data tag", "#vaccine tag", "#virus tag", "#free tag", "#variable tag",
    "dna splicer", "hot chocolate", "chocolate milk", "strawberry milk",
    "vanilla ice cream", "strawberry ice cream", "chocolate ice cream",
    "input field", "drop down", "radio buttons"
}

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
    Collects eligible nursery options by filtering the trainer's temporary inventory
    for any item that is in the EGGS category.
    If none are found, returns a default list.
    """
    options = [item for item in temp_inventory.keys() if item.lower() in EGGS_CATEGORY_ITEMS]
    if not options:
        options = ["Standard Egg", "Incubator"]  # default options if none found
    return options

async def select_trainer_callback(interaction: discord.Interaction, selected_value: str):
    """
    Callback for when a trainer is selected from the paginated dropdown.
    It re-fetches the user's trainers, finds the selected trainer,
    checks that the trainer has at least one "Standard Egg" in the "EGGS" category,
    and then proceeds with the egg roll.
    """
    from core.trainer import get_trainers_from_database
    from core.database import get_inventory_quantity
    user_id = str(interaction.user.id)
    trainers = get_trainers_from_database(user_id)
    selected_trainer = next((t for t in trainers if str(t["id"]) == selected_value), None)
    if not selected_trainer:
        await interaction.response.send_message("Invalid trainer selection.", ephemeral=True)
        return

    # Using modern keys; assume the trainer's display name is in "character_name"
    trainer_name = selected_trainer["character_name"]
    await interaction.response.send_message(f"Checking if **{trainer_name}** has eggs to hatch...", ephemeral=True)
    # Check if the trainer has at least one "Standard Egg" in the "EGGS" category.
    if get_inventory_quantity(selected_trainer["id"], "EGGS", "Standard Egg") >= 1:
        await interaction.followup.send(f"**{trainer_name}** has a Standard Egg. Proceeding with egg roll...", ephemeral=True)
        from market.nursery_options import get_temp_inventory, collect_nursery_options
        temp_inventory = get_temp_inventory(trainer_name)
        selections = await collect_nursery_options(interaction, trainer_name, temp_inventory)
        from core.database import get_inventory_quantity
        splicer_count = get_inventory_quantity(selected_trainer["id"], "EGGS", "DNA Splicer")
        max_select = 1 + splicer_count
        from market.nursery_roll import run_nursery_roll
        await run_nursery_roll(interaction, selections, trainer_name)
    else:
        await interaction.followup.send(f"**{trainer_name}** does not have any Standard Eggs.", ephemeral=True)
