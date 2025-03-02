import random

import discord

from core.database import cursor
from core.mon import register_mon  # This function launches the registration modal
from data.lists import legendary_list, mythical_list, no_evolution


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
        for idx, mon in enumerate(rolled_mons, start=1):
            button = discord.ui.Button(label=f"Claim #{idx}", style=discord.ButtonStyle.primary, custom_id=str(idx))
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
