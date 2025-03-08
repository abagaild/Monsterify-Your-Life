import discord
import random
from core.database import update_character_sheet_item, get_trainer_currency, fetch_trainer_by_name
from core.items import get_inventory_quantity
from core.rollmons import get_default_pool, roll_single_mon, register_mon
from data.lists import legendary_list, mythical_list

# --- Helper Function to Roll Mons for Adoption ---
def roll_adoption_mons():
    pool = get_default_pool()
    # Filter out legendaries and mythicals
    legendary_set = {name.lower() for name in legendary_list}
    mythical_set = {name.lower() for name in mythical_list}
    filtered_pool = [
        mon for mon in pool
        if mon["name"].lower() not in legendary_set and mon["name"].lower() not in mythical_set
    ]
    num_to_roll = random.randint(1, 5)
    return [roll_single_mon(filtered_pool) for _ in range(num_to_roll)]

# --- Main Function to Start Adoption Activity ---
async def start_adoption_activity(interaction: discord.Interaction, user_id: str, trainer_id: int, trainer_name: str):
    # Check if the selected trainer has at least one Daycare Daypass.
    daypass_count = get_inventory_quantity(trainer_name, "Daycare Daypass")
    if daypass_count < 1:
        await interaction.response.send_message(
            "You need at least 1 Daycare Daypass in your inventory to adopt a mon.",
            ephemeral=True
        )
        return
    # Roll a random number (1-5) of mons (excluding legendaries/mythicals).
    rolled_mons = roll_adoption_mons()
    # The trainer can only adopt as many mons as they have day passes or rolled mons.
    max_adoptions = min(daypass_count, len(rolled_mons))
    view = AdoptionCenterView(user_id, rolled_mons, max_adoptions, trainer_id, trainer_name)
    embed = discord.Embed(
        title="Adoption Center",
        description=f"You have {daypass_count} Daycare Daypass(es). You can adopt up to {max_adoptions} mon(s).",
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

# --- Trainer Selection Dropdown ---
class AdoptionTrainerSelect(discord.ui.Select):
    def __init__(self, trainers):
        options = [
            discord.SelectOption(label=trainer["character_name"], value=str(trainer["id"]))
            for trainer in trainers
        ]
        super().__init__(placeholder="Select a trainer for adoption", min_values=1, max_values=1, options=options)
        self.trainers = trainers

    async def callback(self, interaction: discord.Interaction):
        selected_trainer_id = int(self.values[0])
        selected_trainer = next((t for t in self.trainers if t["id"] == selected_trainer_id), None)
        if not selected_trainer:
            await interaction.response.send_message("Trainer not found.", ephemeral=True)
            return
        # Start the adoption activity using the selected trainer.
        await start_adoption_activity(interaction, interaction.user.id, selected_trainer["id"], selected_trainer["character_name"])

class AdoptionTrainerSelectView(discord.ui.View):
    def __init__(self, trainers):
        super().__init__(timeout=60)
        self.add_item(AdoptionTrainerSelect(trainers))

# --- Main Adoption Center View ---
class AdoptionCenterView(discord.ui.View):
    def __init__(self, user_id: str, rolled_mons: list, max_adoptions: int, trainer_id: int, trainer_name: str):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.rolled_mons = rolled_mons
        self.remaining_adoptions = max_adoptions
        self.trainer_id = trainer_id
        self.trainer_name = trainer_name
        # Create one button for each rolled mon.
        for i, mon in enumerate(rolled_mons):
            self.add_item(AdoptionButton(mon, i))
        # Add a button to finish the adoption process.
        self.add_item(FinishAdoptionButton())

    async def finish_adoption(self, interaction: discord.Interaction):
        ending_msg = random.choice([
            "Adoption complete! Enjoy your new companion.",
            "The adoption process is finished. Welcome your new family member!"
        ])
        await interaction.response.send_message(ending_msg, ephemeral=True)
        # Transition to another view if desired (e.g. Town Menu).

# --- Adoption Button for Each Rolled Mon ---
class AdoptionButton(discord.ui.Button):
    def __init__(self, mon: dict, index: int):
        label = mon.get("name", f"Mon {index + 1}")
        super().__init__(label=label, style=discord.ButtonStyle.primary)
        self.mon = mon

    async def callback(self, interaction: discord.Interaction):
        trainer_name = self.view.trainer_name
        # Check if the trainer still has at least one Daycare Daypass.
        daypass_count = get_inventory_quantity(trainer_name, "Daycare Daypass")
        if daypass_count < 1:
            await interaction.response.send_message(
                "You no longer have any Daycare Daypass in your inventory.",
                ephemeral=True
            )
            return
        # Remove one Daycare Daypass from the trainer's inventory.
        success = await update_character_sheet_item(trainer_name, "Daycare Daypass", -1)
        if not success:
            await interaction.response.send_message("Failed to remove a Daycare Daypass.", ephemeral=True)
            return
        # Launch the standardized modal for registering a new mon.
        await register_mon(interaction, trainer_name, self.mon, self.mon.get("name", "Unknown"))
        await interaction.followup.send(
            "Adoption successful. One Daycare Daypass has been used.",
            ephemeral=True
        )
        self.view.remaining_adoptions -= 1
        # Optionally disable further adoption if no adoptions remain.
        if self.view.remaining_adoptions <= 0:
            for child in self.view.children:
                if isinstance(child, discord.ui.Button):
                    child.disabled = True
        await interaction.edit_original_response(view=self.view)

# --- Finish Adoption Button ---
class FinishAdoptionButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Finish Adoption", style=discord.ButtonStyle.secondary)

    async def callback(self, interaction: discord.Interaction):
        await self.view.finish_adoption(interaction)

# --- Function to Send the Initial Trainer Selection View ---
async def send_adoption_center_view(interaction: discord.Interaction, user_id: str, trainers: list):
    """
    Begins the adoption center flow by presenting the player with a dropdown of their trainers.
    """
    view = AdoptionTrainerSelectView(trainers)
    embed = discord.Embed(
        title="Adoption Center",
        description="Select a trainer to adopt a new mon.",
        color=discord.Color.orange()
    )
    await interaction.followup.send(embed=embed, view=view, ephemeral=True)
