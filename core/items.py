import json
import logging
import random
import discord

from core.database import (
    fetch_one,
    fetch_all,
    execute_query,
    fetch_trainer_by_name,
    get_trainer_inventory,
    add_inventory_item,
    get_trainer_currency,
    addsub_trainer_currency
)

def rarity_value(rarity_str: str) -> int:
    """Converts a rarity string to a numeric weight."""
    mapping = {"common": 1, "uncommon": 3, "rare": 5}
    return mapping.get(rarity_str.lower(), 1)

async def roll_items(amount: int = 1, filter_keyword: str = None, game_corner: bool = False) -> list:
    """
    Rolls a set of items from the items table using weighted rarity.
    If game_corner is True, returns items from a fixed list.
    """
    if game_corner:
        GAME_CORNER_ITEMS = [
            "Snack Combo", "Energy Drink", "Lucky Charm", "Mystic Cookie", "Power Bar"
        ]
        return random.choices(GAME_CORNER_ITEMS, k=amount)
    else:
        rows = fetch_all("SELECT name, effect, rarity, category FROM items")
        if not rows:
            return []
        # If a filter keyword is provided, filter based on the category.
        if filter_keyword:
            filters = [f.strip().lower() for f in filter_keyword.split(",")]
            rows = [row for row in rows if any(f in (row["category"] or "").lower() for f in filters)]
            if not rows:
                return []
        # Group items by rarity for weighted selection
        common_items = [row for row in rows if rarity_value(row["rarity"]) == 1]
        uncommon_items = [row for row in rows if rarity_value(row["rarity"]) == 3]
        rare_items = [row for row in rows if rarity_value(row["rarity"]) == 5]
        weights = [0.50, 0.35, 0.15]
        groups = []
        group_weights = []
        if common_items:
            groups.append(common_items)
            group_weights.append(weights[0])
        if uncommon_items:
            groups.append(uncommon_items)
            group_weights.append(weights[1])
        if rare_items:
            groups.append(rare_items)
            group_weights.append(weights[2])
        total_weight = sum(group_weights)
        norm_weights = [w / total_weight for w in group_weights]
        rolled = []
        for _ in range(amount):
            group = random.choices(groups, weights=norm_weights, k=1)[0]
            chosen = random.choice(group)
            rolled.append(chosen["name"])
        return rolled

async def purchase_item(shop: str, user_id: str, item_name: str, quantity: int) -> (bool, str):
    """
    Processes the purchase of an item from a shop.
    Checks purchase limits and available funds, then deducts funds and updates the shop roll record.
    Also updates the trainer's inventory (in the "ITEMS" category).
    """
    today = "2023-03-01"  # Replace with datetime.date.today().isoformat() for current date.
    row = fetch_one("SELECT items FROM shop_rolls WHERE shop=? AND user_id=? AND date=?", (shop, user_id, today))
    if not row:
        return False, "No items available for today."
    items = json.loads(row["items"]) if isinstance(row["items"], str) else row["items"]
    for item in items:
        if item["name"].lower() == item_name.lower():
            # Check purchase limit
            if item["purchased"] + quantity > item["max_purchase"]:
                available = item["max_purchase"] - item["purchased"]
                return False, f"Purchase exceeds the limit. Only {available} left for today."
            # Get trainer record (assuming the user has at least one trainer)
            trainer_record = fetch_one("SELECT id FROM trainers WHERE player_user_id=? ORDER BY id LIMIT 1", (user_id,))
            if not trainer_record:
                return False, "Trainer not found."
            trainer_id = trainer_record["id"]
            # Check funds using per-trainer currency
            funds = get_trainer_currency(trainer_id)
            total_price = item["price"] * quantity if "price" in item else 0
            if funds < total_price:
                return False, "Insufficient funds."
            # Deduct funds using addsub_trainer_currency
            addsub_trainer_currency(trainer_id, -total_price)
            item["purchased"] += quantity
            new_items_json = json.dumps(items)
            execute_query("UPDATE shop_rolls SET items=? WHERE shop=? AND user_id=? AND date=?",
                          (new_items_json, shop, user_id, today))
            # Update trainer's inventory in the "ITEMS" category
            success = add_inventory_item(trainer_id, "ITEMS", item_name, quantity)
            if success:
                return True, f"Purchased {quantity} × {item_name}."
            else:
                return False, "Purchase recorded, but failed to update inventory."
    return False, f"Item '{item_name}' not found in today's {shop} stock."

async def process_reward(interaction: discord.Interaction, feedback: str, duration_minutes: int,
                         item_roll_kwargs: dict = None) -> None:
    """
    Processes rewards after a game or work session.
    Calculates coins based on duration and feedback,
    awards coins to the trainer, and sends a confirmation message.
    """
    if feedback.lower() == "all":
        multiplier = 1.0
    elif feedback.lower() == "some":
        multiplier = 0.5
    else:
        multiplier = 0.0
    coins_awarded = int(duration_minutes * 100 * multiplier)
    # Retrieve trainer record for the interaction user.
    trainer_row = fetch_one("SELECT id FROM trainers WHERE player_user_id=? ORDER BY id LIMIT 1", (str(interaction.user.id),))
    if trainer_row:
        trainer_id = trainer_row["id"]
        addsub_trainer_currency(trainer_id, coins_awarded)
    await interaction.followup.send(f"You earned {coins_awarded} coins for your work session!", ephemeral=True)

def get_temporary_inventory_columns(trainer: dict) -> list:
    """
    Returns a list of keys from the trainer's inventory JSON that are considered temporary.
    For this example, any key starting with "temp_" is considered temporary.
    """
    inv_str = trainer.get("inventory", "{}")
    try:
        inventory = json.loads(inv_str) if inv_str else {}
    except Exception as e:
        logging.error(f"Error parsing inventory for {trainer.get('character_name', 'Unknown')}: {e}")
        inventory = {}
    return [key for key in inventory.keys() if key.startswith("temp_")]

def get_inventory_quantity(trainer_name: str, item_name: str, category ="ITEMS") -> int:
    """
    Returns the quantity of a given item in the trainer's inventory.
    This uses the new inventory helper by first fetching the trainer record.
    Assumes that items are stored under the "ITEMS" category.
    """
    trainer = fetch_trainer_by_name(trainer_name)
    if not trainer:
        logging.error(f"Trainer {trainer_name} not found while getting inventory quantity.")
        return 0
    trainer_id = trainer["id"]
    inventory = get_trainer_inventory(trainer_id)
    items = inventory.get(category, {})
    return items.get(item_name, 0)

def check_inventory(user_id: str, trainer_name: str, item_name: str, required: int, catagory: str) -> (bool, str):
    trainer = fetch_trainer_by_name(trainer_name)
    if not trainer:
        return False, f"Trainer {trainer_name} not found."
    # Use the correct category "EGGS" from the database helper:
    qty = get_inventory_quantity(trainer["character_name"], item_name, catagory)
    if qty >= required:
        return True, f"{trainer_name} has {qty} {item_name}(s)."
    else:
        return False, f"Not enough {item_name}. Required: {required}, available: {qty}."

