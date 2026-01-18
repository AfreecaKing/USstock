import download_data as download
import database as db
'''
db.create_table()
download.insert_ticker("TSLA")
download.insert_ticker("AAPL")
download.update_all()
'''
print(db.select_data("AVGO"))
