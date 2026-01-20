import yfinance as yf
import database as db
import pandas as pd
import requests

HEADERS = {"User-Agent": "j74062@email.com"}


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
            'Dividends': 'dividends',
            'Volume': 'volume',
            'Stock Splits': 'stock_splits'
        })
        df = df[['date', 'open', 'high', 'low', 'close',
                 'volume', 'dividends', 'stock_splits', 'ticker']]
        df['date'] = df['date'].dt.strftime('%Y-%m-%d')
        # ⭐ 四捨五入兩位、volume 強制整數
        price_cols = ['open', 'high', 'low', 'close', 'dividends', 'stock_splits']
        df[price_cols] = df[price_cols].round(2)
        df['volume'] = df['volume'].astype(int)

        db.insert_price(df)
        return True


def update_all_ticker():
    tickers = db.get_all_tickers()
    print(f"📈 Updating {len(tickers)} stocks")
    for ticker in tickers:
        try:
            print(f"🔄 Fetching {ticker} up to today")
            ticker_obj = yf.Ticker(ticker)
            df = ticker_obj.history(period="max")
            fetch_and_store_fundamentals(ticker)
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
            # ⭐ 四捨五入兩位、volume 強制整數
            price_cols = ['open', 'high', 'low', 'close', 'dividends', 'stock_splits']
            df[price_cols] = df[price_cols].round(2)
            df['volume'] = df['volume'].astype(int)

            db.insert_price(df)
            print(f"✅ {ticker} updated ({len(df)} rows total)")
        except Exception as e:
            print(f"❌ {ticker} failed: {e}")


def ticker_to_cik(ticker):
    url = "https://www.sec.gov/files/company_tickers.json"
    r = requests.get(url, headers=HEADERS)
    r.raise_for_status()
    data = r.json()
    df = pd.DataFrame(data).T
    row = df[df["ticker"] == ticker.upper()]
    if row.empty:
        raise ValueError(f"{ticker} not found")
    return str(row.iloc[0]["cik_str"]).zfill(10)


# ====== 取得公司標準化財報資料 ======
def get_company_facts(cik):
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
    r = requests.get(url, headers=HEADERS)
    r.raise_for_status()
    return r.json()


# ====== 從多個 GAAP tag 抓年度資料 ======
def extract_annual_from_tags(us_gaap, tags):
    data = {}
    for tag in tags:
        if tag not in us_gaap:
            continue
        units = us_gaap[tag].get("units", {})
        if not units:
            continue
        first_unit_key = list(units.keys())[0]
        for r in units[first_unit_key]:
            if r.get("form") == "10-K" and "fy" in r:
                data[r["fy"]] = r["val"]
    return data


# ====== 抓歷史年度基本面並存資料庫 ======
def fetch_and_store_fundamentals(ticker):
    try:
        cik = ticker_to_cik(ticker)
        facts = get_company_facts(cik)
        us_gaap = facts["facts"]["us-gaap"]

        # 抓年度資料
        revenue = extract_annual_from_tags(us_gaap, [
            "SalesRevenueNet",
            "Revenues",
            "RevenueFromContractWithCustomerExcludingAssessedTax"
        ])
        cogs = extract_annual_from_tags(us_gaap, [
            "CostOfRevenue",
            "CostOfGoodsAndServicesSold",
            "CostOfRevenueIncludingSpecialItems"
        ])
        operating_income = extract_annual_from_tags(us_gaap, ["OperatingIncomeLoss"])
        net_income = extract_annual_from_tags(us_gaap, ["NetIncomeLoss"])
        shares = extract_annual_from_tags(us_gaap, ["WeightedAverageNumberOfDilutedSharesOutstanding"])

        # EPS
        eps = {year: net_income[year] / shares[year] for year in net_income if year in shares}

        # 毛利率 / 營業利益率 / 淨利率
        gross_margin = {year: (revenue[year] - cogs[year]) / revenue[year] for year in revenue if year in cogs}
        operating_margin = {year: operating_income[year] / revenue[year] for year in revenue if
                            year in operating_income}
        net_margin = {year: net_income[year] / revenue[year] for year in revenue if year in net_income}

        # 整理 DataFrame
        df = pd.DataFrame({
            "ticker": ticker,
            "year": [int(y) for y in revenue.keys()],
            "revenue": [int(revenue[y]) for y in revenue],
            "cogs": [int(cogs.get(y, 0)) for y in revenue],
            "gross_margin": [round(float(gross_margin.get(y, 0)), 4) for y in revenue],
            "operating_income": [int(operating_income.get(y, 0)) for y in revenue],
            "operating_margin": [round(float(operating_margin.get(y, 0)), 4) for y in revenue],
            "net_income": [int(net_income.get(y, 0)) for y in revenue],
            "net_margin": [round(float(net_margin.get(y, 0)), 4) for y in revenue],
            "shares": [int(shares.get(y, 0)) for y in revenue],
            "eps": [round(float(eps.get(y, 0)), 4) for y in revenue],
        })

        # 存入資料庫
        db.insert_fundamentals(df)
        print(f"✅ {ticker} fundamentals stored ({len(df)} years)")
        return True

    except Exception as e:
        print(f"❌ Failed to fetch fundamentals for {ticker}: {e}")
        return False
