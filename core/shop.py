import random
import datetime
import json
from core.database import execute_query, fetch_one, add_inventory_item, addsub_trainer_currency
from core.items import roll_items
from core.database import get_currency


def get_today_date():
    return datetime.date.today().isoformat()


def create_generic_shop_table():
    create_query = """
        CREATE TABLE IF NOT EXISTS generic_shop_rolls (
            shop TEXT,
            user_id TEXT,
            date TEXT,
            items TEXT,
            PRIMARY KEY (shop, user_id, date)
        )
    """
    execute_query(create_query)


create_generic_shop_table()


async def roll_generic_shop_items(shop: str, user_id: str, category_filter: str = None,
                                  exclude_categories: list = None, default_count_range: tuple = (2, 5)):
    today = get_today_date()
    # Remove any outdated roll for this shop and user
    execute_query("DELETE FROM generic_shop_rolls WHERE shop=? AND user_id=? AND date<>?", (shop, user_id, today))
    # Check if today's roll already exists.
    row = fetch_one("SELECT items FROM generic_shop_rolls WHERE shop=? AND user_id=? AND date=?",
                    (shop, user_id, today))
    if row:
        return json.loads(row["items"])
    # Determine number of items to roll
    config = {}  # You can add shop-specific config if needed
    count_range = config.get("count_range", default_count_range)
    count = random.randint(*count_range)
    # Roll items, applying category filters if provided
    if exclude_categories:
        all_items = await roll_items(50)
        filtered = [it for it in all_items if not any(
            ex in (it['name'].lower() if isinstance(it, dict) else it.lower()) for ex in exclude_categories)]
        rolled = filtered if len(filtered) < count else random.sample(filtered, count)
    else:
        filter_keyword = category_filter if category_filter else None
        rolled = await roll_items(count, filter_keyword=filter_keyword)
    # Generate random prices and structure the items
    items = []
    for item in rolled:
        base_price = random.randint(2000, 20000)
        price = base_price
        items.append({
            "name": item if isinstance(item, str) else item.get("name", ""),
            "price": price,
            "purchased": 0,
            "max_purchase": 9999  # treat None as no limit
        })
    # Store the rolled items for today
    execute_query("INSERT INTO generic_shop_rolls (shop, user_id, date, items) VALUES (?, ?, ?, ?)",
                  (shop, user_id, today, json.dumps(items)))
    return items


async def purchase_shop_item(ctx, shop: str, item_name: str, quantity: int, category: str = "ITEMS"):
    """
    Processes the purchase of an item from a shop.
    Checks purchase limits, available funds, then deducts funds and updates the shop roll record.
    Also updates the trainer's inventory in the specified category.

    Parameters:
      - shop: the name of the shop.
      - item_name: the item to purchase.
      - quantity: number of items to purchase.
      - category: the inventory category to update (default "ITEMS").
    """
    user_id = str(ctx.author.id)
    items = await roll_generic_shop_items(shop, user_id)
    # Find the item in today's rolled list
    for item in items:
        if item["name"].lower() == item_name.lower():
            total_price = item["price"] * quantity
            funds = get_currency(user_id)
            if funds < total_price:
                await ctx.send("Insufficient funds.")
                return
            if item["purchased"] + quantity > item["max_purchase"]:
                await ctx.send("Purchase exceeds the daily limit for this item.")
                return
            # Deduct funds using per-trainer currency helper
            trainer_row = fetch_one("SELECT id FROM trainers WHERE player_user_id=? ORDER BY id LIMIT 1", (user_id,))
            if not trainer_row:
                await ctx.send("Trainer not found.")
                return
            trainer_id = trainer_row["id"]
            addsub_trainer_currency(trainer_id, -total_price)
            item["purchased"] += quantity
            new_items_json = json.dumps(items)
            execute_query("UPDATE generic_shop_rolls SET items=? WHERE shop=? AND user_id=? AND date=?",
                          (new_items_json, shop, user_id, get_today_date()))
            # Update the trainer's inventory in the given category.
            success = add_inventory_item(trainer_id, category, item_name, quantity)
            if success:
                await ctx.send(f"Successfully purchased {quantity} × **{item_name}**!")
                return
            else:
                await ctx.send("Purchase recorded, but failed to update inventory.")
                return
    await ctx.send(f"Item **{item_name}** is not available in the {shop.title()} shop today.")
