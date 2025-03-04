import json
import logging
import random

import discord

from core.database import cursor, fetch_one, execute_query, add_item
from core.currency import get_currency, add_currency


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
        cursor.execute("SELECT name, effect, rarity, category FROM items")
        rows = cursor.fetchall()
        if not rows:
            return []
        if filter_keyword:
            filters = [f.strip().lower() for f in filter_keyword.split(",")]
            rows = [row for row in rows if any(f in (row[3] or "").lower() for f in filters)]
            if not rows:
                return []
        # Group items by rarity for weighted selection
        common_items = [row for row in rows if rarity_value(row[2]) == 1]
        uncommon_items = [row for row in rows if rarity_value(row[2]) == 3]
        rare_items = [row for row in rows if rarity_value(row[2]) == 5]
        weights = [0.50, 0.35, 0.15]  # base probabilities for common, uncommon, rare
        groups = []
        group_weights = []
        if common_items:
            groups.append(common_items); group_weights.append(weights[0])
        if uncommon_items:
            groups.append(uncommon_items); group_weights.append(weights[1])
        if rare_items:
            groups.append(rare_items); group_weights.append(weights[2])
        total_weight = sum(group_weights)
        norm_weights = [w / total_weight for w in group_weights]
        rolled = []
        for _ in range(amount):
            group = random.choices(groups, weights=norm_weights, k=1)[0]
            chosen = random.choice(group)
            rolled.append(chosen[0])
        return rolled

async def purchase_item(shop: str, user_id: str, item_name: str, quantity: int) -> (bool, str):
    """
    Processes the purchase of an item from a shop.
    Checks purchase limits and available funds, then deducts funds and updates the roll record.
    Also updates the trainer's inventory on success.
    """
    today = "2023-03-01"  # Example date; in practice use current date
    row = fetch_one("SELECT items FROM shop_rolls WHERE shop=? AND user_id=? AND date=?", (shop, user_id, today))
    if not row:
        return False, "No items available for today."
    items = json.loads(row[0])
    for item in items:
        if item["name"].lower() == item_name.lower():
            # Check purchase limit
            if item["purchased"] + quantity > item["max_purchase"]:
                available = item["max_purchase"] - item["purchased"]
                return False, f"Purchase exceeds the limit. Only {available} left for today."
            # Check funds
            funds = get_currency(user_id)
            total_price = item["price"] * quantity if "price" in item else 0
            if funds < total_price:
                return False, "Insufficient funds."
            # Deduct currency and update purchase count
            add_currency(user_id, -total_price)
            item["purchased"] += quantity
            new_items_json = json.dumps(items)
            execute_query("UPDATE shop_rolls SET items=? WHERE shop=? AND user_id=? AND date=?", (new_items_json, shop, user_id, today))
            # Update trainer's inventory with the purchased item
            trainer_row = fetch_one("SELECT name FROM trainers WHERE player_user_id = ? ORDER BY id LIMIT 1", (user_id,))
            trainer_name = trainer_row[0] if trainer_row else None
            success = False
            if trainer_name:
                success = await add_item(trainer_name, item_name, quantity)
            if success:
                return True, f"Purchased {quantity} × {item_name}."
            else:
                return False, "Purchase recorded, but failed to update inventory."
    return False, f"Item '{item_name}' not found in today's {shop} stock."


async def process_reward(interaction: discord.Interaction, feedback: str, duration_minutes: int,
                         item_roll_kwargs: dict = None) -> None:
    """
    Processes rewards after a game or work session.

    Parameters:
      feedback: A string ("all", "some", or "none") indicating user feedback.
      duration_minutes: Duration of the session in minutes.
      item_roll_kwargs: Optional dictionary of extra parameters for item rewards.

    This function calculates coins based on duration and feedback,
    awards coins to the user, and sends a confirmation message.
    """
    # Example multiplier based on feedback
    if feedback.lower() == "all":
        multiplier = 1.0
    elif feedback.lower() == "some":
        multiplier = 0.5
    else:
        multiplier = 0.0
    coins_awarded = int(duration_minutes * 100 * multiplier)
    add_currency(str(interaction.user.id), coins_awarded)
    await interaction.followup.send(f"You earned {coins_awarded} coins for your work session!", ephemeral=True)