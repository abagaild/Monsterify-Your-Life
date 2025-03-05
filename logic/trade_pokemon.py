import logging
import random
import discord
from core.core_views import create_paginated_trainers_dropdown
from core.database import fetch_all, update_mon_data, get_mons_for_trainer
from core.trainer import get_other_trainers_from_db, get_trainers, get_all_trainers
from core.rollmons import register_mon
from core.currency import add_currency

TRADE_MON_IMAGES = [
    "https://example.com/trade_mons_img1.png",
    "https://example.com/trade_mons_img2.png",
    "https://example.com/trade_mons_img3.png"
]

TRADE_MON_FLAVOR_TEXTS = [
    "A perfect swap!",
    "The mon trade was legendary!",
    "A new bond is formed through trade!"
]

async def transfer_mon(mon_id: int, old_trainer: dict, new_trainer: dict) -> bool:
    """
    Transfers a mon from the old trainer to the new trainer by updating its
    trainer_id and player_user_id in the database.
    """
    try:
        new_trainer_id = new_trainer['id']
        new_player = new_trainer.get('user_id')
        success_db = update_mon_data(mon_id, trainer_id=new_trainer_id, player=new_player)
        if not success_db:
            logging.error(f"DB update failed for mon id {mon_id}")
            return False
        return True
    except Exception as e:
        logging.error(f"Error transferring mon id {mon_id} from {old_trainer['name']} to {new_trainer['name']}: {e}")
        return False

class TradePokemonSelectionView(discord.ui.View):
    def __init__(self, player_id: str):
        super().__init__(timeout=180)
        self.player_id = player_id
        self.trainer1 = None
        self.trainer2 = None
        self.trainer1_mon = None
        self.trainer2_mon = None
        own_trainers = get_trainers(player_id)
        other_trainers = get_other_trainers_from_db(player_id)
        own_dropdown = create_paginated_trainers_dropdown(own_trainers, "Select Your Trainer", self.own_trainer_callback)
        other_dropdown = create_paginated_trainers_dropdown(other_trainers, "Select Other Trainer", self.other_trainer_callback)
        self.add_item(own_dropdown.children[0])
        self.add_item(other_dropdown.children[0])
        self.add_item(TrainerSelectionConfirmButton())

    async def own_trainer_callback(self, interaction: discord.Interaction, selected_value: str):
        for trainer in get_trainers(self.player_id):
            if str(trainer["id"]) == selected_value:
                self.trainer1 = trainer
                break
        await interaction.response.send_message(f"Selected your trainer: {self.trainer1['name']}", ephemeral=True)

    async def other_trainer_callback(self, interaction: discord.Interaction, selected_value: str):
        for trainer in get_other_trainers_from_db(self.player_id):
            if str(trainer["id"]) == selected_value:
                self.trainer2 = trainer
                break
        await interaction.response.send_message(f"Selected other trainer: {self.trainer2['name']}", ephemeral=True)

class TrainerSelectionConfirmButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Confirm Trainer Selection", style=discord.ButtonStyle.success)

    async def callback(self, interaction: discord.Interaction):
        view: TradePokemonSelectionView = self.view  # type: ignore
        if view.trainer1 is None or view.trainer2 is None:
            await interaction.response.send_message("Please select both trainers before proceeding.", ephemeral=True)
            return
        await interaction.response.send_message("Now select a Pokémon from each trainer (or 'None' if gifting):", ephemeral=True)
        view.clear_items()
        mons1 = get_mons_for_trainer(view.trainer1['id'])
        mons2 = get_mons_for_trainer(view.trainer2['id'])
        mons1_options = [discord.SelectOption(label="None", value="none")]
        for mon in mons1:
            mons1_options.append(discord.SelectOption(label=mon["mon_name"], value=str(mon["id"])))
        mons2_options = [discord.SelectOption(label="None", value="none")]
        for mon in mons2:
            mons2_options.append(discord.SelectOption(label=mon["mon_name"], value=str(mon["id"])))
        pkm1_select = PokemonSelect(mons1_options, placeholder="Select a Pokémon from your trainer")
        pkm2_select = PokemonSelect(mons2_options, placeholder="Select a Pokémon from the other trainer")
        view.add_item(pkm1_select)
        view.add_item(pkm2_select)
        view.add_item(PokemonTradeConfirmButton())
        try:
            await interaction.message.edit(view=view)
        except discord.errors.NotFound:
            await interaction.followup.send("Continue with your selection:", view=view, ephemeral=True)

class PokemonSelect(discord.ui.Select):
    def __init__(self, options, placeholder: str):
        super().__init__(placeholder=placeholder, options=options, min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        view: TradePokemonSelectionView = self.view  # type: ignore
        if "your trainer" in self.placeholder.lower():
            view.trainer1_mon = self.values[0]
            await interaction.response.send_message(f"Selected Pokémon from your trainer: {self.values[0]}", ephemeral=True)
        else:
            view.trainer2_mon = self.values[0]
            await interaction.response.send_message(f"Selected Pokémon from other trainer: {self.values[0]}", ephemeral=True)

class PokemonTradeConfirmButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Confirm Pokémon Trade", style=discord.ButtonStyle.success)

    async def callback(self, interaction: discord.Interaction):
        view: TradePokemonSelectionView = self.view  # type: ignore
        if view.trainer1_mon is None or view.trainer2_mon is None:
            await interaction.response.send_message("Please select a Pokémon from each trainer (or 'None') before confirming.", ephemeral=True)
            return
        messages = []
        success = True
        if view.trainer1_mon != "none" and view.trainer2_mon != "none":
            s1 = await transfer_mon(int(view.trainer1_mon), view.trainer1, view.trainer2)
            s2 = await transfer_mon(int(view.trainer2_mon), view.trainer2, view.trainer1)
            if s1 and s2:
                messages.append("Pokémon swapped successfully.")
            else:
                messages.append("Failed to swap one or both Pokémon.")
                success = False
        elif view.trainer1_mon == "none" and view.trainer2_mon != "none":
            s = await transfer_mon(int(view.trainer2_mon), view.trainer2, view.trainer1)
            if s:
                messages.append("Pokémon gifted from Trainer 2 to Trainer 1 successfully.")
            else:
                messages.append("Failed to transfer Pokémon from Trainer 2 to Trainer 1.")
                success = False
        elif view.trainer1_mon != "none" and view.trainer2_mon == "none":
            s = await transfer_mon(int(view.trainer1_mon), view.trainer1, view.trainer2)
            if s:
                messages.append("Pokémon gifted from Trainer 1 to Trainer 2 successfully.")
            else:
                messages.append("Failed to transfer Pokémon from Trainer 1 to Trainer 2.")
                success = False
        else:
            messages.append("No Pokémon selected for trading.")
            success = False
        if success:
            title = "Trade Result"
            description = "\n".join(messages)
            color = discord.Color.green()
        else:
            title = "Trade Error"
            description = "\n".join(messages)
            color = discord.Color.red()
        embed = discord.Embed(title=title, description=description, color=color)
        embed.set_image(url=random.choice(TRADE_MON_IMAGES))
        embed.set_footer(text=random.choice(TRADE_MON_FLAVOR_TEXTS))
        await interaction.response.send_message(embed=embed, ephemeral=True)
