import random
import datetime
import json
from core.database import cursor, db
from core.items import roll_items
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

# Shop-specific configuration.
SHOP_CONFIG = {
    "antique": {
        "max_purchase": 1,
        "price_multiplier": 1,
        "count_range": (1, 3)
    },
    "pirate": {
        "max_purchase": None,
        "price_multiplier": 3,
        "count_range": (2, 5)
    },
    "bakery": {
        "max_purchase": None,
        "price_multiplier": 1,
        "count_range": (2, 5)
    },
    "nursery": {
        "max_purchase": None,
        "price_multiplier": 1,
        "count_range": (2, 5)
    },
    "witch": {
        "max_purchase": None,
        "price_multiplier": 1,
        "count_range": (2, 5)
    },
    "megamart": {
        "max_purchase": None,
        "price_multiplier": 1,
        "count_range": (2, 5)
    }
}

RARITY_MULTIPLIER = {
    "common": 1,
    "uncommon": 3,
    "rare": 5
}

async def roll_generic_shop_items(shop: str, user_id: str, category_filter: str = None, exclude_categories: list = None, default_count_range: tuple = (2, 5)):
    """
    Rolls a daily set of items for the given shop.
    Before rolling new items, any records for this shop and user with a date different from today are deleted.
    Then, if no roll exists for today, a new roll is generated and stored.
    """
    today = get_today_date()
    # Delete any previous day's roll for this shop and user.
    cursor.execute("DELETE FROM generic_shop_rolls WHERE shop=? AND user_id=? AND date<>?", (shop, user_id, today))
    db.commit()

    # Check if a roll for today already exists.
    cursor.execute("SELECT items FROM generic_shop_rolls WHERE shop=? AND user_id=? AND date=?", (shop, user_id, today))
    row = cursor.fetchone()
    if row:
        return json.loads(row[0])

    config = SHOP_CONFIG.get(shop.lower(), {})
    count_range = config.get("count_range", default_count_range)
    count = random.randint(*count_range)

    if exclude_categories:
        all_items = await roll_items(50)
        filtered = [item for item in all_items if not any(ex in item.lower() for ex in exclude_categories)]
        if len(filtered) < count:
            rolled = filtered
        else:
            rolled = random.sample(filtered, count)
    else:
        filter_keyword = category_filter if category_filter else None
        rolled = await roll_items(count, filter_keyword=filter_keyword)

    items = []
    for item in rolled:
        base_price = random.randint(2000, 20000)
        rarity = random.choice(["common", "uncommon", "rare"])
        rarity_multiplier = RARITY_MULTIPLIER[rarity]
        shop_price_multiplier = config.get("price_multiplier", 1)
        price = base_price * rarity_multiplier * shop_price_multiplier
        max_purchase = config.get("max_purchase")
        if max_purchase is None:
            max_purchase = random.randint(1, 3)
        effect = f"Effect of {item}"
        items.append({
            "name": item,
            "effect": effect,
            "price": price,
            "max_purchase": max_purchase,
            "purchased": 0,
            "rarity": rarity
        })
    items_json = json.dumps(items)
    cursor.execute("INSERT INTO generic_shop_rolls (shop, user_id, date, items) VALUES (?, ?, ?, ?)", (shop, user_id, today, items_json))
    db.commit()
    return items

async def purchase_generic_shop_item(shop: str, user_id: str, item_name: str, quantity: int):
    """
    Processes a purchase for a given shop.
    """
    today = get_today_date()
    cursor.execute("SELECT items FROM generic_shop_rolls WHERE shop=? AND user_id=? AND date=?", (shop, user_id, today))
    row = cursor.fetchone()
    if not row:
        return False, "No items available in the shop for today."
    items = json.loads(row[0])
    for item in items:
        if item["name"].lower() == item_name.lower():
            if item["purchased"] + quantity > item["max_purchase"]:
                available = item["max_purchase"] - item["purchased"]
                return False, f"You can only purchase {available} more of {item_name}."
            total_price = item["price"] * quantity
            from core.currency import get_currency, add_currency
            funds = get_currency(user_id)
            if funds < total_price:
                return False, "Insufficient funds."
            add_currency(user_id, -total_price)
            item["purchased"] += quantity
            new_items_json = json.dumps(items)
            cursor.execute("UPDATE generic_shop_rolls SET items=? WHERE shop=? AND user_id=? AND date=?", (new_items_json, shop, user_id, today))
            db.commit()
            return True, f"Purchased {quantity} x {item_name} for {total_price} coins."
    return False, f"Item {item_name} not found in shop."
