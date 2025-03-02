import logging

import discord
from logic.market.nursery_options import get_temp_inventory, collect_nursery_options

from core.database import cursor
from core.google_sheets import update_character_sheet_item
# Assume register_mon is defined in core.mon (centralized registration modal)
from core.mon import register_mon
from core.rollmons import roll_single_mon

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Nursery images and messages.
IMAGES = [
    "https://example.com/nursery1.png",
    "https://example.com/nursery2.png",
    "https://example.com/nursery3.png"
]
MESSAGES = [
    "Welcome to the Nursery!",
    "Your eggs are about to hatch!",
    "Step into the Nursery to nurture your new companions."
]


def get_trainers(user_id: str) -> list:
    """Retrieve trainers for the user from the database."""
    try:
        cursor.execute("SELECT id, name FROM trainers WHERE user_id = ?", (user_id,))
        return [{'id': row[0], 'name': row[1]} for row in cursor.fetchall()]
    except Exception as e:
        logging.error(f"Error fetching trainers for {user_id}: {e}")
        return []


async def run_nursery_activity(interaction: discord.Interaction, user_id: str):
    """
    Runs the complete nursery activity:
      1. Retrieve trainers (using the common get_trainers function)
      2. If multiple trainers exist, select the first one (or use a generic selection if desired)
      3. Check inventory for a Standard Egg and count available DNA Splicers
      4. Retrieve temporary inventory and collect nursery options
      5. Build a mon pool (by combining available Pokémon, Digimon, and Yo-Kai)
      6. Roll 10 mons
      7. Let the user register one mon (here we simply select the first rolled mon for simplicity)
      8. Remove the used egg (and DNA Splicers) from the trainer’s inventory
    """
    await interaction.response.defer(ephemeral=True)

    # Step 1: Retrieve trainers.
    trainers = get_trainers(user_id)
    if not trainers:
        await interaction.followup.send("No trainers found.", ephemeral=True)
        return
    # For simplicity, choose the first trainer.
    trainer = trainers[0]
    trainer_name = trainer['name']
    trainer_id = trainer['id']

    # Step 2: Check inventory for a Standard Egg and DNA Splicer count.
    from core.items import check_inventory  # Assumes this function exists in your core Google Sheets module.
    has_egg, egg_msg = check_inventory(user_id, trainer_name, "Standard Egg", 1)
    if not has_egg:
        await interaction.followup.send(f"{trainer_name} does not have a Standard Egg.", ephemeral=True)
        return
    splicer_count, _ = check_inventory(user_id, trainer_name, "DNA Splicer", 0)
    max_select = 1 + splicer_count  # Allows one by default plus extras per splicer.

    # Step 3: Retrieve temporary inventory and collect nursery options.
    temp_inventory = get_temp_inventory(trainer_name)
    selections = await collect_nursery_options(interaction, trainer_name, temp_inventory)
    logging.debug(f"Nursery selections: {selections}")

    # Step 4: Build the mon pool.
    # For simplicity, combine all available mons from the data sources.
    pokemon_pool = roll_single_mon.__globals__.get('fetch_pokemon_data', lambda: [])()
    digimon_pool = roll_single_mon.__globals__.get('fetch_digimon_data', lambda: [])()
    yokai_pool = roll_single_mon.__globals__.get('fetch_yokai_data', lambda: [])()
    pool = pokemon_pool + digimon_pool + yokai_pool
    if not pool:
        await interaction.followup.send("No valid mons available.", ephemeral=True)
        return

    # Step 5: Roll 10 mons.
    rolled_mons = [roll_single_mon(pool) for _ in range(10)]
    mon_names = [mon['name'] for mon in rolled_mons]
    await interaction.followup.send(f"Rolled mons: {mon_names}", ephemeral=True)

    # Step 6: For simplicity, automatically register the first rolled mon.
    selected_mon = rolled_mons[0]
    await register_mon(interaction, selected_mon)

    # Step 7: Remove used Standard Egg and DNA Splicer items.
    await update_character_sheet_item(trainer_name, "Standard Egg", -1)
    if splicer_count > 0:
        await update_character_sheet_item(trainer_name, "DNA Splicer", -splicer_count)

    await interaction.followup.send("Nursery activity complete.", ephemeral=True)
