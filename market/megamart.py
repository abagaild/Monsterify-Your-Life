import discord
import discord
import random
from discord.ui import View, Modal, TextInput, Button

from views.generic_shop import send_generic_shop_view

IMAGES = [
    "https://i.imgur.com/83k5ZKf.png"
]
MESSAGES = [
    "Welcome to Megamart—your one-stop shop for magical merchandise!",
    "Discover enchanted items and rare finds at Megamart."
]

async def use_items_action(interaction: discord.Interaction, trainer_name: str, usage_data: dict, category: str) -> str:
    await interaction.response.defer(ephemeral=True)
    used_items = []
    # Use the modern helper with the passed in category (e.g. "ITEMS")
    from core.database import update_character_sheet_item
    for item, amount in usage_data.items():
        success = await update_character_sheet_item(trainer_name, item, -amount, category=category)
        if success:
            used_items.append(f"{amount} {item}")
        else:
            return f"Failed to use {amount} {item}. Please check your inventory."
    return f"You used {', '.join(used_items)}."




class MegamartShopView(discord.ui.View):
    def __init__(self, user_id: str):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.image = random.choice(["https://i.imgur.com/ydK6tDb.png"])
        self.message = "Welcome to Megamart! Here you can purchase various items at competitive prices."

    @discord.ui.button(label="Shop", style=discord.ButtonStyle.primary, custom_id="megamart_shop")
    async def shop_button(self, interaction: discord.Interaction, button: Button):
        await send_generic_shop_view(
            interaction,
            "megamart",
            self.user_id,
            exclude_categories=["special", "pastries", "berry", "egg", "stone"]
        )

    @discord.ui.button(label="Use Items", style=discord.ButtonStyle.secondary, custom_id="megamart_activity")
    async def activity_button(self, interaction: discord.Interaction, button: Button):
        await send_use_items_view(interaction, self.user_id)

async def send_megamart_view(interaction: discord.Interaction, user_id: str):
    view = MegamartShopView(user_id)
    embed = discord.Embed(title="Megamart", description=view.message, color=discord.Color.teal())
    embed.set_image(url=view.image)
    await interaction.followup.send(embed=embed, view=view, ephemeral=True)

# Use Items activity for Megamart.
class UseItemsModal(Modal, title="Use Items"):
    trainer_name = TextInput(
        label="Trainer Name",
        placeholder="Enter your trainer's name",
        required=True
    )
    item_category = TextInput(
        label="Item Category",
        placeholder="Enter the category (e.g., ITEMS)",
        required=True
    )
    item_usage = TextInput(
        label="Items to Use",
        placeholder="Format: Potion:2, Elixir:1",
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        trainer = self.trainer_name.value.strip()
        category = self.item_category.value.strip()
        usage_data = {}
        for entry in self.item_usage.value.split(","):
            try:
                item, qty = entry.split(":")
                usage_data[item.strip()] = int(qty.strip())
            except Exception:
                continue
        result = await use_items_action(interaction, trainer, usage_data, category)
        await interaction.followup.send(result, ephemeral=True)

class UseItemsActivityView(View):
    def __init__(self, user_id: str):
        super().__init__(timeout=None)
        self.user_id = user_id

    @discord.ui.button(label="Start Using Items", style=discord.ButtonStyle.primary, custom_id="use_items_start")
    async def start_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(UseItemsModal())

async def send_use_items_view(interaction: discord.Interaction, user_id: str):
    view = UseItemsActivityView(user_id)
    embed = discord.Embed(
        title="Megamart - Use Items",
        description="Enter your trainer name, the item category, and specify the items (with quantities) you wish to remove from your inventory.",
        color=discord.Color.purple()
    )
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
