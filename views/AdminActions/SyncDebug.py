import discord
from discord.ui import View, Button, Modal, TextInput
from core.database import cursor, db
from core.google_sheets import (
    sync_sheets,
    get_mon_sheet_row,
    update_trainer_sheet_data,
    update_mon_sheet_data
)


# Modal to get a specific mon's sheet row.
class GetMonSheetRowModal(Modal, title="Get Mon Sheet Row"):
    trainer_name = TextInput(label="Trainer Name", placeholder="Enter trainer's name (sheet title)", required=True)
    mon_name = TextInput(label="Mon Name", placeholder="Enter the mon's name", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        trainer_name_val = self.trainer_name.value.strip()
        mon_name_val = self.mon_name.value.strip()
        mon_details, header, row_number = await get_mon_sheet_row(trainer_name_val, mon_name_val)
        if mon_details is None:
            await interaction.response.send_message("Mon not found in sheet.", ephemeral=True)
            return
        description = "\n".join([f"**{h}:** {value}" for h, value in zip(header, mon_details)])
        embed = discord.Embed(title=f"Sheet Row for {mon_name_val}", description=description,
                              color=discord.Color.blue())
        embed.set_footer(text=f"Row Number: {row_number}")
        await interaction.response.send_message(embed=embed, ephemeral=True)


# New: Modal to selectively sync a specific trainer's sheet or a single mon.
class SyncSpecificSheetModal(Modal, title="Selective Sync"):
    trainer_name = TextInput(label="Trainer Name", placeholder="Enter trainer's name (sheet title)", required=True)
    mon_name = TextInput(label="Mon Name (optional)", placeholder="Enter a mon's name to sync only that mon",
                         required=False)

    async def on_submit(self, interaction: discord.Interaction):
        trainer_name_val = self.trainer_name.value.strip()
        mon_name_val = self.mon_name.value.strip()

        if not mon_name_val:
            # Sync the entire trainer's sheet.
            cursor.execute("SELECT id, user_id, name, level, img_link FROM trainers WHERE name = ?",
                           (trainer_name_val,))
            trainer_row = cursor.fetchone()
            if not trainer_row:
                await interaction.response.send_message(f"No trainer found with name '{trainer_name_val}'.",
                                                        ephemeral=True)
                return
            trainer_id, user_id, name, level, img_link = trainer_row
            trainer_data = {"B3": name, "B8": str(trainer_id), "B52": img_link}
            success_trainer = await update_trainer_sheet_data(trainer_name_val, trainer_data)

            cursor.execute(
                "SELECT mon_name, level, species1, species2, species3, type1, type2, type3, type4, type5, attribute, img_link FROM mons WHERE trainer_id = ?",
                (trainer_id,))
            mon_rows = cursor.fetchall()
            errors = []
            for mon in mon_rows:
                mon_name_db, mon_level, species1, species2, species3, type1, type2, type3, type4, type5, attribute, mon_img_link = mon
                update_dict = {
                    2: mon_name_db,
                    5: species1,
                    6: species2 or "",
                    7: species3 or "",
                    8: type1,
                    9: type2 or "",
                    10: type3 or "",
                    11: type4 or "",
                    12: type5 or "",
                    13: attribute,
                    15: mon_img_link or ""
                }
                success_mon = await update_mon_sheet_data(trainer_name_val, mon_name_db, update_dict)
                if not success_mon:
                    errors.append(mon_name_db)
            if errors:
                await interaction.response.send_message(
                    f"Selective sync completed for trainer '{trainer_name_val}', but failed for mons: {', '.join(errors)}",
                    ephemeral=True)
            else:
                await interaction.response.send_message(f"Selective sync completed for trainer '{trainer_name_val}'.",
                                                        ephemeral=True)
        else:
            # Sync only a single mon.
            cursor.execute(
                "SELECT t.name, m.mon_name FROM mons m JOIN trainers t ON m.trainer_id = t.id WHERE t.name = ? AND m.mon_name = ?",
                (trainer_name_val, mon_name_val))
            mon_data = cursor.fetchone()
            if not mon_data:
                await interaction.response.send_message(
                    f"Mon '{mon_name_val}' not found for trainer '{trainer_name_val}'.", ephemeral=True)
                return
            trainer_name_db, mon_name_db = mon_data
            update_dict = {}
            cursor.execute(
                "SELECT level, species1, species2, species3, type1, type2, type3, type4, type5, attribute, img_link FROM mons WHERE mon_name = ? AND trainer_id = (SELECT id FROM trainers WHERE name = ?)",
                (mon_name_val, trainer_name_val))
            row = cursor.fetchone()
            if row:
                (mon_level, species1, species2, species3, type1, type2, type3, type4, type5, attribute,
                 mon_img_link) = row
                update_dict = {
                    2: mon_name_db,
                    5: species1,
                    6: species2 or "",
                    7: species3 or "",
                    8: type1,
                    9: type2 or "",
                    10: type3 or "",
                    11: type4 or "",
                    12: type5 or "",
                    13: attribute,
                    15: mon_img_link or ""
                }
            success = await update_mon_sheet_data(trainer_name_val, mon_name_db, update_dict)
            if success:
                await interaction.response.send_message(
                    f"Selective sync completed for mon '{mon_name_val}' on trainer '{trainer_name_val}'.",
                    ephemeral=True)
            else:
                await interaction.response.send_message(
                    f"Failed to sync mon '{mon_name_val}' on trainer '{trainer_name_val}'.", ephemeral=True)


# Main Sheets Sync Debug admin view.
class SheetsSyncDebugView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Sync Sheets Now", style=discord.ButtonStyle.primary, custom_id="sync_sheets_now", row=0)
    async def sync_sheets_now(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(ephemeral=True)
        try:
            await sync_sheets()
            await interaction.followup.send("Sheets synchronized successfully.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"Error during sheets sync: {e}", ephemeral=True)

    @discord.ui.button(label="Get Mon Sheet Row", style=discord.ButtonStyle.primary, custom_id="get_mon_sheet_row",
                       row=0)
    async def get_mon_sheet_row_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(GetMonSheetRowModal())

    @discord.ui.button(label="Selective Sync", style=discord.ButtonStyle.primary, custom_id="selective_sync", row=1)
    async def selective_sync(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(SyncSpecificSheetModal())
