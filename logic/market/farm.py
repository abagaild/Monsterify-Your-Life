"""
logic_farm.py
---------------
Farm Shop logic and breeding module – refactored to use centralized external calls while retaining full breeding logic.
"""

import random

from core.database import cursor
from core.google_sheets import update_character_sheet_item


# Farm shop configuration.
IMAGES = [
    "https://example.com/farm1.png",
    "https://example.com/farm2.png",
]

MESSAGES = [
    "Welcome to the Farm! Enjoy the rustic charm and bountiful harvests.",
    "Step onto the Farm for fresh produce and country vibes."
]

# Global constants for randomization.
POSSIBLE_TYPES = [
    "Normal", "Fire", "Water", "Electric", "Grass", "Ice", "Fighting", "Poison",
    "Ground", "Flying", "Psychic", "Bug", "Rock", "Ghost", "Dragon", "Dark", "Steel", "Fairy"
]
RANDOM_ATTRIBUTES = ["Free", "Virus", "Vaccine", "Data", "Variable"]

# Provided list of fresh Digimon species.
FRESH_DIGIMON = ["Botamon", "Kuramon", "Pabumon", "Poyomon", "Punimon"]

# ----------------------------
# Breeding Helper Functions
# ----------------------------
def get_all_yokai_species() -> list:
    """Returns all Yokai species from the YoKai table."""
    cursor.execute('SELECT "Name" FROM YoKai')
    rows = cursor.fetchall()
    return [row[0].strip() for row in rows if row[0]]

def get_all_pokemon_babies() -> list:
    """Returns all baby species from the pokemon_babies table."""
    cursor.execute("SELECT baby_species FROM pokemon_babies")
    rows = cursor.fetchall()
    return [row[0].strip() for row in rows if row[0]]

def fetch_mon_from_db(mon_id: int) -> tuple:
    """Retrieves a mon record from the database given its ID."""
    cursor.execute("SELECT * FROM mons WHERE id = ?", (mon_id,))
    return cursor.fetchone()

def get_species_from_parent(parent_row: tuple) -> list:
    """
    Extracts species from a parent mon record.
    Uses columns 6–8 (indexes 5,6,7) and falls back to the mon name (column 4, index 3).
    """
    species = []
    for i in [5, 6, 7]:
        try:
            val = parent_row[i]
        except IndexError:
            continue
        if val is not None:
            s = str(val).strip()
            if s:
                species.append(s)
    if not species and len(parent_row) > 3 and str(parent_row[3]).strip():
        species.append(str(parent_row[3]).strip())
    return species

def get_types_from_parent(parent_row: tuple) -> list:
    """
    Extracts types from a parent mon record using columns 9–13 (indexes 8 to 12).
    """
    types = []
    for i in [8, 9, 10, 11, 12]:
        try:
            val = parent_row[i]
        except IndexError:
            continue
        if val and str(val).strip():
            types.append(str(val).strip())
    return types

def get_attribute_from_parent(parent_row: tuple) -> str:
    """Extracts the attribute from a parent mon (column 14, index 13)."""
    try:
        attr = parent_row[13]
    except IndexError:
        return "Free"
    return str(attr).strip() if attr and str(attr).strip() else "Free"

def get_baby_species(species: str) -> str:
    """
    Looks up the baby species for a given Pokémon parent species.
    Returns the baby species if found; otherwise, randomly picks one from all baby species.
    """
    cursor.execute("SELECT baby_species FROM pokemon_babies WHERE lower(parent_species) = ?", (species.lower(),))
    row = cursor.fetchone()
    if row and row[0].strip():
        return row[0].strip()
    babies = get_all_pokemon_babies()
    if babies:
        return random.choice(babies)
    return ""

def convert_species_list_for_pokemon(species_list: list) -> list:
    """Converts each species using the baby lookup function."""
    converted = []
    for sp in species_list:
        baby = get_baby_species(sp)
        if baby:
            converted.append(baby)
    return converted

def determine_origin(mon: tuple) -> str:
    """
    Determines the origin of a mon record:
      - 'digimon' if its name exists in the Digimon table,
      - 'pokemon' if any species is convertible,
      - otherwise 'yokai'.
    """
    mon_name = mon[3].strip() if len(mon) > 3 and mon[3] else ""
    cursor.execute('SELECT "Name" FROM Digimon WHERE lower("Name") = ?', (mon_name.lower(),))
    if cursor.fetchone():
        return "digimon"
    species = get_species_from_parent(mon)
    if species and convert_species_list_for_pokemon(species):
        return "pokemon"
    return "yokai"

