# trade_items.py

import discord
import logging
import random
from core.google_sheets import update_character_sheet_item
from core.trainer import get_trainers, get_other_trainers_from_db  # Pre-existing functions
from core.core_views import create_paginated_trainers_dropdown  # Pre-existing UI dropdown creator

# Random images and flavor texts for trade items.
TRADE_ITEMS_IMAGES = [
    "https://example.com/trade_items_img1.png",
    "https://example.com/trade_items_img2.png",
    "https://example.com/trade_items_img3.png"
]

TRADE_ITEMS_FLAVOR_TEXTS = [
    "May your trades bring fortune!",
    "A deal is a deal!",
    "Trade winds are favorable today!"
]


def parse_trade_input(input_str: str) -> dict:
    """
    Parses a comma-separated string of item:amount pairs into a dictionary.

    Example:
      "Pokeball:2, Potion:1"  -->  {"Pokeball": 2, "Potion": 1}
    """
    trades = {}
    parts = input_str.split(',')
    for part in parts:
        part = part.strip()
        if not part or ':' not in part:
            continue
        item, amt = part.split(':', 1)
        try:
            trades[item.strip()] = int(amt.strip())
        except ValueError:
            logging.error(f"Invalid amount for item '{item}' in trade input.")
    return trades


class TradeModal(discord.ui.Modal, title="Trade Items"):
    # Using concise labels (under 45 characters) for Discord’s limits.
    trainer1_receiving = discord.ui.TextInput(
        label="T1: Items to Receive",
        placeholder="e.g., Pokeball:2, Potion:1",
        required=False
    )
    trainer2_receiving = discord.ui.TextInput(
        label="T2: Items to Receive",
        placeholder="e.g., Berry:3, Elixir:1",
        required=False
    )

    def __init__(self, trainer1: dict, trainer2: dict):
        """
        :param trainer1: A dict representing Trainer 1 (who receives items from trainer2).
        :param trainer2: A dict representing Trainer 2 (who sends items to trainer1).
        """
        super().__init__()
        self.trainer1 = trainer1
        self.trainer2 = trainer2

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        # Parse the input strings into dictionaries mapping item names to amounts.
        trade_for_trainer1 = parse_trade_input(self.trainer1_receiving.value)
        trade_for_trainer2 = parse_trade_input(self.trainer2_receiving.value)
        errors = []

        # For Trainer 1: Remove items from Trainer 2's inventory and add to Trainer 1.
        for item, amount in trade_for_trainer1.items():
            logging.info(f"Trading {amount} of {item} from {self.trainer2['name']} to {self.trainer1['name']}.")
            success_remove = await update_character_sheet_item(self.trainer2['name'], item, -amount)
            success_add = await update_character_sheet_item(self.trainer1['name'], item, amount)
            if not success_remove:
                error_msg = f"Failed to remove {item} (x{amount}) from {self.trainer2['name']}."
                logging.error(error_msg)
                errors.append(error_msg)
            if not success_add:
                error_msg = f"Failed to add {item} (x{amount}) to {self.trainer1['name']}."
                logging.error(error_msg)
                errors.append(error_msg)

        # For Trainer 2: Remove items from Trainer 1's inventory and add to Trainer 2.
        for item, amount in trade_for_trainer2.items():
            logging.info(f"Trading {amount} of {item} from {self.trainer1['name']} to {self.trainer2['name']}.")
            success_remove = await update_character_sheet_item(self.trainer1['name'], item, -amount)
            success_add = await update_character_sheet_item(self.trainer2['name'], item, amount)
            if not success_remove:
                error_msg = f"Failed to remove {item} (x{amount}) from {self.trainer1['name']}."
                logging.error(error_msg)
                errors.append(error_msg)
            if not success_add:
                error_msg = f"Failed to add {item} (x{amount}) to {self.trainer2['name']}."
                logging.error(error_msg)
                errors.append(error_msg)

        # Build an embed showing the result.
        if errors:
            description = "Trade completed with errors:\n" + "\n".join(errors)
            color = discord.Color.red()
        else:
            description = "Trade completed successfully!"
            color = discord.Color.green()
        embed = discord.Embed(title="Trade Result", description=description, color=color)
        embed.set_image(url=random.choice(TRADE_ITEMS_IMAGES))
        embed.set_footer(text=random.choice(TRADE_ITEMS_FLAVOR_TEXTS))
        await interaction.followup.send(embed=embed, ephemeral=True)


# ---------------------------------------------------
# New view for selecting trainers before trading.
# ---------------------------------------------------
class TradeTrainerSelectionView(discord.ui.View):
    """
    A view that lets the player select two trainers (their own and another's)
    before initiating a trade.
    """

    def __init__(self, player_id: str):
        super().__init__(timeout=120)
        self.player_id = player_id
        self.trainer1 = None  # Player's trainer
        self.trainer2 = None  # Other trainer

        own_trainers = get_trainers(player_id)
        other_trainers = get_other_trainers_from_db(player_id)
        # Create dropdown views using the pre-existing function.
        own_dropdown_view = create_paginated_trainers_dropdown(
            own_trainers, "Select Your Trainer", self.own_trainer_callback
        )
        other_dropdown_view = create_paginated_trainers_dropdown(
            other_trainers, "Select Other Trainer", self.other_trainer_callback
        )
        # Add the Select components to this view.
        self.add_item(own_dropdown_view.children[0])
        self.add_item(other_dropdown_view.children[0])
        self.add_item(TradeConfirmButton())

    async def own_trainer_callback(self, interaction: discord.Interaction, selected_value: str):
        for trainer in get_trainers(self.player_id):
            if str(trainer["id"]) == selected_value:
                self.trainer1 = trainer
                break
        await interaction.response.send_message(f"Selected your trainer: {self.trainer1['name']}", ephemeral=True)

    async def other_trainer_callback(self, interaction: discord.Interaction, selected_value: str):
        for trainer in get_other_trainers_from_db(self.player_id):
            if str(trainer["id"]) == selected_value:
                self.trainer2 = trainer
                break
        await interaction.response.send_message(f"Selected other trainer: {self.trainer2['name']}", ephemeral=True)


class TradeConfirmButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Confirm Trade", style=discord.ButtonStyle.success)

    async def callback(self, interaction: discord.Interaction):
        view: TradeTrainerSelectionView = self.view  # type: ignore
        if view.trainer1 is None or view.trainer2 is None:
            await interaction.response.send_message("Please select both trainers before confirming.", ephemeral=True)
            return
        # Launch the trade modal with the selected trainers.
        modal = TradeModal(view.trainer1, view.trainer2)
        await interaction.response.send_modal(modal)
