import yfinance as yf
import database as db


def update_all():
    tickers = db.get_all_tickers()
    print(f"📈 Updating {len(tickers)} stocks")
    for ticker in tickers:
        try:
            print(f"🔄 Fetching {ticker} up to today")
            ticker_obj = yf.Ticker(ticker)
            df = ticker_obj.history(period="max")
            if df.empty:
                print(f"⚠️ No data for {ticker}")
                continue

            df = df.reset_index()
            df['ticker'] = ticker

            df = df.rename(columns={
                'Date': 'date',
                'Open': 'open',
                'High': 'high',
                'Low': 'low',
                'Close': 'close',
                'Volume': 'volume',
                'Dividends': 'dividends',
                'Stock Splits': 'stock_splits'
            })

            df = df[['date', 'open', 'high', 'low', 'close',
                     'volume', 'dividends', 'stock_splits', 'ticker']]
            df['date'] = df['date'].dt.strftime('%Y-%m-%d')
            db.insert_data(df)
            print(f"✅ {ticker} updated ({len(df)} rows total)")

        except Exception as e:
            print(f"❌ {ticker} failed: {e}")


def insert_ticker(ticker):  # 抓個股資料
    print(f"🔄 Fetching {ticker} up to today")
    ticker_obj = yf.Ticker(ticker)
    df = ticker_obj.history(period="max")
    if df.empty:
        print(f"⚠️ No data for {ticker}")
        return False
    else:
        df = df.reset_index()
        df['ticker'] = ticker
        df = df.rename(columns={
            'Date': 'date',
            'Open': 'open',
            'High': 'high',
            'Low': 'low',
            'Close': 'close',
            'Volume': 'volume',
            'Dividends': 'dividends',
            'Stock Splits': 'stock_splits'
        })
        df = df[['date', 'open', 'high', 'low', 'close',
                 'volume', 'dividends', 'stock_splits', 'ticker']]
        df['date'] = df['date'].dt.strftime('%Y-%m-%d')
        db.insert_data(df)
        return True
