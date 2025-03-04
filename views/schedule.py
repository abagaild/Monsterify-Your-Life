# views/view_schedule.py
import discord
from discord.ui import View, Button

from core.mon import register_mon
from views.habits import HabitManagerView
from views.tasks import TaskManagerView
from discord.ui import Modal, TextInput
import random
from logic.schedule import build_schedule_message

class ScheduleMenuView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="View Schedule", style=discord.ButtonStyle.primary, custom_id="view_schedule", row=0)
    async def view_schedule_button(self, interaction: discord.Interaction, button: Button):
        schedule_text = build_schedule_message(str(interaction.user.id))
        embed = discord.Embed(title="Your Schedule", description=schedule_text, color=discord.Color.blue())
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Manage Habits", style=discord.ButtonStyle.secondary, custom_id="manage_habits", row=1)
    async def manage_habits_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message("Opening Habit Manager...", view=HabitManagerView(interaction.user), ephemeral=True)

    @discord.ui.button(label="Manage Tasks", style=discord.ButtonStyle.secondary, custom_id="manage_tasks", row=1)
    async def manage_tasks_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message("Opening Task Manager...", view=TaskManagerView(interaction.user), ephemeral=True)

    @discord.ui.button(label="Create Schedule", style=discord.ButtonStyle.success, custom_id="create_schedule", row=2)
    async def create_schedule_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(CreateScheduleModal())

class CreateScheduleModal(Modal, title="Create Daily Schedule"):
    tasks_input = TextInput(
        label="Enter Tasks (one per line)",
        placeholder="Example:\nTask 1, 08:00, easy\nTask 2, 08:30, medium\n...",
        style=discord.TextStyle.paragraph,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        user_id = str(interaction.user.id)
        raw_text = self.tasks_input.value.strip()
        if not raw_text:
            await interaction.followup.send("No tasks provided.", ephemeral=True)
            return

        lines = raw_text.splitlines()
        task_count = 0
        rolled_items = []
        starter_mon = None

        for line in lines:
            parts = [p.strip() for p in line.split(",")]
            if not parts or not parts[0]:
                continue
            task_name = parts[0]
            time_val = parts[1] if len(parts) > 1 and parts[1].lower() != "none" else None
            difficulty = parts[2] if len(parts) > 2 else "medium"
            carryover = False
            from logic.tasks import add_task
            add_task(user_id, task_name, time_val, carryover, difficulty)
            task_count += 1
            if task_count % 5 == 0:
                from core.items import roll_items
                rolled = await roll_items(1)
                if rolled:
                    rolled_items.append(rolled[0])
            if task_count % 10 == 0:
                from core.rollmons import roll_mons
                starter_mon = roll_mons(interaction, "starter", 1)
        schedule_text = build_schedule_message(user_id)
        from data.messages import random_inspiration, random_inspiration_image
        insp_msg = random.choice(random_inspiration)
        insp_img = random.choice(random_inspiration_image)
        summary = f"**Your Daily Schedule:**\n{schedule_text}\n\n"
        if rolled_items:
            summary += f"Item rewards earned: {', '.join(rolled_items)}\n"
        if starter_mon:
            summary += "A starter mon reward was rolled!\n"
        summary += f"\n*Inspiration: {insp_msg}*"
        embed = discord.Embed(description=summary, color=discord.Color.blurple())
        embed.set_image(url=insp_img)
        if starter_mon or rolled_items:
            view = RewardAssignmentButtonView(starter_mon, rolled_items)
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
        else:
            await interaction.followup.send(embed=embed, ephemeral=True)

class RewardAssignmentButtonView(discord.ui.View):
    def __init__(self, starter_mon: dict = None, rolled_items: list = None):
        super().__init__(timeout=60)
        if starter_mon:
            self.add_item(AssignStarterButton(starter_mon))
        if rolled_items:
            self.add_item(AssignItemsButton(rolled_items))

from discord.ui import Button
from core.core_views import AssignRolledItemsModal

class AssignStarterButton(Button):
    def __init__(self, rolled_mon: dict):
        super().__init__(label="Assign Mon", style=discord.ButtonStyle.primary)
        self.rolled_mon = rolled_mon

    async def callback(self, interaction: discord.Interaction):
        await register_mon(interaction, self.rolled_mon)

class AssignItemsButton(Button):
    def __init__(self, rolled_items: list):
        super().__init__(label="Assign Rolled Items", style=discord.ButtonStyle.primary)
        self.rolled_items = rolled_items

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(AssignRolledItemsModal(self.rolled_items))
