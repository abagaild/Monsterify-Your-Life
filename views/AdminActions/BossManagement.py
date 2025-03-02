import discord
from discord.ui import View, Button, Modal, TextInput
from core.database import cursor, db
# Existing boss functions already in use

# Helper function to retrieve all bosses.
def get_all_bosses():
    cursor.execute(
        "SELECT id, name, max_health, current_health, image_link, flavor_text, is_active FROM boss"
    )
    rows = cursor.fetchall()
    bosses = []
    for row in rows:
        bosses.append({
            "id": row[0],
            "name": row[1],
            "max_health": row[2],
            "current_health": row[3],
            "image_link": row[4] if row[4] else "N/A",
            "flavor_text": row[5] if row[5] else "N/A",
            "is_active": bool(row[6])
        })
    return bosses

# Modal to add a new boss.
class AddBossModal(Modal, title="Add New Boss"):
    name = TextInput(label="Boss Name", placeholder="Enter the boss's name", required=True)
    max_health = TextInput(label="Max Health", placeholder="Enter maximum health (integer)", required=True)
    current_health = TextInput(label="Current Health", placeholder="Enter current health (optional, defaults to max)", required=False)
    image_link = TextInput(label="Image Link", placeholder="Enter image URL (optional)", required=False)
    flavor_text = TextInput(label="Flavor Text", style=discord.TextStyle.paragraph, placeholder="Enter boss flavor text (optional)", required=False)
    is_active = TextInput(label="Active (1 for active, 0 for inactive)", placeholder="Defaults to 1", required=False)

    async def on_submit(self, interaction: discord.Interaction):
        boss_name = self.name.value.strip()
        try:
            max_hp = int(self.max_health.value.strip())
        except ValueError:
            await interaction.response.send_message("Invalid Max Health value.", ephemeral=True)
            return
        current_hp_str = self.current_health.value.strip()
        try:
            current_hp = int(current_hp_str) if current_hp_str else max_hp
        except ValueError:
            current_hp = max_hp
        img = self.image_link.value.strip() if self.image_link.value.strip() else ""
        flavor = self.flavor_text.value.strip() if self.flavor_text.value.strip() else ""
        is_active_str = self.is_active.value.strip()
        try:
            active_val = int(is_active_str) if is_active_str else 1
        except ValueError:
            active_val = 1

        cursor.execute(
            "INSERT INTO boss (name, max_health, current_health, image_link, flavor_text, is_active) VALUES (?, ?, ?, ?, ?, ?)",
            (boss_name, max_hp, current_hp, img, flavor, active_val)
        )
        db.commit()
        await interaction.response.send_message(f"Boss '{boss_name}' added successfully.", ephemeral=True)

# Modal to edit an existing boss.
class EditBossModal(Modal, title="Edit Boss"):
    boss_id = TextInput(label="Boss ID", placeholder="Enter the boss ID", required=True)
    new_name = TextInput(label="New Name", placeholder="Enter new boss name (optional)", required=False)
    new_max_health = TextInput(label="New Max Health", placeholder="Enter new max health (optional)", required=False)
    new_current_health = TextInput(label="New Current Health", placeholder="Enter new current health (optional)", required=False)
    new_image_link = TextInput(label="New Image Link", placeholder="Enter new image URL (optional)", required=False)
    new_flavor_text = TextInput(label="New Flavor Text", style=discord.TextStyle.paragraph, placeholder="Enter new flavor text (optional)", required=False)
    new_is_active = TextInput(label="New Active Status", placeholder="Enter 1 for active or 0 for inactive (optional)", required=False)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            boss_id_val = int(self.boss_id.value.strip())
        except ValueError:
            await interaction.response.send_message("Invalid Boss ID.", ephemeral=True)
            return

        updates = {}
        if self.new_name.value.strip():
            updates["name"] = self.new_name.value.strip()
        if self.new_max_health.value.strip():
            try:
                updates["max_health"] = int(self.new_max_health.value.strip())
            except ValueError:
                await interaction.response.send_message("Invalid max health value.", ephemeral=True)
                return
        if self.new_current_health.value.strip():
            try:
                updates["current_health"] = int(self.new_current_health.value.strip())
            except ValueError:
                await interaction.response.send_message("Invalid current health value.", ephemeral=True)
                return
        if self.new_image_link.value.strip():
            updates["image_link"] = self.new_image_link.value.strip()
        if self.new_flavor_text.value.strip():
            updates["flavor_text"] = self.new_flavor_text.value.strip()
        if self.new_is_active.value.strip():
            try:
                updates["is_active"] = int(self.new_is_active.value.strip())
            except ValueError:
                await interaction.response.send_message("Invalid active status.", ephemeral=True)
                return

        if not updates:
            await interaction.response.send_message("No updates provided.", ephemeral=True)
            return

        fields = []
        values = []
        for key, value in updates.items():
            fields.append(f"{key} = ?")
            values.append(value)
        values.append(boss_id_val)
        query = "UPDATE boss SET " + ", ".join(fields) + " WHERE id = ?"
        cursor.execute(query, tuple(values))
        db.commit()
        await interaction.response.send_message(f"Boss ID {boss_id_val} updated with {updates}.", ephemeral=True)

