import discord
from discord.ui import Modal, TextInput, View, Button
import math
import asyncio

from core.database import (
    addsub_trainer_currency as add_currency,
    fetch_one,
    execute_query,
    update_character_level,
    update_mon_img_link,
    update_character_sheet_item as update_trainer_items,
    fetch_trainer_by_name,
    fetch_mon_by_name,
    update_mon_level
)

# --------------------- BONUS VALUES ------------------------
BONUS_VALUES = {
    "Prop": 1,
    "Simple Background": 2,
    "Complex Background": 5,
    "Not Elliot": 2,
    "Tomfoolery": 8,
    "Simple Animation": 8,
    "Sketch": -2,
    "Inking": 2,
    "Second Character": 3,
    "Third Character": 3,
    "Multi Character": 10
}


# --------------------- LOGIC FUNCTIONS ------------------------

async def process_reference_art(interaction: discord.Interaction, mon_name: str, image_link: str,
                                recipient: str = None) -> str:
    """
    Processes a reference art submission:
      - If a recipient is provided (starting with T: or M:), update that record.
      - Otherwise, look up the mon’s default trainer.
      - Updates the mon’s image link and awards +6 levels and 200 coins.
    """
    if recipient:
        if recipient.lower().startswith("t:"):
            trainer_name_input = recipient[2:].strip()
            success = await update_character_level(trainer_name_input, trainer_name_input, 6)
            if success:
                add_currency(str(interaction.user.id), 200)
                return (f"Reference art submitted successfully! {trainer_name_input} has been rewarded with "
                        f"+6 levels and 200 coins.")
            else:
                return "Failed to update the specified trainer's sheet."
        elif recipient.lower().startswith("m:"):
            mon_name_input = recipient[2:].strip()
            row = fetch_one("SELECT trainer_id FROM mons WHERE name = ? COLLATE NOCASE", (mon_name_input,))
            if row:
                trainer_id = row["trainer_id"]
                trainer_row = fetch_one("SELECT character_name FROM trainers WHERE id = ?", (trainer_id,))
                if trainer_row:
                    trainer_name = trainer_row["character_name"]
                    success = await update_character_level(trainer_name, mon_name_input, 6)
                    if success:
                        add_currency(str(interaction.user.id), 200)
                        return (f"Reference art submitted successfully! {mon_name_input} has been rewarded with "
                                f"+6 levels and 200 coins.")
                    else:
                        return "Failed to update the specified mon's sheet."
            return f"Could not find a mon named '{mon_name_input}'."

    # Default behavior: look up the mon by its name.
    row = fetch_one("SELECT trainer_id, player_user_id FROM mons WHERE name = ? COLLATE NOCASE LIMIT 1", (mon_name,))
    if not row:
        return f"Mon '{mon_name}' not found."
    trainer_id = row["trainer_id"]
    trainer_row = fetch_one("SELECT character_name FROM trainers WHERE id = ?", (trainer_id,))
    if not trainer_row:
        return "Trainer not found for that mon."
    trainer_name = trainer_row["character_name"]

    # Update mon image link and level.
    img_update_error = await update_mon_img_link(trainer_name, mon_name, image_link)
    if img_update_error:
        return f"Error updating image link: {img_update_error}"
    execute_query("UPDATE mons SET img_link = ? WHERE name = ? AND trainer_id = ?", (image_link, mon_name, trainer_id))

    success = await update_character_level(trainer_name, mon_name, 6)
    if not success:
        return "Failed to update mon's level in the sheet."
    execute_query("UPDATE mons SET level = level + 6 WHERE name = ? AND trainer_id = ?", (mon_name, trainer_id))
    add_currency(trainer_id, 200)

    return (f"Reference art submitted successfully! {mon_name} has been updated: +6 levels and 200 coins awarded.")


async def process_game_art(interaction: discord.Interaction, character_names: list) -> str:
    """
    Processes game art submissions by categorizing provided names into trainers and mons,
    then launching the bonus selection view.
    """
    trainers, mons = [], []
    for name in character_names:
        if fetch_one("SELECT id FROM trainers WHERE character_name = ? COLLATE NOCASE", (name,)):
            trainers.append(name)
        else:
            mons.append(name)
    participants = trainers + mons
    await launch_bonus_view(interaction, art_type="game", participants=participants)
    return "Bonus view launched. Please select your bonus options."


async def process_other_art(interaction: discord.Interaction, selected_bonuses: list, recipient: str = None) -> str:
    """
    Processes other art submissions by computing bonus levels based on selected options,
    then updating the target trainer/mon’s levels.
    If no recipient is provided, a modal is launched to prompt the user.
    """
    if not recipient:
        modal = OtherArtRecipientModal()
        await interaction.response.send_modal(modal)
        return "Please specify the recipient in the modal."

    bonus_sum = sum(BONUS_VALUES.get(bonus, 0) for bonus in selected_bonuses)
    total_levels = bonus_sum + 2
    coins = total_levels * 50

    success = await update_character_level(recipient, recipient, total_levels)
    if not success:
        return "Failed to update the recipient's sheet with the new levels."
    add_currency(str(interaction.user.id), coins)
    return (f"Other art submitted! {total_levels} levels awarded to {recipient} and {coins} coins granted.")


