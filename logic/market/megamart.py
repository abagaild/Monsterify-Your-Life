IMAGES = [
    "https://i.imgur.com/83k5ZKf.png"
]
MESSAGES = [
    "Welcome to Megamart—your one-stop shop for magical merchandise!",
    "Discover enchanted items and rare finds at Megamart."
]


async def use_items_action(user_id: str, trainer_name: str, usage_data: dict) -> str:
    used_items = []
    for item, amount in usage_data.items():
        from core.google_sheets import update_character_sheet_item
        success = await update_character_sheet_item(trainer_name, item, -amount)
        if success:
            used_items.append(f"{amount} {item}")
        else:
            return f"Failed to use {amount} {item}. Please check your inventory."
    return f"You used {', '.join(used_items)}."
