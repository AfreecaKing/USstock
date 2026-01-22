import sqlite3
import pandas as pd
import os


def create_table():
    os.makedirs('./database', exist_ok=True)
    conn = sqlite3.connect('database/stock.db')
    cursor = conn.cursor()

    # 原有的價格表
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

    # 原有的基本面表
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

    # 新增：分類表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
    ''')

    # 新增：股票分類對應表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ticker_categories (
            ticker TEXT,
            category_id INTEGER,
            PRIMARY KEY (ticker, category_id),
            FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE
        )
    ''')

    conn.commit()
    cursor.close()
    conn.close()


def insert_price(data):
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
    data_to_insert = list(data.itertuples(index=False, name=None))
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

    data_to_insert = list(df.itertuples(index=False, name=None))
    cursor.executemany(sql, data_to_insert)
    conn.commit()
    conn.close()


def select_fundamentals(ticker):
    conn = sqlite3.connect('database/stock.db')
    try:
        sql = """
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
        sql = """
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


def get_all_tickers():
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
    conn = sqlite3.connect('database/stock.db')
    cursor = conn.cursor()
    try:
        # 刪除股價資料
        cursor.execute("DELETE FROM price_daily WHERE ticker = ?", (ticker,))
        price_deleted = cursor.rowcount

        # 刪除基本面資料
        cursor.execute("DELETE FROM fundamentals_annual WHERE ticker = ?", (ticker,))
        fundamentals_deleted = cursor.rowcount

        # 刪除分類關聯
        cursor.execute("DELETE FROM ticker_categories WHERE ticker = ?", (ticker,))

        conn.commit()
        print(f"🗑️ {ticker} deleted | price_daily: {price_deleted}, fundamentals_annual: {fundamentals_deleted}")
        return (price_deleted + fundamentals_deleted) > 0
    except sqlite3.Error as e:
        print("❌ 刪除失敗：", e)
        return False
    finally:
        conn.close()


# ========== 新增：分類管理功能 ==========

def get_all_categories():
    """取得所有分類"""
    conn = sqlite3.connect('database/stock.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM categories ORDER BY name")
    categories = cursor.fetchall()
    conn.close()
    return categories


def add_category(name):
    """新增分類"""
    conn = sqlite3.connect('database/stock.db')
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO categories (name) VALUES (?)", (name,))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False  # 分類已存在
    finally:
        conn.close()


def delete_category(category_id):
    """刪除分類（會自動刪除相關的股票-分類關聯）"""
    conn = sqlite3.connect('database/stock.db')
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM categories WHERE id = ?", (category_id,))
        conn.commit()
        return True
    except sqlite3.Error:
        return False
    finally:
        conn.close()


def assign_ticker_to_category(ticker, category_id):
    """將股票指定到分類"""
    conn = sqlite3.connect('database/stock.db')
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT OR IGNORE INTO ticker_categories (ticker, category_id)
            VALUES (?, ?)
        """, (ticker, category_id))
        conn.commit()
        return True
    except sqlite3.Error:
        return False
    finally:
        conn.close()


def remove_ticker_from_category(ticker, category_id):
    """將股票從分類中移除"""
    conn = sqlite3.connect('database/stock.db')
    cursor = conn.cursor()
    try:
        cursor.execute("""
            DELETE FROM ticker_categories
            WHERE ticker = ? AND category_id = ?
        """, (ticker, category_id))
        conn.commit()
        return True
    except sqlite3.Error:
        return False
    finally:
        conn.close()


def get_ticker_categories(ticker):
    """取得股票所屬的所有分類"""
    conn = sqlite3.connect('database/stock.db')
    cursor = conn.cursor()
    cursor.execute("""
        SELECT c.id, c.name
        FROM categories c
        JOIN ticker_categories tc ON c.id = tc.category_id
        WHERE tc.ticker = ?
        ORDER BY c.name
    """, (ticker,))
    categories = cursor.fetchall()
    conn.close()
    return categories


def get_tickers_by_category(category_id=None):
    """
    取得分類下的所有股票
    如果 category_id 為 None，回傳所有股票及其分類
    """
    conn = sqlite3.connect('database/stock.db')
    cursor = conn.cursor()

    if category_id is None:
        # 取得所有股票及其分類（支援多分類）
        cursor.execute("""
            SELECT DISTINCT pd.ticker, c.name as category_name
            FROM price_daily pd
            LEFT JOIN ticker_categories tc ON pd.ticker = tc.ticker
            LEFT JOIN categories c ON tc.category_id = c.id
            ORDER BY pd.ticker
        """)
    else:
        # 取得特定分類下的股票
        cursor.execute("""
            SELECT DISTINCT pd.ticker
            FROM price_daily pd
            JOIN ticker_categories tc ON pd.ticker = tc.ticker
            WHERE tc.category_id = ?
            ORDER BY pd.ticker
        """, (category_id,))

    result = cursor.fetchall()
    conn.close()
    return result