async def launch_bonus_view(interaction: discord.Interaction, art_type: str, participants: list = None):
    """
    Launches a bonus selection view for art submissions.
    """

    class BonusSelectView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=60)
            options = []
            for bonus, value in BONUS_VALUES.items():
                options.append(discord.SelectOption(label=bonus, description=f"+{value} levels", value=bonus))
            options.append(discord.SelectOption(label="No Bonus", description="Proceed with no bonus", value="none"))
            self.select = discord.ui.Select(
                placeholder="Select bonus options",
                min_values=0,
                max_values=3,
                options=options,
                custom_id="bonus_select"
            )
            self.select.callback = self.bonus_callback
            self.add_item(self.select)

        async def bonus_callback(self, bonus_interaction: discord.Interaction):
            try:
                selected = self.select.values
                if "none" in selected and len(selected) > 1:
                    selected.remove("none")
                bonus_sum = sum(BONUS_VALUES.get(b, 0) for b in selected if b != "none")
                total_levels = bonus_sum + 2
                coins = total_levels * 50

                if art_type == "game" and participants:
                    resolved = []
                    for name in participants:
                        if fetch_one("SELECT id FROM trainers WHERE character_name = ? COLLATE NOCASE", (name,)):
                            resolved.append(name)
                        else:
                            row = fetch_one("SELECT trainer_id FROM mons WHERE name = ? COLLATE NOCASE", (name,))
                            if row:
                                trainer_id = row["trainer_id"]
                                trainer_row = fetch_one("SELECT character_name FROM trainers WHERE id = ?",
                                                        (trainer_id,))
                                if trainer_row:
                                    resolved.append(trainer_row["character_name"])
                    if not resolved:
                        resolved = ["default_trainer"]
                    per_participant = math.ceil(total_levels / len(resolved))
                    for recipient in resolved:
                        await update_character_level(recipient, recipient, per_participant)
                    msg = (f"Game art submission: Total bonus levels = {total_levels} "
                           f"(split as {per_participant} each among {len(resolved)} participants) "
                           f"and {coins} coins awarded.")
                else:
                    msg = (f"Other art submission: {total_levels} levels awarded and {coins} coins granted.")
                add_currency(str(interaction.user.id), coins)
                if not bonus_interaction.response.is_done():
                    await bonus_interaction.response.send_message(msg, ephemeral=True)
                else:
                    await bonus_interaction.followup.send(msg, ephemeral=True)
                self.stop()
            except Exception as e:
                print("Error in bonus callback:", e)
                self.stop()

    view = BonusSelectView()
    if not interaction.response.is_done():
        await interaction.response.send_message("Select bonus options:", view=view, ephemeral=True)
    else:
        await interaction.followup.send("Select bonus options:", view=view, ephemeral=True)


# --------------------- VIEW CLASSES ------------------------

class ReferenceArtModal(discord.ui.Modal, title="Reference Art Submission"):
    mon_name = discord.ui.TextInput(label="Mon Name", placeholder="Enter the mon's name", required=True)
    image_link = discord.ui.TextInput(label="Image URL", placeholder="Enter the image link", required=True)
    recipient = discord.ui.TextInput(
        label="Recipient (Optional)",
        placeholder="Enter 'T:TrainerName' or 'M:MonName' (optional)",
        required=False
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        result = await process_reference_art(
            interaction,
            self.mon_name.value,
            self.image_link.value,
            self.recipient.value.strip() if self.recipient.value else None
        )
        await interaction.followup.send(result, ephemeral=True)


class GameArtModal(discord.ui.Modal, title="Game Art Submission"):
    num_characters = discord.ui.TextInput(label="Number of Characters", placeholder="Enter a number", required=True)
    character_names = discord.ui.TextInput(label="Character Names", placeholder="Enter names separated by commas",
                                           required=True)

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


class OtherArtRecipientModal(discord.ui.Modal, title="Specify Recipient for Other Art"):
    recipient_input = discord.ui.TextInput(
        label="Recipient",
        placeholder="Enter trainer (T:TrainerName) or mon (M:MonName)",
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        recipient = self.recipient_input.value.strip()
        bonus_sum = 0  # No extra bonuses if not provided.
        total_levels = bonus_sum + 2
        coins = total_levels * 50
        success = await update_character_level(recipient, recipient, total_levels)
        if not success:
            await interaction.followup.send("Failed to update recipient's sheet.", ephemeral=True)
        else:
            add_currency(str(interaction.user.id), coins)
            await interaction.followup.send(
                f"Other art submitted! {total_levels} levels awarded to {recipient} and {coins} coins granted.",
                ephemeral=True
            )


class ArtSubmissionTypeView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Reference Art", style=discord.ButtonStyle.success, custom_id="art_ref", row=0)
    async def reference_art(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ReferenceArtModal())

    @discord.ui.button(label="Game Art", style=discord.ButtonStyle.primary, custom_id="art_game", row=0)
    async def game_art(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(GameArtModal())

    @discord.ui.button(label="Other Art", style=discord.ButtonStyle.secondary, custom_id="art_other", row=0)
    async def other_art(self, interaction: discord.Interaction, button: discord.ui.Button):
        await launch_bonus_view(interaction, art_type="other")
