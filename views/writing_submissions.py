# views/writing_submissions.py
import discord
from discord.ui import View, Modal, TextInput, Select
import asyncio
from logic.writing_submissions import process_writing_submission

class WritingBonusSelectView(View):
    def __init__(self):
        super().__init__(timeout=60)
        self.selected_values = None
        options = [
            discord.SelectOption(label="poetry", description="Add +4 levels", value="poetry"),
            discord.SelectOption(label="world_building", description="Add +3 levels", value="world_building"),
            discord.SelectOption(label="foreign_language", description="Add +4 levels", value="foreign_language"),
            discord.SelectOption(label="editing", description="Halve bonus levels", value="editing"),
            discord.SelectOption(label="No Bonus", description="Proceed with no bonus", value="none"),
        ]
        self.select = Select(
            placeholder="Select bonus options (Ctrl+Click for multiple)",
            min_values=0,
            max_values=len(options),
            options=options
        )
        self.select.callback = self.select_callback
        self.add_item(self.select)

    async def select_callback(self, interaction: discord.Interaction):
        values = self.select.values
        if "none" in values and len(values) > 1:
            values.remove("none")
        self.selected_values = values
        await interaction.response.send_message("Bonus options recorded.", ephemeral=True)
        self.stop()

async def launch_writing_game_interactive(interaction: discord.Interaction, word_count: int):
    """
    Interactive flow for game writing submissions:
      1. Presents a bonus selection dropdown.
      2. Prompts for a difficulty value.
      3. Requests participant names.
      4. Calls the logic function to process the submission.
    """
    def check(m):
        return m.author.id == interaction.user.id and m.channel == interaction.channel

    bonus_view = WritingBonusSelectView()
    await interaction.followup.send("**Game Writing:** Please select bonus options:", view=bonus_view, ephemeral=True)
    await bonus_view.wait()
    bonus_opts = {opt: True for opt in (bonus_view.selected_values or []) if opt != "none"}

    try:
        await interaction.followup.send("Enter a difficulty value (or '0' if none):", ephemeral=True)
        diff_msg = await interaction.client.wait_for("message", check=check, timeout=30)
        diff_value = int(diff_msg.content.strip())
    except (asyncio.TimeoutError, ValueError):
        diff_value = 0

    try:
        await interaction.followup.send("Enter participant names (comma separated):", ephemeral=True)
        part_msg = await interaction.client.wait_for("message", check=check, timeout=30)
        participants = [name.strip() for name in part_msg.content.split(",") if name.strip()]
    except asyncio.TimeoutError:
        participants = []

    game_art_data = {"trainers": participants, "mons": []}
    result = await process_writing_submission(
        writing_type="game",
        word_count=word_count,
        bonus_options=bonus_opts,
        difficulty_value=diff_value,
        game_art_data=game_art_data,
        interaction=interaction
    )
    msg = (f"Game Writing Submission Processed:\n"
           f"Word Count: {word_count}\n"
           f"Total Levels: {result.get('total_levels', 0)}\n"
           f"Coins: {result.get('coins', 0)}")
    await interaction.followup.send(msg, ephemeral=True)

async def launch_writing_other_interactive(interaction: discord.Interaction, word_count: int):
    """
    Interactive flow for other writing submissions:
      1. Presents a bonus selection dropdown.
      2. Prompts for a difficulty value.
      3. Requests the recipient (using 'T:' for trainer or 'M:' for mon).
      4. Processes the submission.
    """
    def check(m):
        return m.author.id == interaction.user.id and m.channel == interaction.channel

    bonus_view = WritingBonusSelectView()
    await interaction.followup.send("**Other Writing:** Please select bonus options:", view=bonus_view, ephemeral=True)
    await bonus_view.wait()
    bonus_opts = {opt: True for opt in (bonus_view.selected_values or []) if opt != "none"}

    try:
        await interaction.followup.send("Enter a difficulty value (or '0' if none):", ephemeral=True)
        diff_msg = await interaction.client.wait_for("message", check=check, timeout=30)
        diff_value = int(diff_msg.content.strip())
    except (asyncio.TimeoutError, ValueError):
        diff_value = 0

    try:
        await interaction.followup.send("Enter recipient (use 'T:TrainerName' or 'M:MonName'):", ephemeral=True)
        rec_msg = await interaction.client.wait_for("message", check=check, timeout=30)
        recipient = rec_msg.content.strip()
    except asyncio.TimeoutError:
        recipient = ""

    result = await process_writing_submission(
        writing_type="other",
        word_count=word_count,
        bonus_options=bonus_opts,
        difficulty_value=diff_value,
        recipient=recipient,
        interaction=interaction
    )
    msg = (f"Other Writing Submission Processed:\n"
           f"Word Count: {word_count}\n"
           f"Total Levels: {result.get('total_levels', 0)}\n"
           f"Coins: {result.get('coins', 0)}")
    await interaction.followup.send(msg, ephemeral=True)

class WritingSubmissionTypeView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Game Writing", style=discord.ButtonStyle.primary, custom_id="writing_game", row=0)
    async def game_writing(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(GameWritingModal())

    @discord.ui.button(label="Other Writing", style=discord.ButtonStyle.primary, custom_id="writing_other", row=0)
    async def other_writing(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(OtherWritingModal())

class GameWritingModal(Modal, title="Game Writing Submission"):
    word_count = TextInput(label="Word Count", placeholder="Enter total word count", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            wc = int(self.word_count.value)
        except ValueError:
            await interaction.response.send_message("Invalid word count.", ephemeral=True)
            return
        await launch_writing_game_interactive(interaction, wc)

class OtherWritingModal(Modal, title="Other Writing Submission"):
    word_count = TextInput(label="Word Count", placeholder="Enter total word count", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            wc = int(self.word_count.value)
        except ValueError:
            await interaction.response.send_message("Invalid word count.", ephemeral=True)
            return
        await launch_writing_other_interactive(interaction, wc)
