import logging

import discord
from discord.ui import View, Select

from core.google_sheets import gc
from data.lists import NURTURE_KITS, RANK_INSENSES, COLOR_INSENSES, ATTRIBUTE_TAGS, POFFINS, MILK_OPTIONS, \
    ICE_CREAM_OPTIONS

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def get_temp_inventory(trainer_name: str):
    """Fetch temporary inventory for a trainer from Google Sheets."""
    try:
        ss = gc.open(trainer_name)
        worksheet = ss.worksheet("Inventory")
        rows = worksheet.get_all_values()
        temp_inventory = []
        for row in rows:
            if len(row) >= 28:  # Assumes Column AA holds quantity and Column AB holds item name.
                item_name = row[27].strip()
                item_quantity = row[26].strip()
                if item_name and item_quantity.isdigit() and int(item_quantity) > 0:
                    temp_inventory.append(item_name)
        logging.debug(f"Temp inventory for {trainer_name}: {temp_inventory}")
        return temp_inventory
    except Exception as e:
        logging.error(f"Error fetching temp inventory for {trainer_name}: {e}")
        return []

class NurseryOptionsView(View):
    """A generic view for selecting nursery options from temporary inventory."""
    def __init__(self, temp_inventory: list, options: list, placeholder: str, custom_id: str, multi_select: bool = False):
        super().__init__(timeout=180)
        self.selections = {}
        select_options = [discord.SelectOption(label=item, value=item) for item in temp_inventory if item in options]
        if not select_options:
            select_options = [discord.SelectOption(label="None", value="None")]
        else:
            select_options.insert(0, discord.SelectOption(label="None", value="None"))
        select = Select(
            placeholder=placeholder,
            custom_id=custom_id,
            options=select_options,
            min_values=1 if not multi_select else 0,
            max_values=len(select_options) if multi_select else 1
        )
        select.callback = self.option_callback
        self.add_item(select)
        self.custom_id = custom_id

    async def option_callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        for child in self.children:
            if isinstance(child, Select) and child.custom_id == self.custom_id:
                self.selections[self.custom_id] = child.values if child.max_values > 1 else child.values[0]
                logging.debug(f"{self.custom_id} selection: {self.selections[self.custom_id]}")
                break
        self.stop()

async def collect_nursery_options(interaction: discord.Interaction, trainer_name: str, temp_inventory: list) -> dict:
    """Collect nursery options over multiple pages and return a dictionary of selections."""
    selections = {}
    pages = [
        (NURTURE_KITS, "Select a Nurture Kit", "nurture_kit"),
        (RANK_INSENSES, "Select a Rank Incense", "rank_incense"),
        (COLOR_INSENSES, "Select Color Incense(s)", "color_incense", True),
        (ATTRIBUTE_TAGS, "Select Attribute Tag(s)", "attribute_tags", True),
        (POFFINS, "Select Poffin(s)", "poffins", True),
        (MILK_OPTIONS, "Select a Milk", "milk"),
        (ICE_CREAM_OPTIONS, "Select an Ice Cream", "ice_cream")
    ]
    for options, placeholder, custom_id, *multi in pages:
        view = NurseryOptionsView(temp_inventory, options, placeholder, custom_id, multi_select=bool(multi))
        await interaction.followup.send(f"**{placeholder}**", view=view, ephemeral=True)
        await view.wait()
        selections.update(view.selections)
    return selections
