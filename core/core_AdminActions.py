import random
import discord
from discord.ext import commands

# Import the actual functions from your modules:
from core.database import (
    add_trainer,
    fetch_trainer_by_name,
    add_mon,
    addsub_trainer_currency,
    get_trainer_currency,
    add_inventory_item,
    remove_inventory_item,
    update_trainer_level,
    update_character_sheet_item, fetch_all, insert_record,
)
from core.rollmons import roll_mon_variant  # assuming you have one for variant rolls

# --- Modals for each operation ---

class RollMonModal(discord.ui.Modal, title="Roll Mons"):
    variant = discord.ui.TextInput(label="Variant", placeholder="e.g., default, egg, legendary", required=True)
    amount = discord.ui.TextInput(label="Amount", placeholder="Enter a number", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            variant = self.variant.value.strip()
            amount = int(self.amount.value.strip())
            # Call the actual roll function; here we call roll_mon_variant from rollmons module.
            # It should return an embed (or you can adapt the result as needed).
            await roll_mon_variant(interaction, variant, amount)
        except Exception as e:
            await interaction.response.send_message(f"Error rolling mons: {e}", ephemeral=True)

class RollItemModal(discord.ui.Modal, title="Roll Items"):
            category = discord.ui.TextInput(label="Category", placeholder="e.g., ITEMS, BALLS, etc.", required=True)
            amount = discord.ui.TextInput(label="Amount", placeholder="Enter a number", required=True)

            async def on_submit(self, interaction: discord.Interaction):
                try:
                    category = self.category.value.strip()
                    amount = int(self.amount.value.strip())
                    # Call the rollitems function from the core.items module.
                    from core.items import roll_items  # Ensures the import is scoped to this function.
                    result = await roll_items(amount, category)
                    await interaction.response.send_message(f"Items rolled successfully: {result}", ephemeral=True)
                except Exception as e:
                    await interaction.response.send_message(f"Error rolling items: {e}", ephemeral=True)

class AddTrainerModal(discord.ui.Modal, title="Add Trainer"):
    trainer_name = discord.ui.TextInput(label="Trainer Name", placeholder="Enter trainer's name", required=True)
    level = discord.ui.TextInput(label="Starting Level", placeholder="Enter starting level (number)", required=True)
    main_ref = discord.ui.TextInput(label="Main Reference", placeholder="Optional reference", required=False)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            user_id = str(interaction.user.id)
            name = self.trainer_name.value.strip()
            level = int(self.level.value.strip())
            main_ref = self.main_ref.value.strip() if self.main_ref.value else ""
            new_id = add_trainer(user_id, name, level, main_ref)
            await interaction.response.send_message(f"Trainer '{name}' added with ID {new_id}.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Error adding trainer: {e}", ephemeral=True)

class AddMonModal(discord.ui.Modal, title="Add Mon"):
    trainer_name = discord.ui.TextInput(label="Trainer Name", placeholder="Enter trainer's name", required=True)
    mon_name = discord.ui.TextInput(label="Mon Name", placeholder="Enter mon's name", required=True)
    level = discord.ui.TextInput(label="Mon Level", placeholder="Enter mon level", required=True)
    species1 = discord.ui.TextInput(label="Species 1", placeholder="Primary species", required=True)
    type1 = discord.ui.TextInput(label="Type 1", placeholder="Primary type", required=True)
    attribute = discord.ui.TextInput(label="Attribute", placeholder="Mon attribute", required=False)
    # Additional fields (species2, species3, type2,... type5) could be added as needed.

    async def on_submit(self, interaction: discord.Interaction):
        try:
            trainer_name = self.trainer_name.value.strip()
            trainer = fetch_trainer_by_name(trainer_name)
            if not trainer:
                await interaction.response.send_message("Trainer not found. Please add the trainer first.", ephemeral=True)
                return
            mon_name = self.mon_name.value.strip()
            level = int(self.level.value.strip())
            species1 = self.species1.value.strip()
            type1 = self.type1.value.strip()
            attribute = self.attribute.value.strip() if self.attribute.value else ""
            # For simplicity, we fill remaining fields with empty strings or defaults.
            new_mon_id = add_mon(
                trainer_id=trainer["id"],
                player=str(interaction.user.id),
                name=mon_name,
                level=level,
                species1=species1,
                species2="",
                species3="",
                type1=type1,
                type2="",
                type3="",
                type4="",
                type5="",
                attribute=attribute,
                img_link=""
            )
            await interaction.response.send_message(f"Mon '{mon_name}' added with ID {new_mon_id}.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Error adding mon: {e}", ephemeral=True)

class UpdateCurrencyModal(discord.ui.Modal, title="Update Currency"):
    trainer_name = discord.ui.TextInput(label="Trainer Name", placeholder="Enter trainer's name", required=True)
    amount = discord.ui.TextInput(label="Amount (use negative to remove)", placeholder="Enter amount", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            trainer_name = self.trainer_name.value.strip()
            trainer = fetch_trainer_by_name(trainer_name)
            if not trainer:
                await interaction.response.send_message("Trainer not found.", ephemeral=True)
                return
            amount = int(self.amount.value.strip())
            new_balance = addsub_trainer_currency(trainer["id"], amount)
            await interaction.response.send_message(f"Trainer '{trainer_name}' new balance: {new_balance} coins.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Error updating currency: {e}", ephemeral=True)

class UpdateInventoryModal(discord.ui.Modal, title="Update Inventory"):
    trainer_name = discord.ui.TextInput(label="Trainer Name", placeholder="Enter trainer's name", required=True)
    category = discord.ui.TextInput(label="Category", placeholder="e.g., ITEMS, BALLS, etc.", required=True)
    item_name = discord.ui.TextInput(label="Item Name", placeholder="Enter item name", required=True)
    quantity = discord.ui.TextInput(label="Quantity (use negative to remove)", placeholder="Enter quantity", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            trainer_name = self.trainer_name.value.strip()
            trainer = fetch_trainer_by_name(trainer_name)
            if not trainer:
                await interaction.response.send_message("Trainer not found.", ephemeral=True)
                return
            category = self.category.value.strip()
            item_name = self.item_name.value.strip()
            quantity = int(self.quantity.value.strip())
            if quantity >= 0:
                success = add_inventory_item(trainer["id"], category, item_name, quantity)
            else:
                success = remove_inventory_item(trainer["id"], category, item_name, -quantity)
            if success:
                await interaction.response.send_message(f"Inventory updated: {quantity} × {item_name} in '{category}'.", ephemeral=True)
            else:
                await interaction.response.send_message("Inventory update failed (possibly insufficient items).", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Error updating inventory: {e}", ephemeral=True)

class AddAllItemsModal(discord.ui.Modal, title="Add All Items (Debug)"):
    trainer_name = discord.ui.TextInput(label="Trainer Name", placeholder="Enter trainer's name", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            trainer_name = self.trainer_name.value.strip()
            trainer = fetch_trainer_by_name(trainer_name)
            if not trainer:
                await interaction.response.send_message("Trainer not found.", ephemeral=True)
                return

            # Fetch all items from the items table.
            rows = fetch_all("SELECT name, category FROM items")
            if not rows:
                await interaction.response.send_message("No items found in the database.", ephemeral=True)
                return

            added_count = 0
            for row in rows:
                item_name = row["name"]
                # Use the item's category if available; otherwise default to "ITEMS"
                category = row["category"] if row["category"] else "ITEMS"
                success = add_inventory_item(trainer["id"], category, item_name, 10)
                if success:
                    added_count += 1

            await interaction.response.send_message(
                f"Debug: Added 10 of each item (total {added_count} items) to trainer '{trainer_name}'.", ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(f"Error adding all items: {e}", ephemeral=True)

class AddBossModal(discord.ui.Modal, title="Add Boss"):
    boss_name = discord.ui.TextInput(label="Boss Name", placeholder="Enter boss name", required=True)
    level = discord.ui.TextInput(label="Level", placeholder="Enter boss level (number)", required=True)
    health = discord.ui.TextInput(label="Health", placeholder="Enter boss health (number)", required=True)
    description = discord.ui.TextInput(
        label="Description",
        placeholder="Enter boss description",
        required=False,
        style=discord.TextStyle.paragraph
    )
    image = discord.ui.TextInput(
        label="Image URL",
        placeholder="Enter boss image URL",
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            boss_name = self.boss_name.value.strip()
            level = int(self.level.value.strip())
            health = int(self.health.value.strip())
            description = self.description.value.strip() if self.description.value else ""
            image = self.image.value.strip() if self.image.value else ""
            new_boss_id = insert_record("boss", {
                "name": boss_name,
                "level": level,
                "health": health,
                "description": description,
                "image": image
            })
            await interaction.response.send_message(f"Boss '{boss_name}' added with ID {new_boss_id}.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Error adding boss: {e}", ephemeral=True)


# --- Admin View with Buttons ---

class AdminDatabaseView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label="Roll Mons", style=discord.ButtonStyle.primary, custom_id="admin_roll_mons")
    async def roll_mons_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = RollMonModal()
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Roll Items", style=discord.ButtonStyle.primary, custom_id="admin_roll_items")
    async def roll_mons_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = RollItemModal()


        await interaction.response.send_modal(modal)


    @discord.ui.button(label="Add Trainer", style=discord.ButtonStyle.primary, custom_id="admin_add_trainer")
    async def add_trainer_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = AddTrainerModal()
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Add Mon", style=discord.ButtonStyle.primary, custom_id="admin_add_mon")
    async def add_mon_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = AddMonModal()
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Update Currency", style=discord.ButtonStyle.success, custom_id="admin_update_currency")
    async def update_currency_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = UpdateCurrencyModal()
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Update Inventory", style=discord.ButtonStyle.success, custom_id="admin_update_inventory")
    async def update_inventory_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = UpdateInventoryModal()
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Add All Items", style=discord.ButtonStyle.danger, custom_id="admin_add_all_items")
    async def add_all_items_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = AddAllItemsModal()
        await interaction.response.send_modal(modal)


    @discord.ui.button(label="Add Boss", style=discord.ButtonStyle.danger, custom_id="admin_add_boss")
    async def add_boss_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = AddBossModal()
        await interaction.response.send_modal(modal)