"""
Boss logic module.
Handles active boss retrieval, damage processing, reward distribution, and boss reset.
"""

from typing import Optional

from core.database import cursor, db
from core.currency import add_currency
import random
import asyncio


def get_active_boss() -> Optional[dict]:
    """
    Retrieves the currently active boss from the database.
    Returns a dictionary with boss info or None if no boss is active.
    """
    query = """
        SELECT id, name, max_health, current_health, image_link, flavor_text
        FROM boss
        WHERE is_active = 1
        ORDER BY id DESC
        LIMIT 1
    """
    cursor.execute(query)
    row = cursor.fetchone()
    if row:
        return {
            "id": row[0],
            "name": row[1],
            "max_health": row[2],
            "current_health": row[3],
            "image_link": row[4],
            "flavor_text": row[5],
        }
    return None


def end_current_boss() -> None:
    """Marks the current boss as inactive."""
    cursor.execute("UPDATE boss SET is_active = 0 WHERE is_active = 1")
    db.commit()




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
    """
    Deals damage to the active boss, logs the attack, and sends taunt messages from the boss.
    """
    boss = get_active_boss()
    if not boss:
        if channel:
            await channel.send("No active boss to attack!")
        return

    new_health = max(0, boss["current_health"] - damage_amount)
    cursor.execute("UPDATE boss SET current_health = ? WHERE id = ?", (new_health, boss["id"]))
    db.commit()

    cursor.execute(
        "INSERT INTO boss_damage (boss_id, user_id, damage) VALUES (?, ?, ?)",
        (boss["id"], user_id, damage_amount)
    )
    db.commit()

    if channel:
        # Report the player's damage.
        attack_msg = f"<@{user_id}> attacked {boss['name']} for **{damage_amount}** damage! Take that!"
        await channel.send(attack_msg)

        # Send a random taunt message from the boss.
        taunt_msg = random.choice(TAUNT_MESSAGES)
        await asyncio.sleep(1)  # slight delay for pacing
        await channel.send(taunt_msg)

        # Send an extra random taunt message.
        extra_taunt = random.choice(EXTRA_TAUNT_MESSAGES)
        await asyncio.sleep(1)
        await channel.send(extra_taunt)

    if new_health <= 0:
        await finalize_boss_defeat(boss["id"], bot=bot, channel=channel)


async def finalize_boss_defeat(boss_id: int, bot=None, channel=None) -> None:
    """
    Finalizes boss defeat by computing damage contributions, distributing rewards,
    and marking the boss inactive.
    """
    cursor.execute("SELECT SUM(damage) FROM boss_damage WHERE boss_id = ?", (boss_id,))
    total_damage = cursor.fetchone()[0] or 1

    cursor.execute("SELECT user_id, damage FROM boss_damage WHERE boss_id = ?", (boss_id,))
    damage_rows = cursor.fetchall()
    if not damage_rows:
        end_current_boss()
        if channel:
            await channel.send("Boss defeated but no damage recorded!")
        return

    # Distribute rewards for each user based on damage fraction.
    for uid, dmg in damage_rows:
        fraction = dmg / total_damage
        # Base rewards (can be adjusted)
        base_levels, base_coins = 1, 100
        extra_levels = base_levels + int(round(4 * fraction))
        extra_coins = base_coins + int(round(400 * fraction))
        # Add coins to user account.
        add_currency(uid, extra_coins)
        # Optionally, record rewards in a rewards table.
        cursor.execute(
            "INSERT INTO boss_rewards (boss_id, user_id, levels, coins, claimed) VALUES (?, ?, ?, ?, 0)",
            (boss_id, uid, extra_levels, extra_coins)
        )
        db.commit()

    end_current_boss()
    if channel:
        await channel.send("**The boss has been defeated!** Rewards have been distributed.")


async def claim_boss_rewards(user_id: str) -> str:
    """
    Claims any unclaimed boss rewards for the user.
    Returns a message indicating the outcome.
    """
    cursor.execute("""
        SELECT boss_id, SUM(levels), SUM(coins)
        FROM boss_rewards
        WHERE user_id = ? AND claimed = 0
        GROUP BY user_id
    """, (user_id,))
    row = cursor.fetchone()
    if not row:
        return "You don't have any unclaimed boss rewards."

    boss_id, total_levels, total_coins = row
    total_levels = int(total_levels or 0)
    total_coins = int(total_coins or 0)

    if total_levels <= 0 and total_coins <= 0:
        cursor.execute("UPDATE boss_rewards SET claimed = 1 WHERE user_id = ? AND claimed = 0", (user_id,))
        db.commit()
        return "No meaningful rewards found. Marked as claimed."

    # Add coins to the user's account.
    add_currency(user_id, total_coins)
    # Here you could also update the user's level in your game logic.
    cursor.execute("UPDATE boss_rewards SET claimed = 1 WHERE user_id = ? AND claimed = 0", (user_id,))
    db.commit()
    return f"Claimed rewards: {total_levels} levels and {total_coins} coins."


def reset_boss(name: str, max_health: int, image_link: str, flavor_text: str) -> None:
    """
    Resets the current boss by marking any active boss as inactive and creating a new one.
    """
    end_current_boss()
    query = """
        INSERT INTO boss (name, max_health, current_health, image_link, flavor_text, is_active)
        VALUES (?, ?, ?, ?, ?, 1)
    """
    cursor.execute(query, (name, max_health, max_health, image_link, flavor_text))
    db.commit()


async def force_kill_boss(bot=None, channel=None) -> str:
    """
    Force kills the active boss, setting its health to zero and finalizing defeat.
    """
    boss = get_active_boss()
    if boss and boss["current_health"] > 0:
        cursor.execute("UPDATE boss SET current_health = 0 WHERE id = ?", (boss["id"],))
        db.commit()
        await finalize_boss_defeat(boss["id"], bot=bot, channel=channel)
        return f"Boss '{boss['name']}' has been force killed."
    return "No active boss to force kill."
