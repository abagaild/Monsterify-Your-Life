import random

import discord

# Import a centralized pagination view (assumed to be in core.views.pagination)
from core.core_views import PaginatedDropdownView
from core.trainer import get_trainers, get_all_trainers, get_mons_for_trainer_dict
from logic.market.farm import IMAGES, MESSAGES


class FarmShopView(discord.ui.View):
    def __init__(self, user_id: str):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.image = random.choice(IMAGES)
        self.message = random.choice(MESSAGES)

    @discord.ui.button(label="Shop", style=discord.ButtonStyle.primary, custom_id="farm_shop")
    async def shop_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        # You might later implement a dedicated shop view or use a generic shop view.
        await interaction.response.send_message(f"Farm Shop action for user {self.user_id} triggered.", ephemeral=True)

    @discord.ui.button(label="Activity (Breed)", style=discord.ButtonStyle.secondary, custom_id="farm_activity")
    async def farm_activity(self, interaction: discord.Interaction, button: discord.ui.Button):
        await open_farm(interaction)

async def send_farm_view(interaction: discord.Interaction, user_id: str):
    view = FarmShopView(user_id)
    embed = discord.Embed(title="Farm", description=view.message, color=discord.Color.dark_green())
    embed.set_image(url=view.image)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

# -------------------------------------
# Breeding Activity Views
# -------------------------------------
class FarmInitialView(discord.ui.View):
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
        player_trainers = get_trainers(self.user)
        all_trainers = get_all_trainers()
        player_options = []
        for t in player_trainers:
            self.player_trainer_map[t["id"]] = t
            player_options.append(discord.SelectOption(label=t["name"], value=str(t["id"])))
        all_options = []
        for t in all_trainers:
            self.all_trainer_map[t["id"]] = t
            all_options.append(discord.SelectOption(label=t["name"], value=str(t["id"])))
        self.player_dropdown = PaginatedDropdownView(
            full_options=player_options,
            placeholder="Select your trainer",
            callback=self.player_trainer_callback
        )
        self.all_dropdown = PaginatedDropdownView(
            full_options=all_options,
            placeholder="Select any trainer",
            callback=self.all_trainer_callback
        )
        for child in self.player_dropdown.children:
            self.add_item(child)
        for child in self.all_dropdown.children:
            self.add_item(child)

    async def player_trainer_callback(self, interaction: discord.Interaction, selected_value: str):
        self.player_trainer_id = int(selected_value)
        await interaction.response.defer()
        await self.check_and_proceed(interaction)

    async def all_trainer_callback(self, interaction: discord.Interaction, selected_value: str):
        self.all_trainer_id = int(selected_value)
        await interaction.response.defer()
        await self.check_and_proceed(interaction)

    async def check_and_proceed(self, interaction: discord.Interaction):
        if self.player_trainer_id and self.all_trainer_id:
            player_trainer = self.player_trainer_map.get(self.player_trainer_id)
            # Verify that the player's trainer has enough Legacy Leeways for breeding.
            from core.google_sheets import check_inventory
            check_result, msg = check_inventory(str(interaction.user.id), player_trainer["name"], "Legacy Leeway", 1)
            if not check_result:
                await interaction.followup.send(
                    f"Your trainer {player_trainer['name']} does not have enough Legacy Leeways to breed. {msg}",
                    ephemeral=True
                )
                return
            next_view = FarmMonSelectView(
                user=interaction.user,
                player_trainer=player_trainer,
                all_trainer=self.all_trainer_map.get(self.all_trainer_id)
            )
            await interaction.edit_original_response(content="Select one mon from each trainer to breed:", view=next_view)

class FarmMonSelectView(discord.ui.View):
    """
    View for selecting one mon from each trainer.
    After both selections are made, calls breed_mons to generate offspring.
    """
    def __init__(self, user: discord.User, player_trainer: dict, all_trainer: dict):
        super().__init__(timeout=120)
        self.user = user
        self.player_trainer = player_trainer
        self.all_trainer = all_trainer
        self.player_mon_id = None
        self.all_mon_id = None
        player_mons = get_mons_for_trainer_dict(player_trainer["id"])
        all_mons = get_mons_for_trainer_dict(all_trainer["id"])
        self.player_mon_map = {mon["id"]: mon for mon in player_mons}
        self.all_mon_map = {mon["id"]: mon for mon in all_mons}
        player_options = [discord.SelectOption(label=mon["mon_name"], value=str(mon["id"])) for mon in player_mons]
        all_options = [discord.SelectOption(label=mon["mon_name"], value=str(mon["id"])) for mon in all_mons]
        self.player_mon_dropdown = PaginatedDropdownView(
            full_options=player_options,
            placeholder=f"Select a mon from {player_trainer['name']}",
            callback=self.player_mon_callback
        )
        self.all_mon_dropdown = PaginatedDropdownView(
            full_options=all_options,
            placeholder=f"Select a mon from {all_trainer['name']}",
            callback=self.all_mon_callback
        )
        for child in self.player_mon_dropdown.children:
            self.add_item(child)
        for child in self.all_mon_dropdown.children:
            self.add_item(child)

    async def player_mon_callback(self, interaction: discord.Interaction, selected_value: str):
        self.player_mon_id = int(selected_value)
        await interaction.response.defer()
        await self.check_and_breed(interaction)

    async def all_mon_callback(self, interaction: discord.Interaction, selected_value: str):
        self.all_mon_id = int(selected_value)
        await interaction.response.defer()
        await self.check_and_breed(interaction)

    async def check_and_breed(self, interaction: discord.Interaction):
        if self.player_mon_id is not None and self.all_mon_id is not None:
            user_id = str(interaction.user.id)
            from logic.market.farm import breed_mons  # Our centralized breeding function
            offspring_list = await breed_mons(self.player_mon_id, self.all_mon_id, user_id)
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
                description_lines.append(f"**Offspring {idx}:**\nSpecies: {species_str}\nTypes: {types_str}\nAttribute: {off.get('attribute', '')}")
            embed = discord.Embed(title="Breeding Results", description="\n\n".join(description_lines), color=0x00AA00)
            await interaction.followup.send(embed=embed)
            # Registration view and next steps can be added here.
            from logic.market.farm import OffspringRegistrationView, FarmResultView
            reg_view = OffspringRegistrationView(self.user, offspring_list, self.player_mon_map.get(self.player_mon_id), self.all_mon_map.get(self.all_mon_id))
            await interaction.followup.send("Register each offspring by clicking the appropriate button:", view=reg_view)
            result_view = FarmResultView(self.user, self.player_trainer, self.all_trainer, self.player_mon_map.get(self.player_mon_id), self.all_mon_map.get(self.all_mon_id))
            await interaction.followup.send("What would you like to do next?", view=result_view)

# A helper to open the Farm view.
async def open_farm(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Welcome to the Farm!",
        description=random.choice([
            "The old barn creaks under the weight of dreams.",
            "A quiet field where nature and magic intertwine."
        ]),
        color=0x00AA00
    )
    embed.set_image(url=random.choice(IMAGES))
    view = FarmInitialView(interaction.user)
    if not interaction.response.is_done():
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    else:
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)
