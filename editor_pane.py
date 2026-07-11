import tkinter as tk
import customtkinter as ctk

class CustomText(tk.Text):
    """
    A custom Tkinter Text widget that generates a <<Change>> event
    whenever characters are inserted or deleted, or when style actions occur.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Handle internal proxies to catch edit events
        self._orig = self._w + "_orig"
        self.tk.call("rename", self._w, self._orig)
        self.tk.createcommand(self._w, self._proxy)

    def _proxy(self, *args):
        # Avoid issues with deleted widget during teardown
        try:
            cmd = (self._orig,) + args
            result = self.tk.call(*cmd)
        except Exception:
            return ""

        # Trigger event on visual changes
        if args[0] in ("insert", "delete", "replace"):
            self.event_generate("<<Change>>", when="tail")

        return result

class EditorPane(ctk.CTkFrame):
    """
    Standard editor pane offering standard title input, auto-wrapped lines,
    distraction-free padded margins, word count tracking, and rich typing experience.
    """
    def __init__(self, master, on_change_callback=None, **kwargs):
        super().__init__(master, **kwargs)
        self.on_change_callback = on_change_callback
        self.current_node_id = None
        self.current_node_type = None

        self.configure(fg_color="#FFFFFF")  # Pure white background like Dabble

        # Content container with margins (simulating page width)
        self.page_container = ctk.CTkFrame(self, fg_color="#FFFFFF", corner_radius=0)
        self.page_container.pack(fill="both", expand=True, padx=40, pady=20)

        # Title Field
        self.title_var = tk.StringVar()
        self.title_entry = ctk.CTkEntry(
            self.page_container,
            textvariable=self.title_var,
            font=("Georgia", 28, "bold"),
            fg_color="#FFFFFF",
            border_width=0,
            text_color="#222222",
            placeholder_text="Enter Title..."
        )
        self.title_entry.pack(fill="x", pady=(10, 20))
        self.title_var.trace_add("write", self._on_title_changed)

        # Separator line
        self.sep = ctk.CTkFrame(self.page_container, height=1, fg_color="#E0E0E0")
        self.sep.pack(fill="x", pady=(0, 15))

        # Text Field (Standard rich look with Georgia/Times/Calibri size 13-14)
        self.text_widget = CustomText(
            self.page_container,
            font=("Georgia", 13),
            bg="#FFFFFF",
            fg="#2C2C2C",
            wrap="word",
            bd=0,
            highlightthickness=0,
            padx=10,
            pady=10,
            undo=True,
            insertbackground="#2C2C2C"
        )
        self.text_widget.pack(fill="both", expand=True)
        self.text_widget.bind("<<Change>>", self._on_content_changed)

        # Word count label at bottom right of the page
        self.stats_label = ctk.CTkLabel(
            self.page_container,
            text="0 words | 0 chars",
            font=("Helvetica", 11),
            text_color="#888888"
        )
        self.stats_label.pack(anchor="se", pady=(5, 0))

    def load_node(self, node_id, node_type, title, content):
        self.current_node_id = node_id
        self.current_node_type = node_type

        # Avoid tracing trigger during loading
        self.title_var.set(title)

        self.text_widget.delete("1.0", tk.END)
        self.text_widget.insert("1.0", content or "")

        self.update_stats()

    def update_stats(self):
        text_content = self.text_widget.get("1.0", tk.END).strip()
        if not text_content:
            words = 0
            chars = 0
        else:
            words = len(text_content.split())
            chars = len(text_content)
        self.stats_label.configure(text=f"{words} words | {chars} chars")
        return words, chars

    def _on_title_changed(self, *args):
        if self.on_change_callback and self.current_node_id:
            self.on_change_callback(self.current_node_id, self.current_node_type, "title", self.title_var.get())

    def _on_content_changed(self, event=None):
        if self.on_change_callback and self.current_node_id:
            content = self.text_widget.get("1.0", tk.END).rstrip("\n")
            self.on_change_callback(self.current_node_id, self.current_node_type, "content", content)
            self.update_stats()
