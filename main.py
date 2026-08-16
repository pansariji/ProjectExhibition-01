import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
import os
import subprocess
from PIL import Image, ImageTk

from server import Receiver
from client import Sender
from web_server import WebReceiver, WebSender, generate_qr_image
from utils import generate_passcode

class LocalDropApp:
    def __init__(self, root):
        self.root = root
        self.root.title("LocalDrop")
        self.root.geometry("460x600")
        self.root.resizable(False, False)
        
        # Variables to hold active instances
        self.receiver = None
        self.web_receiver = None
        self.sender = None
        self.web_sender = None
        
        # Styles
        style = ttk.Style()
        style.configure("TButton", font=("Arial", 11), padding=8)
        style.configure("Title.TLabel", font=("Arial", 24, "bold"))
        style.configure("Passcode.TLabel", font=("Courier", 32, "bold"), foreground="#2563eb")
        style.configure("URL.TLabel", font=("Courier", 11, "bold"), foreground="#059669")
        
        self.current_frame = None
        self.show_home_screen()

    def _switch_frame(self, new_frame_class, **kwargs):
        if self.current_frame is not None:
            self.current_frame.destroy()
        self.current_frame = new_frame_class(self.root, self, **kwargs)
        self.current_frame.pack(fill=tk.BOTH, expand=True)

    def show_home_screen(self):
        if self.receiver:
            self.receiver.stop()
            self.receiver = None
        if self.web_receiver:
            self.web_receiver.stop()
            self.web_receiver = None
        if self.sender:
            self.sender.cancel()
            self.sender = None
        if self.web_sender:
            self.web_sender.stop()
            self.web_sender = None
            
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
        lbl_title.pack(pady=(70, 10))
        
        lbl_subtitle = ttk.Label(self, text="P2P File & Folder Sharing", font=("Arial", 12))
        lbl_subtitle.pack(pady=(0, 40))
        
        btn_send = ttk.Button(self, text="Send File / Folder", command=self.controller.show_send_screen)
        btn_send.pack(fill=tk.X, padx=60, pady=12)
        
        btn_receive = ttk.Button(self, text="Receive File / Folder", command=self.controller.show_receive_screen)
        btn_receive.pack(fill=tk.X, padx=60, pady=12)

