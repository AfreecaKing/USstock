import tkinter as tk
import download_data as download
import database as db
from tkinter import messagebox, simpledialog
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


class StockApp:
    def __init__(self, root):
        self.root = root
        self.root.title('Stock App')
        self.root.geometry("800x500")

        self.frame_stack = []
        self.current_frame = None

        db.create_table()
        self.show_main_page()

    def show_frame(self, new_frame):
        if self.current_frame:
            self.frame_stack.append(self.current_frame)
            self.current_frame.pack_forget()
        new_frame.pack(fill=tk.BOTH, expand=True)
        self.current_frame = new_frame

    def replace_frame(self, new_frame):
        if self.current_frame:
            self.current_frame.pack_forget()
        new_frame.pack(fill=tk.BOTH, expand=True)
        self.current_frame = new_frame

    def back(self):
        if not self.frame_stack:
            self.show_main_page()
            return
        if self.current_frame:
            self.current_frame.pack_forget()
            self.current_frame.destroy()
        self.current_frame = self.frame_stack.pop()
        self.current_frame.pack(fill=tk.BOTH, expand=True)

    # ===== 主頁面 =====
    def show_main_page(self):
        for frame in self.frame_stack:
            frame.destroy()
        self.frame_stack.clear()

        if self.current_frame:
            self.current_frame.pack_forget()
            self.current_frame.destroy()

        main_frame = tk.Frame(self.root)
        center_frame = tk.Frame(main_frame)
        center_frame.pack(expand=True)

        tk.Button(center_frame, text="新增股票", width=15, height=2,
                  command=self.show_insert_page).pack(pady=10)
        tk.Button(center_frame, text="瀏覽股票", width=15, height=2,
                  command=self.show_category_selection_page).pack(pady=10)
        tk.Button(center_frame, text="管理分類", width=15, height=2,
                  command=self.show_category_management_page).pack(pady=10)
        tk.Button(center_frame, text="更新股票資料", width=15, height=2,
                  command=download.update_all_ticker).pack(pady=10)

        main_frame.pack(fill=tk.BOTH, expand=True)
        self.current_frame = main_frame

    # ===== 新增股票頁面（加入分類選擇）=====
    def show_insert_page(self):
        insert_frame = tk.Frame(self.root)

        tk.Label(insert_frame, text="輸入股票代號").pack(pady=10)
        entry = tk.Entry(insert_frame)
        entry.pack(pady=5)

        tk.Label(insert_frame, text="選擇分類（可多選）").pack(pady=10)

        # 分類選擇區（使用可滾動的 Checkbutton）
        categories = db.get_all_categories()
        category_vars = {}

        # 建立可滾動容器
        cat_container = tk.Frame(insert_frame)
        cat_container.pack(pady=5, fill=tk.BOTH, expand=True)

        cat_canvas = tk.Canvas(cat_container, height=150)
        cat_scrollbar = tk.Scrollbar(cat_container, orient="vertical", command=cat_canvas.yview)
        cat_frame = tk.Frame(cat_canvas)

        cat_frame.bind("<Configure>", lambda e: cat_canvas.configure(scrollregion=cat_canvas.bbox("all")))
        cat_canvas.create_window((0, 0), window=cat_frame, anchor="nw")
        cat_canvas.configure(yscrollcommand=cat_scrollbar.set)

        for cat_id, cat_name in categories:
            var = tk.BooleanVar()
            category_vars[cat_id] = var
            tk.Checkbutton(cat_frame, text=cat_name, variable=var).pack(anchor=tk.W, padx=20)

        cat_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        cat_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        label_result = tk.Label(insert_frame, text="")
        label_result.pack(pady=10)

        def insert_stock():
            ticker = entry.get().upper().strip()
            if not ticker:
                label_result.config(text="請輸入股票代號", fg="red")
                return

            # 新增股票資料
            if download.insert_ticker(ticker) and download.fetch_and_store_fundamentals(ticker):
                # 指定分類
                for cat_id, var in category_vars.items():
                    if var.get():
                        db.assign_ticker_to_category(ticker, cat_id)

                label_result.config(text=f"{ticker} 已新增完成！", fg="green")
            else:
                label_result.config(text="新增失敗", fg="red")

        tk.Button(insert_frame, text="新增", command=insert_stock).pack(pady=5)
        tk.Button(insert_frame, text="返回", command=self.back).pack(pady=5)

        self.show_frame(insert_frame)

    # ===== 分類選擇頁面 =====
    def show_category_selection_page(self):
        cat_sel_frame = tk.Frame(self.root)

        tk.Label(cat_sel_frame, text="選擇分類", font=("Arial", 16)).pack(pady=10)

        categories = db.get_all_categories()

        # 建立可滾動的分類按鈕區域
        container = tk.Frame(cat_sel_frame)
        container.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        canvas = tk.Canvas(container)
        scrollbar = tk.Scrollbar(container, orient="vertical", command=canvas.yview)
        btn_frame = tk.Frame(canvas)

        btn_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=btn_frame, anchor="n")
        canvas.configure(yscrollcommand=scrollbar.set)

        # 全部股票按鈕
        tk.Button(btn_frame, text="📊 全部股票", width=30, height=2,
                  command=lambda: self.show_all_ticker_page(None, "全部股票")).pack(pady=5)

        # 各分類按鈕
        for cat_id, cat_name in categories:
            tk.Button(btn_frame, text=f"📁 {cat_name}", width=30, height=2,
                      command=lambda cid=cat_id, cn=cat_name: self.show_all_ticker_page(cid, cn)).pack(pady=5)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        tk.Button(cat_sel_frame, text="返回", width=15, command=self.back).pack(pady=10)

        self.show_frame(cat_sel_frame)

    # ===== 股票清單頁面（支援分類篩選）=====
    def show_all_ticker_page(self, category_id=None, category_name="全部股票"):
        name_frame = tk.Frame(self.root)

        tk.Label(name_frame, text=f"Stock List - {category_name}", font=("Arial", 16)).pack(pady=10)

        # 取得股票列表
        if category_id is None:
            tickers = db.get_all_tickers()
        else:
            tickers = [t[0] for t in db.get_tickers_by_category(category_id)]

        # 建立可滾動的 Frame
        container = tk.Frame(name_frame)
        container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        canvas = tk.Canvas(container)
        scrollbar = tk.Scrollbar(container, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas)

        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # 股票列表
        for ticker in tickers:
            ticker_name = ticker[0] if isinstance(ticker, (tuple, list)) else ticker

            row = tk.Frame(scrollable_frame, relief=tk.RIDGE, borderwidth=1)
            row.pack(fill=tk.X, pady=3, padx=5)

            # 顯示股票分類標籤
            ticker_cats = db.get_ticker_categories(ticker_name)
            cat_labels = ", ".join([c[1] for c in ticker_cats]) if ticker_cats else "未分類"

            info_frame = tk.Frame(row)
            info_frame.pack(side=tk.LEFT, padx=10, pady=5)

            tk.Label(info_frame, text=ticker_name, font=("Arial", 11, "bold")).pack(anchor=tk.W)
            tk.Label(info_frame, text=f"[{cat_labels}]", font=("Arial", 8), fg="gray").pack(anchor=tk.W)

            tk.Button(row, text="基本面", width=10,
                      command=lambda t=ticker_name: self.view_fundamentals(t)).pack(side=tk.LEFT, padx=5)
            tk.Button(row, text="技術面", width=12,
                      command=lambda t=ticker_name: self.view_ticker(t)).pack(side=tk.LEFT, padx=5)
            tk.Button(row, text="編輯分類", width=10,
                      command=lambda t=ticker_name: self.edit_ticker_categories(t)).pack(side=tk.LEFT, padx=5)
            tk.Button(row, text="刪除", width=8, fg="white", bg="red",
                      command=lambda t=ticker_name: self.delete_ticker_ui(t, category_id, category_name)).pack(
                side=tk.LEFT, padx=5)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        tk.Button(name_frame, text="返回", width=15, command=self.back).pack(pady=10)

        self.show_frame(name_frame)

    # ===== 編輯股票分類 =====
    def edit_ticker_categories(self, ticker):
        edit_frame = tk.Frame(self.root)

        tk.Label(edit_frame, text=f"編輯 {ticker} 的分類", font=("Arial", 14)).pack(pady=10)

        categories = db.get_all_categories()
        current_cats = [c[0] for c in db.get_ticker_categories(ticker)]

        category_vars = {}

        # 建立可滾動容器
        cat_container = tk.Frame(edit_frame)
        cat_container.pack(pady=10, fill=tk.BOTH, expand=True, padx=20)

        cat_canvas = tk.Canvas(cat_container, height=200)
        cat_scrollbar = tk.Scrollbar(cat_container, orient="vertical", command=cat_canvas.yview)
        cat_frame = tk.Frame(cat_canvas)

        cat_frame.bind("<Configure>", lambda e: cat_canvas.configure(scrollregion=cat_canvas.bbox("all")))
        cat_canvas.create_window((0, 0), window=cat_frame, anchor="nw")
        cat_canvas.configure(yscrollcommand=cat_scrollbar.set)

        for cat_id, cat_name in categories:
            var = tk.BooleanVar(value=(cat_id in current_cats))
            category_vars[cat_id] = var
            tk.Checkbutton(cat_frame, text=cat_name, variable=var).pack(anchor=tk.W, padx=20)

        cat_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        cat_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        def save_categories():
            # 先移除所有分類
            for cat_id, _ in categories:
                db.remove_ticker_from_category(ticker, cat_id)

            # 重新指定選中的分類
            for cat_id, var in category_vars.items():
                if var.get():
                    db.assign_ticker_to_category(ticker, cat_id)

            messagebox.showinfo("成功", f"{ticker} 的分類已更新")
            self.back()

        tk.Button(edit_frame, text="儲存", width=15, command=save_categories).pack(pady=10)
        tk.Button(edit_frame, text="返回", width=15, command=self.back).pack(pady=5)

        self.show_frame(edit_frame)

    # ===== 分類管理頁面 =====
    def show_category_management_page(self):
        mgmt_frame = tk.Frame(self.root)

        tk.Label(mgmt_frame, text="分類管理", font=("Arial", 16)).pack(pady=10)

        # 新增分類
        add_frame = tk.Frame(mgmt_frame)
        add_frame.pack(pady=10)

        tk.Label(add_frame, text="新增分類：").pack(side=tk.LEFT, padx=5)
        new_cat_entry = tk.Entry(add_frame, width=20)
        new_cat_entry.pack(side=tk.LEFT, padx=5)

        def add_new_category():
            name = new_cat_entry.get().strip()
            if not name:
                messagebox.showwarning("警告", "請輸入分類名稱")
                return
            if db.add_category(name):
                messagebox.showinfo("成功", f"已新增分類：{name}")
                new_cat_entry.delete(0, tk.END)
                self.refresh_category_list(cat_list_frame)
            else:
                messagebox.showerror("失敗", "分類已存在或新增失敗")

        tk.Button(add_frame, text="新增", command=add_new_category).pack(side=tk.LEFT, padx=5)

        # 現有分類列表
        tk.Label(mgmt_frame, text="現有分類：", font=("Arial", 12)).pack(pady=10)

        cat_list_frame = tk.Frame(mgmt_frame)
        cat_list_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        self.refresh_category_list(cat_list_frame)

        tk.Button(mgmt_frame, text="返回", width=15, command=self.back).pack(pady=10)

        self.show_frame(mgmt_frame)

    def refresh_category_list(self, parent_frame):
        """刷新分類列表"""
        for widget in parent_frame.winfo_children():
            widget.destroy()

        categories = db.get_all_categories()

        for cat_id, cat_name in categories:
            row = tk.Frame(parent_frame, relief=tk.RIDGE, borderwidth=1)
            row.pack(fill=tk.X, pady=2)

            tk.Label(row, text=cat_name, width=20, anchor=tk.W).pack(side=tk.LEFT, padx=10)
            tk.Button(row, text="刪除", width=8, bg="lightcoral",
                      command=lambda cid=cat_id, cn=cat_name: self.delete_category_ui(cid, cn, parent_frame)).pack(
                side=tk.LEFT, padx=5)

    def delete_category_ui(self, category_id, category_name, parent_frame):
        """刪除分類"""
        if not messagebox.askyesno("確認", f"確定要刪除分類「{category_name}」嗎？\n（股票不會被刪除，只會解除分類關聯）"):
            return

        if db.delete_category(category_id):
            messagebox.showinfo("成功", f"已刪除分類：{category_name}")
            self.refresh_category_list(parent_frame)
        else:
            messagebox.showerror("失敗", "刪除分類失敗")

    # ===== 刪除股票（更新版）=====
    def delete_ticker_ui(self, ticker, category_id=None, category_name="全部股票"):
        if not messagebox.askyesno("確認刪除", f"確定要刪除 {ticker} 的所有資料嗎？"):
            return

        if db.delete_ticker(ticker):
            messagebox.showinfo("成功", f"{ticker} 已刪除")
            if self.current_frame:
                self.current_frame.pack_forget()
                self.current_frame.destroy()
            self.show_all_ticker_page(category_id, category_name)
        else:
            messagebox.showerror("失敗", f"{ticker} 刪除失敗")

    # ===== 以下是原有的技術面、基本面分析（保持不變）=====
    def view_ticker(self, ticker):
        self.ticker = ticker
        self.df = db.select_price(ticker)
        self.time_offset = 0
        self.current_period = "6M"
        self.chart_type = "price"

        chart_frame = tk.Frame(self.root)
        tk.Label(chart_frame, text=f"{ticker} chart", font=("Arial", 16)).pack(pady=5)

        control_frame = tk.Frame(chart_frame)
        control_frame.pack(pady=5)
        tk.Button(control_frame, text="股價走勢", command=lambda: self.set_chart_type("price")).pack(side=tk.LEFT,
                                                                                                     padx=5)
        tk.Button(control_frame, text="漲跌幅", command=lambda: self.set_chart_type("change")).pack(side=tk.LEFT,
                                                                                                    padx=5)

        period_frame = tk.Frame(chart_frame)
        period_frame.pack(pady=5)
        tk.Button(period_frame, text="1M", command=lambda: self.set_period("1M")).pack(side=tk.LEFT, padx=3)
        tk.Button(period_frame, text="6M", command=lambda: self.set_period("6M")).pack(side=tk.LEFT, padx=3)
        tk.Button(period_frame, text="1Y", command=lambda: self.set_period("1Y")).pack(side=tk.LEFT, padx=3)
        tk.Button(period_frame, text="ALL", command=lambda: self.set_period("ALL")).pack(side=tk.LEFT, padx=3)

        nav_frame = tk.Frame(chart_frame)
        nav_frame.pack(pady=5)
        tk.Button(nav_frame, text="◀ 上一段", command=self.prev_period).pack(side=tk.LEFT, padx=5)
        tk.Button(nav_frame, text="下一段 ▶", command=self.next_period).pack(side=tk.LEFT, padx=5)

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
            colors = ['red' if x > 0 else 'green' if x < 0 else 'gray' for x in df['daily_change']]
            self.ax.bar(df["date"], df['daily_change'], color=colors, alpha=0.7, width=0.8)
            self.ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
            self.ax.set_title(f"{self.ticker} Daily Price Change ({period})")
            self.ax.set_ylabel("Change (%)")
            avg_change = df['daily_change'].mean()
            self.ax.text(0.02, 0.98, f"Avg: {avg_change:.2f}%",
                         transform=self.ax.transAxes, verticalalignment='top',
                         bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

        self.ax.set_xlabel("Date")
        self.figure.autofmt_xdate()
        self.canvas.draw()

    def view_fundamentals(self, ticker):
        self.ticker = ticker
        df = db.select_fundamentals(ticker)

        if df.empty:
            messagebox.showinfo("無資料", f"{ticker} 尚無基本面資料")
            return

        fund_frame = tk.Frame(self.root)
        tk.Label(fund_frame, text=f"{ticker} Fundamentals", font=("Arial", 16)).pack(pady=5)

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
                self.ax.text(bar.get_x() + bar.get_width() / 2, y_pos, label,
                             ha="center", va=va, fontsize=9,
                             color="red" if pd.notna(yoy) and yoy < 0 else "black")
        else:
            for bar, val in zip(bars, y):
                label = "—" if pd.isna(val) else (f"{val:.2f}%" if is_percent else f"{val:.3f}")
                y_pos = bar.get_height()
                va = "bottom" if y_pos >= 0 else "top"
                self.ax.text(bar.get_x() + bar.get_width() / 2, y_pos, label,
                             ha="center", va=va, fontsize=9, color="black")

        self.figure.tight_layout()
        self.canvas.draw()


if __name__ == "__main__":
    root = tk.Tk()
    app = StockApp(root)
    root.mainloop()