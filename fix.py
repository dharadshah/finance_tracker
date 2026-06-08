import sqlite3, glob
db = glob.glob('**/*.db', recursive=True)[0]
conn = sqlite3.connect(db)
conn.execute("ALTER TABLE accounts ADD COLUMN owner VARCHAR(50) DEFAULT 'Dhara'")
conn.execute("UPDATE accounts SET owner = 'Dhara'")
conn.commit()
print('Done')
conn.close()