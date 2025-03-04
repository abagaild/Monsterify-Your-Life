# views/view_habits.py
import discord
from discord.ui import View, Select, Button, Modal, TextInput
# Updated database function names for habits:
from core.database import fetch_habits, remove_habit, mark_habit_complete, add_habit
import random
from logic.boss import deal_boss_damage
from logic.mission import progress_mission
from core.core_views import CompletionRewardModal

class HabitSelect(Select):
    def __init__(self, options):
        super().__init__(placeholder="Select a habit", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"Selected habit: {self.values[0]}", ephemeral=True)

class HabitManagerView(View):
    def __init__(self, user: discord.User):
        super().__init__(timeout=180)
        self.user = user
        self.habit_select = HabitSelect(self.build_options())
        self.add_item(self.habit_select)

    def build_options(self):
        habits = fetch_habits(str(self.user.id))
        options = []
        for habit in habits:
            label = habit.get("name", "Unnamed")
            description = f"Time: {habit.get('time', 'N/A')}, Diff: {habit.get('difficulty', 'medium')}, Streak: {habit.get('streak', 0)}"
            options.append(discord.SelectOption(label=label, description=description, value=label))
        if not options:
            options = [discord.SelectOption(label="No habits", description="Add one using the button", value="none")]
        return options

    def refresh_items(self):
        self.habit_select.options = self.build_options()

    @discord.ui.button(label="Add Habit", style=discord.ButtonStyle.success, custom_id="add_habit", row=0)
    async def add_habit_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(AddHabitModal(self))

    @discord.ui.button(label="Delete Habit", style=discord.ButtonStyle.danger, custom_id="delete_habit", row=0)
    async def delete_habit_button(self, interaction: discord.Interaction, button: Button):
        selected = self.habit_select.values[0] if self.habit_select.values and self.habit_select.values[0] != "none" else None
        if not selected:
            await interaction.response.send_message("No habit selected to delete.", ephemeral=True)
            return
        remove_habit(str(interaction.user.id), selected)
        await interaction.response.send_message(f"Habit '{selected}' deleted.", ephemeral=True)
        self.refresh_items()
        await interaction.message.edit(view=self)

    @discord.ui.button(label="Complete Habit", style=discord.ButtonStyle.primary, custom_id="complete_habit", row=1)
    async def complete_habit_button(self, interaction: discord.Interaction, button: Button):
        user_id = str(interaction.user.id)
        await deal_boss_damage(user_id, random.randint(1, 3), channel=interaction.channel)
        progress_mission(user_id, random.randint(1, 3))
        selected = self.habit_select.values[0] if self.habit_select.values and self.habit_select.values[0] != "none" else None
        if not selected:
            await interaction.response.send_message("No habit selected to complete.", ephemeral=True)
            return
        new_streak = mark_habit_complete(user_id, selected)
        if new_streak is None:
            await interaction.response.send_message(f"Habit '{selected}' not found or already completed.", ephemeral=True)
        else:
            difficulty_str = "medium"
            habits = fetch_habits(user_id)
            for habit in habits:
                if habit["name"].lower() == selected.lower():
                    difficulty_str = habit.get("difficulty", "medium")
                    break
            difficulty_mapping = {"easy": 1, "medium": 2, "hard": 3}
            multiplier = difficulty_mapping.get(difficulty_str.lower(), 2)
            awarded_levels = multiplier * random.randint(1, 3)
            await interaction.response.send_modal(CompletionRewardModal(selected, awarded_levels))
            self.refresh_items()

class AddHabitModal(Modal, title="Add Habit"):
    habit_name = TextInput(label="Habit Name", placeholder="Enter habit name")
    habit_time = TextInput(label="Time (HH:MM or 'none')", placeholder="Optional", required=False)
    habit_difficulty = TextInput(label="Difficulty (easy, medium, hard)", placeholder="Default is medium", required=False)

    def __init__(self, parent_view: HabitManagerView):
        super().__init__()
        self.parent_view = parent_view

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        name = self.habit_name.value.strip()
        time_val = self.habit_time.value.strip() or None
        difficulty = self.habit_difficulty.value.strip() or "medium"
        add_habit(str(interaction.user.id), name, time_val, difficulty)
        updated_view = HabitManagerView(interaction.user)
        await interaction.followup.send(f"Habit '{name}' added.", view=updated_view, ephemeral=True)
