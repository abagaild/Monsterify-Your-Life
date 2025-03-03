legendary_list = [
    # Generation I
    "Articuno", "Zapdos", "Moltres", "Galarian Articuno", "Galarian Zapdos", "Galarian Moltres", "Mewtwo",
    # Generation II
    "Raikou", "Entei", "Suicune", "Lugia", "Ho-Oh",
    # Generation III
    "Regirock", "Regice", "Registeel", "Latias", "Latios", "Kyogre", "Groudon", "Rayquaza",
    # Generation IV
    "Uxie", "Mesprit", "Azelf", "Dialga", "Palkia", "Giratina", "Heatran", "Regigigas", "Cresselia",
    # Generation V
    "Cobalion", "Terrakion", "Virizion", "Tornadus", "Thundurus", "Landorus", "Reshiram", "Zekrom", "Kyurem",
    # Generation VI
    "Xerneas", "Yveltal", "Zygarde",
    # Generation VII
    "Cosmog", "Cosmoem", "Solgaleo", "Lunala", "Necrozma", "Type: Null", "Silvally",
    "Tapu Koko", "Tapu Lele", "Tapu Bulu", "Tapu Fini",
    # Ultra Beasts (Gen VII)
    "Nihilego", "Buzzwole", "Pheromosa", "Xurkitree", "Celesteela", "Kartana", "Guzzlord",
    "Poipole", "Naganadel", "Stakataka", "Blacephalon",
    # Generation VIII
    "Zacian", "Zamazenta", "Eternatus", "Kubfu", "Urshifu", "Regieleki", "Regidrago",
    "Glastrier", "Spectrier", "Calyrex", "Enamorus",
    # Generation IX
    "Wo-Chien", "Chien-Pao", "Ting-Lu", "Chi-Yu", "Koraidon", "Miraidon",
    # Paradox Pokémon (Gen IX)
    "Great Tusk", "Scream Tail", "Brute Bonnet", "Flutter Mane", "Slither Wing", "Sandy Shocks", "Roaring Moon",
    "Iron Treads", "Iron Bundle", "Iron Hands", "Iron Jugulis", "Iron Moth", "Iron Thorns", "Iron Valiant",
    "Walking Wake", "Iron Leaves", "Raging Bolt", "Gouging Fire", "Iron Crown", "Iron Boulder",
    # Gen IX DLC: The Teal Mask & The Indigo Disk
    "Okidogi", "Munkidori", "Fezandipiti", "Ogerpon", "Terapagos"
]
mythical_list = [
    # Generation I
    "Mew",
    # Generation II
    "Celebi",
    # Generation III
    "Jirachi", "Deoxys",
    # Generation IV
    "Phione", "Manaphy", "Darkrai", "Shaymin", "Arceus",
    # Generation V
    "Victini", "Keldeo", "Meloetta", "Genesect",
    # Generation VI
    "Diancie", "Hoopa", "Volcanion",
    # Generation VII
    "Magearna", "Marshadow", "Zeraora", "Meltan", "Melmetal",
    # Generation VIII
    "Zarude",
    # Generation IX
    "Pecharunt"
]
no_evolution = ["Farfetch'd", "Kangaskhan", "Pinsir", "Tauros", "Ditto", "Lapras", "Aerodactyl", "Unown", "Girafarig",
                "Dunsparce", "Qwilfish", "Shuckle", "Heracross", "Delibird", "Skarmory", "Stantler", "Smeargle",
                "Miltank", "Sableye", "Mawile", "Plusle", "Minun", "Volbeat", "Illumise", "Torkoal", "Spinda",
                "Zangoose", "Seviper", "Lunatone", "Solrock", "Castform", "Kecleon", "Tropius", "Chimecho", "Absol",
                "Relicanth", "Luvdisk", "Pachirisu", "Chatot", "Spiritomb", "Carnivine", "Rotom", "Audino", "Throh",
                "Sawk", "Maractus", "Sigilyph", "Emolga", "Alomomola", "Cryogonal", "Stunfisk", "Druddigon",
                "Bouffalant", "Heatmor", "Durant", "Hawlucha", "Dedenne", "Carbink", "Klefki", "Minior", "Komala",
                "Turtonator", "Togedemaru", "Mimikyu", "Bruxish", "Drampa", "Dhelmise", "Cramorant", "Falinks",
                "Pincurchin", "Stonjourner", "Eiscue", "Indeedee", "Morpeko", "Duraludon", "Squawkabilly", "Klawf",
                "Bombirdier", "Cyclizar", "Orthworm", "Flamigo", "Veluza", "Dondozo", "Tatsugiri"]

