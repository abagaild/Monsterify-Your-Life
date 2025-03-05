import random
from typing import List, Dict, Any, Optional

from core.database import update_character_sheet_item
#from core.database import update_character_sheet_item, update_mon_sheet_data
from core.rollmons import fetch_pokemon_data, fetch_digimon_data, fetch_yokai_data
from data.lists import legendary_list, mythical_list, no_evolution
from core.database import cursor, update_mon_data

# Global constant for possible types
POSSIBLE_TYPES: List[str] = [
    "Normal", "Fire", "Water", "Electric", "Grass", "Ice", "Fighting",
    "Poison", "Ground", "Flying", "Psychic", "Bug", "Rock", "Ghost",
    "Dragon", "Dark", "Steel", "Fairy"
]

# =============================================================================
# 1. Build a Pool of Possible Species
# =============================================================================

def get_possible_species_pool() -> List[str]:
    """
    Builds and returns a pool of species names from Pokémon, Digimon, and Yo‑kai data.
    Pokémon are included if they are base stage or listed in no_evolution.
    Digimon are included if their stage is one of a valid set.
    Yo‑kai are always included.
    """
    pool: List[str] = []
    legendary_set = {name.lower() for name in legendary_list}
    mythical_set = {name.lower() for name in mythical_list}
    no_evo_set = {name.lower() for name in no_evolution}

    for p in fetch_pokemon_data():
        name = p.get("name", "").strip()
        stage = p.get("stage", "").strip().lower()
        if name.lower() in legendary_set or name.lower() in mythical_set:
            continue
        if stage in {"base", "base stage"} or name.lower() in no_evo_set:
            pool.append(name)
    valid_digi_stages = {"in training", "trainer i", "trainer ii", "rookie"}
    for d in fetch_digimon_data():
        stage = d.get("stage", "").strip().lower()
        if stage in valid_digi_stages:
            pool.append(d.get("name", "").strip())
    for y in fetch_yokai_data():
        pool.append(y.get("name", "").strip())
    return list(set(pool))

# =============================================================================
# 2. Berry Effect Functions (each modifies the mon dict and returns a message)
# =============================================================================

def effect_mala(mon: Dict[str, Any]) -> str:
    if mon.get("species2"):
        removed = mon["species2"]
        mon["species2"] = ""
        return f"Species 2 '{removed}' removed."
    return "No Species 2 to remove."

def effect_merco(mon: Dict[str, Any]) -> str:
    if mon.get("species3"):
        removed = mon["species3"]
        mon["species3"] = ""
        return f"Species 3 '{removed}' removed."
    return "No Species 3 to remove."

def effect_lilan(mon: Dict[str, Any]) -> str:
    types = mon.get("types", [])
    if len(types) >= 2:
        removed = types.pop(1)
        return f"Type 2 '{removed}' removed."
    return "No Type 2 to remove."

def effect_kham(mon: Dict[str, Any]) -> str:
    types = mon.get("types", [])
    if len(types) >= 3:
        removed = types.pop(2)
        return f"Type 3 '{removed}' removed."
    return "No Type 3 to remove."

def effect_maizi(mon: Dict[str, Any]) -> str:
    types = mon.get("types", [])
    if len(types) >= 4:
        removed = types.pop(3)
        return f"Type 4 '{removed}' removed."
    return "No Type 4 to remove."

def effect_fani(mon: Dict[str, Any]) -> str:
    types = mon.get("types", [])
    if len(types) >= 5:
        removed = types.pop(4)
        return f"Type 5 '{removed}' removed."
    return "No Type 5 to remove."

def effect_miraca(mon: Dict[str, Any]) -> str:
    types = mon.get("types", [])
    if types:
        old = types[0]
        new = random.choice(POSSIBLE_TYPES)
        types[0] = new
        return f"Type 1 changed from '{old}' to '{new}'."
    mon["types"] = [random.choice(POSSIBLE_TYPES)]
    return f"Type 1 set to '{mon['types'][0]}'."

def effect_cocon(mon: Dict[str, Any]) -> str:
    types = mon.get("types", [])
    if len(types) >= 2:
        old = types[1]
        new = random.choice(POSSIBLE_TYPES)
        types[1] = new
        return f"Type 2 changed from '{old}' to '{new}'."
    return "No Type 2 to randomize."

def effect_durian(mon: Dict[str, Any]) -> str:
    types = mon.get("types", [])
    if len(types) >= 3:
        old = types[2]
        new = random.choice(POSSIBLE_TYPES)
        types[2] = new
        return f"Type 3 changed from '{old}' to '{new}'."
    return "No Type 3 to randomize."

