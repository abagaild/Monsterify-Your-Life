import json
import random
import asyncio
import discord
from typing import Tuple, Any
import logging
from core.database import (
    fetch_mon_by_name, add_mon, update_mon_row, remove_mon, get_mons_for_trainer, update_mon_level,
    addsub_trainer_currency, pool
)
from core.database import update_character_sheet_item
from data.lists import no_evolution, mythical_list, legendary_list

def get_mon(trainer_id: str, name: str) -> dict:
    """
    Retrieves a mon record for the given trainer and mon name.
    """
    return fetch_mon_by_name(trainer_id, name)

def add_new_mon(trainer_id: int, player: str, mon_data: dict) -> int:
    """
    Adds a new mon to the database using validated data.
    """
    return add_mon(
        trainer_id, player, mon_data["name"], mon_data["level"],
        mon_data["species1"], mon_data["species2"], mon_data["species3"],
        mon_data["type1"], mon_data["type2"], mon_data["type3"],
        mon_data["type4"], mon_data["type5"], mon_data["attribute"],
        mon_data.get("img_link", "")
    )

async def assign_levels_to_mon(interaction: discord.Interaction, name: str, levels: int):
    """
    Assigns levels to a mon. If it exceeds level 100, extra levels are converted to currency.
    """
    trainer_id = str(interaction.user.id)
    mon = get_mon(trainer_id, name)

    if not mon:
        await interaction.response.send_message(f"Mon '{name}' not found.", ephemeral=True)
        return

    current_level = mon["level"]
    max_level = 100

    if current_level >= max_level:
        extra_coins = levels * 25
        addsub_trainer_currency(trainer_id, extra_coins)
        await interaction.response.send_message(
            f"Mon '{name}' is at level 100. Converted {levels} level(s) into {extra_coins} coins.",
            ephemeral=True
        )
    elif current_level + levels > max_level:
        effective_levels = max_level - current_level
        excess = levels - effective_levels
        update_mon_level(mon["id"], max_level)
        extra_coins = excess * 25
        addsub_trainer_currency(trainer_id, extra_coins)
        await interaction.response.send_message(
            f"Mon '{name}' reached level 100. Added {effective_levels} levels and converted {excess} levels into {extra_coins} coins.",
            ephemeral=True
        )
    else:
        update_mon_level(mon["id"], current_level + levels)
        await interaction.response.send_message(
            f"Added {levels} levels to mon '{name}'.",
            ephemeral=True
        )

def remove_mon_from_trainer(mon_id: int) -> bool:
    """
    Removes a mon from a trainer.
    """
    return remove_mon(mon_id)

def list_mons(trainer_id: int) -> list:
    """
    Retrieves all mons for the given trainer.
    """
    return get_mons_for_trainer(trainer_id)


def is_mon_viable_for_breeding(mon_id: int) -> bool:
    """
    Determines whether a mon is eligible for breeding by checking its species.
    """
    from core.database import fetch_one
    from data.lists import legendary_list, mythical_list, no_evolution

    # Retrieve the mon record.
    row = fetch_one("SELECT * FROM mons WHERE mon_id = ?", (mon_id,))
    if not row:
        return False

    # Use dictionary-style indexing instead of .get()
    species_fields = [
        (row["species1"] or "").strip(),
        (row["species2"] or "").strip(),
        (row["species3"] or "").strip()
    ]
    # Filter out empty entries.
    species_fields = [s for s in species_fields if s]
    if not species_fields:
        return False

    legendary = {name.lower() for name in legendary_list}
    mythical = {name.lower() for name in mythical_list}
    no_evo = {name.lower() for name in no_evolution}

    for species in species_fields:
        species_lower = species.lower()

        # Check in the Pokemon table.
        poke = fetch_one("SELECT Stage FROM Pokemon WHERE lower(Name) = ?", (species_lower,))
        if poke:
            stage = (poke["Stage"] or "").strip().lower()
            # Legendary or mythical Pokémon cannot breed.
            if species_lower in legendary or species_lower in mythical:
                return False
            # If in no evolution list, it's allowed.
            if species_lower in no_evo:
                continue
            # Allowed if final stage.
            if stage == "final stage":
                continue
            return False

        # Check in the Digimon table.
        digi = fetch_one("SELECT Stage FROM Digimon WHERE lower(Name) = ?", (species_lower,))
        if digi:
            stage = (digi["Stage"] or "").strip().lower()
            if stage in {"training 1", "training 2", "rookie", "hybrid"}:
                return False
            continue

        # Check in the Yo‑kai table.
        yokai = fetch_one('SELECT Rank FROM YoKai WHERE lower(Name) = ?', (species_lower,))
        if yokai:
            continue

        # If species is not found in any table, assume it's not viable.
        return False

    return True


