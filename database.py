import sqlite3
import pandas as pd
import os


def create_table():
    os.makedirs('./database', exist_ok=True)
    conn = sqlite3.connect('database/stock.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS price_daily (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume INTEGER,
            dividends REAL,
            stock_splits REAL,
            ticker TEXT,
            UNIQUE (ticker, date))
            ''')
    conn.commit()
    cursor.close()
    conn.close()


def insert_data(data):  # 把資料丟進去資料庫
    conn = sqlite3.connect('database/stock.db')
    cursor = conn.cursor()
    sql = """
    INSERT INTO price_daily (
        date, open, high, low, close, volume, dividends, stock_splits,ticker
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(ticker, date)
    DO UPDATE SET
        open = excluded.open,
        high = excluded.high,
        low = excluded.low,
        close = excluded.close,
        volume = excluded.volume,
        dividends = excluded.dividends,
        stock_splits = excluded.stock_splits;
    """
    data_to_insert = list(data.itertuples(index=False, name=None))  # executemany可以直接用
    cursor.executemany(sql, data_to_insert)
    conn.commit()
    conn.close()


def select_data(ticker):
    """
    取得指定股票的歷史股價資料，回傳 DataFrame

    參數:
        ticker (str): 股票代碼，例如 "AAPL"

    回傳:
        pd.DataFrame: 包含 date, open, high, low, close, volume, dividends, stock_splits
    """

    conn = sqlite3.connect('database/stock.db')

    try:
        sql = f"""
        SELECT date, open, high, low, close, volume, dividends, stock_splits
        FROM price_daily
        WHERE ticker = ?
        ORDER BY date
        """
        df = pd.read_sql_query(sql, conn, params=(ticker,))
        df['date'] = pd.to_datetime(df['date'])
        return df

    finally:
        conn.close()


def get_all_tickers():  # 抓出所有股票名字
    conn = sqlite3.connect('database/stock.db')
    cursor = conn.cursor()

    cursor.execute("""
        SELECT DISTINCT ticker
        FROM price_daily
    """)

    tickers = [row[0] for row in cursor.fetchall()]
    conn.close()
    return tickers


def delete_ticker(ticker):
    """
    刪除指定股票的所有資料

    參數:
        ticker (str): 股票代碼，例如 "AAPL"

    回傳:
        bool: 是否刪除成功
    """
    conn = sqlite3.connect('database/stock.db')
    cursor = conn.cursor()

    try:
        cursor.execute("""
            DELETE FROM price_daily
            WHERE ticker = ?
        """, (ticker,))

        conn.commit()
        return cursor.rowcount > 0  # 有刪到資料才回 True

    except sqlite3.Error as e:
        print("刪除失敗：", e)
        return False

    finally:
        conn.close()
