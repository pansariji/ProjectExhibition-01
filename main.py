import customtkinter as ctk
from PIL import Image
import os
import subprocess
from tkinter import filedialog, messagebox

from server import Receiver
from client import Sender
from web_server import WebReceiver, WebSender, generate_qr_image
from utils import generate_passcode

# Set global CustomTkinter appearance and theme
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class LocalDropApp:
    def __init__(self, root):
        self.root = root
        self.root.title("LocalDrop")
        self.root.geometry("480x660")
        self.root.resizable(False, False)
        
        # Active instances
        self.receiver = None
        self.web_receiver = None
        self.sender = None
        self.web_sender = None
        
        self.current_frame = None
        self.show_home_screen()

    def _switch_frame(self, new_frame_class, **kwargs):
        if self.current_frame is not None:
            self.current_frame.destroy()
        self.current_frame = new_frame_class(self.root, self, **kwargs)
        self.current_frame.pack(fill="both", expand=True)

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

class HomeFrame(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="transparent")
        self.controller = controller
        
        # Title Card
        title_card = ctk.CTkFrame(self, corner_radius=20, fg_color=("#1e293b", "#1e293b"))
        title_card.pack(fill="x", padx=30, pady=(60, 30))
        
        lbl_title = ctk.CTkLabel(
            title_card, 
            text="LocalDrop", 
            font=ctk.CTkFont(size=32, weight="bold"),
            text_color="#38bdf8"
        )
        lbl_title.pack(pady=(25, 5))
        
        lbl_subtitle = ctk.CTkLabel(
            title_card, 
            text="Cross-Device File & Folder Sharing", 
            font=ctk.CTkFont(size=14),
            text_color="#94a3b8"
        )
        lbl_subtitle.pack(pady=(0, 25))
        
        # Action Buttons
        btn_send = ctk.CTkButton(
            self,
            text="📤  Send File or Folder",
            font=ctk.CTkFont(size=16, weight="bold"),
            height=54,
            corner_radius=14,
            fg_color="#2563eb",
            hover_color="#1d4ed8",
            command=self.controller.show_send_screen
        )
        btn_send.pack(fill="x", padx=40, pady=12)
        
        btn_receive = ctk.CTkButton(
            self,
            text="📥  Receive File or Folder",
            font=ctk.CTkFont(size=16, weight="bold"),
            height=54,
            corner_radius=14,
            fg_color="#0d9488",
            hover_color="#0f766e",
            command=self.controller.show_receive_screen
        )
        btn_receive.pack(fill="x", padx=40, pady=12)

        # Footer info
        lbl_info = ctk.CTkLabel(
            self, 
            text="No internet required • Ultra-fast LAN speeds", 
            font=ctk.CTkFont(size=12),
            text_color="#64748b"
        )
        lbl_info.pack(side="bottom", pady=25)


