import discord
from discord.ui import Button, Modal, TextInput
from core.database import update_trainer_field
from core.core_views import BaseView
from core.database import pool
from views.mon import TrainerMonsView


def paginate_trainer_dict(trainer: dict, page_size: int = 10, allowed_keys: list = None):
    """
    Splits the trainer dictionary into pages.
    If allowed_keys is provided, only keys in that list are paginated.
    """
    if allowed_keys is not None:
        items = [(k, v) for k, v in trainer.items() if k in allowed_keys]
    else:
        items = list(trainer.items())
    print(items)
    # Sort to ensure a consistent order.
    items.sort(key=lambda x: x[0])
    pages = [items[i:i + page_size] for i in range(0, len(items), page_size)]
    return pages


class TrainerDetailModal(Modal, title="Edit Trainer Field"):
    field_name = TextInput(label="Field", style=discord.TextStyle.short, required=True)
    new_value = TextInput(label="New Value", style=discord.TextStyle.short, required=True)

    def __init__(self, trainer_id: int):
        super().__init__()
        self.trainer_id = trainer_id

    async def on_submit(self, interaction: discord.Interaction):
        field = self.field_name.value.strip()
        value = self.new_value.value.strip()
        try:
            update_trainer_field(self.trainer_id, field, value)
            await interaction.response.send_message(f"Updated {field} to {value}.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Failed to update field: {str(e)}", ephemeral=True)


class TrainerDetailView(discord.ui.View):
    def __init__(self, trainer: dict, current_user_id: str, allowed_keys: list = None):
        super().__init__(timeout=None)
        self.current_user_id = current_user_id
        # Fetch full record from the database if needed
        conn = pool.get_connection()
        try:
            conn.row_factory = lambda cursor, row: {col[0]: row[idx] for idx, col in enumerate(cursor.description)}
            cur = conn.cursor()
            cur.execute("SELECT * FROM trainers WHERE id = ?", (trainer["id"],))
            full_record = cur.fetchone()
            self.full_trainer = full_record if full_record else trainer
        finally:
            pool.return_connection(conn)

        # Use allowed_keys if provided; otherwise, use all keys.
        self.pages = paginate_trainer_dict(self.full_trainer, page_size=10, allowed_keys=allowed_keys)
        self.current_page = 0

        if str(self.full_trainer.get("player_user_id", "")) == current_user_id:
            self.add_item(TrainerEditButton(self.full_trainer["id"]))
        if len(self.pages) > 1:
            self.add_item(TrainerPrevButton())
            self.add_item(TrainerNextButton())

    async def get_detail_embed(self) -> discord.Embed:
        embed = discord.Embed(title=f"Trainer Details: {self.full_trainer.get('character_name', 'Unknown')}")
        embed.add_field(name="Basic Info", value=f"Level: {self.full_trainer.get('level', 'N/A')}", inline=True)
        if self.full_trainer.get("img_link"):
            embed.set_image(url=self.full_trainer["img_link"])
        page = self.pages[self.current_page] if self.pages else []
        if page:
            details_text = "\n".join(f"**{k}:** {v}" for k, v in page)
            if len(details_text) > 1024:
                details_text = details_text[:1021] + "..."
            embed.add_field(name="Details", value=details_text, inline=False)
        embed.set_footer(text=f"Page {self.current_page + 1} of {len(self.pages)}")
        return embed


class TrainerPrevButton(Button):
    def __init__(self):
        super().__init__(label="Previous", style=discord.ButtonStyle.primary)

    async def callback(self, interaction: discord.Interaction):
        view: TrainerDetailView = self.view  # type: ignore
        if view.current_page > 0:
            view.current_page -= 1
            embed = await view.get_detail_embed()
            await interaction.response.edit_message(embed=embed, view=view)
        else:
            await interaction.response.send_message("Already at the first page.", ephemeral=True)

class TrainerNextButton(Button):
    def __init__(self):
        super().__init__(label="Next", style=discord.ButtonStyle.primary)

    async def callback(self, interaction: discord.Interaction):
        view: TrainerDetailView = self.view  # type: ignore
        if view.current_page < len(view.pages) - 1:
            view.current_page += 1
            embed = await view.get_detail_embed()
            await interaction.response.edit_message(embed=embed, view=view)
        else:
            await interaction.response.send_message("Already at the last page.", ephemeral=True)

