import discord
from core.currency import add_currency
from core.database import fetch_one, execute_query
from core.database import update_character_level, update_mon_img_link
from core.database import add_item  # (alias for update_character_sheet_item)

# Bonus mapping for art submissions.
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

# ---------------- Reference Art ----------------
async def process_reference_art(interaction: discord.Interaction, mon_name: str, image_link: str) -> str:
    """
    Processes a reference art submission by:
      - Looking up the mon and its trainer,
      - Updating the mon’s image link in Google_Sheets and the database,
      - Awarding bonus levels and coins.
    """
    row = fetch_one("SELECT trainer_id, player FROM mons WHERE mon_name = ? LIMIT 1", (mon_name,))
    if not row:
        return f"Mon '{mon_name}' not found."
    trainer_id, player_id = row
    trainer_row = fetch_one("SELECT name FROM trainers WHERE id = ?", (trainer_id,))
    if not trainer_row:
        return "Trainer not found for that mon."
    trainer_name = trainer_row[0]

    img_update_error = await update_mon_img_link(trainer_name, mon_name, image_link)
    if img_update_error:
        return f"Error updating image link: {img_update_error}"

    execute_query("UPDATE mons SET img_link = ? WHERE mon_name = ? AND trainer_id = ?",
                  (image_link, mon_name, trainer_id))

    update_success = await update_character_level(trainer_name, mon_name, 6)
    if not update_success:
        return "Failed to update mon's level in the sheet."
    execute_query("UPDATE mons SET level = level + 6 WHERE mon_name = ? AND trainer_id = ?",
                  (mon_name, trainer_id))
    add_currency(player_id, 200)

    return (f"Reference art submitted successfully! {mon_name} has been updated: "
            f"+6 levels and 200 coins awarded.")

# ---------------- Game Art ----------------
async def process_game_art(interaction: discord.Interaction, character_names: list) -> str:
    """
    Processes game art submissions by separating provided names into trainers and mons,
    then launching a bonus selection view.
    """
    from core.database import fetch_one  # ensure helper is used
    trainers, mons = [], []
    for name in character_names:
        if fetch_one("SELECT id FROM trainers WHERE character_name = ?", (name,)):
            trainers.append(name)
        else:
            mons.append(name)
    participants = trainers + mons
    await launch_bonus_view(interaction, art_type="game", participants=participants)
    return "Bonus view launched. Please select your bonus options."

# ---------------- Other Art ----------------
async def process_other_art(interaction: discord.Interaction, selected_bonuses: list, recipient: str = None) -> str:
    """
    Processes other art submissions by computing bonus levels based on selected options,
    and then updating the target trainer/mon’s levels. If no recipient is provided,
    a modal is launched to prompt the user.
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
    return f"Other art submitted! {total_levels} levels awarded to {recipient} and {coins} coins granted."

class OtherArtRecipientModal(discord.ui.Modal, title="Specify Recipient for Other Art"):
    recipient_input = discord.ui.TextInput(
        label="Recipient",
        placeholder="Enter trainer (t:TrainerName) or mon (m:MonName)",
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        recipient = self.recipient_input.value.strip()
        bonus_sum = 0  # No extra bonuses if not provided
        total_levels = bonus_sum + 2
        coins = total_levels * 50
        success = await update_character_level(recipient, recipient, total_levels)
        if not success:
            await interaction.response.send_message("Failed to update recipient's sheet.", ephemeral=True)
        else:
            from core.currency import add_currency
            add_currency(str(interaction.user.id), coins)
            await interaction.response.send_message(
                f"Other art submitted! {total_levels} levels awarded to {recipient} and {coins} coins granted.",
                ephemeral=True
            )

# ---------------- Bonus View (Shared for Game/Other Art) ----------------
async def launch_bonus_view(interaction: discord.Interaction, art_type: str, participants: list = None):
    from core.database import fetch_one
    from core.database import update_character_level
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

        async def bonus_callback(self, interaction: discord.Interaction):
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
                        if fetch_one("SELECT id FROM trainers WHERE character_name = ?", (name,)):
                            resolved.append(name)
                        else:
                            row = fetch_one("SELECT trainer_id FROM mons WHERE name = ?", (name,))
                            if row:
                                trainer_id = row[0]
                                trainer_row = fetch_one("SELECT character_name FROM trainers WHERE id = ?", (trainer_id,))
                                if trainer_row:
                                    resolved.append(trainer_row[0])
                    if not resolved:
                        resolved = ["default_trainer"]
                    import math
                    per_participant = math.ceil(total_levels / len(resolved))
                    for recipient in resolved:
                        await update_character_level(recipient, recipient, per_participant)
                    msg = (f"Game art submission: Total bonus levels = {total_levels} "
                           f"(split as {per_participant} each among {len(resolved)} participants) "
                           f"and {coins} coins awarded.")
                else:
                    msg = (f"Other art submission: {total_levels} levels awarded and {coins} coins granted.")
                add_currency(str(interaction.user.id), coins)
                if not interaction.response.is_done():
                    await interaction.response.send_message(msg, ephemeral=True)
                else:
                    await interaction.followup.send(msg, ephemeral=True)
                self.stop()
            except Exception as e:
                print("Error in bonus callback:", e)
                self.stop()

    view = BonusSelectView()
    if not interaction.response.is_done():
        await interaction.response.send_message("Select bonus options:", view=view, ephemeral=True)
    else:
        await interaction.followup.send("Select bonus options:", view=view, ephemeral=True)
