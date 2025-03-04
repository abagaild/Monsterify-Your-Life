# views/view_tasks.py
import discord
from discord.ui import View, Select, Button, Modal, TextInput
# Updated database function names for tasks:
from core.database import fetch_tasks, remove_task, mark_task_complete
from logic.tasks import add_task
import random
from logic.boss import deal_boss_damage
from logic.mission import progress_mission
from core.core_views import CompletionRewardModal

class TaskSelect(Select):
    def __init__(self, options):
        super().__init__(placeholder="Select a task", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"Selected task: {self.values[0]}", ephemeral=True)

class TaskManagerView(View):
    def __init__(self, user: discord.User):
        super().__init__(timeout=180)
        self.user = user
        self.task_select = TaskSelect(self.build_options())
        self.add_item(self.task_select)

    def build_options(self):
        tasks = fetch_tasks(str(self.user.id))
        options = []
        for task in tasks:
            label = task.get("name", "Unnamed")
            carry = "Yes" if task.get("carryover") else "No"
            description = f"Time: {task.get('time', 'N/A')}, Diff: {task.get('difficulty','medium')}, Carryover: {carry}"
            options.append(discord.SelectOption(label=label, description=description, value=label))
        if not options:
            options = [discord.SelectOption(label="No tasks", description="Add one using the button", value="none")]
        return options

    def refresh_items(self):
        self.task_select.options = self.build_options()

    @discord.ui.button(label="Add Task", style=discord.ButtonStyle.success, custom_id="add_task", row=0)
    async def add_task_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(AddTaskModal(self))

    @discord.ui.button(label="Delete Task", style=discord.ButtonStyle.danger, custom_id="delete_task", row=0)
    async def delete_task_button(self, interaction: discord.Interaction, button: Button):
        selected = self.task_select.values[0] if self.task_select.values and self.task_select.values[0] != "none" else None
        if not selected:
            await interaction.response.send_message("No task selected to delete.", ephemeral=True)
            return
        remove_task(str(interaction.user.id), selected)
        await interaction.response.send_message(f"Task '{selected}' deleted.", ephemeral=True)
        self.refresh_items()
        await interaction.message.edit(view=self)

    @discord.ui.button(label="Complete Task", style=discord.ButtonStyle.primary, custom_id="complete_task", row=1)
    async def complete_task_button(self, interaction: discord.Interaction, button: Button):
        user_id = str(interaction.user.id)
        await deal_boss_damage(user_id, random.randint(1,3), channel=interaction.channel)
        progress_mission(user_id, random.randint(1,3))
        selected = self.task_select.values[0] if self.task_select.values and self.task_select.values[0] != "none" else None
        if not selected:
            await interaction.response.send_message("No task selected to complete.", ephemeral=True)
            return
        if mark_task_complete(user_id, selected):
            tasks = fetch_tasks(user_id)
            difficulty_str = "medium"
            for task in tasks:
                if task["name"].lower() == selected.lower():
                    difficulty_str = task.get("difficulty", "medium")
                    break
            difficulty_mapping = {"easy": 1, "medium": 2, "hard": 3}
            multiplier = difficulty_mapping.get(difficulty_str.lower(), 2)
            awarded_levels = multiplier * random.randint(1, 3)
            await interaction.response.send_modal(CompletionRewardModal(selected, awarded_levels))
            self.refresh_items()
        else:
            await interaction.response.send_message(f"Task '{selected}' not found or already completed.", ephemeral=True)

class AddTaskModal(Modal, title="Add Task"):
    task_name = TextInput(label="Task Name", placeholder="Enter task name")
    task_time = TextInput(label="Time (HH:MM or 'none')", placeholder="Optional", required=False)
    task_carryover = TextInput(label="Carryover? (yes/no)", placeholder="yes or no", required=False)
    task_difficulty = TextInput(label="Difficulty (easy, medium, hard)", placeholder="Default is medium", required=False)

    def __init__(self, parent_view: TaskManagerView):
        super().__init__()
        self.parent_view = parent_view

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        name = self.task_name.value.strip()
        time_val = self.task_time.value.strip() or None
        carryover = self.task_carryover.value.strip().lower() == "yes" if self.task_carryover.value else False
        difficulty = self.task_difficulty.value.strip() or "medium"
        add_task(str(interaction.user.id), name, time_val, carryover, difficulty)
        updated_view = TaskManagerView(interaction.user)
        await interaction.followup.send(f"Task '{name}' added.", view=updated_view, ephemeral=True)
