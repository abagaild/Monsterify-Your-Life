import discord
import logging
import random
from core.database import update_character_sheet_item
from core.trainer import get_trainers, get_other_trainers_from_db
from core.core_views import create_paginated_trainers_dropdown

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
        super().__init__()
        self.trainer1 = trainer1
        self.trainer2 = trainer2

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        trade_for_trainer1 = parse_trade_input(self.trainer1_receiving.value)
        trade_for_trainer2 = parse_trade_input(self.trainer2_receiving.value)
        errors = []
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
