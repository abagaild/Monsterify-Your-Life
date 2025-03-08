import json
import os
import random
import discord
from core.database import addsub_trainer_currency as add_currency
from core.database import (
    execute_query,
    fetch_one,
    fetch_all,
    insert_record,
    update_record,
    remove_record
)
from core.database import update_mon_data, update_character_level, update_character_sheet_item

# ----------------------------
# Mission Logic Functions
# ----------------------------

def load_missions():
    filename = os.path.join(os.path.dirname(__file__), "../../data/missions.JSON")
    if os.path.exists(filename):
        with open(filename, "r") as f:
            try:
                missions = json.load(f)
                return missions
            except json.JSONDecodeError:
                print("Error decoding missions.json. Using default mission.")
    return [{
        "id": 1,
        "name": "The First Expedition",
        "flavor": "Embark on your first expedition into the unknown.",
        "requirements": {"min_level": 1},
        "difficulty": 1,
        "in_progress_artwork": "default_in_progress.png",
        "complete_artwork": "default_complete.png",
        "rollmons_reward": None,
        "item_reward": "1",
        "level_reward": 2,
        "coin_reward": 50,
        "repeatable": True,
        "max_mons": 3
    }]

def meets_requirements(mon: dict, requirements: dict) -> bool:
    if "min_level" in requirements:
        mon_level = mon.get("level", 0)
        if int(mon_level) < requirements["min_level"]:
            return False
    if "types" in requirements:
        required_types = [t.lower() for t in requirements["types"]]
        mon_types = [mon.get(k, "").lower() for k in ["type1", "type2", "type3", "type4", "type5"] if mon.get(k)]
        if not any(r in mon_types for r in required_types):
            return False
    return True

def get_viable_mons(user_id: str, mission: dict) -> list:
    from core.database import get_all_mons_for_user  # assumed exported from core.database
    all_mons = get_all_mons_for_user(user_id)
    reqs = mission.get("requirements")
    if not reqs:
        return all_mons
    if isinstance(reqs, str):
        try:
            reqs = json.loads(reqs)
        except Exception:
            reqs = {}
    viable = [mon for mon in all_mons if meets_requirements(mon, reqs)]
    return viable

def fetch_missions(user_id: str):
    all_missions = load_missions()
    filtered = []
    for mission in all_missions:
        if get_viable_mons(user_id, mission):
            filtered.append(mission)
    if len(filtered) > 6:
        return random.sample(filtered, 6)
    return filtered

# ----------------------------
# Persistent Active Mission Handling using Centralized CRUD
# ----------------------------

def db_store_active_mission(user_id: str, mission_record: dict):
    data = json.dumps(mission_record)
    existing = fetch_one("SELECT user_id FROM active_missions WHERE user_id = ?", (user_id,))
    if existing:
        # Update existing record using centralized update_record with a custom id_field.
        update_record("active_missions", user_id, {"data": data}, id_field="user_id")
    else:
        # Insert a new record.
        insert_record("active_missions", {"user_id": user_id, "data": data})

def db_get_active_mission(user_id: str) -> dict:
    row = fetch_one("SELECT data FROM active_missions WHERE user_id = ?", (user_id,))
    if row:
        try:
            return json.loads(row["data"])
        except Exception:
            return None
    return None

def db_delete_active_mission(user_id: str):
    # Remove the active mission using centralized remove_record.
    remove_record("active_missions", user_id, id_field="user_id")

# ----------------------------
# Mission Progress and Rewards
# ----------------------------

def start_mission(user_id: str, mission_id: int, selected_mons: list) -> dict:
    missions = load_missions()
    mission = next((m for m in missions if m["id"] == mission_id), None)
    if not mission:
        return None
    required_progress = mission["difficulty"] * random.randint(10, 40)
    active_mission = {
        "mission_id": mission_id,
        "mission_name": mission["name"],
        "flavor": mission.get("flavor", ""),
        "required_progress": required_progress,
        "current_progress": 0,
        "selected_mons": selected_mons,
        "repeatable": mission.get("repeatable", True),
        "reward": {
            "rollmons_reward": mission.get("rollmons_reward"),
            "item_reward": mission.get("item_reward"),
            "level_reward": mission.get("level_reward", 0),
            "coin_reward": mission.get("coin_reward", 0)
        },
        "artwork": {
            "in_progress": mission.get("in_progress_artwork", "default_in_progress.png"),
            "complete": mission.get("complete_artwork", "default_complete.png")
        }
    }
    db_store_active_mission(user_id, active_mission)
    return active_mission

def progress_mission(user_id: str, amount: int) -> dict:
    mission = db_get_active_mission(user_id)
    if not mission:
        return {"error": "No active mission found."}
    mission["current_progress"] += amount
    mission["complete"] = mission["current_progress"] >= mission["required_progress"]
    db_store_active_mission(user_id, mission)
    return mission

