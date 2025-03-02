import discord

# Define images and messages for the Apothecary overall view.
IMAGES = [
    "https://example.com/apothocary1.png",
    "https://example.com/apothocary2.png",
]

MESSAGES = [
    "The sweet aroma of berries greets you as you approach the Apothecary—the berries on sale today are extra ripe and inviting.",
    "'Welcome in,' says a sweet voice from behind the counter. She smiles and then leaves to continue sorting farm-fresh berries. There's really nowhere better to get berries of all sorts."
]

async def shop_action(interaction: discord.Interaction, user_id: str) -> None:
    from views.market.generic_shop import send_generic_shop_view
    await send_generic_shop_view(interaction, "apothecary", user_id, category_filter="berries")
