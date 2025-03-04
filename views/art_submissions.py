# views/art_submission.py
import discord
from discord.ui import View, Modal, TextInput, Button
from logic.art_submissions import process_reference_art, process_game_art, launch_bonus_view

class ArtSubmissionTypeView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Reference Art", style=discord.ButtonStyle.success, custom_id="art_ref", row=0)
    async def reference_art(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(ReferenceArtModal())

    @discord.ui.button(label="Game Art", style=discord.ButtonStyle.primary, custom_id="art_game", row=0)
    async def game_art(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(GameArtModal())

    @discord.ui.button(label="Other Art", style=discord.ButtonStyle.secondary, custom_id="art_other", row=0)
    async def other_art(self, interaction: discord.Interaction, button: Button):
        # Use the updated launch_bonus_view from logic.art_submissions
        await launch_bonus_view(interaction, art_type="other")

class ReferenceArtModal(Modal, title="Reference Art Submission"):
    mon_name = TextInput(label="Mon Name", placeholder="Enter the mon's name", required=True)
    image_link = TextInput(label="Image URL", placeholder="Enter the image link", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        result = await process_reference_art(interaction, self.mon_name.value, self.image_link.value)
        await interaction.followup.send(result, ephemeral=True)

class GameArtModal(Modal, title="Game Art Submission"):
    num_characters = TextInput(label="Number of Characters", placeholder="Enter a number", required=True)
    character_names = TextInput(label="Character Names", placeholder="Enter names separated by commas", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            num = int(self.num_characters.value)
        except ValueError:
            await interaction.followup.send("Invalid number.", ephemeral=True)
            return
        names = [n.strip() for n in self.character_names.value.split(",") if n.strip()]
        if len(names) != num:
            await interaction.followup.send("Mismatch between number entered and names provided.", ephemeral=True)
            return
        result = await process_game_art(interaction, names)
        await interaction.followup.send(result, ephemeral=True)
