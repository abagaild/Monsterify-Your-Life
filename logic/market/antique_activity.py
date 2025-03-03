import json
import random
import discord
from discord.ui import View, Select
from core.mon import register_mon
from core.rollmons import roll_single_mon, get_default_pool, build_mon_embed, RollMonsView
from core.trainer import get_temporary_inventory_columns

# Load antique definitions from a JSON file.
with open("data/antiques.JSON", "r") as f:
    antique_list = json.load(f)

ANTIQUES = {item["name"]: item for item in antique_list}


def antique_appraise_item(antique_item: dict) -> list:
    """
    Rolls a list of mons based on an antique item's appraisal properties.

    Expected antique_item keys:
      - roll_count: number of mons to roll.
      - override_parameters: may include:
            "species_all": list to override every species slot,
            "species1", "species2", "species3": overrides for individual species slots,
            "type": list for overriding mon types,
            "attribute": list for overriding attributes.
      - force_fusion (bool): Force a fusion roll.
      - allow_fusion (bool): Allow fusion rolls (if False, force a non-fusion roll).
      - pool_variant (optional): Specify a different pool.
    """
    roll_count = antique_item.get("roll_count", 1)
    overrides = antique_item.get("override_parameters", {})
    force_fusion = antique_item.get("force_fusion", False)
    allow_fusion = antique_item.get("allow_fusion", True)
    pool_variant = antique_item.get("pool_variant")

    pool = get_default_pool()
    rolled_mons = []

    for _ in range(roll_count):
        if not allow_fusion:
            mon = roll_single_mon(pool, force_fusion=False)
        else:
            mon = roll_single_mon(pool, force_fusion=force_fusion)

        # --- Species Overrides ---
        original_name = mon.get("name", "Unknown")
        if "species_all" in overrides and overrides["species_all"]:
            if " / " in original_name:
                parts = original_name.split(" / ")
                new_parts = [random.choice(overrides["species_all"]) for _ in parts]
                mon["name"] = " / ".join(new_parts)
            else:
                mon["name"] = random.choice(overrides["species_all"])
        else:
            if " / " in original_name:
                parts = original_name.split(" / ")
                if "species1" in overrides and overrides["species1"]:
                    parts[0] = random.choice(overrides["species1"])
                if len(parts) > 1 and "species2" in overrides and overrides["species2"]:
                    parts[1] = random.choice(overrides["species2"])
                if len(parts) > 2 and "species3" in overrides and overrides["species3"]:
                    parts[2] = random.choice(overrides["species3"])
                mon["name"] = " / ".join(parts)
            else:
                if "species1" in overrides and overrides["species1"]:
                    mon["name"] = random.choice(overrides["species1"])
                # Else leave the original name

        # --- Update species fields based on the overridden name ---
        if " / " in mon["name"]:
            parts = [p.strip() for p in mon["name"].split(" / ")]
            mon["species1"] = parts[0]
            mon["species2"] = parts[1] if len(parts) > 1 else ""
            mon["species3"] = parts[2] if len(parts) > 2 else ""
        else:
            mon["species1"] = mon["name"]
            mon["species2"] = ""
            mon["species3"] = ""

        # --- Type and Attribute Overrides ---
        if "type" in overrides and overrides["type"]:
            mon["types"] = [random.choice(overrides["type"])]
        if "attribute" in overrides and overrides["attribute"]:
            mon["attribute"] = random.choice(overrides["attribute"])

        rolled_mons.append(mon)
    return rolled_mons


async def appraise_antique_activity(interaction: discord.Interaction, trainer: dict, antique_item: dict,
                                    claim_limit: int = 1):
    """
    Rolls mons using antique_appraise_item() and displays the results with interactive claim buttons.
    """
    rolled_mons = antique_appraise_item(antique_item)
    embed = build_mon_embed(rolled_mons)
    view = RollMonsView(rolled_mons, claim_limit=claim_limit)
    if interaction.response.is_done():
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)
    else:
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


# --- Inventory Selection Views ---

class AntiqueInventorySelect(Select):
    def __init__(self, antique_items: dict, trainer: dict):
        options = []
        for item_name, quantity in antique_items.items():
            options.append(discord.SelectOption(label=f"{item_name} ({quantity})", value=item_name))
        self.trainer = trainer
        super().__init__(placeholder="Select an antique from your inventory", min_values=1, max_values=1,
                         options=options)

    async def callback(self, interaction: discord.Interaction):
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=True)
        selected_item = self.values[0]
        # Look up the antique definition from the loaded JSON dictionary.
        antique_item = ANTIQUES.get(selected_item)
        if antique_item is None:
            await interaction.followup.send(f"No definition found for '{selected_item}'.", ephemeral=True)
            return
        await appraise_antique_activity(interaction, self.trainer, antique_item)


class AntiqueInventorySelectView(View):
    def __init__(self, antique_items: dict, trainer: dict):
        super().__init__(timeout=60)
        self.add_item(AntiqueInventorySelect(antique_items, trainer))


async def send_antique_inventory_view(interaction: discord.Interaction, trainer_name: str):
    inventory = get_temporary_inventory_columns(trainer_name)
    # Use the same key as your sheet header (e.g. "COLLECTION").
    antique_items = inventory.get("COLLECTION", {}) or {}
    if not antique_items:
        if interaction.response.is_done():
            await interaction.followup.send("You have no antique items in your inventory.", ephemeral=True)
        else:
            await interaction.response.send_message("You have no antique items in your inventory.", ephemeral=True)
        return
    trainer = {"id": trainer_name, "name": trainer_name}
    view = AntiqueInventorySelectView(antique_items, trainer)
    embed = discord.Embed(
        title="Your Antique Inventory",
        description="Select an antique item from your inventory to use for appraisal:",
        color=discord.Color.gold()
    )
    if interaction.response.is_done():
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)
    else:
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


# --- Trainer Selection Views ---

class AntiqueTrainerSelectionView(View):
    def __init__(self, trainers: list):
        super().__init__(timeout=60)
        options = []
        for trainer in trainers:
            options.append(discord.SelectOption(label=trainer["name"], value=str(trainer["id"])))
        self.trainers = {str(trainer["id"]): trainer for trainer in trainers}
        self.add_item(AntiqueTrainerSelect(options, self.trainers))


class AntiqueTrainerSelect(Select):
    def __init__(self, options, trainers: dict):
        super().__init__(placeholder="Select a trainer", min_values=1, max_values=1, options=options)
        self.trainers = trainers

    async def callback(self, interaction: discord.Interaction):
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=True)
        selected_trainer_id = self.values[0]
        trainer = self.trainers[selected_trainer_id]
        await send_antique_inventory_view(interaction, trainer["name"])