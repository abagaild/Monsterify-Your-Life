import random
import discord
from typing import List, Optional, Tuple

from discord.ui import Button, Modal, TextInput, View, Select

from core.database import (
    execute_query, fetch_one, fetch_all, update_mon_data,
    update_mon_sheet_value, update_character_sheet_item, get_mons_for_trainer
)
from core.trainer import get_trainers_from_database as get_trainers
from market.witches_hut_evolution import EVOLUTION_ITEMS


# -------------------- Evolution Logic --------------------

def query_pokemon_evolution(base_species: str) -> Optional[str]:
    """
    Given a base Pokémon species, returns the evolved species from the 'pokemon_evolutions' table.
    """
    row = fetch_one("SELECT evolved_species FROM pokemon_evolutions WHERE LOWER(base_species)=?", (base_species.lower(),))
    return row["evolved_species"] if row and "evolved_species" in row else None

def query_digimon_evolution(base_species: str, evolution_item: str) -> List[str]:
    """
    Given a Digimon base species and an evolution item, returns a list of possible evolved species.
    """
    row = fetch_one(
        "SELECT evolved_species1, evolved_species2, evolved_species3 FROM digimon_evolutions WHERE LOWER(base_species)=? AND LOWER(required_item)=?",
        (base_species.lower(), evolution_item.lower())
    )
    if row:
        return [s for s in (row.get("evolved_species1"), row.get("evolved_species2"), row.get("evolved_species3")) if s]
    return []

def get_trainer_name(trainer_id: int) -> Optional[str]:
    """
    Retrieves the trainer's display name (character_name) from the trainers table.
    """
    row = fetch_one("SELECT character_name FROM trainers WHERE id = ?", (trainer_id,))
    return row["character_name"] if row and "character_name" in row else None

async def evolve_pokemon(mon: dict, evolution_item: str, selected_species: str = None) -> Tuple[bool, str]:
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
        update_mon_data(mon["mon_id"], species1=evolved_species)
    except Exception as e:
        return False, f"Database update failed: {e}"

    trainer_name = get_trainer_name(mon["trainer_id"])
    if trainer_name:
        await update_mon_sheet_value(trainer_name, mon["name"], "species1", evolved_species)

    return True, f"Your {old_species} evolved into {evolved_species}!"

