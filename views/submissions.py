# views/view_submissions.py
import discord
from discord.ui import View, Button
from discord import Interaction

from Battles.battle_ui import SummonBattleMenuButton


class SubmissionTypeView(View):
    def __init__(self, user_id: str):
        """
        Initializes the top-level submission menu view.
        :param user_id: The ID of the user for whom this menu is being displayed.
        """
        super().__init__(timeout=None)
        self.user_id = user_id
        self.add_item(SummonBattleMenuButton())

    @discord.ui.button(label="Art Submission", style=discord.ButtonStyle.primary, custom_id="submission_art")
    async def art_submission(self, interaction: Interaction, button: Button):
        from views.art_submissions import ArtSubmissionTypeView  # Ensure this path is correct
        art_view = ArtSubmissionTypeView()
        if not interaction.response.is_done():
            await interaction.response.send_message("Proceed with Art Submission:", view=art_view, ephemeral=True)
        else:
            await interaction.followup.send("Proceed with Art Submission:", view=art_view, ephemeral=True)

    @discord.ui.button(label="Writing Submission", style=discord.ButtonStyle.primary, custom_id="submission_writing")
    async def writing_submission(self, interaction: Interaction, button: Button):
        from views.writing_submissions import WritingSubmissionTypeView  # Ensure this path is correct
        writing_view = WritingSubmissionTypeView()
        if not interaction.response.is_done():
            await interaction.response.send_message("Proceed with Writing Submission:", view=writing_view, ephemeral=True)
        else:
            await interaction.followup.send("Proceed with Writing Submission:", view=writing_view, ephemeral=True)

    @discord.ui.button(label="Battle", style=discord.ButtonStyle.primary, custom_id="submission_music")
    async def battle_button(self, interaction: Interaction, button: Button):
        from Battles.battle_ui import BattleMenuView
        battle_view = BattleMenuView()
        if not interaction.response.is_done():
            await interaction.response.send_message("Proceed with Battle:", view=battle_view, ephemeral=True)
        else:
            await interaction.followup.send("Proceed with Battle:", view=battle_view, ephemeral=True)