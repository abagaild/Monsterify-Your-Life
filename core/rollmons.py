import random
import discord
from discord.ui import Modal, TextInput

from core.database import (
    add_mon,
    append_mon,
    update_character_sheet_item,
    update_mon_level,
    addsub_trainer_currency,
    get_all_mons_for_user,
    fetch_trainer_by_name,
    fetch_all,
    fetch_one,
    execute_query
)
from data.lists import legendary_list, mythical_list, no_evolution

# ------------------ Raw Data Fetching Functions ------------------
def fetch_pokemon_data():
    """Fetches Pokémon data from the Pokemon table."""
    pokemon_data = []
    try:
        rows = fetch_all('SELECT "Name", "Stage", "Type1", "Type2" FROM Pokemon')
        for row in rows:
            name = row["Name"]
            stage = row["Stage"]
            type1 = row["Type1"]
            type2 = row["Type2"]
            types = []
            if type1:
                types.append(type1.strip())
            if type2:
                types.append(type2.strip())
            pokemon_data.append({
                "name": name,
                "stage": stage,
                "types": types,
                "attribute": "",  # default attribute
                "origin": "pokemon"
            })
    except Exception as e:
        print(f"Error fetching Pokémon data: {e}")
    return pokemon_data

def fetch_digimon_data():
    """Fetches Digimon data from the Digimon table."""
    digimon_data = []
    try:
        rows = fetch_all(
            'SELECT "Name", "Stage", "Rarity", "Kind", "Attribute", "Evolves Into 1", "Evolves Into 2", "Evolves Into 3" FROM Digimon'
        )
        for row in rows:
            name = row["Name"]
            stage = row["Stage"]
            rarity = row["Rarity"]
            kind = row["Kind"]
            attribute = row["Attribute"]
            types = [kind.strip()] if kind else []
            digimon_data.append({
                "name": name,
                "stage": stage,
                "rarity": rarity,
                "types": types,
                "attribute": attribute,
                "origin": "digimon"
            })
    except Exception as e:
        print(f"Error fetching Digimon data: {e}")
    return digimon_data

def fetch_yokai_data():
    """Fetches Yo-Kai data from the YoKai table."""
    yokai_data = []
    try:
        rows = fetch_all('SELECT "Name", "Rank", "Tribe", "Attribute", "Stage" FROM YoKai')
        for row in rows:
            yokai_data.append({
                "name": row["Name"],
                "rank": row["Rank"],
                "tribe": row["Tribe"],
                "attribute": row["Attribute"],
                "origin": "yokai"
            })
    except Exception as e:
        print(f"Error fetching Yo-Kai data: {e}")
    return yokai_data

# ------------------ Pool Construction & Filtering ------------------
def get_default_pool():
    """
    Builds the default mon pool for a standard roll.
    For the default roll we exclude legendaries and mythicals,
    include only Digimon with stage in {"training 1", "training 2", "rookie"},
    and for Pokémon include only those in {"second stage", "final stage"}.
    """
    pokemon = fetch_pokemon_data()
    digimon = fetch_digimon_data()
    yokai = fetch_yokai_data()

    legendary_set = {name.lower() for name in legendary_list}
    mythical_set = {name.lower() for name in mythical_list}

    filtered_pokemon = []
    for p in pokemon:
        pname = p.get("name", "").lower()
        stage = (p.get("stage") or "").lower()
        if pname in no_evolution:
            filtered_pokemon.append(p)
        if pname in legendary_set or pname in mythical_set or stage in {"second stage", "final stage"}:
            continue
        else:
            filtered_pokemon.append(p)

    filtered_digimon = [d for d in digimon if (d.get("stage") or "").lower() in {"training 1", "training 2", "rookie"}]

    filtered_yokai = yokai

    return filtered_pokemon + filtered_digimon + filtered_yokai

