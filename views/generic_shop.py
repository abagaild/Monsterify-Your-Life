import random
import discord
from discord.ui import View, Button, Modal, TextInput, Select
from core.shop import roll_generic_shop_items, purchase_shop_item
from core.database import update_character_sheet_item, get_trainer_currency, get_trainers_from_database

MARKET_IMAGES = [
    "https://example.com/market1.png",
    "https://example.com/market2.png",
    "https://example.com/market3.png",
]
MARKET_MESSAGES = [
    "Welcome to the bustling Market! Explore hidden treasures.",
    "Step into the Market where every corner holds a surprise.",
    "The Market buzzes with life; choose your treasure."
]


class GenericShopPurchaseModal(Modal, title="Purchase Item"):
    quantity = TextInput(
        label="Quantity",
        placeholder="Enter quantity (e.g., 1)",
        required=True
    )
    trainer_sheet = TextInput(
        label="Trainer Sheet",
        placeholder="Enter trainer sheet name for logging",
        required=True
    )

    def __init__(self, shop: str, user_id: str, trainer_id: int, item: dict):
        super().__init__()
        self.shop = shop
        self.user_id = user_id
        self.trainer_id = trainer_id
        self.item = item

    async def on_submit(self, interaction: discord.Interaction):
        try:
            qty = int(self.quantity.value.strip())
        except ValueError:
            await interaction.response.send_message("Invalid quantity. Please enter a number.", ephemeral=True)
            return

        trainer_sheet_name = self.trainer_sheet.value.strip()
        success, msg = await purchase_shop_item(self.shop, self.user_id, self.trainer_id, self.item["name"], qty)
        if success:
            update_success = await update_character_sheet_item(trainer_sheet_name, self.item["name"], qty)
            if update_success:
                msg += f" Purchase logged on {trainer_sheet_name}'s sheet."
            else:
                msg += f" Purchase logged but failed to update sheet."
        await interaction.response.send_message(msg, ephemeral=True)


class GenericShopItemButton(Button):
    def __init__(self, shop: str, user_id: str, item: dict, index: int):
        custom_id = f"{shop}_{index}_{item['name'].replace(' ', '_')}"
        label = f"{item['name']} – {item['price']} coins"
        super().__init__(label=label, style=discord.ButtonStyle.primary, custom_id=custom_id)
        self.shop = shop
        self.user_id = user_id
        self.item = item

    async def callback(self, interaction: discord.Interaction):
        # Use the active trainer ID from the view
        active_trainer_id = self.view.active_trainer_id
        modal = GenericShopPurchaseModal(self.shop, self.user_id, active_trainer_id, self.item)
        await interaction.response.send_modal(modal)


class TrainerSelectDropdown(Select):
    def __init__(self, trainers: list):
        options = []
        for trainer in trainers:
            options.append(discord.SelectOption(label=trainer["character_name"], value=str(trainer["id"])))
        super().__init__(placeholder="Select your trainer", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        selected_trainer_id = int(self.values[0])
        # Update active trainer in the parent view
        for trainer in self.view.trainers:
            if trainer["id"] == selected_trainer_id:
                self.view.active_trainer_id = trainer["id"]
                self.view.active_trainer_name = trainer["character_name"]
                break
        # Update the embed to show the new balance
        new_balance = get_trainer_currency(self.view.active_trainer_id)
        embed = interaction.message.embeds[0].copy()
        # Update or add the "Your Balance" field
        found = False
        for idx, field in enumerate(embed.fields):
            if field.name == "Your Balance":
                embed.set_field_at(idx, name="Your Balance", value=f"{new_balance} coins", inline=False)
                found = True
                break
        if not found:
            embed.add_field(name="Your Balance", value=f"{new_balance} coins", inline=False)
        await interaction.response.edit_message(embed=embed, view=self.view)


class ShopViewWithTrainer(View):
    """
    A view that combines the shop item buttons with a trainer selection dropdown.
    The active trainer’s ID and name are stored on the view.
    """

    def __init__(self, shop: str, user_id: str, items: list, trainers: list):
        super().__init__(timeout=300)
        self.shop = shop
        self.user_id = user_id
        self.items = items
        self.trainers = trainers
        # Set default active trainer as the first trainer.
        self.active_trainer_id = trainers[0]["id"]
        self.active_trainer_name = trainers[0]["character_name"]
        self.add_item(TrainerSelectDropdown(trainers))
        for index, item in enumerate(items):
            self.add_item(GenericShopItemButton(shop, user_id, item, index))


async def send_generic_shop_view(interaction: discord.Interaction, shop: str, user_id: str, category_filter: str = None,
                                 exclude_categories: list = None):
    # Get shop items.
    items = await roll_generic_shop_items(shop, user_id, category_filter=category_filter,
                                          exclude_categories=exclude_categories)
    # Fetch the player's trainers.
    trainers = get_trainers_from_database(user_id)
    if not trainers:
        await interaction.response.send_message("No trainers found. Please create a trainer first.", ephemeral=True)
        return
    # Use the first trainer as default.
    balance = get_trainer_currency(trainers[0]["id"])

    embed = discord.Embed(
        title=f"{shop.title()} Shop",
        description=random.choice(MARKET_MESSAGES),
        color=discord.Color.purple()
    )
    embed.set_image(url=random.choice(MARKET_IMAGES))
    embed.add_field(name="Your Balance", value=f"{balance} coins", inline=False)

    item_lines = []
    for item in items:
        remaining = item["max_purchase"] - item["purchased"]
        effect_text = item.get("effect", f"No effect provided for {item['name']}.")
        item_lines.append(
            f"**{item['name']}**\n_Effect: {effect_text}_\nPrice: {item['price']} coins | Remaining: {remaining}")
    embed.add_field(
        name="Items Available",
        value="\n\n".join(item_lines) if item_lines else "No items available.",
        inline=False
    )
    view = ShopViewWithTrainer(shop, user_id, items, trainers)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
