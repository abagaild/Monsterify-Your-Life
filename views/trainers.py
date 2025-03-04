import discord
from core.trainer import get_trainer_pages, update_trainer_detail
from core.database import get_trainers_from_db  # updated below to include user_id
from core.core_views import BaseView
import asyncio
import logging

# -------------------------------
# Paginated Trainers View – list trainers.
# -------------------------------
class PaginatedTrainersView(BaseView):
    def __init__(self, trainers: list, editable: bool, user_id: str):
        super().__init__(timeout=None)
        self.trainers = trainers
        self.editable = editable
        self.user_id = user_id
        self.current_index = 0

    async def get_current_embed(self) -> discord.Embed:
        if not self.trainers:
            title = "No Trainers Found" if self.editable else "No Other Trainers Found"
            description = ("You have no trainers registered. Use the trainer add command."
                           if self.editable else "There are no other trainers available.")
            return discord.Embed(title=title, description=description)
        trainer = self.trainers[self.current_index]
        embed = discord.Embed(title=f"Trainer: {trainer['name']}",
                              description=f"Level: {trainer['level']}")
        if trainer.get("img_link"):
            embed.set_image(url=trainer["img_link"])
        embed.set_footer(text=f"Trainer {self.current_index + 1} of {len(self.trainers)}")
        return embed

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.primary, custom_id="trainer_prev", row=0)
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.trainers:
            await interaction.response.send_message("No trainers to display.", ephemeral=True)
            return
        self.current_index = (self.current_index - 1) % len(self.trainers)
        embed = await self.get_current_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.primary, custom_id="trainer_next", row=0)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.trainers:
            await interaction.response.send_message("No trainers to display.", ephemeral=True)
            return
        self.current_index = (self.current_index + 1) % len(self.trainers)
        embed = await self.get_current_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Details", style=discord.ButtonStyle.secondary, custom_id="trainer_details", row=1)
    async def details(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.trainers:
            await interaction.response.send_message("No trainers available.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        trainer = self.trainers[self.current_index]
        if self.editable:
            detail_view = EditableTrainerDetailView(trainer, self.user_id)
        else:
            detail_view = BaseTrainerDetailView(trainer)
        embed = await detail_view.get_page_embed()
        await interaction.followup.send(embed=embed, view=detail_view, ephemeral=True)

    @discord.ui.button(label="Back", style=discord.ButtonStyle.danger, custom_id="trainer_back", row=1)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Returning to main menu...", ephemeral=True)

# -------------------------------
# Base Trainer Detail View – read-only.
# -------------------------------
class BaseTrainerDetailView(BaseView):
    def __init__(self, trainer: dict):
        super().__init__(timeout=None)
        self.trainer = trainer
        self.pages_task = asyncio.create_task(get_trainer_pages(trainer['name']))
        self.current_page = 0

    async def get_page_embed(self) -> discord.Embed:
        # Await the task if not already done.
        if self.pages_task is not None:
            self.pages = await self.pages_task
            self.pages_task = None
        page = self.pages[self.current_page] if self.pages else {"header": "", "items": []}
        embed = discord.Embed(title=f"Trainer Details: {self.trainer['name']}")
        embed.add_field(name="Basic Info", value=f"Level: {self.trainer.get('level', 'N/A')}", inline=True)
        if self.trainer.get("img_link"):
            embed.set_image(url=self.trainer["img_link"])
        if page.get("header"):
            embed.add_field(name="Page Header", value=page["header"], inline=False)
        if page.get("items"):
            details_text = "\n".join(f"**{k}:** {v}" for k, v in page["items"])
            if len(details_text) > 1024:
                details_text = details_text[:1021] + "..."
            embed.add_field(name="Details", value=details_text, inline=False)
        total_pages = len(self.pages) if self.pages else 1
        embed.set_footer(text=f"Page {self.current_page + 1} of {total_pages}")
        return embed

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.primary, custom_id="detail_prev", row=0)
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page > 0:
            self.current_page -= 1
            embed = await self.get_page_embed()
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.send_message("Already at the first page.", ephemeral=True)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.primary, custom_id="detail_next", row=0)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.pages and self.current_page < (len(self.pages) - 1):
            self.current_page += 1
            embed = await self.get_page_embed()
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.send_message("Already at the last page.", ephemeral=True)

    @discord.ui.button(label="Mons", style=discord.ButtonStyle.secondary, custom_id="detail_mons", row=1)
    async def open_mons(self, interaction: discord.Interaction, button: discord.ui.Button):
        from views.mons import TrainerMonsView  # ensure proper import
        view = TrainerMonsView(self.trainer)
        embed = view.get_current_embed()
        await interaction.response.send_message("Trainer's mons:", embed=embed, view=view, ephemeral=True)

    @discord.ui.button(label="Back", style=discord.ButtonStyle.danger, custom_id="detail_back", row=1)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Returning...", ephemeral=True)

