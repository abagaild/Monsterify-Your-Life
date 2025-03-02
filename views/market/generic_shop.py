import random
import discord
from discord.ui import View, Button, Modal, TextInput
from core.shop import roll_generic_shop_items, purchase_generic_shop_item
from core.google_sheets import update_character_sheet_item

# Reuse common market messages and images.
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

    def __init__(self, shop: str, user_id: str, item: dict):
        super().__init__()
        self.shop = shop
        self.user_id = user_id
        self.item = item

    async def on_submit(self, interaction: discord.Interaction):
        try:
            qty = int(self.quantity.value.strip())
        except ValueError:
            await interaction.response.send_message("Invalid quantity. Please enter a number.", ephemeral=True)
            return

        trainer_sheet_name = self.trainer_sheet.value.strip()
        success, msg = await purchase_generic_shop_item(self.shop, self.user_id, self.item["name"], qty)
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
        modal = GenericShopPurchaseModal(self.shop, self.user_id, self.item)
        await interaction.response.send_modal(modal)


class GenericShopView(View):
    """
    A views that displays one button per shop item.
    The refresh button has been removed so that the shop rerolls only once per day.
    """

    def __init__(self, shop: str, user_id: str, items: list):
        super().__init__(timeout=300)
        self.shop = shop
        self.user_id = user_id
        self.items = items
        for index, item in enumerate(items):
            self.add_item(GenericShopItemButton(shop, user_id, item, index))


async def send_generic_shop_view(interaction: discord.Interaction, shop: str, user_id: str, category_filter: str = None,
                                 exclude_categories: list = None):
    items = await roll_generic_shop_items(shop, user_id, category_filter=category_filter,
                                          exclude_categories=exclude_categories)
    embed = discord.Embed(
        title=f"{shop.title()} Shop",
        description=random.choice(MARKET_MESSAGES),
        color=discord.Color.purple()
    )
    embed.set_image(url=random.choice(MARKET_IMAGES))
    item_lines = []
    for item in items:
        remaining = item["max_purchase"] - item["purchased"]
        effect_text = item.get("effect", f"Effect of {item['name']}")
        item_lines.append(f"**{item['name']}**\n_{effect_text}_\nPrice: {item['price']} coins | Remaining: {remaining}")
    embed.add_field(
        name="Items Available",
        value="\n\n".join(item_lines) if item_lines else "No items available.",
        inline=False
    )
    view = GenericShopView(shop, user_id, items)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
