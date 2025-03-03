# nursery_options.py
"""
Nursery Options Module: Builds interactive dropdown views for the different
options available to affect the egg roll. It reads the trainer's temporary
inventory from Google Sheets (the "EGGS" column) and filters allowed items by
stripping marker text from allowed option texts.
"""

import discord
import re

# Define allowed option templates with marker texts.
ALLOWED_OPTIONS = {
    "nurture_kit": "[type] Nurture Kit",
    "corruption_code": "Corruption Code",
    "repair_code": "Repair Code",
    "shiny_new_code": "Shiny New Code",
    "rank_incense": "[Rank] Rank Incense",
    "color_insense": "[Yokai Attribute] Color Insense",
    "spell_tag": "Spell Tag",
    "summoning_stone": "Summoning Stone",
    "digimeat": "DigiMeat",
    "digitofu": "DigiTofu",
    "soothe_bell": "SootheBell",
    "broken_bell": "Broken Bell",
    "poffin": "[type] Poffin",
    "tag": "[attribute] tag",
    "dna_splicer": "DNA Splicer",
    "hot_chocolate": "Hot Chocolate",
    "chocolate_milk": "Chocolate Milk",
    "strawberry_milk": "Strawberry Milk",
    "vanilla_ice_cream": "Vanilla Ice Cream",
    "strawberry_ice_cream": "Strawberry Ice Cream",
    "chocolate_ice_cream": "Chocolate Ice Cream",
    "species_override": "Species Override"
}

def normalize_option(text: str) -> str:
    """Removes any marker text enclosed in square brackets and trims the result."""
    return re.sub(r"\[.*?\]", "", text).strip().lower()

async def build_nursery_options_view(trainer_name: str, inventory: dict, user: discord.User) -> discord.ui.View:
    """
    Constructs a Discord view containing dropdowns for each allowed option type,
    based on the trainer's "EGGS" inventory. Each dropdown allows the player to
    select an item that affects the egg roll.
    """
    eggs_inventory = inventory.get("EGGS", {})
    view = discord.ui.View(timeout=180)
    view.selections = {}  # Store player's selections here

    # Create a dropdown for each allowed option if matching items are found.
    for key, allowed_text in ALLOWED_OPTIONS.items():
        normalized_allowed = normalize_option(allowed_text)
        matching_items = []
        for item_name, qty in eggs_inventory.items():
            if qty < 1:
                continue
            normalized_item = normalize_option(item_name)
            if normalized_item == normalized_allowed:
                # Include the item with quantity in the label.
                matching_items.append(discord.SelectOption(label=f"{item_name} ({qty})", value=item_name))
        if matching_items:
            select = discord.ui.Select(
                placeholder=f"Select {allowed_text}",
                min_values=0,
                max_values=1,
                options=matching_items,
                custom_id=key
            )
            async def select_callback(interaction: discord.Interaction, select=select):
                selected_value = select.values[0] if select.values else None
                view.selections[select.custom_id] = selected_value
                await interaction.response.defer()
            select.callback = select_callback
            view.add_item(select)

    # Add a submit button to finalize the selections.
    class SubmitButton(discord.ui.Button):
        def __init__(self):
            super().__init__(label="Submit Options", style=discord.ButtonStyle.success)
        async def callback(self, interaction: discord.Interaction):
            await interaction.response.send_message("Options submitted. Rolling eggs...", ephemeral=True)
            # Call the nursery roll module to process the selections and roll eggs.
            import nursery_roll
            await nursery_roll.run_nursery_roll(interaction, view.selections, trainer_name)
    view.add_item(SubmitButton())
    return view
