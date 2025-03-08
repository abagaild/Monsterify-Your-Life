import discord
import logging
from discord.ui import Modal, TextInput

from core.database import fetch_trainer_by_name, fetch_mon_by_name
from logic.trade_mons import trade_mon
from logic.trade_items import trade_item

class TradeMonsModal(Modal, title="Trade Mons"):
    offering_trainer = TextInput(
        label="Offering Trainer Name",
        placeholder="Enter offering trainer's name",
        required=True
    )
    receiving_trainer = TextInput(
        label="Receiving Trainer Name",
        placeholder="Enter receiving trainer's name",
        required=True
    )
    offering_mon = TextInput(
        label="Offering Mon (ID or Name)",
        placeholder="Enter the mon you are offering (leave empty for gift)",
        required=False
    )
    receiving_mon = TextInput(
        label="Receiving Mon (ID or Name)",
        placeholder="Enter the mon you are receiving (leave empty for gift)",
        required=False
    )

    async def on_submit(self, interaction: discord.Interaction):
        offer_trainer_name = self.offering_trainer.value.strip()
        receive_trainer_name = self.receiving_trainer.value.strip()
        offer_mon_input = self.offering_mon.value.strip()
        receive_mon_input = self.receiving_mon.value.strip()

        # Lookup trainers using the backend function.
        offering_trainer = fetch_trainer_by_name(offer_trainer_name)
        receiving_trainer = fetch_trainer_by_name(receive_trainer_name)
        if not offering_trainer:
            await interaction.response.send_message(
                f"Offering trainer '{offer_trainer_name}' not found.", ephemeral=True)
            return
        if not receiving_trainer:
            await interaction.response.send_message(
                f"Receiving trainer '{receive_trainer_name}' not found.", ephemeral=True)
            return

        messages = []

        # Process trade: move mon from offering trainer to receiving trainer.
        if offer_mon_input:
            try:
                # First, try interpreting the input as an integer mon ID.
                mon_id = int(offer_mon_input)
                success, msg = trade_mon(
                    mon_id=mon_id,
                    from_trainer_id=offering_trainer["id"],
                    to_trainer_id=receiving_trainer["id"]
                )
            except ValueError:
                # If not an integer, treat the input as a mon name.
                mon_record = fetch_mon_by_name(offer_trainer_name, offer_mon_input)
                if not mon_record:
                    success, msg = False, f"Mon '{offer_mon_input}' not found for trainer '{offer_trainer_name}'."
                else:
                    success, msg = trade_mon(
                        mon_id=mon_record["id"],
                        from_trainer_id=offering_trainer["id"],
                        to_trainer_id=receiving_trainer["id"]
                    )
            messages.append(f"Offering Trade: {msg}")

        # Process trade: move mon from receiving trainer to offering trainer.
        if receive_mon_input:
            try:
                mon_id = int(receive_mon_input)
                success, msg = trade_mon(
                    mon_id=mon_id,
                    from_trainer_id=receiving_trainer["id"],
                    to_trainer_id=offering_trainer["id"]
                )
            except ValueError:
                mon_record = fetch_mon_by_name(receive_trainer_name, receive_mon_input)
                if not mon_record:
                    success, msg = False, f"Mon '{receive_mon_input}' not found for trainer '{receive_trainer_name}'."
                else:
                    success, msg = trade_mon(
                        mon_id=mon_record["id"],
                        from_trainer_id=receiving_trainer["id"],
                        to_trainer_id=offering_trainer["id"]
                    )
            messages.append(f"Receiving Trade: {msg}")

        if not offer_mon_input and not receive_mon_input:
            messages.append("No mon trade specified.")

        # The trade functions update the database and trigger Google Sheets sync via notify_sheet_update.
        await interaction.response.send_message("\n".join(messages), ephemeral=True)


class TradeItemsModal(Modal, title="Trade Items"):
    offering_trainer = TextInput(
        label="Offering Trainer Name",
        placeholder="Enter offering trainer's name",
        required=True
    )
    receiving_trainer = TextInput(
        label="Receiving Trainer Name",
        placeholder="Enter receiving trainer's name",
        required=True
    )
    offering_item = TextInput(
        label="Offering Item (Name,Quantity)",
        placeholder="e.g., Health Potion, 3 (leave empty for gift)",
        required=False
    )
    receiving_item = TextInput(
        label="Receiving Item (Name,Quantity)",
        placeholder="e.g., Mana Potion, 2 (leave empty for gift)",
        required=False
    )

    async def on_submit(self, interaction: discord.Interaction):
        offer_trainer_name = self.offering_trainer.value.strip()
        receive_trainer_name = self.receiving_trainer.value.strip()
        offer_item_input = self.offering_item.value.strip()
        receive_item_input = self.receiving_item.value.strip()

        offering_trainer = fetch_trainer_by_name(offer_trainer_name)
        receiving_trainer = fetch_trainer_by_name(receive_trainer_name)
        if not offering_trainer:
            await interaction.response.send_message(
                f"Offering trainer '{offer_trainer_name}' not found.", ephemeral=True)
            return
        if not receiving_trainer:
            await interaction.response.send_message(
                f"Receiving trainer '{receive_trainer_name}' not found.", ephemeral=True)
            return

        messages = []

        # Process item trade: from offering trainer to receiving trainer.
        if offer_item_input:
            parts = [p.strip() for p in offer_item_input.split(",")]
            if len(parts) < 2:
                messages.append("Invalid format for offering item. Use 'Item Name, Quantity'.")
            else:
                item_name = parts[0]
                try:
                    quantity = int(parts[1])
                    success, msg = trade_item(
                        item_name=item_name,
                        quantity=quantity,
                        from_trainer_id=offering_trainer["id"],
                        to_trainer_id=receiving_trainer["id"]
                    )
                except ValueError:
                    success, msg = False, "Quantity must be an integer."
                messages.append(f"Offering Trade: {msg}")

        # Process item trade: from receiving trainer to offering trainer.
        if receive_item_input:
            parts = [p.strip() for p in receive_item_input.split(",")]
            if len(parts) < 2:
                messages.append("Invalid format for receiving item. Use 'Item Name, Quantity'.")
            else:
                item_name = parts[0]
                try:
                    quantity = int(parts[1])
                    success, msg = trade_item(
                        item_name=item_name,
                        quantity=quantity,
                        from_trainer_id=receiving_trainer["id"],
                        to_trainer_id=offering_trainer["id"]
                    )
                except ValueError:
                    success, msg = False, "Quantity must be an integer."
                messages.append(f"Receiving Trade: {msg}")

        if not offer_item_input and not receive_item_input:
            messages.append("No item trade specified.")

        # Inventory adjustments trigger backend Google Sheets sync via inventory update functions.
        await interaction.response.send_message("\n".join(messages), ephemeral=True)
