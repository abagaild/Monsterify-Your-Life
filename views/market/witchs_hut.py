import random
import discord
from logic.evolution import EvolutionFlowView  # centralized evolution flow view
from logic.market.witchs_hut import IMAGES, MESSAGES
from views.market.generic_shop import send_generic_shop_view

class WitchsHutShopView(discord.ui.View):
    def __init__(self, user_id: str) -> None:
        super().__init__(timeout=None)
        self.user_id: str = user_id
        self.image: str = random.choice(IMAGES)
        self.message: str = random.choice(MESSAGES)

    @discord.ui.button(label="Shop", style=discord.ButtonStyle.primary, custom_id="witch_shop")
    async def shop_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await send_generic_shop_view(interaction, "witch", self.user_id, category_filter="stone")

    @discord.ui.button(label="Activity", style=discord.ButtonStyle.secondary, custom_id="witchs_hut_activity")
    async def activity_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        # In a real scenario, the evolution item could be determined dynamically.
        evolution_item: str = "Fire Stone"
        evo_view = EvolutionFlowView(user_id=str(interaction.user.id))
        await interaction.response.send_message("Initiating evolution flow...", view=evo_view, ephemeral=True)

async def send_witchs_hut_view(interaction: discord.Interaction, user_id: str) -> None:
    view = WitchsHutShopView(user_id)
    embed = discord.Embed(
        title="Witch's Hut",
        description=view.message,
        color=discord.Color.dark_purple()
    )
    embed.set_image(url=view.image)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