class ReceiveFrame(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        
        self.passcode = generate_passcode()
        self.received_filepath = None
        self.qr_photo = None
        
        btn_back = ttk.Button(self, text="← Back", command=self.controller.show_home_screen)
        btn_back.pack(anchor=tk.NW, padx=10, pady=10)
        
        # Notebook for modes
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 10))
        
        # Tab 1: QR Web Mode (Mobile Upload)
        self.tab_qr = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_qr, text="📱 Mobile (QR Code)")
        
        # Tab 2: Passcode Mode (Laptop)
        self.tab_pass = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_pass, text="💻 Laptop (Passcode)")
        
        self._setup_qr_tab()
        self._setup_passcode_tab()
        
        # Shared bottom progress & status
        bottom_frame = ttk.Frame(self)
        bottom_frame.pack(fill=tk.X, padx=20, pady=10)
        
        self.status_var = tk.StringVar(value="Select receive mode above")
        lbl_status = ttk.Label(bottom_frame, textvariable=self.status_var, font=("Arial", 10), wraplength=400, justify=tk.CENTER)
        lbl_status.pack(pady=4)
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(bottom_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X, pady=4)
        
        self.speed_var = tk.StringVar(value="")
        lbl_speed = ttk.Label(bottom_frame, textvariable=self.speed_var, font=("Arial", 9))
        lbl_speed.pack()
        
        self.btn_open = ttk.Button(bottom_frame, text="Show Received Item", command=self.open_file, state=tk.DISABLED)
        self.btn_open.pack(pady=6)
        
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)
        self._start_web_receiver()

    def _setup_qr_tab(self):
        lbl_inst = ttk.Label(self.tab_qr, text="Scan with phone camera to send files/folders to laptop:", font=("Arial", 10))
        lbl_inst.pack(pady=(12, 6))
        
        self.lbl_qr_image = ttk.Label(self.tab_qr)
        self.lbl_qr_image.pack(pady=4)
        
        self.url_var = tk.StringVar(value="Starting Web Server...")
        lbl_url = ttk.Label(self.tab_qr, textvariable=self.url_var, style="URL.TLabel")
        lbl_url.pack(pady=6)

    def _setup_passcode_tab(self):
        lbl_inst = ttk.Label(self.tab_pass, text="Tell the sender laptop to enter this passcode:", font=("Arial", 11))
        lbl_inst.pack(pady=(30, 10))
        
        lbl_pass = ttk.Label(self.tab_pass, text=self.passcode, style="Passcode.TLabel")
        lbl_pass.pack(pady=15)

    def _on_tab_changed(self, event):
        selected_index = self.notebook.index(self.notebook.select())
        if selected_index == 0:
            self._start_web_receiver()
        else:
            self._start_passcode_receiver()

    def _start_web_receiver(self):
        if self.controller.receiver:
            self.controller.receiver.stop()
            self.controller.receiver = None
            
        if not self.controller.web_receiver:
            self.controller.web_receiver = WebReceiver(
                port=8080,
                on_status_callback=self.update_status,
                on_progress_callback=self.update_progress,
                on_complete_callback=self.on_complete
            )
            self.controller.web_receiver.start()
            
        url = self.controller.web_receiver.url
        self.url_var.set(url)
        
        pil_img = generate_qr_image(url)
        if pil_img:
            self.qr_photo = ImageTk.PhotoImage(pil_img)
            self.lbl_qr_image.config(image=self.qr_photo)

    def _start_passcode_receiver(self):
        if self.controller.web_receiver:
            self.controller.web_receiver.stop()
            self.controller.web_receiver = None
            
        if not self.controller.receiver:
            self.controller.receiver = Receiver(
                passcode=self.passcode,
                on_status_callback=self.update_status,
                on_progress_callback=self.update_progress,
                on_complete_callback=self.on_complete
            )
            self.controller.receiver.start()

    def update_status(self, msg):
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
            system = subprocess.os.name
            if os.name == 'nt':
                subprocess.run(["explorer", "/select,", os.path.normpath(self.received_filepath)])
            else:
                subprocess.run(["xdg-open", self.received_filepath])


