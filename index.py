import discord
from discord.ext import commands

from Google_Sheets.AdminActionsSync import AdminUpdateView
#from OLD.logic.adventure import active_adventure_sessions
#from logic.adventure import active_adventure_sessions
from core import config
import logging
from discord.ext import commands

from core.core_AdminActions import AdminDatabaseView
from core.database import fetch_trainer_by_name
from logic.adventure import active_adventure_sessions

# Import all views

from mainMenu import TownMenuView
from views.garden import GardenView
from views.schedule import ScheduleMenuView
from views.submissions import SubmissionTypeView
from views.missions import MissionSelectView
from views.adventure import AdventureView
from views.gamecorner import GameCornerDurationView
from views.boss import BossUIView
from core.database import fetch_trainer_by_name

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

from mainMenu import MainMenuView

@bot.command(name="menu")
async def menu_command(ctx):
    """Displays the main menu UI."""
    view = MainMenuView()
    await ctx.send(embed=view.main_embed, view=view)

@bot.command(name="admin_update")
async def admin_update(ctx, *, trainer_name: str):
    view = AdminUpdateView(fetch_trainer_by_name(trainer_name))
    await ctx.send(f"Manual update actions for trainer '{trainer_name}':", view=view)

@bot.command(name="admin_database")
async def admin_database(ctx):
        """
        Admin command to test database functions.
        Shows buttons for rolling mons, adding trainers/mon, and updating currency/inventory.
        """
        view = AdminDatabaseView()
        await ctx.send("Admin Database Test Panel:", view=view, ephemeral=True)

@bot.tree.command(name="menu", description="Display the main menu")
async def slash_menu(interaction: discord.Interaction):
    """Displays the main menu UI via slash command."""
    view = MainMenuView()
    await interaction.response.send_message(embed=view.main_embed, view=view, ephemeral=True)


bot.run(config.TOKEN)
