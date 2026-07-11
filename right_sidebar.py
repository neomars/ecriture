import tkinter as tk
import customtkinter as ctk

class RightSidebar(ctk.CTkFrame):
    """
    Combines daily progress tracking, word goals, customizable target visualizer,
    and a configurable focus Timer (with interactive control).
    """
    def __init__(self, master, on_goal_change_callback=None, **kwargs):
        super().__init__(master, **kwargs)
        self.on_goal_change_callback = on_goal_change_callback

        # Configuration options
        self.configure(fg_color="#F8F9FA", width=220)

        # Title Label
        self.header = ctk.CTkLabel(
            self, text="Goals & Stats", font=("Helvetica", 14, "bold"), text_color="#333333"
        )
        self.header.pack(fill="x", padx=15, pady=(15, 10))

        # Goal Inputs
        self.daily_goal_label = ctk.CTkLabel(self, text="Daily Word Goal:", font=("Helvetica", 11), text_color="#666666", anchor="w")
        self.daily_goal_label.pack(fill="x", padx=15)

        self.daily_goal_var = tk.StringVar(value="500")
        self.daily_goal_entry = ctk.CTkEntry(self, textvariable=self.daily_goal_var, font=("Helvetica", 12), height=25)
        self.daily_goal_entry.pack(fill="x", padx=15, pady=(2, 10))
        self.daily_goal_var.trace_add("write", self._on_goal_changed)

        # Progress Bars and counts
        self.daily_prog_lbl = ctk.CTkLabel(self, text="Daily: 0 / 500 words", font=("Helvetica", 11), text_color="#444444", anchor="w")
        self.daily_prog_lbl.pack(fill="x", padx=15)
        self.daily_progress_bar = ctk.CTkProgressBar(self, height=8, progress_color="#4CAF50")
        self.daily_progress_bar.pack(fill="x", padx=15, pady=(2, 15))
        self.daily_progress_bar.set(0)

        self.overall_prog_lbl = ctk.CTkLabel(self, text="Overall: 0 / 50000 words", font=("Helvetica", 11), text_color="#444444", anchor="w")
        self.overall_prog_lbl.pack(fill="x", padx=15)
        self.overall_progress_bar = ctk.CTkProgressBar(self, height=8, progress_color="#2196F3")
        self.overall_progress_bar.pack(fill="x", padx=15, pady=(2, 20))
        self.overall_progress_bar.set(0)

        # Separator
        self.sep = ctk.CTkFrame(self, height=1, fg_color="#E0E0E0")
        self.sep.pack(fill="x", padx=15, pady=10)

        # Timer Section
        self.timer_header = ctk.CTkLabel(
            self, text="Focus Timer", font=("Helvetica", 13, "bold"), text_color="#333333", anchor="w"
        )
        self.timer_header.pack(fill="x", padx=15, pady=(5, 5))

        self.timer_label = ctk.CTkLabel(
            self, text="15:00", font=("Consolas", 24, "bold"), text_color="#E91E63"
        )
        self.timer_label.pack(pady=5)

        # Time Configuration Slider/Buttons
        self.time_slider = ctk.CTkSlider(self, from_=1, to=60, number_of_steps=59, command=self._slider_changed)
        self.time_slider.pack(fill="x", padx=15, pady=5)
        self.time_slider.set(15)

        # Controls Frame
        self.ctrl_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.ctrl_frame.pack(fill="x", padx=15, pady=10)

        self.start_btn = ctk.CTkButton(
            self.ctrl_frame, text="Start", font=("Helvetica", 11, "bold"),
            fg_color="#4CAF50", hover_color="#45a049", height=25, width=60,
            command=self.toggle_timer
        )
        self.start_btn.pack(side="left", expand=True, padx=2)

        self.reset_btn = ctk.CTkButton(
            self.ctrl_frame, text="Reset", font=("Helvetica", 11),
            fg_color="#D0D0D0", hover_color="#C0C0C0", text_color="#333333", height=25, width=60,
            command=self.reset_timer
        )
        self.reset_btn.pack(side="right", expand=True, padx=2)

        # Internal Timer Variables
        self.time_remaining = 900  # seconds (15 mins default)
        self.timer_running = False
        self.timer_job = None

    def update_stats(self, daily_written, overall_written, daily_goal=None, overall_goal=50000):
        # Update labels & progress bars
        if daily_goal is None:
            try:
                daily_goal = int(self.daily_goal_var.get())
            except ValueError:
                daily_goal = 500

        self.daily_prog_lbl.configure(text=f"Daily: {daily_written} / {daily_goal} words")
        daily_ratio = daily_written / daily_goal if daily_goal > 0 else 0
        self.daily_progress_bar.set(min(1.0, daily_ratio))

        self.overall_prog_lbl.configure(text=f"Overall: {overall_written} / {overall_goal} words")
        overall_ratio = overall_written / overall_goal if overall_goal > 0 else 0
        self.overall_progress_bar.set(min(1.0, overall_ratio))

    def _on_goal_changed(self, *args):
        if self.on_goal_change_callback:
            try:
                val = int(self.daily_goal_var.get())
                self.on_goal_change_callback(val)
            except ValueError:
                pass

    def _slider_changed(self, value):
        if not self.timer_running:
            self.time_remaining = int(value) * 60
            self.update_timer_display()

    def update_timer_display(self):
        mins, secs = divmod(self.time_remaining, 60)
        self.timer_label.configure(text=f"{mins:02d}:{secs:02d}")

    def toggle_timer(self):
        if self.timer_running:
            self.timer_running = False
            self.start_btn.configure(text="Start", fg_color="#4CAF50", hover_color="#45a049")
            if self.timer_job:
                self.after_cancel(self.timer_job)
                self.timer_job = None
        else:
            self.timer_running = True
            self.start_btn.configure(text="Pause", fg_color="#FF9800", hover_color="#FB8C00")
            self.run_timer()

    def run_timer(self):
        if self.timer_running:
            if self.time_remaining > 0:
                self.time_remaining -= 1
                self.update_timer_display()
                self.timer_job = self.after(1000, self.run_timer)
            else:
                self.timer_running = False
                self.start_btn.configure(text="Start", fg_color="#4CAF50", hover_color="#45a049")
                self.timer_label.configure(text="00:00")
                # Trigger end of timer alert or visual change
                self.timer_label.configure(text_color="#4CAF50")
                self.after(2000, lambda: self.timer_label.configure(text_color="#E91E63"))

    def reset_timer(self):
        self.timer_running = False
        if self.timer_job:
            self.after_cancel(self.timer_job)
            self.timer_job = None
        self.start_btn.configure(text="Start", fg_color="#4CAF50", hover_color="#45a049")
        self.time_remaining = int(self.time_slider.get()) * 60
        self.update_timer_display()