class ReceiveFrame(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="transparent")
        self.controller = controller
        
        self.passcode = generate_passcode()
        self.received_filepath = None
        self.ctk_qr_img = None
        
        # Top Bar
        top_bar = ctk.CTkFrame(self, fg_color="transparent")
        top_bar.pack(fill="x", padx=15, pady=(15, 5))
        
        btn_back = ctk.CTkButton(
            top_bar, 
            text="← Back", 
            width=80,
            height=32,
            corner_radius=10,
            fg_color="#334155",
            hover_color="#475569",
            command=self.controller.show_home_screen
        )
        btn_back.pack(side="left")
        
        lbl_header = ctk.CTkLabel(
            top_bar, 
            text="Receive Mode", 
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#f8fafc"
        )
        lbl_header.pack(side="left", padx=20)
        
        # Segmented Tab View
        self.tabview = ctk.CTkTabview(self, corner_radius=16)
        self.tabview.pack(fill="both", expand=True, padx=15, pady=5)
        
        self.tab_qr = self.tabview.add("📱 Mobile (QR Code)")
        self.tab_pass = self.tabview.add("💻 Laptop (Passcode)")
        
        self._setup_qr_tab()
        self._setup_passcode_tab()
        
        # Bottom Status Panel
        self.status_card = ctk.CTkFrame(self, corner_radius=16, fg_color=("#1e293b", "#1e293b"))
        self.status_card.pack(fill="x", padx=15, pady=(5, 15))
        
        self.status_var = ctk.StringVar(value="Select receive mode above")
        lbl_status = ctk.CTkLabel(
            self.status_card, 
            textvariable=self.status_var, 
            font=ctk.CTkFont(size=13),
            wraplength=420
        )
        lbl_status.pack(pady=(12, 4))
        
        self.progress_bar = ctk.CTkProgressBar(self.status_card, height=10, corner_radius=5)
        self.progress_bar.pack(fill="x", padx=20, pady=4)
        self.progress_bar.set(0)
        
        self.speed_var = ctk.StringVar(value="")
        lbl_speed = ctk.CTkLabel(
            self.status_card, 
            textvariable=self.speed_var, 
            font=ctk.CTkFont(size=12),
            text_color="#38bdf8"
        )
        lbl_speed.pack(pady=(0, 4))
        
        self.btn_open = ctk.CTkButton(
            self.status_card, 
            text="Show Received Item", 
            height=36,
            corner_radius=10,
            fg_color="#059669",
            hover_color="#047857",
            command=self.open_file, 
            state="disabled"
        )
        self.btn_open.pack(pady=(4, 12))
        
        self.tabview.configure(command=self._on_tab_changed)
        self._start_web_receiver()

    def _setup_qr_tab(self):
        lbl_inst = ctk.CTkLabel(
            self.tab_qr, 
            text="Scan with phone camera to upload files/folders:", 
            font=ctk.CTkFont(size=13),
            text_color="#94a3b8"
        )
        lbl_inst.pack(pady=(10, 5))
        
        self.qr_card = ctk.CTkFrame(self.tab_qr, corner_radius=14, fg_color="#ffffff", width=210, height=210)
        self.qr_card.pack(pady=5)
        self.qr_card.pack_propagate(False)
        
        self.lbl_qr_image = ctk.CTkLabel(self.qr_card, text="")
        self.lbl_qr_image.pack(expand=True)
        
        self.url_var = ctk.StringVar(value="Starting Web Server...")
        lbl_url = ctk.CTkLabel(
            self.tab_qr, 
            textvariable=self.url_var, 
            font=ctk.CTkFont(family="Courier", size=13, weight="bold"),
            text_color="#10b981"
        )
        lbl_url.pack(pady=8)

    def _setup_passcode_tab(self):
        lbl_inst = ctk.CTkLabel(
            self.tab_pass, 
            text="Tell the sender laptop to enter this passcode:", 
            font=ctk.CTkFont(size=14),
            text_color="#94a3b8"
        )
        lbl_inst.pack(pady=(40, 15))
        
        pass_card = ctk.CTkFrame(self.tab_pass, corner_radius=16, fg_color=("#0f172a", "#0f172a"))
        pass_card.pack(padx=40, pady=10)
        
        lbl_pass = ctk.CTkLabel(
            pass_card, 
            text=self.passcode, 
            font=ctk.CTkFont(family="Courier", size=42, weight="bold"),
            text_color="#38bdf8"
        )
        lbl_pass.pack(padx=35, pady=20)

    def _on_tab_changed(self):
        selected_tab = self.tabview.get()
        if "Mobile" in selected_tab:
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
            self.ctk_qr_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(190, 190))
            self.lbl_qr_image.configure(image=self.ctk_qr_img)

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
        self.controller.root.after(0, lambda: self.progress_bar.set(percent / 100.0))
        self.controller.root.after(0, lambda: self.speed_var.set(speed_str))
        
    def on_complete(self, success, filepath=None):
        def reset_ui():
            if success and filepath:
                self.received_filepath = filepath
                self.btn_open.configure(state="normal")
        self.controller.root.after(0, reset_ui)

    def open_file(self):
        if self.received_filepath and os.path.exists(self.received_filepath):
            if os.name == 'nt':
                subprocess.run(["explorer", "/select,", os.path.normpath(self.received_filepath)])
            else:
                subprocess.run(["xdg-open", self.received_filepath])


