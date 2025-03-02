# logic/submissions.py
import math
from typing import List, Dict


def compute_coins(total_levels: int) -> int:
    """
    Computes the total coins awarded based on the number of levels.

    :param total_levels: The total number of levels earned.
    :return: Total coins, computed as levels * 50.
    """
    return total_levels * 50


def compute_bonus_rolls(total_levels: int) -> int:
    """
    Computes the number of bonus rolls awarded.

    :param total_levels: The total number of levels earned.
    :return: One bonus roll for every 5 levels.
    """
    return total_levels // 5


def assign_levels_to_participants(total_levels: int, participants: List[str]) -> Dict[str, int]:
    """
    Evenly assigns levels to each participant, rounding up as necessary.

    :param total_levels: The total levels available.
    :param participants: A list of participant identifiers (e.g., trainer names).
    :return: A dictionary mapping each participant to the number of levels assigned.
    """
    if not participants:
        return {}
    levels_each = math.ceil(total_levels / len(participants))
    return {participant: levels_each for participant in participants}
