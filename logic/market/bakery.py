IMAGES = [
    "https://example.com/bakery1.png",
    "https://example.com/bakery2.png",
]
MESSAGES = [
    "Welcome to the Bakery! Enjoy the aroma of freshly baked delights.",
    "Step inside the Bakery for warm treats and sweet surprises."
]

from core.google_sheets import update_character_sheet_item
from core.mon import get_mon


def apply_pastry_effect(user_id: str, trainer_sheet: str, mon_name: str, pastry: str, user_input: str) -> str:
    """
    Applies a pastry effect to a mon.
    Uses the PASTRY_EFFECTS mapping (defined in this module) to modify the mon.
    """
    pastry_lower = pastry.lower().strip()
    if pastry_lower not in PASTRY_EFFECTS:
        return f"Pastry '{pastry}' is not recognized."
    mon = get_mon(user_id, mon_name)
    if not mon:
        return f"Mon '{mon_name}' not found."
    effect_func = PASTRY_EFFECTS[pastry_lower]
    result = effect_func(mon, user_input)
    removed = update_character_sheet_item(trainer_sheet, pastry_lower, -1)
    if not removed:
        result += " (Pastry was not found in inventory.)"
    # (Optionally update the mon in the DB/Google Sheet.)
    return result


def effect_miraca_pastry(mon: dict, value: str) -> str:
    types = mon.get("types", [])
    if types:
        old = types[0]
        types[0] = value
    else:
        old = "None"
        types = [value]
    mon["types"] = types
    return f"Type 1 changed from '{old}' to '{value}'."

def effect_cocon_pastry(mon: dict, value: str) -> str:
    types = mon.get("types", [])
    if len(types) >= 2:
        old = types[1]
        types[1] = value
        mon["types"] = types
        return f"Type 2 changed from '{old}' to '{value}'."
    return "Mon does not have a Type 2 slot."

def effect_durian_pastry(mon: dict, value: str) -> str:
    types = mon.get("types", [])
    if len(types) >= 3:
        old = types[2]
        types[2] = value
        mon["types"] = types
        return f"Type 3 changed from '{old}' to '{value}'."
    return "Mon does not have a Type 3 slot."

def effect_monel_pastry(mon: dict, value: str) -> str:
    types = mon.get("types", [])
    if len(types) >= 4:
        old = types[3]
        types[3] = value
        mon["types"] = types
        return f"Type 4 changed from '{old}' to '{value}'."
    return "Mon does not have a Type 4 slot."

def effect_perep_pastry(mon: dict, value: str) -> str:
    types = mon.get("types", [])
    if len(types) >= 5:
        old = types[4]
        types[4] = value
        mon["types"] = types
        return f"Type 5 changed from '{old}' to '{value}'."
    return "Mon does not have a Type 5 slot."

def effect_addish_pastry(mon: dict, value: str) -> str:
    types = mon.get("types", [])
    if len(types) < 2 or (len(types) >= 2 and not types[1]):
        if len(types) < 2:
            types.append(value)
        else:
            types[1] = value
        mon["types"] = types
        return f"Type 2 set to '{value}'."
    return "Mon already has a Type 2."

def effect_sky_carrot_pastry(mon: dict, value: str) -> str:
    types = mon.get("types", [])
    if len(types) < 3 or (len(types) >= 3 and not types[2]):
        if len(types) < 3:
            while len(types) < 2:
                types.append("")
            types.append(value)
        else:
            types[2] = value
        mon["types"] = types
        return f"Type 3 set to '{value}'."
    return "Mon already has a Type 3."

def effect_kembre_pastry(mon: dict, value: str) -> str:
    types = mon.get("types", [])
    if len(types) < 4 or (len(types) >= 4 and not types[3]):
        if len(types) < 4:
            while len(types) < 3:
                types.append("")
            types.append(value)
        else:
            types[3] = value
        mon["types"] = types
        return f"Type 4 set to '{value}'."
    return "Mon already has a Type 4."

def effect_espara_pastry(mon: dict, value: str) -> str:
    types = mon.get("types", [])
    if len(types) < 5 or (len(types) >= 5 and not types[4]):
        if len(types) < 5:
            while len(types) < 4:
                types.append("")
            types.append(value)
        else:
            types[4] = value
        mon["types"] = types
        return f"Type 5 set to '{value}'."
    return "Mon already has a Type 5."

def effect_patama_pastry(mon: dict, value: str) -> str:
    old = mon.get("species1", "")
    mon["species1"] = value
    return f"Species 1 changed from '{old}' to '{value}'."

def effect_bluk_pastry(mon: dict, value: str) -> str:
    if mon.get("species2"):
        old = mon["species2"]
        mon["species2"] = value
        return f"Species 2 changed from '{old}' to '{value}'."
    return "Mon does not have a Species 2 slot."

def effect_nuevo_pastry(mon: dict, value: str) -> str:
    if mon.get("species3"):
        old = mon["species3"]
        mon["species3"] = value
        return f"Species 3 changed from '{old}' to '{value}'."
    return "Mon does not have a Species 3 slot."

def effect_azzuk_pastry(mon: dict, value: str) -> str:
    if not mon.get("species2"):
        mon["species2"] = value
        return f"Species 2 set to '{value}'."
    return "Species 2 already present; no addition."

def effect_mangus_pastry(mon: dict, value: str) -> str:
    if not mon.get("species2"):
        mon["species2"] = value
        return f"Species 2 set to '{value}'."
    return "Species 2 already present; no addition."

def effect_datei_pastry(mon: dict, value: str) -> str:
    old = mon.get("attribute", "Free")
    mon["attribute"] = value
    return f"Attribute changed from '{old}' to '{value}'."

PASTRY_EFFECTS = {
    "miraca pastry": effect_miraca_pastry,
    "cocon pastry": effect_cocon_pastry,
    "durian pastry": effect_durian_pastry,
    "monel pastry": effect_monel_pastry,
    "perep pastry": effect_perep_pastry,
    "addish pastry": effect_addish_pastry,
    "sky carrot pastry": effect_sky_carrot_pastry,
    "kembre pastry": effect_kembre_pastry,
    "espara pastry": effect_espara_pastry,
    "patama pastry": effect_patama_pastry,
    "bluk pastry": effect_bluk_pastry,
    "nuevo pastry": effect_nuevo_pastry,
    "azzuk pastry": effect_azzuk_pastry,
    "mangus pastry": effect_mangus_pastry,
    "datei pastry": effect_datei_pastry,
}