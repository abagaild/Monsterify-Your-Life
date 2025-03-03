# nursery.py
"""
Nursery Module: Provides the user interface for the nursery system,
allowing players to choose between shopping for eggs and performing
the nurture activity. It handles trainer selection, inventory checks,
and transitions to the option selection view.
"""

import discord
from core.core_views import create_paginated_trainers_dropdown
from core.trainer import get_trainers, get_temporary_inventory_columns
import logic.market.nursery_options  # custom module for option dropdowns
import random

class NurseryView(discord.ui.View):
    def __init__(self, user_id: str):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.image = random.choice([
            "https://example.com/nursery1.png",
            "https://example.com/nursery2.png",
            "https://example.com/nursery3.png"
        ])
        self.message = random.choice([
            "Welcome to the Nursery!",
            "Your eggs are about to hatch!",
            "Step into the Nursery to nurture your new companions."
        ])

    @discord.ui.button(label="Shop (Eggs)", style=discord.ButtonStyle.primary, custom_id="nursery_shop")
    async def shop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Use the generic shop view with filter "egg" for rolling eggs.
        await send_generic_shop_view(interaction, "nursery", self.user_id, category_filter="egg")

    async def callback(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        trainers = get_trainers(user_id)
        if not trainers:
            await interaction.response.send_message("No trainers found. Please create a trainer first.", ephemeral=True)
            return
        # If multiple trainers, present a paginated dropdown to select a trainer.
        view = create_paginated_trainers_dropdown(trainers, "Select Trainer", callback=select_trainer_callback)
        await interaction.response.send_message("Select the trainer whose eggs you want to use:", view=view,
                                                ephemeral=True)

async def send_nursery_view(interaction: discord.Interaction, user_id: str):
    view = NurseryView(user_id)
    embed = discord.Embed(title="Nursery", description=view.message, color=discord.Color.green())
    embed.set_image(url=view.image)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
