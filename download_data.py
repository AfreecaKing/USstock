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


def update_all_ticker(update_fundamentals=False):
    """
    更新所有股票的價格資料
    
    Args:
        update_fundamentals: 是否同時更新基本面資料（預設 False，因為基本面是年度資料）
    """
    tickers = db.get_all_tickers()
    print(f"📈 Updating {len(tickers)} stocks (fundamentals: {update_fundamentals})")
    
    success_count = 0
    fail_count = 0
    
    for i, ticker in enumerate(tickers, 1):
        try:
            print(f"[{i}/{len(tickers)}] 🔄 Updating {ticker}...", end=" ")
            
            # 取得最後更新日期
            last_date = db.get_last_price_date(ticker)
            
            ticker_obj = yf.Ticker(ticker)
            
            # 如果有最後日期，只抓取之後的資料
            if last_date:
                # 從最後日期的隔天開始抓
                from datetime import datetime, timedelta
                start_date = (datetime.strptime(last_date, '%Y-%m-%d') + timedelta(days=1)).strftime('%Y-%m-%d')
                df = ticker_obj.history(start=start_date)
                
                if df.empty:
                    print("✓ Already up to date")
                    success_count += 1
                    continue
                    
                print(f"📥 {len(df)} new records", end=" ")
            else:
                # 沒有歷史資料，抓全部
                df = ticker_obj.history(period="max")
                print(f"📥 {len(df)} records (full history)", end=" ")
            
            if df.empty:
                print("⚠️ No data available")
                fail_count += 1
                continue

            # 處理資料格式
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
            
            # 四捨五入兩位、volume 強制整數
            price_cols = ['open', 'high', 'low', 'close', 'dividends', 'stock_splits']
            df[price_cols] = df[price_cols].round(2)
            df['volume'] = df['volume'].astype(int)

            db.insert_price(df)
            
            # 選擇性更新基本面
            if update_fundamentals:
                print("+ updating fundamentals...", end=" ")
                fetch_and_store_fundamentals(ticker)
            
            print("✅")
            success_count += 1
            
        except Exception as e:
            print(f"❌ Error: {e}")
            fail_count += 1
    
    print(f"\n{'='*50}")
    print(f"📊 Update Summary:")
    print(f"   ✅ Success: {success_count}/{len(tickers)}")
    print(f"   ❌ Failed: {fail_count}/{len(tickers)}")
    print(f"{'='*50}")


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

        # ⭐ 修正：檢查是否有 us-gaap 資料
        if "facts" not in facts:
            print(f"⚠️  {ticker}: No facts data available")
            return True  # 回傳 True 讓股票仍可新增

        # 嘗試取得 us-gaap，如果沒有則嘗試其他標準
        us_gaap = None
        if "us-gaap" in facts["facts"]:
            us_gaap = facts["facts"]["us-gaap"]
        elif "ifrs-full" in facts["facts"]:
            # 某些外國公司使用 IFRS 而非 US GAAP
            us_gaap = facts["facts"]["ifrs-full"]
            print(f"ℹ️  {ticker}: Using IFRS standards instead of US-GAAP")
        else:
            # 列出可用的會計標準
            available_standards = list(facts["facts"].keys())
            print(f"⚠️  {ticker}: No us-gaap or ifrs-full found. Available: {available_standards}")
            return True  # 回傳 True 讓股票仍可新增

        # 抓年度資料 - 損益表
        revenue = extract_annual_from_tags(us_gaap, [
            "SalesRevenueNet",
            "Revenues",
            "RevenueFromContractWithCustomerExcludingAssessedTax",
            "Revenue"
        ])

        if not revenue:
            print(f"⚠️  {ticker}: No revenue data found")
            return True

        cogs = extract_annual_from_tags(us_gaap, [
            "CostOfRevenue",
            "CostOfGoodsAndServicesSold",
            "CostOfRevenueIncludingSpecialItems"
        ])
        operating_income = extract_annual_from_tags(us_gaap, ["OperatingIncomeLoss"])
        net_income = extract_annual_from_tags(us_gaap, ["NetIncomeLoss"])
        shares = extract_annual_from_tags(us_gaap, [
            "WeightedAverageNumberOfDilutedSharesOutstanding",
            "WeightedAverageNumberOfSharesOutstandingDiluted"
        ])

        # 抓年度資料 - 現金流量表
        operating_cash_flow = extract_annual_from_tags(us_gaap, [
            "NetCashProvidedByUsedInOperatingActivities",
            "CashProvidedByUsedInOperatingActivities"
        ])
        investing_cash_flow = extract_annual_from_tags(us_gaap, [
            "NetCashProvidedByUsedInInvestingActivities",
            "CashProvidedByUsedInInvestingActivities"
        ])
        financing_cash_flow = extract_annual_from_tags(us_gaap, [
            "NetCashProvidedByUsedInFinancingActivities",
            "CashProvidedByUsedInFinancingActivities"
        ])
        capex = extract_annual_from_tags(us_gaap, [
            "PaymentsToAcquirePropertyPlantAndEquipment",
            "CapitalExpendituresIncurredButNotYetPaid"
        ])

        # 抓年度資料 - 資產負債表
        total_assets = extract_annual_from_tags(us_gaap, ["Assets"])
        total_liabilities = extract_annual_from_tags(us_gaap, [
            "Liabilities",
            "LiabilitiesAndStockholdersEquity"
        ])
        current_liabilities = extract_annual_from_tags(us_gaap, [
            "LiabilitiesCurrent",
            "CurrentLiabilities"
        ])
        long_term_debt = extract_annual_from_tags(us_gaap, [
            "LongTermDebtNoncurrent",
            "LongTermDebt"
        ])
        stockholders_equity = extract_annual_from_tags(us_gaap, [
            "StockholdersEquity",
            "ShareholdersEquity"
        ])

        # 計算衍生指標
        eps = {year: net_income[year] / shares[year] 
               for year in net_income if year in shares and shares[year] != 0}

        # 毛利率 / 營業利益率 / 淨利率
        gross_margin = {year: (revenue[year] - cogs[year]) / revenue[year]
                        for year in revenue if year in cogs and revenue[year] != 0}
        operating_margin = {year: operating_income[year] / revenue[year]
                            for year in revenue if year in operating_income and revenue[year] != 0}
        net_margin = {year: net_income[year] / revenue[year]
                      for year in revenue if year in net_income and revenue[year] != 0}

        # 自由現金流 = 營運現金流 - 資本支出
        free_cash_flow = {year: operating_cash_flow.get(year, 0) - abs(capex.get(year, 0))
                          for year in operating_cash_flow}

        # 負債比率
        debt_to_asset_ratio = {year: total_liabilities[year] / total_assets[year]
                               for year in total_assets if year in total_liabilities and total_assets[year] != 0}

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
            "operating_cash_flow": [int(operating_cash_flow.get(y, 0)) for y in revenue],
            "investing_cash_flow": [int(investing_cash_flow.get(y, 0)) for y in revenue],
            "financing_cash_flow": [int(financing_cash_flow.get(y, 0)) for y in revenue],
            "free_cash_flow": [int(free_cash_flow.get(y, 0)) for y in revenue],
            "total_assets": [int(total_assets.get(y, 0)) for y in revenue],
            "total_liabilities": [int(total_liabilities.get(y, 0)) for y in revenue],
            "current_liabilities": [int(current_liabilities.get(y, 0)) for y in revenue],
            "long_term_debt": [int(long_term_debt.get(y, 0)) for y in revenue],
            "stockholders_equity": [int(stockholders_equity.get(y, 0)) for y in revenue],
            "debt_to_asset_ratio": [round(float(debt_to_asset_ratio.get(y, 0)), 4) for y in revenue],
        })

        if df.empty:
            print(f"⚠️  {ticker}: No valid fundamental data")
            return True

        # 存入資料庫
        db.insert_fundamentals(df)
        print(f"✅ {ticker} fundamentals stored ({len(df)} years)")
        return True

    except ValueError as e:
        # ticker 在 SEC 找不到（可能是外國公司、ETF 等）
        print(f"⚠️  {ticker}: {e} (可能不在 SEC 註冊)")
        return True  # 回傳 True 讓股票仍可新增

    except requests.HTTPError as e:
        if e.response.status_code == 404:
            print(f"⚠️  {ticker}: No SEC filings found (可能是外國公司或 ETF)")
        else:
            print(f"❌ {ticker}: HTTP error {e.response.status_code}")
        return True  # 回傳 True 讓股票仍可新增

    except KeyError as e:
        print(f"❌ Failed to fetch fundamentals for {ticker}: missing key {e}")
        return True  # 回傳 True 讓股票仍可新增

    except Exception as e:
        print(f"❌ Failed to fetch fundamentals for {ticker}: {e}")
        return True  # 回傳 True 讓股票仍可新增
