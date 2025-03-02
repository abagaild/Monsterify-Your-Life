import discord
from discord.ui import View, Button

class AdminActionsView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @staticmethod
    def get_embed() -> discord.Embed:
        """
        Returns an embed for the Admin Actions dashboard.
        """
        embed = discord.Embed(
            title="Admin Actions Dashboard",
            description=(
                "Welcome, Admin!\n\n"
                "Use the buttons below to manage and debug various aspects of Gamify Monster:\n"
                "• Trainer Management, Mon Management, Shop Management,\n"
                "  Mission Management, Boss Management, Minigames Management,\n"
                "  Economy Management, Rollers Testing, Schedule Management,\n"
                "  Sheets Sync Debug, and System Diagnostics."
            ),
            color=discord.Color.dark_blue()
        )
        embed.set_image(url="https://i.imgur.com/yourAdminImage.png")  # Replace with an appropriate URL
        embed.set_footer(text="Use these actions carefully—they affect the backend game state!")
        return embed

    # Row 0
    @discord.ui.button(label="Trainer Management", style=discord.ButtonStyle.primary, custom_id="admin_trainer_mgmt", row=0)
    async def trainer_mgmt(self, interaction: discord.Interaction, button: Button):
        from views import TrainerManagementView  # Ensure this file exists
        view = TrainerManagementView()
        await interaction.response.send_message("Trainer Management Admin Actions:", view=view, ephemeral=True)

    @discord.ui.button(label="Mon Management", style=discord.ButtonStyle.primary, custom_id="admin_mon_mgmt", row=0)
    async def mon_mgmt(self, interaction: discord.Interaction, button: Button):
        from views import MonManagementView  # Ensure this file exists
        view = MonManagementView()
        await interaction.response.send_message("Mon Management Admin Actions:", view=view, ephemeral=True)

    @discord.ui.button(label="Shop Management", style=discord.ButtonStyle.primary, custom_id="admin_shop_mgmt", row=0)
    async def shop_mgmt(self, interaction: discord.Interaction, button: Button):
        from views import ShopManagementView  # Ensure this file exists
        view = ShopManagementView()
        await interaction.response.send_message("Shop Management Admin Actions:", view=view, ephemeral=True)

    # Row 1
    @discord.ui.button(label="Mission Management", style=discord.ButtonStyle.primary, custom_id="admin_mission_mgmt", row=1)
    async def mission_mgmt(self, interaction: discord.Interaction, button: Button):
        from views import MissionManagementView  # Ensure this file exists
        view = MissionManagementView()
        await interaction.response.send_message("Mission Management Admin Actions:", view=view, ephemeral=True)

    @discord.ui.button(label="Boss Management", style=discord.ButtonStyle.primary, custom_id="admin_boss_mgmt", row=1)
    async def boss_mgmt(self, interaction: discord.Interaction, button: Button):
        from views import BossManagementView  # Ensure this file exists
        view = BossManagementView()
        await interaction.response.send_message("Boss Management Admin Actions:", view=view, ephemeral=True)

    @discord.ui.button(label="Minigames Management", style=discord.ButtonStyle.primary, custom_id="admin_minigames_mgmt", row=1)
    async def minigames_mgmt(self, interaction: discord.Interaction, button: Button):
        from views import MinigamesManagementView  # Ensure this file exists
        view = MinigamesManagementView()
        await interaction.response.send_message("Minigames Management Admin Actions:", view=view, ephemeral=True)

    # Row 2
    @discord.ui.button(label="Economy Management", style=discord.ButtonStyle.primary, custom_id="admin_economy_mgmt", row=2)
    async def economy_mgmt(self, interaction: discord.Interaction, button: Button):
        from views import EconomyManagementView  # Ensure this file exists
        view = EconomyManagementView()
        await interaction.response.send_message("Economy Management Admin Actions:", view=view, ephemeral=True)

    @discord.ui.button(label="Rollers Testing", style=discord.ButtonStyle.primary, custom_id="admin_rollers_testing", row=2)
    async def rollers_testing(self, interaction: discord.Interaction, button: Button):
        from views import RollersTestingView  # Ensure this file exists
        view = RollersTestingView()
        await interaction.response.send_message("Rollers Testing Admin Actions:", view=view, ephemeral=True)

    @discord.ui.button(label="Schedule Management", style=discord.ButtonStyle.primary, custom_id="admin_schedule_mgmt", row=2)
    async def schedule_mgmt(self, interaction: discord.Interaction, button: Button):
        from views import ScheduleManagementView  # Ensure this file exists
        view = ScheduleManagementView()
        await interaction.response.send_message("Schedule Management Admin Actions:", view=view, ephemeral=True)

    # Row 3
    @discord.ui.button(label="Sheets Sync Debug", style=discord.ButtonStyle.primary, custom_id="admin_sheets_sync", row=3)
    async def sheets_sync(self, interaction: discord.Interaction, button: Button):
        from views import SheetsSyncDebugView  # Ensure this file exists
        view = SheetsSyncDebugView()
        await interaction.response.send_message("Sheets Sync Debug Admin Actions:", view=view, ephemeral=True)

    @discord.ui.button(label="System Diagnostics", style=discord.ButtonStyle.primary, custom_id="admin_system_diag", row=3)
    async def system_diag(self, interaction: discord.Interaction, button: Button):
        from views import SystemDiagnosticsView  # Ensure this file exists
        view = SystemDiagnosticsView()
        await interaction.response.send_message("System Diagnostics Admin Actions:", view=view, ephemeral=True)
