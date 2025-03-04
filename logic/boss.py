"""
Boss logic module.
Handles active boss retrieval, damage processing, reward distribution, and boss reset.
"""
import random
import asyncio
from typing import Optional
from core.database import execute_query, fetch_one, fetch_all
from core.currency import add_currency
import logging

def get_active_boss() -> Optional[dict]:
    query = """
        SELECT id, name, max_health, current_health, image_link, flavor_text
        FROM boss
        WHERE is_active = 1
        ORDER BY id DESC
        LIMIT 1
    """
    row = fetch_one(query)
    if row:
        return {
            "id": row["id"],
            "name": row["name"],
            "max_health": row["max_health"],
            "current_health": row["current_health"],
            "image_link": row["image_link"],
            "flavor_text": row["flavor_text"],
        }
    return None

def end_current_boss() -> None:
    execute_query("UPDATE boss SET is_active = 0 WHERE is_active = 1")

TAUNT_MESSAGES = [
    "'tis but a scratch, is that all you've got?",
    "Is that all you've got?",
    "You'll need more than that!",
    "Try harder, warrior!",
    "Your attacks are no match for me!",
    "Keep hitting—maybe you'll break through!"
]

EXTRA_TAUNT_MESSAGES = [
    "You call that an attack?",
    "I've seen snails move faster than you!",
    "Is that the best you can do?",
    "You'll never defeat me!",
    "Pathetic!"
]

async def deal_boss_damage(user_id: str, damage_amount: int, bot=None, channel=None) -> None:
    boss = get_active_boss()
    if not boss:
        if channel:
            await channel.send("No active boss to attack!")
        return
    new_health = max(0, boss["current_health"] - damage_amount)
    execute_query("UPDATE boss SET current_health = ? WHERE id = ?", (new_health, boss["id"]))
    execute_query(
        "INSERT INTO boss_damage (boss_id, user_id, damage) VALUES (?, ?, ?)",
        (boss["id"], user_id, damage_amount)
    )
    if channel:
        attack_msg = f"<@{user_id}> attacked {boss['name']} for **{damage_amount}** damage! Take that!"
        await channel.send(attack_msg)
        taunt_msg = random.choice(TAUNT_MESSAGES)
        await asyncio.sleep(1)
        await channel.send(taunt_msg)
        extra_taunt = random.choice(EXTRA_TAUNT_MESSAGES)
        await asyncio.sleep(1)
        await channel.send(extra_taunt)
    if new_health <= 0:
        await finalize_boss_defeat(boss["id"], bot=bot, channel=channel)

async def finalize_boss_defeat(boss_id: int, bot=None, channel=None) -> None:
    row = fetch_one("SELECT SUM(damage) AS total FROM boss_damage WHERE boss_id = ?", (boss_id,))
    total_damage = row["total"] or 1
    damage_rows = fetch_all("SELECT user_id, damage FROM boss_damage WHERE boss_id = ?", (boss_id,))
    if not damage_rows:
        end_current_boss()
        if channel:
            await channel.send("Boss defeated but no damage recorded!")
        return
    for entry in damage_rows:
        uid, dmg = entry["user_id"], entry["damage"]
        fraction = dmg / total_damage
        base_levels, base_coins = 1, 100
        extra_levels = base_levels + int(round(4 * fraction))
        extra_coins = base_coins + int(round(400 * fraction))
        add_currency(uid, extra_coins)
        execute_query(
            "INSERT INTO boss_rewards (boss_id, user_id, levels, coins, claimed) VALUES (?, ?, ?, ?, 0)",
            (boss_id, uid, extra_levels, extra_coins)
        )
    end_current_boss()
    if channel:
        await channel.send("**The boss has been defeated!** Rewards have been distributed.")

async def claim_boss_rewards(user_id: str) -> str:
    row = fetch_one(
        """
        SELECT boss_id, SUM(levels) AS total_levels, SUM(coins) AS total_coins
        FROM boss_rewards
        WHERE user_id = ? AND claimed = 0
        GROUP BY user_id
        """,
        (user_id,)
    )
    if not row:
        return "You don't have any unclaimed boss rewards."
    boss_id = row["boss_id"]
    total_levels = int(row["total_levels"] or 0)
    total_coins = int(row["total_coins"] or 0)
    if total_levels <= 0 and total_coins <= 0:
        execute_query("UPDATE boss_rewards SET claimed = 1 WHERE user_id = ? AND claimed = 0", (user_id,))
        return "No meaningful rewards found. Marked as claimed."
    add_currency(user_id, total_coins)
    execute_query("UPDATE boss_rewards SET claimed = 1 WHERE user_id = ? AND claimed = 0", (user_id,))
    return f"Claimed rewards: {total_levels} levels and {total_coins} coins."

def reset_boss(name: str, max_health: int, image_link: str, flavor_text: str) -> None:
    end_current_boss()
    query = """
        INSERT INTO boss (name, max_health, current_health, image_link, flavor_text, is_active)
        VALUES (?, ?, ?, ?, ?, 1)
    """
    execute_query(query, (name, max_health, max_health, image_link, flavor_text))

async def force_kill_boss(bot=None, channel=None) -> str:
    boss = get_active_boss()
    if boss and boss["current_health"] > 0:
        execute_query("UPDATE boss SET current_health = 0 WHERE id = ?", (boss["id"],))
        await finalize_boss_defeat(boss["id"], bot=bot, channel=channel)
        return f"Boss '{boss['name']}' has been force killed."
    return "No active boss to force kill."
