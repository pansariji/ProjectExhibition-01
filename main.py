import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
import os
import subprocess

from server import Receiver
from client import Sender
from utils import generate_passcode

class LocalDropApp:
    def __init__(self, root):
        self.root = root
        self.root.title("LocalDrop")
        self.root.geometry("400x500")
        self.root.resizable(False, False)
        
        # Variables to hold active instances
        self.receiver = None
        self.sender = None
        
        # Styles
        style = ttk.Style()
        style.configure("TButton", font=("Arial", 12), padding=10)
        style.configure("Title.TLabel", font=("Arial", 24, "bold"))
        style.configure("Passcode.TLabel", font=("Courier", 36, "bold"), foreground="blue")
        
        self.current_frame = None
        self.show_home_screen()

    def _switch_frame(self, new_frame_class, **kwargs):
        if self.current_frame is not None:
            self.current_frame.destroy()
        self.current_frame = new_frame_class(self.root, self, **kwargs)
        self.current_frame.pack(fill=tk.BOTH, expand=True)

    def show_home_screen(self):
        # Stop any active transfers if going back home
        if self.receiver:
            self.receiver.stop()
            self.receiver = None
        if self.sender:
            self.sender.cancel()
            self.sender = None
            
        self._switch_frame(HomeFrame)

    def show_receive_screen(self):
        self._switch_frame(ReceiveFrame)

    def show_send_screen(self):
        self._switch_frame(SendFrame)

