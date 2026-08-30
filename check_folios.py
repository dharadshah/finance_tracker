import sqlite3
c = sqlite3.connect('data/finance_tracker.db')

print('NJ India outflows:')
for r in c.execute('SELECT folio_number, scheme_name, units FROM mf_transactions WHERE direction IS NOT NULL').fetchall():
    print(r)

print()
print('Kuvera transactions for same folios:')
for r in c.execute('SELECT DISTINCT folio_number, scheme_name FROM mf_transactions WHERE order_type IS NOT NULL AND folio_number IN (SELECT folio_number FROM mf_transactions WHERE direction IS NOT NULL)').fetchall():
    print(r)