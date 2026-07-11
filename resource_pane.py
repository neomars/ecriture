import tkinter as tk
import customtkinter as ctk

class ResourcePane(ctk.CTkFrame):
    """
    Sub-pane dedicated for editing Characters & Story Notes.
    Contains profile fields like Name/Title, Role/Type, Description/Content,
    and photo/note summaries.
    """
    def __init__(self, master, project, on_resource_change_callback=None, **kwargs):
        super().__init__(master, **kwargs)
        self.project = project
        self.on_resource_change_callback = on_resource_change_callback
        self.current_resource = None

        self.configure(fg_color="#FFFFFF")

        self.container = ctk.CTkFrame(self, fg_color="#FFFFFF")
        self.container.pack(fill="both", expand=True, padx=40, pady=20)

        # Name / Title Field
        self.name_lbl = ctk.CTkLabel(self.container, text="Name / Title", font=("Helvetica", 11, "bold"), text_color="#555555")
        self.name_lbl.pack(anchor="w")

        self.name_var = tk.StringVar()
        self.name_entry = ctk.CTkEntry(self.container, textvariable=self.name_var, font=("Georgia", 24, "bold"), fg_color="#FFFFFF", border_width=0, text_color="#222222")
        self.name_entry.pack(fill="x", pady=(0, 15))
        self.name_var.trace_add("write", self._on_field_changed)

        # Role / Type Field
        self.role_lbl = ctk.CTkLabel(self.container, text="Role / Note Type", font=("Helvetica", 11, "bold"), text_color="#555555")
        self.role_lbl.pack(anchor="w")

        self.role_var = tk.StringVar()
        self.role_entry = ctk.CTkEntry(self.container, textvariable=self.role_var, font=("Helvetica", 13), height=30)
        self.role_entry.pack(fill="x", pady=(0, 15))
        self.role_var.trace_add("write", self._on_field_changed)

        # Content / Biography Field
        self.desc_lbl = ctk.CTkLabel(self.container, text="Details / Biography", font=("Helvetica", 11, "bold"), text_color="#555555")
        self.desc_lbl.pack(anchor="w")

        self.desc_text = tk.Text(self.container, font=("Helvetica", 12), bg="#FFFFFF", fg="#2C2C2C", wrap="word", bd=1, relief="solid", padx=10, pady=10)
        self.desc_text.pack(fill="both", expand=True, pady=(0, 10))
        self.desc_text.bind("<KeyRelease>", self._on_desc_changed)

    def load_resource(self, resource_item):
        self.current_resource = resource_item

        # Determine fields depending on Character vs Note
        if "name" in resource_item:
            self.name_lbl.configure(text="Character Name")
            self.name_var.set(resource_item["name"])
            self.role_lbl.configure(text="Story Role")
            self.role_var.set(resource_item.get("role", ""))

            self.desc_lbl.configure(text="Biography & Trait details")
            self.desc_text.delete("1.0", tk.END)
            self.desc_text.insert("1.0", resource_item.get("description", ""))
        else:
            self.name_lbl.configure(text="Note Title")
            self.name_var.set(resource_item.get("title", ""))
            self.role_lbl.configure(text="Note Type (e.g. Location, Item, Event)")
            self.role_var.set(resource_item.get("type", ""))

            self.desc_lbl.configure(text="Note Description")
            self.desc_text.delete("1.0", tk.END)
            self.desc_text.insert("1.0", resource_item.get("content", ""))

    def _on_field_changed(self, *args):
        if not self.current_resource:
            return

        if "name" in self.current_resource:
            self.current_resource["name"] = self.name_var.get()
            self.current_resource["role"] = self.role_var.get()
        else:
            self.current_resource["title"] = self.name_var.get()
            self.current_resource["type"] = self.role_var.get()

        if self.on_resource_change_callback:
            self.on_resource_change_callback(self.current_resource)

    def _on_desc_changed(self, event=None):
        if not self.current_resource:
            return

        content = self.desc_text.get("1.0", tk.END).strip()
        if "name" in self.current_resource:
            self.current_resource["description"] = content
        else:
            self.current_resource["content"] = content

        if self.on_resource_change_callback:
            self.on_resource_change_callback(self.current_resource)
