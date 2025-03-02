import json
import logging

from core.database import cursor, fetch_one, execute_query, get_currency, add_currency
from core.google_sheets import update_character_sheet_item, gc


def rarity_value(rarity_str: str) -> int:
    """
    Converts a rarity string to a numeric weight.
    """
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
        # Group items by rarity.
        common_items = [row for row in rows if rarity_value(row[2]) == 1]
        uncommon_items = [row for row in rows if rarity_value(row[2]) == 3]
        rare_items = [row for row in rows if rarity_value(row[2]) == 5]
        # Define base probabilities.
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
        norm_weights = [w/total_weight for w in group_weights]
        rolled = []
        for _ in range(amount):
            group = random.choices(groups, weights=norm_weights, k=1)[0]
            chosen = random.choice(group)
            rolled.append(chosen[0])
        return rolled

async def purchase_item(shop: str, user_id: str, item_name: str, quantity: int) -> (bool, str):
    """
    Processes the purchase of an item.
    Checks purchase limits and available funds, then deducts funds and updates the roll record.
    Also calls update_character_sheet_item to reflect changes on the trainer's sheet.
    """
    # For demonstration, assume we have a table 'shop_rolls' keyed by (shop, user_id, date).
    # This example uses a fixed date string; replace with your date logic.
    today = "2023-03-01"
    row = fetch_one("SELECT items FROM shop_rolls WHERE shop=? AND user_id=? AND date=?", (shop, user_id, today))
    if not row:
        return False, "No items available for today."
    items = json.loads(row[0])
    for item in items:
        if item["name"].lower() == item_name.lower():
            if item["purchased"] + quantity > item["max_purchase"]:
                available = item["max_purchase"] - item["purchased"]
                return False, f"You can only purchase {available} more of {item_name}."
            total_price = item["price"] * quantity
            funds = get_currency(user_id)
            if funds < total_price:
                return False, "Insufficient funds."
            add_currency(user_id, -total_price)
            item["purchased"] += quantity
            new_items = json.dumps(items)
            execute_query("UPDATE shop_rolls SET items=? WHERE shop=? AND user_id=? AND date=?", (new_items, shop, user_id, today))
            success = await update_character_sheet_item(shop, item_name, quantity)
            if success:
                return True, f"Purchased {quantity} of {item_name}."
            else:
                return True, f"Purchased {quantity} of {item_name}, but failed to update the sheet."
    return False, f"Item {item_name} not found."

def get_inventory_quantity(trainer_name: str, item_name: str) -> int:
    """
    Checks the trainer's Google Sheet Inventory and returns the quantity available for a given item.
    Assumes the inventory is organized in paired cells (quantity to the left of item name).
    """
    try:
        ss = gc.open(trainer_name)
        ws = ss.worksheet("Inventory")
    except Exception as e:
        return 0
    rows = ws.get_all_values()
    for row in rows:
        for col in range(1, len(row)):
            cell_value = row[col].strip() if row[col] else ""
            if cell_value.lower() == item_name.lower():
                qty_str = row[col-1].strip() if col-1 < len(row) else "0"
                try:
                    return int(qty_str)
                except ValueError:
                    return 0
    return 0

def check_inventory(user_id: str, trainer_name: str, item_name: str, amount_needed: int = 1) -> (bool, str):
    """
    Checks whether the given trainer has enough of a specific item.

    The function opens the trainer's Google Sheet (named exactly as trainer_name),
    then looks in the "Inventory" worksheet. This worksheet is assumed to be laid out
    in pairs of cells: an amount cell immediately to the left of an item name cell.

    Parameters:
      - user_id: the user's id (for logging or future extension)
      - trainer_name: the name of the trainer's sheet
      - item_name: the name of the item to check for (case-insensitive)
      - amount_needed: the required quantity (default 1)

    Returns:
      - True, "" if the trainer has at least the required quantity.
      - False, "TrainerName does not have enough of ItemName to complete this action"
        if not enough is found.
    """
    try:
        # Open the trainer's spreadsheet by name.
        ss = gc.open(trainer_name)
    except Exception as e:
        logging.error(f"Error opening spreadsheet for {trainer_name}: {e}")
        return False, f"Error opening {trainer_name}'s sheet."

    try:
        # Get the "Inventory" worksheet.
        worksheet = ss.worksheet("Inventory")
    except Exception as e:
        logging.error(f"Error accessing Inventory worksheet for {trainer_name}: {e}")
        return False, f"Could not find Inventory for {trainer_name}."

    # Retrieve all the values in the sheet.
    # It is assumed that the inventory is organized in rows of paired cells:
    # [quantity, item name, quantity, item name, ...]
    rows = worksheet.get_all_values()

    # Iterate over all rows and look at each pair.
    for row in rows:
        # Loop through columns starting from index 1 (which should contain item names)
        for col in range(1, len(row)):
            cell_value = row[col].strip() if row[col] else ""
            if cell_value.lower() == item_name.lower():
                # Get the quantity from the cell immediately to the left.
                if col - 1 >= 0:
                    qty_str = row[col - 1].strip() if row[col - 1] else "0"
                    try:
                        qty = int(qty_str)
                    except ValueError:
                        qty = 0
                    if qty >= amount_needed:
                        return True, ""
                    else:
                        return False, f"{trainer_name} does not have enough of {item_name} to complete this action."
                else:
                    return False, f"Inventory format error: no quantity found for {item_name}."

    # If the item was not found at all, also return a failure.
    return False, f"{trainer_name} does not have enough of {item_name} to complete this action."


import random
import discord
from core.currency import add_currency  # Function to update a user's currency balance


async def process_reward(
        interaction: discord.Interaction,
        feedback: str,
        duration_minutes: int,
        item_roll_kwargs: dict = None
) -> None:
    """
    Processes rewards for a work session based on the user's feedback.

    Args:
        interaction (discord.Interaction): The interaction object to use for responses.
        feedback (str): User feedback on the session ("all", "some", or "none").
        duration_minutes (int): The duration of the work session in minutes.
        item_roll_kwargs (dict, optional): Extra parameters for item reward logic.
            For example, if {"game_corner": True} is provided, an item reward may be rolled.

    Reward Logic:
      - Base coin reward is computed as: duration_minutes * coins_per_minute.
      - A multiplier is applied based on feedback:
            "all"  => multiplier 1.0
            "some" => multiplier 0.5
            "none" => multiplier 0.1
      - An optional item reward is given if the game_corner flag is True and the roll succeeds.

    The function updates the user's currency and sends a follow-up message summarizing the rewards.
    """
    coins_per_minute = 10
    feedback = feedback.lower().strip()
    if feedback == "all":
        factor = 1.0
    elif feedback == "some":
        factor = 0.5
    elif feedback == "none":
        factor = 0.1
    else:
        factor = 0.0

    coin_reward = int(duration_minutes * coins_per_minute * factor)
    # Award the coins to the user (user id is taken as a string).
    add_currency(str(interaction.user.id), coin_reward)

    reward_message = f"You earned {coin_reward} coins for your work session!"

    # Optional item roll if extra keyword arguments are provided.
    item_reward = None
    if item_roll_kwargs and item_roll_kwargs.get("game_corner"):
        # Define a simple pool of game corner items.
        item_pool = ["Snack Combo", "Energy Drink", "Lucky Charm", "Mystic Cookie", "Power Bar"]
        # For instance, use a 20% chance to grant an item.
        if random.random() < 0.20:
            item_reward = random.choice(item_pool)
            reward_message += f" Additionally, you received a **{item_reward}**!"

    await interaction.followup.send(reward_message, ephemeral=True)
