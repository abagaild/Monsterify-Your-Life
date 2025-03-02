import discord
import random



from logic.market.nursery import run_nursery_activity
from views.market.generic_shop import send_generic_shop_view


class NurseryShopView(discord.ui.View):
    """
    Nursery UI that offers two choices:
      - Shop: to roll eggs (using the generic shop view)
      - Activity: to run the nursery activity (nurturing mons)
    """
    def __init__(self, user_id: str):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.image = random.choice([
            "https://example.com/nursery1.png",
            "https://example.com/nursery2.png",
            "https://example.com/nursery3.png"
        ])
        self.message = random.choice([
            "Welcome to the Nursery!",
            "Your eggs are about to hatch!",
            "Step into the Nursery to nurture your new companions."
        ])

    @discord.ui.button(label="Shop (Eggs)", style=discord.ButtonStyle.primary, custom_id="nursery_shop")
    async def shop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Use the generic shop view with filter "egg" for rolling eggs.
        await send_generic_shop_view(interaction, "nursery", self.user_id, category_filter="egg")

    @discord.ui.button(label="Activity (Nurture)", style=discord.ButtonStyle.secondary, custom_id="nursery_activity")
    async def activity_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await run_nursery_activity(interaction, str(interaction.user.id))

async def send_nursery_view(interaction: discord.Interaction, user_id: str):
    view = NurseryShopView(user_id)
    embed = discord.Embed(title="Nursery", description=view.message, color=discord.Color.green())
    embed.set_image(url=view.image)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
