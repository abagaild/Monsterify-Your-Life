import discord
import math
from discord.ui import View, Button, Modal, TextInput
from core.database import cursor, db, add_mon_to_db, update_mon_data

# --- Existing Single Mon Modals ---

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
        # Parse species (comma-separated) and take up to 3 values.
        species_input = self.species.value.strip()
        species_list = [s.strip() for s in species_input.split(",")] if species_input else []
        species1 = species_list[0] if len(species_list) > 0 else mon_name_val
        species2 = species_list[1] if len(species_list) > 1 else ""
        species3 = species_list[2] if len(species_list) > 2 else ""
        # Parse types (comma-separated) and take up to 5 values.
        types_input = self.types.value.strip()
        types_list = [t.strip() for t in types_input.split(",")] if types_input else []
        type1 = types_list[0] if len(types_list) > 0 else "Normal"
        type2 = types_list[1] if len(types_list) > 1 else ""
        type3 = types_list[2] if len(types_list) > 2 else ""
        type4 = types_list[3] if len(types_list) > 3 else ""
        type5 = types_list[4] if len(types_list) > 4 else ""

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
        await interaction.response.send_message(f"Mon '{mon_name_val}' added under Trainer ID {trainer_id_val} with level {level_val}.", ephemeral=True)

class EditMonModal(Modal, title="Edit Mon"):
    mon_id = TextInput(label="Mon ID", placeholder="Enter the mon's ID", required=True)
    new_level = TextInput(label="New Level", placeholder="Enter new level (optional)", required=False)
    new_attribute = TextInput(label="New Attribute", placeholder="Enter new attribute (optional)", required=False)
    new_img_link = TextInput(label="New Image Link", placeholder="Enter new image URL (optional)", required=False)
    new_species = TextInput(label="New Species", placeholder="Enter new species, comma-separated (max 3)", required=False)
    new_types = TextInput(label="New Types", placeholder="Enter new types, comma-separated (max 5)", required=False)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            mon_id_val = int(self.mon_id.value.strip())
        except ValueError:
            await interaction.response.send_message("Invalid Mon ID.", ephemeral=True)
            return

        updates = {}
        if self.new_level.value.strip():
            try:
                updates["level"] = int(self.new_level.value.strip())
            except ValueError:
                await interaction.response.send_message("Invalid level value.", ephemeral=True)
                return
        if self.new_attribute.value.strip():
            updates["attribute"] = self.new_attribute.value.strip()
        if self.new_img_link.value.strip():
            updates["img_link"] = self.new_img_link.value.strip()
        if self.new_species.value.strip():
            species_list = [s.strip() for s in self.new_species.value.strip().split(",")]
            updates["species1"] = species_list[0] if len(species_list) > 0 else ""
            updates["species2"] = species_list[1] if len(species_list) > 1 else ""
            updates["species3"] = species_list[2] if len(species_list) > 2 else ""
        if self.new_types.value.strip():
            types_list = [t.strip() for t in self.new_types.value.strip().split(",")]
            updates["type1"] = types_list[0] if len(types_list) > 0 else ""
            updates["type2"] = types_list[1] if len(types_list) > 1 else ""
            updates["type3"] = types_list[2] if len(types_list) > 2 else ""
            updates["type4"] = types_list[3] if len(types_list) > 3 else ""
            updates["type5"] = types_list[4] if len(types_list) > 4 else ""

        if not updates:
            await interaction.response.send_message("No updates provided.", ephemeral=True)
            return

        update_mon_data(mon_id_val, **updates)
        await interaction.response.send_message(f"Mon ID {mon_id_val} updated with {updates}.", ephemeral=True)

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
        cursor.execute("DELETE FROM mons WHERE id = ?", (mon_id_val,))
        db.commit()
        await interaction.response.send_message(f"Mon ID {mon_id_val} deleted.", ephemeral=True)

# --- New: Bulk Add Mons Modal ---

