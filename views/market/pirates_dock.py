import discord
import random
import asyncio
import logic.market.pirates_dock as logic
from views.market.generic_shop import send_generic_shop_view
from data.fishing_prompts import PROMPTS as FISHING_PROMPTS
from data.deck_prompts import PROMPTS as DECK_PROMPTS
from core.mon import randomize_mon
from core.items import roll_items

class PiratesDockActivityView(discord.ui.View):
    def __init__(self, user_id: str):
        super().__init__(timeout=300)
        self.user_id = user_id

    @discord.ui.button(label="Go Fishing", style=discord.ButtonStyle.primary)
    async def go_fishing_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await go_fishing_activity(interaction, self.user_id)

    @discord.ui.button(label="Swab the Deck", style=discord.ButtonStyle.primary)
    async def swab_deck_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await swab_deck_activity(interaction, self.user_id)

class TimeSelectionModal(discord.ui.Modal, title="Select Activity Duration"):
    time_input = discord.ui.TextInput(
        label="Hours (1-4)",
        placeholder="Enter number of hours",
        required=True
    )
    def __init__(self, callback):
        super().__init__()
        self.callback_func = callback

    async def on_submit(self, interaction: discord.Interaction):
        try:
            hours = int(self.time_input.value)
            if hours < 1 or hours > 4:
                raise ValueError()
        except ValueError:
            await interaction.response.send_message("Invalid input. Please enter a number between 1 and 4.", ephemeral=True)
            return
        interaction.data = {"hours": hours}
        await self.callback_func(interaction, hours)

class EffortSelectionModal(discord.ui.Modal, title="Select Effort Value"):
    effort_input = discord.ui.TextInput(
        label="Effort (1-3)",
        placeholder="Enter effort value",
        required=True
    )
    def __init__(self, callback):
        super().__init__()
        self.callback_func = callback

    async def on_submit(self, interaction: discord.Interaction):
        try:
            effort = int(self.effort_input.value)
            if effort < 1 or effort > 3:
                raise ValueError()
        except ValueError:
            await interaction.response.send_message("Invalid input. Please enter a number between 1 and 3.", ephemeral=True)
            return
        await self.callback_func(interaction, effort)

class TrainerSelectionModal(discord.ui.Modal, title="Select Trainer"):
    trainer_input = discord.ui.TextInput(
        label="Trainer Name",
        placeholder="Enter trainer's name",
        required=True
    )
    def __init__(self, callback):
        super().__init__()
        self.callback_func = callback

    async def on_submit(self, interaction: discord.Interaction):
        trainer = self.trainer_input.value.strip()
        if not trainer:
            await interaction.response.send_message("Trainer name cannot be empty.", ephemeral=True)
            return
        await self.callback_func(interaction, trainer)

async def go_fishing_activity(interaction: discord.Interaction, user_id: str):
    async def time_callback(inter, hours):
        prompt = random.choice(FISHING_PROMPTS)
        await inter.response.send_message(
            f"Your art prompt: **{prompt}**. Spend {hours} hour(s) creating your artwork.",
            ephemeral=True
        )
        await asyncio.sleep(1)
        modal = EffortSelectionModal(effort_callback)
        await inter.followup.send("Activity complete! Now, select an effort value (1-3).", ephemeral=True)
        await inter.response.send_modal(modal)

    async def effort_callback(inter, effort):
        rolled_mon = randomize_mon({"name": "Fishing Mon", "types": ["Water", "Ice"]}, force_min_types=1)
        rolled_mon["level"] = effort
        modal = TrainerSelectionModal(trainer_callback)
        inter.data = {"rolled_mon": rolled_mon}
        await inter.followup.send(
            f"Rolled mon: **{rolled_mon['name']}** (Level {rolled_mon['level']}, Types: {', '.join(rolled_mon['types'])}). "
            "Enter the trainer name to assign this mon.",
            ephemeral=True
        )
        await inter.response.send_modal(modal)

    async def trainer_callback(inter, trainer):
        rolled_mon = inter.data.get("rolled_mon")
        await inter.followup.send(
            f"Assigned mon **{rolled_mon['name']}** (Level {rolled_mon['level']}) to trainer **{trainer}**.",
            ephemeral=True
        )
        await inter.followup.send("Do you want to go fishing again? (Reply YES to continue)", ephemeral=True)

    modal = TimeSelectionModal(time_callback)
    await interaction.response.send_modal(modal)

async def swab_deck_activity(interaction: discord.Interaction, user_id: str):
    async def time_callback(inter, hours):
        prompt = random.choice(DECK_PROMPTS)
        await inter.response.send_message(
            f"Your deck prompt: **{prompt}**. Spend {hours} hour(s) swabbing the deck.",
            ephemeral=True
        )
        await asyncio.sleep(1)
        modal = EffortSelectionModal(effort_callback)
        inter.data = {"hours": hours}
        await inter.followup.send("Activity complete! Now, select an effort value (1-3).", ephemeral=True)
        await inter.response.send_modal(modal)

    async def effort_callback(inter, effort):
        hours = inter.data.get("hours", 1)
        reward_count = round(effort * hours * 1.3)
        items_reward = await roll_items(amount=reward_count)
        await inter.followup.send(
            f"You earned the following items: {', '.join(items_reward)}",
            ephemeral=True
        )
        await inter.followup.send("Do you want to swab the deck again? (Reply YES to continue)", ephemeral=True)

    modal = TimeSelectionModal(time_callback)
    await interaction.response.send_modal(modal)

class PiratesDockShopView(discord.ui.View):
    def __init__(self, user_id: str):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.image = random.choice(logic.IMAGES)
        self.message = "Welcome to Pirate's Dock! Shop here for random items at a massive markup."

    @discord.ui.button(label="Shop", style=discord.ButtonStyle.primary, custom_id="pirates_dock_shop")
    async def shop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await send_generic_shop_view(interaction, "pirate", self.user_id)

    @discord.ui.button(label="Activity", style=discord.ButtonStyle.secondary, custom_id="pirates_dock_activity")
    async def activity_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = PiratesDockActivityView(self.user_id)
        await interaction.response.send_message("Choose an activity:", view=view, ephemeral=True)

async def send_pirates_dock_view(interaction: discord.Interaction, user_id: str):
    view = PiratesDockShopView(user_id)
    embed = discord.Embed(title="Pirate's Dock", description=view.message, color=discord.Color.gold())
    embed.set_image(url=view.image)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
