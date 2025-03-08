import discord
import random
from discord.ui import View, Button, Modal, TextInput, Select
from core.trainer import get_trainers_from_database as get_trainers
from core.database import (
    update_character_sheet_item,
    fetch_trainer_by_name,
    get_inventory_quantity,
    get_trainer_inventory
)
from core.rollmons import get_pool_by_variant, roll_single_mon, register_mon
from views.generic_shop import send_generic_shop_view

import json
import data


# ------------------ Helper Function ------------------

def parse_antiques_json() -> dict:
    """
    Parses the JSON string from data.antiques into a dictionary.
    If the JSON is invalid, returns an empty dictionary.
    """
    try:
        return json.loads(data.antiques)
    except (json.JSONDecodeError, AttributeError) as e:
        print(f"Error parsing data.antiques: {e}")
        return {}


def apply_antique_overrides(rolled_mon: dict, overrides: dict) -> dict:
    """
    Applies override parameters to a rolled mon.
    If an override value is a list, a random element is chosen.
    The override keys are normalized (spaces replaced with underscores and lowercased).
    """
    for key, value in overrides.items():
        norm_key = key.replace(" ", "_").lower()  # e.g., "force fusion" -> "force_fusion"
        if isinstance(value, list):
            rolled_mon[norm_key] = random.choice(value)
        else:
            rolled_mon[norm_key] = value
    return rolled_mon

# ------------------ Utility for Inventory ------------------
def get_total_category_quantity(trainer_id: int, category: str) -> int:
    """
    Sums up the quantities of all items within the given category for the trainer.
    """
    inventory = get_trainer_inventory(trainer_id)
    return sum(inventory.get(category, {}).values())

# ================= Antique Shop Overall View ======================

