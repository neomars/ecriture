import tkinter as tk
from tkinter import ttk
import customtkinter as ctk

class SidebarTree(ctk.CTkFrame):
    """
    Left-hand sidebar tree list showcasing folders, chapters, scenes,
    characters, and story notes. Includes standard filters/search bar and
    interactive nodes to navigate the app layout.
    """
    def __init__(self, master, project, on_select_callback=None, on_action_callback=None, **kwargs):
        super().__init__(master, **kwargs)
        self.project = project
        self.on_select_callback = on_select_callback
        self.on_action_callback = on_action_callback

        self.configure(fg_color="#F8F9FA", width=260)

        # App/Project Header
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.pack(fill="x", padx=10, pady=(15, 5))

        self.title_lbl = ctk.CTkLabel(
            self.header_frame, text=self.project.data["settings"]["title"],
            font=("Georgia", 15, "bold"), text_color="#1F2937", anchor="w"
        )
        self.title_lbl.pack(side="left", fill="x", expand=True)

        # Search/Filter
        self.search_var = tk.StringVar()
        self.search_entry = ctk.CTkEntry(
            self, textvariable=self.search_var, placeholder_text="Filter project files...",
            font=("Helvetica", 11), height=25
        )
        self.search_entry.pack(fill="x", padx=10, pady=(5, 10))
        self.search_var.trace_add("write", self._filter_tree)

        # Treeview setup (using standard ttk treeview styled elegantly)
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Custom.Treeview",
            background="#F8F9FA",
            foreground="#374151",
            rowheight=24,
            fieldbackground="#F8F9FA",
            font=("Helvetica", 10),
            borderwidth=0
        )
        style.map(
            "Custom.Treeview",
            background=[("selected", "#E5E7EB")],
            foreground=[("selected", "#111827")]
        )

        self.tree = ttk.Treeview(self, show="tree", style="Custom.Treeview")
        self.tree.pack(fill="both", expand=True, padx=5, pady=5)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        # Context Menu for right click
        self.context_menu = tk.Menu(self, tearoff=0, bg="#FFFFFF", fg="#333333", activebackground="#E5E7EB", activeforeground="#000000")
        self.context_menu.add_command(label="Add Chapter", command=lambda: self._trigger_action("add_chapter"))
        self.context_menu.add_command(label="Add Scene", command=lambda: self._trigger_action("add_scene"))
        self.context_menu.add_command(label="Add Character", command=lambda: self._trigger_action("add_character"))
        self.context_menu.add_command(label="Add Story Note", command=lambda: self._trigger_action("add_note"))
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Rename", command=lambda: self._trigger_action("rename"))
        self.context_menu.add_command(label="Delete", command=lambda: self._trigger_action("delete"))

        self.tree.bind("<Button-3>", self._show_context_menu)
        self.tree.bind("<Button-2>", self._show_context_menu) # support macOS right click

        # Footer Action buttons (quick-access)
        self.footer = ctk.CTkFrame(self, fg_color="transparent")
        self.footer.pack(fill="x", padx=10, pady=10)

        self.add_chap_btn = ctk.CTkButton(
            self.footer, text="+ Chapter", font=("Helvetica", 10, "bold"),
            fg_color="#3B82F6", hover_color="#2563EB", text_color="#FFFFFF", height=24, width=65,
            command=lambda: self._trigger_action("add_chapter")
        )
        self.add_chap_btn.pack(side="left", padx=2, expand=True)

        self.add_scene_btn = ctk.CTkButton(
            self.footer, text="+ Scene", font=("Helvetica", 10, "bold"),
            fg_color="#10B981", hover_color="#059669", text_color="#FFFFFF", height=24, width=65,
            command=lambda: self._trigger_action("add_scene")
        )
        self.add_scene_btn.pack(side="left", padx=2, expand=True)

        self.add_res_btn = ctk.CTkButton(
            self.footer, text="+ Asset", font=("Helvetica", 10, "bold"),
            fg_color="#8B5CF6", hover_color="#7C3AED", text_color="#FFFFFF", height=24, width=65,
            command=self._quick_asset_dialog
        )
        self.add_res_btn.pack(side="left", padx=2, expand=True)

        self.refresh_tree()

    def update_project_title(self, new_title):
        self.title_lbl.configure(text=new_title)

    def refresh_tree(self):
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Filter query
        query = self.search_var.get().lower()

        # Core Node 1: MANUSCRIPT
        man_node = self.tree.insert("", "end", iid="MANUSCRIPT", text="MANUSCRIPT", open=True)
        # Always add overall Plot Grid representation
        self.tree.insert("", "end", iid="PLOT_GRID", text="📖 Plot Grid")

        # Load Chapter & Scenes
        for chap in self.project.data["manuscript"]:
            if query and query not in chap["title"].lower() and not any(query in sc["title"].lower() for sc in chap["children"]):
                continue

            chap_node = self.tree.insert(man_node, "end", iid=chap["id"], text=f"📁 {chap['title']}", open=True)
            for scene in chap["children"]:
                if query and query not in scene["title"].lower():
                    continue
                self.tree.insert(chap_node, "end", iid=scene["id"], text=f"📄 {scene['title']}")

        # Core Node 2: CHARACTERS
        char_node = self.tree.insert("", "end", iid="CHARACTERS_GROUP", text="CHARACTERS", open=True)
        for char in self.project.data["characters"]:
            if query and query not in char["name"].lower():
                continue
            self.tree.insert(char_node, "end", iid=char["id"], text=f"👤 {char['name']}")

        # Core Node 3: STORY NOTES
        notes_node = self.tree.insert("", "end", iid="STORY_NOTES_GROUP", text="STORY NOTES", open=True)
        for note in self.project.data["story_notes"]:
            if query and query not in note["title"].lower():
                continue
            self.tree.insert(notes_node, "end", iid=note["id"], text=f"📌 {note['title']}")

    def _filter_tree(self, *args):
        self.refresh_tree()

    def _on_select(self, event):
        selected = self.tree.selection()
        if not selected:
            return
        node_id = selected[0]
        if self.on_select_callback:
            self.on_select_callback(node_id)

    def _show_context_menu(self, event):
        iid = self.tree.identify_row(event.y)
        if iid:
            self.tree.selection_set(iid)
            self.context_menu.post(event.x_root, event.y_root)

    def _trigger_action(self, action_type):
        selected = self.tree.selection()
        selected_id = selected[0] if selected else None
        if self.on_action_callback:
            self.on_action_callback(action_type, selected_id)

    def _quick_asset_dialog(self):
        # Displays a neat quick asset creation popup
        dialog = ctk.CTkToplevel(self)
        dialog.title("Add New Asset")
        dialog.geometry("260x150")
        dialog.grab_set()

        lbl = ctk.CTkLabel(dialog, text="Select asset type to create:", font=("Helvetica", 11, "bold"))
        lbl.pack(pady=15)

        btn_char = ctk.CTkButton(
            dialog, text="Character", fg_color="#8B5CF6", hover_color="#7C3AED",
            command=lambda: [self._trigger_action("add_character"), dialog.destroy()]
        )
        btn_char.pack(pady=5, fill="x", padx=30)

        btn_note = ctk.CTkButton(
            dialog, text="Story Note", fg_color="#10B981", hover_color="#059669",
            command=lambda: [self._trigger_action("add_note"), dialog.destroy()]
        )
        btn_note.pack(pady=5, fill="x", padx=30)