import random

# Global constants for possible types and random attributes.
POSSIBLE_TYPES = [
    "Normal", "Fire", "Water", "Electric", "Grass", "Ice", "Fighting",
    "Poison", "Ground", "Flying", "Psychic", "Bug", "Rock", "Ghost",
    "Dragon", "Dark", "Steel", "Fairy"
]
RANDOM_ATTRIBUTES = ["Free", "Virus", "Data", "Variable"]


def randomize_mon(base_mon: dict, force_min_types: int = None) -> dict:
    """
    Returns a randomized mon based on the provided base_mon template.

    This function ensures:
      - A "name" exists; if not, "Unnamed Mon" is used.
      - The primary species ("species1") is set to the mon's name if not provided.
      - "types" is a list and is expanded if force_min_types is specified.
      - An "attribute" is assigned randomly if not provided.
      - A default level (1) and an empty image link are set if missing.
      - The mon's name is automatically updated to a string in the format:
            species1 / species2 / species3
        using only the nonempty species values.

    Parameters:
      - base_mon (dict): A dictionary containing at least a "name" (optional) and optionally "types".
      - force_min_types (int, optional): Minimum number of types to assign.

    Returns:
      A dictionary representing the randomized mon.
    """
    # Copy base_mon to avoid mutating the original dictionary.
    mon = base_mon.copy()

    # Set species1 to the mon's name if not provided.
    if not mon.get("species1"):
        mon["species1"] = mon["name"]

    # Ensure 'types' exists and is a list.
    if not isinstance(mon.get("types"), list):
        mon["types"] = []

    # If force_min_types is specified, add random types until the minimum is reached.
    if force_min_types is not None:
        while len(mon["types"]) < force_min_types:
            available = [t for t in POSSIBLE_TYPES if t not in mon["types"]]
            if not available:
                break
            mon["types"].append(random.choice(available))

    # If no attribute is provided, assign one at random.
    if not mon.get("attribute"):
        mon["attribute"] = random.choice(RANDOM_ATTRIBUTES)

    # Set default level if not specified.
    if "level" not in mon:
        mon["level"] = 1

    # Set a default image link if not provided.
    if "img_link" not in mon:
        mon["img_link"] = ""

    # Automatically update the mon's name to be a combination of species fields.
    species_list = []
    for key in ["species1", "species2", "species3"]:
        s = mon.get(key, "").strip()
        if s:
            species_list.append(s)
    if species_list:
        mon["name"] = " / ".join(species_list)

    return mon


