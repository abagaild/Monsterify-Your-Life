import discord
from discord.ui import View, Button
#from core.database import get_trainers_from_db, get_mons_from_db  # removed; use updated functions
from core.trainer import get_trainers
from core.mon import get_mons_for_trainer
from views.market.generic_shop import send_generic_shop_view
from views.market.apothecary_activity import TrainerSelectionView

class ApothecaryShopView(discord.ui.View):
    def __init__(self, user_id: str) -> None:
        super().__init__(timeout=None)
        self.user_id = user_id
        # Fetch trainers using updated function.
        self.trainers = get_trainers(user_id)
        # For simplicity, if trainers exist, fetch mons for the first trainer.
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
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
