import discord
from discord.ui import View, Select, Button
import random
from logic import mission as logic_missions
from views.mainMenu import MainMenuView  # for returning to menu

MISSION_SELECT_IMAGE = "https://example.com/mission_select.png"  # update with your actual image URL
MISSION_PROGRESS_IMAGES = {
    "in_progress": "https://example.com/mission_in_progress.png",
    "complete": "https://example.com/mission_complete.png"
}
MISSION_FLAVOR_TEXTS = [
    "Adventure awaits!",
    "The journey is just beginning.",
    "Your expedition unfolds..."
]

def get_missions_embed(user_id: str) -> discord.Embed:
    """
    Returns an embed for the missions interface.
    If an active mission exists, it shows progress; otherwise, a mission selection prompt.
    """
    active = logic_missions.get_active_mission(user_id)
    if active:
        title = f"Active Mission: {active['mission_name']}"
        progress = active.get("current_progress", 0)
        required = active.get("required_progress", 0)
        description = f"Progress: {progress} / {required}\n{active.get('flavor', '')}"
        image = active["artwork"].get("complete" if active.get("complete", False) else "in_progress",
                                      MISSION_PROGRESS_IMAGES["in_progress"])
    else:
        title = "Select Your Mission"
        description = "Choose a mission to embark on your next adventure."
        image = MISSION_SELECT_IMAGE
    embed = discord.Embed(title=title, description=description, color=discord.Color.gold())
    embed.set_image(url=image)
    embed.set_footer(text=random.choice(MISSION_FLAVOR_TEXTS))
    return embed

class MissionsInterfaceView(View):
    """
    Top-level missions view. When a player clicks 'missions', this view is launched.
    If the player has an active mission, it shows mission progress; otherwise, it shows available missions.
    """
    def __init__(self, user_id: str):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.active_mission = logic_missions.get_active_mission(user_id)
        if self.active_mission:
            # Active mission: show progress view.
            self.add_item(IncreaseProgressButton())
            self.add_item(ClaimRewardsButton())
            self.add_item(ReturnToMenuButton())
        else:
            # No active mission: show mission selection view.
            missions = logic_missions.fetch_missions(user_id)
            if missions:
                options = []
                for mission in missions:
                    label = mission.get("name", "Unnamed Mission").strip() or "Unnamed Mission"
                    desc = (mission.get("flavor", "")[:50].strip() or "N/A")
                    options.append(discord.SelectOption(label=label, value=str(mission["id"]), description=desc))
                self.add_item(MissionSelect(options, user_id))
            else:
                # No missions available
                self.add_item(Button(label="No missions available", style=discord.ButtonStyle.danger, disabled=True))
            self.add_item(ReturnToMenuButton())

    def get_embed(self) -> discord.Embed:
        return get_missions_embed(self.user_id)

class MissionSelect(Select):
    """
    Dropdown select listing available missions.
    """
    def __init__(self, options, user_id: str):
        super().__init__(placeholder="Select a mission", min_values=1, max_values=1, options=options, custom_id="mission_select")
        self.user_id = user_id

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            mission_id = int(self.values[0])
        except ValueError:
            await interaction.followup.send("Invalid mission selection.", ephemeral=True)
            return
        mission = next((m for m in logic_missions.fetch_missions(self.user_id) if m["id"] == mission_id), None)
        if not mission:
            await interaction.followup.send("Mission not found.", ephemeral=True)
            return
        viable_mons = logic_missions.get_viable_mons(self.user_id, mission)
        if not viable_mons:
            await interaction.followup.send("You have no viable mons for this mission. Choose another mission.", ephemeral=True)
            return
        # Launch the mission mons selection view.
        view = MissionMonsSelectView(self.user_id, mission, viable_mons)
        await interaction.followup.send("Select up to three mons to send on this mission:", view=view, ephemeral=True)

class MissionMonsSelectView(View):
    """
    Displays a multi-select dropdown listing viable mons for the selected mission.
    """
    def __init__(self, user_id: str, mission: dict, viable_mons: list):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.mission = mission
        self.viable_mons = viable_mons
        options = []
        for mon in viable_mons:
            label = mon.get("mon_name", "Unknown Mon").strip() or "Unknown Mon"
            options.append(discord.SelectOption(label=label, value=mon.get("mon_name", "Unknown Mon")))
        self.add_item(MissionMonsSelect(options, user_id, mission))

