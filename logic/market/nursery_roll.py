import discord
import re
from core.rollmons import get_default_pool, roll_single_mon, build_mon_embed, RollMonsView

def extract_first_word(item_name: str) -> str:
    return item_name.split()[0] if item_name else ""

def extract_quantity_from_label(label: str) -> int:
    match = re.search(r"\((\d+)\)", label)
    if match:
        return int(match.group(1))
    return 1

async def run_nursery_roll(interaction: discord.Interaction, selections: dict, trainer_name: str):
    pool = get_default_pool()
    roll_params = {
        "force_fusion": False,
        "force_min_types": None,
        "type_override": None,
        "code_override": None,
    }
    claim_limit = 1

    for key, value in selections.items():
        if not value:
            continue
        if key == "nurture_kit":
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
            rank = value.split()[0]
            pool = [mon for mon in pool if mon.get("origin") == "yokai" and mon.get("rank", "").upper() == rank.upper()]
        elif key == "color_insense":
            color = value.split()[0]
            pool = [mon for mon in pool if mon.get("origin") == "yokai" and mon.get("attribute", "").lower() == color.lower()]
        elif key == "spell_tag":
            pool = [mon for mon in pool if mon.get("origin") != "yokai"]
        elif key == "summoning_stone":
            from core.rollmons import fetch_yokai_data
            yokai = fetch_yokai_data()
            pool.extend(yokai)
        elif key == "digimeat":
            from core.rollmons import fetch_digimon_data
            digimon = fetch_digimon_data()
            pool.extend(digimon)
        elif key == "digitofu":
            pool = [mon for mon in pool if mon.get("origin") != "digimon"]
        elif key == "soothe_bell":
            from core.rollmons import fetch_pokemon_data
            pokemon = fetch_pokemon_data()
            pool.extend(pokemon)
        elif key == "broken_bell":
            pool = [mon for mon in pool if mon.get("origin") != "pokemon"]
        elif key == "poffin":
            desired_type = extract_first_word(value)
            pool = [mon for mon in pool if mon.get("origin") == "pokemon" and any(
                desired_type.lower() == t.lower() for t in mon.get("types", []))]
        elif key == "tag":
            tag = value.replace("#", "").strip()
            pool = [mon for mon in pool if mon.get("origin") == "digimon" and mon.get("attribute", "").lower() == tag.lower()]
        elif key == "dna_splicer":
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
            roll_params["species_override"] = True

    amount = 10
    rolled_mons = []
    for _ in range(amount):
        mon = roll_single_mon(pool, force_fusion=roll_params["force_fusion"],
                              force_min_types=roll_params["force_min_types"])
        if not mon.get("species1"):
            mon["species1"] = mon.get("name", "Unknown")
        rolled_mons.append(mon)

    if roll_params.get("type_override"):
        for mon in rolled_mons:
            if mon.get("types"):
                mon["types"][0] = roll_params["type_override"]
            else:
                mon["types"] = [roll_params["type_override"]]
    if roll_params.get("code_override"):
        for mon in rolled_mons:
            mon["attribute"] = roll_params["code_override"]
    if roll_params.get("species_override"):
        for mon in rolled_mons:
            mon["species1"] = f"{mon['species1']} (override pending)"

    embed = build_mon_embed(rolled_mons)
    view = RollMonsView(rolled_mons, claim_limit=claim_limit)
    await interaction.followup.send(embed=embed, view=view, ephemeral=True)
