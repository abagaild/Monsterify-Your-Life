import random
from typing import Dict, List
import discord
from core.database import cursor
from core.google_sheets import update_character_sheet_item

# Global constants for breeding randomization.
POSSIBLE_TYPES = [
    "Normal", "Fire", "Water", "Electric", "Grass", "Ice", "Fighting", "Poison",
    "Ground", "Flying", "Psychic", "Bug", "Rock", "Ghost", "Dragon", "Dark", "Steel", "Fairy"
]
RANDOM_ATTRIBUTES = ["Free", "Virus", "Vaccine", "Data", "Variable"]
FRESH_DIGIMON = [
    "Bombmon",
    "Bommon",
    "Botamon",
    "Chibickmon",
    "Chibomon",
    "Conomon",
    "Cotsucomon",
    "Curimon",
    "Datirimon",
    "DemiMeramon",
    "Dodomon",
    "Dokimon",
    "Fufumon",
    "Fusamon",
    "Jyarimon",
    "Keemon",
    "Ketomon",
    "Kuramon",
    "Leafmon",
    "MetalKoromon",
    "Mokumon",
    "Nyokimon",
    "Pabumon",
    "Pafumon",
    "Paomon",
    "Petitmon",
    "Pichimon",
    "Popomon",
    "Poyomon",
    "Punimon",
    "Pupamon",
    "Pururumon",
    "Pusumon",
    "Puttimon",
    "Puwamon",
    "Puyomon",
    "Pyonmon",
    "Relemon",
    "Sakumon",
    "Sandmon",
    "Tsubumon",
    "Yolkmon",
    "YukiBotamon",
    "Yuramon",
    "Zerimon",
    "Zurumon"
]


def get_parent_species(mon: Dict) -> List[str]:
    """
    Returns the list of species names from the mon's species fields.
    Safely casts values to string before stripping.
    """
    return [s for s in [
        str(mon.get("species1") or "").strip(),
        str(mon.get("species2") or "").strip(),
        str(mon.get("species3") or "").strip()
    ] if s]


def is_yokai(species: str) -> bool:
    cursor.execute('SELECT "Name" FROM YoKai WHERE lower("Name") = ?', (species.lower(),))
    return cursor.fetchone() is not None


def is_digimon(species: str) -> bool:
    cursor.execute('SELECT "Name" FROM Digimon WHERE lower("Name") = ?', (species.lower(),))
    return cursor.fetchone() is not None


def determine_origin(mon: Dict) -> set:
    origins = set()
    mon_name = (mon.get("mon_name") or "").strip()
    if is_digimon(mon_name):
        origins.add("digimon")
    if is_yokai(mon_name):
        origins.add("yokai")
    for sp in get_parent_species(mon):
        if is_digimon(sp):
            origins.add("digimon")
        if is_yokai(sp):
            origins.add("yokai")
    if not origins:
        origins.add("pokemon")
    return origins


def get_baby_species(species: str) -> str:
    cursor.execute("SELECT baby_species FROM pokemon_babies WHERE lower(parent_species) = ?", (species.lower(),))
    row = cursor.fetchone()
    if row and row[0] and row[0].strip():
        return row[0].strip()
    cursor.execute("SELECT baby_species FROM pokemon_babies")
    babies = [r[0].strip() for r in cursor.fetchall() if r[0]]
    return random.choice(babies) if babies else ""


def build_species_pool(parent1: Dict, parent2: Dict) -> List[str]:
    pool = []
    for mon in [parent1, parent2]:
        for sp in get_parent_species(mon):
            origins = determine_origin(mon)
            if "pokemon" in origins and "digimon" not in origins and "yokai" not in origins:
                baby = get_baby_species(sp)
                if baby:
                    pool.append(baby)
            elif "digimon" in origins:
                pool.append(random.choice(FRESH_DIGIMON))
            elif "yokai" in origins:
                pool.append(sp)
    return list(set(pool)) if pool else ["UnknownSpecies"]