class SendFrame(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.filepath = None
        self.qr_photo = None
        
        btn_back = ttk.Button(self, text="← Back", command=self.controller.show_home_screen)
        btn_back.pack(anchor=tk.NW, padx=10, pady=10)
        
        # File / Folder selection buttons at top
        selection_frame = ttk.Frame(self)
        selection_frame.pack(pady=(0, 10))
        
        btn_select_file = ttk.Button(selection_frame, text="Select File", command=self.select_file)
        btn_select_file.pack(side=tk.LEFT, padx=5)
        
        btn_select_folder = ttk.Button(selection_frame, text="Select Folder", command=self.select_folder)
        btn_select_folder.pack(side=tk.LEFT, padx=5)
        
        self.lbl_file = ttk.Label(self, text="No file or folder selected", font=("Arial", 10), wraplength=400)
        self.lbl_file.pack(pady=4)
        
        # Notebook for Sending Modes
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=15, pady=5)
        
        # Tab 1: QR Code Mode (Mobile Download)
        self.tab_qr = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_qr, text="📱 Mobile (QR Code)")
        
        # Tab 2: Passcode Mode (Laptop Send)
        self.tab_pass = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_pass, text="💻 Laptop (Passcode)")
        
        self._setup_qr_tab()
        self._setup_passcode_tab()
        
        # Shared bottom progress & status
        bottom_frame = ttk.Frame(self)
        bottom_frame.pack(fill=tk.X, padx=20, pady=10)
        
        self.status_var = tk.StringVar(value="")
        lbl_status = ttk.Label(bottom_frame, textvariable=self.status_var, font=("Arial", 10), wraplength=400, justify=tk.CENTER)
        lbl_status.pack(pady=2)
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(bottom_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X, pady=2)
        
        self.speed_var = tk.StringVar(value="")
        lbl_speed = ttk.Label(bottom_frame, textvariable=self.speed_var, font=("Arial", 9))
        lbl_speed.pack()
        
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)

    def _setup_qr_tab(self):
        lbl_inst = ttk.Label(self.tab_qr, text="Scan with phone camera to download from laptop:", font=("Arial", 10))
        lbl_inst.pack(pady=(10, 4))
        
        self.lbl_qr_image = ttk.Label(self.tab_qr)
        self.lbl_qr_image.pack(pady=4)
        
        self.url_var = tk.StringVar(value="Select a file/folder above to share via QR Code")
        lbl_url = ttk.Label(self.tab_qr, textvariable=self.url_var, style="URL.TLabel", wraplength=380, justify=tk.CENTER)
        lbl_url.pack(pady=4)

    def _setup_passcode_tab(self):
        lbl_passcode_inst = ttk.Label(self.tab_pass, text="Enter Receiver Laptop's 4-digit Passcode:", font=("Arial", 11))
        lbl_passcode_inst.pack(pady=(20, 10))
        
        self.passcode_entry = ttk.Entry(self.tab_pass, font=("Courier", 18), width=8, justify=tk.CENTER)
        self.passcode_entry.pack(pady=5)
        
        self.btn_send = ttk.Button(self.tab_pass, text="Send Now", command=self.start_passcode_send, state=tk.DISABLED)
        self.btn_send.pack(pady=15)

    def select_file(self):
        path = filedialog.askopenfilename(parent=self.controller.root)
        if path:
            self.filepath = path
            filename = os.path.basename(path)
            self.lbl_file.config(text=f"Selected File: {filename}")
            self.btn_send.config(state=tk.NORMAL)
            self._update_web_sender_if_active()

    def select_folder(self):
        path = filedialog.askdirectory(parent=self.controller.root)
        if path:
            self.filepath = path
            foldername = os.path.basename(path) or path
            self.lbl_file.config(text=f"Selected Folder: {foldername}")
            self.btn_send.config(state=tk.NORMAL)
            self._update_web_sender_if_active()

    def _on_tab_changed(self, event):
        selected_index = self.notebook.index(self.notebook.select())
        if selected_index == 0:
            # QR Tab active
            if self.controller.sender:
                self.controller.sender.cancel()
                self.controller.sender = None
            self._update_web_sender_if_active()
        else:
            # Passcode Tab active
            if self.controller.web_sender:
                self.controller.web_sender.stop()
                self.controller.web_sender = None
            self.lbl_qr_image.config(image="")
            self.url_var.set("Switched to Laptop Passcode Mode")

    def _update_web_sender_if_active(self):
        if not self.filepath:
            self.url_var.set("Select a file or folder above to share via QR Code")
            return
            
        selected_index = self.notebook.index(self.notebook.select())
        if selected_index != 0:
            return

        if self.controller.web_sender:
            self.controller.web_sender.stop()
            self.controller.web_sender = None

        self.url_var.set("Generating QR Code...")
        self.update_idletasks()

        self.controller.web_sender = WebSender(
            shared_path=self.filepath,
            port=8080,
            on_status_callback=self.update_status,
            on_progress_callback=self.update_progress,
            on_complete_callback=self.on_complete
        )
        self.controller.web_sender.start()
        
        url = self.controller.web_sender.url
        self.url_var.set(url)
        
        pil_img = generate_qr_image(url)
        if pil_img:
            self.qr_photo = ImageTk.PhotoImage(pil_img)
            self.lbl_qr_image.config(image=self.qr_photo)

    def start_passcode_send(self):
        passcode = self.passcode_entry.get().strip()
        if len(passcode) != 4 or not passcode.isdigit():
            messagebox.showerror("Error", "Passcode must be a 4-digit number.")
            return
            
        if not self.filepath:
            messagebox.showerror("Error", "Please select a file or folder first.")
            return
            
        self.btn_send.config(state=tk.DISABLED)
        self.passcode_entry.config(state=tk.DISABLED)
        
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