async def level_up_check_mon(mon_id: int, old_level: int, new_level: int):
    """
    Background function to process a mon's level-up.
    - Increases friendship: 5 + 1 per level gained.
    - For each stat (hp_total, atk_total, def_total, spa_total, spd_total, spe_total),
      increases it by a random amount per level gained (range: EV+IV-15 to EV+IV).
    - For each level gained, with a 20% chance, checks for learning a new move.
      The move learning logic:
         * Determines the mon's types.
         * Queries the "moves" table for moves of type "Normal" or matching one of the mon's types
           that have a level requirement <= new_level.
         * Excludes moves already known (mon's moveset stored as JSON).
         * Randomly selects one move (if available) for each triggered level.
         * Updates the moveset and sends a message listing the newly learned moves.
    """
    # Retrieve the full mon record.
    conn = pool.get_connection()
    try:
        conn.row_factory = lambda cursor, row: {col[0]: row[idx] for idx, col in enumerate(cursor.description)}
        cur = conn.cursor()
        cur.execute("SELECT * FROM mons WHERE mon_id = ?", (mon_id,))
        mon = cur.fetchone()
        if not mon:
            return
    finally:
        pool.return_connection(conn)

    user_id = mon.get("player_user_id", "unknown")
    levels_gained = new_level - old_level

    # Friendship increase: base of 5, plus 1 per level gained.
    current_friendship = mon.get("friendship", 0)
    extra_friendship = 5 + levels_gained
    update_mon_row(mon_id, {"friendship": current_friendship + extra_friendship})
    await send_player_message(user_id, f"Your mon {mon.get('name')} gained {extra_friendship} friendship points.")

    # Stats increase: for each stat, increase by a random amount per level gained.
    stat_fields = ["hp_total", "atk_total", "def_total", "spa_total", "spd_total", "spe_total"]
    stat_updates = {}
    for stat in stat_fields:
        ev_field = stat.replace("total", "ev")
        iv_field = stat.replace("total", "iv")
        ev = mon.get(ev_field, 0)
        iv = mon.get(iv_field, 0)
        total_increase = 0
        for _ in range(levels_gained):
            # Calculate a random increase for this level.
            min_increase = max(ev + iv - 15, 0)
            max_increase = ev + iv
            increase = random.randint(min_increase, max_increase)
            total_increase += increase
        stat_updates[stat] = mon.get(stat, 0) + total_increase
    if stat_updates:
        update_mon_row(mon_id, stat_updates)
        await send_player_message(user_id, f"Your mon {mon.get('name')}'s stats increased: {stat_updates}")

    # Move learning: 20% chance per level gained.
    learned_moves = []
    # Get current moveset.
    current_moveset_str = mon.get("moveset", "[]")
    try:
        current_moveset = json.loads(current_moveset_str)
    except Exception:
        current_moveset = [m.strip() for m in current_moveset_str.split(",") if m.strip()]
    for _ in range(levels_gained):
        if random.random() <= 0.20:
            # Determine mon's types.
            mon_types = []
            for key in ["type1", "type2", "type3", "type4", "type5", "type6"]:
                t = mon.get(key)
                if t:
                    mon_types.append(t)
            # Query the moves table for moves that are either "Normal" or in mon_types and with level_requirement <= new_level.
            conn = pool.get_connection()
            try:
                conn.row_factory = lambda cursor, row: {col[0]: row[idx] for idx, col in enumerate(cursor.description)}
                cur = conn.cursor()
                # Build list of types to search for.
                types_to_search = ["Normal"] + mon_types
                placeholders = ", ".join(["?"] * len(types_to_search))
                query = f"SELECT * FROM moves WHERE type IN ({placeholders}) AND level_requirement <= ?"
                params = types_to_search + [new_level]
                cur.execute(query, tuple(params))
                available_moves = cur.fetchall()
            finally:
                pool.return_connection(conn)
            # Exclude moves already known.
            potential_moves = [m for m in available_moves if m.get("name") not in current_moveset]
            if potential_moves:
                new_move = random.choice(potential_moves)
                current_moveset.append(new_move.get("name"))
                update_mon_row(mon_id, {"moveset": json.dumps(current_moveset)})
                learned_moves.append(new_move.get("name"))
    if learned_moves:
        await send_player_message(user_id, f"Your mon {mon.get('name')} learned new moves: {', '.join(learned_moves)}")