import logging
import discord
from core.database import fetch_all
from core.database import update_character_sheet_item
from logic.market.nursery_options import get_temp_inventory, collect_nursery_options
from logic.market.nursery_roll import run_egg_roll
from core.items import check_inventory  # Assumes check_inventory(user_id, trainer_name, item, amount)

def get_trainers(user_id: str) -> list:
    """Retrieve trainers for the user from the database."""
    try:
        query = "SELECT id, name FROM trainers WHERE player_user_id = ?"
        rows = fetch_all(query, (user_id,))
        return [{'id': row["id"], 'name': row["name"]} for row in rows]
    except Exception as e:
        logging.error(f"Error fetching trainers for {user_id}: {e}")
        return []

async def run_nursery_activity(interaction: discord.Interaction, user_id: str):
    """
    Runs the complete nursery activity.
    """
    await interaction.response.defer(ephemeral=True)
    trainers = get_trainers(user_id)
    if not trainers:
        await interaction.followup.send("No trainers found.", ephemeral=True)
        return

    # If multiple trainers exist, present a dropdown for selection.
    if len(trainers) > 1:
        from core.core_views import create_paginated_trainers_dropdown
        async def trainer_selected_callback(inter, selected_value):
            selected_trainer = next((t for t in trainers if str(t["id"]) == selected_value), None)
            if not selected_trainer:
                await inter.response.send_message("Invalid trainer selection.", ephemeral=True)
                return
            await inter.response.send_message(f"Checking if **{selected_trainer['name']}** has eggs to hatch...", ephemeral=True)
            has_egg, egg_msg = check_inventory(user_id, selected_trainer['name'], "Standard Egg", 1)
            if has_egg:
                await inter.followup.send(f"**{selected_trainer['name']}** has a Standard Egg. Proceeding with egg roll...", ephemeral=True)
                temp_inventory = get_temp_inventory(selected_trainer['name'])
                selections = await collect_nursery_options(inter, selected_trainer['name'], temp_inventory)
                splicer_count, _ = check_inventory(user_id, selected_trainer['name'], "DNA Splicer", 0)
                max_select = 1 + splicer_count
                await run_egg_roll(inter, selected_trainer['name'], selections, max_select)
            else:
                await inter.followup.send(f"**{selected_trainer['name']}** does not have any Standard Eggs. {egg_msg}", ephemeral=True)
        view = create_paginated_trainers_dropdown(trainers, "Select the trainer whose eggs you want to hatch:", trainer_selected_callback)
        await interaction.followup.send("Please select a trainer:", view=view, ephemeral=True)
    else:
        trainer = trainers[0]
        has_egg, egg_msg = check_inventory(user_id, trainer['name'], "Standard Egg", 1)
        if not has_egg:
            await interaction.followup.send(f"{trainer['name']} does not have a Standard Egg.", ephemeral=True)
            return
        await interaction.followup.send(f"Using trainer **{trainer['name']}**. Checking inventory...", ephemeral=True)
        temp_inventory = get_temp_inventory(trainer['name'])
        selections = await collect_nursery_options(interaction, trainer['name'], temp_inventory)
        splicer_count, _ = check_inventory(user_id, trainer['name'], "DNA Splicer", 0)
        max_select = 1 + splicer_count
        await run_egg_roll(interaction, trainer['name'], selections, max_select)
