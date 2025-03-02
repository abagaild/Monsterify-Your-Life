import discord
from discord.ui import View, Button, Modal, TextInput
import json
from core.database import cursor, db


def get_all_missions():
    cursor.execute(
        "SELECT id, name, flavor, requirements, item_rewards, mon_rewards, mon_rewards_params, on_success, on_fail, difficulty, ephemeral, max_mons FROM missions"
    )
    rows = cursor.fetchall()
    missions = []
    for row in rows:
        missions.append({
            "id": row[0],
            "name": row[1],
            "flavor": row[2],
            "requirements": row[3],
            "item_rewards": row[4],
            "mon_rewards": row[5],
            "mon_rewards_params": row[6],
            "on_success": row[7],
            "on_fail": row[8],
            "difficulty": row[9],
            "ephemeral": row[10],
            "max_mons": row[11]
        })
    return missions


# Modal for adding a new mission via JSON input.
class AddMissionModal(Modal, title="Add Mission"):
    mission_data = TextInput(
        label="Mission JSON",
        style=discord.TextStyle.paragraph,
        placeholder='Paste mission JSON here (must include "name")',
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            data = json.loads(self.mission_data.value)
            if "name" not in data:
                await interaction.response.send_message("Mission JSON must include a 'name' field.", ephemeral=True)
                return
            query = """
            INSERT INTO missions (name, flavor, requirements, item_rewards, mon_rewards, mon_rewards_params, on_success, on_fail, difficulty, ephemeral, max_mons)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            params = (
                data.get("name"),
                data.get("flavor", ""),
                data.get("requirements", ""),
                data.get("item_rewards", ""),
                int(data.get("mon_rewards", 0)),
                data.get("mon_rewards_params", ""),
                data.get("on_success", ""),
                data.get("on_fail", ""),
                int(data.get("difficulty", 0)),
                int(data.get("ephemeral", 0)),
                int(data.get("max_mons", 0))
            )
            cursor.execute(query, params)
            db.commit()
            await interaction.response.send_message(f"Mission '{data.get('name')}' added successfully.", ephemeral=True)
        except json.JSONDecodeError:
            await interaction.response.send_message("Invalid JSON format.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Error adding mission: {e}", ephemeral=True)


# Modal for editing an existing mission.
class EditMissionModal(Modal, title="Edit Mission"):
    mission_name = TextInput(
        label="Mission Name",
        placeholder="Enter the mission name to edit",
        required=True
    )
    update_data = TextInput(
        label="Update JSON",
        style=discord.TextStyle.paragraph,
        placeholder='Paste JSON with fields to update',
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        mission_name_val = self.mission_name.value.strip()
        try:
            data = json.loads(self.update_data.value)
        except json.JSONDecodeError:
            await interaction.response.send_message("Invalid JSON format.", ephemeral=True)
            return

        if not data:
            await interaction.response.send_message("No update fields provided.", ephemeral=True)
            return

        fields = []
        values = []
        for key, value in data.items():
            fields.append(f"{key} = ?")
            if key in ["mon_rewards", "difficulty", "ephemeral", "max_mons"]:
                try:
                    values.append(int(value))
                except:
                    values.append(0)
            else:
                values.append(value)
        values.append(mission_name_val)
        query = "UPDATE missions SET " + ", ".join(fields) + " WHERE name = ?"
        try:
            cursor.execute(query, tuple(values))
            db.commit()
            await interaction.response.send_message(f"Mission '{mission_name_val}' updated successfully.",
                                                    ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Error updating mission: {e}", ephemeral=True)


# Modal for deleting a mission.
class DeleteMissionModal(Modal, title="Delete Mission"):
    mission_name = TextInput(
        label="Mission Name",
        placeholder="Enter the mission name to delete",
        required=True
    )
    confirmation = TextInput(
        label="Type YES to confirm",
        placeholder="YES",
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        if self.confirmation.value.strip().upper() != "YES":
            await interaction.response.send_message("Deletion cancelled.", ephemeral=True)
            return
        mission_name_val = self.mission_name.value.strip()
        try:
            cursor.execute("DELETE FROM missions WHERE name = ?", (mission_name_val,))
            db.commit()
            await interaction.response.send_message(f"Mission '{mission_name_val}' deleted successfully.",
                                                    ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Error deleting mission: {e}", ephemeral=True)


# Main Mission Management admin view.
class MissionManagementView(View):
    def __init__(self):
        super().__init__(timeout=None)

    async def refresh_list(self, interaction: discord.Interaction):
        missions = get_all_missions()
        if not missions:
            description = "No missions found."
        else:
            description = "\n".join(
                [
                    f"ID: {m['id']} | Name: {m['name']} | Difficulty: {m['difficulty']} | Max Mons: {m['max_mons']}\n"
                    f"Flavor: {m['flavor']}\nRequirements: {m['requirements']}\n"
                    f"Rewards: {m['item_rewards']}, Mon Rewards: {m['mon_rewards']} ({m['mon_rewards_params']})\n"
                    f"On Success: {m['on_success']}\nOn Fail: {m['on_fail']}\n"
                    f"Ephemeral: {m['ephemeral']}\n"
                    for m in missions
                ]
            )
        embed = discord.Embed(title="All Missions", description=description, color=discord.Color.purple())
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="List Missions", style=discord.ButtonStyle.secondary, custom_id="list_missions", row=0)
    async def list_missions(self, interaction: discord.Interaction, button: Button):
        await self.refresh_list(interaction)

    @discord.ui.button(label="Add Mission", style=discord.ButtonStyle.primary, custom_id="add_mission", row=1)
    async def add_mission(self, interaction: discord.Interaction, button: Button):
        modal = AddMissionModal()
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Edit Mission", style=discord.ButtonStyle.primary, custom_id="edit_mission", row=1)
    async def edit_mission(self, interaction: discord.Interaction, button: Button):
        modal = EditMissionModal()
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Delete Mission", style=discord.ButtonStyle.danger, custom_id="delete_mission", row=1)
    async def delete_mission(self, interaction: discord.Interaction, button: Button):
        modal = DeleteMissionModal()
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Refresh List", style=discord.ButtonStyle.secondary, custom_id="refresh_missions", row=2)
    async def refresh_button(self, interaction: discord.Interaction, button: Button):
        await self.refresh_list(interaction)
