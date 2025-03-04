import asyncio
import logging
import random
from typing import Dict, Any, Optional

import discord
from core.database import save_session, update_session, delete_session
from core.rollmons import roll_single_mon
from core.trainer import assign_levels_to_trainer
from core.mon import assign_levels_to_mon

# Global in-memory store for active adventure sessions
active_adventure_sessions: Dict[int, "AdventureSession"] = {}

class AdventureSession:
    """
    Represents an active adventure session in a designated Discord channel.
    """
    def __init__(self, channel: discord.TextChannel, area_data: Dict[str, Any], hard_mode: bool = False) -> None:
        self.channel: discord.TextChannel = channel
        self.area_data: Dict[str, Any] = area_data
        self.hard_mode: bool = hard_mode
        self.progress: int = 0
        self.encounters_triggered: int = 0
        self.max_encounters: int = 3
        self.players: set[str] = set()  # store user IDs as strings
        self.timer_task: Optional[asyncio.Task] = None
        self.sudden_death_messages = [
            "Time's up! Your adventure ends in sudden death!",
            "You took too long... fate has intervened!",
            "No response for too long; your adventure meets a grim end."
        ]
        # Save session to database and add to active sessions
        save_session(self)
        active_adventure_sessions[self.channel.id] = self
        logging.info(f"Adventure session created in channel {self.channel.id} with hard_mode={self.hard_mode}")
        if self.hard_mode:
            self.reset_timer()

    def reset_timer(self) -> None:
        if self.timer_task:
            self.timer_task.cancel()
        self.timer_task = asyncio.create_task(self.start_timer())

    async def start_timer(self) -> None:
        try:
            await asyncio.sleep(900)  # 15 minutes
            sudden_message = random.choice(self.sudden_death_messages)
            await self.channel.send(sudden_message)
            await self.end_adventure()
        except asyncio.CancelledError:
            pass

    async def handle_message(self, message: discord.Message) -> None:
        logging.info(f"Handling message from {message.author} in channel {message.channel.id}: {message.content}")
        self.players.add(str(message.author.id))
        content = message.content.lower().strip()
        if content == "end":
            await self.channel.send("Adventure ended by player command.")
            await self.end_adventure()
        elif content == "next":
            if self.encounters_triggered < self.max_encounters:
                encounters = self.area_data.get("encounters", [])
                if encounters:
                    encounter = random.choice(encounters)
                    self.encounters_triggered += 1
                    await self.channel.send(encounter.get("flavor_text", "An encounter unfolds..."))
                else:
                    await self.channel.send("No encounters defined for this adventure.")
            else:
                await self.channel.send(random.choice([
                    "Nothing happened...",
                    "The adventure remains quiet.",
                    "All is calm... nothing new occurs."
                ]))
        else:
            word_count = len(content.split())
            self.progress += word_count
            update_session(self)
            await self.channel.send(f"Progress updated: total words = {self.progress}")
        if self.hard_mode:
            self.reset_timer()

    async def end_adventure(self) -> None:
        if self.timer_task:
            self.timer_task.cancel()
        await self.channel.send("Adventure session has ended. Processing rewards...")
        await finalize_adventure_rewards(self)
        delete_session(self.channel.id)
        active_adventure_sessions.pop(self.channel.id, None)
        logging.info(f"Adventure session in channel {self.channel.id} ended.")

async def finalize_adventure_rewards(session: AdventureSession) -> None:
    logging.info("Finalizing adventure rewards...")
    total_word_count = session.progress
    num_players = len(session.players) if session.players else 1
    base_levels = total_word_count / (200 * num_players)
    if session.hard_mode:
        base_levels *= 2
    levels_awarded = round(base_levels)
    logging.info(f"Word count: {total_word_count}, Players: {num_players}, Levels awarded: {levels_awarded}")

    for player_id in session.players:
        member = session.channel.guild.get_member(int(player_id))
        if not member:
            logging.warning(f"Member with ID {player_id} not found.")
            continue
        dm_channel = member.dm_channel or await member.create_dm()
        try:
            await dm_channel.send(f"Your adventure has ended! You earned **{levels_awarded} levels**.")
        except Exception as e:
            logging.error(f"Failed to send DM to {member}: {e}")

        await dm_channel.send("Assign your rewards to a **mon** or your **trainer**? (type 'mon' or 'trainer')")
        try:
            choice_msg = await session.channel.client.wait_for(
                "message",
                check=lambda m: m.author.id == int(player_id) and m.channel == dm_channel,
                timeout=30
            )
            choice = choice_msg.content.strip().lower()
        except asyncio.TimeoutError:
            choice = "trainer"
            await dm_channel.send("No response received. Defaulting to trainer assignment.")

        if choice.startswith("m"):
            await dm_channel.send("Enter the **mon's name** to assign your level rewards:")
            try:
                mon_msg = await session.channel.client.wait_for(
                    "message",
                    check=lambda m: m.author.id == int(player_id) and m.channel == dm_channel,
                    timeout=30
                )
                mon_name = mon_msg.content.strip()
            except asyncio.TimeoutError:
                mon_name = "default"
                await dm_channel.send("No response received. Using default mon assignment.")
            await assign_levels_to_mon(dm_channel, mon_name, levels_awarded, str(player_id))
        else:
            await dm_channel.send("Enter the **trainer's name** to assign your level rewards:")
            try:
                trainer_msg = await session.channel.client.wait_for(
                    "message",
                    check=lambda m: m.author.id == int(player_id) and m.channel == dm_channel,
                    timeout=30
                )
                trainer_name = trainer_msg.content.strip()
            except asyncio.TimeoutError:
                trainer_name = "default"
                await dm_channel.send("No response received. Using default trainer assignment.")
            await assign_levels_to_trainer(dm_channel, trainer_name, levels_awarded, str(player_id))

        item_rolls = levels_awarded // 10
        mon_rolls = levels_awarded // 20
        await dm_channel.send(f"You earned {item_rolls} item roll(s) and {mon_rolls} mon reward roll(s).")
        if mon_rolls > 0:
            for i in range(mon_rolls):
                await dm_channel.send(f"Reward Mon Roll {i + 1}: Please reply with the trainer name to register this mon.")
                try:
                    mon_resp = await session.channel.client.wait_for(
                        "message",
                        check=lambda m: m.author.id == int(player_id) and m.channel == dm_channel,
                        timeout=30
                    )
                    trainer_for_mon = mon_resp.content.strip()
                except asyncio.TimeoutError:
                    trainer_for_mon = "default"
                    await dm_channel.send("No response received. Default assignment used.")
                rolled_mon = roll_single_mon() or {
                    "name": "DefaultMon",
                    "stage": "N/A",
                    "types": ["Normal"],
                    "attribute": "Free",
                    "img_link": ""
                }
                await dm_channel.send(f"Reward Mon Rolled: **{rolled_mon.get('name', 'Unknown')}**.")
                from core.rollmons import register_mon
                await register_mon(dm_channel, rolled_mon)
    await session.channel.send("Thank you for adventuring! Your rewards have been processed.")
    logging.info("Adventure rewards finalization complete.")
