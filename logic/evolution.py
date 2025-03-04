import discord
from discord.ui import Select, Modal, TextInput, Button, View
from typing import List, Optional
from logic.market.witchs_hut import evolve_mon
from core.trainer import get_trainers
from core.database import fetch_all

EVOLUTION_ITEMS: List[str] = [
    "Normal Evolution Stone", "Fire Evolution Stone", "Fighting Evolution Stone", "Water Evolution Stone",
    "Flying Evolution Stone", "Grass Evolution Stone", "Poison Evolution Stone", "Electric Evolution Stone",
    "Ground Evolution Stone", "Psychic Evolution Stone", "Rock Evolution Stone", "Ice Evolution Stone",
    "Bug Evolution Stone", "Dragon Evolution Stone", "Ghost Evolution Stone", "Dark Evolution Stone",
    "Steel Evolution Stone", "Fairy Evolution Stone", "Void Evolution Stone", "Auroras Evolution Stone",
    "Digital Bytes", "Digital Kilobytes", "Digital Megabytes", "Digital Gigabytes", "Digital Petabytes",
    "Digital Repair Mode"
]

def get_full_mons_for_trainer(trainer_id: int) -> List[dict]:
    rows = fetch_all("SELECT mon_id, mon_name, species1, species2, species3, trainer_id FROM mons WHERE trainer_id = ?", (trainer_id,))
    return [
        {
            "id": row["mon_id"],
            "mon_name": row["mon_name"],
            "species1": row["species1"] or "",
            "species2": row["species2"] or "",
            "species3": row["species3"] or "",
            "trainer_id": row["trainer_id"]
        }
        for row in rows
    ]

class EvolutionFlowView(View):
    """
    Guides the player through the evolution process.
    """
    def __init__(self, user_id: str) -> None:
        super().__init__(timeout=180)
        self.user_id: str = user_id
        self.selected_trainer: Optional[dict] = None
        self.selected_mon: Optional[dict] = None
        self.evolution_item: Optional[str] = None
        self.selected_species: Optional[str] = None
        self.repair_input: Optional[str] = None
        self.clear_items()
        self.add_item(self.TrainerSelect(self))

    class TrainerSelect(Select):
        def __init__(self, parent_view: 'EvolutionFlowView') -> None:
            self.parent_view = parent_view
            trainers = get_trainers(parent_view.user_id)
            options = [discord.SelectOption(label=t["name"], value=str(t["id"])) for t in trainers]
            super().__init__(placeholder="Select your trainer", min_values=1, max_values=1, options=options)

        async def callback(self, interaction: discord.Interaction) -> None:
            trainer_id = int(self.values[0])
            self.parent_view.selected_trainer = next(
                t for t in get_trainers(self.parent_view.user_id) if t["id"] == trainer_id
            )
            self.parent_view.clear_items()
            self.parent_view.add_item(self.parent_view.MonSelect(self.parent_view))
            await interaction.response.edit_message(
                content=f"Trainer **{self.parent_view.selected_trainer['name']}** selected. Now select a mon to evolve:",
                view=self.parent_view
            )

    class MonSelect(Select):
        def __init__(self, parent_view: 'EvolutionFlowView') -> None:
            self.parent_view = parent_view
            mons = get_full_mons_for_trainer(parent_view.selected_trainer["id"])
            options = [discord.SelectOption(label=mon["mon_name"], value=str(mon["id"])) for mon in mons]
            super().__init__(placeholder="Select a mon to evolve", min_values=1, max_values=1, options=options)

        async def callback(self, interaction: discord.Interaction) -> None:
            mon_id = int(self.values[0])
            self.parent_view.selected_mon = next(
                m for m in get_full_mons_for_trainer(self.parent_view.selected_trainer["id"]) if m["id"] == mon_id
            )
            self.parent_view.clear_items()
            self.parent_view.add_item(self.parent_view.ItemSelect(self.parent_view))
            await interaction.response.edit_message(
                content=f"Selected mon **{self.parent_view.selected_mon['mon_name']}**. Now select an evolution item:",
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
            if self.parent_view.evolution_item == "Digital Repair Mode":
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