def get_pool_by_variant(variant: str, unique_terms: dict = None):
    """
    Returns a pool of mons based on the variant.
    Supported variants: "default"/"standard", "egg", "breeding", "garden", "gamecorner",
    "special", "legendary", "mythical", "starter".
    unique_terms is an optional dict for extra filtering.
    """
    variant = variant.lower()
    if variant in {"default", "standard", "egg", "breeding"}:
        return get_default_pool()
    elif variant == "garden":
        pool = []
        allowed_types = {"flying", "normal", "grass", "bug", "water"}
        for p in fetch_pokemon_data():
            if (p.get("stage") or "").lower() in {"base", "base stage"}:
                p_types = [t.lower() for t in p.get("types", [])]
                if any(t in allowed_types for t in p_types):
                    pool.append(p)
        for d in fetch_digimon_data():
            stage = (d.get("stage") or "").lower()
            if stage in {"training 1", "training 2", "rookie"}:
                d_types = d.get("types", [])
                if d_types and d_types[0].lower() in {"plant", "wind"}:
                    pool.append(d)
        for y in fetch_yokai_data():
            if (y.get("attribute") or "").lower() in {"earth", "wind"}:
                pool.append(y)
        return pool
    elif variant == "gamecorner":
        return get_default_pool()
    elif variant == "special":
        pool = get_default_pool()
        if unique_terms and "filter" in unique_terms:
            term = unique_terms["filter"].lower()
            pool = [m for m in pool if term in m.get("name", "").lower()]
        return pool
    elif variant == "legendary":
        pool = fetch_pokemon_data()
        legendary_set = {name.lower() for name in legendary_list}
        return [m for m in pool if (m.get("name") or "").lower() in legendary_set]
    elif variant == "mythical":
        pool = fetch_pokemon_data()
        mythical_set = {name.lower() for name in mythical_list}
        return [m for m in pool if (m.get("name") or "").lower() in mythical_set]
    elif variant == "starter":
        pokemon = fetch_pokemon_data()
        digimon = fetch_digimon_data()
        starter_pokemon = [
            p for p in pokemon if (p.get("stage") or "").lower() in {"base", "base stage"}
                                  or (p.get("name") or "").lower() in {n.lower() for n in no_evolution}
        ]
        starter_digimon = [d for d in digimon if (d.get("stage") or "").lower() in {"baby", "rookie"}]
        yokai = fetch_yokai_data()
        return starter_pokemon + starter_digimon + yokai
    else:
        return get_default_pool()

def roll_single_mon(pool: list, force_fusion: bool = False, force_min_types: int = None) -> dict:
    """
    Rolls a single mon from the provided pool.
    Has a chance for fusion if force_fusion is True or based on random chance.
    """
    POSSIBLE_TYPES = [
        "Normal", "Fire", "Water", "Electric", "Grass", "Ice", "Fighting",
        "Psychic", "Bug", "Rock", "Ghost", "Dragon", "Dark", "Steel", "Fairy"
    ]
    RANDOM_ATTRIBUTES = ["Free", "Virus", "Data", "Variable"]
    if force_fusion or (len(pool) >= 2 and random.random() < 0.5):
        mon1, mon2 = random.sample(pool, 2)
        fused = {
            "name": f"{mon1['name']} / {mon2['name']}",
            "stage": "Fusion",
            "origin": "fusion"
        }
        num_types = random.randint(force_min_types if force_min_types else 1, 3)
        fused["types"] = random.sample(POSSIBLE_TYPES, num_types)
        fused["attribute"] = random.choice(RANDOM_ATTRIBUTES)
        return fused
    else:
        mon = random.choice(pool)
        num_types = random.randint(force_min_types if force_min_types else 1, 3)
        mon["types"] = random.sample(POSSIBLE_TYPES, num_types)
        mon["attribute"] = random.choice(RANDOM_ATTRIBUTES)
        return mon

def build_mon_embed(rolled_mons: list) -> discord.Embed:
    """
    Builds an embed listing each rolled mon.
    Each mon is shown with its species (if available), types, and attribute.
    """
    embed = discord.Embed(title="Rolled Mons", color=discord.Color.blurple())
    description_lines = []
    for mon in rolled_mons:
        species = []
        for key in ["species1", "species2", "species3"]:
            s = mon.get(key, "").strip()
            if s:
                species.append(s)
        species_line = "**" + " / ".join(species) + "**" if species else "**Unknown Species**"
        types = [t for t in mon.get("types", []) if t]
        types_line = "Types: " + " - ".join(types) if types else "Types: N/A"
        attr_line = f"Attribute: {mon.get('attribute', 'N/A')}"
        description_lines.append(f"{species_line}\n{types_line}\n{attr_line}")
    embed.description = "\n\n".join(description_lines)
    return embed

