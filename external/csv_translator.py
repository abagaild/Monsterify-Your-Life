#this takes CSV files and itterates them into corresponding tables in the database, leaving this here to easily update digimon and pokemon tables if needed
import sqlite3
import csv


def create_table_from_csv(csv_file, db_name):
    """
    Creates a table from a CSV file in the specified SQLite database.
    The table name will be the same as the CSV filename (without the extension).
    """
    table_name = csv_file.split('.')[0]  # Extract table name from CSV filename (excluding extension)

    # Connect to the SQLite database
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    # Read the CSV file and create the table with column names from the first row
    with open(csv_file, 'r', encoding='utf-8') as file:
        reader = csv.reader(file)
        headers = next(reader)  # First row contains column names

        # Create the table dynamically
        columns = ", ".join([f"{header} TEXT" for header in headers])  # Assuming all columns are of TEXT type
        cursor.execute(f"CREATE TABLE IF NOT EXISTS {table_name} ({columns})")

        # Insert rows into the table
        for row in reader:
            placeholders = ", ".join(["?" for _ in headers])  # Placeholder for each value
            cursor.execute(f"INSERT INTO {table_name} ({', '.join(headers)}) VALUES ({placeholders})", row)

    # Commit the changes and close the connection
    conn.commit()
    conn.close()


# Example usage: Creating tables from three CSV files
#csv_files = ['Digimon.csv', 'Pokemon.csv', 'Yokai.csv']  # List of your CSV files
csv_files = ['pokemon_babies.csv']  # List of your CSV files
db_name = 'bot_data.db'  # Your SQLite database file

for csv_file in csv_files:
    create_table_from_csv(csv_file, db_name)

print("CSV files have been imported into the database.")
