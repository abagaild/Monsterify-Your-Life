import random
from discord.ui import Modal, TextInput
import discord

from core.database import update_character_sheet_item, update_character_level, fetch_trainer_by_name, \
    update_trainer_level


class BaseView(discord.ui.View):
    """
    A base view that provides common utility functions.
    """
    def __init__(self, timeout: int = 300):
        super().__init__(timeout=timeout)

    async def safe_send(self, interaction: discord.Interaction, content: str, ephemeral: bool = True):
        """
        Sends a message safely using an Interaction. If the interaction hasn't been responded to yet,
        it sends the message via response; otherwise, it sends a follow-up message.
        """
        if not interaction.response.is_done():
            await interaction.response.send_message(content, ephemeral=ephemeral)
        else:
            await interaction.followup.send(content, ephemeral=ephemeral)

class PaginatedDropdownView(BaseView):
    """
    A view that displays a paginated dropdown selector for long option lists.
    The view automatically adds "Previous" and "Next" buttons if needed.
    """
    def __init__(self, options: list, placeholder: str, callback, page_size: int = 25, timeout: int = 120):
        """
        Parameters:
          options (list): A list of discord.SelectOption objects.
          placeholder (str): The placeholder text for the select.
          callback (function): A function that accepts (interaction, selected_value).
          page_size (int): Maximum options per page.
        """
        super().__init__(timeout=timeout)
        self.full_options = options
        self.page_size = page_size
        self.current_page = 0
        self.callback = callback
        self.placeholder = placeholder

        self.select = discord.ui.Select(placeholder=self.placeholder, min_values=1, max_values=1)
        self.update_select_options()
        self.select.callback = self.select_callback
        self.add_item(self.select)

        if len(self.full_options) > self.page_size:
            self.add_item(PaginatedPrevButton(self))
            self.add_item(PaginatedNextButton(self))

    def update_select_options(self):
        start = self.current_page * self.page_size
        end = start + self.page_size
        self.select.options = self.full_options[start:end]

    async def select_callback(self, interaction: discord.Interaction):
        selected_value = self.select.values[0]
        await self.callback(interaction, selected_value)

class PaginatedPrevButton(discord.ui.Button):
    """
    A button to move to the previous page of a paginated dropdown.
    """
    def __init__(self, view: PaginatedDropdownView):
        super().__init__(label="Previous", style=discord.ButtonStyle.secondary)
        self.view_ref = view

    async def callback(self, interaction: discord.Interaction):
        if self.view_ref.current_page > 0:
            self.view_ref.current_page -= 1
            self.view_ref.update_select_options()
            await interaction.response.edit_message(view=self.view_ref)
        else:
            await interaction.response.send_message("Already at the first page.", ephemeral=True)

class PaginatedNextButton(discord.ui.Button):
    """
    A button to move to the next page of a paginated dropdown.
    """
    def __init__(self, view: PaginatedDropdownView):
        super().__init__(label="Next", style=discord.ButtonStyle.secondary)
        self.view_ref = view

    async def callback(self, interaction: discord.Interaction):
        if self.view_ref.current_page < (len(self.view_ref.full_options) - 1) // self.view_ref.page_size:
            self.view_ref.current_page += 1
            self.view_ref.update_select_options()
            await interaction.response.edit_message(view=self.view_ref)
        else:
            await interaction.response.send_message("Already at the last page.", ephemeral=True)

class AwardLevelsModal(Modal, title="Award Levels"):
    """
    Modal for awarding levels to a trainer or a specific mon.
    Optionally also assigns a rolled item.
    """
    trainer_field = TextInput(label="Trainer", placeholder="Enter trainer's name", required=True)
    mon_field = TextInput(label="Mon (optional)", placeholder="Enter mon's name (if applicable)", required=False)

    def __init__(self, awarded_levels: int, rolled_item: str = None):
        super().__init__()
        self.awarded_levels = awarded_levels
        self.rolled_item = rolled_item

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        trainer_name = self.trainer_field.value.strip()
        mon_name = self.mon_field.value.strip()
        target_name = mon_name if mon_name else trainer_name

        # Update levels via database (trainer or mon depending on input)
        success = await update_character_level(trainer_name, target_name, self.awarded_levels)
        message = f"Awarded {self.awarded_levels} levels to {target_name} (via trainer {trainer_name}).\n"
        if self.rolled_item:
            # Assign rolled item to trainer's inventory
            item_success = await update_character_sheet_item(trainer_name, self.rolled_item, 1)
            message += f"Also assigned item '{self.rolled_item}'." if item_success else "Failed to assign item."
        await interaction.followup.send(message, ephemeral=True)

