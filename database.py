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
    cursor.execute('''
            CREATE TABLE IF NOT EXISTS fundamentals_annual (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT,
                year INTEGER,
                revenue REAL,
                cogs REAL,
                gross_margin REAL,
                operating_income REAL,
                operating_margin REAL,
                net_income REAL,
                net_margin REAL,
                shares REAL,
                eps REAL,
                UNIQUE (ticker, year)
            )
        ''')
    conn.commit()
    cursor.close()
    conn.close()


def insert_price(data):  # 把價格丟進去資料庫
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


def insert_fundamentals(df):
    conn = sqlite3.connect('database/stock.db')
    cursor = conn.cursor()

    sql = """
    INSERT INTO fundamentals_annual (
        ticker, year, revenue, cogs, gross_margin,
        operating_income, operating_margin, net_income, net_margin,
        shares, eps
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(ticker, year)
    DO UPDATE SET
        revenue=excluded.revenue,
        cogs=excluded.cogs,
        gross_margin=excluded.gross_margin,
        operating_income=excluded.operating_income,
        operating_margin=excluded.operating_margin,
        net_income=excluded.net_income,
        net_margin=excluded.net_margin,
        shares=excluded.shares,
        eps=excluded.eps;
    """

    data_to_insert = list(df.itertuples(index=False, name=None))  # executemany可以直接用
    cursor.executemany(sql, data_to_insert)
    conn.commit()
    conn.close()


def select_fundamentals(ticker):
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
        SELECT ticker, year, revenue, cogs, gross_margin,operating_income, operating_margin, net_income, net_margin,shares, eps
        FROM fundamentals_annual
        WHERE ticker = ?
        ORDER BY year
        """
        df = pd.read_sql_query(sql, conn, params=(ticker,))
        return df

    finally:
        conn.close()


def select_price(ticker):
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
    刪除指定股票的所有資料（股價 + 基本面）

    參數:
        ticker (str): 股票代碼，例如 "AAPL"

    回傳:
        bool: 是否有成功刪除任何資料
    """
    conn = sqlite3.connect('database/stock.db')
    cursor = conn.cursor()

    try:
        # 刪除股價資料
        cursor.execute("""
            DELETE FROM price_daily
            WHERE ticker = ?
        """, (ticker,))
        price_deleted = cursor.rowcount

        # 刪除基本面資料
        cursor.execute("""
            DELETE FROM fundamentals_annual
            WHERE ticker = ?
        """, (ticker,))
        fundamentals_deleted = cursor.rowcount

        conn.commit()

        print(
            f"🗑️ {ticker} deleted | "
            f"price_daily: {price_deleted}, "
            f"fundamentals_annual: {fundamentals_deleted}"
        )

        # 只要其中一個有刪到，就算成功
        return (price_deleted + fundamentals_deleted) > 0

    except sqlite3.Error as e:
        print("❌ 刪除失敗：", e)
        return False

    finally:
        conn.close()