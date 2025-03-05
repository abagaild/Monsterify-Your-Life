import discord
from core.core_views import PaginatedDropdownView
from core.trainer import get_trainers, get_all_trainers
from core.database import get_mons_for_trainer
from core.items import check_inventory
from logic.market.farm_breeding import breed_mons
from core.mon import register_mon  # For offspring registration
from logic.market.farm_breeding import OffspringRegistrationView, FarmResultView

class FarmInitialViewLogic(discord.ui.View):
    """
    Initial view for selecting two trainers:
      - The player's trainer (from get_trainers)
      - Any trainer from the full list (from get_all_trainers)
    """
    def __init__(self, user: discord.User):
        super().__init__(timeout=120)
        self.user = user
        self.player_trainer_id = None
        self.all_trainer_id = None
        self.player_trainer_map = {}
        self.all_trainer_map = {}

        player_trainers = get_trainers(str(self.user.id))
        all_trainers = get_all_trainers()

        player_options = []
        for t in player_trainers:
            self.player_trainer_map[t["id"]] = t
            player_options.append(discord.SelectOption(label=t["character_name"], value=str(t["id"])))
        if not player_options:
            player_options = [discord.SelectOption(label="No trainers available", value="none", default=True)]
        all_options = []
        for t in all_trainers:
            self.all_trainer_map[t["id"]] = t
            all_options.append(discord.SelectOption(label=t["character_name"], value=str(t["id"])))
        if not all_options:
            all_options = [discord.SelectOption(label="No trainers available", value="none", default=True)]
        self.player_dropdown = PaginatedDropdownView(
            player_options,
            "Select your trainer",
            self.player_trainer_callback,
            page_size=25
        )
        self.all_dropdown = PaginatedDropdownView(
            all_options,
            "Select any trainer",
            self.all_trainer_callback,
            page_size=25
        )
        for child in self.player_dropdown.children:
            self.add_item(child)
        for child in self.all_dropdown.children:
            self.add_item(child)

    async def player_trainer_callback(self, interaction: discord.Interaction, selected_value: str):
        if selected_value == "none":
            await interaction.response.send_message("No trainers available for selection.", ephemeral=True)
            return
        self.player_trainer_id = int(selected_value)
        await interaction.response.defer(ephemeral=True)
        await self.check_and_proceed(interaction)

    async def all_trainer_callback(self, interaction: discord.Interaction, selected_value: str):
        if selected_value == "none":
            await interaction.response.send_message("No trainers available for selection.", ephemeral=True)
            return
        self.all_trainer_id = int(selected_value)
        await interaction.response.defer(ephemeral=True)
        await self.check_and_proceed(interaction)

    async def check_and_proceed(self, interaction: discord.Interaction):
        if self.player_trainer_id and self.all_trainer_id:
            player_trainer = self.player_trainer_map.get(self.player_trainer_id)
            check_result, msg = check_inventory(str(interaction.user.id), player_trainer["name"], "Legacy Leeway", 1)
            if not check_result:
                await interaction.followup.send(
                    f"Your trainer {player_trainer['name']} does not have enough Legacy Leeways to breed. {msg}",
                    ephemeral=True
                )
                return
            next_view = FarmMonSelectViewLogic(
                user=interaction.user,
                player_trainer=player_trainer,
                all_trainer=self.all_trainer_map.get(self.all_trainer_id)
            )
            await interaction.edit_original_response(
                content="Select one mon from each trainer to breed:",
                view=next_view
            )

class FarmMonSelectViewLogic(discord.ui.View):
    """
    View for selecting one mon from each trainer.
    """
    def __init__(self, user: discord.User, player_trainer: dict, all_trainer: dict):
        super().__init__(timeout=120)
        self.user = user
        self.player_trainer = player_trainer
        self.all_trainer = all_trainer
        self.selected_player_mon = None
        self.selected_all_mon = None

        player_mons = get_mons_for_trainer(player_trainer["id"])
        all_mons = get_mons_for_trainer(all_trainer["id"])
        self.player_mon_map = {mon["id"]: mon for mon in player_mons}
        self.all_mon_map = {mon["id"]: mon for mon in all_mons}

        player_options = [discord.SelectOption(label=mon["mon_name"], value=str(mon["id"])) for mon in player_mons]
        if not player_options:
            player_options = [discord.SelectOption(label="No mons available", value="none", default=True)]
        all_options = [discord.SelectOption(label=mon["mon_name"], value=str(mon["id"])) for mon in all_mons]
        if not all_options:
            all_options = [discord.SelectOption(label="No mons available", value="none", default=True)]

        self.player_mon_dropdown = PaginatedDropdownView(
            player_options,
            "Select a mon from your trainer",
            self.player_mon_callback,
            page_size=25
        )
        self.all_mon_dropdown = PaginatedDropdownView(
            all_options,
            "Select a mon from the other trainer",
            self.all_mon_callback,
            page_size=25
        )
        for child in self.player_mon_dropdown.children:
            self.add_item(child)
        for child in self.all_mon_dropdown.children:
            self.add_item(child)

    async def player_mon_callback(self, interaction: discord.Interaction, selected_value: str):
        if selected_value == "none":
            await interaction.response.send_message("No mon available from your trainer.", ephemeral=True)
            return
        self.selected_player_mon = int(selected_value)
        await interaction.response.defer(ephemeral=True)
        await self.check_mon_selection(interaction)

    async def all_mon_callback(self, interaction: discord.Interaction, selected_value: str):
        if selected_value == "none":
            await interaction.response.send_message("No mon available from the other trainer.", ephemeral=True)
            return
        self.selected_all_mon = int(selected_value)
        await interaction.response.defer(ephemeral=True)
        await self.check_and_breed(interaction)

    async def check_mon_selection(self, interaction: discord.Interaction):
        if self.selected_player_mon is not None and self.selected_all_mon is not None:
            await self.check_and_breed(interaction)

    async def check_and_breed(self, interaction: discord.Interaction):
        if self.selected_player_mon is not None and self.selected_all_mon is not None:
            player_mon = self.player_mon_map.get(self.selected_player_mon)
            other_mon = self.all_mon_map.get(self.selected_all_mon)
            if not player_mon or not other_mon:
                await interaction.followup.send("Selected mon not found.", ephemeral=True)
                return
            offspring_list = await breed_mons(player_mon["id"], other_mon["id"], str(interaction.user.id))
            if not offspring_list:
                await interaction.followup.send("Breeding failed. Ensure selected mons are eligible.", ephemeral=True)
                return
            description_lines = []
            for idx, off in enumerate(offspring_list, start=1):
                species_str = off.get('species1', '')
                if off.get('species2'):
                    species_str += f" / {off.get('species2')}"
                if off.get('species3'):
                    species_str += f" / {off.get('species3')}"
                types_str = ", ".join(off.get("types", []))
                description_lines.append(
                    f"**Offspring {idx}:**\nSpecies: {species_str}\nTypes: {types_str}\nAttribute: {off.get('attribute', '')}"
                )
            embed = discord.Embed(
                title="Breeding Results",
                description="\n\n".join(description_lines),
                color=0x00AA00
            )
            await interaction.followup.send(embed=embed)
            reg_view = OffspringRegistrationView(
                self.user, offspring_list, player_mon, other_mon
            )
            await interaction.followup.send("Register your offspring:", view=reg_view)
            result_view = FarmResultView(
                self.user, self.player_trainer, self.all_trainer, player_mon, other_mon
            )
            await interaction.followup.send("What would you like to do next?", view=result_view)
