# views/view_Adventure.py
import discord
import json
import random
from typing import List

from core import config

# Static image used for region selection.
STATIC_REGION_SELECT_IMAGE = "https://i.imgur.com/R48BhNs.png"

# Mapping of regions to image URLs.
REGION_IMAGES = {
    "Forest": "https://i.imgur.com/jtOqNRt.jpeg",
    "Mountain": "https://example.com/mountain.png",
    "Desert": "https://example.com/desert.png",
    # Add more region-image pairs as needed.
}

class AdventureView(discord.ui.View):
    def __init__(self, user_id: str):
        """
        Initializes the adventure view by loading adventure data and prompting region selection.
        """
        super().__init__(timeout=None)
        self.user_id = user_id
        with open("data/adventures.JSON", "r") as f:
            self.adventures_data = json.load(f)
        self.regions: List[str] = list(self.adventures_data.keys())
        self.add_item(RegionSelect(self.regions))

class RegionSelect(discord.ui.Select):
    def __init__(self, regions: List[str]):
        options = [discord.SelectOption(label=region) for region in regions]
        super().__init__(
            placeholder="Select a region",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="region_select"
        )

    async def callback(self, interaction: discord.Interaction):
        selected_region = self.values[0]
        region_data = self.view.adventures_data.get(selected_region, {})
        areas = list(region_data.get("areas", {}).keys())
        if not areas:
            await interaction.response.send_message("No areas found for this region.", ephemeral=True)
            return

        # Look up the image for the selected region.
        region_image = REGION_IMAGES.get(selected_region)
        self.view.clear_items()
        self.view.add_item(AreaSelect(selected_region, areas))
        embed = discord.Embed(
            title=f"Region **{selected_region}** selected",
            description="Now choose an area:",
            color=discord.Color.blue()
        )
        if region_image:
            embed.set_image(url=region_image)
        await interaction.response.edit_message(embed=embed, view=self.view)

class AreaSelect(discord.ui.Select):
    def __init__(self, region: str, areas: List[str]):
        self.region = region
        options = [discord.SelectOption(label=area) for area in areas]
        super().__init__(
            placeholder="Select an area",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        selected_area = self.values[0]
        region_data = self.view.adventures_data.get(self.region, {})
        area_data = region_data.get("areas", {}).get(selected_area, {})
        embed = discord.Embed(
            title=f"Area **{selected_area}** selected",
            description="Choose your adventure mode:",
            color=discord.Color.blue()
        )
        region_image = REGION_IMAGES.get(self.region)
        if region_image:
            embed.set_image(url=region_image)
        mode_view = ModeSelectView(self.region, selected_area, area_data)
        await interaction.response.edit_message(embed=embed, view=mode_view)

class ModeSelectView(discord.ui.View):
    def __init__(self, region: str, area: str, area_data: dict):
        super().__init__(timeout=180)
        self.region = region
        self.area = area
        self.area_data = area_data

    @discord.ui.button(label="Hard Mode (Sudden Death)", style=discord.ButtonStyle.danger)
    async def hard_mode(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        await self.start_adventure(interaction, hard_mode=True)

    @discord.ui.button(label="Easy Mode (Leisurely Exploration)", style=discord.ButtonStyle.success)
    async def easy_mode(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        await self.start_adventure(interaction, hard_mode=False)

    async def start_adventure(self, interaction: discord.Interaction, hard_mode: bool) -> None:
        # Ensure the command is used in the designated adventure channel.
        if interaction.channel.id != config.ADVENTURE_CHANNEL_ID:
            await interaction.followup.send("This command can only be used in the designated adventure channel.", ephemeral=True)
            return
        mode_text = "Hard Mode" if hard_mode else "Easy Mode"
        dialogue_options = self.area_data.get("intro_dialogue_options", [])
        dialogue = random.choice(dialogue_options) if dialogue_options else "No dialogue available."
        embed = discord.Embed(
            title=f"Adventure: {self.area} - {mode_text}",
            description=dialogue,
            color=discord.Color.blue()
        )
        await interaction.channel.send(embed=embed)
        await interaction.followup.send(f"Starting adventure in {mode_text}!", ephemeral=True)
        from OLD.logic.adventure import AdventureSession
        session = AdventureSession(interaction.channel, self.area_data, hard_mode=hard_mode)
        # Inform players that the session has started.
        await interaction.channel.send("Adventure session started! Type your messages to progress, 'next' for encounters, or 'end' to finish.")
