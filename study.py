

import tkinter as tk
from tkinter import ttk
import math

# ==================== PALETTE WARNA ====================
BG_MAIN = "#F0F2F5"
BG_SIDEBAR = "#FFFFFF"
BG_CARD = "#FFFFFF"
PRIMARY = "#5B4FE9"       # ungu-biru (pengganti teal di referensi)
PRIMARY_DARK = "#4338CA"
ACCENT = "#FF8A3D"        # oranye untuk tombol CTA
TEXT_DARK = "#1F2937"
TEXT_GRAY = "#6B7280"
TEXT_LIGHT = "#9CA3AF"
PROGRESS_DONE = "#5B4FE9"
PROGRESS_INPROGRESS = "#F59E0B"
PROGRESS_NOTSTARTED = "#E5E7EB"
CARD_BORDER = "#E5E7EB"


class SidebarButton(tk.Frame):
    def __init__(self, master, text, icon, active=False, **kwargs):
        bg = PRIMARY if active else BG_SIDEBAR
        fg = "white" if active else TEXT_GRAY
        super().__init__(master, bg=bg, **kwargs)
        self.label = tk.Label(
            self, text=f"  {icon}   {text}", bg=bg, fg=fg,
            font=("Segoe UI", 10, "bold" if active else "normal"),
            anchor="w", padx=14, pady=10
        )
        self.label.pack(fill="x")


class DonutChart(tk.Canvas):
    """Donut chart sederhana untuk Learning Progress"""
    def __init__(self, master, completed, in_progress, not_started, **kwargs):
        super().__init__(master, width=170, height=170, bg=BG_CARD,
                          highlightthickness=0, **kwargs)
        total = completed + in_progress + not_started
        start = 90
        segments = [
            (completed, PROGRESS_DONE),
            (in_progress, PROGRESS_INPROGRESS),
            (not_started, PROGRESS_NOTSTARTED),
        ]
        for value, color in segments:
            extent = -360 * (value / total)
            self.create_arc(15, 15, 155, 155, start=start, extent=extent,
                             fill="", outline=color, width=16, style="arc")
            start += extent
        self.create_text(85, 85, text=f"{total}", font=("Segoe UI", 16, "bold"),
                          fill=TEXT_DARK)
        self.create_text(85, 105, text="Total Jam", font=("Segoe UI", 8),
                          fill=TEXT_GRAY)


class CourseCard(tk.Frame):
    def __init__(self, master, category, title, author, duration, progress, **kwargs):
        super().__init__(master, bg=BG_CARD, highlightbackground=CARD_BORDER,
                          highlightthickness=1, **kwargs)
        thumb = tk.Frame(self, bg="#D9DCE3", height=90)
        thumb.pack(fill="x", padx=10, pady=(10, 8))
        thumb.pack_propagate(False)

        tk.Label(self, text=category.upper(), bg=BG_CARD, fg=PRIMARY,
                  font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=12)
        tk.Label(self, text=title, bg=BG_CARD, fg=TEXT_DARK,
                  font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=12, pady=(2, 0))
        tk.Label(self, text=f"{author}  •  {duration}", bg=BG_CARD, fg=TEXT_GRAY,
                  font=("Segoe UI", 8)).pack(anchor="w", padx=12, pady=(2, 8))

        bar_bg = tk.Frame(self, bg="#E5E7EB", height=6)
        bar_bg.pack(fill="x", padx=12, pady=(0, 12))
        bar_fill = tk.Frame(bar_bg, bg=PRIMARY, height=6)
        bar_fill.place(relwidth=progress, relheight=1)


class TaskItem(tk.Frame):
    def __init__(self, master, icon, title, remaining, **kwargs):
        super().__init__(master, bg="#F5F6FA", **kwargs)
        left = tk.Frame(self, bg="#F5F6FA")
        left.pack(side="left", fill="x", expand=True, padx=10, pady=8)
        tk.Label(left, text=f"{icon}  {title}", bg="#F5F6FA", fg=TEXT_DARK,
                  font=("Segoe UI", 9, "bold"), anchor="w").pack(anchor="w")
        tk.Label(left, text=remaining, bg="#F5F6FA", fg=TEXT_GRAY,
                  font=("Segoe UI", 8), anchor="w").pack(anchor="w")


