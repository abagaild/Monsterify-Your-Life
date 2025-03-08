import logging
from core.database import get_record, update_mon_row, update_trainer_field


def trade_mon(mon_id: int, from_trainer_id: int, to_trainer_id: int) -> (bool, str):
    """
    Trades a mon from one trainer to another.

    Parameters:
      - mon_id: The unique identifier of the mon to trade.
      - from_trainer_id: The ID of the trainer offering the mon.
      - to_trainer_id: The ID of the receiving trainer.

    Returns:
      A tuple (success: bool, message: str) indicating whether the trade was successful.

    Process:
      1. Fetch the mon record by its ID.
      2. Verify that the mon currently belongs to the offering trainer.
      3. Fetch the receiving trainer’s record.
      4. Update the mon record by setting its trainer_id and player_user_id (from the receiving trainer).
      5. Adjust the trainers’ mon counts (if maintained in the database).
    """
    # Fetch the mon record (using the mons table primary key "mon_id")
    mon = get_record("mons", mon_id, id_field="mon_id")
    if not mon:
        return False, "Mon not found."
    if mon.get("trainer_id") != from_trainer_id:
        return False, "The mon does not belong to the offering trainer."

    # Fetch the receiving trainer record
    receiving_trainer = get_record("trainers", to_trainer_id)
    if not receiving_trainer:
        return False, "Receiving trainer not found."

    # Update the mon's trainer_id and player_user_id to match the receiving trainer
    try:
        update_mon_row(mon_id, {
            "trainer_id": to_trainer_id,
            "player_user_id": receiving_trainer.get("player_user_id")
        })
    except Exception as e:
        logging.error("Error updating mon record: %s", e)
        return False, "Failed to update mon record."

    # Update mon counts for both trainers (if maintained)
    # Decrement offering trainer's mon_amount by 1
    offering_trainer = get_record("trainers", from_trainer_id)
    if offering_trainer:
        current_count = offering_trainer.get("mon_amount") or 0
        new_count = max(current_count - 1, 0)
        update_trainer_field(from_trainer_id, "mon_amount", new_count)
    # Increment receiving trainer's mon_amount by 1
    current_count = receiving_trainer.get("mon_amount") or 0
    update_trainer_field(to_trainer_id, "mon_amount", current_count + 1)

    return True, "Mon trade successful."

