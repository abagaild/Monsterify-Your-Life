import asyncio
import datetime
import random
import discord
from discord import Embed
from core.database import execute_query, fetch_one, update_character_sheet_item, increment_garden_harvest
from core.items import roll_items
from core.rollmons import roll_mons
from data.garden_tasks import GARDEN_TASKS
from data.messages import (
    GARDEN_WELCOME_FLAVOR_TEXTS, GARDEN_WELCOME_IMAGES,
    GARDEN_HARVESTED_FLAVOR_TEXTS, GARDEN_HARVESTED_IMAGES,
    GARDEN_NO_HARVESTS_FLAVOR_TEXTS, GARDEN_NO_HARVESTS_IMAGES,
    GARDEN_TASK_DOING_FLAVOR_TEXTS, GARDEN_TASK_DOING_IMAGES,
    GARDEN_TASK_ACCOMPLISHED_FLAVOR_TEXTS, GARDEN_TASK_ACCOMPLISHED_IMAGES,
    GARDEN_SPECIAL_FLAVOR_TEXTS, GARDEN_SPECIAL_IMAGES
)

def claim_garden_harvest(ctx):
    user_id = str(ctx.user.id)
    row = fetch_one("SELECT amount FROM garden_harvest WHERE user_id = ?", (user_id,))
    if row is None or row["amount"] <= 0:
        no_harvest_embed = Embed(
            title="No Harvest Available",
            description="🌱 You haven't completed any garden tasks yet. Tackle some tasks to grow your harvest!",
            color=0xFFA500
        )
        no_harvest_embed.set_image(url=random.choice(GARDEN_NO_HARVESTS_IMAGES))
        no_harvest_embed.set_footer(text=random.choice(GARDEN_NO_HARVESTS_FLAVOR_TEXTS))
        return no_harvest_embed
    harvest_amount = row["amount"]
    now = datetime.datetime.now().isoformat()
    execute_query("UPDATE garden_harvest SET amount = 0, last_claimed = ? WHERE user_id = ?", (now, user_id))
    # Note: roll_items is async, so we use asyncio.run if not already in an async context.
    rolled_items = asyncio.run(roll_items(harvest_amount))
    harvested_embed = Embed(
        title="Harvest Claimed!",
        description=f"🌿 You harvested **{harvest_amount} item(s)**!\nYou received: {', '.join(rolled_items)}",
        color=0x00FF00
    )
    harvested_embed.set_image(url=random.choice(GARDEN_HARVESTED_IMAGES))
    harvested_embed.set_footer(text=random.choice(GARDEN_HARVESTED_FLAVOR_TEXTS))
    return harvested_embed

class TaskDoneView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=600)
        self.completed = False

    @discord.ui.button(label="Task Done", style=discord.ButtonStyle.success)
    async def task_done(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.completed = True
        self.stop()
        await interaction.response.send_message("Task confirmed!", ephemeral=True)

async def process_garden(ctx, mode: str = "tend"):
    user_id = str(ctx.user.id)
    welcome_embed = Embed(
        title="Welcome to Your Garden!",
        description=random.choice(GARDEN_WELCOME_FLAVOR_TEXTS),
        color=0x00AA00
    )
    welcome_embed.set_image(url=random.choice(GARDEN_WELCOME_IMAGES))
    await ctx.followup.send(embed=welcome_embed)
    if mode == "harvest":
        embed = claim_garden_harvest(ctx)
        await ctx.followup.send(embed=embed)
        return
    task_text = random.choice(GARDEN_TASKS)
    task_embed = Embed(
        title="Garden Task",
        description=f"🌿 {task_text}\nClick the **Task Done** button when you complete this task!",
        color=0x0000FF
    )
    task_embed.set_image(url=random.choice(GARDEN_TASK_DOING_IMAGES))
    task_embed.set_footer(text=random.choice(GARDEN_TASK_DOING_FLAVOR_TEXTS))
    task_view = TaskDoneView()
    await ctx.followup.send(embed=task_embed, view=task_view)
    await task_view.wait()
    if not task_view.completed:
        await ctx.followup.send("⏳ Task timeout. Try again when you're ready!")
        return
    increment_garden_harvest(user_id, count=1)
    if random.random() < 0.20:
        special_embed = Embed(
            title="Special Garden Encounter",
            description="🌿 You feel a strange energy... A special creature appears!",
            color=0x800080
        )
        special_embed.set_image(url=random.choice(GARDEN_SPECIAL_IMAGES))
        special_embed.set_footer(text=random.choice(GARDEN_SPECIAL_FLAVOR_TEXTS))
        await ctx.followup.send(embed=special_embed)
        await roll_mons(ctx, "garden", 1)
        return
    else:
        rolled_item_list = await roll_items(1, filter_keyword="berry")
        garden_item = rolled_item_list[0] if rolled_item_list else "Unknown Berry"
        reward_embed = Embed(
            title="Garden Reward",
            description=f"🌱 You found **{garden_item}**!\nWhich character sheet should I add it to?\nEnter the **exact** sheet name or type `skip` to do nothing.",
            color=0x00FFFF
        )
        reward_embed.set_image(url=random.choice(GARDEN_TASK_ACCOMPLISHED_IMAGES))
        reward_embed.set_footer(text=random.choice(GARDEN_TASK_ACCOMPLISHED_FLAVOR_TEXTS))
        await ctx.followup.send(embed=reward_embed)
        def check_any(m):
            return m.author.id == ctx.user.id and m.channel.id == ctx.channel.id
        try:
            msg_sheet = await ctx.client.wait_for("message", check=check_any, timeout=60)
        except asyncio.TimeoutError:
            await ctx.followup.send("⏳ Timeout waiting for sheet name. Operation cancelled.")
            return
        if msg_sheet.content.lower() == "skip":
            await ctx.followup.send("Operation cancelled. Item remains unassigned.")
            return
        trainer_sheet = msg_sheet.content.strip()
        success = await update_character_sheet_item(trainer_sheet, garden_item, 1)
        if success:
            await ctx.followup.send(f"Added **{garden_item}** to {trainer_sheet}'s sheet!")
        else:
            await ctx.followup.send("Failed to update the character sheet with the garden item.")
