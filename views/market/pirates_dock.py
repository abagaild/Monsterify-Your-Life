import discord
import random
import logic.market.pirates_dock as logic
from views.market.generic_shop import send_generic_shop_view

class PiratesDockShopView(discord.ui.View):
    def __init__(self, user_id: str):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.image = random.choice(logic.IMAGES)
        self.message = "Welcome to Pirate's Dock! Shop here for random items at a massive markup. (No activity available.)"

    @discord.ui.button(label="Shop", style=discord.ButtonStyle.primary, custom_id="pirates_dock_shop")
    async def shop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await send_generic_shop_view(interaction, "pirate", self.user_id)

    @discord.ui.button(label="Activity", style=discord.ButtonStyle.secondary, custom_id="pirates_dock_activity")
    async def activity_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # For Pirate's Dock, no activity is implemented.
        await interaction.response.send_message("Pirate's Dock does not have an activity.", ephemeral=True)

async def send_pirates_dock_view(interaction: discord.Interaction, user_id: str):
    view = PiratesDockShopView(user_id)
    embed = discord.Embed(title="Pirate's Dock", description=view.message, color=discord.Color.gold())
    embed.set_image(url=view.image)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
