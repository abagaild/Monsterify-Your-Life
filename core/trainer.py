import asyncio
import logging
from core.database import cursor, db, update_trainer_field
from core.database import fetch_trainer_by_name

def get_trainers(user_id: str) -> list:
    """
    Retrieves all trainer records for the given user.
    """
    cursor.execute("SELECT id, name, level, main_ref, user_id FROM trainers WHERE user_id = ?", (user_id,))
    rows = cursor.fetchall()
    return [{"id": row[0], "name": row[1], "level": row[2], "main_ref": row[3], "user_id": row[4]} for row in rows]

def get_other_trainers_from_db(user_id: str) -> list:
    cursor.execute("SELECT id, name, level, main_ref, user_id FROM trainers WHERE user_id != ?", (user_id,))
    rows = cursor.fetchall()
    return [{"id": row[0], "name": row[1], "level": row[2], "main_ref": row[3], "user_id": row[4]} for row in rows]

def add_trainer(user_id: str, name: str, level: int = 1, main_ref: str = ""):
    cursor.execute("INSERT INTO trainers (user_id, name, level, main_ref) VALUES (?, ?, ?, ?)", (user_id, name, level, main_ref))
    db.commit()

def delete_trainer(user_id: str, trainer_name: str):
    cursor.execute("DELETE FROM trainers WHERE user_id = ? AND LOWER(name) = ?", (user_id, trainer_name.lower()))
    db.commit()

def update_trainer(trainer_id: int, **kwargs):
    if not kwargs:
        return
    fields = []
    values = []
    for key, value in kwargs.items():
        fields.append(f"{key} = ?")
        values.append(value)
    values.append(trainer_id)
    query = "UPDATE trainers SET " + ", ".join(fields) + " WHERE id = ?"
    cursor.execute(query, tuple(values))
    db.commit()

async def assign_levels_to_trainer(interaction, trainer_name: str, levels: int):
    user_id = str(interaction.user.id)
    cursor.execute("SELECT id, level FROM trainers WHERE user_id = ? AND LOWER(name)=?", (user_id, trainer_name.lower()))
    row = cursor.fetchone()
    if not row:
        await interaction.response.send_message(f"Trainer '{trainer_name}' not found. Please add the trainer first.", ephemeral=True)
        return
    trainer_id, current_level = row
    new_level = current_level + levels
    update_trainer_field(trainer_id, "level", new_level)
    await interaction.response.send_message(
        f"Assigned {levels} levels to trainer '{trainer_name}'. New level: {new_level}.",
        ephemeral=True
    )

def get_all_trainers() -> list:
    """
    Retrieves all trainers from the database.
    """
    cursor.execute("SELECT id, name, level, main_ref, user_id FROM trainers")
    rows = cursor.fetchall()
    return [{"id": row[0], "name": row[1], "level": row[2], "main_ref": row[3], "user_id": row[4]} for row in rows]

def get_mons_for_trainer_dict(trainer_id: int) -> list:
    """
    Retrieves all mons for the given trainer as a list of dictionaries.
    """
    query = """
        SELECT id, mon_name, level, species1, species2, species3, main_ref 
        FROM mons 
        WHERE trainer_id = ?
    """
    cursor.execute(query, (trainer_id,))
    rows = cursor.fetchall()
    mons = []
    for row in rows:
        mon = {
            "id": row[0],
            "mon_name": row[1],
            "level": row[2],
            "species1": row[3] if row[3] is not None else "",
            "species2": row[4] if row[4] is not None else "",
            "species3": row[5] if row[5] is not None else "",
            "main_ref": row[6] if row[6] is not None else ""
        }
        mons.append(mon)
    return mons
