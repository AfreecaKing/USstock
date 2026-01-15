import yfinance as yf
import pandas as pd
import database as dt

ticker = yf.Ticker("TSLA")
data = ticker.history(period="max")

# 將 date 從索引變成欄位
data.reset_index(inplace=True)
# 統一欄位名稱為小寫
data.columns = data.columns.str.lower()
data['date'] = data['date'].dt.strftime('%Y-%m-%d')
# 加入 ticker 欄位
data['ticker'] = "TSLA"

# 確保欄位順序正確
data = data[['date', 'open', 'high', 'low', 'close', 'volume', 'dividends', 'stock splits', 'ticker']]

# 處理 'stock splits' 欄位名稱中的空格
data.rename(columns={'stock splits': 'stock_splits'}, inplace=True)

data.to_csv('test.csv', index=False)
print(data.head())

dt.create_table()
dt.insert_data(data)
print(dt.select_data("TSLA").head())