class AntiqueShopView(View):
    def __init__(self, user_id: str) -> None:
        super().__init__(timeout=None)
        self.user_id = user_id
        self.trainers = get_trainers(user_id)

    @discord.ui.button(label="Shop", style=discord.ButtonStyle.primary, custom_id="antique_shop_shop")
    async def shop_button(self, interaction: discord.Interaction, button: Button) -> None:
        await send_generic_shop_view(interaction, "collection", self.user_id)

    @discord.ui.button(label="Antique Appraisal", style=discord.ButtonStyle.primary, custom_id="antique_appraisal")
    async def appraisal_button(self, interaction: discord.Interaction, button: Button) -> None:
        if not self.trainers:
            await interaction.response.send_message("No trainers found for your account.", ephemeral=True)
            return
        view = AntiqueTrainerSelectionView(self.trainers)
        embed = discord.Embed(
            title="Antique Appraisal",
            description="Select a trainer to use an antique for appraisal:",
            color=discord.Color.gold()
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

async def send_antique_overall_view(interaction: discord.Interaction, user_id: str) -> None:
    view = AntiqueShopView(user_id)
    embed = discord.Embed(
        title="Antique Shop",
        description="Welcome to the Antique Shop! Choose an option below:",
        color=discord.Color.gold()
    )
    await interaction.followup.send(embed=embed, view=view, ephemeral=True)

# ================= Trainer Selection for Antique Appraisal ======================

class AntiqueTrainerSelection(Select):
    def __init__(self, trainers: list):
        options = [
            discord.SelectOption(label=trainer["character_name"], value=str(trainer["id"]))
            for trainer in trainers
        ]
        super().__init__(placeholder="Select a trainer", min_values=1, max_values=1, options=options)
        self.trainers = trainers

    async def callback(self, interaction: discord.Interaction):
        selected_id = int(self.values[0])
        selected_trainer = next((t for t in self.trainers if t["id"] == selected_id), None)
        if not selected_trainer:
            await interaction.response.send_message("Trainer not found.", ephemeral=True)
            return
        await send_antique_appraisal_view(interaction, selected_trainer)

class AntiqueTrainerSelectionView(View):
    def __init__(self, trainers: list):
        super().__init__(timeout=60)
        self.add_item(AntiqueTrainerSelection(trainers))


ANTIQUE_EFFECTS = parse_antiques_json()


# ================= Antique Appraisal Flow ======================

async def send_antique_appraisal_view(interaction: discord.Interaction, trainer: dict):
    """
    Presents the trainer with a dropdown of antique items available in their inventory.
    """
    # Use the modern inventory system: check total antiques in the "Antiques" category.
    total_antiques = get_total_category_quantity(trainer["id"], "COLLECTION")
    if total_antiques < 1:
        await interaction.response.send_message(
            f"Trainer {trainer['character_name']} does not have any antique items in inventory.",
            ephemeral=True
        )
        return

    # Check each defined antique item in the antique effects.
    
    available_antiques = {}
    for antique_name in ANTIQUE_EFFECTS.keys():
        count = get_inventory_quantity(trainer["id"], "COLLECTION", antique_name)
        if count > 0:
            available_antiques[antique_name] = count

    if not available_antiques:
        await interaction.response.send_message(
            f"Trainer {trainer['character_name']} does not have any usable antique items.",
            ephemeral=True
        )
        return

    view = AntiqueItemSelectView(trainer, available_antiques)
    embed = discord.Embed(
        title="Antique Appraisal",
        description="Select an antique item from your inventory to use for appraisal:",
        color=discord.Color.dark_purple()
    )
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

class AntiqueItemSelect(Select):
    def __init__(self, antique_options: list):
        options = [
            discord.SelectOption(label=f"{name} (x{count})", value=name)
            for name, count in antique_options
        ]
        super().__init__(placeholder="Select an antique item", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        selected_antique = self.values[0]
        await process_antique_appraisal(interaction, self.view.trainer, selected_antique)

class AntiqueItemSelectView(View):
    def __init__(self, trainer: dict, antiques: dict):
        super().__init__(timeout=60)
        self.trainer = trainer
        antique_options = list(antiques.items())
        self.add_item(AntiqueItemSelect(antique_options))

# ================= Process Antique Appraisal ======================

async def process_antique_appraisal(interaction: discord.Interaction, trainer: dict, antique_item: str):
    """
    Processes the antique appraisal:
      - Looks up the antique effect.
      - Removes one instance of the antique from the trainer's inventory.
      - Rolls a mon based on the antique's effect and applies any override parameters.
      - Launches the standardized registration modal to register the rolled mon.
    """
    effect = ANTIQUE_EFFECTS.get(antique_item)
    if not effect:
        await interaction.response.send_message("This antique has no defined effect.", ephemeral=True)
        return

    # Remove one instance of the antique item from the trainer's "Antiques" inventory.
    success = await update_character_sheet_item(trainer["character_name"], antique_item, -1, category="COLLECTION")
    if not success:
        await interaction.response.send_message("Failed to remove the antique item from your inventory.", ephemeral=True)
        return

    roll_count = effect.get("roll_count", 1)
    force_fusion = effect.get("force_fusion", False)
    force_min_types = effect.get("force_min_types", None)

    # Get a pool based on the antique's variant.
    pool = get_pool_by_variant(effect.get("variant", "default"), unique_terms=effect.get("unique_terms"))
    if not pool:
        await interaction.response.send_message("No mons available for this antique effect.", ephemeral=True)
        return

    # Roll a mon (or roll_count mons, if needed; here we roll one).
    rolled_mon = roll_single_mon(pool, force_fusion=force_fusion, force_min_types=force_min_types)
    # Apply any override parameters.
    overrides = effect.get("override_parameters", {})
    if overrides:
        rolled_mon = apply_antique_overrides(rolled_mon, overrides)
    # Register the rolled mon.
    await register_mon(interaction, trainer["character_name"], rolled_mon, rolled_mon.get("name", "Unknown"))
    await interaction.followup.send(
        f"Antique appraisal complete! You used **{antique_item}** and registered a new mon.",
        ephemeral=True
    )
