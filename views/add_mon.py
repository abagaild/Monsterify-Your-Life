import discord
from discord.ui import View, Button, Select
import asyncio

from core.trainer import get_trainers, fetch_trainer_by_name  # to retrieve trainer info
from core.mon import add_mon, add_full_mon  # simple and complex mon insertion functions


# ==================================================
# Step 1. Trainer Selection for Mon Addition
# ==================================================

class TrainerSelectForMonView(View):
    def __init__(self, user_id: str):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.selected_trainer = None
        trainers = get_trainers(user_id)
        options = []
        for t in trainers:
            options.append(discord.SelectOption(label=t["character_name"], value=str(t["id"])))
        # Add an option to manually enter trainer.
        options.append(discord.SelectOption(label="Manually Enter Trainer", value="manual"))
        self.add_item(TrainerSelectDropdown(options))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == int(self.user_id)


class TrainerSelectDropdown(Select):
    def __init__(self, options):
        super().__init__(placeholder="Select a trainer for the mon", options=options, min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        value = self.values[0]
        view: TrainerSelectForMonView = self.view  # type: ignore
        if value == "manual":
            await interaction.response.send_message("Please enter the trainer name in chat:", ephemeral=True)

            def check(m: discord.Message):
                return m.author.id == interaction.user.id and m.channel.id == interaction.channel.id

            try:
                msg = await interaction.client.wait_for("message", check=check, timeout=60)
                trainer_name = msg.content.strip()
                trainer = fetch_trainer_by_name(trainer_name)
                if not trainer:
                    await interaction.followup.send("Trainer not found.", ephemeral=True)
                    return
                view.selected_trainer = trainer
                await interaction.followup.send(f"Trainer '{trainer['character_name']}' selected.", ephemeral=True)
                await send_mon_path_selection(interaction, trainer)
            except asyncio.TimeoutError:
                await interaction.followup.send("Timed out waiting for trainer name.", ephemeral=True)
        else:
            trainer_id = int(value)
            trainers = get_trainers(str(interaction.user.id))
            trainer = next((t for t in trainers if t["id"] == trainer_id), None)
            if not trainer:
                await interaction.response.send_message("Trainer not found.", ephemeral=True)
                return
            view.selected_trainer = trainer
            await interaction.response.send_message(f"Trainer '{trainer['character_name']}' selected.", ephemeral=True)
            await send_mon_path_selection(interaction, trainer)


async def send_trainer_select_for_mon(interaction: discord.Interaction, user_id: str):
    view = TrainerSelectForMonView(user_id)
    await interaction.followup.send("Please select the trainer to add the mon to:", view=view, ephemeral=True)


# ==================================================
# Step 2. Path Selection: Simple vs Complex
# ==================================================

async def send_mon_path_selection(interaction: discord.Interaction, trainer: dict):
    """Send a view that lets the user choose between a simple or complex mon creation flow."""
    view = AddMonPathSelectionView(trainer)
    await interaction.followup.send("Do you want to add the mon via a simple or complex path?", view=view,
                                    ephemeral=True)


class AddMonPathSelectionView(View):
    def __init__(self, trainer: dict):
        super().__init__(timeout=None)
        self.trainer = trainer

    @discord.ui.button(label="Simple Add Mon", style=discord.ButtonStyle.primary)
    async def simple(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Starting simple add mon flow...", ephemeral=True)
        await start_mon_conversation_simple(interaction, self.trainer)

    @discord.ui.button(label="Complex Add Mon", style=discord.ButtonStyle.secondary)
    async def complex(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Starting complex add mon flow...", ephemeral=True)
        await start_mon_conversation_complex(interaction, self.trainer)


# ==================================================
# Step 3. Mon Conversation Flows
# ==================================================

async def ask_mon_question(interaction: discord.Interaction, question: str) -> str:
    """Sends a question and waits for a reply."""
    await interaction.followup.send(question, ephemeral=True)

    def check(m: discord.Message):
        return m.author.id == interaction.user.id and m.channel.id == interaction.channel.id

    try:
        msg = await interaction.client.wait_for("message", check=check, timeout=60)
        return msg.content.strip()
    except asyncio.TimeoutError:
        await interaction.followup.send("Timed out waiting for your response. Please try again.", ephemeral=True)
        raise


# --- Simple Flow ---
async def start_mon_conversation_simple(interaction: discord.Interaction, trainer: dict):
    """
    Simple add mon flow. Asks for:
      - mon name (required)
      - mon level (default 1 if null)
      - mon species 1 (required), species 2, species 3
      - mon type 1 (required), type 2, type 3, type 4, type 5
      - mon attribute (optional)
      - mon reference image URL (optional)
    """
    mon_data = {}
    # mon name (required)
    while True:
        name = await ask_mon_question(interaction, "Enter mon name (required):")
        if name.lower() == "null" or not name:
            await interaction.followup.send("Mon name is required.", ephemeral=True)
        else:
            mon_data["name"] = name
            break
    # mon level
    level = await ask_mon_question(interaction, "Enter mon level (or 'null' for default 1):")
    mon_data["level"] = int(level) if level.lower() != "null" and level.isdigit() else 1
    # species1 (required)
    while True:
        sp1 = await ask_mon_question(interaction, "Enter mon species 1 (required):")
        if sp1.lower() == "null" or not sp1:
            await interaction.followup.send("Species 1 is required.", ephemeral=True)
        else:
            mon_data["species1"] = sp1
            break
    # species2
    sp2 = await ask_mon_question(interaction, "Enter mon species 2 (or 'null'):")
    mon_data["species2"] = None if sp2.lower() == "null" else sp2
    # species3
    sp3 = await ask_mon_question(interaction, "Enter mon species 3 (or 'null'):")
    mon_data["species3"] = None if sp3.lower() == "null" else sp3
    # type1 (required)
    while True:
        t1 = await ask_mon_question(interaction, "Enter mon type 1 (required):")
        if t1.lower() == "null" or not t1:
            await interaction.followup.send("Type 1 is required.", ephemeral=True)
        else:
            mon_data["type1"] = t1
            break
    # type2
    t2 = await ask_mon_question(interaction, "Enter mon type 2 (or 'null'):")
    mon_data["type2"] = None if t2.lower() == "null" else t2
    # type3
    t3 = await ask_mon_question(interaction, "Enter mon type 3 (or 'null'):")
    mon_data["type3"] = None if t3.lower() == "null" else t3
    # type4
    t4 = await ask_mon_question(interaction, "Enter mon type 4 (or 'null'):")
    mon_data["type4"] = None if t4.lower() == "null" else t4
    # type5
    t5 = await ask_mon_question(interaction, "Enter mon type 5 (or 'null'):")
    mon_data["type5"] = None if t5.lower() == "null" else t5
    # attribute
    attr = await ask_mon_question(interaction, "Enter mon attribute (or 'null'):")
    mon_data["attribute"] = None if attr.lower() == "null" else attr
    # reference image URL
    img = await ask_mon_question(interaction, "Enter mon reference image URL (or 'null'):")
    mon_data["img_link"] = None if img.lower() == "null" else img

    # Insert mon using the simple add_mon function.
    try:
        from core.mon import \
            add_mon  # add_mon(trainer_id, player, name, level, species1, species2, species3, type1, type2, type3, type4, type5, attribute, img_link)
        mon_id = add_mon(trainer["id"], str(interaction.user.id),
                         mon_data["name"],
                         mon_data["level"],
                         mon_data["species1"],
                         mon_data.get("species2"),
                         mon_data.get("species3"),
                         mon_data["type1"],
                         mon_data.get("type2"),
                         mon_data.get("type3"),
                         mon_data.get("type4"),
                         mon_data.get("type5"),
                         mon_data.get("attribute"),
                         mon_data.get("img_link"))
        await interaction.followup.send(f"Mon '{mon_data['name']}' added successfully (ID: {mon_id})!", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"An error occurred while adding mon: {e}", ephemeral=True)
        return

    await ask_add_another_mon(interaction, trainer)


# --- Complex Flow ---
async def start_mon_conversation_complex(interaction: discord.Interaction, trainer: dict):
    """
    Complex add mon flow.
    This flow prompts for a larger set of fields.
    (For brevity, only a subset is shown; expand the list as needed.)
    """
    mon_data = {}
    fields = [
        ("name", "Enter mon name (required):", True),
        ("level", "Enter mon level (required, number):", True),
        ("species1", "Enter mon species 1 (required):", True),
        ("species2", "Enter mon species 2 (or 'null'):", False),
        ("species3", "Enter mon species 3 (or 'null'):", False),
        ("type1", "Enter mon type 1 (required):", True),
        ("type2", "Enter mon type 2 (or 'null'):", False),
        ("type3", "Enter mon type 3 (or 'null'):", False),
        ("type4", "Enter mon type 4 (or 'null'):", False),
        ("type5", "Enter mon type 5 (or 'null'):", False),
        ("attribute", "Enter mon attribute (or 'null'):", False),
        ("img_link", "Enter mon reference image URL (or 'null'):", False),
        ("hp_total", "Enter mon total HP (or 'null'):", False),
        ("atk_total", "Enter mon total ATK (or 'null'):", False),
        ("def_total", "Enter mon total DEF (or 'null'):", False),
        ("spa_total", "Enter mon total SPA (or 'null'):", False),
        ("spd_total", "Enter mon total SPD (or 'null'):", False),
        ("spe_total", "Enter mon total SPE (or 'null'):", False),
        ("ability", "Enter mon ability (or 'null'):", False),
        ("talk", "Enter mon talk (or 'null'):", False)
        # Add more fields as needed...
    ]
    for key, prompt, required in fields:
        answer = None
        while True:
            answer = await ask_mon_question(interaction, prompt)
            if required and (answer.lower() == "null" or answer == ""):
                await interaction.followup.send(f"'{key}' is required. Please enter a valid value.", ephemeral=True)
            else:
                break
        mon_data[key] = answer if answer.lower() != "null" else None
    try:
        # Convert numeric fields as needed.
        mon_data["level"] = int(mon_data["level"]) if mon_data["level"] is not None and mon_data[
            "level"].isdigit() else 1
    except:
        mon_data["level"] = 1
    try:
        from core.mon import add_full_mon  # add_full_mon(trainer_id, player, mon_data) should return mon_id
        mon_id = add_full_mon(trainer["id"], str(interaction.user.id), mon_data)
        await interaction.followup.send(f"Mon '{mon_data['name']}' added successfully (ID: {mon_id})!", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"An error occurred while adding mon: {e}", ephemeral=True)
        return
    await ask_add_another_mon(interaction, trainer)


# ==================================================
# Step 4. Ask to Add Another Mon or Return to Main Menu
# ==================================================

async def ask_add_another_mon(interaction: discord.Interaction, trainer: dict):
    await interaction.followup.send("Would you like to add another mon? (yes/no)", ephemeral=True)

    def check(m: discord.Message):
        return m.author.id == interaction.user.id and m.channel.id == interaction.channel.id

    try:
        msg = await interaction.client.wait_for("message", check=check, timeout=60)
        response = msg.content.strip().lower()
        if response in ["yes", "y"]:
            await interaction.followup.send("Restarting add mon flow...", ephemeral=True)
            await send_trainer_select_for_mon(interaction, str(interaction.user.id))
        else:
            await interaction.followup.send("Returning to main menu...", ephemeral=True)
            from views.mainMenu import MainMenuView
            await interaction.followup.send(view=MainMenuView(), ephemeral=True)
    except asyncio.TimeoutError:
        await interaction.followup.send("Timed out. Returning to main menu...", ephemeral=True)
        from views.mainMenu import MainMenuView
        await interaction.followup.send(view=MainMenuView(), ephemeral=True)
