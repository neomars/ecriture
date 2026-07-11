import os
import sys
import tkinter as tk
from tkinter import messagebox, simpledialog
import customtkinter as ctk

from project_manager import NovelProject
from sidebar_tree import SidebarTree
from editor_pane import EditorPane
from right_sidebar import RightSidebar
from plot_grid_pane import PlotGridPane
from resource_pane import ResourcePane

class DabbleNovelistApp(ctk.CTk):
    """
    Main Novelist application frame bringing together standard multi-pane layout,
    auto-saving systems, and easy file import/export.
    """
    def __init__(self):
        super().__init__()

        # Setup standard app configurations
        self.title("Dabble Novelist Studio")
        self.geometry("1100x700")

        # Core active project
        self.project_path = "my_novel_project.json"
        self.project = NovelProject(self.project_path)

        # Set default UI Theme (Clean Light palette mimicking dabblewriter.com)
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")

        # Create Top Menu Bar
        self._create_menu_bar()

        # Build Layout container
        self.main_container = ctk.CTkFrame(self, fg_color="#F3F4F6", corner_radius=0)
        self.main_container.pack(fill="both", expand=True)

        # Left Sidebar (Hierarchical Structure Tree)
        self.left_sidebar = SidebarTree(
            self.main_container,
            project=self.project,
            on_select_callback=self._on_tree_select,
            on_action_callback=self._on_tree_action,
            width=260,
            corner_radius=0
        )
        self.left_sidebar.pack(side="left", fill="y")

        # Right Sidebar (Goals & Stats, focus timer)
        self.right_sidebar = RightSidebar(
            self.main_container,
            on_goal_change_callback=self._on_goal_change,
            width=220,
            corner_radius=0
        )
        self.right_sidebar.pack(side="right", fill="y")

        # Central Workspace Frame (Hosts current active view)
        self.workspace_frame = ctk.CTkFrame(self.main_container, fg_color="#FFFFFF", corner_radius=0)
        self.workspace_frame.pack(side="left", fill="both", expand=True)

        # Initialize the different specialized central panes
        self.editor_pane = EditorPane(
            self.workspace_frame,
            on_change_callback=self._on_editor_change
        )
        self.plot_grid_pane = PlotGridPane(
            self.workspace_frame,
            project=self.project
        )
        self.resource_pane = ResourcePane(
            self.workspace_frame,
            project=self.project,
            on_resource_change_callback=self._on_resource_change
        )

        # Load starting default active screen (Welcome or first scene)
        self.current_pane = None
        self._switch_pane(self.editor_pane)
        self._load_initial_scene()

        # Update initial progress & stats
        self._update_right_sidebar_stats()

    def _create_menu_bar(self):
        menubar = tk.Menu(self)

        # File Menu
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="New Project", command=self._new_project)
        file_menu.add_command(label="Open Project...", command=self._open_project)
        file_menu.add_command(label="Save Project", command=self._save_project)
        file_menu.add_separator()
        file_menu.add_command(label="Export as Text file...", command=self._export_project_text)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.quit)
        menubar.add_cascade(label="File", menu=file_menu)

        # Edit Menu
        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(label="Project Settings", command=self._open_project_settings)
        menubar.add_cascade(label="Edit", menu=edit_menu)

        # Help Menu
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="About", command=self._show_about)
        menubar.add_cascade(label="Help", menu=help_menu)

        self.config(menu=menubar)

    def _switch_pane(self, new_pane):
        if self.current_pane:
            self.current_pane.pack_forget()
        self.current_pane = new_pane
        self.current_pane.pack(fill="both", expand=True)

    def _load_initial_scene(self):
        # Load the very first scene if it exists
        if self.project.data["manuscript"]:
            first_chap = self.project.data["manuscript"][0]
            if first_chap["children"]:
                first_scene = first_chap["children"][0]
                self._load_scene_into_editor(first_scene["id"])
                return
        # Fallback view (plot grid)
        self._switch_pane(self.plot_grid_pane)

    def _load_scene_into_editor(self, scene_id):
        node = self.project.find_node(scene_id)
        if node:
            self._switch_pane(self.editor_pane)
            self.editor_pane.load_node(
                node_id=node["id"],
                node_type="scene",
                title=node["title"],
                content=node.get("content", "")
            )

    def _load_chapter_into_editor(self, chap_id):
        node = self.project.find_node(chap_id)
        if node:
            self._switch_pane(self.editor_pane)
            # Chapter contents can be modeled as summary text or overview of scene titles
            summary = "\n".join([f"- {scene['title']}" for scene in node["children"]])
            self.editor_pane.load_node(
                node_id=node["id"],
                node_type="chapter",
                title=node["title"],
                content=summary or "Add scenes to start drafting this chapter."
            )

    def _load_character_into_resource(self, char_id):
        for char in self.project.data["characters"]:
            if char["id"] == char_id:
                self._switch_pane(self.resource_pane)
                self.resource_pane.load_resource(char)
                break

    def _load_note_into_resource(self, note_id):
        for note in self.project.data["story_notes"]:
            if note["id"] == note_id:
                self._switch_pane(self.resource_pane)
                self.resource_pane.load_resource(note)
                break

    def _on_tree_select(self, node_id):
        if node_id == "PLOT_GRID":
            self._switch_pane(self.plot_grid_pane)
            self.plot_grid_pane.refresh_grid()
        elif node_id in ["MANUSCRIPT", "CHARACTERS_GROUP", "STORY_NOTES_GROUP"]:
            pass # header nodes
        elif node_id.startswith("chap_"):
            self._load_chapter_into_editor(node_id)
        elif node_id.startswith("scene_"):
            self._load_scene_into_editor(node_id)
        elif node_id.startswith("char_"):
            self._load_character_into_resource(node_id)
        elif node_id.startswith("note_"):
            self._load_note_into_resource(node_id)

    def _on_tree_action(self, action_type, node_id):
        if action_type == "add_chapter":
            title = simpledialog.askstring("Add Chapter", "Enter Chapter Name:", parent=self)
            if title:
                new_chap = self.project.add_chapter(title)
                self.left_sidebar.refresh_tree()
                self._load_chapter_into_editor(new_chap["id"])
                self._save_project()

        elif action_type == "add_scene":
            # Ensure we have a chapter to add to
            parent_id = node_id if (node_id and node_id.startswith("chap_")) else None
            if not parent_id and self.project.data["manuscript"]:
                parent_id = self.project.data["manuscript"][-1]["id"]

            if not parent_id:
                messagebox.showerror("Error", "Create a Chapter first!", parent=self)
                return

            title = simpledialog.askstring("Add Scene", "Enter Scene Name:", parent=self)
            if title:
                new_scene = self.project.add_scene(parent_id, title)
                self.left_sidebar.refresh_tree()
                self._load_scene_into_editor(new_scene["id"])
                self._save_project()

        elif action_type == "add_character":
            name = simpledialog.askstring("Add Character", "Enter Character Name:", parent=self)
            if name:
                new_char = {
                    "id": f"char_{int(os.urandom(3).hex(), 16)}",
                    "name": name,
                    "role": "Major Character",
                    "description": ""
                }
                self.project.data["characters"].append(new_char)
                self.left_sidebar.refresh_tree()
                self._load_character_into_resource(new_char["id"])
                self._save_project()

        elif action_type == "add_note":
            title = simpledialog.askstring("Add Story Note", "Enter Note Title:", parent=self)
            if title:
                new_note = {
                    "id": f"note_{int(os.urandom(3).hex(), 16)}",
                    "title": title,
                    "type": "General",
                    "content": ""
                }
                self.project.data["story_notes"].append(new_note)
                self.left_sidebar.refresh_tree()
                self._load_note_into_resource(new_note["id"])
                self._save_project()

        elif action_type == "rename":
            if not node_id or node_id in ["MANUSCRIPT", "CHARACTERS_GROUP", "STORY_NOTES_GROUP", "PLOT_GRID"]:
                return

            new_title = simpledialog.askstring("Rename", "Enter New Name:", parent=self)
            if new_title:
                node = self.project.find_node(node_id)
                if node:
                    node["title"] = new_title
                else:
                    # Search resources
                    for c in self.project.data["characters"]:
                        if c["id"] == node_id:
                            c["name"] = new_title
                    for n in self.project.data["story_notes"]:
                        if n["id"] == node_id:
                            n["title"] = new_title

                self.left_sidebar.refresh_tree()
                self._save_project()

        elif action_type == "delete":
            if not node_id or node_id in ["MANUSCRIPT", "CHARACTERS_GROUP", "STORY_NOTES_GROUP", "PLOT_GRID"]:
                return

            confirm = messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete this item?", parent=self)
            if confirm:
                deleted = self.project.delete_node(node_id)
                if not deleted:
                    # Delete resource
                    self.project.data["characters"] = [c for c in self.project.data["characters"] if c["id"] != node_id]
                    self.project.data["story_notes"] = [n for n in self.project.data["story_notes"] if n["id"] != node_id]

                self.left_sidebar.refresh_tree()
                self._load_initial_scene()
                self._save_project()

    def _on_editor_change(self, node_id, node_type, field, value):
        node = self.project.find_node(node_id)
        if node:
            node[field] = value
            if field == "title":
                self.left_sidebar.refresh_tree()
            self._update_right_sidebar_stats()
            # Perform elegant silent saving
            self._save_project()

    def _on_resource_change(self, updated_resource):
        # Already updated in-place via reference, just refresh & save
        self.left_sidebar.refresh_tree()
        self._save_project()

    def _on_goal_change(self, new_val):
        self.project.data["settings"]["daily_goal"] = new_val
        self._update_right_sidebar_stats()
        self._save_project()

    def _update_right_sidebar_stats(self):
        # Recount total project statistics
        self.project.recalculate_word_counts()
        overall = self.project.data["settings"]["overall_written"]
        daily_goal = self.project.data["settings"].get("daily_goal", 500)
        overall_goal = self.project.data["settings"].get("overall_goal", 50000)

        # Simple simulation: let's treat daily written as equal to overall written up to daily goal
        daily_written = min(daily_goal, overall)
        self.right_sidebar.update_stats(
            daily_written=daily_written,
            overall_written=overall,
            daily_goal=daily_goal,
            overall_goal=overall_goal
        )

    def _save_project(self):
        self.project.save()

    def _new_project(self):
        confirm = messagebox.askyesno("New Project", "Create a new project? Any unsaved changes will be lost.")
        if confirm:
            self.project.data = self.project.get_default_data()
            self.project.data["settings"]["title"] = "My Masterpiece"
            self.left_sidebar.update_project_title("My Masterpiece")
            self.left_sidebar.refresh_tree()
            self._load_initial_scene()
            self._save_project()

    def _open_project(self):
        # Simply re-read standard file
        self.project.load()
        self.left_sidebar.update_project_title(self.project.data["settings"]["title"])
        self.left_sidebar.refresh_tree()
        self._load_initial_scene()
        self._update_right_sidebar_stats()

    def _open_project_settings(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Project Settings")
        dialog.geometry("340x220")
        dialog.grab_set()

        lbl_title = ctk.CTkLabel(dialog, text="Novel Title:", font=("Helvetica", 11, "bold"))
        lbl_title.pack(anchor="w", padx=20, pady=(15, 2))
        entry_title = ctk.CTkEntry(dialog)
        entry_title.insert(0, self.project.data["settings"]["title"])
        entry_title.pack(fill="x", padx=20, pady=(0, 10))

        lbl_goal = ctk.CTkLabel(dialog, text="Overall Word Goal:", font=("Helvetica", 11, "bold"))
        lbl_goal.pack(anchor="w", padx=20, pady=(5, 2))
        entry_goal = ctk.CTkEntry(dialog)
        entry_goal.insert(0, str(self.project.data["settings"]["overall_goal"]))
        entry_goal.pack(fill="x", padx=20, pady=(0, 20))

        def save_settings():
            self.project.data["settings"]["title"] = entry_title.get()
            try:
                self.project.data["settings"]["overall_goal"] = int(entry_goal.get())
            except ValueError:
                pass

            self.left_sidebar.update_project_title(entry_title.get())
            self._update_right_sidebar_stats()
            self._save_project()
            dialog.destroy()

        btn = ctk.CTkButton(dialog, text="Save Settings", fg_color="#3B82F6", hover_color="#2563EB", command=save_settings)
        btn.pack(pady=5)

    def _export_project_text(self):
        # Compiles entire manuscript into a single standard .txt document
        output_file = "my_novel_draft.txt"
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(f"=== {self.project.data['settings']['title']} ===\n\n")
                for chap in self.project.data["manuscript"]:
                    f.write(f"\n--- {chap['title']} ---\n\n")
                    for scene in chap["children"]:
                        f.write(f"[{scene['title']}]\n")
                        f.write(f"{scene.get('content', '')}\n\n")
            messagebox.showinfo("Export Success", f"Successfully exported novel to '{output_file}'!")
        except Exception as e:
            messagebox.showerror("Export Failed", f"Could not export: {e}")

    def _show_about(self):
        messagebox.showinfo("About Dabble Novelist", "Dabble Novelist Studio v1.0\nA beautiful distraction-free story writing & planning platform inspired by Dabble.")

if __name__ == "__main__":
    app = DabbleNovelistApp()
    # Force complete window layout updates so sidebars are rendered accurately
    app.update()
    # Use normal state but maximize utilizing geometry to support all platforms
    app.geometry("1100x700")
    app.mainloop()