# Modal to reset a boss's health.
class ResetBossHealthModal(Modal, title="Reset Boss Health"):
    boss_id = TextInput(label="Boss ID", placeholder="Enter the boss ID", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            boss_id_val = int(self.boss_id.value.strip())
        except ValueError:
            await interaction.response.send_message("Invalid Boss ID.", ephemeral=True)
            return
        cursor.execute("SELECT max_health FROM boss WHERE id = ?", (boss_id_val,))
        row = cursor.fetchone()
        if not row:
            await interaction.response.send_message("Boss not found.", ephemeral=True)
            return
        max_hp = row[0]
        cursor.execute("UPDATE boss SET current_health = ? WHERE id = ?", (max_hp, boss_id_val))
        db.commit()
        await interaction.response.send_message(f"Boss ID {boss_id_val} health reset to {max_hp}.", ephemeral=True)

# Modal to toggle a boss's active status.
class ToggleBossActiveModal(Modal, title="Toggle Boss Active Status"):
    boss_id = TextInput(label="Boss ID", placeholder="Enter the boss ID", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            boss_id_val = int(self.boss_id.value.strip())
        except ValueError:
            await interaction.response.send_message("Invalid Boss ID.", ephemeral=True)
            return
        cursor.execute("SELECT is_active FROM boss WHERE id = ?", (boss_id_val,))
        row = cursor.fetchone()
        if not row:
            await interaction.response.send_message("Boss not found.", ephemeral=True)
            return
        current_status = row[0]
        new_status = 0 if current_status else 1
        cursor.execute("UPDATE boss SET is_active = ? WHERE id = ?", (new_status, boss_id_val))
        db.commit()
        status_text = "active" if new_status else "inactive"
        await interaction.response.send_message(f"Boss ID {boss_id_val} is now {status_text}.", ephemeral=True)

# Modal to delete a boss.
class DeleteBossModal(Modal, title="Delete Boss"):
    boss_id = TextInput(label="Boss ID", placeholder="Enter the boss ID to delete", required=True)
    confirmation = TextInput(label="Type YES to confirm", placeholder="YES", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        if self.confirmation.value.strip().upper() != "YES":
            await interaction.response.send_message("Deletion cancelled.", ephemeral=True)
            return
        try:
            boss_id_val = int(self.boss_id.value.strip())
        except ValueError:
            await interaction.response.send_message("Invalid Boss ID.", ephemeral=True)
            return
        cursor.execute("DELETE FROM boss WHERE id = ?", (boss_id_val,))
        db.commit()
        await interaction.response.send_message(f"Boss ID {boss_id_val} deleted.", ephemeral=True)

# --- New: Modal to Force Kill a Boss ---
class ForceKillBossModal(Modal, title="Force Kill Boss"):
    boss_id = TextInput(label="Boss ID", placeholder="Enter the boss ID to force kill", required=True)
    confirmation = TextInput(label="Type FORCE to confirm", placeholder="FORCE", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        if self.confirmation.value.strip().upper() != "FORCE":
            await interaction.response.send_message("Force kill cancelled.", ephemeral=True)
            return
        try:
            boss_id_val = int(self.boss_id.value.strip())
        except ValueError:
            await interaction.response.send_message("Invalid Boss ID.", ephemeral=True)
            return
        # Force kill: set current health to 0 and mark inactive.
        cursor.execute("UPDATE boss SET current_health = 0, is_active = 0 WHERE id = ?", (boss_id_val,))
        db.commit()
        await interaction.response.send_message(f"Boss ID {boss_id_val} force killed (health set to 0 and inactive).", ephemeral=True)

# --- New: Modal to Manually Add Boss Damage ---
class AddBossDamageModal(Modal, title="Add Boss Damage"):
    boss_id = TextInput(label="Boss ID", placeholder="Enter the boss ID", required=True)
    user_id = TextInput(label="User ID", placeholder="Enter the user's Discord ID", required=True)
    damage = TextInput(label="Damage Amount", placeholder="Enter damage amount (integer)", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            boss_id_val = int(self.boss_id.value.strip())
            damage_val = int(self.damage.value.strip())
        except ValueError:
            await interaction.response.send_message("Invalid Boss ID or Damage value.", ephemeral=True)
            return
        user_id_val = self.user_id.value.strip()
        # Insert a damage record.
        cursor.execute("INSERT INTO boss_damage (boss_id, user_id, damage) VALUES (?, ?, ?)", (boss_id_val, user_id_val, damage_val))
        # Update boss health.
        cursor.execute("SELECT current_health FROM boss WHERE id = ?", (boss_id_val,))
        row = cursor.fetchone()
        if not row:
            await interaction.response.send_message("Boss not found.", ephemeral=True)
            return
        current_health = row[0]
        new_health = current_health - damage_val
        if new_health < 0:
            new_health = 0
        cursor.execute("UPDATE boss SET current_health = ? WHERE id = ?", (new_health, boss_id_val))
        db.commit()
        await interaction.response.send_message(
            f"Added damage of {damage_val} to Boss ID {boss_id_val}. New health is {new_health}.", ephemeral=True
        )

# Main Boss Management admin view with new actions.
class BossManagementView(View):
    def __init__(self):
        super().__init__(timeout=None)

    async def refresh_list(self, interaction: discord.Interaction):
        bosses = get_all_bosses()
        if not bosses:
            description = "No bosses found."
        else:
            description = "\n\n".join(
                [
                    f"ID: {b['id']} | Name: {b['name']}\nMax HP: {b['max_health']} | Current HP: {b['current_health']}\n"
                    f"Active: {'Yes' if b['is_active'] else 'No'}\nFlavor: {b['flavor_text']}\nImage: {b['image_link']}"
                    for b in bosses
                ]
            )
        embed = discord.Embed(title="All Bosses", description=description, color=discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="List Bosses", style=discord.ButtonStyle.secondary, custom_id="list_bosses", row=0)
    async def list_bosses(self, interaction: discord.Interaction, button: Button):
        await self.refresh_list(interaction)

    @discord.ui.button(label="Add Boss", style=discord.ButtonStyle.primary, custom_id="add_boss", row=1)
    async def add_boss(self, interaction: discord.Interaction, button: Button):
        modal = AddBossModal()
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Edit Boss", style=discord.ButtonStyle.primary, custom_id="edit_boss", row=1)
    async def edit_boss(self, interaction: discord.Interaction, button: Button):
        modal = EditBossModal()
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Reset Health", style=discord.ButtonStyle.primary, custom_id="reset_boss_health", row=2)
    async def reset_health(self, interaction: discord.Interaction, button: Button):
        modal = ResetBossHealthModal()
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Toggle Active", style=discord.ButtonStyle.primary, custom_id="toggle_boss_active", row=2)
    async def toggle_active(self, interaction: discord.Interaction, button: Button):
        modal = ToggleBossActiveModal()
        await interaction.response.send_modal(modal)

    # New Force Kill action.
    @discord.ui.button(label="Force Kill Boss", style=discord.ButtonStyle.danger, custom_id="force_kill_boss", row=4)
    async def force_kill_boss(self, interaction: discord.Interaction, button: Button):
        modal = ForceKillBossModal()
        await interaction.response.send_modal(modal)

    # New Add Damage action.
    @discord.ui.button(label="Add Boss Damage", style=discord.ButtonStyle.primary, custom_id="add_boss_damage", row=4)
    async def add_boss_damage(self, interaction: discord.Interaction, button: Button):
        modal = AddBossDamageModal()
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Delete Boss", style=discord.ButtonStyle.danger, custom_id="delete_boss", row=3)
    async def delete_boss(self, interaction: discord.Interaction, button: Button):
        modal = DeleteBossModal()
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Refresh List", style=discord.ButtonStyle.secondary, custom_id="refresh_bosses", row=3)
    async def refresh_button(self, interaction: discord.Interaction, button: Button):
        await self.refresh_list(interaction)
