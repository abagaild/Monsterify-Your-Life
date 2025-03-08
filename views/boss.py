import discord
from discord.ui import View, Button
import random
import asyncio
import logging
from typing import Optional

# Import centralized database helpers
from core.database import (
    execute_query,
    fetch_one,
    fetch_all,
    insert_record,
    update_record
)
from core.database import addsub_trainer_currency as add_currency

# --------------------------------------
# Boss UI (Discord View Components)
# --------------------------------------
TAUNT_MESSAGES = [
    "Is that all you've got?",
    "You'll need more than that!",
    "Try harder, warrior!",
    "Your attacks are no match for the boss!",
    "Keep hitting—maybe you'll break through!"
]

class BossUIView(View):
    def __init__(self, user_id: str):
        super().__init__(timeout=None)  # Persistent view
        self.user_id = user_id
        # Preload the boss embed immediately
        self.current_embed = self.get_embed()
        self.refresh_view()

    def get_embed(self) -> discord.Embed:
        boss = get_active_boss()
        if boss:
            embed = discord.Embed(
                title=f"Boss Battle: {boss['name']}",
                color=discord.Color.red()
            )
            embed.add_field(name="Health", value=f"{boss['current_health']} / {boss['max_health']}")
            status = "Defeated" if boss["current_health"] <= 0 else "Alive"
            embed.add_field(name="Status", value=status, inline=False)
            embed.set_image(url=boss["image_link"])
            embed.set_footer(text=boss["flavor_text"])
        else:
            embed = discord.Embed(
                title="No Active Boss",
                description="There is currently no boss active.",
                color=discord.Color.green()
            )
        return embed

    def refresh_view(self):
        # Clear any existing buttons and then add the Refresh button.
        self.clear_items()
        self.add_item(RefreshButton())
        # Add Claim Rewards button if there is no active boss or if the boss is defeated.
        boss = get_active_boss()
        if boss is None or boss["current_health"] <= 0:
            self.add_item(ClaimRewardsButton())

    async def refresh(self, interaction: discord.Interaction):
        # Refresh the embed and the view, then update the message.
        self.current_embed = self.get_embed()
        self.refresh_view()
        await interaction.response.edit_message(embed=self.current_embed, view=self)

class RefreshButton(Button):
    def __init__(self):
        super().__init__(label="Refresh", style=discord.ButtonStyle.secondary, custom_id="boss_refresh")
    async def callback(self, interaction: discord.Interaction):
        await self.view.refresh(interaction)

class ClaimRewardsButton(Button):
    def __init__(self):
        super().__init__(label="Claim Rewards", style=discord.ButtonStyle.success, custom_id="boss_claim_rewards")
    async def callback(self, interaction: discord.Interaction):
        msg = await claim_boss_rewards(str(interaction.user.id))
        self.disabled = True
        await self.view.refresh(interaction)
        await interaction.followup.send(content=msg, ephemeral=True)

# --------------------------------------
# Boss Logic (Database Operations)
# --------------------------------------
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
    # For multi-row update queries, we still use execute_query.
    execute_query("UPDATE boss SET is_active = 0 WHERE is_active = 1")

TAUNT_MESSAGES_LOGIC = [
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
    # Use centralized update_record to update the boss's health.
    update_record("boss", boss["id"], {"current_health": new_health})
    # Use centralized insert_record to log damage.
    insert_record("boss_damage", {"boss_id": boss["id"], "user_id": user_id, "damage": damage_amount})
    if channel:
        attack_msg = f"<@{user_id}> attacked {boss['name']} for **{damage_amount}** damage! Take that!"
        await channel.send(attack_msg)
        taunt_msg = random.choice(TAUNT_MESSAGES_LOGIC)
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
        # Insert rewards using centralized insert_record.
        insert_record("boss_rewards", {
            "boss_id": boss_id,
            "user_id": uid,
            "levels": extra_levels,
            "coins": extra_coins,
            "claimed": 0
        })
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
    # Use centralized insert_record to create a new active boss.
    insert_record("boss", {
        "name": name,
        "max_health": max_health,
        "current_health": max_health,
        "image_link": image_link,
        "flavor_text": flavor_text,
        "is_active": 1
    })

async def force_kill_boss(bot=None, channel=None) -> str:
    boss = get_active_boss()
    if boss and boss["current_health"] > 0:
        # Use centralized update_record to set current_health to 0.
        update_record("boss", boss["id"], {"current_health": 0})
        await finalize_boss_defeat(boss["id"], bot=bot, channel=channel)
        return f"Boss '{boss['name']}' has been force killed."
    return "No active boss to force kill."
