import discord
from discord.ui import View, Button
from core.database import get_trainers_from_db
from core.trainer import get_trainers
from views.market.generic_shop import send_generic_shop_view
from logic.market.antique_activity import AntiqueTrainerSelectionView

class AntiqueShopView(View):
    def __init__(self, user_id: str) -> None:
        super().__init__(timeout=None)
        self.user_id = user_id
        # Fetch trainers for this user.
        self.trainers = get_trainers_from_db(user_id)

    @discord.ui.button(label="Shop", style=discord.ButtonStyle.primary, custom_id="antique_shop")
    async def shop_button(self, interaction: discord.Interaction, button: Button) -> None:
        # Open the generic shop view with "antique" as the shop name.
        await send_generic_shop_view(interaction, "collection", self.user_id)

    @discord.ui.button(label="Antique Appraisal", style=discord.ButtonStyle.primary)
    async def antique_activity(self, interaction: discord.Interaction, button: Button) -> None:
        user_id = str(interaction.user.id)
        trainers = get_trainers(user_id)
        if not trainers:
            await interaction.response.send_message("No trainers found for your account.", ephemeral=True)
            return
        # Create the Trainer Selection view for Antique Appraisal Activity.
        trainer_view = AntiqueTrainerSelectionView(trainers)
        await interaction.response.send_message(
            "Please select a trainer to use an antique from your inventory:",
            view=trainer_view,
            ephemeral=True
        )

async def send_antique_overall_view(interaction: discord.Interaction, user_id: str) -> None:
    view = AntiqueShopView(user_id)
    embed = discord.Embed(
        title="Antique Shop",
        description="Welcome to the Antique Shop! Choose an option below:",
        color=discord.Color.gold()
    )
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
