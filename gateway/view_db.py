import sqlite3
import pandas as pd

# Connect to the secure database created by the Gateway
try:
    with sqlite3.connect("secure_grid.db") as conn:
        # Read the database into a pandas DataFrame so it prints beautifully
        df = pd.read_sql_query("SELECT * FROM telemetry ORDER BY id DESC LIMIT 15", conn)
        
        print("\n=== ⚡ SECURE GRID DATABASE (LAST 15 RECORDS) ⚡ ===")
        if df.empty:
            print("Database is currently empty. Run the meter and gateway to collect data!")
        else:
            print(df.to_string(index=False))
            print("===================================================\n")
            
except sqlite3.OperationalError:
    print("Database not found! Make sure you run the Gateway first so it can create 'secure_grid.db'.")