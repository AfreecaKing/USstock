import tkinter as tk
import download_data as download
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


class StockApp:
    def __init__(self, root):
        self.root = root
        self.root.title('Stock App')
        self.root.geometry("800x500")

        # 主頁 Frame
        self.main_frame = tk.Frame(root)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        '''按鈕設置'''
        # 新增股票
        button_insert_stock = tk.Button(self.main_frame, text="新增股票", command=self.show_insert_page)
        button_insert_stock.pack(side=tk.LEFT)
        # 瀏覽股票
        button_get_name = tk.Button(self.main_frame, text="瀏覽股票", command=self.show_all_ticker_page)
        button_get_name.pack(side=tk.LEFT)

    # -----------------------------
    # 顯示新增股票頁面
    # -----------------------------
    def show_insert_page(self):
        # 隱藏主頁
        self.main_frame.pack_forget()

        # 新增股票 Frame
        self.insert_frame = tk.Frame(self.root)
        self.insert_frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(self.insert_frame, text="輸入股票代號:").pack(pady=10)
        self.entry = tk.Entry(self.insert_frame)
        self.entry.pack(pady=5)

        tk.Button(self.insert_frame, text="新增", command=self.insert_stock).pack(pady=5)
        tk.Button(self.insert_frame, text="返回", command=self.back_to_main).pack(pady=5)

        # 顯示操作結果
        self.label_result = tk.Label(self.insert_frame, text="")
        self.label_result.pack(pady=10)

    # -----------------------------
    # 執行新增股票
    # -----------------------------
    def insert_stock(self):
        ticker = self.entry.get().upper().strip()  # 取得輸入
        if ticker:
            if download.insert_ticker(ticker):  # 你原本的新增股票函式
                self.label_result.config(text=f"{ticker} 已新增完成！", fg="green")
            else:
                self.label_result.config(text=f"新增失敗", fg="red")
        else:
            self.label_result.config(text="請輸入股票代號", fg="red")

    # -----------------------------
    # 返回主頁
    # -----------------------------
    def back_to_main(self):
        self.insert_frame.pack_forget()
        self.main_frame.pack(fill=tk.BOTH, expand=True)

    # -----------------------------
    # 顯示全部股票頁面
    # -----------------------------
    def show_all_ticker_page(self):
        self.main_frame.pack_forget()
        # 新增 Frame
        self.name_frame = tk.Frame(self.root)
        self.name_frame.pack(fill=tk.BOTH, expand=True)


# -----------------------------
# 執行程式
# -----------------------------
if __name__ == "__main__":
    root = tk.Tk()
    app = StockApp(root)
    root.mainloop()
