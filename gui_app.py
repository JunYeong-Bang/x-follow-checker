from pathlib import Path
from io import BytesIO
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Any, Dict, List, Tuple
import webbrowser
from urllib.error import URLError
from urllib.request import Request, urlopen

import customtkinter as ctk

try:
    from PIL import Image, ImageDraw, ImageTk

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

from archive_checker import analyze_archive_bundle


class FollowArchiveApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()

        self.title("X Archive Follow Checker")
        self.geometry("1140x770")
        self.minsize(1020, 700)

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.bg_color = "#000000"
        self.card_bg = "#16181c"
        self.card_border = "#2f3336"
        self.primary = "#1d9bf0"
        self.text_primary = "#e7e9ea"
        self.text_secondary = "#71767b"
        self.input_bg = "#202327"

        self.configure(fg_color=self.bg_color)

        self.path_var = tk.StringVar(value="아카이브 zip 파일을 선택하세요")
        self.summary_var = tk.StringVar(value="분석 전")

        self.result: Dict[str, List[str]] = {
            "one_way_following": [],
            "mutuals": [],
            "one_way_followers": [],
        }
        self.profile: Dict[str, str] = {
            "display_name": "",
            "username": "",
            "account_id": "",
            "avatar_url": "",
        }
        self.counts: Dict[str, int] = {
            "following_total": 0,
            "followers_total": 0,
        }

        self.avatar_url = ""
        self.avatar_photo: Any = None

        self._configure_treeview_style()
        self._build_ui()

    def _configure_treeview_style(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure(
            "App.Treeview",
            background="#0f1113",
            foreground=self.text_primary,
            fieldbackground="#0f1113",
            rowheight=32,
            bordercolor=self.card_border,
            borderwidth=1,
            font=("Segoe UI", 10),
        )
        style.configure(
            "App.Treeview.Heading",
            background="#151a1e",
            foreground=self.text_secondary,
            bordercolor=self.card_border,
            font=("Segoe UI", 10, "bold"),
        )
        style.map(
            "App.Treeview",
            background=[("selected", "#1d9bf033")],
            foreground=[("selected", self.text_primary)],
        )

    def _build_ui(self) -> None:
        layout = ctk.CTkFrame(self, fg_color="transparent")
        layout.pack(fill="both", expand=True, padx=16, pady=16)

        sidebar = ctk.CTkFrame(
            layout,
            fg_color="transparent",
            width=280,
        )
        sidebar.pack(side="left", fill="y", padx=(0, 14))
        sidebar.pack_propagate(False)

        main = ctk.CTkFrame(layout, fg_color="transparent")
        main.pack(side="left", fill="both", expand=True)

        self._build_sidebar(sidebar)
        self._build_main(main)

    def _build_main(self, parent: ctk.CTkFrame) -> None:
        ctk.CTkLabel(
            parent,
            text="X Follow Archive Dashboard",
            text_color=self.text_primary,
            font=ctk.CTkFont("Segoe UI", 22, "bold"),
        ).pack(anchor="w")
        ctk.CTkLabel(
            parent,
            text="zip 파일을 업로드해 일방 팔로우 / 맞팔 / 일방 팔로워를 확인하세요.",
            text_color=self.text_secondary,
            font=ctk.CTkFont("Segoe UI", 12),
        ).pack(anchor="w", pady=(2, 10))

        upload_card = ctk.CTkFrame(
            parent,
            fg_color=self.card_bg,
            border_width=1,
            border_color=self.card_border,
            corner_radius=16,
        )
        upload_card.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            upload_card,
            text="데이터 아카이브(zip)",
            text_color=self.text_secondary,
            font=ctk.CTkFont("Segoe UI", 12),
        ).pack(anchor="w", padx=14, pady=(12, 6))

        row = ctk.CTkFrame(upload_card, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=(0, 12))

        self.path_entry = ctk.CTkEntry(
            row,
            textvariable=self.path_var,
            fg_color=self.input_bg,
            border_color=self.card_border,
            text_color=self.text_primary,
            corner_radius=12,
            height=38,
        )
        self.path_entry.pack(side="left", fill="x", expand=True)

        ctk.CTkButton(
            row,
            text="파일 선택",
            command=self.pick_file,
            fg_color=self.input_bg,
            hover_color="#2b2f34",
            border_color=self.card_border,
            border_width=1,
            text_color=self.text_primary,
            corner_radius=12,
            height=38,
            width=92,
        ).pack(side="left", padx=(8, 0))

        ctk.CTkButton(
            row,
            text="분석",
            command=self.run_analysis,
            fg_color=self.primary,
            hover_color="#178ad8",
            text_color="#ffffff",
            corner_radius=12,
            height=38,
            width=78,
        ).pack(side="left", padx=(8, 0))

        self.summary_label = ctk.CTkLabel(
            parent,
            textvariable=self.summary_var,
            text_color="#8ecdf8",
            font=ctk.CTkFont("Segoe UI", 12, "bold"),
        )
        self.summary_label.pack(anchor="w", pady=(0, 10))

        tabs_card = ctk.CTkFrame(
            parent,
            fg_color=self.card_bg,
            border_width=1,
            border_color=self.card_border,
            corner_radius=16,
        )
        tabs_card.pack(fill="both", expand=True)

        self.tabview = ctk.CTkTabview(
            tabs_card,
            fg_color=self.card_bg,
            segmented_button_fg_color="#0f1113",
            segmented_button_selected_color=self.primary,
            segmented_button_selected_hover_color="#178ad8",
            segmented_button_unselected_color="#202327",
            segmented_button_unselected_hover_color="#2b2f34",
            text_color=self.text_primary,
            corner_radius=14,
            border_width=0,
        )
        self.tabview.pack(fill="both", expand=True, padx=10, pady=10)

        self.one_way_following_table = self._build_table_tab("일방 팔로우")
        self.mutuals_table = self._build_table_tab("맞팔")
        self.one_way_followers_table = self._build_table_tab("일방 팔로워")

    def _build_table_tab(self, title: str) -> ttk.Treeview:
        tab = self.tabview.add(title)

        table_wrap = tk.Frame(tab, bg=self.card_bg)
        table_wrap.pack(fill="both", expand=True, padx=8, pady=8)

        table = ttk.Treeview(table_wrap, columns=("identifier", "x_link"), show="headings", style="App.Treeview")
        table.heading("identifier", text="ID / Username")
        table.heading("x_link", text="X Link")
        table.column("identifier", width=230, anchor="w")
        table.column("x_link", width=650, anchor="w")
        table.pack(side="left", fill="both", expand=True)

        table.tag_configure("odd", background="#101318")
        table.tag_configure("even", background="#0b0d10")

        scrollbar = ctk.CTkScrollbar(table_wrap, orientation="vertical", command=table.yview)
        scrollbar.pack(side="right", fill="y")
        table.configure(yscrollcommand=scrollbar.set)
        table.bind("<Double-1>", self._open_selected_link)
        return table

    def _build_sidebar(self, parent: ctk.CTkFrame) -> None:
        profile_card = ctk.CTkFrame(
            parent,
            fg_color=self.card_bg,
            border_width=1,
            border_color=self.card_border,
            corner_radius=16,
        )
        profile_card.pack(fill="x")

        ctk.CTkLabel(
            profile_card,
            text="내 프로필",
            text_color=self.text_secondary,
            font=ctk.CTkFont("Segoe UI", 12, "bold"),
        ).pack(anchor="w", padx=14, pady=(12, 8))

        self.avatar_canvas = tk.Canvas(
            profile_card,
            width=320,
            height=320,
            bg=self.card_bg,
            highlightthickness=0,
            cursor="hand2",
        )
        self.avatar_canvas.pack(padx=14, pady=(0, 10), anchor="center")
        self.avatar_circle_id = self.avatar_canvas.create_oval(10, 10, 310, 310, fill=self.primary, outline="")
        self.avatar_text_id = self.avatar_canvas.create_text(160, 160, text="ME", fill="white", font=("Segoe UI", 28, "bold"))
        self.avatar_canvas.bind("<Button-1>", self._open_avatar_link)

        self.profile_name_var = tk.StringVar(value="이름: -")
        self.profile_username_var = tk.StringVar(value="사용자명: -")
        self.profile_id_var = tk.StringVar(value="ID: -")
        self.following_count_var = tk.StringVar(value="팔로잉: 0")
        self.followers_count_var = tk.StringVar(value="팔로워: 0")
        self.avatar_hint_var = tk.StringVar(value="아바타 링크 없음")

        for var in [
            self.profile_name_var,
            self.profile_username_var,
            self.profile_id_var,
            self.following_count_var,
            self.followers_count_var,
        ]:
            ctk.CTkLabel(
                profile_card,
                textvariable=var,
                text_color=self.text_primary,
                font=ctk.CTkFont("Segoe UI", 12),
            ).pack(anchor="w", padx=14, pady=(0, 4))

        ctk.CTkLabel(
            profile_card,
            textvariable=self.avatar_hint_var,
            text_color=self.text_secondary,
            font=ctk.CTkFont("Segoe UI", 11),
            wraplength=240,
            justify="left",
        ).pack(anchor="w", padx=14, pady=(4, 12))

        help_card = ctk.CTkFrame(
            parent,
            fg_color=self.card_bg,
            border_width=1,
            border_color=self.card_border,
            corner_radius=16,
        )
        help_card.pack(fill="x", pady=(12, 0))

        ctk.CTkLabel(
            help_card,
            text="사용 가이드",
            text_color=self.text_secondary,
            font=ctk.CTkFont("Segoe UI", 12, "bold"),
        ).pack(anchor="w", padx=14, pady=(12, 8))

        ctk.CTkLabel(
            help_card,
            text="표 행 더블클릭: X 링크 열기",
            text_color=self.text_secondary,
            font=ctk.CTkFont("Segoe UI", 11),
        ).pack(anchor="w", padx=14)
        ctk.CTkLabel(
            help_card,
            text="아바타 클릭: 원본 이미지 열기",
            text_color=self.text_secondary,
            font=ctk.CTkFont("Segoe UI", 11),
        ).pack(anchor="w", padx=14, pady=(4, 12))

    def pick_file(self) -> None:
        selected = filedialog.askopenfilename(
            title="X 데이터 아카이브 zip 선택",
            filetypes=[("Zip files", "*.zip"), ("All files", "*.*")],
        )
        if selected:
            self.path_var.set(selected)

    def run_analysis(self) -> None:
        value = self.path_var.get().strip()
        archive_path = Path(value)

        if not value or not archive_path.exists() or not archive_path.is_file():
            messagebox.showerror("오류", "올바른 zip 파일을 선택하세요.")
            return

        try:
            bundle: Dict[str, Any] = analyze_archive_bundle(archive_path)
            self.result = bundle.get("result", self.result)
            self.profile = bundle.get("profile", self.profile)
            self.counts = bundle.get("counts", self.counts)
            self._render_results()
            self._render_sidebar()
        except Exception as exc:
            messagebox.showerror("분석 실패", str(exc))

    def _render_results(self) -> None:
        one_way_following = self.result["one_way_following"]
        mutuals = self.result["mutuals"]
        one_way_followers = self.result["one_way_followers"]

        self.summary_var.set(
            f"일방 팔로우: {len(one_way_following)} | 맞팔: {len(mutuals)} | 일방 팔로워: {len(one_way_followers)}"
        )

        self._update_table(self.one_way_following_table, one_way_following)
        self._update_table(self.mutuals_table, mutuals)
        self._update_table(self.one_way_followers_table, one_way_followers)

    def _render_sidebar(self) -> None:
        display_name = (self.profile.get("display_name") or "").strip() or "-"
        username = (self.profile.get("username") or "").strip()
        account_id = (self.profile.get("account_id") or "").strip() or "-"

        username_text = f"@{username}" if username else "-"

        initials = "ME"
        if username:
            initials = username[:2].upper()
        elif display_name != "-":
            initials = display_name[:2].upper()

        self.avatar_url = (self.profile.get("avatar_url") or "").strip()
        self._render_avatar(initials)
        if self.avatar_url:
            self.avatar_hint_var.set("원형 아바타 클릭: 프로필 이미지 열기")
        else:
            self.avatar_hint_var.set("아바타 링크 없음")

        self.profile_name_var.set(f"이름: {display_name}")
        self.profile_username_var.set(f"사용자명: {username_text}")
        self.profile_id_var.set(f"ID: {account_id}")
        self.following_count_var.set(f"팔로잉: {self.counts.get('following_total', 0)}")
        self.followers_count_var.set(f"팔로워: {self.counts.get('followers_total', 0)}")

    @staticmethod
    def _to_table_row(value: str) -> Tuple[str, str]:
        if value.isdigit():
            return value, f"https://x.com/i/user/{value}"
        username = value.lstrip("@")
        return f"@{username}", f"https://x.com/{username}"

    @staticmethod
    def _update_table(table: ttk.Treeview, values: List[str]) -> None:
        for item_id in table.get_children():
            table.delete(item_id)
        for idx, value in enumerate(values):
            identifier, link = FollowArchiveApp._to_table_row(value)
            table.insert("", tk.END, values=(identifier, link), tags=("odd" if idx % 2 else "even",))

    def _open_selected_link(self, event: tk.Event) -> None:
        table = event.widget
        if not isinstance(table, ttk.Treeview):
            return
        selection = table.selection()
        if not selection:
            return

        values = table.item(selection[0], "values")
        if len(values) < 2:
            return
        link = str(values[1]).strip()
        if link.startswith("http"):
            webbrowser.open_new_tab(link)

    def _open_avatar_link(self, _event: tk.Event) -> None:
        if self.avatar_url.startswith("http"):
            webbrowser.open_new_tab(self.avatar_url)

    def _render_avatar(self, initials: str) -> None:
        self.avatar_canvas.delete("avatar_img")
        self.avatar_canvas.itemconfigure(self.avatar_text_id, text=initials)
        self.avatar_canvas.itemconfigure(self.avatar_circle_id, fill=self.primary)  # 기본 파란색 원 표시

        if not PIL_AVAILABLE or not self.avatar_url.startswith("http"):
            self.avatar_photo = None
            return

        try:
            request = Request(self.avatar_url, headers={"User-Agent": "Mozilla/5.0"})
            with urlopen(request, timeout=5) as response:
                raw = response.read()

            image = Image.open(BytesIO(raw)).convert("RGBA")
            image = image.resize((300, 300), Image.Resampling.LANCZOS)

            # 고해상도 마스크로 정밀한 원형 생성
            mask = Image.new("L", (1200, 1200), 0)
            draw = ImageDraw.Draw(mask)
            draw.ellipse((0, 0, 1199, 1199), fill=255)
            mask = mask.resize((300, 300), Image.Resampling.LANCZOS)
            image.putalpha(mask)

            self.avatar_photo = ImageTk.PhotoImage(image)
            self.avatar_canvas.create_image(160, 160, image=self.avatar_photo, tags="avatar_img")
            self.avatar_canvas.itemconfigure(self.avatar_text_id, text="")
            self.avatar_canvas.itemconfigure(self.avatar_circle_id, fill="")  # 파란색 원 숨기기
        except (OSError, URLError, ValueError):
            self.avatar_photo = None


def main() -> None:
    app = FollowArchiveApp()
    app.mainloop()


if __name__ == "__main__":
    main()