# ------------------ RollMons UI ------------------
class RollMonsView(discord.ui.View):
    """
    A Discord UI view with a button for each rolled mon plus a Skip button.
    Claiming a mon launches the registration process.
    """
    def __init__(self, rolled_mons: list, claim_limit: int = 1):
        super().__init__(timeout=180)
        self.rolled_mons = rolled_mons
        self.claim_limit = claim_limit
        self.claimed = 0
        for mon in rolled_mons:
            label = (mon.get("species1") or mon.get("name") or "Unknown").strip()[:80]
            button = discord.ui.Button(label=f"Claim {label}", style=discord.ButtonStyle.primary)
            button.callback = self.make_claim_callback(mon)
            self.add_item(button)
        skip_button = discord.ui.Button(label="Skip", style=discord.ButtonStyle.secondary, custom_id="skip")
        skip_button.callback = self.skip_callback
        self.add_item(skip_button)

    def make_claim_callback(self, mon: dict):
        async def callback(interaction: discord.Interaction):
            if self.claimed >= self.claim_limit:
                await interaction.response.send_message("Maximum mons already claimed.", ephemeral=True)
                return
            # Launch the registration process
            await register_mon(interaction, mon.get("trainer_name", "Unknown"), mon, mon.get("name", "Unknown"))
            self.claimed += 1
            if self.claimed >= self.claim_limit:
                for item in self.children:
                    if isinstance(item, discord.ui.Button) and item.custom_id != "skip":
                        item.disabled = True
                await interaction.edit_original_response(view=self)
        return callback

    async def skip_callback(self, interaction: discord.Interaction):
        await interaction.response.send_message("No mons claimed.", ephemeral=True)
        self.stop()

# ------------------ Main Roll Functions ------------------
async def roll_mon_variant(ctx, variant: str, amount: int):
    """
    Rolls a given number of mons based on the specified variant.
    Sends an embed with a simple list of rolled mon names and their types.
    """
    pool = get_pool_by_variant(variant)
    if not pool:
        await ctx.send("No mons available for the given variant.", ephemeral=True)
        return
    rolled_mons = [roll_single_mon(pool) for _ in range(amount)]
    # Build a simple description listing the rolled mons.
    description = "\n".join(
        f"{idx+1}. {mon.get('name', 'Unknown')} (Types: {', '.join(mon.get('types', []))})"
        for idx, mon in enumerate(rolled_mons)
    )
    embed = discord.Embed(title=f"Rolled Mons for Variant '{variant}'", description=description, color=discord.Color.blurple())
    await ctx.send(embed=embed)


class RegisterMonModal(Modal, title="Register Rolled Mon"):
    # The modal will ask for the trainer's name and a custom display name for the mon.
    trainer_name = TextInput(
        label="Trainer Name",
        placeholder="Enter trainer's name",
        required=True
    )
    custom_mon_name = TextInput(
        label="Custom Mon Name",
        placeholder="Enter a custom display name for your mon",
        required=True
    )

    def __init__(self, mon: dict):
        super().__init__()
        self.mon = mon

    async def on_submit(self, interaction: discord.Interaction):
        # Get the values entered by the user.
        trainer_name = self.trainer_name.value.strip()
        custom_mon_name = self.custom_mon_name.value.strip()

        try:
            # Ensure the types list has exactly 5 elements.
            types = self.mon.get("types", [])
            if len(types) < 5:
                types = types + [""] * (5 - len(types))
            # Use the add_mon helper to insert the mon into the database.
            mon_id = add_mon(
                trainer_id=self.mon.get("trainer_id", int(interaction.user.id)),
                player=self.mon.get("player_id", str(interaction.user.id)),
                name=custom_mon_name,
                level=self.mon.get("level", 1),
                species1=self.mon.get("species1", ""),
                species2=self.mon.get("species2", ""),
                species3=self.mon.get("species3", ""),
                type1=types[0],
                type2=types[1],
                type3=types[2],
                type4=types[3],
                type5=types[4],
                attribute=self.mon.get("attribute", ""),
                img_link=self.mon.get("img_link", "")
            )
        except Exception as e:
            await interaction.response.send_message(
                f"Error adding mon to database: {e}",
                ephemeral=True
            )
            return

        # Append the mon to the trainer's count (or update the trainer's sheet).
        error = await append_mon(trainer_name, [])
        if error:
            await interaction.response.send_message(
                f"Mon added to database but failed to update sheet: {error}",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"Registered mon **{custom_mon_name}** to trainer **{trainer_name}** successfully.",
                ephemeral=True
            )
            # Deduct one Pokéball from the trainer's sheet.
            await update_character_sheet_item(trainer_name, "Pokeball", -1, "BALLS")


