import asyncio

import discord
import random

from discord.ui import View, Select, Button

from views.generic_shop import send_generic_shop_view
from core.trainer import get_trainers_from_database as get_trainers

class BakeryShopView(discord.ui.View):
    def __init__(self, user_id: str):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.image = random.choice(IMAGES)
        self.message = "Welcome to the Bakery! Here you can purchase delicious pastries to feed your mons."

    @discord.ui.button(label="Buy Pastries", style=discord.ButtonStyle.primary, custom_id="bakery_shop")
    async def shop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await send_generic_shop_view(interaction, "bakery", self.user_id, category_filter="pastries")

    @discord.ui.button(label="Bakery Activity", style=discord.ButtonStyle.secondary, custom_id="bakery_activity")
    async def activity_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        trainers = get_trainers(str(interaction.user.id))
        if not trainers:
            await interaction.response.send_message("No trainers found for your account.", ephemeral=True)
            return
        view = BakeryTrainerSelectionView(trainers)
        await interaction.response.send_message(
            "Select a trainer to begin Bakery Activity (feeding pastries):",
            view=view,
            ephemeral=True
        )

async def send_bakery_view(interaction: discord.Interaction, user_id: str):
    view = BakeryShopView(user_id)
    embed = discord.Embed(title="Bakery", description=view.message, color=discord.Color.orange())
    embed.set_image(url=view.image)
    await interaction.followup.send(embed=embed, view=view, ephemeral=True)


class BakeryTrainerSelectionView(View):
    def __init__(self, trainers: list):
        super().__init__(timeout=300)
        self.trainers = trainers
        self.selected_trainer = None
        options = [
            discord.SelectOption(label=trainer["character_name"], value=str(trainer["id"]))
            for trainer in trainers
        ] if trainers else [discord.SelectOption(label="No Trainers Found", value="none")]
        self.add_item(BakeryTrainerSelect(options))

class BakeryTrainerSelect(Select):
    def __init__(self, options: list):
        super().__init__(placeholder="Select a trainer", min_values=1, max_values=1, options=options, row=0)

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "none":
            await interaction.response.send_message("No valid trainer available.", ephemeral=True)
            return
        selected_trainer_id = int(self.values[0])
        view: BakeryTrainerSelectionView = self.view  # type: ignore
        for trainer in view.trainers:
            if trainer["id"] == selected_trainer_id:
                view.selected_trainer = trainer
                break
        await interaction.response.send_message(
            f"Trainer '{view.selected_trainer['character_name']}' selected. Preparing mon and pastry selection...",
            ephemeral=True
        )
        mons = get_mons_for_trainer(view.selected_trainer["id"])
        await send_mon_pastry_selection_view(interaction, view.selected_trainer, mons)

class MonPastrySelectionView(View):
    def __init__(self, trainer: dict, mons: list, trainer_sheet: str):
        super().__init__(timeout=300)
        self.trainer = trainer
        self.trainer_sheet = trainer_sheet
        self.mons = mons
        self.selected_mon = None
        self.selected_pastry = None

        # Use the modern mon key "name" instead of "mon_name"
        mon_options = [
            discord.SelectOption(label=mon["name"], value=mon["name"])
            for mon in mons
        ] if mons else [discord.SelectOption(label="No Mons Found", value="none")]
        self.add_item(MonDropdown(mon_options))

        pastry_options = [
            discord.SelectOption(label=pastry.title(), value=pastry)
            for pastry in sorted(PASTRY_EFFECTS.keys())
        ] if PASTRY_EFFECTS else [discord.SelectOption(label="No Pastries Found", value="none")]
        self.add_item(PastryDropdown(pastry_options))

        self.add_item(SubmitButtonBakery())
        self.add_item(CancelButtonBakery())

class MonDropdown(Select):
    def __init__(self, options: list):
        super().__init__(placeholder="Select a mon", min_values=1, max_values=1, options=options, row=0)

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "none":
            await interaction.response.send_message("No valid mon available.", ephemeral=True)
        else:
            self.view.selected_mon = self.values[0]
            await interaction.response.send_message(f"Selected mon: {self.values[0]}", ephemeral=True)

