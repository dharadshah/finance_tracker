import sqlite3, glob
db = glob.glob('**/*.db', recursive=True)[0]
conn = sqlite3.connect(db)
conn.execute("DELETE FROM mf_nav_history")
conn.commit()
print('Cleared')
conn.close()