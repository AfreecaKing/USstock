import requests
import pandas as pd

# ====== 設定 User-Agent，SEC 官方規定 ======
HEADERS = {"User-Agent": "j74062@email.com"}


# ====== Ticker → CIK ======
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


# ====== 主函式 ======
def get_10k_financials(ticker):
    cik = ticker_to_cik(ticker)
    facts = get_company_facts(cik)
    us_gaap = facts["facts"]["us-gaap"]

    # Revenue、OperatingIncome、NetIncome
    revenue = extract_annual_from_tags(us_gaap, [
        "SalesRevenueNet",
        "Revenues",
        "RevenueFromContractWithCustomerExcludingAssessedTax"
    ])
    operating_income = extract_annual_from_tags(us_gaap, ["OperatingIncomeLoss"])
    net_income = extract_annual_from_tags(us_gaap, ["NetIncomeLoss"])

    # 股數
    shares = extract_annual_from_tags(us_gaap, ["WeightedAverageNumberOfDilutedSharesOutstanding"])

    # EPS
    eps = {year: net_income[year] / shares[year] for year in net_income if year in shares}

    # COGS 多個備選
    cogs = extract_annual_from_tags(us_gaap, [
        "CostOfRevenue",
        "CostOfGoodsAndServicesSold",
        "CostOfRevenueIncludingSpecialItems"
    ])

    # 毛利率
    gross_margin = {year: (revenue[year] - cogs[year]) / revenue[year] for year in revenue if year in cogs}

    # 營業利益率
    operating_margin = {year: operating_income[year] / revenue[year] for year in revenue if year in operating_income}

    # 淨利率
    net_margin = {year: net_income[year] / revenue[year] for year in revenue if year in net_income}

    # 整理成 DataFrame
    df = pd.DataFrame({
        "revenue": revenue,
        "cogs": cogs,
        "gross_margin": gross_margin,
        "operating_income": operating_income,
        "operating_margin": operating_margin,
        "net_income": net_income,
        "net_margin": net_margin,
        "shares": shares,
        "eps": eps,
    }).sort_index()
    df['ticker'] = ticker
    return df


# ====== 範例：Apple ======
# 假設你已經有每年年末股價


df = get_10k_financials("AAPL")
print(df)

# 存成 CSV
df.to_csv("AAPL_10K_full.csv")
