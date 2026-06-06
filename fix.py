import sqlite3
import glob

db_files = glob.glob('**/*.db', recursive=True)
for db in db_files:
    conn = sqlite3.connect(db)
    cur = conn.cursor()
    # Delete the bad account with 'investment' type
    cur.execute("DELETE FROM accounts WHERE account_type='investment'")
    print(f"Deleted {cur.rowcount} bad account(s)")
    conn.commit()
    cur.execute("SELECT id, name, account_type, institution FROM accounts")
    for row in cur.fetchall():
        print(row)
    conn.close()