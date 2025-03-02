import discord
from discord.ui import View, Button, Modal, TextInput
from core.database import cursor, db
from shop import get_today_date, roll_generic_shop_items  # from your shop.py module
import json


# Modal to list today's shop roll for a given shop and user.
class ListShopRollModal(Modal, title="List Shop Roll"):
    shop = TextInput(label="Shop Name", placeholder="Enter shop name (e.g., antique, pirate)", required=True)
    user_id = TextInput(label="User ID", placeholder="Enter the user's Discord ID", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        shop_name = self.shop.value.strip().lower()
        user_id_val = self.user_id.value.strip()
        today = get_today_date()
        cursor.execute(
            "SELECT items FROM generic_shop_rolls WHERE shop=? AND user_id=? AND date=?",
            (shop_name, user_id_val, today)
        )
        row = cursor.fetchone()
        if not row:
            await interaction.response.send_message(
                f"No shop roll found for shop '{shop_name}' and user {user_id_val} for today.", ephemeral=True)
            return
        try:
            items = json.loads(row[0])
            description = "\n".join([
                                        f"{i + 1}. {item['name']} (Price: {item['price']}, Purchased: {item['purchased']}/{item['max_purchase']})"
                                        for i, item in enumerate(items)])
        except Exception as e:
            description = f"Error parsing shop items: {e}"
        embed = discord.Embed(title=f"Shop Roll for '{shop_name}' (User: {user_id_val})", description=description,
                              color=discord.Color.gold())
        await interaction.response.send_message(embed=embed, ephemeral=True)


# Modal to force a reroll of shop items.
class ForceRerollShopModal(Modal, title="Force Reroll Shop Items"):
    shop = TextInput(label="Shop Name", placeholder="Enter shop name (e.g., antique, pirate)", required=True)
    user_id = TextInput(label="User ID", placeholder="Enter the user's Discord ID", required=True)

    # Optionally, you could add a field for category_filter if needed.

    async def on_submit(self, interaction: discord.Interaction):
        shop_name = self.shop.value.strip().lower()
        user_id_val = self.user_id.value.strip()
        # Force a new roll; note: this will delete previous roll for non-today entries
        try:
            items = await roll_generic_shop_items(shop_name, user_id_val)
            if not items:
                description = "No items rolled."
            else:
                description = "\n".join([f"{i + 1}. {item} " for i, item in enumerate(items)])
            embed = discord.Embed(title=f"New Shop Roll for '{shop_name}' (User: {user_id_val})",
                                  description=description, color=discord.Color.green())
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Error during reroll: {e}", ephemeral=True)


# Modal to delete today's shop roll.
class DeleteShopRollModal(Modal, title="Delete Shop Roll"):
    shop = TextInput(label="Shop Name", placeholder="Enter shop name (e.g., antique, pirate)", required=True)
    user_id = TextInput(label="User ID", placeholder="Enter the user's Discord ID", required=True)
    confirmation = TextInput(label="Type YES to confirm", placeholder="YES", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        if self.confirmation.value.strip().upper() != "YES":
            await interaction.response.send_message("Deletion cancelled.", ephemeral=True)
            return
        shop_name = self.shop.value.strip().lower()
        user_id_val = self.user_id.value.strip()
        today = get_today_date()
        cursor.execute(
            "DELETE FROM generic_shop_rolls WHERE shop=? AND user_id=? AND date=?",
            (shop_name, user_id_val, today)
        )
        db.commit()
        await interaction.response.send_message(
            f"Deleted shop roll for '{shop_name}' and user {user_id_val} for today.", ephemeral=True)


# Main Shop Management admin view.
class ShopManagementView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="List Shop Roll", style=discord.ButtonStyle.secondary, custom_id="list_shop_roll", row=0)
    async def list_shop_roll(self, interaction: discord.Interaction, button: Button):
        modal = ListShopRollModal()
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Force Reroll", style=discord.ButtonStyle.primary, custom_id="force_reroll_shop", row=0)
    async def force_reroll_shop(self, interaction: discord.Interaction, button: Button):
        modal = ForceRerollShopModal()
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Delete Shop Roll", style=discord.ButtonStyle.danger, custom_id="delete_shop_roll", row=1)
    async def delete_shop_roll(self, interaction: discord.Interaction, button: Button):
        modal = DeleteShopRollModal()
        await interaction.response.send_modal(modal)