async def process_mon_level_reward(user_id: str, mon_name: str, level_reward: int) -> str:
    row = fetch_one("SELECT mon_id, trainer_id, level FROM mons WHERE mon_name = ? AND player_user_id = ?", (mon_name, user_id))
    if not row:
        return f"Mon '{mon_name}' not found or does not belong to you."
    mon_id, trainer_id, current_level = row["mon_id"], row["trainer_id"], row["level"]
    trainer_row = fetch_one("SELECT name FROM trainers WHERE id = ?", (trainer_id,))
    if not trainer_row:
        return "Trainer not found for that mon."
    trainer_name = trainer_row["name"]
    new_level = current_level + level_reward
    if current_level >= 100:
        extra_coins = level_reward * 25
        add_currency(user_id, extra_coins)
        return f"Mon '{mon_name}' is at level 100. Converted {level_reward} level(s) into {extra_coins} coins."
    elif new_level > 100:
        effective_levels = 100 - current_level
        excess = level_reward - effective_levels
        success = await update_character_level(trainer_name, mon_name, effective_levels)
        if success:
            update_mon_data(mon_id, level=new_level)
            extra_coins = excess * 25
            add_currency(user_id, extra_coins)
            return f"Mon '{mon_name}' reached level 100. Added {effective_levels} level(s) and converted {excess} extra level(s) into {extra_coins} coins."
        else:
            return "Failed to update the mon's sheet."
    else:
        success = await update_character_level(trainer_name, mon_name, level_reward)
        if success:
            update_mon_data(mon_id, level=new_level)
            return f"Added {level_reward} level(s) to mon '{mon_name}' on trainer {trainer_name}'s sheet."
        else:
            return "Failed to update the mon's sheet."

async def claim_mission_rewards(ctx, user_id: str) -> str:
    mission = db_get_active_mission(user_id)
    if not mission:
        return "No active mission found."
    if not mission.get("complete", False):
        return "Mission not complete yet."
    reward_summary = []
    coin_reward = mission["reward"].get("coin_reward", 0)
    if coin_reward:
        add_currency(user_id, coin_reward)
        reward_summary.append(f"{coin_reward} coins")
    level_reward = mission["reward"].get("level_reward", 0)
    if level_reward and mission.get("selected_mons"):
        level_msgs = []
        for mon_name in mission["selected_mons"]:
            msg = await process_mon_level_reward(user_id, mon_name, level_reward)
            level_msgs.append(msg)
        reward_summary.append("Level Rewards: " + "; ".join(level_msgs))
    item_reward = mission["reward"].get("item_reward")
    if item_reward:
        try:
            num_items = int(item_reward)
        except Exception:
            num_items = 1
        from core.items import roll_items
        rolled_items = await roll_items(num=num_items)
        if rolled_items:
            first_mon = mission["selected_mons"][0]
            row = fetch_one("SELECT trainer_id FROM mons WHERE mon_name = ? AND player_user_id = ?", (first_mon, user_id))
            if row:
                trainer_row = fetch_one("SELECT name FROM trainers WHERE id = ?", (row["trainer_id"],))
                if trainer_row:
                    trainer_name = trainer_row["name"]
                    success_items = []
                    for item in rolled_items:
                        success = await update_character_sheet_item(trainer_name, item, 1)
                        if success:
                            success_items.append(item)
                    if success_items:
                        reward_summary.append("Items: " + ", ".join(success_items))
                    else:
                        reward_summary.append("Failed to update sheet with items.")
                else:
                    reward_summary.append("Trainer not found for item reward.")
            else:
                reward_summary.append("No trainer found for item reward.")
        else:
            reward_summary.append("No items rolled.")
    rollmons_reward = mission["reward"].get("rollmons_reward")
    if rollmons_reward:
        from core.rollmons import roll_mons
        rolled_mon = roll_mons(ctx, 'default', 1)
        if rolled_mon:
            reward_summary.append(f"Mon reward: {rolled_mon.get('name', 'Unknown')}")
        else:
            reward_summary.append("No mon reward rolled.")
    if not mission.get("repeatable", True):
        mark_mission_done(user_id, mission["mission_id"])
    db_delete_active_mission(user_id)
    summary = "Rewards claimed: " + ", ".join(reward_summary)
    return summary

def mark_mission_done(user_id: str, mission_id: int):
    execute_query("INSERT OR IGNORE INTO completed_missions (user_id, mission_id) VALUES (?,?)", (user_id, mission_id))

def get_active_mission(user_id: str) -> dict:
    return db_get_active_mission(user_id)

