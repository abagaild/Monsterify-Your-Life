import discord
from discord.ext import commands
from Google_Sheets.google_sheets_authentication import (
    update_trainer_information,
    update_inventory,
    update_unlocks,
    update_mon_data,
    update_move_data,
    gc,
    get_mons_for_trainer
)
from core.database import fetch_trainer_by_name

# This view defines a set of buttons for forcing manual updates.
class AdminUpdateView(discord.ui.View):
    def __init__(self, trainer: dict):
        super().__init__(timeout=180)
        self.trainer = trainer

    async def open_sheet(self):
        sheet_name = self.trainer.get("character_name", "")
        try:
            ss = gc.open(sheet_name)
            return ss
        except Exception as e:
            raise Exception(f"Error opening spreadsheet '{sheet_name}': {e}")

    @discord.ui.button(label="Update Trainer Data", style=discord.ButtonStyle.primary)
    async def update_trainer(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Defer the response so the interaction token doesn't expire
        await interaction.response.defer(ephemeral=True)
        try:
            ss = await self.open_sheet()
            try:
                ws_info = ss.worksheet("Trainer Data")
            except Exception:
                ws_info = ss.add_worksheet(title="Trainer Data", rows="100", cols="50")
            update_trainer_information(ws_info, self.trainer)
            await interaction.followup.send("Trainer Data Updated.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"Error updating trainer data: {e}", ephemeral=True)

    @discord.ui.button(label="Update Inventory", style=discord.ButtonStyle.primary)
    async def update_inventory_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        try:
            ss = await self.open_sheet()
            try:
                ws_inv = ss.worksheet("Item Data")
            except Exception:
                ws_inv = ss.add_worksheet(title="Item Data", rows="100", cols="10")
            update_inventory(ws_inv, self.trainer.get("inventory", "{}"))
            await interaction.followup.send("Inventory Updated.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"Error updating inventory: {e}", ephemeral=True)

    @discord.ui.button(label="Update Mon Data", style=discord.ButtonStyle.primary)
    async def update_mon_data_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        try:
            ss = await self.open_sheet()
            mons = get_mons_for_trainer(self.trainer["id"])
            try:
                ws_mon_data = ss.worksheet("Mon Data")
            except Exception:
                ws_mon_data = ss.add_worksheet(title="Mon Data", rows="100", cols="50")
            update_mon_data(ws_mon_data, mons)
            await interaction.followup.send("Mon Data Updated.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"Error updating mon data: {e}", ephemeral=True)

    @discord.ui.button(label="Update Move Data", style=discord.ButtonStyle.primary)
    async def update_move_data_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        try:
            ss = await self.open_sheet()
            mons = get_mons_for_trainer(self.trainer["id"])
            try:
                ws_move_data = ss.worksheet("Move Data")
            except Exception:
                ws_move_data = ss.add_worksheet(title="Move Data", rows="100", cols="50")
            update_move_data(ws_move_data, mons)
            await interaction.followup.send("Move Data Updated.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"Error updating move data: {e}", ephemeral=True)

    @discord.ui.button(label="Update Unlocks", style=discord.ButtonStyle.primary)
    async def update_unlocks_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        try:
            ss = await self.open_sheet()
            try:
                ws_unlocks = ss.worksheet("Unlocks")
            except Exception:
                ws_unlocks = ss.add_worksheet(title="Unlocks", rows="10", cols="10")
            update_unlocks(ws_unlocks, self.trainer)
            await interaction.followup.send("Unlocks Updated.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"Error updating unlocks: {e}", ephemeral=True)

# Admin command using a text command (triggered with !admin_update)
class AdminCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="admin_update")
    @commands.is_owner()  # Change this check if needed to match your admin list
    async def admin_update(self, ctx: commands.Context, *, trainer_name: str):
        """
        Admin command to manually force a Google Sheet update.
        Usage: !admin_update <trainer_name>
        """
        trainer = fetch_trainer_by_name(trainer_name)
        if not trainer:
            await ctx.send(f"Trainer '{trainer_name}' not found.")
            return

        view = AdminUpdateView(trainer)
        await ctx.send(f"Manual update actions for trainer '{trainer_name}':", view=view)

def setup(bot: commands.Bot):
    bot.add_cog(AdminCommands(bot))