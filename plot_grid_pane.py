import os
import tkinter as tk
import customtkinter as ctk

class PlotGridPane(ctk.CTkFrame):
    """
    Signature Dabble Plot Grid featuring horizontal lanes for plotlines
    (e.g., Romance, Scandal, Subplot) and columns corresponding to scenes,
    with custom card management (add/edit/delete cards).
    """
    def __init__(self, master, project, on_card_click_callback=None, **kwargs):
        super().__init__(master, **kwargs)
        self.project = project
        self.on_card_click_callback = on_card_click_callback

        self.configure(fg_color="#FFFFFF")

        # Scrollable Canvas container for grid structure
        self.canvas = tk.Canvas(self, bg="#FFFFFF", highlightthickness=0)
        self.v_scrollbar = ctk.CTkScrollbar(self, orientation="vertical", command=self.canvas.yview)
        self.h_scrollbar = ctk.CTkScrollbar(self, orientation="horizontal", command=self.canvas.xview)

        self.grid_frame = ctk.CTkFrame(self.canvas, fg_color="#FFFFFF")
        self.grid_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        self.canvas.create_window((0, 0), window=self.grid_frame, anchor="nw")
        self.canvas.configure(xscrollcommand=self.h_scrollbar.set, yscrollcommand=self.v_scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.v_scrollbar.pack(side="right", fill="y")
        self.h_scrollbar.pack(side="bottom", fill="x")

        self.refresh_grid()

    def refresh_grid(self):
        # Clear children of grid_frame
        for widget in self.grid_frame.winfo_children():
            widget.destroy()

        # Collect list of scenes from manuscript hierarchically
        scenes = []
        def gather_scenes(nodes):
            for n in nodes:
                if n["type"] == "scene":
                    scenes.append(n)
                elif "children" in n:
                    gather_scenes(n["children"])
        gather_scenes(self.project.data["manuscript"])

        # Layout Column Headers: Scenes
        lbl = ctk.CTkLabel(self.grid_frame, text="Plotlines / Scenes", font=("Helvetica", 12, "bold"), text_color="#333333")
        lbl.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        for c_idx, scene in enumerate(scenes):
            s_header = ctk.CTkFrame(self.grid_frame, fg_color="#E0F2F1", corner_radius=6, border_width=1, border_color="#B2DFDB")
            s_header.grid(row=0, column=c_idx + 1, padx=10, pady=10, sticky="nsew")

            s_title = ctk.CTkLabel(s_header, text=scene["title"], font=("Helvetica", 11, "bold"), text_color="#004D40", width=160, wraplength=140)
            s_title.pack(padx=10, pady=5)

        # Plotlines (Rows)
        plotlines = self.project.data["plot"]["plotlines"]
        for r_idx, pl in enumerate(plotlines):
            # Row header
            pl_header = ctk.CTkFrame(self.grid_frame, fg_color="#F3E5F5", corner_radius=6, border_width=1, border_color="#E1BEE7")
            pl_header.grid(row=r_idx + 1, column=0, padx=10, pady=5, sticky="nsew")

            pl_lbl = ctk.CTkLabel(pl_header, text=pl["title"], font=("Georgia", 12, "bold"), text_color="#4A148C", width=140, wraplength=130)
            pl_lbl.pack(padx=10, pady=15)

            # Cards for this plotline & scenes
            for c_idx, scene in enumerate(scenes):
                card = self.find_card(pl["id"], scene["id"])

                card_container = ctk.CTkFrame(self.grid_frame, fg_color="#FFFFFF", border_width=1, border_color="#E0E0E0", corner_radius=6, width=180, height=100)
                card_container.grid(row=r_idx + 1, column=c_idx + 1, padx=10, pady=5, sticky="nsew")
                card_container.grid_propagate(False)

                if card:
                    card_title_lbl = ctk.CTkLabel(card_container, text=card["title"], font=("Helvetica", 11, "bold"), text_color="#1A237E", wraplength=160)
                    card_title_lbl.pack(anchor="w", padx=8, pady=(8, 2))

                    card_desc_lbl = ctk.CTkLabel(card_container, text=card["content"], font=("Helvetica", 10), text_color="#555555", wraplength=160, anchor="nw", justify="left")
                    card_desc_lbl.pack(fill="both", expand=True, padx=8, pady=(0, 8))

                    # Double click to edit card
                    card_container.bind("<Double-Button-1>", lambda e, c=card: self.edit_card(c))
                    card_title_lbl.bind("<Double-Button-1>", lambda e, c=card: self.edit_card(c))
                    card_desc_lbl.bind("<Double-Button-1>", lambda e, c=card: self.edit_card(c))
                else:
                    # Place a quick '+' button or label to add a card
                    add_btn = ctk.CTkButton(
                        card_container, text="+ Add Card", font=("Helvetica", 10),
                        fg_color="transparent", hover_color="#EEEEEE", text_color="#888888",
                        command=lambda p_id=pl["id"], s_id=scene["id"]: self.add_card(p_id, s_id)
                    )
                    add_btn.pack(fill="both", expand=True)

    def find_card(self, plotline_id, scene_id):
        for card in self.project.data["plot"]["cards"]:
            if card["plotline_id"] == plotline_id and card["scene_id"] == scene_id:
                return card
        return None

    def add_card(self, plotline_id, scene_id):
        new_id = f"card_{int(tk.datetime.datetime.now().timestamp() * 1000)}" if hasattr(tk, 'datetime') else f"card_{int(os.urandom(3).hex(), 16)}"
        new_card = {
            "id": new_id,
            "plotline_id": plotline_id,
            "scene_id": scene_id,
            "title": "New Card",
            "content": "Describe details..."
        }
        self.project.data["plot"]["cards"].append(new_card)
        self.refresh_grid()
        self.edit_card(new_card)

    def edit_card(self, card):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Edit Plot Card")
        dialog.geometry("360x280")
        dialog.grab_set()

        lbl_t = ctk.CTkLabel(dialog, text="Card Title:", font=("Helvetica", 11, "bold"))
        lbl_t.pack(anchor="w", padx=15, pady=(15, 2))

        entry_t = ctk.CTkEntry(dialog, font=("Helvetica", 12))
        entry_t.insert(0, card["title"])
        entry_t.pack(fill="x", padx=15, pady=(0, 10))

        lbl_c = ctk.CTkLabel(dialog, text="Card Content:", font=("Helvetica", 11, "bold"))
        lbl_c.pack(anchor="w", padx=15, pady=(5, 2))

        text_c = tk.Text(dialog, font=("Helvetica", 11), height=5, wrap="word", bd=1, relief="solid")
        text_c.insert("1.0", card["content"])
        text_c.pack(fill="x", padx=15, pady=(0, 15))

        def save_card():
            card["title"] = entry_t.get()
            card["content"] = text_c.get("1.0", tk.END).strip()
            dialog.destroy()
            self.refresh_grid()

        def delete_card():
            self.project.data["plot"]["cards"].remove(card)
            dialog.destroy()
            self.refresh_grid()

        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(fill="x", padx=15)

        del_btn = ctk.CTkButton(btn_frame, text="Delete", fg_color="#F44336", hover_color="#D32F2F", command=delete_card, width=80)
        del_btn.pack(side="left")

        save_btn = ctk.CTkButton(btn_frame, text="Save", fg_color="#4CAF50", hover_color="#45a049", command=save_card, width=80)
        save_btn.pack(side="right")