def get_combined_types(parent1: dict, parent2: dict) -> list:
    types1 = parent1.get("types", [])
    types2 = parent2.get("types", [])
    combined = list(set(types1 + types2))
    return combined if combined else ["Normal"]


def get_combined_attribute(parent1: dict, parent2: dict) -> str:
    attrs = []
    if parent1.get("attribute"):
        attrs.append(parent1["attribute"])
    if parent2.get("attribute"):
        attrs.append(parent2["attribute"])
    return random.choice(attrs) if attrs else "Free"


def breed_offspring(parent1: dict, parent2: dict) -> list:
    """
    Breeds offspring by fusing up to three species from the parents.
    The offspring will store the fusion across three separate species fields.
    """
    species_pool = build_species_pool(parent1, parent2)
    types_pool = get_combined_types(parent1, parent2)
    default_attr = get_combined_attribute(parent1, parent2)
    num_offspring = random.randint(1, 3)
    offspring_list = []
    for i in range(num_offspring):
        # Fusion: choose between 1 and up to 3 species from the candidate pool.
        if species_pool:
            max_species = min(3, len(species_pool))
            num_species = random.randint(1, max_species)
            selected_species = random.sample(species_pool, num_species)
            off_species1 = selected_species[0] if len(selected_species) >= 1 else ""
            off_species2 = selected_species[1] if len(selected_species) >= 2 else ""
            off_species3 = selected_species[2] if len(selected_species) >= 3 else ""
        else:
            off_species1, off_species2, off_species3 = "UnknownSpecies", "", ""

        num_types = random.randint(1, min(5, len(types_pool))) if types_pool else 1
        off_types = random.sample(types_pool, num_types) if types_pool else ["Normal"]
        off_attr = default_attr
        # 20% chance for a mutation altering species, types, or attribute.
        if random.random() < 0.20:
            mutation_choice = random.choice(["species", "types", "attribute"])
            if mutation_choice == "species":
                cursor.execute("SELECT Name FROM Digimon")
                digimon_candidates = [row[0].strip() for row in cursor.fetchall() if row[0]]
                cursor.execute('SELECT "Name" FROM YoKai')
                yokai_candidates = [row[0].strip() for row in cursor.fetchall() if row[0]]
                mutation_pool = digimon_candidates + yokai_candidates + species_pool
                if mutation_pool:
                    max_species_mut = min(3, len(mutation_pool))
                    num_species_mut = random.randint(1, max_species_mut)
                    selected_mut_species = random.sample(mutation_pool, num_species_mut)
                    off_species1 = selected_mut_species[0] if len(selected_mut_species) >= 1 else ""
                    off_species2 = selected_mut_species[1] if len(selected_mut_species) >= 2 else ""
                    off_species3 = selected_mut_species[2] if len(selected_mut_species) >= 3 else ""
            elif mutation_choice == "types":
                off_types = random.sample(POSSIBLE_TYPES, random.randint(1, 5))
            elif mutation_choice == "attribute":
                off_attr = random.choice(RANDOM_ATTRIBUTES)
        offspring = {
            "mon_name": f"Offspring {i + 1} of {parent1.get('mon_name', 'Parent1')} & {parent2.get('mon_name', 'Parent2')}",
            "species1": off_species1,
            "species2": off_species2,
            "species3": off_species3,
            "types": off_types,
            "attribute": off_attr,
            "level": 1,
            "img_link": ""
        }
        offspring_list.append(offspring)
    return offspring_list


