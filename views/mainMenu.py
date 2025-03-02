import discord
from discord.ui import View, Button
from core.config import (
    market_channel_id, garden_channel_id, schedule_channel_id,
    submissions_channel_id, mission_channel_id, ADVENTURE_CHANNEL_ID,
    game_corner_channel_id, boss_channel_id, admin_actions_channel_id
)
from core.database import get_trainers_from_db
from core.trainer import get_other_trainers_from_db
from logic.trade_items import TradeTrainerSelectionView
from logic.trade_pokemon import TradePokemonSelectionView
from views.trainers import PaginatedTrainersView

# Mapping button custom_ids to target channel IDs.
TARGET_CHANNELS = {
    "menu_market": market_channel_id,
    "menu_garden": garden_channel_id,
    "menu_schedule": schedule_channel_id,
    "menu_submissions": submissions_channel_id,
    "menu_mission": mission_channel_id,
    "adventure_menu": ADVENTURE_CHANNEL_ID,
    "menu_game_corner": game_corner_channel_id,
    "menu_boss_battle": boss_channel_id,
    "menu_admin_actions": admin_actions_channel_id,
}

# Helper function to get a target channel (same as before)
def get_target_channel(interaction: discord.Interaction, custom_id: str, extra_mapping: dict = None):
    mapping = TARGET_CHANNELS.copy()
    if extra_mapping:
        mapping.update(extra_mapping)
    if interaction.guild is None:
        return interaction.channel
    target_id = mapping.get(custom_id)
    channel = interaction.client.get_channel(target_id) if target_id else None
    return channel if channel else interaction.channel