class HomeFrame(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        
        lbl_title = ttk.Label(self, text="LocalDrop", style="Title.TLabel")
        lbl_title.pack(pady=(60, 20))
        
        lbl_subtitle = ttk.Label(self, text="P2P Local Network File Sharing", font=("Arial", 12))
        lbl_subtitle.pack(pady=(0, 40))
        
        btn_send = ttk.Button(self, text="Send Files", command=self.controller.show_send_screen)
        btn_send.pack(fill=tk.X, padx=50, pady=10)
        
        btn_receive = ttk.Button(self, text="Receive Files", command=self.controller.show_receive_screen)
        btn_receive.pack(fill=tk.X, padx=50, pady=10)

class ReceiveFrame(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        
        self.passcode = generate_passcode()
        
        btn_back = ttk.Button(self, text="← Back", command=self.controller.show_home_screen)
        btn_back.pack(anchor=tk.NW, padx=10, pady=10)
        
        lbl_title = ttk.Label(self, text="Receive Mode", font=("Arial", 18))
        lbl_title.pack(pady=(10, 20))
        
        lbl_inst = ttk.Label(self, text="Tell the sender to enter this passcode:", font=("Arial", 12))
        lbl_inst.pack()
        
        lbl_passcode = ttk.Label(self, text=self.passcode, style="Passcode.TLabel")
        lbl_passcode.pack(pady=20)
        
        self.status_var = tk.StringVar()
        self.status_var.set("Starting server...")
        lbl_status = ttk.Label(self, textvariable=self.status_var, font=("Arial", 10), wraplength=350, justify=tk.CENTER)
        lbl_status.pack(pady=10)
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(self, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X, padx=30, pady=10)
        
        self.speed_var = tk.StringVar()
        self.speed_var.set("")
        lbl_speed = ttk.Label(self, textvariable=self.speed_var, font=("Arial", 10))
        lbl_speed.pack()
        
        self.received_filepath = None
        self.btn_open = ttk.Button(self, text="Show File in Finder", command=self.open_file, state=tk.DISABLED)
        self.btn_open.pack(pady=10)
        
        # Initialize and start receiver
        self.controller.receiver = Receiver(
            passcode=self.passcode,
            on_status_callback=self.update_status,
            on_progress_callback=self.update_progress,
            on_complete_callback=self.on_complete
        )
        self.controller.receiver.start()

    def update_status(self, msg):
        # Use root.after to safely update GUI from a background thread
        self.controller.root.after(0, lambda: self.status_var.set(msg))

    def update_progress(self, percent, speed_str):
        self.controller.root.after(0, lambda: self.progress_var.set(percent))
        self.controller.root.after(0, lambda: self.speed_var.set(speed_str))
        
    def on_complete(self, success, filepath=None):
        def reset_ui():
            if success and filepath:
                self.received_filepath = filepath
                self.btn_open.config(state=tk.NORMAL)
        self.controller.root.after(0, reset_ui)

    def open_file(self):
        if self.received_filepath and os.path.exists(self.received_filepath):
            import platform
            system = platform.system()
            if system == "Darwin": # macOS
                subprocess.run(["open", "-R", self.received_filepath])
            elif system == "Windows":
                # On Windows, open explorer with the file selected
                subprocess.run(["explorer", "/select,", os.path.normpath(self.received_filepath)])
            else: # Linux and others
                # On Linux, open the containing directory
                subprocess.run(["xdg-open", os.path.dirname(self.received_filepath)])

class SendFrame(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        
        self.filepath = None
        
        btn_back = ttk.Button(self, text="← Back", command=self.controller.show_home_screen)
        btn_back.pack(anchor=tk.NW, padx=10, pady=10)
        
        lbl_title = ttk.Label(self, text="Send Mode", font=("Arial", 18))
        lbl_title.pack(pady=(10, 20))
        
        self.lbl_file = ttk.Label(self, text="No file selected", font=("Arial", 10), wraplength=350)
        self.lbl_file.pack(pady=5)
        
        btn_select = ttk.Button(self, text="Select File", command=self.select_file)
        btn_select.pack(pady=10)
        
        lbl_pass_inst = ttk.Label(self, text="Enter Receiver's Passcode:", font=("Arial", 12))
        lbl_pass_inst.pack(pady=(20, 5))
        
        self.passcode_entry = ttk.Entry(self, font=("Arial", 24), width=6, justify=tk.CENTER)
        self.passcode_entry.pack(pady=5)
        
        self.btn_send = ttk.Button(self, text="Send", command=self.start_send, state=tk.DISABLED)
        self.btn_send.pack(pady=20)
        
        self.status_var = tk.StringVar()
        self.status_var.set("Ready.")
        lbl_status = ttk.Label(self, textvariable=self.status_var, font=("Arial", 10), wraplength=350, justify=tk.CENTER)
        lbl_status.pack(pady=5)
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(self, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X, padx=30, pady=10)
        
        self.speed_var = tk.StringVar()
        self.speed_var.set("")
        lbl_speed = ttk.Label(self, textvariable=self.speed_var, font=("Arial", 10))
        lbl_speed.pack()

    def select_file(self):
        path = filedialog.askopenfilename(parent=self.controller.root)
        if path:
            self.filepath = path
            filename = os.path.basename(path)
            self.lbl_file.config(text=f"Selected: {filename}")
            self.btn_send.config(state=tk.NORMAL)

    def start_send(self):
        passcode = self.passcode_entry.get().strip()
        if len(passcode) != 4 or not passcode.isdigit():
            messagebox.showerror("Error", "Passcode must be a 4-digit number.")
            return
            
        if not self.filepath:
            return
            
        self.btn_send.config(state=tk.DISABLED)
        self.passcode_entry.config(state=tk.DISABLED)
        
        # Initialize and start sender
        self.controller.sender = Sender(
            on_status_callback=self.update_status,
            on_progress_callback=self.update_progress,
            on_complete_callback=self.on_complete
        )
        self.controller.sender.discover_and_send(self.filepath, passcode)

    def update_status(self, msg):
        self.controller.root.after(0, lambda: self.status_var.set(msg))

    def update_progress(self, percent, speed_str):
        self.controller.root.after(0, lambda: self.progress_var.set(percent))
        self.controller.root.after(0, lambda: self.speed_var.set(speed_str))
        
    def on_complete(self, success):
        def reset_ui():
            self.btn_send.config(state=tk.NORMAL)
            self.passcode_entry.config(state=tk.NORMAL)
        self.controller.root.after(0, reset_ui)


if __name__ == "__main__":
    root = tk.Tk()
    app = LocalDropApp(root)
    root.mainloop()