class PastryDropdown(Select):
    def __init__(self, options: list):
        super().__init__(placeholder="Select a pastry", min_values=1, max_values=1, options=options, row=1)

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "none":
            await interaction.response.send_message("No valid pastry available.", ephemeral=True)
        else:
            self.view.selected_pastry = self.values[0]
            await interaction.response.send_message(f"Selected pastry: {self.values[0].title()}", ephemeral=True)

class SubmitButtonBakery(Button):
    def __init__(self):
        super().__init__(label="Submit", style=discord.ButtonStyle.success, custom_id="submit_pastry", row=2)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        view: MonPastrySelectionView = self.view  # type: ignore
        if not view.selected_mon or not view.selected_pastry:
            await interaction.followup.send("Please select both a mon and a pastry.", ephemeral=True)
            return
        await interaction.followup.send(
            "Please enter the predetermined value for the selected pastry (e.g., type, attribute, or species):",
            ephemeral=True
        )
        def check(m):
            return m.author.id == interaction.user.id and m.channel == interaction.channel
        try:
            msg = await interaction.client.wait_for("message", check=check, timeout=60)
            user_input = msg.content.strip()
        except asyncio.TimeoutError:
            await interaction.followup.send("Timed out waiting for input.", ephemeral=True)
            return
        result = apply_pastry_effect(
            str(interaction.user.id), view.trainer_sheet, view.selected_mon, view.selected_pastry, user_input
        )
        await interaction.followup.send(result, ephemeral=True)

class CancelButtonBakery(Button):
    def __init__(self):
        super().__init__(label="Cancel", style=discord.ButtonStyle.danger, custom_id="cancel_pastry", row=2)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message("Bakery activity cancelled.", ephemeral=True)

async def send_mon_pastry_selection_view(interaction: discord.Interaction, trainer: dict, mons: list):
    trainer_sheet = trainer["character_name"]
    view = MonPastrySelectionView(trainer, mons, trainer_sheet)
    embed = discord.Embed(
        title="Bakery Activity",
        description="Select a mon and a pastry to feed. You will then be prompted for additional input.",
        color=discord.Color.gold()
    )
    await interaction.followup.send(embed=embed, view=view, ephemeral=True)

IMAGES = [
    "https://example.com/bakery1.png",
    "https://example.com/bakery2.png",
]
MESSAGES = [
    "Welcome to the Bakery! Enjoy the aroma of freshly baked delights.",
    "Step inside the Bakery for warm treats and sweet surprises."
]

from core.database import update_character_sheet_item, get_mons_for_trainer
from core.mon import get_mon

def apply_pastry_effect(user_id: str, trainer_sheet: str, mon_name: str, pastry: str, user_input: str) -> str:
    """
    Applies a pastry effect to a mon.
    Uses the PASTRY_EFFECTS mapping (defined in this module) to modify the mon.
    """
    pastry_lower = pastry.lower().strip()
    if pastry_lower not in PASTRY_EFFECTS:
        return f"Pastry '{pastry}' is not recognized."
    mon = get_mon(user_id, mon_name)
    if not mon:
        return f"Mon '{mon_name}' not found."
    effect_func = PASTRY_EFFECTS[pastry_lower]
    result = effect_func(mon, user_input)
    # Update the inventory using the modern helper with category "Pastries"
    removed = update_character_sheet_item(trainer_sheet, pastry_lower, -1, category="Pastries")
    if not removed:
        result += " (Pastry was not found in inventory.)"
    # (Optionally update the mon in the database/Google Sheet.)
    return result

def effect_miraca_pastry(mon: dict, value: str) -> str:
    types = mon.get("types", [])
    if types:
        old = types[0]
        types[0] = value
    else:
        old = "None"
        types = [value]
    mon["types"] = types
    return f"Type 1 changed from '{old}' to '{value}'."

def effect_cocon_pastry(mon: dict, value: str) -> str:
    types = mon.get("types", [])
    if len(types) >= 2:
        old = types[1]
        types[1] = value
        mon["types"] = types
        return f"Type 2 changed from '{old}' to '{value}'."
    return "Mon does not have a Type 2 slot."

def effect_durian_pastry(mon: dict, value: str) -> str:
    types = mon.get("types", [])
    if len(types) >= 3:
        old = types[2]
        types[2] = value
        mon["types"] = types
        return f"Type 3 changed from '{old}' to '{value}'."
    return "Mon does not have a Type 3 slot."