class BulkAddMonsModal(Modal, title="Bulk Add Mons"):
    trainer_id = TextInput(label="Trainer ID", placeholder="Enter the trainer's numeric ID", required=True)
    player_id = TextInput(label="Player ID", placeholder="Enter the owner's Discord ID", required=True)
    bulk_data = TextInput(
        label="Bulk Mons Data",
        style=discord.TextStyle.paragraph,
        placeholder=(
            "Enter one mon per line in CSV format:\n"
            "mon_name, level, species, types, attribute, img_link\n"
            "• For species and types, you can separate multiple values with a semicolon.\n"
            "• Leave optional fields blank to use defaults."
        ),
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            trainer_id_val = int(self.trainer_id.value.strip())
        except ValueError:
            await interaction.response.send_message("Invalid Trainer ID.", ephemeral=True)
            return
        player_id_val = self.player_id.value.strip()
        bulk_text = self.bulk_data.value.strip()
        if not bulk_text:
            await interaction.response.send_message("No data provided.", ephemeral=True)
            return
        lines = bulk_text.splitlines()
        added = 0
        errors = []
        for i, line in enumerate(lines, start=1):
            # Expect CSV: mon_name, level, species, types, attribute, img_link
            parts = [p.strip() for p in line.split(",")]
            if len(parts) < 1 or not parts[0]:
                errors.append(f"Line {i}: Missing mon name.")
                continue
            mon_name_val = parts[0]
            try:
                level_val = int(parts[1]) if len(parts) > 1 and parts[1] else 1
            except ValueError:
                level_val = 1
            # For species and types, split by semicolon.
            species_list = parts[2].split(";") if len(parts) > 2 and parts[2] else []
            species_list = [s.strip() for s in species_list if s.strip()]
            species1 = species_list[0] if species_list else mon_name_val
            species2 = species_list[1] if len(species_list) > 1 else ""
            species3 = species_list[2] if len(species_list) > 2 else ""
            types_list = parts[3].split(";") if len(parts) > 3 and parts[3] else []
            types_list = [t.strip() for t in types_list if t.strip()]
            type1 = types_list[0] if types_list else "Normal"
            type2 = types_list[1] if len(types_list) > 1 else ""
            type3 = types_list[2] if len(types_list) > 2 else ""
            type4 = types_list[3] if len(types_list) > 3 else ""
            type5 = types_list[4] if len(types_list) > 4 else ""
            attribute_val = parts[4] if len(parts) > 4 and parts[4] else "Free"
            img_link_val = parts[5] if len(parts) > 5 else ""
            try:
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
                added += 1
            except Exception as e:
                errors.append(f"Line {i}: {e}")
        response_text = f"Bulk add complete: {added} mons added."
        if errors:
            response_text += "\nErrors:\n" + "\n".join(errors)
        await interaction.response.send_message(response_text, ephemeral=True)

# --- New: Filtered List Mons Modal with Pagination ---

class FilterMonsModal(Modal, title="Filtered List Mons"):
    trainer_id = TextInput(label="Trainer ID", placeholder="Optional: Enter trainer's numeric ID", required=False)
    player_id = TextInput(label="Player ID", placeholder="Optional: Enter player's Discord ID", required=False)
    page_number = TextInput(label="Page Number", placeholder="Enter page number (default 1)", required=False)

    async def on_submit(self, interaction: discord.Interaction):
        trainer_filter = self.trainer_id.value.strip()
        player_filter = self.player_id.value.strip()
        try:
            page = int(self.page_number.value.strip()) if self.page_number.value.strip() else 1
        except ValueError:
            page = 1
        per_page = 10
        query = "SELECT m.id, t.name, m.mon_name, m.level, m.attribute, m.img_link FROM mons m LEFT JOIN trainers t ON m.trainer_id = t.id"
        filters = []
        params = []
        if trainer_filter:
            filters.append("m.trainer_id = ?")
            try:
                params.append(int(trainer_filter))
            except ValueError:
                await interaction.response.send_message("Invalid Trainer ID filter.", ephemeral=True)
                return
        if player_filter:
            filters.append("m.player = ?")
            params.append(player_filter)
        if filters:
            query += " WHERE " + " AND ".join(filters)
        query += " ORDER BY m.id ASC LIMIT ? OFFSET ?"
        params.extend([per_page, per_page * (page - 1)])
        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()
        if not rows:
            description = "No mons found for the given filters/page."
        else:
            description = "\n".join([
                f"ID: {row[0]} | Trainer: {row[1] if row[1] else 'N/A'} | Name: {row[2]} | Level: {row[3]} | Attr: {row[4]} | Img: {row[5]}"
                for row in rows
            ])
        embed = discord.Embed(title=f"Mon List (Page {page})", description=description, color=discord.Color.orange())
        await interaction.response.send_message(embed=embed, ephemeral=True)

# --- Main Mon Management Admin View with Pagination & Bulk Add ---

class MonManagementView(View):
    def __init__(self):
        super().__init__(timeout=None)

    async def refresh_list(self, interaction: discord.Interaction):
        # Default: list all mons (page 1)
        query = "SELECT m.id, t.name, m.mon_name, m.level, m.attribute, m.img_link FROM mons m LEFT JOIN trainers t ON m.trainer_id = t.id ORDER BY m.id ASC LIMIT 10 OFFSET 0"
        cursor.execute(query)
        rows = cursor.fetchall()
        if not rows:
            description = "No mons found."
        else:
            description = "\n".join(
                [
                    f"ID: {row[0]} | Trainer: {row[1] if row[1] else 'N/A'} | Name: {row[2]} | Level: {row[3]} | Attr: {row[4]} | Img: {row[5]}"
                    for row in rows
                ]
            )
        embed = discord.Embed(title="All Mons (Page 1)", description=description, color=discord.Color.orange())
        await interaction.followup.send(embed=embed, ephemeral=True)

    @discord.ui.button(label="List Mons", style=discord.ButtonStyle.secondary, custom_id="list_mons", row=0)
    async def list_mons(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(ephemeral=True)
        await self.refresh_list(interaction)

    @discord.ui.button(label="Filtered List Mons", style=discord.ButtonStyle.secondary, custom_id="filtered_list_mons", row=0)
    async def filtered_list_mons(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(ephemeral=True)
        modal = FilterMonsModal()
        await interaction.followup.send_modal(modal)

    @discord.ui.button(label="Add Mon", style=discord.ButtonStyle.primary, custom_id="add_mon", row=1)
    async def add_mon(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(ephemeral=True)
        modal = AddMonModal()
        await interaction.followup.send_modal(modal)

    @discord.ui.button(label="Edit Mon", style=discord.ButtonStyle.primary, custom_id="edit_mon", row=1)
    async def edit_mon(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(ephemeral=True)
        modal = EditMonModal()
        await interaction.followup.send_modal(modal)

    @discord.ui.button(label="Delete Mon", style=discord.ButtonStyle.danger, custom_id="delete_mon", row=1)
    async def delete_mon(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(ephemeral=True)
        modal = DeleteMonModal()
        await interaction.followup.send_modal(modal)

    @discord.ui.button(label="Bulk Add Mons", style=discord.ButtonStyle.primary, custom_id="bulk_add_mons", row=2)
    async def bulk_add_mons(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(ephemeral=True)
        modal = BulkAddMonsModal()
        await interaction.followup.send_modal(modal)

    @discord.ui.button(label="Refresh List", style=discord.ButtonStyle.secondary, custom_id="refresh_mons", row=2)
    async def refresh_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(ephemeral=True)
        await self.refresh_list(interaction)
