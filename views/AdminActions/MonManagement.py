import discord
from discord.ui import View, Button, Modal, TextInput
from core.database import cursor, db, add_mon_to_db, update_mon_data
from core.google_sheets import append_mon_to_sheet, update_mon_sheet_data, get_mon_sheet_row


# Helper to list all mons in the database with trainer info.
def get_all_mons():
    query = """
        SELECT m.id, t.name, m.mon_name, m.level, m.attribute, m.img_link
        FROM mons m
        LEFT JOIN trainers t ON m.trainer_id = t.id
    """
    cursor.execute(query)
    rows = cursor.fetchall()
    mons = []
    for row in rows:
        mons.append({
            "id": row[0],
            "trainer_name": row[1] if row[1] else "N/A",
            "mon_name": row[2],
            "level": row[3],
            "attribute": row[4],
            "img_link": row[5]
        })
    return mons


# Modal to add a new mon with species and types fields.
class AddMonModal(Modal, title="Add New Mon"):
    trainer_id = TextInput(label="Trainer ID", placeholder="Enter the trainer's numeric ID", required=True)
    player_id = TextInput(label="Player ID", placeholder="Enter the owner's Discord ID", required=True)
    mon_name = TextInput(label="Mon Name", placeholder="Enter the mon's name", required=True)
    level = TextInput(label="Level", placeholder="Enter initial level (default 1)", required=False)
    attribute = TextInput(label="Attribute", placeholder="Enter attribute (default 'Free')", required=False)
    img_link = TextInput(label="Image Link", placeholder="Optional image URL", required=False)
    species = TextInput(label="Species", placeholder="Enter species, separated by commas (max 3)", required=False)
    types = TextInput(label="Types", placeholder="Enter types, separated by commas (max 5)", required=False)

    async def on_submit(self, interaction: discord.Interaction):
        # Validate and parse inputs.
        try:
            trainer_id_val = int(self.trainer_id.value.strip())
        except ValueError:
            await interaction.response.send_message("Invalid Trainer ID.", ephemeral=True)
            return
        player_id_val = self.player_id.value.strip()
        mon_name_val = self.mon_name.value.strip()
        try:
            level_val = int(self.level.value.strip()) if self.level.value.strip() else 1
        except ValueError:
            level_val = 1
        attribute_val = self.attribute.value.strip() if self.attribute.value.strip() else "Free"
        img_link_val = self.img_link.value.strip() if self.img_link.value.strip() else ""

        # Parse species input (max 3).
        species_input = self.species.value.strip()
        species_list = [s.strip() for s in species_input.split(",")] if species_input else []
        species1 = species_list[0] if len(species_list) > 0 else mon_name_val
        species2 = species_list[1] if len(species_list) > 1 else ""
        species3 = species_list[2] if len(species_list) > 2 else ""

        # Parse types input (max 5).
        types_input = self.types.value.strip()
        types_list = [t.strip() for t in types_input.split(",")] if types_input else []
        type1 = types_list[0] if len(types_list) > 0 else "Normal"
        type2 = types_list[1] if len(types_list) > 1 else ""
        type3 = types_list[2] if len(types_list) > 2 else ""
        type4 = types_list[3] if len(types_list) > 3 else ""
        type5 = types_list[4] if len(types_list) > 4 else ""

        # Add mon to the database.
        add_mon_to_db(
            trainer_id=trainer_id_val,
            player=player_id_val,
            mon_name=mon_name_val,
            level=level_val,
            species1=species1,
            species2=species2,
            species3=species3,
            type1=type1,
            type2=type2,
            type3=type3,
            type4=type4,
            type5=type5,
            attribute=attribute_val,
            img_link=img_link_val
        )

        # Fetch trainer name from the database.
        cursor.execute("SELECT name FROM trainers WHERE id = ?", (trainer_id_val,))
        trainer_row = cursor.fetchone()
        if trainer_row:
            trainer_name = trainer_row[0]
        else:
            trainer_name = "Unknown Trainer"

        # Prepare sheet row in the expected format:
        # ["", mon_name, "", species1, species2, species3, type1, type2, type3, type4, type5, attribute, "", img_link]
        sheet_row = ["", mon_name_val, "", species1, species2, species3,
                     type1, type2, type3, type4, type5, attribute_val, "", img_link_val]
        # Update the trainer's Google Sheet.
        error = await append_mon_to_sheet(trainer_name, sheet_row)
        if error:
            await interaction.response.send_message(f"Mon added but failed to update sheet: {error}", ephemeral=True)
        else:
            await interaction.response.send_message(
                f"Mon '{mon_name_val}' added under Trainer ID {trainer_id_val} with level {level_val}.",
                ephemeral=True
            )


