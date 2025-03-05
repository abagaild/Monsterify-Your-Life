from discord.ui import View, Button
import asyncio
import discord
from core.database import execute_query
# Make sure your core.trainer module does not conflict – we now use only add_full_trainer below.

class AddTrainerEmbedView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Add a trainer for yourself", style=discord.ButtonStyle.primary)
    async def add_self(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Starting trainer creation flow for yourself...", ephemeral=True)
        await start_trainer_conversation(interaction, user_id=str(interaction.user.id))

    @discord.ui.button(label="Add an NPC/Other Player's Trainer", style=discord.ButtonStyle.secondary)
    async def add_other(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Please enter the target User ID in the chat:", ephemeral=True)
        def check(m: discord.Message):
            return m.author.id == interaction.user.id and m.channel.id == interaction.channel.id
        try:
            msg = await interaction.client.wait_for("message", check=check, timeout=60)
            target_user_id = msg.content.strip()
            await interaction.followup.send(f"Starting trainer creation flow for user ID: {target_user_id}", ephemeral=True)
            await start_trainer_conversation(interaction, user_id=target_user_id)
        except asyncio.TimeoutError:
            await interaction.followup.send("Timed out waiting for the user ID.", ephemeral=True)

async def ask_question(interaction: discord.Interaction, question: str) -> str:
    """Sends a question and waits for the user’s reply."""
    await interaction.followup.send(question, ephemeral=True)
    def check(m: discord.Message):
        return m.author.id == interaction.user.id and m.channel.id == interaction.channel.id
    try:
        msg = await interaction.client.wait_for("message", check=check, timeout=60)
        return msg.content.strip()
    except asyncio.TimeoutError:
        await interaction.followup.send("Timed out waiting for your response. Please try again.", ephemeral=True)
        raise

async def start_trainer_conversation(interaction: discord.Interaction, user_id: str):
    """
    Runs the conversation flow to collect trainer details.
    For every field (except character_name) the user may type 'null' to leave it blank.
    """
    trainer_data = {}
    # Each tuple: (field_key, prompt text, required flag)
    fields = [
        ("character_name", "Enter Character Name (required):", True),
        ("nickname", "Enter Nickname (or type 'null' to skip):", False),
        ("species", "Enter Species (or type 'null'):", False),
        ("faction", "Enter Faction (or type 'null'):", False),
        ("species1", "Enter species1 (or type 'null'):", False),
        ("species2", "Enter species2 (or type 'null'):", False),
        ("species3", "Enter species3 (or type 'null'):", False),
        ("type1", "Enter type1 (or type 'null'):", False),
        ("type2", "Enter type2 (or type 'null'):", False),
        ("type3", "Enter type3 (or type 'null'):", False),
        ("type4", "Enter type4 (or type 'null'):", False),
        ("type5", "Enter type5 (or type 'null'):", False),
        ("type6", "Enter type6 (or type 'null'):", False),
        ("alteration_level", "Enter alteration level (or type 'null'):", False),
        ("ability", "Enter ability (or type 'null'):", False),
        ("nature", "Enter nature (or type 'null'):", False),
        ("characteristic", "Enter characteristic (or type 'null'):", False),
        ("fav_berry", "Enter favorite berry (or type 'null'):", False),
        ("fav_type1", "Enter favorite type1 (or type 'null'):", False),
        ("fav_type2", "Enter favorite type2 (or type 'null'):", False),
        ("fav_type3", "Enter favorite type3 (or type 'null'):", False),
        ("fav_type4", "Enter favorite type4 (or type 'null'):", False),
        ("fav_type5", "Enter favorite type5 (or type 'null'):", False),
        ("fav_type6", "Enter favorite type6 (or type 'null'):", False),
        ("gender", "Enter gender (or type 'null'):", False),
        ("pronouns", "Enter pronouns (or type 'null'):", False),
        ("sexuality", "Enter sexuality (or type 'null'):", False),
        ("age", "Enter age (or type 'null'):", False),
        ("birthday", "Enter birthday (or type 'null'):", False),
        ("height_cm", "Enter height in cm (or type 'null'):", False),
        ("height_ft", "Enter height in feet (or type 'null'):", False),
        ("height_in", "Enter height in inches (or type 'null'):", False),
        ("birthplace", "Enter birthplace (or type 'null'):", False),
        ("residence", "Enter residence (or type 'null'):", False),
        ("job", "Enter job (or type 'null'):", False),
        ("main_ref", "Enter main reference (or type 'null'):", False),
        ("main_ref_artist", "Enter main reference artist (or type 'null'):", False),
        ("quote", "Enter quote (or type 'null'):", False),
        ("tldr", "Enter a short description (tldr) (or type 'null'):", False),
        ("long_bio", "Enter a long biography (or type 'null'):", False)
    ]

    try:
        for key, prompt, required in fields:
            answer = None
            # Loop until a valid answer is provided for required fields
            while True:
                answer = await ask_question(interaction, prompt)
                if required and (answer.lower() == "null" or answer == ""):
                    await interaction.followup.send(f"'{key}' is required. Please enter a valid value.", ephemeral=True)
                else:
                    break
            trainer_data[key] = None if answer.lower() == "null" else answer

        # Insert the trainer record using all collected fields.
        add_full_trainer(user_id, trainer_data)
        await interaction.followup.send(f"Trainer '{trainer_data['character_name']}' added successfully!", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"An error occurred during trainer creation: {e}", ephemeral=True)

def add_full_trainer(user_id: str, trainer_data: dict):
    """
    Inserts a new trainer into the trainers table using all provided fields.
    It uses the following columns:
      player_user_id, character_name, nickname, species, faction, species1, species2, species3,
      type1, type2, type3, type4, type5, type6, alteration_level, ability, nature, characteristic,
      fav_berry, fav_type1, fav_type2, fav_type3, fav_type4, fav_type5, fav_type6, gender, pronouns,
      sexuality, age, birthday, height_cm, height_ft, height_in, birthplace, residence, job, main_ref,
      main_ref_artist, quote, tldr, long_bio
    """
    # List of keys (fields) collected in the conversation (41 fields).
    keys = [
        "character_name",
        "nickname",
        "species",
        "faction",
        "species1",
        "species2",
        "species3",
        "type1",
        "type2",
        "type3",
        "type4",
        "type5",
        "type6",
        "alteration_level",
        "ability",
        "nature",
        "characteristic",
        "fav_berry",
        "fav_type1",
        "fav_type2",
        "fav_type3",
        "fav_type4",
        "fav_type5",
        "fav_type6",
        "gender",
        "pronouns",
        "sexuality",
        "age",
        "birthday",
        "height_cm",
        "height_ft",
        "height_in",
        "birthplace",
        "residence",
        "job",
        "main_ref",
        "main_ref_artist",
        "quote",
        "tldr",
        "long_bio"
    ]
    # Build a tuple of values for these keys, defaulting to None if not provided.
    values = tuple(trainer_data.get(key, None) for key in keys)
    # The INSERT statement includes player_user_id first.
    query = f"""
    INSERT INTO trainers (
        player_user_id,
        character_name,
        nickname,
        species,
        faction,
        species1,
        species2,
        species3,
        type1,
        type2,
        type3,
        type4,
        type5,
        type6,
        alteration_level,
        ability,
        nature,
        characteristic,
        fav_berry,
        fav_type1,
        fav_type2,
        fav_type3,
        fav_type4,
        fav_type5,
        fav_type6,
        gender,
        pronouns,
        sexuality,
        age,
        birthday,
        height_cm,
        height_ft,
        height_in,
        birthplace,
        residence,
        job,
        main_ref,
        main_ref_artist,
        quote,
        tldr,
        long_bio
    ) VALUES ({', '.join('?' for _ in range(len(keys)+1))})
    """
    # Prepend user_id so the parameters tuple has 42 elements.
    params = (user_id,) + values
    execute_query(query, params)
