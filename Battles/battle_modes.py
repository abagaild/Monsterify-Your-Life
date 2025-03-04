# cogs/battle/battle_modes.py
import discord
from discord.ext import commands
from Battles import battle_core, battle_ui
import random

# Global dictionary to track active battles (keyed by user id)
active_battles = {}


class BattleMode(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="battle")
    async def battle(self, ctx: commands.Context):
        """
        Command to open the battle menu.
        """
        view = battle_ui.BattleMenuView()
        await ctx.send("Choose your battle mode:", view=view)

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        # Check if the interaction is one of our battle mode buttons
        custom_id = interaction.data.get("custom_id", "")
        if custom_id.startswith("battle_") and custom_id != "battle_attack":
            mode = custom_id.split("_")[1]  # e.g. "friendly", "rival", etc.
            # Create a new battle state based on the mode
            battle_state = self.create_battle_state(interaction.user.id, mode)
            active_battles[interaction.user.id] = battle_state
            # Respond with a battle initiation message and an Attack button view
            await interaction.response.send_message(
                f"Battle mode **{mode.capitalize()}** selected.\n"
                f"Your mon: **{battle_state.player_mon['name']}** (HP: {battle_state.player_mon['hp']}).\n"
                f"Opponent mon: **{battle_state.opponent_mon['name']}** (HP: {battle_state.opponent_mon['hp']}).\n"
                "Click the button below to attack!",
                view=BattleActionView(battle_state),
                ephemeral=True
            )

    def create_battle_state(self, user_id: int, mode: str) -> battle_core.BattleState:
        """
        Creates a new BattleState with dummy mon data.
        Adjust stats based on battle mode as needed.
        """
        # Example dummy data for player and opponent mons
        player_mon = {"name": "Pika", "hp": 100, "attack": 30, "defense": 20}
        opponent_mon = {"name": "RivalMon", "hp": 100, "attack": 25, "defense": 15}
        if mode == "friendly":
            opponent_mon["hp"] = 80
        elif mode == "rival":
            opponent_mon["hp"] = 120
        elif mode == "custom":
            opponent_mon["hp"] = 100
        elif mode == "frontier":
            opponent_mon["hp"] = 150
        elif mode == "gym":
            opponent_mon["hp"] = 130
        return battle_core.BattleState(user_id, player_mon, opponent_mon, mode)


class BattleActionView(discord.ui.View):
    """
    A view that contains an Attack button to allow the player to submit an attack.
    """

    def __init__(self, battle_state: battle_core.BattleState, timeout: float = 180):
        super().__init__(timeout=timeout)
        self.battle_state = battle_state
        self.add_item(BattleAttackButton())


class BattleAttackButton(discord.ui.Button):
    """
    A button that, when clicked, opens the attack submission modal.
    """

    def __init__(self):
        super().__init__(label="Attack", style=discord.ButtonStyle.success, custom_id="battle_attack")

    async def callback(self, interaction: discord.Interaction):
        # When the Attack button is clicked, show the AttackSubmissionModal.
        await interaction.response.send_modal(battle_ui.AttackSubmissionModal())


def setup(bot):
    bot.add_cog(BattleMode(bot))
