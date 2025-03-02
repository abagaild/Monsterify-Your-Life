import discord
import random
import asyncio
from discord.ext import commands
from core.items import process_reward  # Generalized reward logic

# Define available durations (in minutes) and associated start messages.
AVAILABLE_DURATIONS: dict[str, int] = {
    "10": 10,
    "30": 30,
    "60": 60,
    "120": 120
}

POMODORO_START_MESSAGES: dict[str, list[str]] = {
    "10": [
        "Quick sprint: Let's go!",
        "10-minute burst of productivity!",
        "Ready, set, focus for 10 minutes!"
    ],
    "30": [
        "30 minutes of focus begins now!",
        "Let's dive into a 30-minute work session!",
        "Settle in for 30 minutes of concentrated work!"
    ],
    "60": [
        "One hour of work time: Focus up!",
        "60 minutes of dedication ahead!",
        "Time to channel your energy for the next 60 minutes!"
    ],
    "120": [
        "Two hours of deep work: Let's do this!",
        "120 minutes to conquer your tasks!",
        "Prepare for a marathon session of productivity for 120 minutes!"
    ]
}

class GameCornerDurationView(discord.ui.View):
    """
    A view that presents selectable work session durations for the Pomodoro Game Corner.
    """
    def __init__(self, user: discord.User) -> None:
        super().__init__(timeout=None)
        self.user = user

    @discord.ui.button(label="10 minutes", style=discord.ButtonStyle.primary, custom_id="gamecorner_10", row=0)
    async def ten_minutes(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self.start_session(interaction, "10")

    @discord.ui.button(label="30 minutes", style=discord.ButtonStyle.primary, custom_id="gamecorner_30", row=0)
    async def thirty_minutes(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self.start_session(interaction, "30")

    @discord.ui.button(label="60 minutes", style=discord.ButtonStyle.primary, custom_id="gamecorner_60", row=0)
    async def sixty_minutes(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self.start_session(interaction, "60")

    @discord.ui.button(label="120 minutes", style=discord.ButtonStyle.primary, custom_id="gamecorner_120", row=0)
    async def one_twenty_minutes(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self.start_session(interaction, "120")

    async def start_session(self, interaction: discord.Interaction, duration_key: str) -> None:
        """
        Starts the session if the interaction is from the original user.
        Disables buttons to prevent re-clicking and sends a random start message.
        """
        if interaction.user != self.user:
            await interaction.response.send_message("This session isn’t for you.", ephemeral=True)
            return

        # Disable all buttons.
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(view=self)

        start_msgs = POMODORO_START_MESSAGES.get(duration_key, ["Focus time has started!"])
        start_msg = random.choice(start_msgs)
        await interaction.followup.send(f"Starting your {duration_key}-minute work session.\n{start_msg}", ephemeral=True)
        asyncio.create_task(self.run_session(interaction, int(duration_key)))

    async def run_session(self, interaction: discord.Interaction, duration_minutes: int) -> None:
        """
        Waits for the selected session duration (in minutes), then shows the feedback view.
        """
        await asyncio.sleep(duration_minutes * 60)
        feedback_view = GameCornerFeedbackView(interaction.user, duration_minutes)
        await interaction.followup.send("Your work session is over! How much of the time did you work?", view=feedback_view, ephemeral=True)

class GameCornerFeedbackView(discord.ui.View):
    """
    A view that collects feedback after the work session ends.
    """
    def __init__(self, user: discord.User, duration_minutes: int) -> None:
        super().__init__(timeout=120)
        self.user = user
        self.duration_minutes = duration_minutes

    @discord.ui.button(label="All", style=discord.ButtonStyle.success, custom_id="feedback_all")
    async def feedback_all(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self.process_feedback(interaction, "all")

    @discord.ui.button(label="Some", style=discord.ButtonStyle.primary, custom_id="feedback_some")
    async def feedback_some(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self.process_feedback(interaction, "some")

    @discord.ui.button(label="None", style=discord.ButtonStyle.danger, custom_id="feedback_none")
    async def feedback_none(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self.process_feedback(interaction, "none")

    async def process_feedback(self, interaction: discord.Interaction, feedback: str) -> None:
        """
        Processes the feedback by calling the reward logic and then prompts a restart option.
        """
        if interaction.user != self.user:
            await interaction.response.send_message("This isn’t your session.", ephemeral=True)
            return

        await process_reward(
            interaction,
            feedback,
            self.duration_minutes,
            item_roll_kwargs={"game_corner": True}
        )
        restart_view = GameCornerRestartView(self.user)
        await interaction.followup.send("Would you like to start another work session?", view=restart_view, ephemeral=True)

class GameCornerRestartView(discord.ui.View):
    """
    A view that allows the user to restart the Game Corner session or exit.
    """
    def __init__(self, user: discord.User) -> None:
        super().__init__(timeout=60)
        self.user = user

    @discord.ui.button(label="Restart", style=discord.ButtonStyle.success, custom_id="restart_yes")
    async def restart_yes(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if interaction.user != self.user:
            await interaction.response.send_message("This session isn’t for you.", ephemeral=True)
            return
        new_view = GameCornerDurationView(self.user)
        await interaction.response.send_message("Restarting the Pomodoro Game Corner!", view=new_view, ephemeral=True)

    @discord.ui.button(label="Exit", style=discord.ButtonStyle.danger, custom_id="restart_no")
    async def restart_no(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if interaction.user != self.user:
            await interaction.response.send_message("This session isn’t for you.", ephemeral=True)
            return
        await interaction.response.send_message("Thanks for playing the Pomodoro Game Corner! See you next time!", ephemeral=True)

def setup(bot: commands.Bot) -> None:
    @bot.command(name="gamecorner")
    async def game_corner_command(ctx: commands.Context) -> None:
        view = GameCornerDurationView(ctx.author)
        await ctx.send("Welcome to the Pomodoro Game Corner! Choose a work session duration:", view=view)
