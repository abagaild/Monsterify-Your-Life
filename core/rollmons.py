import random
import discord

from core.database import cursor, db
from core.database import append_mon_to_sheet, update_character_sheet_level, update_character_sheet_item
from data.lists import legendary_list, mythical_list, no_evolution
# ... (data fetching functions for Pokemon, Digimon, etc. remain unchanged) ...

async def roll_mon_variant(ctx, variant: str, amount: int):
    """
    Rolls a given number of mons based on the specified variant (standard or special).
    Sends the rolled mons as a list.
    (This function would generate mon data; simplified for brevity.)
    """
    # Implementation not shown for brevity
    pass

async def register_mon(ctx, trainer_name: str, mon: dict, custom_display_name: str):
    """
    Registers a rolled mon to the given trainer in the database and updates records.
    """
    try:
        # Insert mon into the database
        cursor.execute(
            """
            INSERT INTO mons (trainer_id, player, mon_name, level, 
                               species1, species2, species3,
                               type1, type2, type3, type4, type5,
                               attribute, img_link)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                mon["trainer_id"], mon["player_id"], custom_display_name, mon.get("level", 1),
                mon.get("species1", ""), mon.get("species2", ""), mon.get("species3", ""),
                mon["types"][0], mon["types"][1], mon["types"][2], mon["types"][3], mon["types"][4],
                mon.get("attribute", ""), mon.get("img_link", "")
            )
        )
        db.commit()
    except Exception as e:
        await ctx.send(f"Error adding mon to database: {e}")
        return

    # Update trainer's mon count (and queue sheet update if enabled)
    error = await append_mon_to_sheet(trainer_name, [])
    if error:
        await ctx.send(f"Mon added to database but failed to update sheet: {error}")
    else:
        await ctx.send(f"Registered mon **{custom_display_name}** to trainer **{trainer_name}** successfully.")
        # Deduct one Pokéball from trainer's inventory
        await update_character_sheet_item(trainer_name, "Pokeball", -1)

async def assign_levels_to_mon(ctx, mon_name: str, levels: int, user_id: str):
    """
    Assigns levels to a mon when called via a text command.
    Converts any levels beyond 100 into coins for the trainer.
    """
    cursor.execute("SELECT trainer_id, level FROM mons WHERE mon_name = ? AND player = ?", (mon_name, user_id))
    res = cursor.fetchone()
    if not res:
        await ctx.send(f"Mon '{mon_name}' not found or does not belong to you.")
        return
    trainer_id, current_level = res
    cursor.execute("SELECT name FROM trainers WHERE id = ?", (trainer_id,))
    t_res = cursor.fetchone()
    if not t_res:
        await ctx.send("Trainer not found for that mon.")
        return
    trainer_name = t_res[0]
    if current_level >= 100:
        extra_coins = levels * 25
        cursor.execute("UPDATE trainers SET currency_amount = currency_amount + ? WHERE id = ?", (extra_coins, trainer_id))
        db.commit()
        await ctx.send(f"Mon '{mon_name}' is at level 100. Converted {levels} level(s) into {extra_coins} coins.")
    elif current_level + levels > 100:
        effective_levels = 100 - current_level
        excess = levels - effective_levels
        success = await update_character_sheet_level(trainer_name, mon_name, effective_levels)
        if success:
            extra_coins = excess * 25
            cursor.execute("UPDATE trainers SET currency_amount = currency_amount + ? WHERE id = ?", (extra_coins, trainer_id))
            db.commit()
            await ctx.send(
                f"Mon '{mon_name}' reached level 100. Added {effective_levels} level(s) and converted {excess} extra level(s) into {extra_coins} coins."
            )
        else:
            await ctx.send("Mon level updated in database, but sheet update failed for '{mon_name}'.")
    else:
        success = await update_character_sheet_level(trainer_name, mon_name, levels)
        if success:
            await ctx.send(f"Added {levels} level(s) to mon '{mon_name}'.")
        else:
            await ctx.send("Failed to update the mon's level.")

# ------------------ Raw Data Fetching Functions ------------------
def fetch_pokemon_data():
    """Fetches Pokémon data from the Pokemon table."""
    pokemon_data = []
    try:
        cursor.execute('SELECT "Name", "Stage", "Type1", "Type2" FROM Pokemon')
        for row in cursor.fetchall():
            name, stage, type1, type2 = row
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
        cursor.execute(
            'SELECT "Name", "Stage", "Rarity", "Kind", "Attribute", "Evolves Into 1", "Evolves Into 2", "Evolves Into 3" FROM Digimon'
        )
        for row in cursor.fetchall():
            name, stage, rarity, kind, attribute, evolves1, evolves2, evolves3 = row
            # We'll store the 'kind' as the first element in a types list for filtering purposes.
            types = [kind.strip()] if kind else []
            digimon_data.append({
                "name": name,
                "stage": stage,
                "rarity": rarity,
                "types": types,  # Contains 'kind'
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
        cursor.execute('SELECT "Name", "Rank", "Tribe", "Attribute", "Stage" FROM YoKai')
        for row in cursor.fetchall():
            name, rank, tribe, attribute, stage = row
            yokai_data.append({
                "name": name,
                "rank": rank,
                "tribe": tribe,
                "attribute": attribute,
                "stage": stage,
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

    legendary_set = set(name.lower() for name in legendary_list)
    mythical_set = set(name.lower() for name in mythical_list)

    filtered_pokemon = []
    for p in pokemon:
        name = p.get("name", "").lower()
        stage = p.get("stage", "").lower()
        if name in legendary_set or name in mythical_set:
            continue
        if stage in {"second stage", "final stage"}:
            filtered_pokemon.append(p)

    filtered_digimon = [d for d in digimon if d.get("stage", "").lower() in {"training 1", "training 2", "rookie"}]

    # For Yo-Kai, no extra filtering for the default pool.
    filtered_yokai = yokai

    return filtered_pokemon + filtered_digimon + filtered_yokai


def get_pool_by_variant(variant: str, unique_terms: dict = None):
    """
    Returns a pool of mons based on the variant.
    Supported variants include:
      - "default"/"standard"
      - "egg" (handled separately by breeding functions)
      - "breeding"
      - "garden"
      - "gamecorner"
      - "special"
      - "legendary"
      - "mythical"
      - "starter"
    unique_terms is an optional dict that can override or add filtering parameters.
    """
    variant = variant.lower()
    if variant in {"default", "standard"}:
        return get_default_pool()
    elif variant == "egg":
        # Egg rolls handled separately.
        return get_default_pool()
    elif variant == "breeding":
        return get_default_pool()
    elif variant == "garden":
        # Apply garden-specific filters.
        pool = []
        # For Pokémon: Only include base stage and at least one allowed type.
        allowed_types = {"flying", "normal", "grass", "bug", "water"}
        for p in fetch_pokemon_data():
            if str(p.get("stage", "")).lower() in {"base", "base stage"}:
                p_types = [t.lower() for t in p.get("types", [])]
                if any(t in allowed_types for t in p_types):
                    pool.append(p)
        # For Digimon: Only include those whose stage is in {"training 1", "training 2", "rookie"}
        # and whose kind (first element in types) is either "plant" or "wind".
        for d in fetch_digimon_data():
            stage = str(d.get("stage", "")).lower()
            if stage in {"training 1", "training 2", "rookie"}:
                d_types = d.get("types", [])
                if d_types:
                    kind = d_types[0].lower()
                    if kind in {"plant", "wind"}:
                        pool.append(d)
        # For YoKai: Only include those with attribute "earth" or "wind".
        for y in fetch_yokai_data():
            if str(y.get("attribute", "")).lower() in {"earth", "wind"}:
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
        legendary_set = set(name.lower() for name in legendary_list)
        return [m for m in pool if m.get("name", "").lower() in legendary_set]
    elif variant == "mythical":
        pool = fetch_pokemon_data()
        mythical_set = set(name.lower() for name in mythical_list)
        return [m for m in pool if m.get("name", "").lower() in mythical_set]
    elif variant == "starter":
        pokemon = fetch_pokemon_data()
        digimon = fetch_digimon_data()
        starter_pokemon = [
            p for p in pokemon if str(p.get("stage", "")).lower() in {"base", "base stage"}
                                  or p.get("name", "").lower() in {n.lower() for n in no_evolution}
        ]
        starter_digimon = [d for d in digimon if str(d.get("stage", "")).lower() in {"baby", "rookie"}]
        yokai = fetch_yokai_data()
        return starter_pokemon + starter_digimon + yokai
    else:
        return get_default_pool()


def roll_single_mon(pool: list, force_fusion: bool = False, force_min_types: int = None) -> dict:
    """
    Rolls a single mon from the provided pool.
    With a chance for fusion if force_fusion is True or random chance passes.
    """
    POSSIBLE_TYPES = [
        "Normal", "Fire", "Water", "Electric", "Grass", "Ice", "Fighting", "Poison",
        "Ground", "Flying", "Psychic", "Bug", "Rock", "Ghost", "Dragon", "Dark", "Steel", "Fairy"
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


# ------------------ Embed and View Building ------------------
def build_mon_embed(rolled_mons: list) -> discord.Embed:
    """
    Builds an embed listing each rolled mon in the following format per mon:
      **Species1 / Species2 / Species3**
      Types: type1 - type2 - ...
      Attribute: attribute
    Only nonempty species and types are shown.
    """
    embed = discord.Embed(title="Rolled Mons", color=discord.Color.blurple())
    description_lines = []
    for idx, mon in enumerate(rolled_mons, start=1):
        species = [mon.get("species1", "").strip(), mon.get("species2", "").strip(), mon.get("species3", "").strip()]
        species = [s for s in species if s]
        species_line = "**" + " / ".join(species) + "**" if species else "**Unknown Species**"
        types = [t for t in mon.get("types", []) if t]
        types_line = "Types: " + " - ".join(types) if types else "Types: N/A"
        attr_line = f"Attribute: {mon.get('attribute', 'N/A')}"
        description_lines.append(f"{species_line}\n{types_line}\n{attr_line}")
    embed.description = "\n\n".join(description_lines)
    return embed


class RollMonsView(discord.ui.View):
    """
    A views with a button for each rolled mon plus a skip button.
    Claim limit determines how many mon buttons can be pressed (default 1).
    Pressing a mon button launches the register_mon modal.
    """

    def __init__(self, rolled_mons: list, claim_limit: int = 1):
        super().__init__(timeout=180)
        self.rolled_mons = rolled_mons
        self.claim_limit = claim_limit
        self.claimed = 0
        for mon in rolled_mons:
            # Use species1 if available, otherwise fallback to the mon's name.
            species_label = (mon.get("species1") or mon.get("name") or "Unknown").strip()
            # Truncate label if necessary (Discord limits button label length to 80 characters)
            species_label = species_label[:80]
            button = discord.ui.Button(label=f"Claim {species_label}", style=discord.ButtonStyle.primary)
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
            await register_mon(interaction, mon)
            self.claimed += 1
            if self.claimed >= self.claim_limit:
                for item in self.children:
                    if isinstance(item, discord.ui.Button) and item.custom_id != "skip":
                        item.disabled = True
                await interaction.message.edit(view=self)

        return callback

    async def skip_callback(self, interaction: discord.Interaction):
        await interaction.response.send_message("No mons claimed.", ephemeral=True)
        self.stop()


# ------------------ Main Roll Function ------------------
async def roll_mons(ctx, variant: str = "default", amount: int = 10, unique_terms: dict = None, claim_limit: int = 1):
    """
    Rolls a set of mons based on the variant.
    Supported variants: "default", "egg", "breeding", "garden", "gamecorner", "special", "legendary", "mythical", "starter".
    unique_terms is an optional dict for extra filtering.
    Amount defaults to 10.

    For the garden variant, the pool is filtered as follows:
      • Pokémon: Only include mons with stage "base" or "base stage" and with at least one type in {flying, normal, grass, bug, water}.
      • Digimon: Only include mons whose stage is in {"training 1", "training 2", "rookie"} and whose first type (kind) is "plant" or "wind".
      • YoKai: Only include mons with attribute "earth" or "wind".

    After rolling, an embed is built listing each mon:
      **Species1 / Species2 / Species3**
      Types: type1 - type2 - …
      Attribute: attribute

    A views is attached with a button for each mon (and a Skip button). By default, only claim_limit mons may be claimed.
    Claiming a mon launches the registration modal.
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


def get_egg_pool():
    """
    Builds a pool for egg rolls.
    Only includes:
      - Pokémon that are in "Base Stage" (or "base") or whose name is in no_evolution,
        excluding legendary and mythical Pokémon.
      - Digimon whose stage is exactly "training 1" (case-insensitive).
      - Yo-Kai whose rank is one of E, D, C, or B.
    """
    pokemon = fetch_pokemon_data()
    digimon = fetch_digimon_data()
    yokai = fetch_yokai_data()

    legendary_set = set(name.lower() for name in legendary_list)
    mythical_set = set(name.lower() for name in mythical_list)
    no_evo_set = set(n.lower() for n in no_evolution)

    # Filter Pokémon: only include those in base stage or in the no_evolution list.
    filtered_pokemon = []
    for p in pokemon:
        name = (p.get("name") or "").lower()
        stage = (p.get("stage") or "").lower()
        if name in legendary_set or name in mythical_set:
            continue
        if stage in {"base", "base stage"} or name in no_evo_set:
            filtered_pokemon.append(p)

    # Filter Digimon: only include those with stage exactly "training 1".
    filtered_digimon = [d for d in digimon if (d.get("stage") or "").strip().lower() == "training 1"]

    # Filter Yo-Kai: only include those whose rank is E, D, C, or B.
    allowed_ranks = {"e", "d", "c", "b"}
    filtered_yokai = [y for y in yokai if (y.get("rank") or "").strip().lower() in allowed_ranks]

    return filtered_pokemon + filtered_digimon + filtered_yokai