async def breed_mons(mon1_id: int, mon2_id: int, user_id: str) -> list:
    from core.mon import is_mon_viable_for_breeding
    cursor.execute("SELECT * FROM mons WHERE id = ?", (mon1_id,))
    parent1_tuple = cursor.fetchone()
    cursor.execute("SELECT * FROM mons WHERE id = ?", (mon2_id,))
    parent2_tuple = cursor.fetchone()
    if not parent1_tuple or not parent2_tuple:
        return []
    keys = ["id", "trainer_id", "player", "mon_name", "species1", "species2", "species3",
            "type1", "type2", "type3", "type4", "type5", "attribute", "img_link"]
    parent1 = dict(zip(keys, parent1_tuple))
    parent2 = dict(zip(keys, parent2_tuple))
    # Combine type columns into a list.
    parent1["types"] = [parent1.pop("type1"), parent1.pop("type2"), parent1.pop("type3"),
                        parent1.pop("type4"), parent1.pop("type5")]
    parent1["types"] = [t for t in parent1["types"] if t]
    parent2["types"] = [parent2.pop("type1"), parent2.pop("type2"), parent2.pop("type3"),
                        parent2.pop("type4"), parent2.pop("type5")]
    parent2["types"] = [t for t in parent2["types"] if t]
    if parent1["player"] != user_id and parent2["player"] != user_id:
        return []
    if not is_mon_viable_for_breeding(mon1_id) or not is_mon_viable_for_breeding(mon2_id):
        return []
    trainer_id = parent1["trainer_id"] if parent1["player"] == user_id else parent2["trainer_id"]
    cursor.execute("SELECT name FROM trainers WHERE id = ?", (trainer_id,))
    row = cursor.fetchone()
    if row:
        trainer_name = row[0]
        removal_success = await update_character_sheet_item(trainer_name, "Legacy Leeway", -1)
        if not removal_success:
            return []
    return breed_offspring(parent1, parent2)


# UI components for offspring registration and post-breeding options.

class OffspringRegistrationButton(discord.ui.Button):
    def __init__(self, offspring: dict):
        super().__init__(label=f"Register {offspring['mon_name']}", style=discord.ButtonStyle.primary)
        self.offspring = offspring

    async def callback(self, interaction: discord.Interaction):
        from core.mon import register_mon  # centralized registration modal
        await register_mon(interaction, self.offspring)
        self.disabled = True
        await interaction.response.edit_message(view=self.view)
        await interaction.followup.send(f"{self.offspring['mon_name']} registered successfully!", ephemeral=True)

class DoneButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Done", style=discord.ButtonStyle.secondary)

    async def callback(self, interaction: discord.Interaction):
        for item in self.view.children:
            item.disabled = True
        await interaction.response.edit_message(view=self.view)
        await interaction.followup.send("Offspring registration completed.", ephemeral=True)

class OffspringRegistrationView(discord.ui.View):
    def __init__(self, user: discord.User, offspring_list: list, player_mon: dict, other_mon: dict):
        super().__init__(timeout=120)
        self.user = user
        self.offspring_list = offspring_list
        self.player_mon = player_mon
        self.other_mon = other_mon
        for offspring in offspring_list:
            self.add_item(OffspringRegistrationButton(offspring))
        self.add_item(DoneButton())

class BreedAgainButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Breed Again", style=discord.ButtonStyle.primary)

    async def callback(self, interaction: discord.Interaction):
        from logic.market.farm import open_farm_logic
        await interaction.response.send_message("Restarting breeding process...", ephemeral=True)
        embed, view = await open_farm_logic(interaction)
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

class ReturnToMainMenuButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Return to Main Menu", style=discord.ButtonStyle.secondary)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message("Returning to main menu...", ephemeral=True)

class FarmResultView(discord.ui.View):
    def __init__(self, user: discord.User, player_trainer: dict, other_trainer: dict, player_mon: dict, other_mon: dict):
        super().__init__(timeout=120)
        self.user = user
        self.player_trainer = player_trainer
        self.other_trainer = other_trainer
        self.player_mon = player_mon
        self.other_mon = other_mon
        self.add_item(BreedAgainButton())
        self.add_item(ReturnToMainMenuButton())