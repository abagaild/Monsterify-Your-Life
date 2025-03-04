import discord
from discord.ext import commands
#from logic.adventure import active_adventure_sessions
from core import config
import logging

# Import all views

from views.mainMenu import MainMenuView, TownMenuView
from views.garden import GardenView
from views.schedule import ScheduleMenuView
from views.submissions import SubmissionTypeView
from views.mission import MissionSelectView
from views.adventure import AdventureView
from views.gamecorner import GameCornerDurationView
from views.boss import BossUIView
from views.AdminActions.Overall import AdminActionsView

# Set up logging
logging.basicConfig(level=logging.INFO)

# Set up Discord intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

class MyBot(commands.Bot):
    async def on_ready(self):
        logging.info(f"Logged in as {self.user.name}")
        try:
            await self.tree.sync()
        except Exception as e:
            logging.error(f"Error syncing command tree: {e}")
        logging.info("Bot is ready!")

        # Create persistent view instances and add them to the bot.
        views = [
            MainMenuView(),
            GardenView(""),
            TownMenuView(),
            ScheduleMenuView(),
            SubmissionTypeView(""),
            MissionSelectView(""),
            AdventureView(""),
            GameCornerDurationView(""),
            BossUIView(""),
            AdminActionsView()
        ]
        for view in views:
            self.add_view(view)

    async def on_message(self, message: discord.Message):
        # Ignore messages from bots.
        if message.author.bot:
            return

        # Process messages in the designated adventure channel.
        if message.channel.id == config.ADVENTURE_CHANNEL_ID:
            logging.info(f"Adventure Channel Message from {message.author}: {message.content}")
            session = active_adventure_sessions.get(message.channel.id)
            if session:
                await session.handle_message(message)
            else:
                logging.info("No active adventure session for this channel.")
        await self.process_commands(message)

# Create bot instance
bot = MyBot(command_prefix="!", intents=intents)

from views.mainMenu import MainMenuView

@bot.command(name="menu")
async def menu_command(ctx):
    """Displays the main menu UI."""
    view = MainMenuView()
    await ctx.send(embed=view.main_embed, view=view)

@bot.tree.command(name="menu", description="Display the main menu")
async def slash_menu(interaction: discord.Interaction):
    """Displays the main menu UI via slash command."""
    view = MainMenuView()
    await interaction.response.send_message(embed=view.main_embed, view=view, ephemeral=True)

bot.run(config.TOKEN)
