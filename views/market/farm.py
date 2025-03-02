import discord
from logic.market.farm import build_farm_shop_embed, open_farm_logic

class FarmShopView(discord.ui.View):
    def __init__(self, user_id: str):
        super().__init__(timeout=None)
        self.user_id = user_id

    @discord.ui.button(label="Shop", style=discord.ButtonStyle.primary, custom_id="farm_shop")
    async def shop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Here you could launch a dedicated shop view.
        await interaction.response.send_message(f"Farm Shop action for user {self.user_id} triggered.", ephemeral=True)

    @discord.ui.button(label="Activity (Breed)", style=discord.ButtonStyle.secondary, custom_id="farm_activity")
    async def farm_activity(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed, view = await open_farm_logic(interaction)
        if not interaction.response.is_done():
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        else:
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)

async def send_farm_view(interaction: discord.Interaction, user_id: str):
    embed = await build_farm_shop_embed(user_id)
    view = FarmShopView(user_id)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