def effect_monel(mon: Dict[str, Any]) -> str:
    types = mon.get("types", [])
    if len(types) >= 4:
        old = types[3]
        new = random.choice(POSSIBLE_TYPES)
        types[3] = new
        return f"Type 4 changed from '{old}' to '{new}'."
    return "No Type 4 to randomize."

def effect_perep(mon: Dict[str, Any]) -> str:
    types = mon.get("types", [])
    if len(types) >= 5:
        old = types[4]
        new = random.choice(POSSIBLE_TYPES)
        types[4] = new
        return f"Type 5 changed from '{old}' to '{new}'."
    return "No Type 5 to randomize."

def effect_addish(mon: Dict[str, Any]) -> str:
    types = mon.get("types", [])
    if len(types) < 2 or (len(types) >= 2 and not types[1]):
        new = random.choice(POSSIBLE_TYPES)
        if len(types) < 2:
            types.append(new)
        else:
            types[1] = new
        return f"Type 2 added: '{new}'."
    return "Type 2 already present; no addition."

def effect_sky_carrot(mon: Dict[str, Any]) -> str:
    types = mon.get("types", [])
    if len(types) < 3 or (len(types) >= 3 and not types[2]):
        new = random.choice(POSSIBLE_TYPES)
        while len(types) < 2:
            types.append("")
        if len(types) < 3:
            types.append(new)
        else:
            types[2] = new
        return f"Type 3 added: '{new}'."
    return "Type 3 already present; no addition."

def effect_kembre(mon: Dict[str, Any]) -> str:
    types = mon.get("types", [])
    if len(types) < 4 or (len(types) >= 4 and not types[3]):
        new = random.choice(POSSIBLE_TYPES)
        while len(types) < 3:
            types.append("")
        if len(types) < 4:
            types.append(new)
        else:
            types[3] = new
        return f"Type 4 added: '{new}'."
    return "Type 4 already present; no addition."

def effect_espara(mon: Dict[str, Any]) -> str:
    types = mon.get("types", [])
    if len(types) < 5 or (len(types) >= 5 and not types[4]):
        new = random.choice(POSSIBLE_TYPES)
        while len(types) < 4:
            types.append("")
        if len(types) < 5:
            types.append(new)
        else:
            types[4] = new
        return f"Type 5 added: '{new}'."
    return "Type 5 already present; no addition."

def effect_patama(mon: Dict[str, Any]) -> str:
    old_species = mon.get("species1", "")
    new_species = random.choice(get_possible_species_pool())
    mon["species1"] = new_species
    return f"Species 1 changed from '{old_species}' to '{new_species}'."

def effect_bluk(mon: Dict[str, Any]) -> str:
    if mon.get("species2"):
        old_species = mon["species2"]
        new_species = random.choice(get_possible_species_pool())
        mon["species2"] = new_species
        return f"Species 2 changed from '{old_species}' to '{new_species}'."
    return "Species 2 not present; no effect."

def effect_nuevo(mon: Dict[str, Any]) -> str:
    if mon.get("species3"):
        old_species = mon["species3"]
        new_species = random.choice(get_possible_species_pool())
        mon["species3"] = new_species
        return f"Species 3 changed from '{old_species}' to '{new_species}'."
    return "Species 3 not present; no effect."

def effect_azzuk(mon: Dict[str, Any]) -> str:
    if not mon.get("species2"):
        new_species = random.choice(get_possible_species_pool())
        mon["species2"] = new_species
        return f"Species 2 added: '{new_species}'."
    return "Species 2 already present; no addition."

def effect_mangus(mon: Dict[str, Any]) -> str:
    if not mon.get("species2"):
        new_species = random.choice(get_possible_species_pool())
        mon["species2"] = new_species
        return f"Species 2 added: '{new_species}'."
    return "Species 2 already present; no addition."

def effect_datei(mon: Dict[str, Any]) -> str:
    old = mon.get("attribute", "Free")
    new = random.choice(["Free", "Virus", "Vaccine", "Data", "Variable"])
    mon["attribute"] = new
    return f"Attribute changed from '{old}' to '{new}'."

# =============================================================================
# 3. Berry Effects Mapping
# =============================================================================

