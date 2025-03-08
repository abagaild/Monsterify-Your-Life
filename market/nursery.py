import logging
import random

import discord

from core.core_views import create_paginated_trainers_dropdown
from core.database import fetch_all
from market.nursery_options import get_temp_inventory, collect_nursery_options, select_trainer_callback
from core.items import check_inventory
from views.generic_shop import send_generic_shop_view


def get_trainers(user_id: str) -> list:
    """Retrieve trainers for the user from the database."""
    try:
        query = "SELECT id, character_name as name FROM trainers WHERE player_user_id = ?"
        rows = fetch_all(query, (user_id,))
        return [{'id': row["id"], 'name': row["name"]} for row in rows]
    except Exception as e:
        logging.error(f"Error fetching trainers for {user_id}: {e}")
        return []

async def run_nursery_activity(interaction: discord.Interaction, user_id: str):
    """
    Runs the complete nursery activity.
    Uses the modern inventory architecture to check for Standard Eggs and DNA Splicers.
    """
    await interaction.response.defer(ephemeral=True)
    trainers = get_trainers(user_id)
    if not trainers:
        await interaction.followup.send("No trainers found.", ephemeral=True)
        return

    if len(trainers) > 1:
        from core.core_views import create_paginated_trainers_dropdown
        async def trainer_selected_callback(inter, selected_value):
            selected_trainer = next((t for t in trainers if str(t["id"]) == selected_value), None)
            if not selected_trainer:
                await inter.response.send_message("Invalid trainer selection.", ephemeral=True)
                return
            await inter.response.send_message(f"Checking if **{selected_trainer['name']}** has eggs to hatch...", ephemeral=True)
            has_egg = check_inventory(user_id, selected_trainer['name'], "Standard Egg", 1, "EGGS")
            if has_egg:
                await inter.followup.send(f"**{selected_trainer['name']}** has a Standard Egg. Proceeding with egg roll...", ephemeral=True)
                temp_inventory = get_temp_inventory(selected_trainer['name'])
                selections = await collect_nursery_options(inter, selected_trainer['name'], temp_inventory)
                splicer_count, _ = check_inventory(user_id, selected_trainer['name'], "DNA Splicer", 0, "EGGS")
                max_select = 1 + splicer_count
                from market.nursery_roll import run_nursery_roll
                await run_nursery_roll(inter, selections, selected_trainer['name'])
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
        from market.nursery_roll import run_nursery_roll
        await run_nursery_roll(interaction, selections, trainer['name'])

class NurseryView(discord.ui.View):
    def __init__(self, user_id: str):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.image = random.choice([
"https://i.imgur.com/TZuUGws.png"        ])
        self.message = random.choice([
            "Welcome to the Nursery!",
            "Your eggs are about to hatch!",
            "Step into the Nursery to nurture your new companions."
        ])


    @discord.ui.button(label="Shop (Eggs)", style=discord.ButtonStyle.primary, custom_id="nursery_shop")
    async def shop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Use the generic shop view with filter "egg" for rolling eggs.
        await send_generic_shop_view(interaction, "nursery", self.user_id, category_filter="eggs")

    @discord.ui.button(label="Hatch Eggs", style=discord.ButtonStyle.secondary, custom_id="nursery_activity")
    async def activity_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await run_nursery_activity(interaction, self.user_id)

    async def callback(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        trainers = get_trainers(user_id)
        if not trainers:
            await interaction.response.send_message("No trainers found. Please create a trainer first.", ephemeral=True)
            return
        view = create_paginated_trainers_dropdown(trainers, "Select Trainer", callback=select_trainer_callback)
        await interaction.response.send_message("Select the trainer whose eggs you want to use:", view=view, ephemeral=True)


async def send_nursery_view(interaction: discord.Interaction, user_id: str):
    view = NurseryView(user_id)
    embed = discord.Embed(title="Nursery", description=view.message, color=discord.Color.green())
    embed.set_image(url=view.image)
    await interaction.followup.send(embed=embed, view=view, ephemeral=True)

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
    trainers = get_trainers(user_id)
    selected_trainer = next((t for t in trainers if str(t["id"]) == selected_value), None)
    if not selected_trainer:
        await interaction.response.send_message("Invalid trainer selection.", ephemeral=True)
        return

    # Using modern keys; assume the trainer's display name is in "character_name"
    trainer_name = selected_trainer["character_name"]
    await interaction.response.send_message(f"Checking if **{trainer_name}** has eggs to hatch...", ephemeral=True)
    # Check if the trainer has at least one "Standard Egg" in the "EGGS" category.
    if get_inventory_quantity(selected_trainer["id"], "EGGS", "Standard Egg") >= 1:
        await interaction.followup.send(f"**{trainer_name}** has a Standard Egg. Proceeding with egg roll...",
                                        ephemeral=True)
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