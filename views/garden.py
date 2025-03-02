# views/view_garden.py
import discord
from discord.ui import View, Button
from logic.garden import process_garden, claim_garden_harvest

class GardenView(View):
    def __init__(self, user_id: str):
        """
        Initializes the Garden view with two separate buttons.
        """
        super().__init__(timeout=None)
        self.user_id = user_id
        self.add_item(TendGardenButton())
        self.add_item(HarvestGardenButton())

class TendGardenButton(Button):
    def __init__(self):
        super().__init__(label="Tend Garden", style=discord.ButtonStyle.primary, custom_id="garden_tend")

    async def callback(self, interaction: discord.Interaction):
        # Defer the interaction response and process a garden task (tend mode)
        await interaction.response.defer(ephemeral=True)
        await process_garden(interaction, mode="tend")

class HarvestGardenButton(Button):
    def __init__(self):
        super().__init__(label="Harvest Garden", style=discord.ButtonStyle.secondary, custom_id="garden_harvest")

    async def callback(self, interaction: discord.Interaction):
        # Defer the interaction response and claim the harvest
        await interaction.response.defer(ephemeral=True)
        await claim_garden_harvest(interaction)
