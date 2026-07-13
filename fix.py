import sqlite3, glob
db = glob.glob('**/*.db', recursive=True)[0]
conn = sqlite3.connect(db)
conn.execute("""
CREATE TABLE IF NOT EXISTS stock_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    symbol VARCHAR(30) NOT NULL,
    isin VARCHAR(20),
    exchange VARCHAR(10) NOT NULL,
    trade_date DATE NOT NULL,
    trade_type VARCHAR(10) NOT NULL,
    quantity NUMERIC(14,4) NOT NULL,
    price NUMERIC(14,4) NOT NULL,
    trade_id VARCHAR(50) NOT NULL,
    order_id VARCHAR(50),
    source_file VARCHAR(255),
    UNIQUE(trade_id)
)
""")
conn.execute("""
CREATE TABLE IF NOT EXISTS stock_price_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol VARCHAR(30) NOT NULL,
    exchange VARCHAR(10) NOT NULL,
    price_date DATE NOT NULL,
    close_price NUMERIC(14,4) NOT NULL,
    UNIQUE(symbol, exchange, price_date)
)
""")
conn.commit()
print('Done')
conn.close()