# -------------------------------
# Editable Trainer Detail View – for a trainer owned by the current user.
# -------------------------------
class EditableTrainerDetailView(BaseTrainerDetailView):
    def __init__(self, trainer: dict, current_user_id: str):
        super().__init__(trainer)
        self.current_user_id = current_user_id
        # Ensure the trainer dictionary includes the "user_id" key.
        if str(trainer.get("user_id", "")) == current_user_id:
            # Instead of adding TrainerEditView directly, add an Edit button.
            self.add_item(TrainerEditButton(trainer))

# -------------------------------
# Trainer Edit Button – launches the TrainerEditView.
# -------------------------------
class TrainerEditButton(discord.ui.Button):
    def __init__(self, trainer: dict):
        super().__init__(label="Edit", style=discord.ButtonStyle.secondary)
        self.trainer = trainer

    async def callback(self, interaction: discord.Interaction):
        # Instantiate TrainerEditView as a separate view.
        edit_view = TrainerEditView(self.trainer)
        await interaction.response.send_message("Editing trainer details:", view=edit_view, ephemeral=True)

# -------------------------------
# Trainer Edit View – remains as a full view handling editing.
# -------------------------------
class TrainerEditView(BaseView):
    def __init__(self, trainer: dict):
        super().__init__(timeout=120)
        self.trainer = trainer
        # Schedule get_trainer_pages as a task.
        self.pages_task = asyncio.create_task(get_trainer_pages(trainer['name']))
        self.pages = None
        self.options = []
        asyncio.create_task(self.init_options())
        # Add a Back button to return to the trainers view.
        self.add_item(TrainerEditBackButton(trainer))

    async def init_options(self):
        if self.pages_task is not None:
            self.pages = await self.pages_task
            self.pages_task = None
        pages = self.pages if self.pages else []
        current_page_items = pages[0]["items"] if pages else []
        seen = set()
        self.options = []
        for key, _ in current_page_items:
            if key not in seen:
                seen.add(key)
                self.options.append(discord.SelectOption(label=key, value=key))
        if self.options:
            self.add_item(TrainerEditSelect(self.options, self.trainer))

class TrainerEditSelect(discord.ui.Select):
    def __init__(self, options, trainer: dict):
        super().__init__(placeholder="Select a detail to edit", min_values=1, max_values=1, options=options)
        self.trainer = trainer

    async def callback(self, interaction: discord.Interaction):
        selected_key = self.values[0]
        await interaction.response.defer(ephemeral=True)
        await interaction.followup.send(f"Please type the new value for **{selected_key}**", ephemeral=True)
        def check(m):
            return m.author == interaction.user and m.channel == interaction.channel
        try:
            msg = await interaction.client.wait_for("message", check=check, timeout=60)
        except Exception:
            await interaction.followup.send("Timed out waiting for input.", ephemeral=True)
            return
        new_value = msg.content.strip()
        success = await update_trainer_detail(self.trainer['name'], selected_key, new_value)
        if success:
            await interaction.followup.send(f"Updated **{selected_key}** to **{new_value}**.", ephemeral=True)
        else:
            await interaction.followup.send(f"Failed to update **{selected_key}**.", ephemeral=True)

class TrainerEditBackButton(discord.ui.Button):
    def __init__(self, trainer: dict):
        super().__init__(label="Back", style=discord.ButtonStyle.danger)
        self.trainer = trainer

    async def callback(self, interaction: discord.Interaction):
        trainers = get_trainers_from_db(str(interaction.user.id))
        new_view = PaginatedTrainersView(trainers, editable=True, user_id=str(interaction.user.id))
        embed = await new_view.get_current_embed()
        await interaction.response.send_message("Returning to trainers view...", embed=embed, view=new_view, ephemeral=True)
# -------------------------------
# Updated database query function – ensures each trainer includes the "user_id" key.
# -------------------------------
def get_trainers_from_db(user_id: str):
    # This function selects the user_id so that trainer dictionaries include it.
    from core.database import fetch_all
    rows = fetch_all("SELECT id, user_id, name, level, img_link FROM trainers WHERE user_id = ?", (user_id,))
    return [{"id": row[0], "user_id": row[1], "name": row[2], "level": row[3], "img_link": row[4]} for row in rows]