def effect_monel_pastry(mon: dict, value: str) -> str:
    types = mon.get("types", [])
    if len(types) >= 4:
        old = types[3]
        types[3] = value
        mon["types"] = types
        return f"Type 4 changed from '{old}' to '{value}'."
    return "Mon does not have a Type 4 slot."

def effect_perep_pastry(mon: dict, value: str) -> str:
    types = mon.get("types", [])
    if len(types) >= 5:
        old = types[4]
        types[4] = value
        mon["types"] = types
        return f"Type 5 changed from '{old}' to '{value}'."
    return "Mon does not have a Type 5 slot."

def effect_addish_pastry(mon: dict, value: str) -> str:
    types = mon.get("types", [])
    if len(types) < 2 or (len(types) >= 2 and not types[1]):
        if len(types) < 2:
            types.append(value)
        else:
            types[1] = value
        mon["types"] = types
        return f"Type 2 set to '{value}'."
    return "Mon already has a Type 2."

def effect_sky_carrot_pastry(mon: dict, value: str) -> str:
    types = mon.get("types", [])
    if len(types) < 3 or (len(types) >= 3 and not types[2]):
        if len(types) < 3:
            while len(types) < 2:
                types.append("")
            types.append(value)
        else:
            types[2] = value
        mon["types"] = types
        return f"Type 3 set to '{value}'."
    return "Mon already has a Type 3."

def effect_kembre_pastry(mon: dict, value: str) -> str:
    types = mon.get("types", [])
    if len(types) < 4 or (len(types) >= 4 and not types[3]):
        if len(types) < 4:
            while len(types) < 3:
                types.append("")
            types.append(value)
        else:
            types[3] = value
        mon["types"] = types
        return f"Type 4 set to '{value}'."
    return "Mon already has a Type 4."

def effect_espara_pastry(mon: dict, value: str) -> str:
    types = mon.get("types", [])
    if len(types) < 5 or (len(types) >= 5 and not types[4]):
        if len(types) < 5:
            while len(types) < 4:
                types.append("")
            types.append(value)
        else:
            types[4] = value
        mon["types"] = types
        return f"Type 5 set to '{value}'."
    return "Mon already has a Type 5."

def effect_patama_pastry(mon: dict, value: str) -> str:
    old = mon.get("species1", "")
    mon["species1"] = value
    return f"Species 1 changed from '{old}' to '{value}'."

def effect_bluk_pastry(mon: dict, value: str) -> str:
    if mon.get("species2"):
        old = mon["species2"]
        mon["species2"] = value
        return f"Species 2 changed from '{old}' to '{value}'."
    return "Mon does not have a Species 2 slot."

def effect_nuevo_pastry(mon: dict, value: str) -> str:
    if mon.get("species3"):
        old = mon["species3"]
        mon["species3"] = value
        return f"Species 3 changed from '{old}' to '{value}'."
    return "Mon does not have a Species 3 slot."

def effect_azzuk_pastry(mon: dict, value: str) -> str:
    if not mon.get("species2"):
        mon["species2"] = value
        return f"Species 2 set to '{value}'."
    return "Species 2 already present; no addition."

def effect_mangus_pastry(mon: dict, value: str) -> str:
    if not mon.get("species2"):
        mon["species2"] = value
        return f"Species 2 set to '{value}'."
    return "Species 2 already present; no addition."

def effect_datei_pastry(mon: dict, value: str) -> str:
    old = mon.get("attribute", "Free")
    mon["attribute"] = value
    return f"Attribute changed from '{old}' to '{value}'."

PASTRY_EFFECTS = {
    "miraca pastry": effect_miraca_pastry,
    "cocon pastry": effect_cocon_pastry,
    "durian pastry": effect_durian_pastry,
    "monel pastry": effect_monel_pastry,
    "perep pastry": effect_perep_pastry,
    "addish pastry": effect_addish_pastry,
    "sky carrot pastry": effect_sky_carrot_pastry,
    "kembre pastry": effect_kembre_pastry,
    "espara pastry": effect_espara_pastry,
    "patama pastry": effect_patama_pastry,
    "bluk pastry": effect_bluk_pastry,
    "nuevo pastry": effect_nuevo_pastry,
    "azzuk pastry": effect_azzuk_pastry,
    "mangus pastry": effect_mangus_pastry,
    "datei pastry": effect_datei_pastry,
}