async def evolve_digimon(mon: dict, evolution_item: str, selected_species: str = None, repair_input: str = None) -> Tuple[bool, str]:
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
      - Retrieves the mon record (ensuring it belongs to the user).
      - Determines evolution type and calls the appropriate function.
      - Deducts one evolution item from the trainer’s inventory.
      - Returns a response message.
    """
    row = fetch_one("SELECT * FROM mons WHERE mon_id = ? AND player_user_id = ?", (mon_id, user_id))
    if not row:
        return "Mon not found or does not belong to you."

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
            # Deduct one evolution item from inventory (assume category "Evolution")
            await update_character_sheet_item(trainer_name, evolution_item, -1, category="Evolution")
        message += "\nReturning to Witch's Hut..."
    return message

# -------------------- Witch's Hut Shop View --------------------

# If you have a centralized EvolutionFlowView defined elsewhere, import it here.
# from logic.evolution import EvolutionFlowView

# For demonstration, we assume EvolutionFlowView is defined elsewhere.
class WitchsHutShopView(discord.ui.View):
    def __init__(self, user_id: str) -> None:
        super().__init__(timeout=None)
        self.user_id: str = user_id
        # These images and messages could be defined in a separate data file.
        self.image: str = random.choice([
            "https://i.imgur.com/L4XpZDd.png"
        ])
        self.message: str = random.choice([
            "I gots rocks, lots o rocks, rocks for all your mons, well 'cept your Yo-Kai Mon, can't fix those none.",
        ])

    @discord.ui.button(label="Shop", style=discord.ButtonStyle.primary, custom_id="witch_shop")
    async def shop_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        # Launch the generic shop view for evolution stones.
        from views.generic_shop import send_generic_shop_view
        await send_generic_shop_view(interaction, "witch", self.user_id, category_filter="stone")

    @discord.ui.button(label="Activity", style=discord.ButtonStyle.secondary, custom_id="witchs_hut_activity")
    async def activity_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.defer(ephemeral=True)
        evo_view = EvolutionFlowView(user_id=str(interaction.user.id))
        await interaction.followup.send("Evolution flow started", view=evo_view, ephemeral=True)

async def send_witchs_hut_view(interaction: discord.Interaction, user_id: str) -> None:
    view = WitchsHutShopView(user_id)
    embed = discord.Embed(
        title="Witch's Hut",
        description=view.message,
        color=discord.Color.dark_purple()
    )
    embed.set_image(url=view.image)
    await interaction.followup.send(embed=embed, view=view, ephemeral=True)

class EvolutionFlowView(View):
    """
    Guides the user through the evolution process.
    Steps:
      1. Select trainer.
      2. Select mon from that trainer.
      3. Select an evolution item.
      4. If multiple species exist for the mon, choose target species.
      5. If Digital Repair Mode is chosen, prompt for manual input.
      6. Confirm evolution.
    """
    def __init__(self, user_id: str) -> None:
        super().__init__(timeout=180)
        self.user_id: str = user_id
        self.selected_trainer: Optional[dict] = None
        self.selected_mon: Optional[dict] = None
        self.evolution_item: Optional[str] = None
        self.selected_species: Optional[str] = None
        self.repair_input: Optional[str] = None
        self.clear_items()  # Clear any preexisting items.
        self.add_item(self.TrainerSelect(self))

    class TrainerSelect(Select):
        def __init__(self, parent_view: 'EvolutionFlowView') -> None:
            self.parent_view = parent_view
            trainers = get_trainers(parent_view.user_id)
            options = [discord.SelectOption(label=t["character_name"], value=str(t["id"])) for t in trainers]
            super().__init__(placeholder="Select your trainer", min_values=1, max_values=1, options=options)

        async def callback(self, interaction: discord.Interaction) -> None:
            trainer_id = int(self.values[0])
            trainers = get_trainers(self.parent_view.user_id)
            self.parent_view.selected_trainer = next((t for t in trainers if t["id"] == trainer_id), None)
            self.parent_view.clear_items()
            self.parent_view.add_item(self.parent_view.MonSelect(self.parent_view))
            await interaction.response.edit_message(
                content=f"Trainer **{self.parent_view.selected_trainer['character_name']}** selected. Now select a mon to evolve.",
                view=self.parent_view
            )

    class MonSelect(Select):
        def __init__(self, parent_view: 'EvolutionFlowView') -> None:
            self.parent_view = parent_view
            mons = get_mons_for_trainer(self.parent_view.selected_trainer["id"])
            options = [discord.SelectOption(label=m["name"], value=str(m["mon_id"])) for m in mons]
            super().__init__(placeholder="Select a mon to evolve", min_values=1, max_values=1, options=options)

        async def callback(self, interaction: discord.Interaction) -> None:
            mon_id = int(self.values[0])
            mons = get_mons_for_trainer(self.parent_view.selected_trainer["id"])
            self.parent_view.selected_mon = next((m for m in mons if m["mon_id"] == mon_id), None)
            self.parent_view.clear_items()
            self.parent_view.add_item(self.parent_view.ItemSelect(self.parent_view))
            await interaction.response.edit_message(
                content=f"Selected mon **{self.parent_view.selected_mon['name']}**. Now select an evolution item.",
                view=self.parent_view
            )

    class ItemSelect(Select):
        def __init__(self, parent_view: 'EvolutionFlowView') -> None:
            self.parent_view = parent_view
            options = [discord.SelectOption(label=item, value=item) for item in EVOLUTION_ITEMS]
            super().__init__(placeholder="Select an evolution item", min_values=1, max_values=1, options=options)

        async def callback(self, interaction: discord.Interaction) -> None:
            self.parent_view.evolution_item = self.values[0]
            self.parent_view.clear_items()
            # Gather available species from the selected mon (e.g., species1, species2, species3).
            species_options = [
                self.parent_view.selected_mon.get(f"species{i}", "").strip()
                for i in range(1, 4)
                if self.parent_view.selected_mon.get(f"species{i}", "").strip()
            ]
            if len(species_options) > 1:
                self.parent_view.add_item(self.parent_view.SpeciesSelect(self.parent_view, species_options))
                content = (
                    f"Selected evolution item: **{self.parent_view.evolution_item}**.\n"
                    "Multiple species options found—please select the target species."
                )
            else:
                self.parent_view.selected_species = species_options[0] if species_options else None
                content = (
                    f"Selected evolution item: **{self.parent_view.evolution_item}**.\n"
                    f"Evolving species: **{self.parent_view.selected_species or 'Unknown'}**."
                )
            if self.parent_view.evolution_item.lower() == "digital repair mode":
                await interaction.response.send_modal(self.parent_view.RepairInputModal(self.parent_view))
            else:
                self.parent_view.add_item(self.parent_view.ConfirmButton(self.parent_view))
                await interaction.response.edit_message(content=content, view=self.parent_view)

    class SpeciesSelect(Select):
        def __init__(self, parent_view: 'EvolutionFlowView', species_options: List[str]) -> None:
            self.parent_view = parent_view
            options = [discord.SelectOption(label=sp, value=sp) for sp in species_options]
            super().__init__(placeholder="Select the target species", min_values=1, max_values=1, options=options)

        async def callback(self, interaction: discord.Interaction) -> None:
            self.parent_view.selected_species = self.values[0]
            self.parent_view.add_item(self.parent_view.ConfirmButton(self.parent_view))
            await interaction.response.edit_message(
                content=f"Selected species: **{self.parent_view.selected_species}**. Confirm evolution?",
                view=self.parent_view
            )

    class RepairInputModal(Modal, title="Digital Repair Evolution"):
        repair_input = TextInput(
            label="Enter target species",
            placeholder="Type the species you wish to evolve into",
            required=True
        )
        def __init__(self, parent_view: 'EvolutionFlowView') -> None:
            super().__init__()
            self.parent_view = parent_view

        async def on_submit(self, interaction: discord.Interaction) -> None:
            self.parent_view.repair_input = self.repair_input.value.strip()
            self.parent_view.add_item(self.parent_view.ConfirmButton(self.parent_view))
            await interaction.response.edit_message(
                content=f"Selected repair target: **{self.parent_view.repair_input}**. Confirm evolution?",
                view=self.parent_view
            )

    class ConfirmButton(Button):
        def __init__(self, parent_view: 'EvolutionFlowView') -> None:
            self.parent_view = parent_view
            super().__init__(label="Confirm Evolution", style=discord.ButtonStyle.primary, custom_id="confirm_evolution")

        async def callback(self, interaction: discord.Interaction) -> None:
            response_message = await evolve_mon(
                self.parent_view.user_id,
                self.parent_view.selected_mon["id"],
                self.parent_view.evolution_item,
                selected_species=self.parent_view.selected_species,
                repair_input=self.parent_view.repair_input
            )
            self.parent_view.stop()
            await interaction.response.send_message(response_message, ephemeral=True)