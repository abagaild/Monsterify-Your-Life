import discord
from discord.ui import View, Button, Modal, TextInput
import core.mon
from core.database import update_mon_row, fetch_mon_by_name
from core.database import pool

def paginate_dict(data: dict, page_size: int = 10):
    items = list(data.items())
    items.sort(key=lambda x: x[0])
    pages = [items[i:i + page_size] for i in range(0, len(items), page_size)]
    return pages


class MonsDetailModal(Modal, title="Edit Mon Field"):
    field_name = TextInput(label="Field", style=discord.TextStyle.short, required=True)
    new_value = TextInput(label="New Value", style=discord.TextStyle.short, required=True)

    def __init__(self, mon_id: int):
        super().__init__()
        self.mon_id = mon_id

    async def on_submit(self, interaction: discord.Interaction):
        from core.database import update_mon_row  # make sure update_mon_row is imported
        field = self.field_name.value.strip()
        value = self.new_value.value.strip()
        try:
            update_mon_row(self.mon_id, {field: value})
            await interaction.response.send_message(f"Updated {field} to {value}.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Failed to update field: {str(e)}", ephemeral=True)


class MonsDetailView(discord.ui.View):
    """
    Displays detailed Pokémon information with custom sections:
    - General Information: includes Level, Trainer Number, Box Number,
      combined Species (species1 / species2 / species3) and combined Types (type1 / type2 / … / type5),
      plus the attribute.
    - Additional sections for Status, Mega info, Battle Stats, and Profile.
    """

    def __init__(self, mon: dict, editable: bool):
        super().__init__(timeout=None)
        self.editable = editable
        # Query the full mon record from the database
        conn = pool.get_connection()
        try:
            conn.row_factory = lambda cursor, row: {col[0]: row[idx] for idx, col in enumerate(cursor.description)}
            cur = conn.cursor()
            cur.execute("SELECT * FROM mons WHERE mon_id = ?", (mon["mon_id"],))
            full_record = cur.fetchone()
            self.full_mon = full_record if full_record else mon
        finally:
            pool.return_connection(conn)


    async def get_embed(self) -> discord.Embed:
        mon_name = self.full_mon.get("name", "Unknown")
        embed = discord.Embed(title=f"Pokémon Details: {mon_name}",
                              color=discord.Color.purple())

        # --- General Information ---
        level = self.full_mon.get("level", "N/A")
        trainer_number = self.full_mon.get("mon_trainer_number", "N/A")
        box_number = self.full_mon.get("box_number", "N/A")
        # Combine species (only include those that have a value)
        species_list = [self.full_mon.get("species1"), self.full_mon.get("species2"), self.full_mon.get("species3")]
        species_text = " / ".join([s for s in species_list if s])
        # Combine types similarly
        types_list = [self.full_mon.get("type1"), self.full_mon.get("type2"), self.full_mon.get("type3"),
                      self.full_mon.get("type4"), self.full_mon.get("type5")]
        types_text = " / ".join([t for t in types_list if t])
        attribute = self.full_mon.get("attribute", "N/A")

        general = f"**Level:** {level}\n"
        general += f"**Trainer Number:** {trainer_number}\n"
        general += f"**Box Number:** {box_number}\n"
        if species_text:
            general += f"**Species:** {species_text}\n"
        if types_text:
            general += f"**Types:** {types_text}\n"
        general += f"**Attribute:** {attribute}\n"
        embed.add_field(name="General Information", value=general, inline=False)

        # --- Status Information ---
        status = ""
        for key in ["acquired", "poke_ball", "talk", "shiny", "alpha", "shadow", "paradox", "paradox_type", "fused",
                    "pokerus"]:
            value = self.full_mon.get(key)
            if value not in (None, ""):
                label = key.replace("_", " ").capitalize()
                status += f"**{label}:** {value}\n"
        if status:
            embed.add_field(name="Status Information", value=status, inline=False)

        # --- Mega Information ---
        mega = ""
        for key in ["mega_stone", "mega_image", "mega_type1", "mega_type2", "mega_type3", "mega_type4", "mega_type5",
                    "mega_type6", "mega_ability", "mega_stat_bonus"]:
            value = self.full_mon.get(key)
            if value not in (None, ""):
                label = key.replace("_", " ").capitalize()
                mega += f"**{label}:** {value}\n"
        if mega:
            embed.add_field(name="Mega", value=mega, inline=False)

        # --- Battle Stats ---
        stats = ""
        for stat in ["hp_total", "hp_ev", "hp_iv", "atk_total", "atk_ev", "atk_iv", "def_total", "def_ev", "def_iv",
                     "spa_total", "spa_ev", "spa_iv", "spd_total", "spd_ev", "spd_iv", "spe_total", "spe_ev", "spe_iv"]:
            value = self.full_mon.get(stat)
            if value not in (None, ""):
                stats += f"**{stat.upper()}:** {value}\n"
        if stats:
            embed.add_field(name="Battle Stats", value=stats, inline=False)

        # --- Profile & Additional ---
        profile = ""
        for key in ["moveset", "friendship", "gender", "pronouns", "nature", "characteristic",
                    "fav_berry", "held_item", "seal", "mark", "date_met", "where_met", "talking",
                    "height_m", "height_imperial", "tldr", "og_trainer_id", "og_trainer_name", "bio"]:
            value = self.full_mon.get(key)
            if value not in (None, ""):
                label = key.replace("_", " ").capitalize()
                profile += f"**{label}:** {value}\n"
        if profile:
            embed.add_field(name="Profile & Additional", value=profile, inline=False)

        # Set the main image and thumbnail if available
        if self.full_mon.get("img_link"):
            embed.set_image(url=self.full_mon["img_link"])

        return embed

    @discord.ui.button(label="Edit", style=discord.ButtonStyle.secondary, custom_id="mon_edit")
    async def edit(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = MonsDetailModal(self.full_mon["mon_id"])
        await interaction.response.send_modal(modal)

class MonsPrevButton(Button):
    def __init__(self):
        super().__init__(label="Previous", style=discord.ButtonStyle.primary)

    async def callback(self, interaction: discord.Interaction):
        view: MonsDetailView = self.view  # type: ignore
        if view.current_page > 0:
            view.current_page -= 1
            await interaction.response.edit_message(embed=await view.get_embed(), view=view)
        else:
            await interaction.response.send_message("Already at the first page.", ephemeral=True)

class MonsNextButton(Button):
    def __init__(self):
        super().__init__(label="Next", style=discord.ButtonStyle.primary)

    async def callback(self, interaction: discord.Interaction):
        view: MonsDetailView = self.view  # type: ignore
        if view.current_page < len(view.pages) - 1:
            view.current_page += 1
            await interaction.response.edit_message(embed=await view.get_embed(), view=view)
        else:
            await interaction.response.send_message("Already at the last page.", ephemeral=True)

class MonsEditButton(Button):
    def __init__(self, mon_id: int):
        super().__init__(label="Edit", style=discord.ButtonStyle.secondary)
        self.mon_id = mon_id

    async def callback(self, interaction: discord.Interaction):
        modal = MonsDetailModal(self.mon_id)
        await interaction.response.send_modal(modal)


class TrainerMonsView(discord.ui.View):
    """
    A view for cycling through a trainer’s mons.
    If a mon has a primary image (img_link) and a reference image (box_img_link),
    they are displayed as the main image and thumbnail, respectively.
    """
    def __init__(self, trainer: dict):
        super().__init__(timeout=None)
        self.trainer = trainer
        # Expect core.mon.get_mons_for_trainer to return a list of mon dictionaries.
        self.mons = core.mon.get_mons_for_trainer(trainer['id'])
        self.current_index = 0

    def get_current_embed(self) -> discord.Embed:
        if not self.mons:
            return discord.Embed(title="No Mons Found", description="This trainer has no mons registered.")
        mon = self.mons[self.current_index]
        embed = discord.Embed(title=f"Mon: {mon['name']}", description=f"Level: {mon['level']}")
        # Show primary mon image and use box image as thumbnail if available.
        if mon.get("img_link"):
            embed.set_image(url=mon["img_link"])
        if mon.get("box_img_link"):
            embed.set_thumbnail(url=mon["box_img_link"])
        embed.set_footer(text=f"Mon {self.current_index + 1} of {len(self.mons)}")
        return embed

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.primary, custom_id="mons_prev", row=0)
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.mons:
            await interaction.response.send_message("No mons to display.", ephemeral=True)
            return
        self.current_index = (self.current_index - 1) % len(self.mons)
        embed = self.get_current_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.primary, custom_id="mons_next", row=0)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.mons:
            await interaction.response.send_message("No mons to display.", ephemeral=True)
            return
        self.current_index = (self.current_index + 1) % len(self.mons)
        embed = self.get_current_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Details", style=discord.ButtonStyle.secondary, custom_id="mons_details", row=1)
    async def details(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.mons:
            await interaction.response.send_message("No mons to display.", ephemeral=True)
            return
        mon = self.mons[self.current_index]
        # If the mon belongs to the user, allow editing.
        if mon.get("player") == str(interaction.user.id):
            detail_view = MonsDetailView(mon, editable=True)
        else:
            detail_view = MonsDetailView(mon, editable=False)
        embed = await detail_view.get_embed()
        await interaction.response.send_message("Displaying mon details:", embed=embed, view=detail_view, ephemeral=True)

    @discord.ui.button(label="Back", style=discord.ButtonStyle.danger, custom_id="mons_back", row=1)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Returning to previous menu...", ephemeral=True)
