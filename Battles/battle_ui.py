# cogs/battle/battle_ui.py
import json
import os
import random

import discord
from discord.ui import Button, View, Modal, Select, TextInput
from Battles import battle_core, battle_modes  # Import battle_modes to access active battles


class BattleMenuView(View):
    """
    A view that presents buttons for each battle mode.
    """

    def __init__(self, timeout: float = 180):
        super().__init__(timeout=timeout)
        # Each button’s custom_id will determine the mode
        self.add_item(
            Button(label="Friendly Competition", style=discord.ButtonStyle.primary, custom_id="battle_friendly"))
        self.add_item(Button(label="Battle Rival", style=discord.ButtonStyle.primary, custom_id="battle_rival"))
        self.add_item(Button(label="Custom Battle", style=discord.ButtonStyle.primary, custom_id="battle_custom"))
        self.add_item(Button(label="Battle Frontier", style=discord.ButtonStyle.primary, custom_id="battle_frontier"))
        self.add_item(Button(label="Gym League", style=discord.ButtonStyle.primary, custom_id="battle_gym"))


class AttackSubmissionModal(Modal):
    """
    A modal for the player to submit an attack.
    """

    def __init__(self):
        super().__init__(title="Submit Your Attack")
        self.attack_name = TextInput(label="Attack Name", placeholder="Enter the move name")
        self.add_item(self.attack_name)
        self.artwork_url = TextInput(label="Artwork URL", placeholder="Enter the link to your artwork")
        self.add_item(self.artwork_url)
        self.bonus = TextInput(label="Bonus (number)", placeholder="Enter any bonus damage (e.g. 5)", required=False)
        self.add_item(self.bonus)

    async def callback(self, interaction: discord.Interaction):
        # Retrieve values from modal input
        move_name = self.attack_name.value
        url = self.artwork_url.value  # You could later validate/display this image in an embed
        bonus_val = int(self.bonus.value) if self.bonus.value.isdigit() else 0

        # Look up the battle state for this user (using the global active_battles from battle_modes)
        battle_state = battle_modes.active_battles.get(interaction.user.id)
        if not battle_state:
            return await interaction.response.send_message("No active battle found.", ephemeral=True)

        # Process the player's attack
        damage, remaining_hp = battle_core.process_player_attack(battle_state, move_name, bonus_val)
        response_text = (
            f"Your **{battle_state.player_mon['name']}** used **{move_name}** and dealt **{damage}** damage!\n"
            f"Opponent **{battle_state.opponent_mon['name']}** HP is now **{remaining_hp}**."
        )
        # Check if opponent is defeated
        if battle_state.opponent_mon["hp"] <= 0:
            response_text += "\nOpponent defeated! You win!"
            battle_modes.active_battles.pop(interaction.user.id, None)
            return await interaction.response.send_message(response_text, ephemeral=True)

        # Now let the AI retaliate
        ai_damage = battle_core.ai_attack(battle_state)
        response_text += (
            f"\nOpponent **{battle_state.opponent_mon['name']}** retaliates and deals **{ai_damage}** damage to your mon!\n"
            f"Your mon **{battle_state.player_mon['name']}** HP is now **{battle_state.player_mon['hp']}**."
        )
        if battle_state.player_mon["hp"] <= 0:
            response_text += "\nYour mon fainted! You lose!"
            battle_modes.active_battles.pop(interaction.user.id, None)
        await interaction.response.send_message(response_text, ephemeral=True)


def load_enemy_trainers():
    """Load enemy trainer data from the JSON file."""
    path = os.path.join(os.path.dirname(__file__), "enemies.json")
    with open(path, "r") as f:
        data = json.load(f)
    return data["trainers"]


# Cache enemy trainers from JSON
ENEMY_TRAINERS = load_enemy_trainers()


class SummonBattleMenuButton(discord.ui.Button):
    """
    A button that, when clicked, summons the enemy trainer selection menu.
    """

    def __init__(self):
        super().__init__(label="Battle Menu", style=discord.ButtonStyle.primary, custom_id="summon_battle_menu")

    async def callback(self, interaction: discord.Interaction):
        # When the button is clicked, send the EnemyTrainerSelectView.
        view = BattleMenuView()
        await interaction.response.send_message("Select a battle mode:", view=view, ephemeral=True)

class EnemyTrainerSelectView(View):
    """
    A view containing a select menu to choose an enemy trainer.
    """

    def __init__(self, timeout: float = 180):
        super().__init__(timeout=timeout)
        self.add_item(EnemyTrainerSelect())


class EnemyTrainerSelect(Select):
    """
    A select menu listing enemy trainers loaded from the JSON file.
    """

    def __init__(self):
        options = []
        for trainer in ENEMY_TRAINERS:
            options.append(discord.SelectOption(label=trainer["name"], description=f"Battle {trainer['name']}"))
        super().__init__(
            placeholder="Choose a trainer...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="enemy_trainer_select"
        )

    async def callback(self, interaction: discord.Interaction):
        selected_name = self.values[0]
        trainer = next((t for t in ENEMY_TRAINERS if t["name"] == selected_name), None)
        if not trainer:
            return await interaction.response.send_message("Trainer not found.", ephemeral=True)

        # Create an embed with the trainer details.
        embed = discord.Embed(title=f"Trainer: {trainer['name']}", description="Enemy trainer details")
        embed.set_image(url=trainer.get("image", ""))
        mons_list = "\n".join([f"{mon['name']} ({mon['species']})" for mon in trainer.get("mons", [])])
        embed.add_field(name="Mons", value=mons_list or "No mons available", inline=False)

        view = TrainerDetailView(trainer)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class TrainerDetailView(View):
    """
    A view showing trainer details with a button to view the trainer's mons.
    """

    def __init__(self, trainer_data, timeout: float = 180):
        super().__init__(timeout=timeout)
        self.trainer_data = trainer_data
        self.add_item(ViewMonsButton(trainer_data))


