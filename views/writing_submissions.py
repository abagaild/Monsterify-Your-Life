import math
import discord
import asyncio

from core.database import (
    addsub_trainer_currency,
    fetch_one,
    execute_query,
    update_character_level
)


# --------------------- PROCESSING FUNCTION ---------------------
async def process_writing_submission(
        writing_type: str,
        word_count: int,
        bonus_options: dict,
        extra_bonus: int = 0,
        difficulty_value: int = 0,
        game_art_data: dict = None,
        recipient: str = None,
        interaction: discord.Interaction = None
) -> dict:
    """
    Processes a writing submission by computing bonus levels based on:
      - writing type (professional vs. other),
      - word count,
      - bonus options,
      - additional difficulty,
      - and extra bonus.

    If game_art_data is provided, bonus levels are split among participants.
    If a recipient is provided (for 'other' writing), the recipient's level is updated.

    Returns a dictionary with:
      total_levels, coins, num_rolls, and assigned_levels.
    """
    if interaction and not interaction.response.is_done():
        await interaction.response.defer(ephemeral=True)

    base_bonus = 2 if writing_type.lower() == "professional" else 0
    bonus = base_bonus
    if bonus_options.get("poetry"):
        bonus += 4
    if bonus_options.get("world_building"):
        bonus += 3
    if bonus_options.get("foreign_language"):
        bonus += 4

    # Apply difficulty factor (each unit adds 2 levels) and any extra bonus.
    difficulty_val = bonus_options.get("difficulty", 0) + difficulty_value
    bonus += difficulty_val * 2
    if bonus_options.get("editing"):
        bonus //= 2

    total_bonus = bonus + extra_bonus
    levels_from_words = word_count // 100
    total_levels = levels_from_words + total_bonus
    coins = total_levels * 50
    num_rolls = total_levels // 5

    assigned_levels = {}
    if game_art_data:
        participants = game_art_data.get("trainers", []) + game_art_data.get("mons", [])
        if participants:
            levels_each = math.ceil(total_levels / len(participants))
            assigned_levels = {participant: levels_each for participant in participants}
            # Update each participant's level.
            for participant in participants:
                await update_character_level(participant, participant, levels_each)
        else:
            assigned_levels = {}
    else:
        if recipient:
            assigned_levels = {recipient: total_levels}
            if interaction:
                if recipient.lower().startswith("t:"):
                    trainer_name_input = recipient[2:].strip()
                    await update_character_level(trainer_name_input, trainer_name_input, total_levels)
                    assigned_levels = {}
                    trainer_ID = fetch_one("SELECT id FROM trainers WHERE character_name = ? COLLATE NOCASE",)
                    addsub_trainer_currency(trainer_ID, coins)
                elif recipient.lower().startswith("m:"):
                    mon_name_input = recipient[2:].strip()
                    row = fetch_one("SELECT trainer_id FROM mons WHERE name = ? COLLATE NOCASE", (mon_name_input,))
                    if row:
                        trainer_id = row["trainer_id"]
                        addsub_trainer_currency(trainer_id, coins)
                        trainer_row = fetch_one("SELECT character_name FROM trainers WHERE id = ?", (trainer_id,))
                        if trainer_row:
                            await update_character_level(trainer_row["character_name"], mon_name_input, total_levels)
                    assigned_levels = {}

        else:
            assigned_levels = {}



    return {
        "total_levels": total_levels,
        "coins": coins,
        "num_rolls": num_rolls,
        "assigned_levels": assigned_levels
    }


# --------------------- INTERACTIVE FLOWS ---------------------
async def launch_writing_game_interactive(interaction: discord.Interaction, word_count: int, recipient: str = None):
    """
    Interactive flow for game writing submissions:
      1. Presents a bonus selection dropdown.
      2. Prompts for a difficulty value.
      3. Requests participant names.
      4. Processes the submission.
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
        recipient=recipient,
        interaction=interaction
    )
    msg = (f"Game Writing Submission Processed:\n"
           f"Word Count: {word_count}\n"
           f"Total Levels: {result.get('total_levels', 0)}\n"
           f"Coins: {result.get('coins', 0)}")
    await interaction.followup.send(msg, ephemeral=True)


async def launch_writing_other_interactive(interaction: discord.Interaction, word_count: int, recipient: str):
    """
    Interactive flow for other writing submissions:
      1. Presents a bonus selection dropdown.
      2. Prompts for a difficulty value.
      3. Processes the submission using the provided recipient.
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


# --------------------- BONUS SELECTION VIEW ---------------------
class WritingBonusSelectView(discord.ui.View):
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
        self.select = discord.ui.Select(
            placeholder="Select bonus options (Ctrl+Click for multiple)",
            min_values=0,
            max_values=len(options),
            options=options,
            custom_id="writing_bonus_select"
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


# --------------------- MODAL CLASSES & TOP-LEVEL VIEW ---------------------
class GameWritingModal(discord.ui.Modal, title="Game Writing Submission"):
    word_count = discord.ui.TextInput(label="Word Count", placeholder="Enter total word count", required=True)
    recipient = discord.ui.TextInput(
        label="Recipient (Optional)",
        placeholder="Enter 'T:TrainerName' or 'M:MonName' (optional)",
        required=False
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            wc = int(self.word_count.value)
        except ValueError:
            await interaction.followup.send("Invalid word count.", ephemeral=True)
            return
        rec = self.recipient.value.strip() if self.recipient.value else None
        await launch_writing_game_interactive(interaction, wc, rec)


class OtherWritingModal(discord.ui.Modal, title="Other Writing Submission"):
    word_count = discord.ui.TextInput(label="Word Count", placeholder="Enter total word count", required=True)
    recipient = discord.ui.TextInput(
        label="Recipient",
        placeholder="Enter 'T:TrainerName' or 'M:MonName'",
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            wc = int(self.word_count.value)
        except ValueError:
            await interaction.followup.send("Invalid word count.", ephemeral=True)
            return
        rec = self.recipient.value.strip()
        await launch_writing_other_interactive(interaction, wc, rec)


class WritingSubmissionTypeView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Game Writing", style=discord.ButtonStyle.primary, custom_id="writing_game", row=0)
    async def game_writing(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(GameWritingModal())

    @discord.ui.button(label="Other Writing", style=discord.ButtonStyle.primary, custom_id="writing_other", row=0)
    async def other_writing(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(OtherWritingModal())