# Modal to edit an existing mon with species and types update fields.
class EditMonModal(Modal, title="Edit Mon"):
    mon_id = TextInput(label="Mon ID", placeholder="Enter the mon's ID", required=True)
    new_level = TextInput(label="New Level", placeholder="Enter new level (optional)", required=False)
    new_attribute = TextInput(label="New Attribute", placeholder="Enter new attribute (optional)", required=False)
    new_img_link = TextInput(label="New Image Link", placeholder="Enter new image URL (optional)", required=False)
    new_species = TextInput(label="New Species", placeholder="Enter new species, comma-separated (max 3)",
                            required=False)
    new_types = TextInput(label="New Types", placeholder="Enter new types, comma-separated (max 5)", required=False)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            mon_id_val = int(self.mon_id.value.strip())
        except ValueError:
            await interaction.response.send_message("Invalid Mon ID.", ephemeral=True)
            return

        updates = {}
        sheet_updates = {}
        if self.new_level.value.strip():
            try:
                updates["level"] = int(self.new_level.value.strip())
            except ValueError:
                await interaction.response.send_message("Invalid level value.", ephemeral=True)
                return
        if self.new_attribute.value.strip():
            attr = self.new_attribute.value.strip()
            updates["attribute"] = attr
            sheet_updates[13] = attr  # Column 13: attribute
        if self.new_img_link.value.strip():
            img = self.new_img_link.value.strip()
            updates["img_link"] = img
            sheet_updates[15] = img  # Column 15: image link
        if self.new_species.value.strip():
            species_list = [s.strip() for s in self.new_species.value.strip().split(",")]
            updates["species1"] = species_list[0] if len(species_list) > 0 else ""
            updates["species2"] = species_list[1] if len(species_list) > 1 else ""
            updates["species3"] = species_list[2] if len(species_list) > 2 else ""
            sheet_updates[5] = updates["species1"]  # Column 5: species1
            sheet_updates[6] = updates["species2"]  # Column 6: species2
            sheet_updates[7] = updates["species3"]  # Column 7: species3
        if self.new_types.value.strip():
            types_list = [t.strip() for t in self.new_types.value.strip().split(",")]
            updates["type1"] = types_list[0] if len(types_list) > 0 else ""
            updates["type2"] = types_list[1] if len(types_list) > 1 else ""
            updates["type3"] = types_list[2] if len(types_list) > 2 else ""
            updates["type4"] = types_list[3] if len(types_list) > 3 else ""
            updates["type5"] = types_list[4] if len(types_list) > 4 else ""
            sheet_updates[8] = updates["type1"]  # Column 8: type1
            sheet_updates[9] = updates["type2"]  # Column 9: type2
            sheet_updates[10] = updates["type3"]  # Column 10: type3
            sheet_updates[11] = updates["type4"]  # Column 11: type4
            sheet_updates[12] = updates["type5"]  # Column 12: type5

        if not updates:
            await interaction.response.send_message("No updates provided.", ephemeral=True)
            return

        update_mon_data(mon_id_val, **updates)
        # Query the DB for the mon's current details to obtain trainer name and mon name.
        query = """
            SELECT t.name, m.mon_name 
            FROM mons m 
            JOIN trainers t ON m.trainer_id = t.id 
            WHERE m.id = ?
        """
        cursor.execute(query, (mon_id_val,))
        row = cursor.fetchone()
        if row:
            trainer_name, mon_name_val = row
        else:
            trainer_name, mon_name_val = "Unknown Trainer", "Unknown Mon"

        # Update the Google Sheet using update_mon_sheet_data.
        # This function expects a dictionary mapping column numbers to new values.
        # We update only the fields provided.
        success = await update_mon_sheet_data(trainer_name, mon_name_val, sheet_updates)
        if success:
            await interaction.response.send_message(f"Mon ID {mon_id_val} updated with {updates}.", ephemeral=True)
        else:
            await interaction.response.send_message("Mon updated in DB but failed to update sheet.", ephemeral=True)