# All standard Pokémon types.
POKEMON_TYPES = [
    "Normal", "Fire", "Water", "Electric", "Grass", "Ice", "Fighting", "Poison",
    "Ground", "Flying", "Psychic", "Bug", "Rock", "Ghost", "Dragon", "Dark", "Steel", "Fairy"
]

# Possible Yokai ranks for Rank Insense.
YOKAI_RANKS = ["S", "A", "B", "C", "D", "E"]

# Possible Yokai color/attribute values for Color Insense.
YOKAI_ATTRIBUTES = ["Brave", "Tough", "Slippery", "Shady", "Mysterious", "Eerie", "Mochi", "Enma", "Heros", "Charming", "Friendly", "Righteous", "Elder", "Fierce", "Tornado", "Gloomy", "Hands", "Princess", "Eagle", "Fish", "Unknown" ]

# Possible Digimon attributes for the "# [attribute] tag".
DIGIMON_ATTRIBUTES = ["Free", "Virus", "Vaccine", "Data", "Variable"]
# -------------------- Expanded Item Lists --------------------

# Generate a Nurture Kit for every Pokémon type.
NURTURE_KITS = [f"{ptype} Type Nurture Kit" for ptype in POKEMON_TYPES]

# Generate a Poffin for every Pokémon type.
POFFINS = [f"{ptype} Type Poffin" for ptype in POKEMON_TYPES]

# Generate a Rank Insense for every Yokai rank.
RANK_INSENSES = [f"{rank} Rank Insense" for rank in YOKAI_RANKS]

# Generate a Color Insense for every Yokai attribute.
COLOR_INSENSES = [f"{attr} Color Insense" for attr in YOKAI_ATTRIBUTES]

# Generate attribute tags for Digimon.
ATTRIBUTE_TAGS = [f"# {attr} tag" for attr in DIGIMON_ATTRIBUTES]

MILK_OPTIONS = ["Hot Chocolate", "Strawberry Milk", "Chocolate Milk"]

ICE_CREAM_OPTIONS = ["Vanilla Ice Cream", "Strawberry Ice Cream", "Chocolate Ice Cream"]

# -------------------- Egg Secondary Items --------------------
# These are the secondary options available when using an Egg item.
EGG_SECONDARY_ITEMS = []
EGG_SECONDARY_ITEMS.append("Incubator")
EGG_SECONDARY_ITEMS.extend(NURTURE_KITS)
EGG_SECONDARY_ITEMS.append("Corruption Code")
EGG_SECONDARY_ITEMS.append("Repair Code")
EGG_SECONDARY_ITEMS.append("Shiny New Code")
EGG_SECONDARY_ITEMS.extend(RANK_INSENSES)
EGG_SECONDARY_ITEMS.extend(COLOR_INSENSES)
EGG_SECONDARY_ITEMS.append("Spell Tag")
EGG_SECONDARY_ITEMS.append("Summoning Stone")
EGG_SECONDARY_ITEMS.append("DigiMeat")
EGG_SECONDARY_ITEMS.append("DigiTofu")
EGG_SECONDARY_ITEMS.append("SootheBell")
EGG_SECONDARY_ITEMS.append("Broken Bell")
EGG_SECONDARY_ITEMS.extend(POFFINS)
EGG_SECONDARY_ITEMS.extend(ATTRIBUTE_TAGS)
EGG_SECONDARY_ITEMS.append("DNA Splicer")
EGG_SECONDARY_ITEMS.append("Hot Chocolate")
EGG_SECONDARY_ITEMS.append("Chocolate Milk")
EGG_SECONDARY_ITEMS.append("Strawberry Milk")
EGG_SECONDARY_ITEMS.append("Input Field")
EGG_SECONDARY_ITEMS.append("Drop Down")
EGG_SECONDARY_ITEMS.append("Radio Buttons")

