import random
from core.database import execute_query, fetch_one, update_mon_data
from core.database import update_mon_sheet_value, update_character_sheet_item

def query_pokemon_evolution(base_species: str) -> str:
    """
    Given a base Pokémon species, returns the evolved species from the 'pokemon_evolutions' table.
    """
    row = fetch_one("SELECT evolved_species FROM pokemon_evolutions WHERE lower(base_species)=?", (base_species.lower(),))
    return row[0] if row else None

def query_digimon_evolution(base_species: str, evolution_item: str) -> list:
    """
    Given a Digimon base species and an evolution item, returns a list of possible evolved species.
    """
    row = fetch_one(
        "SELECT evolved_species1, evolved_species2, evolved_species3 FROM digimon_evolutions WHERE lower(base_species)=? AND lower(required_item)=?",
        (base_species.lower(), evolution_item.lower())
    )
    return [s for s in row if s] if row else []

def get_trainer_name(trainer_id: int) -> str:
    row = fetch_one("SELECT name FROM trainers WHERE id = ?", (trainer_id,))
    return row[0] if row else None

async def evolve_pokemon(mon: dict, evolution_item: str, selected_species: str = None) -> (bool, str):
    """
    Processes evolution for a Pokémon mon.
    """
    base_species = selected_species if selected_species else mon.get("species1")
    if not base_species:
        return False, "No base species found for evolution."

    evolved_species = query_pokemon_evolution(base_species)
    if not evolved_species:
        return False, f"{base_species} cannot evolve."

    stone_lower = evolution_item.lower()
    if stone_lower == "void stone":
        pass
    elif "auroras" in stone_lower:
        current_types = [mon.get(f"type{i}", "") for i in range(1, 6)]
        non_empty = [t for t in current_types if t]
        if len(non_empty) < 5:
            POSSIBLE_TYPES = [
                "Normal", "Fire", "Water", "Electric", "Grass", "Ice", "Fighting", "Poison",
                "Ground", "Flying", "Psychic", "Bug", "Rock", "Ghost", "Dragon", "Dark", "Steel", "Fairy"
            ]
            available = [t for t in POSSIBLE_TYPES if t.lower() not in [x.lower() for x in non_empty]]
            if available:
                new_type = random.choice(available)
                for key in [f"type{i}" for i in range(1, 6)]:
                    if not mon.get(key):
                        mon[key] = new_type
                        break
        else:
            return False, "Auroras Evolution Stone cannot be used on mons with 5 types."
    else:
        stone_type = evolution_item.replace(" Evolution Stone", "").strip()
        current_types = [mon.get(f"type{i}", "") for i in range(1, 6)]
        if stone_type.lower() not in [t.lower() for t in current_types if t]:
            for key in [f"type{i}" for i in range(1, 6)]:
                if not mon.get(key):
                    mon[key] = stone_type
                    break

    old_species = mon.get("species1")
    mon["species1"] = evolved_species

    try:
        # Use the new primary key column "mon_id"
        update_mon_data(mon["mon_id"], species1=evolved_species)
    except Exception as e:
        return False, f"Database update failed: {e}"

    trainer_name = get_trainer_name(mon["trainer_id"])
    if trainer_name:
        await update_mon_sheet_value(trainer_name, mon["name"], "species1", evolved_species)

    return True, f"Your {old_species} evolved into {evolved_species}!"

async def evolve_digimon(mon: dict, evolution_item: str, selected_species: str = None, repair_input: str = None) -> (bool, str):
    """
    Processes evolution for a Digimon mon.
    """
    base_species = selected_species if selected_species else mon.get("species1")
    if not base_species:
        return False, "No base species found for evolution."

    if evolution_item.lower() == "digital repair mode":
        if not repair_input:
            return False, "Digital Repair Mode requires manual input for evolution."
        evolved_species = repair_input
    else:
        options = query_digimon_evolution(base_species, evolution_item)
        if not options:
            return False, f"{base_species} cannot evolve with {evolution_item}."
        evolved_species = random.choice(options)

    old_species = mon.get("species1")
    mon["species1"] = evolved_species

    try:
        update_mon_data(mon["mon_id"], species1=evolved_species)
    except Exception as e:
        return False, f"Database update failed: {e}"

    return True, f"Your {old_species} evolved into {evolved_species}!"

async def evolve_mon(user_id: str, mon_id: int, evolution_item: str, selected_species: str = None,
                     repair_input: str = None) -> str:
    """
    Main function to evolve a mon:
      • Retrieves the mon record (ensuring it belongs to the user) using new column names.
      • Determines evolution type and calls the appropriate function.
      • Deducts one evolution item from the trainer’s inventory.
      • Returns a response message.
    """
    # Updated query: use "mon_id" and "player_user_id"
    row = fetch_one("SELECT * FROM mons WHERE mon_id = ? AND player_user_id = ?", (mon_id, user_id))
    if not row:
        return "Mon not found or does not belong to you."

    # Build the mon record using updated column names.
    keys = [
        "mon_id", "trainer_id", "player_user_id", "name", "level",
        "species1", "species2", "species3", "type1", "type2",
        "type3", "type4", "type5", "attribute", "img_link"
    ]
    mon = {key: row[i] for i, key in enumerate(keys)}

    if query_pokemon_evolution(mon.get("species1", "")) is not None:
        success, message = await evolve_pokemon(mon, evolution_item, selected_species)
    else:
        success, message = await evolve_digimon(mon, evolution_item, selected_species, repair_input)

    if success:
        trainer_name = get_trainer_name(mon["trainer_id"])
        if trainer_name:
            await update_character_sheet_item(trainer_name, evolution_item, -1)
        message += "\nReturning to Witch's Hut..."
    return message
