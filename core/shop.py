import random
import datetime
import json
from core.database import cursor, db
from core.items import roll_items
from core.currency import get_currency, add_currency

def get_today_date():
    return datetime.date.today().isoformat()

def create_generic_shop_table():
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS generic_shop_rolls (
            shop TEXT,
            user_id TEXT,
            date TEXT,
            items TEXT,
            PRIMARY KEY (shop, user_id, date)
        )
    """)
    db.commit()

create_generic_shop_table()

# Configuration for each shop type
SHOP_CONFIG = {
    "antique": {"max_purchase": 1, "price_multiplier": 1, "count_range": (1, 3)},
    "pirate":  {"max_purchase": None, "price_multiplier": 3, "count_range": (2, 5)},
    "bakery":  {"max_purchase": None, "price_multiplier": 1, "count_range": (2, 5)},
    "nursery": {"max_purchase": None, "price_multiplier": 1, "count_range": (2, 5)},
    "witch":   {"max_purchase": None, "price_multiplier": 1, "count_range": (2, 5)},
    "megamart":{"max_purchase": None, "price_multiplier": 1, "count_range": (2, 5)}
}

RARITY_MULTIPLIER = {"common": 1, "uncommon": 3, "rare": 5}

async def roll_generic_shop_items(shop: str, user_id: str, category_filter: str = None, exclude_categories: list = None, default_count_range: tuple = (2, 5)):
    """
    Rolls a daily set of items for the given shop and user.
    Ensures only one roll per day per user, and reuses the roll if already done.
    """
    today = get_today_date()
    # Remove any outdated roll for this shop and user
    cursor.execute("DELETE FROM generic_shop_rolls WHERE shop=? AND user_id=? AND date<>?", (shop, user_id, today))
    db.commit()
    # Check if today's roll already exists
    cursor.execute("SELECT items FROM generic_shop_rolls WHERE shop=? AND user_id=? AND date=?", (shop, user_id, today))
    row = cursor.fetchone()
    if row:
        return json.loads(row[0])
    # Determine number of items to roll
    config = SHOP_CONFIG.get(shop.lower(), {})
    count_range = config.get("count_range", default_count_range)
    count = random.randint(*count_range)
    # Roll items, applying category filters if provided
    if exclude_categories:
        all_items = await roll_items(50)
        filtered = [it for it in all_items if not any(ex in it.lower() for ex in exclude_categories)]
        rolled = filtered if len(filtered) < count else random.sample(filtered, count)
    else:
        filter_keyword = category_filter if category_filter else None
        rolled = await roll_items(count, filter_keyword=filter_keyword)
    # Generate random prices and structure the items
    items = []
    for item in rolled:
        base_price = random.randint(2000, 20000)
        rarity = "common"
        if item in RARITY_MULTIPLIER:
            rarity = item  # In our context, item name might itself indicate rarity
        price = base_price * RARITY_MULTIPLIER.get(rarity, 1) * config.get("price_multiplier", 1)
        items.append({
            "name": item,
            "price": price,
            "purchased": 0,
            "max_purchase": config.get("max_purchase", 1) or 9999  # treat None as effectively no limit
        })
    # Store the rolled items for today
    cursor.execute("INSERT INTO generic_shop_rolls (shop, user_id, date, items) VALUES (?, ?, ?, ?)", (shop, user_id, today, json.dumps(items)))
    db.commit()
    return items

async def purchase_shop_item(ctx, shop: str, item_name: str, quantity: int):
    """
    Facilitates the purchase of an item from the daily shop selection.
    Checks user funds and purchase limits, updates the database and notifies the user.
    """
    user_id = str(ctx.author.id)
    items = await roll_generic_shop_items(shop, user_id)
    # Find the item in today's rolled list
    for item in items:
        if item["name"].lower() == item_name.lower():
            total_price = item["price"] * quantity
            # Check currency
            funds = get_currency(user_id)
            if funds < total_price:
                await ctx.send("Insufficient funds.")
                return
            # Check max purchase limit
            if item["purchased"] + quantity > item["max_purchase"]:
                await ctx.send("Purchase exceeds the daily limit for this item.")
                return
            # Deduct currency and update purchase count
            add_currency(user_id, -total_price)
            item["purchased"] += quantity
            new_items_json = json.dumps(items)
            cursor.execute("UPDATE generic_shop_rolls SET items=? WHERE shop=? AND user_id=? AND date=?", (new_items_json, shop, user_id, get_today_date()))
            db.commit()
            await ctx.send(f"Successfully purchased {quantity} × **{item_name}**!")
            return
    await ctx.send(f"Item **{item_name}** is not available in the {shop.title()} shop today.")
