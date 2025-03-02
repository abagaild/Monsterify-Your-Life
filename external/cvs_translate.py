import csv
import sqlite3


def main():
    csv_file = 'data.csv'

    # Connect to (or create) the SQLite database file.
    conn = sqlite3.connect('../bot_data.db')
    cur = conn.cursor()

    try:
        # Open the CSV file and read its header.
        with open(csv_file, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            if not fieldnames:
                print("CSV file must have headers.")
                return

            # Quote all column names to avoid conflicts with SQL keywords.
            columns = ', '.join([
                f'"{field}" TEXT PRIMARY KEY' if field == "Name" else f'"{field}" TEXT'
                for field in fieldnames
            ])
            create_table_query = f"CREATE TABLE IF NOT EXISTS Digimon ({columns});"
            cur.execute(create_table_query)
            conn.commit()

            # Prepare the insert statement with quoted column names.
            placeholders = ', '.join('?' for _ in fieldnames)
            quoted_fields = ', '.join([f'"{field}"' for field in fieldnames])
            insert_query = f"INSERT OR IGNORE INTO Digimon ({quoted_fields}) VALUES ({placeholders});"

            # Insert each row into the table.
            for row in reader:
                values = [row[field] for field in fieldnames]
                cur.execute(insert_query, values)
            conn.commit()

        print("Data has been imported into the 'Digimon' table; duplicate 'Name' entries have been ignored.")

    except FileNotFoundError:
        print(f"Error: The file '{csv_file}' was not found.")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
