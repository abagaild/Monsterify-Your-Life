from typing import List, Optional

import discord
import discord
from discord.ui import Button, View, Select
from core.trainer import get_trainers_from_database as get_trainers
from core.mon import get_mons_for_trainer
from market.apothecary_activity import BERRY_EFFECTS, apply_berry_effect
from views.generic_shop import send_generic_shop_view

# Define images and messages for the Apothecary overall view.
IMAGES = [
    "https://example.com/apothocary1.png",
    "https://example.com/apothocary2.png",
]

MESSAGES = [
    "The sweet aroma of berries greets you as you approach the Apothecary—the berries on sale today are extra ripe and inviting.",
    "'Welcome in,' says a sweet voice from behind the counter. She smiles and then leaves to continue sorting farm-fresh berries. There's really nowhere better to get berries of all sorts."
]

async def shop_action(interaction: discord.Interaction, user_id: str) -> None:
    from views.generic_shop import send_generic_shop_view
    # Call the generic shop view with "apothecary" as the shop name and filter for berries.
    await send_generic_shop_view(interaction, "apothecary", user_id, category_filter="berries")

class ApothecaryShopView(discord.ui.View):
    def __init__(self, user_id: str) -> None:
        super().__init__(timeout=None)
        self.user_id = user_id
        # Fetch trainers using the modern helper.
        self.trainers = get_trainers(user_id)
        # If trainers exist, fetch mons for the first trainer.
        if self.trainers:
            trainer_id = self.trainers[0]["id"]
            self.mons = get_mons_for_trainer(trainer_id)
        else:
            self.mons = []

    @discord.ui.button(label="Shop", style=discord.ButtonStyle.primary, custom_id="apoth_shop")
    async def shop_button(self, interaction: discord.Interaction, button: Button) -> None:
        # Call the generic shop view with "apothecary" as the shop name and filter for berries.
        await send_generic_shop_view(interaction, "apothecary", self.user_id, category_filter="berries")

    @discord.ui.button(label="Apothecary Activity", style=discord.ButtonStyle.primary)
    async def apothecary_activity(self, interaction: discord.Interaction, button: Button) -> None:
        user_id = str(interaction.user.id)
        trainers = get_trainers(user_id)
        if not trainers:
            await interaction.response.send_message("No trainers found for your account.", ephemeral=True)
            return
        # Create the Trainer Selection view (Step 1 of the apothecary process)
        trainer_view = TrainerSelectionView(trainers)
        await interaction.response.send_message(
            "Please select a trainer to begin Apothecary Activity:",
            view=trainer_view,
            ephemeral=True
        )

async def send_apothocary_overall_view(interaction: discord.Interaction, user_id: str) -> None:
    view = ApothecaryShopView(user_id)
    embed = discord.Embed(
        title="Apothecary",
        description="Welcome to the Apothecary! Choose an option below:",
        color=discord.Color.purple()
    )
    await interaction.followup.send(embed=embed, view=view, ephemeral=True)


# ============================================
# Step 1: Trainer Selection View
# ============================================

class TrainerSelectionView(View):
    def __init__(self, trainers: List[dict]) -> None:
        super().__init__(timeout=300)
        self.trainers = trainers  # Each trainer dict should include "id" and "name"/"character_name"
        self.selected_trainer = None
        options = []
        if trainers:
            for trainer in trainers:
                # Using the modern display name (character_name)
                options.append(discord.SelectOption(label=trainer["character_name"], value=str(trainer["id"])))
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
        self.trainer_sheet = trainer_sheet  # Typically the trainer's identifier used for sheet updates.
        self.mons = mons
        self.selected_mon: Optional[str] = None
        self.selected_berry: Optional[str] = None

        # Mon dropdown on row 0.
        mon_options = []
        if mons:
            for mon in mons:
                mon_options.append(discord.SelectOption(label=mon["name"], value=mon["name"]))
        else:
            mon_options.append(discord.SelectOption(label="No Mons Found", value="none"))
        self.add_item(MonSelect(mon_options))

        # Berry dropdown on row 1.
        berry_options = []
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
    trainer_sheet = trainer["character_name"]
    view = MonBerrySelectionView(trainer, mons, trainer_sheet)
    embed = discord.Embed(
        title="Mon & Berry Selection",
        description="Select a mon and a berry from the dropdowns below, then click Submit.",
        color=discord.Color.purple()
    )
    await interaction.followup.send(embed=embed, view=view, ephemeral=True)
