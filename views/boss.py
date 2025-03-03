import discord
from discord.ui import View, Button
from logic.boss import get_active_boss, claim_boss_rewards

TAUNT_MESSAGES = [
    "Is that all you've got?",
    "You'll need more than that!",
    "Try harder, warrior!",
    "Your attacks are no match for the boss!",
    "Keep hitting—maybe you'll break through!"
]

class BossUIView(View):
    def __init__(self, user_id: str):
        super().__init__(timeout=None)  # Persistent view
        self.user_id = user_id
        # Preload the boss embed immediately
        self.current_embed = self.get_embed()
        self.refresh_view()

    def get_embed(self) -> discord.Embed:
        boss = get_active_boss()
        if boss:
            embed = discord.Embed(
                title=f"Boss Battle: {boss['name']}",
                color=discord.Color.red()
            )
            embed.add_field(name="Health", value=f"{boss['current_health']} / {boss['max_health']}")
            status = "Defeated" if boss["current_health"] <= 0 else "Alive"
            embed.add_field(name="Status", value=status, inline=False)
            embed.set_image(url=boss["image_link"])
            embed.set_footer(text=boss["flavor_text"])
        else:
            embed = discord.Embed(
                title="No Active Boss",
                description="There is currently no boss active.",
                color=discord.Color.green()
            )
        return embed

    def refresh_view(self):
        # Clear any existing buttons and then add the Refresh button.
        self.clear_items()
        self.add_item(RefreshButton())
        # Add Claim Rewards button if there is no active boss or if the boss is defeated.
        boss = get_active_boss()
        if boss is None or boss["current_health"] <= 0:
            self.add_item(ClaimRewardsButton())

    async def refresh(self, interaction: discord.Interaction):
        # Refresh the embed and the view, then update the message.
        self.current_embed = self.get_embed()
        self.refresh_view()
        await interaction.response.edit_message(embed=self.current_embed, view=self)

class RefreshButton(Button):
    def __init__(self):
        super().__init__(label="Refresh", style=discord.ButtonStyle.secondary, custom_id="boss_refresh")
    async def callback(self, interaction: discord.Interaction):
        await self.view.refresh(interaction)

class ClaimRewardsButton(Button):
    def __init__(self):
        super().__init__(label="Claim Rewards", style=discord.ButtonStyle.success, custom_id="boss_claim_rewards")
    async def callback(self, interaction: discord.Interaction):
        msg = await claim_boss_rewards(str(interaction.user.id))
        self.disabled = True
        await self.view.refresh(interaction)
        await interaction.followup.send(content=msg, ephemeral=True)