class AssignRolledItemsModal(Modal, title="Assign Rolled Items"):
    """
    Modal for assigning multiple rolled items to a trainer.
    """
    trainer_name = TextInput(label="Trainer Name", placeholder="Enter the exact trainer name", required=True)

    def __init__(self, rolled_items: list):
        super().__init__()
        self.rolled_items = rolled_items

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        trainer = self.trainer_name.value.strip()
        success_items = []
        for item in self.rolled_items:
            success = await update_character_sheet_item(trainer, item, 1)
            if success:
                success_items.append(item)
        if success_items:
            await interaction.followup.send(
                f"Successfully assigned items: {', '.join(success_items)} to trainer '{trainer}'.",
                ephemeral=True
            )
        else:
            await interaction.followup.send("Failed to assign rolled items.", ephemeral=True)

def create_paginated_trainers_dropdown(trainers: list, placeholder: str, callback, page_size: int = 25) -> PaginatedDropdownView:
    """
    Creates a paginated dropdown view for a list of trainer dictionaries.

    Each trainer dictionary is expected to have:
      - "id": a unique trainer identifier.
      - "name": the trainer's display name.

    Returns:
      PaginatedDropdownView with selectable trainer options.
    """
    options = [discord.SelectOption(label=trainer["name"], value=str(trainer["id"])) for trainer in trainers]
    return PaginatedDropdownView(options=options, placeholder=placeholder, callback=callback, page_size=page_size)

def create_paginated_mons_dropdown(mons: list, placeholder: str, callback, page_size: int = 25) -> PaginatedDropdownView:
    """
    Creates a paginated dropdown view for a list of mon dictionaries.

    Each mon dictionary is expected to have:
      - "id": a unique mon identifier.
      - "mon_name": the mon's display name.
    """
    options = [discord.SelectOption(label=mon["mon_name"], value=str(mon["id"])) for mon in mons]
    return PaginatedDropdownView(options=options, placeholder=placeholder, callback=callback, page_size=page_size)


class CompletionRewardModal(Modal, title="Completion Reward"):
    """
    A centralized modal to confirm completion rewards.

    When a task, habit, or mission is completed, this modal is shown.
    The user must type "CONFIRM" to accept the reward.

    Upon confirmation, this modal:
      - Retrieves the trainer’s record using the provided trainer name.
      - Increments the trainer's level by the awarded levels.
      - Updates the database accordingly.

    Parameters:
        subject (str): Description of the completed objective.
        awarded_levels (int): Number of levels to be awarded.
        trainer_name (str): The trainer's name whose level will be updated.
    """
    confirmation = TextInput(
        label="Type CONFIRM to accept the reward",
        placeholder="CONFIRM",
        required=True
    )

    def __init__(self, subject: str, awarded_levels: int, trainer_name: str):
        super().__init__()
        self.subject = subject
        self.awarded_levels = awarded_levels
        self.trainer_name = trainer_name

    async def on_submit(self, interaction: discord.Interaction):
        if self.confirmation.value.strip().lower() != "confirm":
            await interaction.response.send_message(
                "Reward confirmation failed. Please type 'CONFIRM' exactly to accept your reward.",
                ephemeral=True
            )
            return

        trainer = fetch_trainer_by_name(self.trainer_name)
        if trainer is None:
            await interaction.response.send_message(
                f"Trainer '{self.trainer_name}' not found. Unable to update reward.",
                ephemeral=True
            )
            return

        new_level = trainer["level"] + self.awarded_levels
        update_trainer_level(trainer["id"], new_level)
        await interaction.response.send_message(
            f"Reward processed: {self.awarded_levels} levels awarded for completing '{self.subject}'.\n"
            f"Trainer '{trainer['name']}' is now at level {new_level}.",
            ephemeral=True
        )