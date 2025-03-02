import asyncio
import discord
from discord.ui import View, Select, Button
from logic.market.bakery import apply_pastry_effect, PASTRY_EFFECTS
from core.mon import get_mons_for_trainer

class BakeryTrainerSelectionView(View):
    def __init__(self, trainers: list):
        super().__init__(timeout=300)
        self.trainers = trainers
        self.selected_trainer = None
        options = [discord.SelectOption(label=trainer["name"], value=str(trainer["id"])) for trainer in trainers] \
                  if trainers else [discord.SelectOption(label="No Trainers Found", value="none")]
        self.add_item(BakeryTrainerSelect(options))

class BakeryTrainerSelect(Select):
    def __init__(self, options: list):
        super().__init__(placeholder="Select a trainer", min_values=1, max_values=1, options=options, row=0)

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "none":
            await interaction.response.send_message("No valid trainer available.", ephemeral=True)
            return
        selected_trainer_id = int(self.values[0])
        view: BakeryTrainerSelectionView = self.view
        for trainer in view.trainers:
            if trainer["id"] == selected_trainer_id:
                view.selected_trainer = trainer
                break
        await interaction.response.send_message(
            f"Trainer '{view.selected_trainer['name']}' selected. Preparing mon and pastry selection...",
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

        mon_options = [discord.SelectOption(label=mon["mon_name"], value=mon["mon_name"]) for mon in mons] \
                      if mons else [discord.SelectOption(label="No Mons Found", value="none")]
        self.add_item(MonDropdown(mon_options))

        pastry_options = [discord.SelectOption(label=pastry.title(), value=pastry) for pastry in sorted(PASTRY_EFFECTS.keys())] \
                         if PASTRY_EFFECTS else [discord.SelectOption(label="No Pastries Found", value="none")]
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
        view: MonPastrySelectionView = self.view
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
        result = apply_pastry_effect(str(interaction.user.id), view.trainer_sheet, view.selected_mon, view.selected_pastry, user_input)
        await interaction.followup.send(result, ephemeral=True)

class CancelButtonBakery(Button):
    def __init__(self):
        super().__init__(label="Cancel", style=discord.ButtonStyle.danger, custom_id="cancel_pastry", row=2)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message("Bakery activity cancelled.", ephemeral=True)

async def send_mon_pastry_selection_view(interaction: discord.Interaction, trainer: dict, mons: list):
    trainer_sheet = trainer["name"]
    view = MonPastrySelectionView(trainer, mons, trainer_sheet)
    embed = discord.Embed(
        title="Bakery Activity",
        description="Select a mon and a pastry to feed. You will then be prompted for additional input.",
        color=discord.Color.gold()
    )
    await interaction.followup.send(embed=embed, view=view, ephemeral=True)
