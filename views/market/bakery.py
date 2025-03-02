import discord
import random
from logic.market import bakery
from views.market.generic_shop import send_generic_shop_view

class BakeryShopView(discord.ui.View):
    def __init__(self, user_id: str):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.image = random.choice(bakery.IMAGES)
        self.message = "Welcome to the Bakery! Here you can purchase delicious pastries to feed your mons."

    @discord.ui.button(label="Buy Pastries", style=discord.ButtonStyle.primary, custom_id="bakery_shop")
    async def shop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await send_generic_shop_view(interaction, "bakery", self.user_id, category_filter="pastry")

    @discord.ui.button(label="Bakery Activity", style=discord.ButtonStyle.secondary, custom_id="bakery_activity")
    async def activity_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        from views.market.bakery_pastries import BakeryTrainerSelectionView
        from core.trainer import get_trainers
        trainers = get_trainers(str(interaction.user.id))
        if not trainers:
            await interaction.response.send_message("No trainers found for your account.", ephemeral=True)
            return
        view = BakeryTrainerSelectionView(trainers)
        await interaction.response.send_message("Select a trainer to begin Bakery Activity (feeding pastries):", view=view, ephemeral=True)

async def send_bakery_view(interaction: discord.Interaction, user_id: str):
    view = BakeryShopView(user_id)
    embed = discord.Embed(title="Bakery", description=view.message, color=discord.Color.orange())
    embed.set_image(url=view.image)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
