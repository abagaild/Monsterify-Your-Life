import discord
from discord.ui import View, Select, Button
from typing import List, Optional, Dict, Any
from logic.market.apothecary_activity import apply_berry_effect, BERRY_EFFECTS
from core.mon import get_mons_for_trainer
from core.database import fetch_one  # use our helper for queries

# ============================================
# Step 1: Trainer Selection View
# ============================================

class TrainerSelectionView(View):
    def __init__(self, trainers: List[dict]) -> None:
        super().__init__(timeout=300)
        self.trainers = trainers  # Each trainer dict should include "id" and "name"
        self.selected_trainer = None
        options = []
        if trainers:
            for trainer in trainers:
                options.append(discord.SelectOption(label=trainer["name"], value=str(trainer["id"])))
        else:
            options.append(discord.SelectOption(label="No Trainers Found", value="none"))
        self.add_item(TrainerSelect(options))

class TrainerSelect(Select):
    def __init__(self, options: List[discord.SelectOption]) -> None:
        super().__init__(placeholder="Select a trainer", min_values=1, max_values=1, options=options, row=0)

    async def callback(self, interaction: discord.Interaction) -> None:
        if self.values[0] == "none":
            await interaction.response.send_message("No valid trainer available.", ephemeral=True)
            return
        selected_trainer_id = int(self.values[0])
        view: TrainerSelectionView = self.view  # type: ignore
        for trainer in view.trainers:
            if trainer["id"] == selected_trainer_id:
                view.selected_trainer = trainer
                break
        await interaction.response.send_message(
            f"Trainer '{view.selected_trainer['character_name']}' selected. Preparing mon and berry selection...",
            ephemeral=True
        )
        mons = get_mons_for_trainer(view.selected_trainer["id"])
        await send_mon_berry_selection_view(interaction, view.selected_trainer, mons)

# ============================================
# Step 2: Mon & Berry Selection View
# ============================================

class MonBerrySelectionView(View):
    def __init__(self, trainer: dict, mons: List[dict], trainer_sheet: str) -> None:
        super().__init__(timeout=300)
        self.trainer = trainer
        self.trainer_sheet = trainer_sheet
        self.mons = mons
        self.selected_mon: Optional[str] = None
        self.selected_berry: Optional[str] = None

        # Mon dropdown on row 0.
        mon_options: List[discord.SelectOption] = []
        if mons:
            for mon in mons:
                # Use the "name" key (not "mon_name")
                mon_options.append(discord.SelectOption(label=mon["name"], value=mon["name"]))
        else:
            mon_options.append(discord.SelectOption(label="No Mons Found", value="none"))
        self.add_item(MonSelect(mon_options))

        # Berry dropdown on row 1.
        berry_options: List[discord.SelectOption] = []
        berries = sorted(BERRY_EFFECTS.keys())
        if berries:
            for berry in berries:
                berry_options.append(discord.SelectOption(label=berry.title(), value=berry))
        else:
            berry_options.append(discord.SelectOption(label="No Berries Found", value="none"))
        self.add_item(BerrySelect(berry_options))

        # Buttons on row 2.
        self.add_item(SubmitButton())
        self.add_item(CancelButton())

class MonSelect(Select):
    def __init__(self, options: List[discord.SelectOption]) -> None:
        super().__init__(placeholder="Select a mon", min_values=1, max_values=1, options=options, row=0)

    async def callback(self, interaction: discord.Interaction) -> None:
        if self.values[0] == "none":
            await interaction.response.send_message("No valid mon available.", ephemeral=True)
        else:
            self.view.selected_mon = self.values[0]
            await interaction.response.send_message(f"Selected mon: {self.values[0]}", ephemeral=True)

class BerrySelect(Select):
    def __init__(self, options: List[discord.SelectOption]) -> None:
        super().__init__(placeholder="Select a berry", min_values=1, max_values=1, options=options, row=1)

    async def callback(self, interaction: discord.Interaction) -> None:
        if self.values[0] == "none":
            await interaction.response.send_message("No valid berry available.", ephemeral=True)
        else:
            self.view.selected_berry = self.values[0]
            await interaction.response.send_message(f"Selected berry: {self.values[0].title()}", ephemeral=True)

class SubmitButton(Button):
    def __init__(self) -> None:
        super().__init__(label="Submit", style=discord.ButtonStyle.success, custom_id="submit_berry", row=2)

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        view: MonBerrySelectionView = self.view  # type: ignore
        if not view.selected_mon or not view.selected_berry:
            await interaction.followup.send("Please select both a mon and a berry.", ephemeral=True)
            return
        user_id_str = str(interaction.user.id)
        result = await apply_berry_effect(user_id_str, view.trainer_sheet, view.selected_mon, view.selected_berry)
        await interaction.followup.send(result, ephemeral=True)

class CancelButton(Button):
    def __init__(self) -> None:
        super().__init__(label="Cancel", style=discord.ButtonStyle.danger, custom_id="cancel_apothecary", row=2)

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message("Mon and berry selection cancelled.", ephemeral=True)

async def send_mon_berry_selection_view(interaction: discord.Interaction, trainer: dict, mons: List[dict]) -> None:
    trainer_sheet = trainer["name"]
    view = MonBerrySelectionView(trainer, mons, trainer_sheet)
    embed = discord.Embed(
        title="Mon & Berry Selection",
        description="Select a mon and a berry from the dropdowns below, then click Submit.",
        color=discord.Color.purple()
    )
    await interaction.followup.send(embed=embed, view=view, ephemeral=True)

# ============================================
# Database Helper Function for Mon Retrieval
# ============================================

def get_mon(trainer_id: str, mon_name: str) -> Optional[Dict[str, Any]]:
    """
    Retrieves a mon record from the database for the given trainer and mon name.
    Uses the correct database helper function.
    """
    query = """
        SELECT mon_id, species1, species2, species3, type1, type2, type3, type4, type5, attribute, name
        FROM mons WHERE name = ? AND player_user_id = ?
    """
    row = fetch_one(query, (mon_name, trainer_id))
    if row:
        mon = {
            "id": row["mon_id"],
            "species1": row["species1"],
            "species2": row["species2"],
            "species3": row["species3"],
            "types": [row["type1"], row["type2"], row["type3"], row["type4"], row["type5"]],
            "attribute": row["attribute"],
            "name": row["name"]
        }
        mon["types"] = [t for t in mon["types"] if t]
        return mon
    return None