class Dashboard(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("MyCourse Dashboard")
        self.geometry("1150x680")
        self.configure(bg=BG_MAIN)
        self.resizable(True, True)

        self._build_sidebar()
        self._build_main_content()

    # ---------------- SIDEBAR ----------------
    def _build_sidebar(self):
        sidebar = tk.Frame(self, bg=BG_SIDEBAR, width=210)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        tk.Label(sidebar, text="🎓 MyCourse", bg=BG_SIDEBAR, fg=PRIMARY,
                  font=("Segoe UI", 14, "bold")).pack(anchor="w", padx=18, pady=20)

        menu_items = [
            ("🏠", "Dashboard", True),
            ("📚", "Courses", False),
            ("📝", "Assignment", False),
            ("📅", "Events", False),
            ("⚙", "Settings", False),
            ("🚪", "Logout", False),
        ]
        for icon, text, active in menu_items:
            SidebarButton(sidebar, text, icon, active=active).pack(fill="x", pady=1)

        promo = tk.Frame(sidebar, bg="#EEF0FF", highlightbackground=CARD_BORDER,
                          highlightthickness=1)
        promo.pack(side="bottom", fill="x", padx=14, pady=20)
        tk.Label(promo, text="🚀", bg="#EEF0FF", font=("Segoe UI", 20)).pack(pady=(12, 0))
        tk.Label(promo, text="3 Juta Member\nmenggunakan Paket Platinum",
                  bg="#EEF0FF", fg=TEXT_DARK, font=("Segoe UI", 8, "bold"),
                  justify="center").pack(pady=(4, 8))
        tk.Button(promo, text="Upgrade Sekarang", bg=ACCENT, fg="white",
                   font=("Segoe UI", 8, "bold"), relief="flat", padx=8, pady=6
                   ).pack(pady=(0, 12))

    # ---------------- MAIN CONTENT ----------------
    def _build_main_content(self):
        main = tk.Frame(self, bg=BG_MAIN)
        main.pack(side="left", fill="both", expand=True)

        # ---- Top bar ----
        topbar = tk.Frame(main, bg=BG_MAIN)
        topbar.pack(fill="x", padx=20, pady=(18, 10))
        search = tk.Entry(topbar, font=("Segoe UI", 9), relief="flat", width=30)
        search.insert(0, "  🔍  Cari...")
        search.pack(side="left", ipady=6)
        tk.Label(topbar, text="👤 William Jones", bg=BG_MAIN, fg=TEXT_DARK,
                  font=("Segoe UI", 10, "bold")).pack(side="right")

        # ---- Body: left column + right column ----
        body = tk.Frame(main, bg=BG_MAIN)
        body.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        left_col = tk.Frame(body, bg=BG_MAIN)
        left_col.pack(side="left", fill="both", expand=True)

        right_col = tk.Frame(body, bg=BG_MAIN, width=260)
        right_col.pack(side="right", fill="y", padx=(16, 0))
        right_col.pack_propagate(False)

        self._build_welcome_banner(left_col)
        self._build_category_row(left_col)
        self._build_course_list(left_col)

        self._build_progress_card(right_col)
        self._build_task_card(right_col)

    def _build_welcome_banner(self, parent):
        banner = tk.Frame(parent, bg=PRIMARY, height=110)
        banner.pack(fill="x", pady=(0, 16))
        banner.pack_propagate(False)
        tk.Label(banner, text="Selamat Datang Kembali, Jones!", bg=PRIMARY, fg="white",
                  font=("Segoe UI", 15, "bold")).pack(anchor="w", padx=20, pady=(18, 2))
        tk.Label(banner, text="Yuk, upgrade ke Paket Platinum sekarang", bg=PRIMARY,
                  fg="#E0E0FF", font=("Segoe UI", 9)).pack(anchor="w", padx=20)
        tk.Button(banner, text="Gabung Sekarang ›", bg=ACCENT, fg="white",
                   font=("Segoe UI", 8, "bold"), relief="flat", padx=10, pady=5
                   ).pack(anchor="w", padx=20, pady=10)

    def _build_category_row(self, parent):
        row = tk.Frame(parent, bg=BG_MAIN)
        row.pack(fill="x", pady=(0, 16))
        categories = [
            ("🎨", "Graphic Design", "8/15 Video"),
            ("💻", "Coding", "2/9 Video"),
            ("📈", "Marketing", "2/9 Video"),
        ]
        for icon, name, progress in categories:
            card = tk.Frame(row, bg=BG_CARD, highlightbackground=CARD_BORDER,
                             highlightthickness=1)
            card.pack(side="left", fill="x", expand=True, padx=(0, 10), ipady=10)
            tk.Label(card, text=f"{icon}  {name}", bg=BG_CARD, fg=TEXT_DARK,
                      font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=12, pady=(4, 0))
            tk.Label(card, text=progress, bg=BG_CARD, fg=TEXT_GRAY,
                      font=("Segoe UI", 8)).pack(anchor="w", padx=12, pady=(0, 4))

    def _build_course_list(self, parent):
        header = tk.Frame(parent, bg=BG_MAIN)
        header.pack(fill="x", pady=(0, 10))
        tk.Label(header, text="Kursus Terakhir Dibuka", bg=BG_MAIN, fg=TEXT_DARK,
                  font=("Segoe UI", 11, "bold")).pack(side="left")

        cards_row = tk.Frame(parent, bg=BG_MAIN)
        cards_row.pack(fill="both", expand=True)

        courses = [
            ("Coding", "Kursus Tiga", "John Doe", "3 jam • Menengah", 0.55),
            ("Coding", "Kursus Dua", "Michael Brown", "2 jam • Pemula", 0.30),
            ("Graphic Design", "Kursus Empat", "James Smith", "3 jam • Ahli", 0.80),
        ]
        for cat, title, author, duration, progress in courses:
            CourseCard(cards_row, cat, title, author, duration, progress
                       ).pack(side="left", fill="both", expand=True, padx=(0, 10))

    def _build_progress_card(self, parent):
        card = tk.Frame(parent, bg=BG_CARD, highlightbackground=CARD_BORDER,
                         highlightthickness=1)
        card.pack(fill="x", pady=(0, 16))

        tk.Label(card, text="Progres Belajar", bg=BG_CARD, fg=TEXT_DARK,
                  font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=16, pady=(14, 0))
        tk.Label(card, text="Mingguan ▾", bg=BG_CARD, fg=TEXT_GRAY,
                  font=("Segoe UI", 8)).pack(anchor="w", padx=16)

        donut_frame = tk.Frame(card, bg=BG_CARD)
        donut_frame.pack(pady=10)
        DonutChart(donut_frame, completed=60, in_progress=40, not_started=20).pack()

        legend = tk.Frame(card, bg=BG_CARD)
        legend.pack(fill="x", padx=16, pady=(0, 16))
        items = [
            (PROGRESS_DONE, "Selesai", "60/120"),
            (PROGRESS_INPROGRESS, "Berjalan", "40/120"),
            (PROGRESS_NOTSTARTED, "Belum Mulai", "20/120"),
        ]
        for color, label, val in items:
            row = tk.Frame(legend, bg=BG_CARD)
            row.pack(fill="x", pady=2)
            tk.Canvas(row, width=10, height=10, bg=BG_CARD, highlightthickness=0
                       ).pack(side="left")
            tk.Label(row, text=label, bg=BG_CARD, fg=TEXT_GRAY,
                      font=("Segoe UI", 8)).pack(side="left", padx=6)
            tk.Label(row, text=val, bg=BG_CARD, fg=TEXT_DARK,
                      font=("Segoe UI", 8, "bold")).pack(side="right")

    def _build_task_card(self, parent):
        card = tk.Frame(parent, bg=BG_CARD, highlightbackground=CARD_BORDER,
                         highlightthickness=1)
        card.pack(fill="both", expand=True)

        header = tk.Frame(card, bg=BG_CARD)
        header.pack(fill="x", padx=16, pady=(14, 8))
        tk.Label(header, text="Tugas Kursus", bg=BG_CARD, fg=TEXT_DARK,
                  font=("Segoe UI", 11, "bold")).pack(side="left")
        tk.Label(header, text="Lihat Semua", bg=BG_CARD, fg=PRIMARY,
                  font=("Segoe UI", 8, "bold")).pack(side="right")

        tasks = [
            ("📌", "Mulai Tugas Satu", "3 hari 16 jam tersisa"),
            ("✏️", "Mulai Tugas Dua", "3 hari 20 jam tersisa"),
            ("📐", "Mulai Tugas Tiga", "4 hari 6 jam tersisa"),
        ]
        for icon, title, remaining in tasks:
            TaskItem(card, icon, title, remaining).pack(fill="x", padx=16, pady=4)


if __name__ == "__main__":
    app = Dashboard()
    app.mainloop()