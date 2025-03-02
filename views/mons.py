import random
import asyncio
from typing import Any
import discord
from core.database import cursor, db, add_currency, update_mon_in_db, get_mons_for_trainer
from core.google_sheets import append_mon_to_sheet, update_mon_sheet_value, update_character_sheet_level, \
    update_character_sheet_item, get_mon_sheet_row
from data.lists import no_evolution, mythical_list, legendary_list
from logic.market.farm_breeding import get_parent_species
from core.mon import should_ignore_column

# ---------------------------------------------
# Base Mon Detail View (common functionality)
# ---------------------------------------------
class BaseMonDetailView(discord.ui.View):
    """
    Loads a mon’s details from its Google Sheet row and builds an embed.
    This base class is used by both editable (your own) and read-only (others) mon views.
    """
    def __init__(self, trainer: dict, mon: dict):
        super().__init__(timeout=None)
        self.trainer = trainer
        self.mon = mon
        self.mon_details = None
        self.header = None
        self.row_number = None

    async def load_details(self):
        result, header, row_number = await asyncio.to_thread(get_mon_sheet_row, self.trainer['name'], self.mon['mon_name'])
        self.mon_details = result
        self.header = header
        self.row_number = row_number

    async def get_detail_embed(self) -> discord.Embed:
        await self.load_details()
        embed = discord.Embed(title=f"Details for {self.mon['mon_name']}")
        if not self.mon_details or not self.header:
            embed.description = "No details found on the sheet."
        else:
            details = ""
            for idx, key in enumerate(self.header, start=1):
                if should_ignore_column(idx):
                    continue
                value = self.mon_details[idx - 1] if idx - 1 < len(self.mon_details) else ""
                details += f"**{key}:** {value}\n"
            embed.description = details if details else "No details available."
        if self.mon.get("img_link"):
            embed.set_image(url=self.mon["img_link"])
        return embed

# ---------------------------------------------
# Editable Mon Detail View – for your own mons.
# ---------------------------------------------
class MonDetailView(BaseMonDetailView):
    def __init__(self, trainer: dict, mon: dict):
        super().__init__(trainer, mon)
        self.add_item(MonEditInfoButton())
        self.add_item(MonEditDetailsButton())
        self.add_item(MonDetailBackButton())

# ---------------------------------------------
# Read-Only Mon Detail View – for others' mons.
# ---------------------------------------------
class OtherMonDetailView(BaseMonDetailView):
    def __init__(self, trainer: dict, mon: dict):
        super().__init__(trainer, mon)
        self.add_item(MonDetailBackButton())

# ---------------------------------------------
# Mon Detail View Buttons
# ---------------------------------------------
class MonEditInfoButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Edit Information", style=discord.ButtonStyle.secondary)
    async def callback(self, interaction: discord.Interaction):
        view: MonDetailView = self.view  # type: ignore
        # Define allowed fields for basic info editing.
        allowed_fields = {"mon name", "species1", "species2", "species3", "type1", "type2", "type3", "attribute"}
        options = []
        if view.header:
            for idx, key in enumerate(view.header, start=1):
                if key.lower() in allowed_fields:
                    options.append(discord.SelectOption(label=key, value=key))
        if not options:
            await interaction.response.send_message("No editable information fields available.", ephemeral=True)
            return
        edit_view = MonEditSelectView(view.trainer, view.mon['mon_name'], options, parent_view=view)
        await interaction.response.send_message("Select an information field to edit:", view=edit_view, ephemeral=True)

class MonEditDetailsButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Edit Details", style=discord.ButtonStyle.secondary)
    async def callback(self, interaction: discord.Interaction):
        view: MonDetailView = self.view  # type: ignore
        options = []
        if view.header:
            for idx, key in enumerate(view.header, start=1):
                if idx >= 16 and not should_ignore_column(idx):
                    options.append(discord.SelectOption(label=key, value=key))
        if not options:
            await interaction.response.send_message("No editable detail fields available.", ephemeral=True)
            return
        edit_view = MonEditSelectView(view.trainer, view.mon['mon_name'], options, parent_view=view)
        await interaction.response.send_message("Select a detail field to edit:", view=edit_view, ephemeral=True)

class MonDetailBackButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Back", style=discord.ButtonStyle.danger)
    async def callback(self, interaction: discord.Interaction):
        # Return to the trainer’s mons view.
        trainer = self.view.trainer  # type: ignore
        new_view = TrainerMonsView(trainer)
        embed = new_view.get_current_embed()
        await interaction.response.send_message("Returning to mons view...", embed=embed, view=new_view, ephemeral=True)

# ---------------------------------------------
# Base Edit View for Mon Editing (used by both info and details editing)
# ---------------------------------------------
class BaseMonEditView(discord.ui.View):
    def __init__(self, trainer: dict, mon_name: str, options: list, parent_view: BaseMonDetailView):
        super().__init__(timeout=120)
        self.trainer = trainer
        self.mon_name = mon_name
        self.parent_view = parent_view
        self.add_item(MonEditSelect(options, trainer, mon_name, parent_view))
        self.add_item(MonEditBackButton(trainer, mon_name, parent_view))

