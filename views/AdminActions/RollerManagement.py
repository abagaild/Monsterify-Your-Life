import discord
from discord.ui import View, Button, Modal, TextInput


# Modal to test the item rolling function.
class TestItemRollModal(Modal, title="Test Item Roll"):
    amount = TextInput(
        label="Amount",
        placeholder="Enter number of items to roll",
        required=True
    )
    filter_keyword = TextInput(
        label="Filter Keyword",
        placeholder="Optional: Enter filter keywords (comma-separated)",
        required=False
    )
    game_corner = TextInput(
        label="Game Corner Mode",
        placeholder="Type YES for game corner mode, otherwise leave blank",
        required=False
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            amount_val = int(self.amount.value.strip())
        except ValueError:
            await interaction.response.send_message("Invalid amount.", ephemeral=True)
            return

        filter_keyword_val = self.filter_keyword.value.strip() or None
        game_corner_val = True if self.game_corner.value.strip().upper() == "YES" else False

        # Import and call the roll_items function from your items module.
        from core.items import roll_items
        rolled_items = await roll_items(amount=amount_val, filter_keyword=filter_keyword_val,
                                        game_corner=game_corner_val)

        if not rolled_items:
            message = "No items were rolled."
        else:
            message = "Rolled Items:\n" + "\n".join([f"{i + 1}. {item}" for i, item in enumerate(rolled_items)])
        await interaction.response.send_message(message, ephemeral=True)


# Modal to test the mon rolling function.
class TestMonRollModal(Modal, title="Test Mon Roll"):
    variant = TextInput(
        label="Variant",
        placeholder="Enter variant (e.g., default, egg, breeding, garden, etc.)",
        required=True
    )
    amount = TextInput(
        label="Amount",
        placeholder="Enter number of mons to roll (default 10)",
        required=False
    )
    claim_limit = TextInput(
        label="Claim Limit",
        placeholder="Enter claim limit (default 1)",
        required=False
    )

    async def on_submit(self, interaction: discord.Interaction):
        variant_val = self.variant.value.strip().lower()
        try:
            amount_val = int(self.amount.value.strip()) if self.amount.value.strip() else 10
        except ValueError:
            amount_val = 10
        try:
            claim_limit_val = int(self.claim_limit.value.strip()) if self.claim_limit.value.strip() else 1
        except ValueError:
            claim_limit_val = 1

        # Import and call the roll_mons function from your rollmons module.
        from core.rollmons import roll_mons
        # roll_mons sends its own embed with a claim view.
        await roll_mons(interaction, variant=variant_val, amount=amount_val, claim_limit=claim_limit_val)


# Main Rollers Testing admin view.
class RollersTestingView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Test Item Roll", style=discord.ButtonStyle.primary, custom_id="test_item_roll", row=0)
    async def test_item_roll(self, interaction: discord.Interaction, button: Button):
        modal = TestItemRollModal()
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Test Mon Roll", style=discord.ButtonStyle.primary, custom_id="test_mon_roll", row=0)
    async def test_mon_roll(self, interaction: discord.Interaction, button: Button):
        modal = TestMonRollModal()
        await interaction.response.send_modal(modal)
