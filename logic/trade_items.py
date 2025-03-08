import logging
from core.database import get_record, get_inventory_quantity, remove_inventory_item, add_inventory_item


def trade_item(item_name: str, quantity: int, from_trainer_id: int, to_trainer_id: int, category: str = "ITEMS") -> (
bool, str):
    """
    Trades items between two trainers.

    Parameters:
      - item_name: The name of the item to trade.
      - quantity: The number of items to trade.
      - from_trainer_id: The ID of the trainer offering the item(s).
      - to_trainer_id: The ID of the receiving trainer.
      - category: The inventory category where the item is stored (default "ITEMS").

    Returns:
      A tuple (success: bool, message: str) indicating whether the trade was successful.

    Process:
      1. Verify that both trainers exist.
      2. Check that the offering trainer has at least the required quantity of the item.
      3. Remove the item(s) from the offering trainer's inventory.
      4. Add the item(s) to the receiving trainer's inventory.
      5. If adding fails, roll back the removal.
    """
    # Verify the offering trainer exists
    from_trainer = get_record("trainers", from_trainer_id)
    if not from_trainer:
        return False, "Offering trainer not found."

    # Verify the receiving trainer exists
    to_trainer = get_record("trainers", to_trainer_id)
    if not to_trainer:
        return False, "Receiving trainer not found."

    # Check if the offering trainer has enough of the item
    available_qty = get_inventory_quantity(from_trainer_id, category, item_name)
    if available_qty < quantity:
        return False, f"Not enough '{item_name}' to trade. Available: {available_qty}, required: {quantity}."

    # Remove items from the offering trainer's inventory
    if not remove_inventory_item(from_trainer_id, category, item_name, quantity):
        return False, "Failed to remove items from offering trainer."

    # Add items to the receiving trainer's inventory
    if not add_inventory_item(to_trainer_id, category, item_name, quantity):
        # Roll back removal if adding fails
        add_inventory_item(from_trainer_id, category, item_name, quantity)
        return False, "Failed to add items to receiving trainer."

    return True, "Item trade successful."
