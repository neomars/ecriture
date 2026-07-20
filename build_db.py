import sqlite3
import os
import sys
import re

def main():
    sql_path = "lexique_repo/lexique.sql"
    db_path = "lexique.db"

    if os.path.exists(db_path):
        os.remove(db_path)

    print("Connecting to sqlite database...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create tables with indexes for maximum speed
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS lexique (
        ortho TEXT,
        phon TEXT,
        lemme TEXT,
        cgram TEXT,
        genre TEXT,
        nombre TEXT,
        freqlemlivres REAL,
        freqlivres REAL,
        infover TEXT
    )
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_lexique_ortho ON lexique(ortho)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_lexique_lemme ON lexique(lemme)")

    print("Reading and parsing lexique.sql...")

    # We will read line by line and insert in chunks/batches
    batch = []
    count = 0

    # Regex to extract VALUES(...)
    # Example: INSERT INTO `lexique` VALUES('a','a','a','NOM','m','',81.36,58.65,81.36,58.65,'',3,8,1,1,1,'V','V',25,18,1,1,'a',1,'V','a','a','a');
    # Because of doubled single quotes, parsing can be tricky if we use a simple regex.
    # Instead, we can split by ',' but respect quoted strings, or write a state-machine/parser.
    # Actually, a simple state machine to parse the VALUES part of the string is robust and fast.

    def parse_values(line):
        # Find the start after VALUES(
        start_idx = line.find("VALUES(")
        if start_idx == -1:
            return None
        start_idx += 7
        end_idx = line.rfind(");")
        if end_idx == -1:
            end_idx = len(line)

        values_str = line[start_idx:end_idx]

        # State machine parser for SQLite SQL line values
        parts = []
        current = []
        in_quotes = False
        i = 0
        n = len(values_str)
        while i < n:
            c = values_str[i]
            if in_quotes:
                if c == "'":
                    if i + 1 < n and values_str[i+1] == "'":
                        current.append("'")
                        i += 2
                        continue
                    else:
                        in_quotes = False
                        i += 1
                        continue
                else:
                    current.append(c)
                    i += 1
            else:
                if c == "'":
                    in_quotes = True
                    i += 1
                elif c == ",":
                    parts.append("".join(current).strip())
                    current = []
                    i += 1
                else:
                    current.append(c)
                    i += 1
        parts.append("".join(current).strip())

        # We only want specific indexes:
        # ortho: index 0
        # phon: index 1
        # lemme: index 2
        # cgram: index 3
        # genre: index 4
        # nombre: index 5
        # freqlemlivres: index 7
        # freqlivres: index 9
        # infover: index 10
        if len(parts) < 11:
            return None

        try:
            ortho = parts[0]
            phon = parts[1]
            lemme = parts[2]
            cgram = parts[3]
            genre = parts[4]
            nombre = parts[5]
            freqlemlivres = float(parts[7]) if parts[7] else 0.0
            freqlivres = float(parts[9]) if parts[9] else 0.0
            infover = parts[10]
            return (ortho, phon, lemme, cgram, genre, nombre, freqlemlivres, freqlivres, infover)
        except Exception as e:
            return None

    with open(sql_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.startswith("INSERT INTO"):
                continue
            row = parse_values(line)
            if row:
                batch.append(row)
                count += 1
                if len(batch) >= 10000:
                    cursor.executemany("INSERT INTO lexique VALUES (?,?,?,?,?,?,?,?,?)", batch)
                    batch = []
                    print(f"Imported {count} rows...")

        if batch:
            cursor.executemany("INSERT INTO lexique VALUES (?,?,?,?,?,?,?,?,?)", batch)
            print(f"Imported {count} rows final.")

    conn.commit()
    conn.close()
    print("Database built successfully!")

if __name__ == "__main__":
    main()