class ViewMonsButton(Button):
    """
    A button that, when clicked, shows a view for selecting a mon from the trainer.
    """

    def __init__(self, trainer_data):
        super().__init__(label="View Mons", style=discord.ButtonStyle.secondary, custom_id="view_mons_button")
        self.trainer_data = trainer_data

    async def callback(self, interaction: discord.Interaction):
        view = MonsView(self.trainer_data)
        await interaction.response.send_message("Select a mon to view details:", view=view, ephemeral=True)


class MonsView(View):
    """
    A view containing a select menu to choose one of the trainer's mons.
    """

    def __init__(self, trainer_data, timeout: float = 180):
        super().__init__(timeout=timeout)
        self.trainer_data = trainer_data
        self.add_item(MonsSelect(trainer_data))


class MonsSelect(Select):
    """
    A select menu listing the mons of the selected trainer.
    """

    def __init__(self, trainer_data):
        options = []
        for mon in trainer_data.get("mons", []):
            options.append(
                discord.SelectOption(label=mon["name"], description=f"Species: {mon.get('species', 'Unknown')}"))
        super().__init__(
            placeholder="Choose a mon...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="mons_select"
        )
        self.trainer_data = trainer_data

    async def callback(self, interaction: discord.Interaction):
        selected_mon_name = self.values[0]
        mon = next((m for m in self.trainer_data.get("mons", []) if m["name"] == selected_mon_name), None)
        if not mon:
            return await interaction.response.send_message("Mon not found.", ephemeral=True)

        # Create an embed with mon details.
        embed = discord.Embed(title=f"{mon['name']} Details", description=f"Species: {mon.get('species', 'Unknown')}")
        embed.add_field(name="HP", value=str(mon.get("hp", "N/A")), inline=True)
        embed.add_field(name="Attack", value=str(mon.get("attack", "N/A")), inline=True)
        embed.add_field(name="Defense", value=str(mon.get("defense", "N/A")), inline=True)
        embed.set_thumbnail(url=mon.get("image", ""))
        await interaction.response.send_message(embed=embed, ephemeral=True)

class BattleState:
    """
    Represents an ongoing battle between the player's team and an enemy trainer’s team.
    """
    def __init__(self, user_id: int, enemy_trainer_name: str):
        self.user_id = user_id
        self.enemy_trainer_name = enemy_trainer_name
        self.player_team = []   # List of dicts for each mon selected by the user.
        self.enemy_team = []    # List of dicts for enemy mons.
        self.levels_earned = 0
        self.coins = 0
        self.category = None    # E.g. 'league', 'custom', etc.

def calculate_damage(attack_power: int, attacker_stat: int, defender_stat: int, bonus: int = 0, is_status: bool = False) -> int:
    """
    Calculates damage using a simple formula.
    Damage = ((attack_power + bonus) * attacker_stat / defender_stat)
    If the move is a status move, damage doubles.
    """
    base_damage = (attack_power + bonus) * attacker_stat / defender_stat
    if is_status:
        base_damage *= 2
    return round(base_damage)

def process_player_attack(battle_state: BattleState, attacking_mon: dict, selected_attack: dict, extra_names: list, bonus: int) -> int:
    """
    Processes the player's attack.
    - Counts 2 bonus per extra name provided.
    - Retrieves the move power from the selected attack (if not found, defaults to 10).
    - Multiplies by the attacking mon’s stat (using physical stat here, or special if move indicates).
    - Returns the damage dealt.
    """
    extra_bonus = 2 * len(extra_names)
    total_bonus = bonus + extra_bonus
    move_power = selected_attack.get("power", 10)
    is_status = selected_attack.get("is_status", False)
    # For simplicity, assume physical move: use 'attack' and compare against enemy mon’s 'defense'
    damage = calculate_damage(move_power, attacking_mon.get("attack", 10), attacking_mon.get("defense", 10), bonus=total_bonus, is_status=is_status)
    return damage

def process_enemy_retaliation(battle_state: BattleState, enemy_mon: dict, player_mon: dict) -> int:
    """
    Processes enemy retaliation.
    - Computes the difference between enemy’s attack and player's mon attack.
    - If positive: damage = (difference * enemy attack) / (player's defense or special defense, chosen randomly)
    - If negative: make difference positive, add to enemy attack, divide by player's defense or special defense.
    """
    diff = enemy_mon.get("attack", 10) - player_mon.get("attack", 10)
    defense_stat = player_mon.get("defense", 10) if random.choice([True, False]) else player_mon.get("special_defense", 10)
    if diff > 0:
        damage = (diff * enemy_mon.get("attack", 10)) / defense_stat
    else:
        damage = ((abs(diff) + enemy_mon.get("attack", 10))) / defense_stat
    return round(damage)