class SendFrame(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="transparent")
        self.controller = controller
        self.filepath = None
        self.ctk_qr_img = None
        
        # Top Bar
        top_bar = ctk.CTkFrame(self, fg_color="transparent")
        top_bar.pack(fill="x", padx=15, pady=(15, 5))
        
        btn_back = ctk.CTkButton(
            top_bar, 
            text="← Back", 
            width=80,
            height=32,
            corner_radius=10,
            fg_color="#334155",
            hover_color="#475569",
            command=self.controller.show_home_screen
        )
        btn_back.pack(side="left")
        
        lbl_header = ctk.CTkLabel(
            top_bar, 
            text="Send Mode", 
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#f8fafc"
        )
        lbl_header.pack(side="left", padx=20)
        
        # File / Folder Picker Card
        picker_card = ctk.CTkFrame(self, corner_radius=14, fg_color=("#1e293b", "#1e293b"))
        picker_card.pack(fill="x", padx=15, pady=5)
        
        btn_box = ctk.CTkFrame(picker_card, fg_color="transparent")
        btn_box.pack(pady=(12, 6))
        
        btn_select_file = ctk.CTkButton(
            btn_box, 
            text="📄 Select File", 
            width=130,
            height=36,
            corner_radius=10,
            fg_color="#2563eb",
            hover_color="#1d4ed8",
            command=self.select_file
        )
        btn_select_file.pack(side="left", padx=6)
        
        btn_select_folder = ctk.CTkButton(
            btn_box, 
            text="📁 Select Folder", 
            width=130,
            height=36,
            corner_radius=10,
            fg_color="#8b5cf6",
            hover_color="#7c3aed",
            command=self.select_folder
        )
        btn_select_folder.pack(side="left", padx=6)
        
        self.lbl_file = ctk.CTkLabel(
            picker_card, 
            text="No item selected", 
            font=ctk.CTkFont(size=13),
            text_color="#94a3b8",
            wraplength=420
        )
        self.lbl_file.pack(pady=(0, 10))
        
        # Segmented Tab View
        self.tabview = ctk.CTkTabview(self, corner_radius=16)
        self.tabview.pack(fill="both", expand=True, padx=15, pady=5)
        
        self.tab_qr = self.tabview.add("📱 Mobile (QR Code)")
        self.tab_pass = self.tabview.add("💻 Laptop (Passcode)")
        
        self._setup_qr_tab()
        self._setup_passcode_tab()
        
        # Bottom Status Panel
        self.status_card = ctk.CTkFrame(self, corner_radius=16, fg_color=("#1e293b", "#1e293b"))
        self.status_card.pack(fill="x", padx=15, pady=(5, 15))
        
        self.status_var = ctk.StringVar(value="")
        lbl_status = ctk.CTkLabel(
            self.status_card, 
            textvariable=self.status_var, 
            font=ctk.CTkFont(size=13),
            wraplength=420
        )
        lbl_status.pack(pady=(10, 4))
        
        self.progress_bar = ctk.CTkProgressBar(self.status_card, height=10, corner_radius=5)
        self.progress_bar.pack(fill="x", padx=20, pady=4)
        self.progress_bar.set(0)
        
        self.speed_var = ctk.StringVar(value="")
        lbl_speed = ctk.CTkLabel(
            self.status_card, 
            textvariable=self.speed_var, 
            font=ctk.CTkFont(size=12),
            text_color="#38bdf8"
        )
        lbl_speed.pack(pady=(0, 10))
        
        self.tabview.configure(command=self._on_tab_changed)

    def _setup_qr_tab(self):
        lbl_inst = ctk.CTkLabel(
            self.tab_qr, 
            text="Scan with phone camera to download from laptop:", 
            font=ctk.CTkFont(size=13),
            text_color="#94a3b8"
        )
        lbl_inst.pack(pady=(8, 4))
        
        self.qr_card = ctk.CTkFrame(self.tab_qr, corner_radius=14, fg_color="#ffffff", width=180, height=180)
        self.qr_card.pack(pady=4)
        self.qr_card.pack_propagate(False)
        
        self.lbl_qr_image = ctk.CTkLabel(self.qr_card, text="")
        self.lbl_qr_image.pack(expand=True)
        
        self.url_var = ctk.StringVar(value="Select a file or folder above")
        lbl_url = ctk.CTkLabel(
            self.tab_qr, 
            textvariable=self.url_var, 
            font=ctk.CTkFont(family="Courier", size=12, weight="bold"),
            text_color="#10b981",
            wraplength=380
        )
        lbl_url.pack(pady=4)

    def _setup_passcode_tab(self):
        lbl_passcode_inst = ctk.CTkLabel(
            self.tab_pass, 
            text="Enter Receiver Laptop's 4-digit Passcode:", 
            font=ctk.CTkFont(size=14),
            text_color="#94a3b8"
        )
        lbl_passcode_inst.pack(pady=(20, 10))
        
        self.passcode_entry = ctk.CTkEntry(
            self.tab_pass, 
            font=ctk.CTkFont(family="Courier", size=24, weight="bold"),
            width=140,
            height=48,
            justify="center",
            corner_radius=12
        )
        self.passcode_entry.pack(pady=5)
        
        self.btn_send = ctk.CTkButton(
            self.tab_pass, 
            text="Send Now", 
            height=42,
            corner_radius=12,
            fg_color="#2563eb",
            hover_color="#1d4ed8",
            command=self.start_passcode_send, 
            state="disabled"
        )
        self.btn_send.pack(pady=15)

    def select_file(self):
        path = filedialog.askopenfilename(parent=self.controller.root)
        if path:
            self.filepath = path
            filename = os.path.basename(path)
            self.lbl_file.configure(text=f"Selected File: {filename}", text_color="#f8fafc")
            self.btn_send.configure(state="normal")
            self._update_web_sender_if_active()

    def select_folder(self):
        path = filedialog.askdirectory(parent=self.controller.root)
        if path:
            self.filepath = path
            foldername = os.path.basename(path) or path
            self.lbl_file.configure(text=f"Selected Folder: {foldername}", text_color="#f8fafc")
            self.btn_send.configure(state="normal")
            self._update_web_sender_if_active()

    def _on_tab_changed(self):
        selected_tab = self.tabview.get()
        if "Mobile" in selected_tab:
            if self.controller.sender:
                self.controller.sender.cancel()
                self.controller.sender = None
            self._update_web_sender_if_active()
        else:
            if self.controller.web_sender:
                self.controller.web_sender.stop()
                self.controller.web_sender = None
            self.lbl_qr_image.configure(image="")
            self.url_var.set("Switched to Laptop Passcode Mode")

    def _update_web_sender_if_active(self):
        if not self.filepath:
            self.url_var.set("Select a file or folder above")
            return
            
        selected_tab = self.tabview.get()
        if "Mobile" not in selected_tab:
            return

        if self.controller.web_sender:
            self.controller.web_sender.stop()
            self.controller.web_sender = None

        self.url_var.set("Generating QR Code...")

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
            self.ctk_qr_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(160, 160))
            self.lbl_qr_image.configure(image=self.ctk_qr_img)

    def start_passcode_send(self):
        passcode = self.passcode_entry.get().strip()
        if len(passcode) != 4 or not passcode.isdigit():
            messagebox.showerror("Error", "Passcode must be a 4-digit number.")
            return
            
        if not self.filepath:
            messagebox.showerror("Error", "Please select a file or folder first.")
            return
            
        self.btn_send.configure(state="disabled")
        self.passcode_entry.configure(state="disabled")
        
        self.controller.sender = Sender(
            on_status_callback=self.update_status,
            on_progress_callback=self.update_progress,
            on_complete_callback=self.on_complete
        )
        self.controller.sender.discover_and_send(self.filepath, passcode)

    def update_status(self, msg):
        self.controller.root.after(0, lambda: self.status_var.set(msg))

    def update_progress(self, percent, speed_str):
        self.controller.root.after(0, lambda: self.progress_bar.set(percent / 100.0))
        self.controller.root.after(0, lambda: self.speed_var.set(speed_str))
        
    def on_complete(self, success):
        def reset_ui():
            self.btn_send.configure(state="normal")
            self.passcode_entry.configure(state="normal")
        self.controller.root.after(0, reset_ui)

if __name__ == "__main__":
    root = ctk.CTk()
    app = LocalDropApp(root)
    root.mainloop()
