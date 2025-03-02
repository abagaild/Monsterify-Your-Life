import random
import discord

# Farm shop configuration
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
    (The breeding setup view is provided by logic.farm_setup.)
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
    # Import the breeding setup view from the logic layer.
    from logic.market.farm_setup import FarmInitialViewLogic
    view = FarmInitialViewLogic(interaction.user)
    return embed, view
