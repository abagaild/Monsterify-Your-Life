import discord
import random
from discord.ui import View, Modal, TextInput, Button
from views.market.generic_shop import send_generic_shop_view

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
            exclude_categories=["special", "pastry", "berry", "egg", "stone"]
        )

    @discord.ui.button(label="Use Items", style=discord.ButtonStyle.secondary, custom_id="megamart_activity")
    async def activity_button(self, interaction: discord.Interaction, button: Button):
        await send_use_items_view(interaction, self.user_id)

async def send_megamart_view(interaction: discord.Interaction, user_id: str):
    view = MegamartShopView(user_id)
    embed = discord.Embed(title="Megamart", description=view.message, color=discord.Color.teal())
    embed.set_image(url=view.image)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

# Use Items activity for Megamart.
class UseItemsModal(Modal, title="Use Items"):
    trainer_name = TextInput(
        label="Trainer Name",
        placeholder="Enter your trainer's name",
        required=True
    )
    item_usage = TextInput(
        label="Items to Use",
        placeholder="Format: Potion:2, Elixir:1",
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        trainer = self.trainer_name.value.strip()
        usage_data = {}
        for entry in self.item_usage.value.split(","):
            try:
                item, qty = entry.split(":")
                usage_data[item.strip()] = int(qty.strip())
            except Exception:
                continue
        from logic.market.megamart import use_items_action
        result = await use_items_action(interaction, trainer, usage_data)
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
        description="Enter your trainer name and specify the items (with quantities) you wish to use to remove them from your inventory.",
        color=discord.Color.purple()
    )
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
