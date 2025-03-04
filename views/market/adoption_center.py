import discord
import random
from logic.market.adoption_center import start_adoption_activity
from core.database import update_character_sheet_item  # updated to use core.database
#from core.rollmons import register_mon  <-- assumed unchanged; ensure it’s up‐to‐date in core.rollmons

class AdoptionCenterView(discord.ui.View):
    def __init__(self, user_id: str, rolled_mons: list, max_adoptions: int):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.rolled_mons = rolled_mons
        self.remaining_adoptions = max_adoptions
        # One button per rolled mon.
        for i, mon in enumerate(rolled_mons):
            self.add_item(AdoptionButton(mon, i))
        # Finish button to complete the adoption activity.
        self.add_item(FinishAdoptionButton())

    async def finish_adoption(self, interaction: discord.Interaction):
        ending_msg = random.choice([
            "Adoption complete! Enjoy your new companion.",
            "The adoption process is finished. Welcome your new family member!"
        ])
        await interaction.response.send_message(ending_msg, ephemeral=True)
        from views.mainMenu import TownMenuView
        channel = interaction.channel
        embed = discord.Embed(title="Visit Town", description="Select a location to visit:", color=discord.Color.blue())
        await channel.send(embed=embed, view=TownMenuView())

class AdoptionButton(discord.ui.Button):
    def __init__(self, mon: dict, index: int):
        label = mon.get("name", f"Mon {index + 1}")
        super().__init__(label=label, style=discord.ButtonStyle.primary)
        self.mon = mon

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message("Enter the trainer name for adoption (using your Daycare Daypass):", ephemeral=True)

        def check(m):
            return m.author.id == interaction.user.id and m.channel.id == interaction.channel.id

        try:
            msg_trainer = await interaction.client.wait_for("message", check=check, timeout=30)
            trainer_name = msg_trainer.content.strip()
        except Exception:
            await interaction.followup.send("Timed out waiting for trainer name. Adoption cancelled.", ephemeral=True)
            return

        from core.rollmons import register_mon
        await register_mon(interaction, self.mon)
        # Use updated database function
        daypass_removed = await update_character_sheet_item(trainer_name, "Daycare Daypass", -1)
        if not daypass_removed:
            await interaction.followup.send("Warning: Failed to remove a Daycare Daypass from your inventory.", ephemeral=True)
        else:
            await interaction.followup.send("One Daycare Daypass has been removed from your inventory.", ephemeral=True)
        self.disabled = True
        await interaction.message.edit(view=self.view)

class FinishAdoptionButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Finish Adoption", style=discord.ButtonStyle.secondary)

    async def callback(self, interaction: discord.Interaction):
        await self.view.finish_adoption(interaction)

class AdoptionTrainerSelectView(discord.ui.View):
    def __init__(self, trainers, user_id: str):
        super().__init__(timeout=60)
        self.user_id = user_id
        options = [discord.SelectOption(label=trainer["name"], value=trainer["name"]) for trainer in trainers]
        self.add_item(AdoptionTrainerSelect(options, user_id))

class AdoptionTrainerSelect(discord.ui.Select):
    def __init__(self, options, user_id: str):
        super().__init__(placeholder="Select a trainer", min_values=1, max_values=1, options=options)
        self.user_id = user_id

    async def callback(self, interaction: discord.Interaction):
        trainer_name = self.values[0]
        await interaction.response.defer(ephemeral=True)
        await start_adoption_activity(interaction, self.user_id, trainer_name)

async def send_adoption_center_view(interaction: discord.Interaction, user_id: str, target_channel: discord.TextChannel):
    """
    Starts the adoption center UI flow.
    """
    await target_channel.send("Starting Adoption Center flow...")
    await start_adoption_activity(interaction, user_id)
