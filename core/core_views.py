import random
from discord.ui import Modal, TextInput
from core.google_sheets import update_character_sheet_item
import discord

from core.google_sheets import update_character_sheet_level


class BaseView(discord.ui.View):
    """
    A base views that provides common utility functions.
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
    A views that displays a paginated dropdown selector for long option lists.
    The views automatically adds "Previous" and "Next" buttons if needed.
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
        max_page = (len(self.view_ref.full_options) - 1) // self.view_ref.page_size
        if self.view_ref.current_page < max_page:
            self.view_ref.current_page += 1
            self.view_ref.update_select_options()
            await interaction.response.edit_message(view=self.view_ref)
        else:
            await interaction.response.send_message("Already at the last page.", ephemeral=True)

class GenericSelect(discord.ui.Select):
    """
    A generic select component that accepts a callback function.
    This can be used to build selection views with custom behavior.
    """
    def __init__(self, options: list, placeholder: str, callback, min_values: int = 1, max_values: int = 1, custom_id: str = None, row: int = None):
        super().__init__(placeholder=placeholder, min_values=min_values, max_values=max_values, options=options, custom_id=custom_id, row=row)
        self.select_callback = callback

    async def callback(self, interaction: discord.Interaction):
        await self.select_callback(interaction, self.values)

class SelectionView(BaseView):
    """
    A generic views that presents a single selection dropdown.
    """
    def __init__(self, options: list, placeholder: str, callback, min_values: int = 1, max_values: int = 1):
        super().__init__(timeout=120)
        self.add_item(GenericSelect(options, placeholder, callback, min_values, max_values))

class GenericButton(discord.ui.Button):
    """
    A generic button that calls a provided callback function when clicked.
    """
    def __init__(self, label: str, style: discord.ButtonStyle, callback_func, custom_id: str = None, row: int = None):
        super().__init__(label=label, style=style, custom_id=custom_id, row=row)
        self.callback_func = callback_func

    async def callback(self, interaction: discord.Interaction):
        await self.callback_func(interaction)

class GenericModal(discord.ui.Modal):
    """
    A base modal that can be extended for custom forms.
    Subclasses should override on_submit to process input.
    """
    def __init__(self, title: str):
        super().__init__(title=title)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message("Submitted!", ephemeral=True)

class ConfirmationModal(GenericModal):
    """
    A simple confirmation modal that prompts the user to type 'YES' to confirm.
    """
    def __init__(self, title: str, prompt: str):
        super().__init__(title=title)
        self.prompt = prompt
        self.response_input = TextInput(label="Type YES to confirm", placeholder="YES", required=True)
        self.add_item(self.response_input)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        if self.response_input.value.strip().upper() == "YES":
            await interaction.followup.send("Confirmed!", ephemeral=True)
        else:
            await interaction.followup.send("Action cancelled.", ephemeral=True)

class CompletionRewardModal(Modal, title="Reward Assignment"):
    def __init__(self, completed_name: str, awarded_levels: int, rolled_item: str = None):
        super().__init__()
        self.completed_name = completed_name
        self.awarded_levels = awarded_levels
        self.rolled_item = rolled_item

        self.trainer_field = TextInput(
            label="Trainer",
            placeholder="Enter trainer's name",
            required=True
        )
        self.mon_field = TextInput(
            label="Mon (optional)",
            placeholder="Enter mon's name (if applicable)",
            required=False
        )
        self.add_item(self.trainer_field)
        self.add_item(self.mon_field)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        trainer_name = self.trainer_field.value.strip()
        mon_name = self.mon_field.value.strip()
        target_name = mon_name if mon_name else trainer_name
        level_success = await update_character_sheet_level(trainer_name, target_name, self.awarded_levels)
        message = f"Awarded {self.awarded_levels} levels to {target_name} (via trainer {trainer_name}).\n"
        if self.rolled_item:
            item_success = await update_character_sheet_item(trainer_name, target_name, 1)
            message += f"Also assigned item '{self.rolled_item}'." if item_success else "Failed to assign item."
        await interaction.followup.send(message, ephemeral=True)

class AssignRolledItemsModal(Modal, title="Assign Rolled Items"):
    trainer_name = TextInput(
        label="Trainer Name",
        placeholder="Enter the exact trainer name",
        required=True
    )

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

def create_paginated_trainers_dropdown(trainers: list, placeholder: str, callback,
                                       page_size: int = 25) -> PaginatedDropdownView:
    """
    Creates a paginated dropdown views for a list of trainer dictionaries.

    Each trainer dictionary is expected to have:
      - "id": a unique trainer identifier.
      - "name": the trainer's display name.

    Parameters:
      trainers (list): List of trainer dicts.
      placeholder (str): Placeholder text for the dropdown.
      callback (function): A function that accepts (interaction, selected_value).
      page_size (int): Maximum number of options per page.

    Returns:
      PaginatedDropdownView: A views with a select that supports pagination.
    """
    options = [discord.SelectOption(label=trainer["name"], value=str(trainer["id"])) for trainer in trainers]
    view = PaginatedDropdownView(options=options, placeholder=placeholder, callback=callback, page_size=page_size)
    return view


def create_paginated_mons_dropdown(mons: list, placeholder: str, callback,
                                   page_size: int = 25) -> PaginatedDropdownView:
    """
    Creates a paginated dropdown views for a list of mon dictionaries.

    Each mon dictionary is expected to have:
      - "id": a unique mon identifier.
      - "mon_name": the display name of the mon.

    Parameters:
      mons (list): List of mon dicts.
      placeholder (str): Placeholder text for the dropdown.
      callback (function): A function that accepts (interaction, selected_value).
      page_size (int): Maximum number of options per page.

    Returns:
      PaginatedDropdownView: A views with a select that supports pagination.
    """
    options = [discord.SelectOption(label=mon["mon_name"], value=str(mon["id"])) for mon in mons]
    view = PaginatedDropdownView(options=options, placeholder=placeholder, callback=callback, page_size=page_size)
    return view


def create_generic_embed_view(title: str, messages: list, images: list, color: discord.Color = discord.Color.blurple(),
                              extra_description: str = "") -> discord.Embed:
    """
    Creates a generic embed views that randomly selects a flavor message and image from the provided lists.

    Parameters:
      title (str): The title of the embed.
      messages (list): A list of possible flavor messages (strings).
      images (list): A list of possible image URLs (strings).
      color (discord.Color): The color for the embed (default is blurple).
      extra_description (str): Optional additional description text.

    Returns:
      discord.Embed: An embed with a randomly chosen flavor message and image.
    """
    message = random.choice(messages) if messages else ""
    image = random.choice(images) if images else None
    description = message
    if extra_description:
        description += "\n\n" + extra_description
    embed = discord.Embed(title=title, description=description, color=color)
    if image:
        embed.set_image(url=image)
    return embed


class CompletionRewardModal(Modal, title="Reward Assignment"):
    def __init__(self, completed_name: str, awarded_levels: int, rolled_item: str = None):
        """
        Modal used to assign level (and optional item) rewards after a habit/task is completed.
        """
        super().__init__()
        self.completed_name = completed_name
        self.awarded_levels = awarded_levels
        self.rolled_item = rolled_item

        self.trainer_field = TextInput(
            label="Trainer",
            placeholder="Enter trainer's name",
            required=True
        )
        self.mon_field = TextInput(
            label="Mon (optional)",
            placeholder="Enter mon's name (if applicable)",
            required=False
        )
        self.add_item(self.trainer_field)
        self.add_item(self.mon_field)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        trainer_name = self.trainer_field.value.strip()
        mon_name = self.mon_field.value.strip()
        target_name = mon_name if mon_name else trainer_name
        level_success = await update_character_sheet_level(trainer_name, target_name, self.awarded_levels)
        message = f"Awarded {self.awarded_levels} levels to {target_name} (via trainer {trainer_name}).\n"
        if self.rolled_item:
            item_success = await update_character_sheet_item(trainer_name, target_name, 1)
            message += f"Also assigned item '{self.rolled_item}'." if item_success else "Failed to assign item."
        await interaction.followup.send(message, ephemeral=True)



class AssignRolledItemsModal(Modal, title="Assign Rolled Items"):
    """
    A modal that prompts the user to specify the trainer to which the rolled items will be assigned.
    Upon submission, it updates the trainer's character sheet with each rolled item.
    """
    trainer_name = TextInput(
        label="Trainer Name",
        placeholder="Enter the exact trainer name",
        required=True
    )

    def __init__(self, rolled_items: list):
        """
        :param rolled_items: A list of rolled item names.
        """
        super().__init__()
        self.rolled_items = rolled_items

    async def on_submit(self, interaction: discord.Interaction):
        trainer = self.trainer_name.value.strip()
        success_items = []
        for item in self.rolled_items:
            success = await update_character_sheet_item(trainer, item, 1)
            if success:
                success_items.append(item)
        if success_items:
            await interaction.response.send_message(
                f"Successfully assigned items: {', '.join(success_items)} to trainer '{trainer}'.",
                ephemeral=True
            )
        else:
            await interaction.response.send_message("Failed to assign rolled items.", ephemeral=True)