BERRY_EFFECTS: Dict[str, Any] = {
    "mala berry": effect_mala,
    "merco berry": effect_merco,
    "lilan berry": effect_lilan,
    "kham berry": effect_kham,
    "maizi berry": effect_maizi,
    "fani berry": effect_fani,
    "miraca berry": effect_miraca,
    "cocon berry": effect_cocon,
    "durian berry": effect_durian,
    "monel berry": effect_monel,
    "perep berry": effect_perep,
    "addish berry": effect_addish,
    "sky carrot berry": effect_sky_carrot,
    "kembre berry": effect_kembre,
    "espara berry": effect_espara,
    "patama berry": effect_patama,
    "bluk berry": effect_bluk,
    "nuevo berry": effect_nuevo,
    "azzuk berry": effect_azzuk,
    "mangus berry": effect_mangus,
    "datei berry": effect_datei,
}

# =============================================================================
# 4. Helper Functions for Mon Database Interaction
# =============================================================================

def get_mon(trainer_id: str, mon_name: str) -> Optional[Dict[str, Any]]:
    """
    Retrieves a mon record from the database for the given trainer and mon name.
    """
    cursor.execute(
        "SELECT id, species1, species2, species3, type1, type2, type3, type4, type5, attribute "
        "FROM mons WHERE mon_name = ? AND player = ?",
        (mon_name, trainer_id)
    )
    row = cursor.fetchone()
    if row:
        mon = {
            "id": row[0],
            "species1": row[1],
            "species2": row[2],
            "species3": row[3],
            "types": [row[4], row[5], row[6], row[7], row[8]],
            "attribute": row[9],
            "mon_name": mon_name
        }
        mon["types"] = [t for t in mon["types"] if t]
        return mon
    return None

async def update_mon(trainer_sheet: str, trainer_id: str, mon_name: str, mon: Dict[str, Any]) -> bool:
    """
    Updates the mon record in the database and the corresponding Google Sheet.
    """
    current_mon = get_mon(trainer_id, mon_name)
    if not current_mon:
        return False
    mon_id = current_mon["id"]
    update_fields = {
        "species1": mon.get("species1", ""),
        "species2": mon.get("species2", ""),
        "species3": mon.get("species3", ""),
        "attribute": mon.get("attribute", "")
    }
    types = mon.get("types", [])
    for i in range(5):
        update_fields[f"type{i+1}"] = types[i] if i < len(types) else ""
    try:
        update_mon_data(mon_id, **update_fields)
    except Exception as e:
        print(f"Error updating mon in DB: {e}")
        return False
    try:
        # Prepare data mapping: column numbers to updated values.
        data = {
            5: mon.get("species1", ""),
            6: mon.get("species2", ""),
            7: mon.get("species3", ""),
            8: types[0] if len(types) > 0 else "",
            9: types[1] if len(types) > 1 else "",
            10: types[2] if len(types) > 2 else "",
            11: types[3] if len(types) > 3 else "",
            12: types[4] if len(types) > 4 else "",
            13: mon.get("attribute", "")
        }
        success = await update_mon_sheet_data(trainer_sheet, mon_name, data)
        if not success:
            print("Failed to update mon data in Google Sheet.")
            return False
    except Exception as e:
        print(f"Error updating mon in Google Sheets: {e}")
        return False
    return True

async def remove_berry_from_inventory(trainer_sheet: str, berry: str, amount: int = 1) -> bool:
    """
    Removes a given amount of a berry from the trainer's inventory via the Google Sheet.
    """
    try:
        result = await update_character_sheet_item(trainer_sheet, berry, -amount)
        return bool(result)
    except Exception as e:
        print(f"Error removing berry from inventory: {e}")
        return False

# =============================================================================
# 5. Core Function: Applying a Berry Effect to a Mon
# =============================================================================

async def apply_berry_effect(trainer_id: str, trainer_sheet: str, mon_name: str, berry: str) -> str:
    """
    Applies the effect of the specified berry to the mon.
    Updates the mon in the database and removes one berry from inventory.
    Returns a message describing the effect.
    """
    berry_lower = berry.lower().strip()
    if berry_lower not in BERRY_EFFECTS:
        return f"Berry '{berry}' is not recognized."
    mon = get_mon(trainer_id, mon_name)
    if not mon:
        return f"Mon '{mon_name}' not found."
    effect_func = BERRY_EFFECTS[berry_lower]
    result = effect_func(mon)
    removed = await remove_berry_from_inventory(trainer_sheet, berry_lower)
    if not removed:
        result += " (Note: Berry was not found in inventory.)"
    updated = await update_mon(trainer_sheet, trainer_id, mon_name, mon)
    if not updated:
        result += " (Error updating mon data.)"
    return result
