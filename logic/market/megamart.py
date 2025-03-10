import discord

IMAGES = [
    "https://i.imgur.com/83k5ZKf.png"
]
MESSAGES = [
    "Welcome to Megamart—your one-stop shop for magical merchandise!",
    "Discover enchanted items and rare finds at Megamart."
]

async def use_items_action(interaction: discord.Interaction, trainer_name: str, usage_data: dict) -> str:
    await interaction.response.defer(ephemeral=True)
    used_items = []
    for item, amount in usage_data.items():
        from core.database import update_character_sheet_item
        success = await update_character_sheet_item(trainer_name, item, -amount)
        if success:
            used_items.append(f"{amount} {item}")
        else:
            return f"Failed to use {amount} {item}. Please check your inventory."
    return f"You used {', '.join(used_items)}."
