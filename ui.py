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

        # 頁面堆疊管理
        self.frame_stack = []
        self.current_frame = None

        # 資料初始化
        db.create_table()

        # 顯示主頁
        self.show_main_page()

    # =============================
    # 通用 Frame 切換（自動管理堆疊）
    # =============================
    def show_frame(self, new_frame):
        """切換到新頁面，自動將當前頁面加入堆疊"""
        if self.current_frame:
            self.frame_stack.append(self.current_frame)
            self.current_frame.pack_forget()

        new_frame.pack(fill=tk.BOTH, expand=True)
        self.current_frame = new_frame

    def replace_frame(self, new_frame):
        """替換當前頁面（不加入堆疊，用於重新整理頁面）"""
        if self.current_frame:
            self.current_frame.pack_forget()

        new_frame.pack(fill=tk.BOTH, expand=True)
        self.current_frame = new_frame

    # =============================
    # 返回上一頁（統一處理）
    # =============================
    def back(self):
        """返回上一頁，如果沒有上一頁則回到主頁"""
        if not self.frame_stack:
            # 已經在最頂層，回到主頁
            self.show_main_page()
            return

        # 隱藏目前頁面並銷毀
        if self.current_frame:
            self.current_frame.pack_forget()
            self.current_frame.destroy()

        # 回到上一頁
        self.current_frame = self.frame_stack.pop()
        self.current_frame.pack(fill=tk.BOTH, expand=True)

    # =============================
    # 主頁面
    # =============================
    def show_main_page(self):
        """顯示主頁（清空堆疊）"""
        # 清空堆疊
        for frame in self.frame_stack:
            frame.destroy()
        self.frame_stack.clear()

        if self.current_frame:
            self.current_frame.pack_forget()
            self.current_frame.destroy()

        # 建立主頁
        main_frame = tk.Frame(self.root)
        center_frame = tk.Frame(main_frame)
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
            command=download.update_all_ticker
        ).pack(pady=10)

        main_frame.pack(fill=tk.BOTH, expand=True)
        self.current_frame = main_frame

    # =============================
    # 新增股票頁面
    # =============================
    def show_insert_page(self):
        insert_frame = tk.Frame(self.root)

        tk.Label(insert_frame, text="輸入股票代號").pack(pady=10)

        entry = tk.Entry(insert_frame)
        entry.pack(pady=5)

        label_result = tk.Label(insert_frame, text="")
        label_result.pack(pady=10)

        def insert_stock():
            ticker = entry.get().upper().strip()
            if not ticker:
                label_result.config(text="請輸入股票代號", fg="red")
                return

            if download.insert_ticker(ticker) and download.fetch_and_store_fundamentals(ticker):
                label_result.config(text=f"{ticker} 已新增完成！", fg="green")
            else:
                label_result.config(text="新增失敗", fg="red")

        tk.Button(insert_frame, text="新增", command=insert_stock).pack(pady=5)
        tk.Button(insert_frame, text="返回", command=self.back).pack(pady=5)

        self.show_frame(insert_frame)

    # =============================
    # 股票清單頁面
    # =============================
    def show_all_ticker_page(self):
        name_frame = tk.Frame(self.root)

        tk.Label(name_frame, text="Stock List", font=("Arial", 16)).pack(pady=10)

        tickers = db.get_all_tickers()

        # 建立可滾動的 Frame
        container = tk.Frame(name_frame)
        container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        canvas = tk.Canvas(container)
        scrollbar = tk.Scrollbar(container, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # 股票列表
        for ticker in tickers:
            ticker_name = ticker[0] if isinstance(ticker, (tuple, list)) else ticker

            row = tk.Frame(scrollable_frame, relief=tk.RIDGE, borderwidth=1)
            row.pack(fill=tk.X, pady=3, padx=5)

            tk.Label(
                row,
                text=ticker_name,
                width=15,
                anchor="w",
                font=("Arial", 11, "bold")
            ).pack(side=tk.LEFT, padx=10, pady=5)

            tk.Button(
                row,
                text="基本面",
                width=10,
                command=lambda t=ticker_name: self.view_fundamentals(t)
            ).pack(side=tk.LEFT, padx=5)

            tk.Button(
                row,
                text="技術面",
                width=12,
                command=lambda t=ticker_name: self.view_ticker(t)
            ).pack(side=tk.LEFT, padx=5)

            tk.Button(
                row,
                text="刪除",
                width=8,
                fg="white",
                bg="red",
                command=lambda t=ticker_name: self.delete_ticker_ui(t)
            ).pack(side=tk.LEFT, padx=5)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        tk.Button(name_frame, text="返回", width=15, command=self.back).pack(pady=10)

        self.show_frame(name_frame)

    # =============================
    # 技術面分析頁面
    # =============================
    def view_ticker(self, ticker):
        self.ticker = ticker
        self.df = db.select_price(ticker)

        # 初始化時間控制
        self.time_offset = 0
        self.current_period = "6M"
        self.chart_type = "price"

        chart_frame = tk.Frame(self.root)

        tk.Label(chart_frame, text=f"{ticker} chart", font=("Arial", 16)).pack(pady=5)

        # 圖表類型控制
        control_frame = tk.Frame(chart_frame)
        control_frame.pack(pady=5)

        tk.Button(control_frame, text="股價走勢",
                  command=lambda: self.set_chart_type("price")).pack(side=tk.LEFT, padx=5)
        tk.Button(control_frame, text="漲跌幅",
                  command=lambda: self.set_chart_type("change")).pack(side=tk.LEFT, padx=5)

        # 時間區間控制
        period_frame = tk.Frame(chart_frame)
        period_frame.pack(pady=5)

        tk.Button(period_frame, text="1M",
                  command=lambda: self.set_period("1M")).pack(side=tk.LEFT, padx=3)
        tk.Button(period_frame, text="6M",
                  command=lambda: self.set_period("6M")).pack(side=tk.LEFT, padx=3)
        tk.Button(period_frame, text="1Y",
                  command=lambda: self.set_period("1Y")).pack(side=tk.LEFT, padx=3)
        tk.Button(period_frame, text="ALL",
                  command=lambda: self.set_period("ALL")).pack(side=tk.LEFT, padx=3)

        # 上一段 / 下一段平移
        nav_frame = tk.Frame(chart_frame)
        nav_frame.pack(pady=5)

        tk.Button(nav_frame, text="◀ 上一段", command=self.prev_period).pack(side=tk.LEFT, padx=5)
        tk.Button(nav_frame, text="下一段 ▶", command=self.next_period).pack(side=tk.LEFT, padx=5)

        # 圖表顯示區
        self.figure = plt.Figure(figsize=(7, 4))
        self.ax = self.figure.add_subplot(111)

        self.canvas = FigureCanvasTkAgg(self.figure, chart_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        tk.Button(chart_frame, text="返回", command=self.back).pack(pady=5)

        self.show_frame(chart_frame)
        self.draw_chart(self.chart_type, self.current_period)

    def set_chart_type(self, chart_type):
        self.chart_type = chart_type
        self.time_offset = 0
        self.draw_chart(chart_type, self.current_period)

    def set_period(self, period):
        self.current_period = period
        self.time_offset = 0
        self.draw_chart(self.chart_type, period)

    def prev_period(self):
        self.time_offset += 1
        self.draw_chart(self.chart_type, self.current_period)

    def next_period(self):
        if self.time_offset > 0:
            self.time_offset -= 1
        self.draw_chart(self.chart_type, self.current_period)

    def draw_chart(self, chart_type="price", period="6M"):
        self.ax.clear()
        df = self.df.copy()

        if len(df) >= 20:
            df['MA20'] = df['close'].rolling(20).mean()
        if len(df) >= 60:
            df['MA60'] = df['close'].rolling(60).mean()

        if period != "ALL":
            end_date = df["date"].max()
            if period == "1M":
                end_date -= pd.DateOffset(months=self.time_offset)
                start_date = end_date - pd.DateOffset(months=1)
            elif period == "6M":
                end_date -= pd.DateOffset(months=6 * self.time_offset)
                start_date = end_date - pd.DateOffset(months=6)
            elif period == "1Y":
                end_date -= pd.DateOffset(years=self.time_offset)
                start_date = end_date - pd.DateOffset(years=1)
            df = df[(df["date"] > start_date) & (df["date"] <= end_date)]

        if chart_type == "price":
            self.ax.plot(df["date"], df["close"], label="Close", color='blue')
            if 'MA20' in df:
                self.ax.plot(df["date"], df['MA20'], label="MA20", color='orange')
            if 'MA60' in df:
                self.ax.plot(df["date"], df['MA60'], label="MA60", color='green')

            self.ax.set_title(f"{self.ticker} Price Chart ({period})")
            self.ax.set_ylabel("Price")
            self.ax.legend()

        elif chart_type == "change":
            df['daily_change'] = df['close'].pct_change() * 100
            colors = ['red' if x > 0 else 'green' if x < 0 else 'gray'
                      for x in df['daily_change']]

            self.ax.bar(df["date"], df['daily_change'], color=colors, alpha=0.7, width=0.8)
            self.ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5)

            self.ax.set_title(f"{self.ticker} Daily Price Change ({period})")
            self.ax.set_ylabel("Change (%)")

            avg_change = df['daily_change'].mean()
            self.ax.text(0.02, 0.98, f"Avg: {avg_change:.2f}%",
                         transform=self.ax.transAxes,
                         verticalalignment='top',
                         bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

        self.ax.set_xlabel("Date")
        self.figure.autofmt_xdate()
        self.canvas.draw()

    # =============================
    # 基本面分析
    # =============================
    def view_fundamentals(self, ticker):
        self.ticker = ticker
        df = db.select_fundamentals(ticker)

        if df.empty:
            messagebox.showinfo("無資料", f"{ticker} 尚無基本面資料")
            return

        fund_frame = tk.Frame(self.root)
        tk.Label(fund_frame, text=f"{ticker} Fundamentals", font=("Arial", 16)).pack(pady=5)

        # 圖表切換按鈕
        control_frame = tk.Frame(fund_frame)
        control_frame.pack(pady=5)

        tk.Button(control_frame, text="Revenue",
                  command=lambda: self.draw_fundamental_chart(df, "revenue", "Revenue (Billion USD)", scale=1e-9)).pack(
            side=tk.LEFT, padx=3)
        tk.Button(control_frame, text="EPS",
                  command=lambda: self.draw_fundamental_chart(df, "eps", "EPS (USD)")).pack(side=tk.LEFT, padx=3)
        tk.Button(control_frame, text="Gross Margin",
                  command=lambda: self.draw_fundamental_chart(df, "gross_margin", "Gross Margin (%)",
                                                              is_percent=True)).pack(side=tk.LEFT, padx=3)
        tk.Button(control_frame, text="Operating Margin",
                  command=lambda: self.draw_fundamental_chart(df, "operating_margin", "Operating Margin (%)",
                                                              is_percent=True)).pack(side=tk.LEFT, padx=3)
        tk.Button(control_frame, text="Net Margin",
                  command=lambda: self.draw_fundamental_chart(df, "net_margin", "Net Margin (%)",
                                                              is_percent=True)).pack(side=tk.LEFT, padx=3)

        # 圖表
        self.figure = plt.Figure(figsize=(7, 4))
        self.ax = self.figure.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.figure, fund_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        tk.Button(fund_frame, text="返回", command=self.back).pack(pady=5)

        self.show_frame(fund_frame)
        self.draw_fundamental_chart(df, "revenue", "Revenue (Billion USD)", scale=1e-9)

    def draw_fundamental_chart(self, df, col, ylabel=None, scale=1, is_percent=False):
        self.ax.clear()

        df = df.sort_values("year").copy()
        x = df["year"]
        y = df[col] * scale

        bars = self.ax.bar(x, y, color="skyblue" if not is_percent else "lightgreen")

        self.ax.set_xlabel("Year")
        self.ax.set_ylabel(ylabel if ylabel else col)
        self.ax.set_title(f"{self.ticker} {col}")
        self.ax.set_xticks(x)
        self.ax.set_xticklabels(x, rotation=45)

        if col.lower() == "revenue":
            df["yoy"] = df["revenue"].pct_change() * 100
            for bar, yoy in zip(bars, df["yoy"]):
                label = "—" if pd.isna(yoy) else f"{yoy:+.1f}%"
                y_pos = bar.get_height()
                va = "bottom" if y_pos >= 0 else "top"
                self.ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    y_pos,
                    label,
                    ha="center",
                    va=va,
                    fontsize=9,
                    color="red" if pd.notna(yoy) and yoy < 0 else "black"
                )
        else:
            for bar, val in zip(bars, y):
                label = "—" if pd.isna(val) else (f"{val:.2f}%" if is_percent else f"{val:.3f}")
                y_pos = bar.get_height()
                va = "bottom" if y_pos >= 0 else "top"
                self.ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    y_pos,
                    label,
                    ha="center",
                    va=va,
                    fontsize=9,
                    color="black"
                )

        self.figure.tight_layout()
        self.canvas.draw()

    # =============================
    # 刪除股票
    # =============================
    def delete_ticker_ui(self, ticker):
        if not messagebox.askyesno("確認刪除", f"確定要刪除 {ticker} 的所有資料嗎？"):
            return

        if db.delete_ticker(ticker):
            messagebox.showinfo("成功", f"{ticker} 已刪除")
            # 刪除成功後，重新載入股票列表頁面
            # 先清除當前頁面
            if self.current_frame:
                self.current_frame.pack_forget()
                self.current_frame.destroy()

            # 重新顯示股票列表（不改變堆疊）
            self.show_all_ticker_page_refresh()
        else:
            messagebox.showerror("失敗", f"{ticker} 刪除失敗")

    def show_all_ticker_page_refresh(self):
        """重新整理股票列表（不加入堆疊）"""
        name_frame = tk.Frame(self.root)

        tk.Label(name_frame, text="Stock List", font=("Arial", 16)).pack(pady=10)

        tickers = db.get_all_tickers()

        # 建立可滾動的 Frame
        container = tk.Frame(name_frame)
        container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        canvas = tk.Canvas(container)
        scrollbar = tk.Scrollbar(container, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # 股票列表
        for ticker in tickers:
            ticker_name = ticker[0] if isinstance(ticker, (tuple, list)) else ticker

            row = tk.Frame(scrollable_frame, relief=tk.RIDGE, borderwidth=1)
            row.pack(fill=tk.X, pady=3, padx=5)

            tk.Label(
                row,
                text=ticker_name,
                width=15,
                anchor="w",
                font=("Arial", 11, "bold")
            ).pack(side=tk.LEFT, padx=10, pady=5)

            tk.Button(
                row,
                text="基本面",
                width=10,
                command=lambda t=ticker_name: self.view_fundamentals(t)
            ).pack(side=tk.LEFT, padx=5)

            tk.Button(
                row,
                text="技術面",
                width=12,
                command=lambda t=ticker_name: self.view_ticker(t)
            ).pack(side=tk.LEFT, padx=5)

            tk.Button(
                row,
                text="刪除",
                width=8,
                fg="white",
                bg="red",
                command=lambda t=ticker_name: self.delete_ticker_ui(t)
            ).pack(side=tk.LEFT, padx=5)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        tk.Button(name_frame, text="返回", width=15, command=self.back).pack(pady=10)

        # 直接替換當前頁面（不加入堆疊）
        name_frame.pack(fill=tk.BOTH, expand=True)
        self.current_frame = name_frame


if __name__ == "__main__":
    root = tk.Tk()
    app = StockApp(root)
    root.mainloop()