class TrainerEditButton(Button):
    def __init__(self, trainer_id: int):
        super().__init__(label="Edit", style=discord.ButtonStyle.secondary)
        self.trainer_id = trainer_id

    async def callback(self, interaction: discord.Interaction):
        modal = TrainerDetailModal(self.trainer_id)
        await interaction.response.send_modal(modal)

class PaginatedTrainersView(BaseView):
    def __init__(self, trainers: list, editable: bool, user_id: str):
        super().__init__(timeout=None)
        self.trainers = trainers
        self.editable = editable
        self.user_id = user_id
        self.current_index = 0

    async def get_current_embed(self) -> discord.Embed:
        if not self.trainers:
            title = "No Trainers Found" if self.editable else "No Other Trainers Found"
            description = ("You have no trainers registered. Use the trainer add command."
                           if self.editable else "There are no other trainers available.")
            return discord.Embed(title=title, description=description)
        trainer = self.trainers[self.current_index]
        embed = discord.Embed(title=f"Trainer: {trainer['character_name']}",
                              description=f"Level: {trainer['level']}")
        if trainer.get("main_ref"):
            embed.set_image(url=trainer["main_ref"])
        embed.set_footer(text=f"Trainer {self.current_index + 1} of {len(self.trainers)}")
        return embed

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.primary, custom_id="trainer_prev", row=0)
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.trainers:
            await interaction.response.send_message("No trainers to display.", ephemeral=True)
            return
        self.current_index = (self.current_index - 1) % len(self.trainers)
        embed = await self.get_current_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.primary, custom_id="trainer_next", row=0)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.trainers:
            await interaction.response.send_message("No trainers to display.", ephemeral=True)
            return
        self.current_index = (self.current_index + 1) % len(self.trainers)
        embed = await self.get_current_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Details", style=discord.ButtonStyle.secondary, custom_id="trainer_details", row=1)
    async def details(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.trainers:
            await interaction.response.send_message("No trainers available.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        trainer = self.trainers[self.current_index]
        if self.editable:
            detail_view = EditableTrainerDetailView(trainer, self.user_id)
        else:
            detail_view = BaseTrainerDetailView(trainer)
        embed = await detail_view.get_detail_embed()
        await interaction.followup.send(embed=embed, view=detail_view, ephemeral=True)

    @discord.ui.button(label="Inventory", style=discord.ButtonStyle.secondary, custom_id="trainer_inventory", row=1)
    async def inventory(self, interaction: discord.Interaction, button: discord.ui.Button):
        trainer = self.trainers[self.current_index]
        # Create an inventory view for the current trainer.
        view = TrainerInventoryView(trainer)
        embed = view.get_embed()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(label="Mons", style=discord.ButtonStyle.secondary, custom_id="trainer_mons", row=1)
    async def mons(self, interaction: discord.Interaction, button: discord.ui.Button):
        trainer = self.trainers[self.current_index]
        # Open the mons view (as defined previously).
        view = TrainerMonsView(trainer)
        embed = view.get_current_embed()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(label="Back", style=discord.ButtonStyle.danger, custom_id="trainer_back", row=1)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Returning to main menu...", ephemeral=True)



class BaseTrainerDetailView(discord.ui.View):
    """
    Displays trainer details from the database, organized into sections:

    Trainer Information

    Basic Information:
        - Name
        - Level (displayed as "<level> + <level_modifier>")
        - Currency Amount
        - Species
        - (if present) Species 1, Species 2, Species 3, and Type 1...Type 6

    Basic Information Extended:
        - ID, mon_amount, reference_amount, reference_percent, Gender, Faction

    Profile:
        - nickname, title, ribbon, alteration_level, shiny, alpha, paradox, ability, nature, characteristic

    Favourites:
        - fav_berry, fav_type1, fav_type2, fav_type3, fav_type4, fav_type5, fav_type6

    Resume:
        - gender, pronouns, sexuality, age, birthday, height_cm, height_ft, height_in, birthplace, residence, job

    External Information:
        - theme_song, label, other_profile, label2, google_sheets_link, main_ref, main_ref_artist

    Flavor:
        - quote (if present), tldr

    Mega:
        - mega_evo, mega_main_reference, mega_artist, mega_type1, mega_type2, mega_type3, mega_type4, mega_type5, mega_type6, mega_ability

    Additional Information:
        - additional_ref1, additional_ref1_artist, additional_ref2, additional_ref2_artist

    Badges:
        - badges_earned, badge_amount, frontier_badges_earned, frontier_badges_amount, contest_ribbons_earned

    Progression:
        - achievements, prompts, trainer_progression

    Biography:
        - long_bio
    """

    def __init__(self, trainer: dict):
        super().__init__(timeout=None)
        # Query the full record (every field) for the trainer
        conn = pool.get_connection()
        try:
            conn.row_factory = lambda cursor, row: {col[0]: row[idx] for idx, col in enumerate(cursor.description)}
            cur = conn.cursor()
            cur.execute("SELECT * FROM trainers WHERE id = ?", (trainer["id"],))
            full_record = cur.fetchone()
            self.trainer = full_record if full_record else trainer
        finally:
            pool.return_connection(conn)

    async def get_detail_embed(self) -> discord.Embed:
        embed = discord.Embed(title="Trainer Information", color=discord.Color.blue())

        # --- Basic Information ---
        basic_info = ""
        name = self.trainer.get("character_name")
        level = self.trainer.get("level")
        level_modifier = self.trainer.get("level_modifier", 0)
        currency = self.trainer.get("currency_amount")
        species = self.trainer.get("species")
        if name:
            basic_info += f"**Name:** {name}\n"
        if level is not None and level_modifier is not None:
            basic_info += f"**Level:** {level} + {level_modifier}\n"
        if currency is not None:
            basic_info += f"**Currency Amount:** {currency}\n"
        if species:
            basic_info += f"**Species:** {species}\n"
        # Additional species and types (only if present)
        for key in ["species1", "species2", "species3"]:
            value = self.trainer.get(key)
            if value:
                basic_info += f"**{key.capitalize()}:** {value}\n"
        for key in ["type1", "type2", "type3", "type4", "type5", "type6"]:
            value = self.trainer.get(key)
            if value:
                basic_info += f"**{key.capitalize()}:** {value}\n"
        embed.add_field(name="Basic Information", value=basic_info or "N/A", inline=False)

        # --- Basic Information Extended ---
        basic_extended = ""
        for key in ["id", "mon_amount", "reference_amount", "reference_percent", "gender", "faction"]:
            value = self.trainer.get(key)
            if value not in (None, ""):
                label = key.capitalize() if key not in ["mon_amount", "reference_amount", "reference_percent"] else key
                basic_extended += f"**{label}:** {value}\n"
        if basic_extended:
            embed.add_field(name="Basic Information Extended", value=basic_extended, inline=False)

        # --- Profile ---
        profile = ""
        for key in ["nickname", "title", "ribbon", "alteration_level", "shiny", "alpha", "paradox", "ability", "nature",
                    "characteristic"]:
            value = self.trainer.get(key)
            if value not in (None, ""):
                label = key.replace("_", " ").capitalize()
                profile += f"**{label}:** {value}\n"
        if profile:
            embed.add_field(name="Profile", value=profile, inline=False)

        # --- Favourites ---
        favourites = ""
        for key in ["fav_berry", "fav_type1", "fav_type2", "fav_type3", "fav_type4", "fav_type5", "fav_type6"]:
            value = self.trainer.get(key)
            if value:
                label = key.replace("fav_", "").capitalize()
                favourites += f"**{label}:** {value}\n"
        if favourites:
            embed.add_field(name="Favourites", value=favourites, inline=False)

        # --- Resume ---
        resume = ""
        for key in ["gender", "pronouns", "sexuality", "age", "birthday", "height_cm", "height_ft", "height_in",
                    "birthplace", "residence", "job"]:
            value = self.trainer.get(key)
            if value not in (None, ""):
                label = key.replace("_", " ").capitalize()
                resume += f"**{label}:** {value}\n"
        if resume:
            embed.add_field(name="Resume", value=resume, inline=False)

        # --- External Information ---
        external = ""
        for key in ["theme_song", "label", "other_profile", "label2", "google_sheets_link", "main_ref",
                    "main_ref_artist"]:
            value = self.trainer.get(key)
            if value:
                label = key.replace("_", " ").capitalize()
                external += f"**{label}:** {value}\n"
        if external:
            embed.add_field(name="External Information", value=external, inline=False)

        # --- Flavor ---
        flavor = ""
        # Include "quote" if available; otherwise, just tldr.
        if self.trainer.get("quote"):
            flavor += f"**Quote:** {self.trainer.get('quote')}\n"
        if self.trainer.get("tldr"):
            flavor += f"**Tldr:** {self.trainer.get('tldr')}\n"
        if flavor:
            embed.add_field(name="Flavor", value=flavor, inline=False)

        # --- Mega ---
        mega = ""
        for key in ["mega_evo", "mega_main_reference", "mega_artist", "mega_type1", "mega_type2", "mega_type3",
                    "mega_type4", "mega_type5", "mega_type6", "mega_ability"]:
            value = self.trainer.get(key)
            if value:
                label = key.replace("_", " ").capitalize()
                mega += f"**{label}:** {value}\n"
        if mega:
            embed.add_field(name="Mega", value=mega, inline=False)

        # --- Additional Information ---
        additional = ""
        for key in ["additional_ref1", "additional_ref1_artist", "additional_ref2", "additional_ref2_artist"]:
            value = self.trainer.get(key)
            if value:
                label = key.replace("_", " ").capitalize()
                additional += f"**{label}:** {value}\n"
        if additional:
            embed.add_field(name="Additional Information", value=additional, inline=False)

        # --- Badges ---
        badges = ""
        for key in ["badges_earned", "badge_amount", "frontier_badges_earned", "frontier_badges_amount",
                    "contest_ribbons_earned"]:
            value = self.trainer.get(key)
            if value:
                label = key.replace("_", " ").capitalize()
                badges += f"**{label}:** {value}\n"
        if badges:
            embed.add_field(name="Badges", value=badges, inline=False)

        # --- Progression ---
        progression = ""
        for key in ["achievements", "prompts", "trainer_progression"]:
            value = self.trainer.get(key)
            if value:
                label = key.replace("_", " ").capitalize()
                progression += f"**{label}:** {value}\n"
        if progression:
            embed.add_field(name="Progression", value=progression, inline=False)

        # --- Biography ---
        biography = self.trainer.get("long_bio", "")
        if biography:
            embed.add_field(name="Biography", value=biography, inline=False)

        # Ensure the trainer image is always visible (using a thumbnail)
        if self.trainer.get("main_ref"):
            embed.set_image(url=self.trainer["main_ref"])

        return embed

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.primary, custom_id="detail_prev", row=0)
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page > 0:
            self.current_page -= 1
            embed = await self.get_detail_embed()
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.send_message("Already at the first page.", ephemeral=True)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.primary, custom_id="detail_next", row=0)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.pages and self.current_page < (len(self.pages) - 1):
            self.current_page += 1
            embed = await self.get_detail_embed()
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.send_message("Already at the last page.", ephemeral=True)

    @discord.ui.button(label="Mons", style=discord.ButtonStyle.secondary, custom_id="detail_mons", row=1)
    async def open_mons(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = TrainerMonsView(self.trainer)
        embed = view.get_current_embed()
        await interaction.response.send_message("Trainer's mons:", embed=embed, view=view, ephemeral=True)

    @discord.ui.button(label="Back", style=discord.ButtonStyle.danger, custom_id="detail_back", row=1)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Returning...", ephemeral=True)

class TrainerEditModal(Modal, title="Edit Trainer Detail"):
    """
    Prompts for a field name and new value for the trainer record.
    """
    field = TextInput(label="Field to Edit", placeholder="e.g. level, favorite_color", required=True)
    new_value = TextInput(label="New Value", placeholder="Enter new value", required=True)

    def __init__(self, trainer_id: int):
        super().__init__()
        self.trainer_id = trainer_id

    async def on_submit(self, interaction: discord.Interaction):
        field = self.field.value.strip()
        value = self.new_value.value.strip()
        try:
            update_trainer_field(self.trainer_id, field, value)
            await interaction.response.send_message(f"Updated {field} to {value}.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Failed to update: {str(e)}", ephemeral=True)


class EditableTrainerDetailView(BaseTrainerDetailView):
    """
    Extends BaseTrainerDetailView by adding an Edit button if the current user is the owner.
    """
    def __init__(self, trainer: dict, current_user_id: str):
        super().__init__(trainer)
        self.current_user_id = current_user_id
        # Only add the Edit button if the trainer's owner matches the current user.
        if str(trainer.get("user_id", "")) == current_user_id:
            pass  # We add the button via decorator below.

    @discord.ui.button(label="Edit", style=discord.ButtonStyle.secondary, custom_id="detail_edit", row=0)
    async def edit(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = TrainerEditModal(self.trainer["id"])
        await interaction.response.send_modal(modal)


# Define inventory categories with all the items. (Adjust these lists as needed.)
import discord
import json

# Define inventory categories with the item names exactly as in the inventory JSON.
INVENTORY_CATEGORIES = {
    "ITEMS": [
        "Fertalizer", "Poké Puff", "Charge Capsule", "Scroll of Secrets",
        "Shard", "Bottle Cap", "Gold Bottle Cap", "Z-Crystal",
        "Legacy Leeway", "Daycare Daypass"
    ],
    "BALLS": [
        "Poké Ball", "Cygnus Ball", "Ranger Ball", "Premier Ball",
        "Great Ball", "Ultra Ball", "Master Ball", "Safari Ball",
        "Fast Ball", "Level Ball", "Lure Ball", "Heavy Ball",
        "Love Ball", "Friend Ball", "Moon Ball", "Sport Ball",
        "Net Ball", "Dive Ball", "Nest Ball", "Repeat Ball",
        "Timer Ball", "Luxury Ball", "Dusk Ball", "Heal Ball",
        "Quick Ball", "Marble Ball", "Godly Ball", "Rainbow Ball",
        "Pumpkin Ball", "Slime Ball", "Bat Ball", "Sweet Ball",
        "Ghost Ball", "Spider Ball", "Eye Ball", "Bloody Ball",
        "Patched Ball", "Snow Ball", "Gift Ball", "Ugly Christmas Ball",
        "Snowflake Ball", "Holly Ball", "Candy Cane Ball"
    ],
    "BERRIES": [
        "Mala Berry", "Merco Berry", "Lilan Berry", "Kham Berry",
        "Maizi Berry", "Fani Berry", "Miraca Berry", "Cocon Berry",
        "Durian Berry", "Monel Berry", "Perep Berry", "Addish Berry",
        "Sky Carrot Berry", "Kembre Berry", "Espara Berry", "Patama Berry",
        "Bluk Berry", "Nuevo Berry", "Azzuk Berry", "Mangus Berry",
        "Datei Berry", "Forget-me-not", "Edenweiss"
    ],
    "PASTRIES": [
        "Miraca Pastry", "Cocon Pastry", "Durian Pastry", "Monel Pastry",
        "Perep Pastry", "Addish Pastry", "Sky Carrot Pastry", "Kembre Pastry",
        "Espara Pastry", "Patama Pastry", "Bluk Pastry", "Nuevo Pastry",
        "Azzuk Pastry", "Mangus Pastry", "Datei Pastry"
    ],
    "EVOLUTION ITEMS": [
        "Normal Evolution Stone", "Fire Evolution Stone", "Fighting Evolution Stone",
        "Water Evolution Stone", "Flying Evolution Stone", "Grass Evolution Stone",
        "Poison Evolution Stone", "Electric Evolution Stone", "Ground Evolution Stone",
        "Psychic Evolution Stone", "Rock Evolution Stone", "Ice Evolution Stone",
        "Bug Evolution Stone", "Dragon Evolution Stone", "Ghost Evolution Stone",
        "Dark Evolution Stone", "Steel Evolution Stone", "Fairy Evolution Stone",
        "Void Evolution Stone", "Aurora Evolution Stone", "Digital Bytes",
        "Digital Kilobytes", "Digital Megabytes", "Digital Gigabytes",
        "Digital Petabytes", "Digital Terabytes", "Digital Repair Mode"
    ],
    "EGGS": [
        "Standard Egg", "Incubator", "Fire Nurture Kit", "Water Nurture Kit",
        "Electric Nurture Kit", "Grass Nurture Kit", "Ice Nurture Kit",
        "Fighting Nurture Kit", "Poison Nurture Kit", "Ground Nurture Kit",
        "Flying Nurture Kit", "Psychic Nurture Kit", "Bug Nurture Kit",
        "Rock Nurture Kit", "Ghost Nurture Kit", "Dragon Nurture Kit",
        "Dark Nurture Kit", "Steel Nurture Kit", "Fairy Nurture Kit",
        "Normal Nurture Kit", "Corruption Code", "Repair Code", "Shiny New Code",
        "E-Rank Incense", "D-Rank Incense", "C-Rank Incense", "B-Rank Incense",
        "A-Rank Incense", "S-Rank Incense", "Brave Color Incense",
        "Mysterious Color Incense", "Eerie Color Incense", "Tough Color Incense",
        "Charming Color Incense", "Heartful Color Incense", "Shady Color Incense",
        "Slippery Color Incense", "Wicked Color Incense", "Fire Poffin",
        "Water Poffin", "Electric Poffin", "Grass Poffin", "Ice Poffin",
        "Fighting Poffin", "Poison Poffin", "Ground Poffin", "Flying Poffin",
        "Psychic Poffin", "Bug Poffin", "Rock Poffin", "Ghost Poffin",
        "Dragon Poffin", "Dark Poffin", "Steel Poffin", "Fairy Poffin",
        "Spell Tag", "Summoning Stone", "DigiMeat", "DigiTofu", "Soothe Bell",
        "Broken Bell", "#Data Tag", "#Vaccine Tag", "#Virus Tag", "#Free Tag",
        "#Variable Tag", "DNA Splicer", "Hot Chocolate", "Chocolate Milk",
        "Strawberry Milk", "Vanilla Ice Cream", "Strawberry Ice Cream",
        "Chocolate Ice Cream", "Input Field", "Drop Down", "Radio Buttons"
    ],
    "COLLECTION": [
        "Resolution Rocket", "Love Velvet Cake", "Lucky Leprechaun’s Loot",
        "Can’t Believe It’s Not Butter", "Bunny’s Basket Bonanza",
        "Star-Spangled Sparkler", "Fright Night Fudge", "Turkey Trot Tonic",
        "Jolly Holly Jamboree", "Sweet Shofar Surprise", "Day of Atonement Amulet",
        "Harvest Haven Hummus", "Latke Lightning in a Jar", "Sectored Cookie",
        "Matzah Marvel", "Frosty Czar’s Confection", "Snowflake Samovar",
        "Brave Bear Barrel", "Victory Vodka Vortex", "Pancake Palooza",
        "Diwali Dazzle Diyas", "Color Carnival Concoction", "Raksha Rhapsody",
        "Ganesh’s Glorious Goodie", "Tricolor Triumph Tonic", "Lunar Lantern Loot",
        "Dragon Dance Delight", "Fortune Cookie Fusions"
    ],
    "HELD ITEMS": [
        "Mega Stone"
    ],
    "SEALS": [
        "White Smoke Sticker", "Bolt Sticker", "Blue Bubble Sticker",
        "Fire Sticker", "Red Ribbon Sticker", "Wind-Blown Leaves Sticker",
        "Misty Swirl Sticker"
    ]
}


class TrainerInventoryView(discord.ui.View):
    def __init__(self, trainer: dict):
        super().__init__(timeout=None)
        # Parse the inventory JSON from the trainer record.
        inv_str = trainer.get("inventory", "{}")
        try:
            self.inventory = json.loads(inv_str)
        except Exception:
            self.inventory = {}

        # Build pages for each category.
        # For each category in INVENTORY_CATEGORIES, read the corresponding sub-dictionary
        # from the trainer inventory; if missing, default to an empty dict.
        self.pages = []
        for category, items in INVENTORY_CATEGORIES.items():
            cat_inventory = self.inventory.get(category, {})
            page_lines = []
            for item in items:
                qty = cat_inventory.get(item, 0)
                page_lines.append(f"**{item}:** {qty}")
            page_text = "\n".join(page_lines)
            self.pages.append((category, page_text))
        self.current_page = 0

    def get_embed(self) -> discord.Embed:
        category, page_text = self.pages[self.current_page]
        embed = discord.Embed(
            title=f"Inventory - {category}",
            description=page_text,
            color=discord.Color.green()
        )
        embed.set_footer(text=f"Page {self.current_page + 1} of {len(self.pages)}")
        return embed

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.primary, custom_id="inv_prev", row=0)
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page > 0:
            self.current_page -= 1
            await interaction.response.edit_message(embed=self.get_embed(), view=self)
        else:
            await interaction.response.send_message("Already at the first page.", ephemeral=True)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.primary, custom_id="inv_next", row=0)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page < len(self.pages) - 1:
            self.current_page += 1
            await interaction.response.edit_message(embed=self.get_embed(), view=self)
        else:
            await interaction.response.send_message("Already at the last page.", ephemeral=True)
