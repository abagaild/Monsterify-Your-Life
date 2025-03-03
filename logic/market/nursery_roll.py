# nursery_roll.py
"""
Nursery Roll Module: Processes the selected nursery options and adjusts the egg roll accordingly.
It retrieves the egg pool from the rollmons module, applies filters and item effects based on
the player's selections, rolls a set number of mons, and displays the results in an embed with
a claim view.
"""

import discord
from rollmons import get_default_pool, roll_single_mon, build_mon_embed, RollMonsView
import re


def extract_first_word(item_name: str) -> str:
    """Extracts the first word from an item name, used for type overrides."""
    return item_name.split()[0] if item_name else ""


def extract_quantity_from_label(label: str) -> int:
    """Extracts a numerical quantity from an item label formatted with parentheses."""
    match = re.search(r"\((\d+)\)", label)
    if match:
        return int(match.group(1))
    return 1


async def run_nursery_roll(interaction: discord.Interaction, selections: dict, trainer_name: str):
    """
    Executes the egg roll process using the provided selections.
    It adjusts the mon pool, applies item effects, rolls the mons,
    and sends an embed with interactive claim buttons.
    """
    # Retrieve the default egg pool.
    pool = get_default_pool()
    # Initialize roll parameters.
    roll_params = {
        "force_fusion": False,
        "force_min_types": None,
        "type_override": None,
        "code_override": None,
    }
    claim_limit = 1

    # Process each selection to adjust roll parameters and filter the pool.
    for key, value in selections.items():
        if not value:
            continue
        if key == "nurture_kit":
            # e.g., "Fire Nurture Kit" forces primary type to "Fire".
            roll_params["type_override"] = extract_first_word(value)
        elif key == "corruption_code":
            if value.lower() == "corruption code":
                roll_params["code_override"] = "Virus"
        elif key == "repair_code":
            if value.lower() == "repair code":
                roll_params["code_override"] = "Vaccine"
        elif key == "shiny_new_code":
            if value.lower() == "shiny new code":
                roll_params["code_override"] = "Data"
        elif key == "rank_incense":
            # Filter pool to include only Yo-Kai of the specified rank.
            rank = value.split()[0]
            pool = [mon for mon in pool if mon.get("origin") == "yokai" and mon.get("rank", "").upper() == rank.upper()]
        elif key == "color_insense":
            # Filter pool to include only Yo-Kai with the specified attribute.
            color = value.split()[0]
            pool = [mon for mon in pool if
                    mon.get("origin") == "yokai" and mon.get("attribute", "").lower() == color.lower()]
        elif key == "spell_tag":
            # Exclude Yo-Kai from the pool.
            pool = [mon for mon in pool if mon.get("origin") != "yokai"]
        elif key == "summoning_stone":
            # Ensure Yo-Kai are included.
            from rollmons import fetch_yokai_data
            yokai = fetch_yokai_data()
            pool.extend(yokai)
        elif key == "digimeat":
            # Include Digimon.
            from rollmons import fetch_digimon_data
            digimon = fetch_digimon_data()
            pool.extend(digimon)
        elif key == "digitofu":
            # Exclude Digimon.
            pool = [mon for mon in pool if mon.get("origin") != "digimon"]
        elif key == "soothe_bell":
            # Ensure Pokémon are included.
            from rollmons import fetch_pokemon_data
            pokemon = fetch_pokemon_data()
            pool.extend(pokemon)
        elif key == "broken_bell":
            # Exclude Pokémon.
            pool = [mon for mon in pool if mon.get("origin") != "pokemon"]
        elif key == "poffin":
            # Filter pool for Pokémon with a matching type.
            desired_type = extract_first_word(value)
            pool = [mon for mon in pool if mon.get("origin") == "pokemon" and any(
                desired_type.lower() == t.lower() for t in mon.get("types", []))]
        elif key == "tag":
            # Filter pool for Digimon with a specific attribute tag.
            tag = value.replace("#", "").strip()
            pool = [mon for mon in pool if
                    mon.get("origin") == "digimon" and mon.get("attribute", "").lower() == tag.lower()]
        elif key == "dna_splicer":
            # Increase claim limit based on the quantity of DNA Splicer selected.
            qty = extract_quantity_from_label(value)
            claim_limit += qty
        elif key == "hot_chocolate":
            roll_params["force_fusion"] = True
        elif key == "chocolate_milk":
            roll_params["force_min_types"] = max(roll_params.get("force_min_types") or 0, 2)
        elif key == "strawberry_milk":
            roll_params["force_min_types"] = max(roll_params.get("force_min_types") or 0, 3)
        elif key == "vanilla_ice_cream":
            roll_params["force_min_types"] = max(roll_params.get("force_min_types") or 0, 1)
        elif key == "strawberry_ice_cream":
            roll_params["force_min_types"] = max(roll_params.get("force_min_types") or 0, 2)
        elif key == "chocolate_ice_cream":
            roll_params["force_min_types"] = max(roll_params.get("force_min_types") or 0, 3)
        elif key == "species_override":
            # Flag indicating species override is requested; in a full implementation, trigger a modal.
            roll_params["species_override"] = True

    # Roll a fixed number of mons (default 10).
    amount = 10
    rolled_mons = []
    for _ in range(amount):
        mon = roll_single_mon(pool, force_fusion=roll_params["force_fusion"],
                              force_min_types=roll_params["force_min_types"])
        # Ensure species designation is set.
        if not mon.get("species1"):
            mon["species1"] = mon.get("name", "Unknown")
        rolled_mons.append(mon)

    # Apply nurture kit effect: override first type if specified.
    if roll_params.get("type_override"):
        for mon in rolled_mons:
            if mon.get("types"):
                mon["types"][0] = roll_params["type_override"]
            else:
                mon["types"] = [roll_params["type_override"]]
    # Apply code overrides to set attributes.
    if roll_params.get("code_override"):
        for mon in rolled_mons:
            mon["attribute"] = roll_params["code_override"]
    # Handle species override (simulate by appending a note).
    if roll_params.get("species_override"):
        for mon in rolled_mons:
            mon["species1"] = f"{mon['species1']} (override pending)"

    # Build the Discord embed and claim view.
    embed = build_mon_embed(rolled_mons)
    view = RollMonsView(rolled_mons, claim_limit=claim_limit)
    await interaction.followup.send(embed=embed, view=view, ephemeral=True)