# Modal to delete a mon (clears sheet row before deletion).
class DeleteMonModal(Modal, title="Delete Mon"):
    mon_id = TextInput(label="Mon ID", placeholder="Enter the mon's ID to delete", required=True)
    confirmation = TextInput(label="Type YES to confirm", placeholder="YES", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        if self.confirmation.value.strip().upper() != "YES":
            await interaction.response.send_message("Deletion cancelled.", ephemeral=True)
            return
        try:
            mon_id_val = int(self.mon_id.value.strip())
        except ValueError:
            await interaction.response.send_message("Invalid Mon ID.", ephemeral=True)
            return

        # Attempt to retrieve trainer name and mon name before deletion.
        query = """
            SELECT t.name, m.mon_name 
            FROM mons m 
            JOIN trainers t ON m.trainer_id = t.id 
            WHERE m.id = ?
        """
        cursor.execute(query, (mon_id_val,))
        row = cursor.fetchone()
        if row:
            trainer_name, mon_name_val = row
            # Prepare a blank update to clear the sheet fields.
            clear_data = {2: "", 5: "", 6: "", 7: "", 8: "", 9: "", 10: "", 11: "", 12: "", 13: "", 15: ""}
            await update_mon_sheet_data(trainer_name, mon_name_val, clear_data)
        else:
            trainer_name, mon_name_val = None, None

        cursor.execute("DELETE FROM mons WHERE id = ?", (mon_id_val,))
        db.commit()
        await interaction.response.send_message(f"Mon ID {mon_id_val} deleted.", ephemeral=True)


# Main Mon Management admin view.
class MonManagementView(View):
    def __init__(self):
        super().__init__(timeout=None)

    async def refresh_list(self, interaction: discord.Interaction):
        mons = get_all_mons()
        if not mons:
            description = "No mons found."
        else:
            description = "\n".join(
                [
                    f"ID: {m['id']} | Trainer: {m['trainer_name']} | Name: {m['mon_name']} | Level: {m['level']} | "
                    f"Attribute: {m['attribute']} | Img: {m['img_link']}"
                    for m in mons
                ]
            )
        embed = discord.Embed(title="All Mons", description=description, color=discord.Color.orange())
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="List Mons", style=discord.ButtonStyle.secondary, custom_id="list_mons", row=0)
    async def list_mons(self, interaction: discord.Interaction, button: Button):
        await self.refresh_list(interaction)

    @discord.ui.button(label="Add Mon", style=discord.ButtonStyle.primary, custom_id="add_mon", row=1)
    async def add_mon(self, interaction: discord.Interaction, button: Button):
        modal = AddMonModal()
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Edit Mon", style=discord.ButtonStyle.primary, custom_id="edit_mon", row=1)
    async def edit_mon(self, interaction: discord.Interaction, button: Button):
        modal = EditMonModal()
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Delete Mon", style=discord.ButtonStyle.danger, custom_id="delete_mon", row=1)
    async def delete_mon(self, interaction: discord.Interaction, button: Button):
        modal = DeleteMonModal()
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Refresh List", style=discord.ButtonStyle.secondary, custom_id="refresh_mons", row=2)
    async def refresh_button(self, interaction: discord.Interaction, button: Button):
        await self.refresh_list(interaction)
