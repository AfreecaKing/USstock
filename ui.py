import tkinter as tk
import download_data as download
import database as db
from tkinter import messagebox
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


class StockApp:
    def __init__(self, root):
        self.root = root
        self.root.title('Stock App')
        self.root.geometry("800x500")

        # ====== 主頁 Frame ======
        self.main_frame = tk.Frame(root)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        center_frame = tk.Frame(self.main_frame)
        center_frame.pack(expand=True)

        tk.Button(
            center_frame,
            text="新增股票",
            width=15,
            height=2,
            command=self.show_insert_page
        ).pack(pady=10)

        tk.Button(
            center_frame,
            text="瀏覽股票",
            width=15,
            height=2,
            command=self.show_all_ticker_page
        ).pack(pady=10)

        tk.Button(
            center_frame,
            text="更新股票資料",
            width=15,
            height=2,
            command=download.update_all
        ).pack(pady=10)

        # 目前顯示的頁面
        self.current_frame = self.main_frame
        # 🔁 頁面歷史（stack）
        self.frame_stack = []

    # =============================
    # 通用 Frame 切換
    # =============================
    def show_frame(self, frame):
        if self.current_frame:
            # 🔁 把目前頁面推進 stack
            self.frame_stack.append(self.current_frame)
            self.current_frame.pack_forget()

        frame.pack(fill=tk.BOTH, expand=True)
        self.current_frame = frame

    # =============================
    # 通用返回主頁
    # =============================
    def back_to_main(self):
        self.show_frame(self.main_frame)

    # =============================
    # 返回上一頁
    # =============================
    def back(self):
        if not self.frame_stack:
            return  # 已經是第一頁

        # 隱藏目前頁面
        self.current_frame.pack_forget()

        # 回到上一頁
        self.current_frame = self.frame_stack.pop()
        self.current_frame.pack(fill=tk.BOTH, expand=True)

    # =============================
    # 新增股票頁面
    # =============================
    def show_insert_page(self):
        self.insert_frame = tk.Frame(self.root)

        tk.Label(self.insert_frame, text="輸入股票代號").pack(pady=10)

        self.entry = tk.Entry(self.insert_frame)
        self.entry.pack(pady=5)

        tk.Button(
            self.insert_frame,
            text="新增",
            command=self.insert_stock
        ).pack(pady=5)

        tk.Button(
            self.insert_frame,
            text="返回",
            command=self.back
        ).pack(pady=5)

        self.label_result = tk.Label(self.insert_frame, text="")
        self.label_result.pack(pady=10)

        self.show_frame(self.insert_frame)

    # =============================
    # 新增股票動作
    # =============================
    def insert_stock(self):
        ticker = self.entry.get().upper().strip()
        if not ticker:
            self.label_result.config(text="請輸入股票代號", fg="red")
            return

        if download.insert_ticker(ticker):
            self.label_result.config(
                text=f"{ticker} 已新增完成！",
                fg="green"
            )
        else:
            self.label_result.config(
                text="新增失敗",
                fg="red"
            )

    # =============================
    # 股票清單頁面
    # =============================

    def show_all_ticker_page(self):
        self.name_frame = tk.Frame(self.root)

        tk.Label(
            self.name_frame,
            text="股票清單",
            font=("Arial", 16)
        ).pack(pady=10)

        tickers = db.get_all_tickers()

        list_frame = tk.Frame(self.name_frame)
        list_frame.pack(pady=10)

        for ticker in tickers:
            ticker_name = ticker[0] if isinstance(ticker, (tuple, list)) else ticker

            row = tk.Frame(list_frame)
            row.pack(fill=tk.X, pady=2)

            tk.Label(
                row,
                text=ticker_name,
                width=15,
                anchor="w"
            ).pack(side=tk.LEFT, padx=5)

            tk.Button(
                row,
                text="瀏覽",
                command=lambda t=ticker_name: self.view_ticker(t)
            ).pack(side=tk.LEFT, padx=5)

            # 🔴 刪除按鈕
            tk.Button(
                row,
                text="刪除",
                fg="red",
                command=lambda t=ticker_name: self.delete_ticker_ui(t)
            ).pack(side=tk.LEFT, padx=5)

        tk.Button(
            self.name_frame,
            text="返回",
            command=self.back
        ).pack(pady=10)

        self.show_frame(self.name_frame)

    # -------------------------------
    # 瀏覽股票 & 畫圖功能
    # -------------------------------
    def view_ticker(self, ticker):
        self.ticker = ticker
        self.df = db.select_data(ticker)

        # 初始化時間控制
        self.time_offset = 0  # 時間平移偏移量
        self.current_period = "6M"  # 預設時間區間
        self.chart_type = "price"  # 預設圖表

        self.chart_frame = tk.Frame(self.root)

        # ===== 標題 =====
        tk.Label(
            self.chart_frame,
            text=f"{ticker} chart",
            font=("Arial", 16)
        ).pack(pady=5)

        # ===== 圖表類型控制 =====
        control_frame = tk.Frame(self.chart_frame)
        control_frame.pack(pady=5)

        tk.Button(control_frame, text="股價走勢",
                  command=lambda: self.set_chart_type("price")).pack(side=tk.LEFT, padx=5)
        tk.Button(control_frame, text="本益比",
                  command=lambda: self.set_chart_type("pe")).pack(side=tk.LEFT, padx=5)
        tk.Button(control_frame, text="營收",
                  command=lambda: self.set_chart_type("revenue")).pack(side=tk.LEFT, padx=5)

        # ===== 時間區間控制 =====
        period_frame = tk.Frame(self.chart_frame)
        period_frame.pack(pady=5)

        tk.Button(period_frame, text="1M",
                  command=lambda: self.set_period("1M")).pack(side=tk.LEFT, padx=3)
        tk.Button(period_frame, text="6M",
                  command=lambda: self.set_period("6M")).pack(side=tk.LEFT, padx=3)
        tk.Button(period_frame, text="1Y",
                  command=lambda: self.set_period("1Y")).pack(side=tk.LEFT, padx=3)
        tk.Button(period_frame, text="ALL",
                  command=lambda: self.set_period("ALL")).pack(side=tk.LEFT, padx=3)

        # ===== 上一段 / 下一段平移 =====
        nav_frame = tk.Frame(self.chart_frame)
        nav_frame.pack(pady=5)

        tk.Button(nav_frame, text="◀ 上一段", command=self.prev_period).pack(side=tk.LEFT, padx=5)
        tk.Button(nav_frame, text="下一段 ▶", command=self.next_period).pack(side=tk.LEFT, padx=5)

        # ===== 圖表顯示區 =====
        self.figure = plt.Figure(figsize=(7, 4))
        self.ax = self.figure.add_subplot(111)

        self.canvas = FigureCanvasTkAgg(self.figure, self.chart_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # 返回上一頁
        tk.Button(self.chart_frame, text="返回", command=self.back).pack(pady=5)

        # 顯示頁面
        self.show_frame(self.chart_frame)

        # 預設畫圖
        self.draw_chart(self.chart_type, self.current_period)

    # -------------------------------
    # 設定圖表類型
    # -------------------------------
    def set_chart_type(self, chart_type):
        self.chart_type = chart_type
        self.time_offset = 0  # 每次切換圖表類型回到最新
        self.draw_chart(chart_type, self.current_period)

    # -------------------------------
    # 設定時間區間
    # -------------------------------
    def set_period(self, period):
        self.current_period = period
        self.time_offset = 0  # 每次切換時間區間回到最新
        self.draw_chart(self.chart_type, period)

    # -------------------------------
    # 平移上一段 / 下一段
    # -------------------------------
    def prev_period(self):
        self.time_offset += 1
        self.draw_chart(self.chart_type, self.current_period)

    def next_period(self):
        if self.time_offset > 0:
            self.time_offset -= 1
        self.draw_chart(self.chart_type, self.current_period)

    # -------------------------------
    # 畫圖核心
    # -------------------------------
    def draw_chart(self, chart_type="price", period="6M"):
        self.ax.clear()
        df = self.df.copy()

        # ===== 時間區間過濾 =====
        if period != "ALL":
            end_date = df["date"].max() - pd.DateOffset(months=self.time_offset * (
                1 if period == "1M" else 6 if period == "6M" else 12 if period == "1Y" else 0))
            if period == "1M":
                start_date = end_date - pd.DateOffset(months=1)
            elif period == "6M":
                start_date = end_date - pd.DateOffset(months=6)
            elif period == "1Y":
                start_date = end_date - pd.DateOffset(years=1)
            df = df[(df["date"] > start_date) & (df["date"] <= end_date)]

        # ===== 畫圖 =====
        if chart_type == "price":
            self.ax.plot(df["date"], df["close"])
            self.ax.set_title(f"{self.ticker} price ({period})")
            self.ax.set_ylabel("Price")
        elif chart_type == "pe":
            self.ax.text(0.5, 0.5, "本益比尚未實作", ha="center", va="center", transform=self.ax.transAxes)
        elif chart_type == "revenue":
            self.ax.text(0.5, 0.5, "營收尚未實作", ha="center", va="center", transform=self.ax.transAxes)

        self.ax.set_xlabel("Date")
        self.figure.autofmt_xdate()
        self.canvas.draw()

    # =============================
    # 刪除股票
    # =============================
    def delete_ticker_ui(self, ticker):
        # 確認視窗
        if not messagebox.askyesno(
                "確認刪除",
                f"確定要刪除 {ticker} 的所有資料嗎？"
        ):
            return

        # 執行刪除
        if db.delete_ticker(ticker):
            messagebox.showinfo("成功", f"{ticker} 已刪除")
            # 重新整理頁面
            self.show_all_ticker_page()
        else:
            messagebox.showerror("失敗", f"{ticker} 刪除失敗")


# =============================
# 程式進入點
# =============================
if __name__ == "__main__":
    root = tk.Tk()
    app = StockApp(root)
    root.mainloop()