# --- Main Menu View ---
class MainMenuView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.main_embed = discord.Embed(
            title="Adventure Awaits!",
            description="Welcome to the game. Choose an option below to begin your journey.",
            color=discord.Color.green()
        )
        self.main_embed.set_image(url="https://i.imgur.com/eZupnoL.jpg")
        self.main_embed.set_footer(text="Embrace the challenge. Your destiny is just a click away!")

    # Row 0: Schedule & Submissions
    @discord.ui.button(label="📆 Schedule", style=discord.ButtonStyle.secondary, custom_id="menu_schedule", row=0)
    async def schedule(self, interaction: discord.Interaction, button: discord.ui.Button):
        from views.schedule import ScheduleMenuView  # updated import if needed
        channel = get_target_channel(interaction, button.custom_id)
        embed = discord.Embed(title="Schedule UI", color=discord.Color.green())
        await channel.send(embed=embed, view=ScheduleMenuView())

    @discord.ui.button(label="📒 Submissions", style=discord.ButtonStyle.secondary, custom_id="menu_submissions", row=0)
    async def submissions(self, interaction: discord.Interaction, button: discord.ui.Button):
        from views.submissions import SubmissionTypeView  # adjust path if necessary
        view = SubmissionTypeView(str(interaction.user.id))
        channel = get_target_channel(interaction, button.custom_id)
        embed = discord.Embed(title="Submissions", color=discord.Color.green())
        await channel.send(embed=embed, view=view)

    # Row 1: Visit Town & Character
    @discord.ui.button(label="🏘 Visit Town", style=discord.ButtonStyle.primary, custom_id="menu_visit_town", row=1)
    async def visit_town(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Send the nested Visit Town view
        channel = interaction.channel  # or use get_target_channel with extra mapping if needed
        embed = discord.Embed(title="Visit Town", description="Select a location to visit:", color=discord.Color.blue())
        await channel.send(embed=embed, view=TownMenuView())

    @discord.ui.button(label="👤 Character", style=discord.ButtonStyle.primary, custom_id="menu_character", row=1)
    async def character(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Send the nested Character view
        channel = interaction.channel
        embed = discord.Embed(title="Character Options", description="Choose an option:", color=discord.Color.blue())
        await channel.send(embed=embed, view=CharacterMenuView())

    # Row 2: Admin Actions & Boss
    @discord.ui.button(label="Admin Actions", style=discord.ButtonStyle.secondary, custom_id="menu_admin_actions", row=2)
    async def admin_actions(self, interaction: discord.Interaction, button: discord.ui.Button):
        from views.AdminActions.Overall import AdminActionsView  # updated path if needed
        view = AdminActionsView()
        channel = get_target_channel(interaction, button.custom_id)
        embed = discord.Embed(title="Admin Actions", color=discord.Color.purple())
        await channel.send(embed=embed, view=view)

    @discord.ui.button(label="⚔️ Boss", style=discord.ButtonStyle.danger, custom_id="menu_boss", row=2)
    async def boss(self, interaction: discord.Interaction, button: discord.ui.Button):
        from views.boss import BossUIView  # updated path if needed
        view = BossUIView(str(interaction.user.id))
        channel = get_target_channel(interaction, button.custom_id)
        embed = discord.Embed(title="Boss Battle", color=discord.Color.red())
        await channel.send(embed=embed, view=view)

# --- Nested View for Visit Town ---
class TownMenuView(View):
    def __init__(self):
        super().__init__(timeout=None)


    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return True

    # Each button callback sends the appropriate view/message.
    @discord.ui.button(label="Apothecary", style=discord.ButtonStyle.secondary, custom_id="town_apothecary", row=0)
    async def apothecary(self, interaction: discord.Interaction, button: discord.ui.Button):
        from views.market.apothecary import send_apothocary_overall_view  # adjust import path and function name
        channel = interaction.channel
        await send_apothocary_overall_view(interaction, str(interaction.user.id))

    @discord.ui.button(label="Bakery", style=discord.ButtonStyle.secondary, custom_id="town_bakery", row=0)
    async def bakery(self, interaction: discord.Interaction, button: discord.ui.Button):
        from views.market.bakery import send_bakery_view
        channel = interaction.channel
        await send_bakery_view(interaction, str(interaction.user.id))

    @discord.ui.button(label="Witch's Hut", style=discord.ButtonStyle.secondary, custom_id="town_witch", row=0)
    async def witch_hut(self, interaction: discord.Interaction, button: discord.ui.Button):
        from views.market.witchs_hut import send_witchs_hut_view
        channel = interaction.channel
        await send_witchs_hut_view(interaction, str(interaction.user.id))

    @discord.ui.button(label="Antique Store", style=discord.ButtonStyle.secondary, custom_id="town_antique", row=0)
    async def antique_store(self, interaction: discord.Interaction, button: discord.ui.Button):
        from views.market import send_antique_store_view
        channel = interaction.channel
        await send_antique_store_view(interaction, str(interaction.user.id), target_channel=channel)

    @discord.ui.button(label="Adoption Center", style=discord.ButtonStyle.secondary, custom_id="town_adoption", row=1)
    async def adoption_center(self, interaction: discord.Interaction, button: discord.ui.Button):
        from views.market.adoption_center import start_adoption_activity
        channel = interaction.channel
        await start_adoption_activity(interaction, str(interaction.user.id), str(interaction.user.id))

    @discord.ui.button(label="Pirate's Dock", style=discord.ButtonStyle.secondary, custom_id="town_pirate", row=1)
    async def pirate_dock(self, interaction: discord.Interaction, button: discord.ui.Button):
        from views.market.pirates_dock import send_pirates_dock_view
        channel = interaction.channel
        await send_pirates_dock_view(interaction, str(interaction.user.id))

    @discord.ui.button(label="Megamart", style=discord.ButtonStyle.secondary, custom_id="town_megamart", row=1)
    async def megamart(self, interaction: discord.Interaction, button: discord.ui.Button):
        from views.market.megamart import send_megamart_view
        channel = interaction.channel
        await send_megamart_view(interaction, str(interaction.user.id))

    @discord.ui.button(label="Adventure", style=discord.ButtonStyle.success, custom_id="town_adventure", row=2)
    async def adventure(self, interaction: discord.Interaction, button: discord.ui.Button):
        from views.adventure import AdventureView
        embed = discord.Embed(title="Adventure Awaits!", description="Choose your adventure!", color=discord.Color.blue())
        embed.set_image(url="https://i.imgur.com/R48BhNs.png")
        channel = interaction.channel
        await channel.send(embed=embed, view=AdventureView(user_id=str(interaction.user.id)))

    @discord.ui.button(label="Mission", style=discord.ButtonStyle.success, custom_id="town_mission", row=2)
    async def mission(self, interaction: discord.Interaction, button: discord.ui.Button):
        from views.mission import MissionSelectView
        view = MissionSelectView(str(interaction.user.id))
        channel = interaction.channel
        embed = view.get_embed()
        await channel.send(embed=embed, view=view)

    @discord.ui.button(label="Game Corner", style=discord.ButtonStyle.success, custom_id="town_game_corner", row=2)
    async def game_corner(self, interaction: discord.Interaction, button: discord.ui.Button):
        from views.gamecorner import GameCornerDurationView
        view = GameCornerDurationView(interaction.user)
        channel = interaction.channel
        embed = discord.Embed(title="Game Corner", description="Welcome to the Pomodoro Game Corner!", color=discord.Color.green())
        await channel.send(embed=embed, view=view)

    @discord.ui.button(label="Garden", style=discord.ButtonStyle.secondary, custom_id="town_garden", row=3)
    async def garden(self, interaction: discord.Interaction, button: discord.ui.Button):
        from views.garden import GardenView
        view = GardenView(str(interaction.user.id))
        channel = interaction.channel
        embed = discord.Embed(title="Garden", color=discord.Color.green())
        await channel.send(embed=embed, view=view)

    @discord.ui.button(label="Farm", style=discord.ButtonStyle.secondary, custom_id="town_farm", row=3)
    async def farm(self, interaction: discord.Interaction, button: discord.ui.Button):
        from views.market.farm import send_farm_view
        await send_farm_view(interaction, str(interaction.user.id))


    @discord.ui.button(label="Nursery", style=discord.ButtonStyle.secondary, custom_id="town_nursery", row=3)
    async def nursery(self, interaction: discord.Interaction, button: discord.ui.Button):
        from views.market.nursery import send_nursery_view
        await send_nursery_view(interaction,str(interaction.user.id))

    @discord.ui.button(label="Poffin Crafting", style=discord.ButtonStyle.secondary, custom_id="town_poffin", row=3)
    async def poffin(self, interaction: discord.Interaction, button: discord.ui.Button):
        from views.town import send_poffin_view
        channel = interaction.channel
        await send_poffin_view(interaction, str(interaction.user.id), target_channel=channel)


# --- Nested View for Character Options ---
class CharacterMenuView(View):
    def __init__(self):
        super().__init__(timeout=120)

    @discord.ui.button(label="View My Characters", style=discord.ButtonStyle.primary, custom_id="char_view_my", row=0)
    async def view_my_characters(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = str(interaction.user.id)
        trainers = get_trainers_from_db(str(user_id))
        view = PaginatedTrainersView(trainers, editable=True, user_id=str(user_id))
        await interaction.response.send_message(embed=view.get_current_embed(), view=view, ephemeral=True)

    @discord.ui.button(label="View Other Characters", style=discord.ButtonStyle.primary, custom_id="char_view_other", row=0)
    async def view_other_characters(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = str(interaction.user.id)
        # Assume this function returns trainers whose user_id is NOT equal to the given user_id.
        other_trainers = get_other_trainers_from_db(user_id)
        view = PaginatedTrainersView(other_trainers, editable=False, user_id=user_id)
        await interaction.response.send_message(embed=view.get_current_embed(), view=view, ephemeral=True)

    @discord.ui.button(label="Trade Items", style=discord.ButtonStyle.secondary, custom_id="char_trade_items", row=1)
    async def trade_items(self, interaction: discord.Interaction, button: discord.ui.Button):
        player_id = str(interaction.user.id)
        view = TradeTrainerSelectionView(player_id)
        await interaction.response.send_message("Select your trainer and an opponent for trading:", view=view,
                                                ephemeral=True)

    @discord.ui.button(label="Trade Pokemon", style=discord.ButtonStyle.secondary, custom_id="char_trade_pokemon", row=1)
    async def trade_pokemon(self, interaction: discord.Interaction, button: discord.ui.Button):
        player_id = str(interaction.user.id)
        view = TradePokemonSelectionView(player_id)
        await interaction.response.send_message("Select trainers for the Pokémon trade:", view=view, ephemeral=True)
