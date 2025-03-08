import random
import discord

# Farm shop configuration data
IMAGES = [
    "https://example.com/farm1.png",
    "https://example.com/farm2.png",
]
MESSAGES = [
    "Welcome to the Farm! Enjoy the rustic charm and bountiful harvests.",
    "Step onto the Farm for fresh produce and country vibes."
]

def get_farm_shop_data() -> (str, str):
    """
    Returns a tuple (image, message) for the farm shop.
    """
    image = random.choice(IMAGES)
    message = random.choice(MESSAGES)
    return image, message

async def build_farm_shop_embed(user_id: str) -> discord.Embed:
    """
    Builds an embed for the Farm shop using a random image and message.
    """
    image, message = get_farm_shop_data()
    embed = discord.Embed(title="Farm", description=message, color=discord.Color.dark_green())
    embed.set_image(url=image)
    return embed

async def open_farm_logic(interaction: discord.Interaction) -> (discord.Embed, discord.ui.View):
    """
    Prepares the farm “activity” embed and the initial breeding setup view.
    """
    embed = discord.Embed(
        title="Welcome to the Farm!",
        description=random.choice([
            "The old barn creaks under the weight of dreams.",
            "A quiet field where nature and magic intertwine."
        ]),
        color=0x00AA00
    )
    embed.set_image(url=random.choice(IMAGES))
    from market.farm_setup import FarmInitialViewLogic
    view = FarmInitialViewLogic(interaction.user)
    return embed, view


class FarmShopView(discord.ui.View):
    def __init__(self, user_id: str):
        super().__init__(timeout=None)
        self.user_id = user_id

    @discord.ui.button(label="Shop", style=discord.ButtonStyle.primary, custom_id="farm_shop")
    async def shop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Launch a dedicated shop view (expandable in the future)
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
    await interaction.followup.send(embed=embed, view=view, ephemeral=True)