# cogs/battle/battle_core.py
import random

import discord
import discord.ui
from discord.ui import Button, View


class BattleState:
    """
    Stores the state of an ongoing battle.
    """
    def __init__(self, player_id, player_mon, opponent_mon, mode: str):
        self.player_id = player_id
        self.player_mon = player_mon      # e.g., a dict: {"name": "Pika", "hp": 100, "attack": 30, "defense": 20}
        self.opponent_mon = opponent_mon  # e.g., {"name": "RivalMon", "hp": 100, "attack": 25, "defense": 15}
        self.mode = mode                  # one of "friendly", "rival", "custom", "frontier", "gym"
        self.turn = 1
        self.active = True

def calculate_damage(attacker: dict, defender: dict, move_power: int, bonus: int = 0) -> int:
    """
    Calculates damage using a simple formula.
    Damage = ((attacker attack / defender defense) * move_power * random variance) + bonus
    """
    base = (attacker.get("attack", 10) / defender.get("defense", 10)) * move_power
    variance = random.uniform(0.85, 1.0)
    damage = base * variance + bonus
    return int(damage)

def apply_attack(battle_state: BattleState, damage: int) -> int:
    """
    Subtract damage from opponent HP and update battle state.
    """
    battle_state.opponent_mon["hp"] -= damage
    if battle_state.opponent_mon["hp"] <= 0:
        battle_state.opponent_mon["hp"] = 0
        battle_state.active = False
    return battle_state.opponent_mon["hp"]

def process_player_attack(battle_state: BattleState, move_name: str, bonus: int = 0) -> (int, int):
    """
    Processes the player’s attack.
    For demonstration, assign move power based on the move name.
    """
    # Example: if the move name is "Thunder", use a higher power.
    move_power = 25 if move_name.lower() == "thunder" else 20
    damage = calculate_damage(battle_state.player_mon, battle_state.opponent_mon, move_power, bonus)
    remaining_hp = apply_attack(battle_state, damage)
    return damage, remaining_hp

def ai_attack(battle_state: BattleState) -> int:
    """
    The AI selects a random move (with random power) and attacks the player's mon.
    """
    # For demonstration, use a random move power between 10 and 20.
    move_power = random.randint(10, 20)
    damage = calculate_damage(battle_state.opponent_mon, battle_state.player_mon, move_power)
    battle_state.player_mon["hp"] -= damage
    if battle_state.player_mon["hp"] <= 0:
        battle_state.player_mon["hp"] = 0
        battle_state.active = False
    return damage



class BattleMenuView(View):
    """
    A view that presents buttons for each battle mode.
    """
    def __init__(self, timeout: float = 180):
        super().__init__(timeout=timeout)
        self.add_item(Button(label="Friendly Competition", style=discord.ButtonStyle.primary, custom_id="battle_friendly"))
        self.add_item(Button(label="Battle Rival", style=discord.ButtonStyle.primary, custom_id="battle_rival"))
        self.add_item(Button(label="Custom Battle", style=discord.ButtonStyle.primary, custom_id="battle_custom"))
        self.add_item(Button(label="Battle Frontier", style=discord.ButtonStyle.primary, custom_id="battle_frontier"))
        self.add_item(Button(label="Gym League", style=discord.ButtonStyle.primary, custom_id="battle_gym"))