class MissionMonsSelect(Select):
    """
    Multi-select dropdown allowing selection of 1 to 3 mons.
    """
    def __init__(self, options, user_id: str, mission: dict):
        super().__init__(placeholder="Select mons (1-3)", min_values=1, max_values=3, options=options, custom_id="mission_mons_select")
        self.user_id = user_id
        self.mission = mission

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        selected_mons = self.values
        active_mission = logic_missions.start_mission(self.user_id, int(self.mission["id"]), selected_mons)
        if not active_mission:
            await interaction.followup.send("Failed to start mission.", ephemeral=True)
            return
        # Replace the view with a mission progress view.
        new_view = MissionProgressView(self.user_id, active_mission)
        await interaction.followup.send("Mission started! Here is your mission progress:", embed=new_view.get_embed(), view=new_view, ephemeral=True)

class MissionProgressView(View):
    """
    Displays active mission progress with artwork, progress field, and control buttons.
    """
    def __init__(self, user_id: str, mission: dict):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.mission = mission
        self.add_item(IncreaseProgressButton())
        self.add_item(ClaimRewardsButton())
        self.add_item(ReturnToMenuButton())

    def get_embed(self) -> discord.Embed:
        progress = self.mission.get("current_progress", 0)
        required = self.mission.get("required_progress", 0)
        title = f"Mission: {self.mission.get('mission_name', 'Unnamed')}"
        description = f"{self.mission.get('flavor', '')}\nProgress: {progress} / {required}"
        image = (self.mission["artwork"].get("complete", MISSION_PROGRESS_IMAGES["complete"])
                 if self.mission.get("complete", False)
                 else self.mission["artwork"].get("in_progress", MISSION_PROGRESS_IMAGES["in_progress"]))
        embed = discord.Embed(title=title, description=description, color=discord.Color.blue())
        embed.set_image(url=image)
        embed.set_footer(text=random.choice(MISSION_FLAVOR_TEXTS))
        return embed

class IncreaseProgressButton(Button):
    """
    Increases mission progress by a random increment.
    """
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.primary, label="Increase Progress", custom_id="increase_progress")

    async def callback(self, interaction: discord.Interaction):
        increment = random.randint(5, 15)
        updated_mission = logic_missions.progress_mission(self.view.user_id, increment)
        self.view.mission = updated_mission
        message = random.choice([
            "Your expedition team advances steadily.",
            "They push forward with determination.",
            "Step by step, progress is made.",
            "The mission nears its climax!"
        ])
        if updated_mission.get("complete", False):
            message = "Mission complete! Rewards are ready to claim."
            self.view.clear_items()
            self.view.add_item(ClaimRewardsButton())
            self.view.add_item(ReturnToMenuButton())
        await interaction.response.edit_message(embed=self.view.get_embed(), view=self.view)
        await interaction.followup.send(f"{message} (+{increment} progress)", ephemeral=True)

class ClaimRewardsButton(Button):
    """
    Allows the player to claim mission rewards.
    """
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.success, label="Claim Rewards", custom_id="claim_rewards")

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        result = await logic_missions.claim_mission_rewards(interaction, self.view.user_id)
        await interaction.followup.send(f"Rewards claimed! {result}", ephemeral=True)

class ReturnToMenuButton(Button):
    """
    Returns to the main menu.
    """
    def __init__(self, custom_id: str = "return_to_menu"):
        super().__init__(style=discord.ButtonStyle.secondary, label="Return to Menu", custom_id=custom_id)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message("Returning to main menu...", view=MainMenuView(), ephemeral=True)

class StartNewMissionButton(Button):
    """
    Starts a new mission.
    """
    def __init__(self, custom_id: str = "start_new_mission"):
        super().__init__(style=discord.ButtonStyle.primary, label="Start New Mission", custom_id=custom_id)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message("Select a new mission:", view=MissionSelectView(str(interaction.user.id)), ephemeral=True)

class MissionSelectView(View):
    """
    A view that displays a dropdown of available missions (filtered by viability).
    """
    def __init__(self, user_id: str):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.missions = logic_missions.fetch_missions(user_id)
        options = []
        for mission in self.missions:
            label = (mission.get("name", "Unnamed Mission")).strip() or "Unnamed Mission"
            desc = (mission.get("flavor", "")[:50].strip() or "N/A")
            options.append(discord.SelectOption(label=label, value=str(mission["id"]), description=desc))
        self.add_item(MissionSelect(options, user_id))
        self.add_item(ReturnToMenuButton())

    def get_embed(self) -> discord.Embed:
        return get_missions_embed(self.user_id)
