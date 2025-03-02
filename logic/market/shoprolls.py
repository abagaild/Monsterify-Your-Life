import random
import datetime
import json
from core.database import cursor, db
from core.items import roll_items

def get_today_date():
    return datetime.date.today().isoformat()

def create_shop_rolls_table():
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS shop_rolls (
            shop TEXT,
            user_id TEXT,
            date TEXT,
            items TEXT,
            PRIMARY KEY (shop, user_id, date)
        )
    """)
    db.commit()

create_shop_rolls_table()

async def roll_shop_items(shop: str, user_id: str, *, category_filter: str = None, exclude_categories: list = None, count_range: tuple = (2, 5)):
    """
    Rolls a set of items for the given shop and user.
    Before rolling, any previous roll (not matching today's date) is deleted,
    ensuring that a new roll is generated only once per day.
    """
    today = datetime.date.today().isoformat()
    # Delete previous rolls.
    cursor.execute("DELETE FROM shop_rolls WHERE shop=? AND user_id=? AND date<>?", (shop, user_id, today))
    db.commit()

    # Check if today's roll exists.
    cursor.execute("SELECT items FROM shop_rolls WHERE shop=? AND user_id=? AND date=?", (shop, user_id, today))
    row = cursor.fetchone()
    if row:
        return json.loads(row[0])

    count = random.randint(*count_range)
    if exclude_categories:
        all_items = await roll_items(50)
        filtered = [item for item in all_items if not any(ex in (item['name'].lower() if isinstance(item, dict) else item.lower()) for ex in exclude_categories)]
        if len(filtered) < count:
            rolled = filtered
        else:
            rolled = random.sample(filtered, count)
    else:
        filter_keyword = category_filter if category_filter else None
        rolled = await roll_items(count, filter_keyword=filter_keyword)

    items = []
    for item in rolled:
        price = random.randint(2000, 60000)
        max_purchase = random.randint(1, 3)
        if isinstance(item, dict):
            item_name = item.get("name", "")
            effect = item.get("effect", "")
            rarity = item.get("rarity", "")
        else:
            item_name = item
            effect = ""
            rarity = ""
        items.append({
            "name": item_name,
            "effect": effect,
            "rarity": rarity,
            "price": price,
            "max_purchase": max_purchase,
            "purchased": 0
        })
    items_json = json.dumps(items)
    cursor.execute("INSERT INTO shop_rolls (shop, user_id, date, items) VALUES (?, ?, ?, ?)", (shop, user_id, today, items_json))
    db.commit()
    return items

async def purchase_item(shop: str, user_id: str, item_name: str, quantity: int):
    today = get_today_date()
    cursor.execute("SELECT items FROM shop_rolls WHERE shop=? AND user_id=? AND date=?", (shop, user_id, today))
    row = cursor.fetchone()
    if not row:
        return False, "No items available in the shop for today."
    items = json.loads(row[0])
    for item in items:
        if item["name"].lower() == item_name.lower():
            if item["purchased"] + quantity > item["max_purchase"]:
                return False, f"You can only purchase {item['max_purchase'] - item['purchased']} more of {item_name}."
            total_price = item["price"] * quantity
            from core.currency import get_currency, add_currency
            funds = get_currency(user_id)
            if funds < total_price:
                return False, "Insufficient funds."
            add_currency(user_id, -total_price)
            item["purchased"] += quantity
            new_items_json = json.dumps(items)
            cursor.execute("UPDATE shop_rolls SET items=? WHERE shop=? AND user_id=? AND date=?", (new_items_json, shop, user_id, today))
            db.commit()
            return True, f"Purchased {quantity} x {item_name} for {total_price} coins."
    return False, f"Item {item_name} not found in shop."