class MonEditSelect(discord.ui.Select):
    def __init__(self, options, trainer: dict, mon_name: str, parent_view: BaseMonDetailView):
        super().__init__(placeholder="Select a field to edit", min_values=1, max_values=1, options=options)
        self.trainer = trainer
        self.mon_name = mon_name
        self.parent_view = parent_view
    async def callback(self, interaction: discord.Interaction):
        selected_key = self.values[0]
        await interaction.response.send_message(f"Enter the new value for **{selected_key}**:", ephemeral=True)
        def check(m):
            return m.author == interaction.user and m.channel == interaction.channel
        try:
            msg = await interaction.client.wait_for("message", check=check, timeout=60)
        except Exception:
            await interaction.followup.send("Timed out waiting for input.", ephemeral=True)
            return
        new_value = msg.content.strip()
        # Update both the Google Sheet and the database.
        success_sheet = await update_mon_sheet_value(self.trainer['name'], self.mon_name, selected_key, new_value)
        success_db = await update_mon_in_db(self.mon_name, selected_key, new_value, str(interaction.user.id))
        if success_sheet and success_db:
            await interaction.followup.send(f"Updated **{selected_key}** to **{new_value}** successfully.", ephemeral=True)
        elif not success_sheet:
            await interaction.followup.send(f"Failed to update **{selected_key}** in sheet.", ephemeral=True)
        elif not success_db:
            await interaction.followup.send(f"Updated sheet but failed to update database for **{selected_key}**.", ephemeral=True)
        # Refresh the mon detail view.
        new_detail_view = MonDetailView(self.trainer, {"mon_name": self.mon_name, "img_link": self.parent_view.mon.get("img_link", "")})
        embed = await new_detail_view.get_detail_embed()
        await interaction.followup.send("Refreshing details...", embed=embed, view=new_detail_view, ephemeral=True)

class MonEditBackButton(discord.ui.Button):
    def __init__(self, trainer: dict, mon_name: str, parent_view: BaseMonDetailView):
        super().__init__(label="Back", style=discord.ButtonStyle.danger)
        self.trainer = trainer
        self.mon_name = mon_name
        self.parent_view = parent_view
    async def callback(self, interaction: discord.Interaction):
        new_detail_view = MonDetailView(self.trainer, {"mon_name": self.mon_name, "img_link": self.parent_view.mon.get("img_link", "")})
        embed = await new_detail_view.get_detail_embed()
        await interaction.response.send_message("Returning to mon details...", embed=embed, view=new_detail_view, ephemeral=True)

# ---------------------------------------------
# Mon Edit Select View – a convenience view for editing.
# ---------------------------------------------
class MonEditSelectView(BaseMonEditView):
    def __init__(self, trainer: dict, mon_name: str, options: list, parent_view: BaseMonDetailView):
        super().__init__(trainer, mon_name, options, parent_view)

# ---------------------------------------------
# Trainer's Mons View – paginated list of mons.
# ---------------------------------------------
class TrainerMonsView(discord.ui.View):
    def __init__(self, trainer: dict):
        super().__init__(timeout=None)
        self.trainer = trainer
        self.mons = get_mons_for_trainer(trainer['id'])
        self.current_index = 0

    def get_current_embed(self) -> discord.Embed:
        if not self.mons:
            return discord.Embed(title="No Mons Found", description="This trainer has no mons registered.")
        mon = self.mons[self.current_index]
        embed = discord.Embed(title=f"Mon: {mon['mon_name']}", description=f"Level: {mon['level']}")
        if mon.get("img_link"):
            embed.set_image(url=mon["img_link"])
        embed.set_footer(text=f"Mon {self.current_index + 1} of {len(self.mons)}")
        return embed

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.primary, custom_id="mons_prev", row=0)
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.mons:
            await interaction.response.send_message("No mons to display.", ephemeral=True)
            return
        self.current_index = (self.current_index - 1) % len(self.mons)
        embed = self.get_current_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.primary, custom_id="mons_next", row=0)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.mons:
            await interaction.response.send_message("No mons to display.", ephemeral=True)
            return
        self.current_index = (self.current_index + 1) % len(self.mons)
        embed = self.get_current_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Details", style=discord.ButtonStyle.secondary, custom_id="mons_details", row=1)
    async def details(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.mons:
            await interaction.response.send_message("No mons to display.", ephemeral=True)
            return
        mon = self.mons[self.current_index]
        # Check if this mon belongs to the current user.
        current_user = str(interaction.user.id)
        # Assuming mon['player'] is the owner user id.
        if mon.get("player") == current_user:
            detail_view = MonDetailView(self.trainer, mon)
        else:
            detail_view = OtherMonDetailView(self.trainer, mon)
        embed = await detail_view.get_detail_embed()
        await interaction.response.send_message(embed=embed, view=detail_view, ephemeral=True)

    @discord.ui.button(label="Back", style=discord.ButtonStyle.danger, custom_id="mons_back", row=1)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Return to trainer detail view.
        from views.trainers import BaseTrainerDetailView  # ensure proper import
        detail_view = BaseTrainerDetailView(self.trainer)
        embed = detail_view.get_page_embed()
        await interaction.response.send_message("Returning to trainer details...", embed=embed, view=detail_view, ephemeral=True)