async def register_mon(interaction: discord.Interaction, mon: dict, trainer_name = "",  mon_name: str = ""):
    """
    Instead of immediately registering the mon,
    this function presents a modal to ask for the trainer's name and custom mon name.
    When the modal is submitted, the registration is performed.
    """
    modal = RegisterMonModal(mon)
    # Check if the interaction response has been sent or deferred
    if interaction.response.is_done():
        await interaction.followup.send_modal(modal)
    else:
        await interaction.response.send_modal(modal)

    # Modal submission and mon registration are handled within the modal callback.


async def assign_levels_to_mon(ctx, mon_name: str, levels: int, user_id: str):
    """
    Assigns levels to a mon belonging to the user.
    If the total level would exceed 100, extra levels are converted to coins.
    Uses get_all_mons_for_user, update_mon_level, and addsub_trainer_currency from core.database.
    """
    mons = get_all_mons_for_user(user_id)
    mon = next((m for m in mons if m["name"].lower() == mon_name.lower()), None)
    if not mon:
        await ctx.send(f"Mon '{mon_name}' not found or does not belong to you.")
        return

    trainer_id = mon["trainer_id"]
    current_level = mon["level"]
    # Optionally, fetch trainer record for display.
    trainer = fetch_trainer_by_name(mon.get("trainer_name", ""))
    trainer_name = trainer["character_name"] if trainer else "Unknown"

    max_level = 100
    if current_level >= max_level:
        extra_coins = levels * 25
        addsub_trainer_currency(trainer_id, extra_coins)
        await ctx.send(f"Mon '{mon_name}' is already at level {max_level}. Converted {levels} level(s) into {extra_coins} coins.")
    elif current_level + levels > max_level:
        effective_levels = max_level - current_level
        excess = levels - effective_levels
        update_mon_level(mon["id"], max_level)
        extra_coins = excess * 25
        addsub_trainer_currency(trainer_id, extra_coins)
        await ctx.send(
            f"Mon '{mon_name}' reached level {max_level}. Added {effective_levels} level(s) and converted {excess} extra level(s) into {extra_coins} coins."
        )
    else:
        new_level = current_level + levels
        update_mon_level(mon["id"], new_level)
        await ctx.send(f"Added {levels} level(s) to mon '{mon_name}'. New level is {new_level}.")

async def roll_mons(ctx, variant: str = "default", amount: int = 10, unique_terms: dict = None, claim_limit: int = 1):
    """
    Rolls a set of mons based on the specified variant.
    Builds an embed displaying each rolled mon’s species, types, and attribute.
    Attaches a UI view allowing the user to claim up to claim_limit mons.
    """
    pool = get_pool_by_variant(variant, unique_terms)
    if not pool:
        if hasattr(ctx, "response") and not ctx.response.is_done():
            await ctx.response.send_message("No mons available for the given criteria.", ephemeral=True)
        else:
            await ctx.send("No mons available for the given criteria.", ephemeral=True)
        return

    rolled_mons = [roll_single_mon(pool) for _ in range(amount)]
    embed = build_mon_embed(rolled_mons)
    view = RollMonsView(rolled_mons, claim_limit=claim_limit)

    if hasattr(ctx, "response") and not ctx.response.is_done():
        await ctx.response.send_message(embed=embed, view=view, ephemeral=True)
    else:
        await ctx.send(embed=embed, view=view, ephemeral=True)
