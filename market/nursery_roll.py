import discord
import re
from core.rollmons import get_default_pool, roll_single_mon, build_mon_embed, RollMonsView
from market.nursery_options import get_temp_inventory

def extract_first_word(item_name: str) -> str:
    return item_name.split()[0] if item_name else ""

def extract_quantity_from_label(label: str) -> int:
    match = re.search(r"\((\d+)\)", label)
    if match:
        return int(match.group(1))
    return 1

async def run_nursery_roll(interaction: discord.Interaction, selections: dict, trainer_name: str):
    """
    Executes the egg roll based on nursery options (selections).
    Builds a candidate pool from the default pool and applies overrides based on selections.
    Finally, it builds an embed with rolled mons and a claim UI.
    """
    if isinstance(selections, list):
        options_dict = {}
        for option in selections:
            norm = option.lower()
            if "nurture kit" in norm:
                options_dict["nurture_kit"] = option
            elif "corruption code" in norm:
                options_dict["corruption_code"] = option
            elif "repair code" in norm:
                options_dict["repair_code"] = option
            elif "shiny new code" in norm:
                options_dict["shiny_new_code"] = option
            elif "rank incense" in norm:
                options_dict["rank_incense"] = option
            elif "color incense" in norm:  # (note: check spelling if needed)
                options_dict["color_insense"] = option
            elif "spell tag" in norm:
                options_dict["spell_tag"] = option
            elif "summoning stone" in norm:
                options_dict["summoning_stone"] = option
            elif "digimeat" in norm:
                options_dict["digimeat"] = option
            elif "digitofu" in norm:
                options_dict["digitofu"] = option
            elif "soothe bell" in norm:
                options_dict["soothe_bell"] = option
            elif "broken bell" in norm:
                options_dict["broken_bell"] = option
            elif "poffin" in norm:
                options_dict["poffin"] = option
            elif "tag" in norm:
                options_dict["tag"] = option
            elif "dna splicer" in norm:
                options_dict["dna_splicer"] = option
            elif "hot chocolate" in norm:
                options_dict["hot_chocolate"] = option
            elif "chocolate milk" in norm:
                options_dict["chocolate_milk"] = option
            elif "strawberry milk" in norm:
                options_dict["strawberry_milk"] = option
            elif "vanilla ice cream" in norm:
                options_dict["vanilla_ice_cream"] = option
            elif "strawberry ice cream" in norm:
                options_dict["strawberry_ice_cream"] = option
            elif "chocolate ice cream" in norm:
                options_dict["chocolate_ice_cream"] = option
            elif "species override" in norm:
                options_dict["species_override"] = option
        selections = options_dict

    pool = get_default_pool()
    roll_params = {
        "force_fusion": False,
        "force_min_types": None,
        "type_override": None,
        "code_override": None,
        "species_override": False,
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