# -------------------- Berry Items --------------------
# These items allow modification of a mon's traits.
BERRY_ITEMS = [
    "Mala Berry",       # Remove a species
    "Lilan Berry",      # Remove a type
    "Miraca Berry",     # Reroll/reassign a type
    "Addish Berry",     # Add a new type
    "Patama Berry",     # Reroll/reassign a species slot
    "Azzuk Berry",      # Roll a new species (if less than 3 exist)
    "Datei Berry"       # Reroll/reassign attribute
]

# -------------------- Pastry Items --------------------
# These items allow modification of a mon's traits.
PASTRY_ITEMS = [
    "Mala Pastry",       # Remove a species
    "Lilan Pastry",      # Remove a type
    "Miraca Pastry",     # Reroll/reassign a type
    "Addish Pastry",     # Add a new type
    "Patama Pastry",     # Reroll/reassign a species slot
    "Azzuk Pastry",      # Roll a new species (if less than 3 exist)
    "Datei Pastry"       # Reroll/reassign attribute
]

# -------------------- Non-Berry Items --------------------
# These items yield an immediate effect.
NONBERRY_ITEMS = [
    "Legacy Leeway",
    "Daycare Daypass",
    "Lottery Ticket",
    "Fertalizer",
    "Valentine Velvet",
    "Fruit Cake",
    "Hallowseve Candy",
    "Can't Believe it's Not Butter"
]

# -------------------- Bulk Items --------------------
# These are items that can be used in multiples (a form is generated per 5 items used).
BULK_ITEMS = [
    "Poké Ball", "Cygnus Ball", "Ranger Ball", "Premier Ball", "Great Ball", "Ultra Ball",
    "Master Ball", "Safari Ball", "Fast Ball", "Level Ball", "Lure Ball", "Heavy Ball",
    "Love Ball", "Friend Ball", "Moon Ball", "Sport Ball", "Net Ball", "Dive Ball",
    "Nest Ball", "Repeat Ball", "Timer Ball", "Luxury Ball", "Dusk Ball", "Heal Ball",
    "Quick Ball", "Marble Ball", "Godly Ball", "Rainbow Ball", "Pumpkin Ball", "Slime Ball",
    "Bat Ball", "Sweet Ball", "Ghost Ball", "Spider Ball", "Eye Ball", "Bloody Ball",
    "Patched Ball", "Snow Ball", "Gift Ball", "Ugly Christmas Ball", "Snowflake Ball",
    "Holly Ball", "Candy Cane Ball", "Park Ball", "Dream Ball", "Beast Ball",
    "Strange Ball", "Cherish Ball",
    "Normal Evolution Stone", "Fire Evolution Stone", "Fighting Evolution Stone",
    "Water Evolution Stone", "Flying Evolution Stone", "Grass Evolution Stone",
    "Poison Evolution Stone", "Electric Evolution Stone", "Ground Evolution Stone",
    "Psychic Evolution Stone", "Rock Evolution Stone", "Ice Evolution Stone",
    "Bug Evolution Stone", "Dragon Evolution Stone", "Ghost Evolution Stone",
    "Dark Evolution Stone", "Steel Evolution Stone", "Fairy Evolution Stone",
    "Cosmic Evolution Stone", "Light Evolution Stone",
    "Digital Bytes", "Digital Kilobytes", "Digital Megabytes", "Digital Gigabytes",
    "Digital Petabytes"
]

# -------------------- Primary Item Categories --------------------
# This list is used in the UI dropdown for primary item selection.
ITEM_CATEGORIES = (
    ["Egg"] +
    BERRY_ITEMS +
    NONBERRY_ITEMS +
    BULK_ITEMS
)

# -------------------- Special Mon Roll Lists --------------------
# These lists are used by non-berry items that roll mons.
VALENTINES_MONS = ["Cupidmon", "Lovermon", "Heartmon"]
WINTER_HOLIDAY_MONS = ["Snowmon", "Frostmon", "Icemon"]
HALLOWEEN_MONS = ["SpookyMon", "PumpkinMon", "GhostMon"]
FAKE_TYPE = ["FakeType1", "FakeType2"]

#--------------------- Actually Usefull Shit ---------------------
habit_reward = ["habit reward 1", "habit reward 2"]
task_reward = ["tasks are rewarding?", "tasks are rewarding!"]


