import sqlite3

# Connect to SQLite database or create it if it doesn't exist
conn = sqlite3.connect('passport_data.db')

cursor = conn.cursor() 
# Create table
cursor.execute('''
        CREATE TABLE IF NOT EXISTS passports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            FirstName TEXT,
            LastName TEXT,
            PassportNumber TEXT UNIQUE,
            DateOfBirth DATE,
            DateOfExpiration DATE,
            DateOfIssue DATE,
            Sex TEXT,
            Nationality TEXT
        )
''') 


res = cursor.execute("SELECT name FROM sqlite_master")
print(res.fetchone())

try:
    
    conn.commit() 
    print("Table 'passports' created successfully.")
except Exception as e:
    print(f"Error creating table: {e}")
finally:
    conn.close() 

