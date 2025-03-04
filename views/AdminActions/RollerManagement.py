import discord
from discord.ui import View, Button, Modal, TextInput
import random

# Modal to test the item rolling function.
class TestItemRollModal(Modal, title="Test Item Roll"):
    amount = TextInput(
        label="Amount",
        placeholder="Enter number of items to roll",
        required=True
    )
    filter_keyword = TextInput(
        label="Filter Keyword",
        placeholder="Optional: Enter filter keywords (comma-separated)",
        required=False
    )
    game_corner = TextInput(
        label="Game Corner Mode",
        placeholder="Type YES for game corner mode, otherwise leave blank",
        required=False
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            amount_val = int(self.amount.value.strip())
        except ValueError:
            await interaction.response.send_message("Invalid amount.", ephemeral=True)
            return

        filter_keyword_val = self.filter_keyword.value.strip() or None
        game_corner_val = True if self.game_corner.value.strip().upper() == "YES" else False

        # Import and call the roll_items function from your items module.
        from core.items import roll_items
        rolled_items = await roll_items(amount=amount_val, filter_keyword=filter_keyword_val,
                                        game_corner=game_corner_val)

        if not rolled_items:
            message = "No items were rolled."
        else:
            message = "Rolled Items:\n" + "\n".join([f"{i + 1}. {item}" for i, item in enumerate(rolled_items)])
        await interaction.response.send_message(message, ephemeral=True)


# Modal to test the mon rolling function.
class TestMonRollModal(Modal, title="Test Mon Roll"):
    variant = TextInput(
        label="Variant",
        placeholder="Enter variant (e.g., default, egg, breeding, garden, etc.)",
        required=True
    )
    amount = TextInput(
        label="Amount",
        placeholder="Enter number of mons to roll (default 10)",
        required=False
    )
    claim_limit = TextInput(
        label="Claim Limit",
        placeholder="Enter claim limit (default 1)",
        required=False
    )

    async def on_submit(self, interaction: discord.Interaction):
        variant_val = self.variant.value.strip().lower()
        try:
            amount_val = int(self.amount.value.strip()) if self.amount.value.strip() else 10
        except ValueError:
            amount_val = 10
        try:
            claim_limit_val = int(self.claim_limit.value.strip()) if self.claim_limit.value.strip() else 1
        except ValueError:
            claim_limit_val = 1

        # Import and call the roll_mons function from your rollmons module.
        from core.rollmons import roll_mons
        # roll_mons sends its own embed with a claim view.
        await roll_mons(interaction, variant=variant_val, amount=amount_val, claim_limit=claim_limit_val)


class TestTaskCompletionModal(Modal, title="Test Task Completion Reward"):
    user_id = TextInput(label="User ID", placeholder="Enter user's Discord ID", required=True)
    task_name = TextInput(label="Task Name", placeholder="Enter the task name", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        uid = self.user_id.value.strip()
        task = self.task_name.value.strip()
        # Simulate reward: coin bonus between 10 and 50, and random item from a fixed list.
        coins = random.randint(10, 50)
        items = ["Pokeball", "Super Potion", "Rare Candy"]
        item_awarded = random.choice(items)
        message = f"Simulated Task Completion Reward for {uid} on task '{task}': {coins} coins and 1 {item_awarded}."
        await interaction.response.send_message(message, ephemeral=True)


# Modal to test schedule creation reward simulation.
class TestScheduleCreationModal(Modal, title="Test Schedule Creation Reward"):
    user_id = TextInput(label="User ID", placeholder="Enter user's Discord ID", required=True)
    task_count = TextInput(label="Task Count", placeholder="Enter task count (e.g., 5 or 10)", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        uid = self.user_id.value.strip()
        try:
            count = int(self.task_count.value.strip())
        except ValueError:
            await interaction.response.send_message("Invalid task count.", ephemeral=True)
            return
        # Simulate reward: Higher reward for 10 tasks than for 5.
        if count >= 10:
            coins = random.randint(50, 100)
        elif count >= 5:
            coins = random.randint(20, 40)
        else:
            coins = random.randint(5, 15)
        message = f"Simulated Schedule Creation Reward for {uid} with {count} tasks completed: {coins} coins awarded."
        await interaction.response.send_message(message, ephemeral=True)


# Modal to test game corner completion reward simulation.
class TestGameCornerModal(Modal, title="Test Game Corner Reward"):
    user_id = TextInput(label="User ID", placeholder="Enter user's Discord ID", required=True)
    duration = TextInput(label="Duration (minutes)", placeholder="Enter play duration in minutes", required=False)

    async def on_submit(self, interaction: discord.Interaction):
        uid = self.user_id.value.strip()
        try:
            duration_val = int(self.duration.value.strip()) if self.duration.value.strip() else 5
        except ValueError:
            duration_val = 5
        # Simulate reward: coins based on duration.
        coins = duration_val * random.randint(2, 5)
        message = f"Simulated Game Corner Reward for {uid}: {coins} coins awarded for {duration_val} minutes of play."
        await interaction.response.send_message(message, ephemeral=True)


# Modal to test garden completion reward simulation.
class TestGardenModal(Modal, title="Test Garden Completion Reward"):
    user_id = TextInput(label="User ID", placeholder="Enter user's Discord ID", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        uid = self.user_id.value.strip()
        # Simulate reward: random coins and chance for a rare seed.
        coins = random.randint(10, 30)
        rare_seed = random.choice([True, False])
        message = f"Simulated Garden Reward for {uid}: {coins} coins awarded."
        if rare_seed:
            message += " Additionally, a rare seed was found!"
        await interaction.response.send_message(message, ephemeral=True)

# Main Rollers Testing admin view.
class RollersTestingView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Test Item Roll", style=discord.ButtonStyle.primary, custom_id="test_item_roll", row=0)
    async def test_item_roll(self, interaction: discord.Interaction, button: Button):
        modal = TestItemRollModal()
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Test Mon Roll", style=discord.ButtonStyle.primary, custom_id="test_mon_roll", row=0)
    async def test_mon_roll(self, interaction: discord.Interaction, button: Button):
        modal = TestMonRollModal()
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Test Task Completion", style=discord.ButtonStyle.primary,
                       custom_id="test_task_completion", row=0)
    async def test_task_completion(self, interaction: discord.Interaction, button: Button):
        modal = TestTaskCompletionModal()
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Test Schedule Creation", style=discord.ButtonStyle.primary,
                       custom_id="test_schedule_creation", row=0)
    async def test_schedule_creation(self, interaction: discord.Interaction, button: Button):
        modal = TestScheduleCreationModal()
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Test Game Corner", style=discord.ButtonStyle.primary, custom_id="test_game_corner", row=1)
    async def test_game_corner(self, interaction: discord.Interaction, button: Button):
        modal = TestGameCornerModal()
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Test Garden Completion", style=discord.ButtonStyle.primary,
                       custom_id="test_garden_completion", row=1)
    async def test_garden_completion(self, interaction: discord.Interaction, button: Button):
        modal = TestGardenModal()
        await interaction.response.send_modal(modal)