import discord
from discord.ui import View, Button

import core.trainer
import views.trainer
from core.config import (
    market_channel_id, garden_channel_id, schedule_channel_id,
    submissions_channel_id, mission_channel_id, ADVENTURE_CHANNEL_ID,
    game_corner_channel_id, boss_channel_id, admin_actions_channel_id
)
from logic.trade_pokemon import TradePokemonSelectionView
from views.add_mon import send_trainer_select_for_mon
from views.add_trainer import AddTrainerEmbedView

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

def get_target_channel(interaction: discord.Interaction, custom_id: str, extra_mapping: dict = None):
    mapping = TARGET_CHANNELS.copy()
    if extra_mapping:
        mapping.update(extra_mapping)
    if interaction.guild is None:
        return interaction.channel
    target_id = mapping.get(custom_id)
    channel = interaction.client.get_channel(target_id) if target_id else None
    return channel if channel else interaction.channel

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

    @discord.ui.button(label="📆 Schedule", style=discord.ButtonStyle.secondary, custom_id="menu_schedule", row=0)
    async def schedule(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Defer immediately
        await interaction.response.defer()
        from views.schedule import ScheduleMenuView
        channel = get_target_channel(interaction, button.custom_id)
        embed = discord.Embed(title="Schedule UI", color=discord.Color.green())
        await channel.send(embed=embed, view=ScheduleMenuView())

    @discord.ui.button(label="📒 Submissions", style=discord.ButtonStyle.secondary, custom_id="menu_submissions", row=0)
    async def submissions(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        from views.submissions import SubmissionTypeView
        view = SubmissionTypeView(str(interaction.user.id))
        channel = get_target_channel(interaction, button.custom_id)
        embed = discord.Embed(title="Submissions", color=discord.Color.green())
        await channel.send(embed=embed, view=view)

    @discord.ui.button(label="🌇 Visit Town", style=discord.ButtonStyle.primary, custom_id="menu_visit_town", row=1)
    async def visit_town(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        channel = interaction.channel
        embed = discord.Embed(title="Visit Town", description="Select a location to visit:", color=discord.Color.blue())
        # Using followup here so the response appears in the same channel.
        await interaction.followup.send(embed=embed, view=TownMenuView())

    @discord.ui.button(label="👤 Character", style=discord.ButtonStyle.primary, custom_id="menu_character", row=1)
    async def character(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        channel = interaction.channel
        embed = discord.Embed(title="Character Options", description="Choose an option:", color=discord.Color.blue())
        await interaction.followup.send(embed=embed, view=CharacterMenuView())

    @discord.ui.button(label="Admin Actions", style=discord.ButtonStyle.secondary, custom_id="menu_admin_actions", row=2)
    async def admin_actions(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        from views.AdminActions.Overall import AdminActionsView
        view = AdminActionsView()
        channel = get_target_channel(interaction, button.custom_id)
        embed = discord.Embed(title="Admin Actions", color=discord.Color.purple())
        await channel.send(embed=embed, view=view)

    @discord.ui.button(label="⚔️ Boss", style=discord.ButtonStyle.danger, custom_id="menu_boss", row=2)
    async def boss(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        from views.boss import BossUIView
        view = BossUIView(str(interaction.user.id))
        channel = get_target_channel(interaction, button.custom_id)
        embed = discord.Embed(title="Boss Battle", color=discord.Color.red())
        await channel.send(embed=embed, view=view)

class TownMenuView(View):
    def __init__(self):
        super().__init__(timeout=None)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return True

    @discord.ui.button(label="Apothecary", style=discord.ButtonStyle.secondary, custom_id="town_apothecary", row=0)
    async def apothecary(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        from views.market.apothecary import send_apothocary_overall_view
        await send_apothocary_overall_view(interaction, str(interaction.user.id))

    @discord.ui.button(label="Bakery", style=discord.ButtonStyle.secondary, custom_id="town_bakery", row=0)
    async def bakery(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        from views.market.bakery import send_bakery_view
        await send_bakery_view(interaction, str(interaction.user.id))

    @discord.ui.button(label="Witch's Hut", style=discord.ButtonStyle.secondary, custom_id="town_witch", row=0)
    async def witch_hut(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        from views.market.witchs_hut import send_witchs_hut_view
        await send_witchs_hut_view(interaction, str(interaction.user.id))

    @discord.ui.button(label="Antique Store", style=discord.ButtonStyle.secondary, custom_id="town_antique", row=0)
    async def antique_store(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        from views.market.antiques import send_antique_overall_view
        await send_antique_overall_view(interaction, str(interaction.user.id))

    @discord.ui.button(label="Adoption Center", style=discord.ButtonStyle.secondary, custom_id="town_adoption", row=1)
    async def adoption_center(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        from views.market.adoption_center import send_adoption_center_view
        await send_adoption_center_view(interaction, str(interaction.user.id), target_channel=interaction.channel)

    @discord.ui.button(label="Pirate's Dock", style=discord.ButtonStyle.secondary, custom_id="town_pirate", row=1)
    async def pirate_dock(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        from views.market.pirates_dock import send_pirates_dock_view
        await send_pirates_dock_view(interaction, str(interaction.user.id))

    @discord.ui.button(label="Megamart", style=discord.ButtonStyle.secondary, custom_id="town_megamart", row=1)
    async def megamart(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        from views.market.megamart import send_megamart_view
        await send_megamart_view(interaction, str(interaction.user.id))

    @discord.ui.button(label="Adventure", style=discord.ButtonStyle.success, custom_id="town_adventure", row=2)
    async def adventure(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        from views.adventure import AdventureView
        embed = discord.Embed(title="Adventure Awaits!", description="Choose your adventure!", color=discord.Color.blue())
        embed.set_image(url="https://i.imgur.com/R48BhNs.png")
        await interaction.followup.send(embed=embed, view=AdventureView(user_id=str(interaction.user.id)))

    @discord.ui.button(label="Mission", style=discord.ButtonStyle.success, custom_id="town_mission", row=2)
    async def mission(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        from views.mission import MissionSelectView
        view = MissionSelectView(str(interaction.user.id))
        embed = view.get_embed()
        await interaction.followup.send(embed=embed, view=view)

    @discord.ui.button(label="Game Corner", style=discord.ButtonStyle.success, custom_id="town_game_corner", row=2)
    async def game_corner(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        from views.gamecorner import GameCornerDurationView
        view = GameCornerDurationView(interaction.user)
        embed = discord.Embed(title="Game Corner", description="Welcome to the Pomodoro Game Corner!", color=discord.Color.green())
        await interaction.followup.send(embed=embed, view=view)

    @discord.ui.button(label="Garden", style=discord.ButtonStyle.secondary, custom_id="town_garden", row=3)
    async def garden(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        from views.garden import GardenView
        view = GardenView(str(interaction.user.id))
        embed = discord.Embed(title="Garden", color=discord.Color.green())
        await interaction.followup.send(embed=embed, view=view)

    @discord.ui.button(label="Farm", style=discord.ButtonStyle.secondary, custom_id="town_farm", row=3)
    async def farm(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        from views.market.farm import send_farm_view
        await send_farm_view(interaction, str(interaction.user.id))

    @discord.ui.button(label="Nursery", style=discord.ButtonStyle.secondary, custom_id="town_nursery", row=3)
    async def nursery(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        from views.market.nursery import send_nursery_view
        await send_nursery_view(interaction, str(interaction.user.id))

class CharacterMenuView(View):
    def __init__(self):
        super().__init__(timeout=120)

    @discord.ui.button(label="View My Characters", style=discord.ButtonStyle.primary, custom_id="char_view_my", row=0)
    async def view_my_characters(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        user_id = str(interaction.user.id)
        trainers = core.trainer.get_trainers(user_id)
        view = views.trainer.PaginatedTrainersView(trainers, editable=True, user_id=user_id)
        embed = await view.get_current_embed()
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(label="View Other Characters", style=discord.ButtonStyle.primary, custom_id="char_view_other", row=0)
    async def view_other_characters(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        user_id = str(interaction.user.id)
        other_trainers = core.trainer.get_other_trainers_from_db(user_id)
        view = views.trainer.PaginatedTrainersView(other_trainers, editable=False, user_id=user_id)
        embed = await view.get_current_embed()
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(label="Trade Items", style=discord.ButtonStyle.secondary, custom_id="char_trade_items", row=1)
    async def trade_items(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        player_id = str(interaction.user.id)
        # Assuming a TradeTrainerSelectionView exists; adjust import as needed.
        from logic.trade_items import TradeTrainerSelectionView
        view = TradeTrainerSelectionView(player_id)
        await interaction.followup.send("Select your trainer and an opponent for trading:", view=view, ephemeral=True)

    @discord.ui.button(label="Trade Pokemon", style=discord.ButtonStyle.secondary, custom_id="char_trade_pokemon", row=1)
    async def trade_pokemon(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        player_id = str(interaction.user.id)
        view = TradePokemonSelectionView(player_id)
        await interaction.followup.send("Select trainers for the Pokémon trade:", view=view, ephemeral=True)

    @discord.ui.button(label="Add Trainer", style=discord.ButtonStyle.primary, custom_id="char_add_trainer", row=2)
    async def add_trainer_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        embed = discord.Embed(
            title="Add Trainer",
            description="Choose one of the following options:",
            color=discord.Color.blue()
        )
        embed.set_image(url="https://i.imgur.com/example.jpg")
        view = AddTrainerEmbedView()
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(label="Add Mon", style=discord.ButtonStyle.primary, custom_id="add_mon", row=2)
    async def add_mon_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        embed = discord.Embed(
            title="Add Mon",
            description="Please select a trainer for the new mon:",
            color=discord.Color.blue()
        )
        embed.set_image(url="https://i.imgur.com/example.jpg")
        from views.add_mon import TrainerSelectForMonView
        trainer_select_view = TrainerSelectForMonView(str(interaction.user.id))
        await interaction.followup.send(embed=embed, view=trainer_select_view, ephemeral=True)
