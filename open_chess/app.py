from __future__ import annotations

import os
import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import customtkinter as ctk
from PIL import Image

from .database import Database
from .excel_import import read_student_rows
from .reports import pairings_pdf, participants_pdf, standings_pdf
from .swiss import calculate_standings, generate_pairings


BG = "#EAF1F5"
SURFACE = "#FFFFFF"
NAVY = "#102F49"
PRIMARY = "#2676B5"
PRIMARY_HOVER = "#195D91"
TAB_SELECTED = "#8CCBEA"
TAB_SELECTED_HOVER = "#72BBDD"
GREEN = "#287A5C"
GREEN_HOVER = "#1E6048"
RED = "#B54848"
TEXT = "#19364D"
MUTED = "#5D7182"
BORDER = "#D0DEE6"
PALE_BLUE = "#E7F2F9"
SHADOW = "#DCE6EB"
HEADER_BG = "#0A2639"
HEADER_CARD = "#174864"
HEADER_BORDER = "#5C91AD"

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")


def default_data_path() -> Path:
    if sys.platform == "win32":
        root = Path(os.environ.get("APPDATA", Path.home())) / "OpenChess"
    else:
        root = Path.home() / ".open_chess"
    return root / "open_chess.db"


def resource_path(relative_path: str) -> Path:
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    return root / relative_path


def safe_name(value: str) -> str:
    return "".join(char if char.isalnum() else "_" for char in value).strip("_").lower()


def number(value: float) -> str:
    return str(int(value)) if value.is_integer() else str(value).replace(".", ",")


def open_file(path: str) -> None:
    if sys.platform == "win32":
        os.startfile(path)  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdg-open", path])


def configure_tree_style(root: tk.Misc) -> None:
    style = ttk.Style(root)
    if "clam" in style.theme_names():
        style.theme_use("clam")
    style.configure("OpenChess.Treeview", background=SURFACE, fieldbackground=SURFACE,
                    foreground=TEXT, rowheight=36, font=("Segoe UI", 12), borderwidth=0)
    style.map("OpenChess.Treeview", background=[("selected", "#CFE7F5")],
              foreground=[("selected", TEXT)])
    style.configure("OpenChess.Treeview.Heading", background="#DDEAF1", foreground=TEXT,
                    font=("Segoe UI", 10, "bold"), padding=(8, 9), borderwidth=0)


def make_tree(parent, columns, headings, widths, anchors=None) -> ttk.Treeview:
    shadow = ctk.CTkFrame(parent, fg_color=SHADOW, corner_radius=18)
    shadow.pack(fill="both", expand=True)
    card = ctk.CTkFrame(shadow, fg_color=SURFACE, corner_radius=16,
                        border_width=1, border_color=BORDER)
    card.pack(fill="both", expand=True, padx=3, pady=3)
    holder = tk.Frame(card, bg=SURFACE)
    holder.pack(fill="both", expand=True, padx=9, pady=9)
    tree = ttk.Treeview(holder, columns=columns, show="headings", style="OpenChess.Treeview")
    for index, (column, heading, width) in enumerate(zip(columns, headings, widths)):
        tree.heading(column, text=heading)
        anchor = anchors[index] if anchors else ("center" if width <= 120 else "w")
        tree.column(column, width=width, minwidth=50, anchor=anchor)
    scrollbar = ttk.Scrollbar(holder, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)
    tree.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    return tree


