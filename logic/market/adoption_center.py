import datetime
import random

import discord

from core.items import get_inventory_quantity
from core.rollmons import roll_single_mon

# Global dictionary to store the last adoption date per user.
USER_ADOPTION_LAST = {}

ADOPTION_START_MESSAGES = [
    "Welcome to the Adoption Center! Your Daycare Daypass unlocks new opportunities.",
    "Step right up! Adopt a new companion with your Daycare Daypass."
]

ADOPTION_END_MESSAGES = [
    "Adoption complete! Welcome your new family member.",
    "The adoption process is finished. Enjoy your new companion!"
]

def can_adopt_today(user_id: str) -> bool:
    today = datetime.date.today().isoformat()
    return USER_ADOPTION_LAST.get(user_id) != today

def mark_adopted_today(user_id: str):
    USER_ADOPTION_LAST[user_id] = datetime.date.today().isoformat()

async def start_adoption_activity(interaction, user_id: str, trainer_name: str):
    if not interaction.response.is_done():
        await interaction.response.defer(ephemeral=True)
    if not can_adopt_today(user_id):
        await interaction.followup.send("You have already completed an adoption today. Try again tomorrow!", ephemeral=True)
        return
    passes = get_inventory_quantity(trainer_name, "Daycare Daypass")
    if passes < 1:
        await interaction.followup.send(f"{trainer_name} does not have enough Daycare Daypass to adopt.", ephemeral=True)
        return

    start_msg = random.choice(ADOPTION_START_MESSAGES)
    await interaction.followup.send(start_msg, ephemeral=True)

    num_rolls = random.randint(1, 4)
    rolled_mons = []
    for _ in range(num_rolls):
        mon = roll_single_mon()
        if mon:
            rolled_mons.append(mon)
    if not rolled_mons:
        await interaction.followup.send("No mons available for adoption at this time.", ephemeral=True)
        return

    mark_adopted_today(user_id)
    # Assume ADOPTION_FLAVOR_TEXTS is defined in your data/messages.py
    from data.messages import ADOPTION_FLAVOR_TEXTS
    flavor_text = random.choice(ADOPTION_FLAVOR_TEXTS.get(len(rolled_mons), ["A wonderful opportunity awaits you!"]))

    mon_details = []
    for mon in rolled_mons:
        if mon.get("origin") == "fusion":
            species_parts = [part.strip() for part in mon["name"].split("/")]
        else:
            species_parts = [mon["name"]]
        species_display = " / ".join(species_parts)
        types_display = ", ".join(mon.get("types", []))
        attribute_display = mon.get("attribute", "")
        mon_details.append(f"{species_display} - {types_display} - {attribute_display}")
    details_text = "\n".join(mon_details)
    embed_description = f"{flavor_text}\n\n{details_text}"

    embed = discord.Embed(
        title="Adoption Center",
        description=embed_description,
        color=0xFFD700
    )
    embed.set_footer(text=f"You may adopt up to {passes} mon(s) using your Daycare Daypass.")

    from views.market.adoption_center import AdoptionCenterView
    view = AdoptionCenterView(user_id, rolled_mons, passes)
    await interaction.followup.send(embed=embed, view=view, ephemeral=True)
