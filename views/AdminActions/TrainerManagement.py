import discord
from discord.ui import View, Button, Modal, TextInput
from core.database import cursor, db, add_trainer_to_db, update_trainer_data

# Helper: Get all trainers from the database.
def get_all_trainers():
    cursor.execute("SELECT id, user_id, name, level, img_link FROM trainers")
    rows = cursor.fetchall()
    return [
        {"id": row[0], "user_id": row[1], "name": row[2], "level": row[3], "img_link": row[4]}
        for row in rows
    ]

# Modal to add a new trainer.
class AddTrainerModal(Modal, title="Add Trainer"):
    user_id = TextInput(label="User ID", placeholder="Enter the user's ID", required=True)
    trainer_name = TextInput(label="Trainer Name", placeholder="Enter the trainer's name", required=True)
    level = TextInput(label="Level", placeholder="Enter initial level (default 1)", required=False)
    img_link = TextInput(label="Image Link", placeholder="Enter image URL (optional)", required=False)

    async def on_submit(self, interaction: discord.Interaction):
        uid = self.user_id.value.strip()
        name = self.trainer_name.value.strip()
        try:
            level_val = int(self.level.value.strip()) if self.level.value.strip() else 1
        except ValueError:
            level_val = 1
        img = self.img_link.value.strip() if self.img_link.value.strip() else ""
        add_trainer_to_db(uid, name, level_val, img)
        await interaction.response.send_message(
            f"Trainer '{name}' added for user {uid} with level {level_val}.", ephemeral=True
        )

# Modal to edit an existing trainer.
class EditTrainerModal(Modal, title="Edit Trainer"):
    trainer_id = TextInput(label="Trainer ID", placeholder="Enter the trainer's ID", required=True)
    new_level = TextInput(label="New Level", placeholder="Enter new level (leave blank to skip)", required=False)
    new_img_link = TextInput(label="New Image Link", placeholder="Enter new image URL (leave blank to skip)", required=False)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            t_id = int(self.trainer_id.value.strip())
        except ValueError:
            await interaction.response.send_message("Invalid trainer ID.", ephemeral=True)
            return

        updates = {}
        if self.new_level.value.strip():
            try:
                updates["level"] = int(self.new_level.value.strip())
            except ValueError:
                await interaction.response.send_message("Invalid level value.", ephemeral=True)
                return
        if self.new_img_link.value.strip():
            updates["img_link"] = self.new_img_link.value.strip()

        if not updates:
            await interaction.response.send_message("No updates provided.", ephemeral=True)
            return

        update_trainer_data(t_id, **updates)
        await interaction.response.send_message(f"Trainer ID {t_id} updated with {updates}.", ephemeral=True)

# Modal to delete a trainer.
class DeleteTrainerModal(Modal, title="Delete Trainer"):
    trainer_id = TextInput(label="Trainer ID", placeholder="Enter the trainer's ID to delete", required=True)
    confirmation = TextInput(label="Type YES to confirm", placeholder="YES", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        if self.confirmation.value.strip().upper() != "YES":
            await interaction.response.send_message("Deletion cancelled.", ephemeral=True)
            return
        try:
            t_id = int(self.trainer_id.value.strip())
        except ValueError:
            await interaction.response.send_message("Invalid trainer ID.", ephemeral=True)
            return
        # Delete trainer by ID (admin override).
        cursor.execute("DELETE FROM trainers WHERE id = ?", (t_id,))
        db.commit()
        await interaction.response.send_message(f"Trainer ID {t_id} deleted.", ephemeral=True)

# Main Trainer Management admin view.
class TrainerManagementView(View):
    def __init__(self):
        super().__init__(timeout=None)

    # Helper to refresh and display the list of trainers.
    async def refresh_list(self, interaction: discord.Interaction):
        trainers = get_all_trainers()
        if not trainers:
            description = "No trainers found."
        else:
            description = "\n".join(
                [
                    f"ID: {t['id']} | User: {t['user_id']} | Name: {t['name']} | Level: {t['level']} | Img: {t['img_link']}"
                    for t in trainers
                ]
            )
        embed = discord.Embed(title="All Trainers", description=description, color=discord.Color.green())
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="List Trainers", style=discord.ButtonStyle.secondary, custom_id="list_trainers", row=0)
    async def list_trainers(self, interaction: discord.Interaction, button: Button):
        await self.refresh_list(interaction)

    @discord.ui.button(label="Add Trainer", style=discord.ButtonStyle.primary, custom_id="add_trainer", row=1)
    async def add_trainer(self, interaction: discord.Interaction, button: Button):
        modal = AddTrainerModal()
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Edit Trainer", style=discord.ButtonStyle.primary, custom_id="edit_trainer", row=1)
    async def edit_trainer(self, interaction: discord.Interaction, button: Button):
        modal = EditTrainerModal()
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Delete Trainer", style=discord.ButtonStyle.danger, custom_id="delete_trainer", row=1)
    async def delete_trainer(self, interaction: discord.Interaction, button: Button):
        modal = DeleteTrainerModal()
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Refresh List", style=discord.ButtonStyle.secondary, custom_id="refresh_trainers", row=2)
    async def refresh_button(self, interaction: discord.Interaction, button: Button):
        await self.refresh_list(interaction)