class OpenChessApp(ctk.CTk):
    def __init__(self, db_path: str | Path | None = None):
        super().__init__()
        self.title("Open Chess · Campeonatos escolares")
        self.geometry("1280x820")
        self.minsize(1050, 700)
        self.configure(fg_color=BG)
        self.db = Database(db_path or default_data_path())
        self.current_id: int | None = None
        self.current_name = ""
        self.current_school = "CEIP Vista Alegre"
        self.editing_player_id: int | None = None
        self.group_labels: dict[str, object] = {}
        configure_tree_style(self)
        self._build_shell()
        self._build_groups_tab()
        self._build_pairings_tab()
        self._build_standings_tab()
        self.refresh_all()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def _build_shell(self) -> None:
        header = ctk.CTkFrame(self, height=116, corner_radius=0, fg_color=HEADER_BG)
        header.pack(fill="x")
        header.pack_propagate(False)
        header_shadow = ctk.CTkFrame(header, fg_color="#061B29", corner_radius=22)
        header_shadow.pack(fill="both", expand=True, padx=17, pady=(10, 8))
        header_card = ctk.CTkFrame(header_shadow, fg_color=HEADER_CARD, corner_radius=20,
                                   border_width=1, border_color=HEADER_BORDER)
        header_card.pack(fill="both", expand=True, pady=(0, 4))

        brand = ctk.CTkFrame(header_card, fg_color="transparent")
        brand.pack(side="left", padx=(20, 28), pady=11)
        icon_path = resource_path("assets/openchess-icon-1024.png")
        self.header_logo = ctk.CTkImage(light_image=Image.open(icon_path),
                                        dark_image=Image.open(icon_path), size=(62, 62))
        ctk.CTkLabel(brand, text="", image=self.header_logo).pack(side="left", padx=(0, 12))
        brand_text = ctk.CTkFrame(brand, fg_color="transparent")
        brand_text.pack(side="left")
        ctk.CTkLabel(brand_text, text="OPEN CHESS", text_color="white",
                     font=ctk.CTkFont(size=25, weight="bold"), anchor="w").pack(anchor="w")
        ctk.CTkLabel(brand_text, text="VISTA ALEGRE", text_color="#A9DDF4",
                     font=ctk.CTkFont(size=12, weight="bold"), anchor="w").pack(anchor="w")

        separator = ctk.CTkFrame(header_card, width=2, height=58, corner_radius=1,
                                 fg_color="#5D8298")
        separator.pack(side="left", padx=(0, 27), pady=17)
        title_box = ctk.CTkFrame(header_card, fg_color="transparent")
        title_box.pack(side="left", fill="y", pady=17)
        ctk.CTkLabel(title_box, text="Gestión de campeonatos escolares", text_color="white",
                     font=ctk.CTkFont(size=18, weight="bold"), anchor="w").pack(anchor="w")
        self.global_status = ctk.CTkLabel(title_box, text="", text_color="#C8D9E5",
                                          font=ctk.CTkFont(size=12), anchor="w")
        self.global_status.pack(anchor="w")
        ctk.CTkButton(header_card, text="Restaurar copia", command=self.restore_group,
                      width=150, height=42, corner_radius=12, fg_color="#8CD4F2",
                      hover_color="#A9E1F7", border_width=2, border_color="#C8EEFC",
                      text_color="#103149", font=ctk.CTkFont(weight="bold")).pack(
                          side="right", padx=22)

        tabs_shell = ctk.CTkFrame(self, fg_color="#F2F7FA", corner_radius=24,
                                  border_width=1, border_color="#D5E2E8")
        tabs_shell.pack(fill="both", expand=True, padx=18, pady=(12, 18))
        self.tabs = ctk.CTkTabview(
            tabs_shell, fg_color="#F2F7FA", corner_radius=19, border_width=0,
            segmented_button_fg_color="#D6E4EC", segmented_button_selected_color=TAB_SELECTED,
            segmented_button_selected_hover_color=TAB_SELECTED_HOVER,
            segmented_button_unselected_color="#E4EDF2",
            segmented_button_unselected_hover_color="#CADDE7",
            text_color=TEXT,
        )
        self.tabs.pack(fill="both", expand=True, padx=4, pady=4)
        self.groups_tab = self.tabs.add("Grupos")
        self.pairings_tab = self.tabs.add("Emparejamientos")
        self.standings_tab = self.tabs.add("Clasificaciones")
        self.tabs._segmented_button.configure(
            height=47, corner_radius=13, border_width=3,
            font=ctk.CTkFont(size=15, weight="bold")
        )
        self.tabs.set("Grupos")

    def _build_groups_tab(self) -> None:
        tab = self.groups_tab
        tab.grid_columnconfigure(0, weight=0, minsize=300)
        tab.grid_columnconfigure(1, weight=1)
        tab.grid_rowconfigure(0, weight=1)
        left = ctk.CTkFrame(tab, width=300, fg_color=SURFACE, corner_radius=18,
                            border_width=1, border_color=BORDER)
        left.grid(row=0, column=0, sticky="nsew", padx=(4, 10), pady=8)
        left.grid_propagate(False)
        left.grid_rowconfigure(3, weight=1)
        ctk.CTkLabel(left, text="Grupos", text_color=TEXT,
                     font=ctk.CTkFont(size=21, weight="bold"), anchor="w").grid(
                         row=0, column=0, sticky="ew", padx=18, pady=(18, 5))
        ctk.CTkLabel(left, text="Selecciona un grupo para gestionarlo", text_color=MUTED,
                     font=ctk.CTkFont(size=12), anchor="w").grid(row=1, column=0, sticky="ew", padx=18)
        ctk.CTkButton(left, text="＋ Crear grupo", command=self.toggle_new_group_form,
                      height=39, corner_radius=11, fg_color=PRIMARY, hover_color=PRIMARY_HOVER,
                      text_color="white", font=ctk.CTkFont(weight="bold")).grid(
                          row=2, column=0, sticky="ew", padx=16, pady=(14, 8))
        self.groups_list = ctk.CTkScrollableFrame(left, fg_color="transparent")
        self.groups_list.grid(row=3, column=0, sticky="nsew", padx=10, pady=(0, 8))
        self.groups_list.grid_columnconfigure(0, weight=1)
        tools = ctk.CTkFrame(left, fg_color="transparent")
        tools.grid(row=4, column=0, sticky="ew", padx=16, pady=(0, 16))
        ctk.CTkButton(tools, text="Guardar copia", command=self.backup_group, height=36,
                      corner_radius=9, fg_color="#E4EDF3", hover_color="#D3E2EA",
                      text_color=TEXT).pack(fill="x", pady=(0, 6))
        ctk.CTkButton(tools, text="Eliminar grupo", command=self.delete_group, height=36,
                      corner_radius=9, fg_color="transparent", hover_color="#F7E5E5",
                      border_width=1, border_color="#DDAAAA", text_color=RED).pack(fill="x")

        right = ctk.CTkFrame(tab, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew", padx=(0, 4), pady=8)
        right.grid_rowconfigure(3, weight=1)
        right.grid_columnconfigure(0, weight=1)
        self.new_group_panel = ctk.CTkFrame(right, fg_color=PALE_BLUE, corner_radius=16)
        self.new_group_panel.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        ctk.CTkLabel(self.new_group_panel, text="Nuevo grupo", text_color=TEXT,
                     font=ctk.CTkFont(size=16, weight="bold")).pack(side="left", padx=(18, 10), pady=14)
        self.new_group_entry = ctk.CTkEntry(self.new_group_panel, placeholder_text="Nombre del grupo",
            height=38, corner_radius=10, fg_color=SURFACE, border_color="#AAC2D1", text_color=TEXT)
        self.new_group_entry.pack(side="left", fill="x", expand=True, padx=8, pady=11)
        ctk.CTkButton(self.new_group_panel, text="Crear", command=self.create_group, width=90,
                      height=38, corner_radius=10, fg_color=GREEN, hover_color=GREEN_HOVER,
                      text_color="white").pack(side="left", padx=8, pady=11)
        ctk.CTkButton(self.new_group_panel, text="Cancelar", command=self.hide_new_group_form, width=90,
                      height=38, corner_radius=10, fg_color="#DCE7ED", hover_color="#CBDCE5",
                      text_color=TEXT).pack(side="left", padx=(0, 14), pady=11)
        self.new_group_panel.grid_remove()

        group_header = ctk.CTkFrame(right, fg_color="transparent")
        group_header.grid(row=1, column=0, sticky="ew", pady=(2, 10))
        self.players_title = ctk.CTkLabel(group_header, text="Selecciona un grupo", text_color=TEXT,
                                          font=ctk.CTkFont(size=22, weight="bold"), anchor="w")
        self.players_title.pack(side="left")
        self.players_count = ctk.CTkLabel(group_header, text="", text_color=MUTED,
                                          font=ctk.CTkFont(size=13))
        self.players_count.pack(side="right")

        self.player_form = ctk.CTkFrame(right, fg_color=SURFACE, corner_radius=16,
                                        border_width=1, border_color=BORDER)
        self.player_form.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        self.player_entries: dict[str, ctk.CTkEntry] = {}
        fields = (("Nombre *", "first_name", 1), ("Apellidos *", "last_name", 2),
                  ("Curso", "course", 1), ("Centro", "center", 2))
        for col, (label, key, weight) in enumerate(fields):
            self.player_form.grid_columnconfigure(col, weight=weight)
            ctk.CTkLabel(self.player_form, text=label, text_color=TEXT,
                         font=ctk.CTkFont(size=12, weight="bold")).grid(
                             row=0, column=col, sticky="w", padx=(14 if col == 0 else 6, 6), pady=(11, 2))
            entry = ctk.CTkEntry(self.player_form, height=36, corner_radius=9, fg_color="#F8FAFC",
                                 border_color="#B8CAD6", text_color=TEXT)
            entry.grid(row=1, column=col, sticky="ew", padx=(14 if col == 0 else 6, 6), pady=(0, 12))
            self.player_entries[key] = entry
        self.player_submit = ctk.CTkButton(self.player_form, text="Añadir", command=self.submit_player,
            width=95, height=36, corner_radius=9, fg_color=GREEN, hover_color=GREEN_HOVER, text_color="white")
        self.player_submit.grid(row=1, column=4, padx=(6, 7), pady=(0, 12))
        self.player_cancel = ctk.CTkButton(self.player_form, text="Cancelar", command=self.cancel_player_edit,
            width=85, height=36, corner_radius=9, fg_color="#E4EDF3", hover_color="#D3E2EA", text_color=TEXT)
        self.player_cancel.grid(row=1, column=5, padx=(0, 12), pady=(0, 12))
        self.player_cancel.grid_remove()

        table_area = ctk.CTkFrame(right, fg_color="transparent")
        table_area.grid(row=3, column=0, sticky="nsew")
        actions = ctk.CTkFrame(table_area, fg_color="transparent")
        actions.pack(fill="x", pady=(0, 8))
        ctk.CTkButton(actions, text="Editar seleccionado", command=self.start_player_edit,
                      width=145, height=35, corner_radius=9, fg_color="#E4EDF3",
                      hover_color="#D3E2EA", text_color=TEXT).pack(side="left")
        ctk.CTkButton(actions, text="Retirar", command=self.remove_player, width=95, height=35,
                      corner_radius=9, fg_color="transparent", hover_color="#F7E5E5",
                      border_width=1, border_color="#DDAAAA", text_color=RED).pack(side="left", padx=7)
        ctk.CTkButton(actions, text="Importar Excel", command=self.import_students_excel,
                      width=130, height=35, corner_radius=9, fg_color=GREEN,
                      hover_color=GREEN_HOVER, text_color="white",
                      font=ctk.CTkFont(weight="bold")).pack(side="left")
        ctk.CTkButton(actions, text="Exportar alumnos PDF", command=self.export_players_pdf,
                      width=155, height=35, corner_radius=9, fg_color=PRIMARY,
                      hover_color=PRIMARY_HOVER, text_color="white").pack(side="right")
        self.players_tree = make_tree(table_area, ("name", "course", "center"),
                                      ("Alumno/a", "Curso", "Centro"), (350, 120, 280),
                                      anchors=("w", "center", "center"))

    def _build_pairings_tab(self) -> None:
        tab = self.pairings_tab
        toolbar = ctk.CTkFrame(tab, fg_color=SURFACE, corner_radius=16, border_width=1, border_color=BORDER)
        toolbar.pack(fill="x", padx=4, pady=(8, 10))
        ctk.CTkLabel(toolbar, text="Grupo", text_color=TEXT,
                     font=ctk.CTkFont(size=13, weight="bold")).pack(side="left", padx=(16, 8), pady=13)
        self.pairing_group_var = tk.StringVar(value="Sin grupos")
        self.pairing_group_menu = ctk.CTkOptionMenu(toolbar, variable=self.pairing_group_var,
            values=["Sin grupos"], command=self.select_group_label, width=245, height=37,
            corner_radius=10, fg_color="#DDEAF1", button_color="#B9D2E0", text_color=TEXT)
        self.pairing_group_menu.pack(side="left", pady=10)
        ctk.CTkButton(toolbar, text="Generar siguiente ronda", command=self.new_round,
                      height=37, corner_radius=10, fg_color=GREEN, hover_color=GREEN_HOVER,
                      text_color="white", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=12, pady=10)
        ctk.CTkLabel(toolbar, text="Ronda", text_color=TEXT,
                     font=ctk.CTkFont(size=13, weight="bold")).pack(side="left", padx=(5, 7))
        self.round_var = tk.StringVar(value="0")
        self.round_menu = ctk.CTkOptionMenu(toolbar, variable=self.round_var, values=["0"],
            command=lambda _value: self.refresh_pairings(), width=82, height=37, corner_radius=10,
            fg_color=PRIMARY, button_color=PRIMARY_HOVER, text_color="white")
        self.round_menu.pack(side="left", pady=10)
        ctk.CTkButton(toolbar, text="Exportar PDF", command=self.export_pairings_pdf,
                      width=115, height=37, corner_radius=10, fg_color=PRIMARY,
                      hover_color=PRIMARY_HOVER, text_color="white").pack(side="right", padx=14, pady=10)
        table_area = ctk.CTkFrame(tab, fg_color="transparent")
        table_area.pack(fill="both", expand=True, padx=4)
        self.pairings_tree = make_tree(table_area, ("board", "white", "black", "result"),
            ("Mesa", "Blancas", "Negras", "Resultado"), (70, 350, 350, 130))
        self.pairings_tree.bind("<<TreeviewSelect>>", self.on_pairing_selected)
        result_bar = ctk.CTkFrame(tab, fg_color="#E2EDF3", corner_radius=17,
                                  border_width=1, border_color="#B5CCD9")
        result_bar.pack(fill="x", padx=4, pady=(10, 8))
        result_text = ctk.CTkFrame(result_bar, fg_color="transparent")
        result_text.pack(side="left", fill="x", expand=True, padx=(17, 10), pady=11)
        ctk.CTkLabel(result_text, text="Puntuar la mesa seleccionada", text_color=TEXT,
                     font=ctk.CTkFont(size=14, weight="bold"), anchor="w").pack(anchor="w")
        self.score_hint = ctk.CTkLabel(result_text, text="Selecciona un emparejamiento de la lista",
                                       text_color=MUTED, font=ctk.CTkFont(size=12), anchor="w")
        self.score_hint.pack(anchor="w")
        ctk.CTkButton(result_bar, text="↺\nDejar pendiente", command=self.clear_selected_result,
                      width=125, height=54, corner_radius=12, fg_color="#E8EFF3",
                      hover_color="#D3E2EA", border_width=2, border_color="#A9BEC9",
                      text_color=TEXT, font=ctk.CTkFont(size=13, weight="bold")).pack(
                          side="left", padx=5, pady=10)
        ctk.CTkButton(result_bar, text="1–0\nGanan blancas", command=lambda: self.score_selected("1-0"),
                      width=150, height=54, corner_radius=12, fg_color="#2778B8",
                      hover_color="#1B6092", border_width=2, border_color="#15517D",
                      text_color="white", font=ctk.CTkFont(size=13, weight="bold")).pack(
                          side="left", padx=5, pady=10)
        ctk.CTkButton(result_bar, text="½–½\nTablas", command=lambda: self.score_selected("1/2-1/2"),
                      width=135, height=54, corner_radius=12, fg_color="#E4B443",
                      hover_color="#CEA02F", border_width=2, border_color="#A87B18",
                      text_color="#352706", font=ctk.CTkFont(size=13, weight="bold")).pack(
                          side="left", padx=5, pady=10)
        ctk.CTkButton(result_bar, text="0–1\nGanan negras", command=lambda: self.score_selected("0-1"),
                      width=150, height=54, corner_radius=12, fg_color="#263F55",
                      hover_color="#172D40", border_width=2, border_color="#10283B",
                      text_color="white", font=ctk.CTkFont(size=13, weight="bold")).pack(
                          side="left", padx=(5, 14), pady=10)

    def _build_standings_tab(self) -> None:
        tab = self.standings_tab
        toolbar = ctk.CTkFrame(tab, fg_color=SURFACE, corner_radius=16, border_width=1, border_color=BORDER)
        toolbar.pack(fill="x", padx=4, pady=(8, 10))
        ctk.CTkLabel(toolbar, text="Grupo", text_color=TEXT,
                     font=ctk.CTkFont(size=13, weight="bold")).pack(side="left", padx=(16, 8), pady=13)
        self.standings_group_var = tk.StringVar(value="Sin grupos")
        self.standings_group_menu = ctk.CTkOptionMenu(toolbar, variable=self.standings_group_var,
            values=["Sin grupos"], command=self.select_group_label, width=245, height=37,
            corner_radius=10, fg_color="#DDEAF1", button_color="#B9D2E0", text_color=TEXT)
        self.standings_group_menu.pack(side="left", pady=10)
        ctk.CTkLabel(toolbar, text="Orden: puntos · Buchholz · victorias · nombre", text_color=MUTED,
                     font=ctk.CTkFont(size=12)).pack(side="left", padx=18)
        ctk.CTkButton(toolbar, text="Exportar PDF", command=self.export_standings_pdf,
                      width=115, height=37, corner_radius=10, fg_color=PRIMARY,
                      hover_color=PRIMARY_HOVER, text_color="white").pack(side="right", padx=14, pady=10)
        ctk.CTkButton(toolbar, text="Actualizar", command=self.refresh_standings,
                      width=100, height=37, corner_radius=10, fg_color="#E4EDF3",
                      hover_color="#D3E2EA", text_color=TEXT).pack(side="right", pady=10)
        table_area = ctk.CTkFrame(tab, fg_color="transparent")
        table_area.pack(fill="both", expand=True, padx=4, pady=(0, 8))
        self.standings_tree = make_tree(table_area,
            ("pos", "name", "course", "center", "points", "buchholz", "wins"),
            ("Pos.", "Alumno/a", "Curso", "Centro", "Puntos", "Buchholz", "Victorias"),
            (55, 285, 105, 230, 75, 85, 80))

    def toggle_new_group_form(self) -> None:
        self.new_group_panel.grid()
        self.new_group_entry.focus_set()

    def hide_new_group_form(self) -> None:
        self.new_group_entry.delete(0, "end")
        self.new_group_panel.grid_remove()

    def create_group(self) -> None:
        name = self.new_group_entry.get().strip()
        try:
            tournament_id = self.db.create_tournament(name)
        except ValueError as exc:
            messagebox.showerror("No se pudo crear", str(exc), parent=self)
            return
        tournament = self.db.get_tournament(tournament_id)
        self.hide_new_group_form()
        self.current_id, self.current_name = tournament_id, name
        self.current_school = tournament["school_name"]
        self.refresh_all()

    def select_group(self, tournament_id: int, name: str, school_name: str) -> None:
        self.current_id, self.current_name, self.current_school = tournament_id, name, school_name
        self.cancel_player_edit()
        self.refresh_all()

    def select_group_label(self, label: str) -> None:
        tournament = self.group_labels.get(label)
        if tournament is not None:
            self.select_group(int(tournament["id"]), tournament["name"], tournament["school_name"])

    def refresh_all(self) -> None:
        tournaments = self.db.list_tournaments()
        ids = {int(row["id"]) for row in tournaments}
        if self.current_id not in ids:
            if tournaments:
                self.current_id = int(tournaments[0]["id"])
                self.current_name = tournaments[0]["name"]
                self.current_school = tournaments[0]["school_name"]
            else:
                self.current_id, self.current_name = None, ""
                self.current_school = "CEIP Vista Alegre"
        self.group_labels = {}
        for row in tournaments:
            label = row["name"]
            while label in self.group_labels:
                label += "\u200b"
            self.group_labels[label] = row
        labels = list(self.group_labels) or ["Sin grupos"]
        self.pairing_group_menu.configure(values=labels)
        self.standings_group_menu.configure(values=labels)
        selected_label = next((label for label, row in self.group_labels.items() if row["id"] == self.current_id), labels[0])
        self.pairing_group_var.set(selected_label)
        self.standings_group_var.set(selected_label)
        total_players = sum(len(self.db.list_players(row["id"])) for row in tournaments)
        school_status = f"  ·  {self.current_school}" if self.current_id else ""
        self.global_status.configure(text=f"{len(tournaments)} grupos activos  ·  {total_players} alumnos{school_status}")
        self.refresh_group_list(tournaments)
        self.refresh_players()
        self.refresh_rounds()
        self.refresh_standings()

    def refresh_group_list(self, tournaments) -> None:
        for widget in self.groups_list.winfo_children():
            widget.destroy()
        for index, row in enumerate(tournaments):
            selected = row["id"] == self.current_id
            ctk.CTkButton(self.groups_list, text=row["name"], anchor="w",
                height=47, corner_radius=11, fg_color=PRIMARY if selected else "#E5EEF4",
                hover_color=PRIMARY_HOVER if selected else "#D2E2EB",
                text_color="white" if selected else TEXT, font=ctk.CTkFont(size=13, weight="bold"),
                command=lambda item=row: self.select_group(int(item["id"]), item["name"], item["school_name"])).grid(
                    row=index, column=0, sticky="ew", padx=3, pady=4)

    def refresh_players(self) -> None:
        self.players_tree.delete(*self.players_tree.get_children())
        enabled = self.current_id is not None
        self.players_title.configure(text=f"Alumnos · {self.current_name}" if enabled else "Selecciona o crea un grupo")
        players = self.db.list_players(self.current_id) if enabled else []
        self.players_count.configure(text=f"{self.current_school}  ·  {len(players)} participantes" if enabled else "")
        for player in players:
            self.players_tree.insert("", "end", iid=str(player["id"]), values=(
                f"{player['first_name']} {player['last_name']}", player["course"] or "-", player["center"] or "-"))
        state = "normal" if enabled else "disabled"
        self.player_submit.configure(state=state)

    def submit_player(self) -> None:
        if self.current_id is None:
            return
        values = {key: entry.get() for key, entry in self.player_entries.items()}
        try:
            if self.editing_player_id is None:
                self.db.add_player(self.current_id, **values)
            else:
                self.db.update_player(self.editing_player_id, **values)
        except ValueError as exc:
            messagebox.showerror("Datos incompletos", str(exc), parent=self)
            return
        self.cancel_player_edit()
        self.refresh_all()

    def import_students_excel(self) -> None:
        if self.current_id is None:
            messagebox.showinfo("Sin grupo", "Crea o selecciona un grupo antes de importar.", parent=self)
            return
        path = filedialog.askopenfilename(
            parent=self,
            title="Importar alumnos desde Excel",
            filetypes=[("Archivos de Excel", "*.xlsx *.xls"), ("Todos los archivos", "*.*")],
        )
        if not path:
            return
        try:
            students = read_student_rows(path)
            count = self.db.add_players_batch(self.current_id, students)
        except (OSError, ValueError) as exc:
            messagebox.showerror("No se pudo importar", str(exc), parent=self)
            return
        self.refresh_all()
        messagebox.showinfo(
            "Importación completada",
            f"Se han añadido {count} alumnos al grupo «{self.current_name}».",
            parent=self,
        )

    def start_player_edit(self) -> None:
        selected = self.players_tree.selection()
        if not selected:
            messagebox.showinfo("Editar", "Selecciona un alumno.", parent=self)
            return
        player_id = int(selected[0])
        player = next(row for row in self.db.list_players(self.current_id, False) if row["id"] == player_id)
        self.editing_player_id = player_id
        for key, entry in self.player_entries.items():
            entry.delete(0, "end")
            entry.insert(0, player[key])
        self.player_submit.configure(text="Guardar")
        self.player_cancel.grid()

    def cancel_player_edit(self) -> None:
        self.editing_player_id = None
        for entry in getattr(self, "player_entries", {}).values():
            entry.delete(0, "end")
        if hasattr(self, "player_submit"):
            self.player_submit.configure(text="Añadir")
            self.player_cancel.grid_remove()

    def remove_player(self) -> None:
        selected = self.players_tree.selection()
        if not selected:
            messagebox.showinfo("Retirar", "Selecciona un alumno.", parent=self)
            return
        if messagebox.askyesno("Retirar alumno", "¿Retirar al alumno seleccionado?", parent=self):
            self.db.remove_player(int(selected[0]))
            self.refresh_all()

    def backup_group(self) -> None:
        if self.current_id is None:
            messagebox.showinfo("Sin grupo", "Selecciona un grupo.", parent=self)
            return
        path = filedialog.asksaveasfilename(parent=self, title="Guardar copia del grupo",
            defaultextension=".openchess", filetypes=[("Copia de Open Chess", "*.openchess")],
            initialfile=f"{safe_name(self.current_name)}_copia.openchess")
        if path:
            try:
                self.db.export_tournament(self.current_id, path)
                messagebox.showinfo("Copia guardada", "El grupo completo se ha guardado correctamente.", parent=self)
            except (OSError, ValueError) as exc:
                messagebox.showerror("No se pudo guardar", str(exc), parent=self)

    def restore_group(self) -> None:
        path = filedialog.askopenfilename(parent=self, title="Restaurar grupo",
            filetypes=[("Copias de Open Chess", "*.openchess *.json"), ("Todos los archivos", "*.*")])
        if path:
            try:
                tournament_id = self.db.import_tournament(path)
                tournament = self.db.get_tournament(tournament_id)
                self.current_id, self.current_name = tournament_id, tournament["name"]
                self.current_school = tournament["school_name"]
                self.refresh_all()
                self.tabs.set("Grupos")
            except (OSError, ValueError) as exc:
                messagebox.showerror("No se pudo restaurar", str(exc), parent=self)

    def delete_group(self) -> None:
        if self.current_id is None:
            return
        message = (f"¿Eliminar definitivamente «{self.current_name}»?\n\n"
                   "Se borrarán sus alumnos, rondas y resultados. Esta acción no se puede deshacer.")
        if messagebox.askyesno("Eliminar grupo", message, parent=self):
            self.db.delete_tournament(self.current_id)
            self.current_id = None
            self.refresh_all()

    def refresh_rounds(self) -> None:
        current = self.db.current_round(self.current_id) if self.current_id else 0
        values = [str(value) for value in range(1, current + 1)] or ["0"]
        self.round_menu.configure(values=values)
        if self.round_var.get() not in values:
            self.round_var.set(values[-1])
        self.refresh_pairings()

    def refresh_pairings(self) -> None:
        self.pairings_tree.delete(*self.pairings_tree.get_children())
        self.score_hint.configure(text="Selecciona un emparejamiento de la lista")
        if self.current_id is None or self.round_var.get() == "0":
            return
        for pairing in self.db.get_round_pairings(self.current_id, int(self.round_var.get())):
            self.pairings_tree.insert("", "end", iid=str(pairing["id"]), values=(
                pairing["board"], pairing["white_name"], pairing["black_name"], pairing["result"] or "Pendiente"))

    def new_round(self) -> None:
        if self.current_id is None:
            messagebox.showinfo("Sin grupo", "Crea o selecciona un grupo.", parent=self)
            return
        current = self.db.current_round(self.current_id)
        if not self.db.round_is_complete(self.current_id, current):
            messagebox.showwarning("Ronda pendiente", "Completa todos los resultados de la ronda actual.", parent=self)
            return
        try:
            pairs = generate_pairings(self.db.list_players(self.current_id), self.db.pairing_history(self.current_id))
            self.db.create_round(self.current_id, pairs)
        except ValueError as exc:
            messagebox.showerror("No se pudo emparejar", str(exc), parent=self)
            return
        self.refresh_all()
        self.round_var.set(str(self.db.current_round(self.current_id)))
        self.refresh_pairings()

    def on_pairing_selected(self, _event=None) -> None:
        selected = self.pairings_tree.selection()
        if not selected:
            self.score_hint.configure(text="Selecciona un emparejamiento de la lista")
            return
        values = self.pairings_tree.item(selected[0])["values"]
        self.score_hint.configure(text=f"Mesa {values[0]}: {values[1]}  ·  {values[2]}")

    def score_selected(self, result: str) -> None:
        selected = self.pairings_tree.selection()
        if not selected:
            messagebox.showinfo("Resultado", "Selecciona una mesa.", parent=self)
            return
        selected_id = selected[0]
        children = list(self.pairings_tree.get_children())
        selected_index = children.index(selected_id)
        if self.pairings_tree.item(selected_id)["values"][2] == "DESCANSA":
            return
        next_id = next((item for item in children[selected_index + 1:]
                        if self.pairings_tree.item(item)["values"][2] != "DESCANSA"), None)
        self.db.set_result(int(selected_id), result)
        self.refresh_pairings()
        self.refresh_standings()
        if next_id is not None and self.pairings_tree.exists(next_id):
            self.pairings_tree.selection_set(next_id)
            self.pairings_tree.focus(next_id)
            self.pairings_tree.see(next_id)
        else:
            self.score_hint.configure(text="No hay más mesas debajo; revisa la ronda antes de continuar")

    def clear_selected_result(self) -> None:
        selected = self.pairings_tree.selection()
        if not selected:
            messagebox.showinfo("Dejar pendiente", "Selecciona una mesa.", parent=self)
            return
        selected_id = selected[0]
        if self.pairings_tree.item(selected_id)["values"][2] == "DESCANSA":
            return
        self.db.set_result(int(selected_id), "")
        self.refresh_pairings()
        self.refresh_standings()
        if self.pairings_tree.exists(selected_id):
            self.pairings_tree.selection_set(selected_id)
            self.pairings_tree.focus(selected_id)
            self.pairings_tree.see(selected_id)

    def refresh_standings(self) -> None:
        self.standings_tree.delete(*self.standings_tree.get_children())
        if self.current_id is None:
            return
        standings = calculate_standings(self.db.list_players(self.current_id), self.db.pairing_history(self.current_id))
        for pos, standing in enumerate(standings, 1):
            self.standings_tree.insert("", "end", values=(pos, standing.name, standing.course or "-",
                standing.center or "-", number(standing.points), number(standing.buchholz), standing.wins))

    def export_players_pdf(self) -> None:
        if self.current_id is None:
            return
        path = filedialog.asksaveasfilename(parent=self, defaultextension=".pdf",
            filetypes=[("Documento PDF", "*.pdf")], initialfile=f"{safe_name(self.current_name)}_participantes.pdf")
        if path:
            self._create_pdf(path, lambda: participants_pdf(
                path, f"{self.current_name} · {self.current_school}", self.db.list_players(self.current_id)))

    def export_pairings_pdf(self) -> None:
        if self.current_id is None or self.round_var.get() == "0":
            messagebox.showinfo("Sin rondas", "Genera una ronda antes de exportar.", parent=self)
            return
        round_number = int(self.round_var.get())
        path = filedialog.asksaveasfilename(parent=self, defaultextension=".pdf",
            filetypes=[("Documento PDF", "*.pdf")], initialfile=f"{safe_name(self.current_name)}_ronda_{round_number}.pdf")
        if path:
            self._create_pdf(path, lambda: pairings_pdf(path, f"{self.current_name} · {self.current_school}", round_number,
                                                        self.db.get_round_pairings(self.current_id, round_number)))

    def export_standings_pdf(self) -> None:
        if self.current_id is None:
            return
        path = filedialog.asksaveasfilename(parent=self, defaultextension=".pdf",
            filetypes=[("Documento PDF", "*.pdf")], initialfile=f"{safe_name(self.current_name)}_clasificacion.pdf")
        if path:
            self._create_pdf(path, lambda: standings_pdf(path, f"{self.current_name} · {self.current_school}",
                calculate_standings(self.db.list_players(self.current_id), self.db.pairing_history(self.current_id))))

    def _create_pdf(self, path: str, builder) -> None:
        try:
            builder()
            if messagebox.askyesno("PDF creado", "¿Quieres abrir el documento?", parent=self):
                open_file(path)
        except Exception as exc:
            messagebox.showerror("No se pudo crear el PDF", str(exc), parent=self)

    def on_close(self) -> None:
        self.db.close()
        self.destroy()


def main() -> None:
    OpenChessApp().mainloop()


if __name__ == "__main__":
    main()
