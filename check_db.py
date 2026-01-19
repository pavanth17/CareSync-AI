import sqlite3

conn = sqlite3.connect('patient_care_dev.db')
cursor = conn.cursor()

# Get table names
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print("Tables:", [t[0] for t in tables])

# Get patient schema
cursor.execute("PRAGMA table_info(patients)")
cols = cursor.fetchall()
print("\nPatients table columns:")
for col in cols:
    print(f"  {col[1]}: {col[2]}")

# Get sample patient data
cursor.execute("SELECT * FROM patients LIMIT 3")
patients = cursor.fetchall()
print(f"\nSample patients ({len(patients)} rows):")
for p in patients:
    print(f"  {p}")

# Check ChatMessage table
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='chat_message'")
chat_exists = cursor.fetchone()
print(f"\nChatMessage table exists: {chat_exists is not None}")

if chat_exists:
    cursor.execute("PRAGMA table_info(chat_message)")
    cols = cursor.fetchall()
    print("ChatMessage table columns:")
    for col in cols:
        print(f"  {col[1]}: {col[2]}")

conn.close()