async def remove_legacy_leeway(trainer_id: int) -> bool:
    """Removes one Legacy Leeway from the trainer's inventory using Google Sheets update."""
    cursor.execute("SELECT name FROM trainers WHERE id = ?", (trainer_id,))
    row = cursor.fetchone()
    if row:
        trainer_name = row[0]
        return await update_character_sheet_item(trainer_name, "Legacy Leeway", -1)
    return False

def get_valid_pokemon_babies() -> list:
    cursor.execute("SELECT baby_species FROM pokemon_babies")
    rows = cursor.fetchall()
    return [row[0].strip() for row in rows if row[0]]

def breed_offspring(parent1: tuple, parent2: tuple) -> list:
    """
    Generates between 1 and 3 offspring from two parent mons.
    Applies rules for Pokémon, Digimon, or Yo-Kai and includes a chance for mutation.
    """
    origin1 = determine_origin(parent1)
    origin2 = determine_origin(parent2)
    species_pool = []
    if origin1 == "pokemon" or origin2 == "pokemon":
        baby_list1 = [get_baby_species(sp) for sp in get_species_from_parent(parent1) if get_baby_species(sp)]
        baby_list2 = [get_baby_species(sp) for sp in get_species_from_parent(parent2) if get_baby_species(sp)]
        valid_babies = get_valid_pokemon_babies()
        species_pool = [b for b in baby_list1 + baby_list2 if b in valid_babies]
    elif origin1 == "digimon" or origin2 == "digimon":
        species_pool = FRESH_DIGIMON
    else:
        species_pool = list(set(get_species_from_parent(parent1) + get_species_from_parent(parent2)))
        if not species_pool:
            species_pool = ["UnknownSpecies"]
    types_pool = list(set(get_types_from_parent(parent1) + get_types_from_parent(parent2)))
    if not types_pool:
        types_pool = ["Normal"]
    parent_attrs = [get_attribute_from_parent(parent1), get_attribute_from_parent(parent2)]
    parent_attrs = [attr for attr in parent_attrs if attr]
    default_attr = random.choice(parent_attrs) if parent_attrs else "Free"
    num_offspring = random.randint(1, 3)
    offspring_list = []
    for i in range(num_offspring):
        off_species = [random.choice(species_pool) if species_pool else "UnknownSpecies"]
        num_types = random.randint(1, min(5, len(types_pool)))
        off_types = random.sample(types_pool, num_types)
        off_attr = default_attr
        if random.random() < 0.20:  # Mutation chance.
            mutation_choice = random.choice(["species", "types", "attribute"])
            if mutation_choice == "species":
                mutation_pool = get_all_yokai_species() + get_valid_pokemon_babies() + FRESH_DIGIMON
                off_species = [random.choice(mutation_pool)]
            elif mutation_choice == "types":
                off_types = random.sample(POSSIBLE_TYPES, random.randint(1, 5))
            elif mutation_choice == "attribute":
                off_attr = random.choice(RANDOM_ATTRIBUTES)
        parent1_name = parent1[3] if len(parent1) > 3 and parent1[3] else "Parent1"
        parent2_name = parent2[3] if len(parent2) > 3 and parent2[3] else "Parent2"
        mon_name_off = f"Offspring {i + 1} of {parent1_name} & {parent2_name}"
        offspring = {
            "mon_name": mon_name_off,
            "species1": off_species[0],
            "species2": "",
            "species3": "",
            "types": off_types,
            "attribute": off_attr,
            "level": 1,
            "img_link": ""
        }
        offspring_list.append(offspring)
    return offspring_list

async def breed_mons(mon1_id: int, mon2_id: int, user_id: str) -> list:
    """
    Breeds two mons (by their database IDs) if eligibility checks pass.
    Removes one Legacy Leeway from the trainer's inventory.
    Returns a list of offspring dictionaries or an empty list on failure.
    """
    from core.mon import is_mon_viable_for_breeding  # External eligibility check.
    parent1 = fetch_mon_from_db(mon1_id)
    parent2 = fetch_mon_from_db(mon2_id)
    if not parent1 or not parent2:
        return []
    if parent1[2] != user_id and parent2[2] != user_id:
        return []
    if not is_mon_viable_for_breeding(mon1_id) or not is_mon_viable_for_breeding(mon2_id):
        return []
    trainer_id = parent1[1] if parent1[2] == user_id else parent2[1]
    removal_success = await remove_legacy_leeway(trainer_id)
    if not removal_success:
        return []
    return breed_offspring(parent1, parent2)

async def register_mon_in_farm(interaction, mon_data: dict, trainer_name: str, custom_name: str = None):
    """
    Registers a mon as part of the Farm activity.
    Delegates to the centralized register_mon function.
    """
    from core.mon import register_mon  # Centralized mon registration
    await register_mon(interaction, mon_data)
