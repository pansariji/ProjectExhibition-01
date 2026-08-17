import customtkinter as ctk
from tkinter import filedialog, messagebox
import os

import config
from utils import generate_qr_image
from p2p import Sender
from web import WebSender

class SendFrame(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color=config.COLOR_BG)
        self.controller = controller
        self.filepath = None
        self.ctk_qr_img = None
        
        # Top Bar
        top_bar = ctk.CTkFrame(self, fg_color="transparent")
        top_bar.pack(fill="x", padx=20, pady=(15, 5))
        
        btn_back = ctk.CTkButton(
            top_bar, 
            text="← Back", 
            width=84,
            height=34,
            corner_radius=17,
            fg_color="#eae4d7",
            text_color=config.COLOR_TEXT_PRIMARY,
            hover_color="#d8d0c0",
            border_width=1,
            border_color="#c8c0b0",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self.controller.show_home_screen
        )
        btn_back.pack(side="left")
        
        lbl_header = ctk.CTkLabel(
            top_bar, 
            text="Send Route", 
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=config.COLOR_TEXT_PRIMARY
        )
        lbl_header.pack(side="left", padx=20)
        
        # File / Folder Picker Card
        picker_card = ctk.CTkFrame(
            self, 
            corner_radius=16, 
            fg_color=config.COLOR_CARD,
            border_width=1,
            border_color=config.COLOR_BORDER
        )
        picker_card.pack(fill="x", padx=20, pady=5)
        
        btn_box = ctk.CTkFrame(picker_card, fg_color="transparent")
        btn_box.pack(pady=(12, 6))
        
        btn_select_file = ctk.CTkButton(
            btn_box, 
            text="📄 Select File", 
            width=135,
            height=38,
            corner_radius=19,
            fg_color=config.COLOR_BTN_PRIMARY_BG,
            text_color=config.COLOR_BTN_PRIMARY_FG,
            hover_color=config.COLOR_BTN_PRIMARY_HOVER,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self.select_file
        )
        btn_select_file.pack(side="left", padx=6)
        
        btn_select_folder = ctk.CTkButton(
            btn_box, 
            text="📁 Select Folder", 
            width=135,
            height=38,
            corner_radius=19,
            fg_color=config.COLOR_BTN_SEC_BG,
            text_color=config.COLOR_BTN_SEC_FG,
            hover_color=config.COLOR_BTN_SEC_HOVER,
            border_width=1,
            border_color="#d8d0c0",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self.select_folder
        )
        btn_select_folder.pack(side="left", padx=6)
        
        self.lbl_file = ctk.CTkLabel(
            picker_card, 
            text="No item selected", 
            font=ctk.CTkFont(size=12),
            text_color=config.COLOR_TEXT_MUTED,
            wraplength=420
        )
        self.lbl_file.pack(pady=(0, 10))
        
        # Segmented Tab View
        self.tabview = ctk.CTkTabview(
            self, 
            corner_radius=16,
            fg_color=config.COLOR_CARD,
            segmented_button_fg_color="#eae4d7",
            segmented_button_selected_color="#1c1917",
            segmented_button_unselected_color="#e2dcd0"
        )
        self.tabview.pack(fill="both", expand=True, padx=20, pady=5)
        
        self.tab_qr = self.tabview.add("📱 Mobile QR")
        self.tab_pass = self.tabview.add("💻 Laptop Passcode")
        
        self._setup_qr_tab()
        self._setup_passcode_tab()
        
        # Bottom Status Panel
        self.status_card = ctk.CTkFrame(
            self, 
            corner_radius=16, 
            fg_color=config.COLOR_CARD,
            border_width=1,
            border_color=config.COLOR_BORDER
        )
        self.status_card.pack(fill="x", padx=20, pady=(5, 15))
        
        self.status_var = ctk.StringVar(value="")
        lbl_status = ctk.CTkLabel(
            self.status_card, 
            textvariable=self.status_var, 
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=config.COLOR_TEXT_PRIMARY,
            wraplength=420
        )
        lbl_status.pack(pady=(10, 4))
        
        self.progress_bar = ctk.CTkProgressBar(
            self.status_card, 
            height=10, 
            corner_radius=10,
            progress_color=config.COLOR_GREEN,
            fg_color="#e2dcd0"
        )
        self.progress_bar.pack(fill="x", padx=20, pady=4)
        self.progress_bar.set(0)
        
        self.speed_var = ctk.StringVar(value="")
        lbl_speed = ctk.CTkLabel(
            self.status_card, 
            textvariable=self.speed_var, 
            font=ctk.CTkFont(family="Consolas", size=12, weight="bold"),
            text_color=config.COLOR_GREEN
        )
        lbl_speed.pack(pady=(0, 10))
        
        self.tabview.configure(command=self._on_tab_changed)
        self._update_tab_styles()

    def _setup_qr_tab(self):
        lbl_inst = ctk.CTkLabel(
            self.tab_qr, 
            text="Scan with mobile camera to download:", 
            font=ctk.CTkFont(size=11),
            text_color=config.COLOR_TEXT_MUTED
        )
        lbl_inst.pack(pady=(6, 4))
        
        self.qr_card = ctk.CTkFrame(
            self.tab_qr, 
            corner_radius=14, 
            fg_color="#faf7f0", 
            width=160, 
            height=160,
            border_width=1,
            border_color="#d8d0c0"
        )
        self.qr_card.pack(pady=4)
        self.qr_card.pack_propagate(False)
        
        self.lbl_qr_image = ctk.CTkLabel(self.qr_card, text="")
        self.lbl_qr_image.pack(expand=True)
        
        self.url_var = ctk.StringVar(value="Select a file or folder above")
        lbl_url = ctk.CTkLabel(
            self.tab_qr, 
            textvariable=self.url_var, 
            font=ctk.CTkFont(family="Consolas", size=12, weight="bold"),
            text_color=config.COLOR_GREEN,
            wraplength=380
        )
        lbl_url.pack(pady=4)

    def _setup_passcode_tab(self):
        lbl_passcode_inst = ctk.CTkLabel(
            self.tab_pass, 
            text="Enter receiver laptop passcode:", 
            font=ctk.CTkFont(size=12),
            text_color=config.COLOR_TEXT_MUTED
        )
        lbl_passcode_inst.pack(pady=(6, 2))
        
        self.passcode_entry = ctk.CTkEntry(
            self.tab_pass, 
            font=ctk.CTkFont(family="Consolas", size=20, weight="bold"),
            width=140,
            height=36,
            justify="center",
            corner_radius=10,
            border_width=1,
            border_color="#d8d0c0"
        )
        self.passcode_entry.pack(pady=2)

        lbl_ip_inst = ctk.CTkLabel(
            self.tab_pass, 
            text="Receiver IP (Optional / College Wi-Fi):", 
            font=ctk.CTkFont(size=11),
            text_color=config.COLOR_TEXT_MUTED
        )
        lbl_ip_inst.pack(pady=(6, 2))

        self.ip_entry = ctk.CTkEntry(
            self.tab_pass, 
            placeholder_text="e.g. 10.1.20.150 (Leave empty for auto-scan)",
            font=ctk.CTkFont(family="Consolas", size=11),
            width=270,
            height=32,
            justify="center",
            corner_radius=10,
            border_width=1,
            border_color="#d8d0c0"
        )
        self.ip_entry.pack(pady=2)
        
        self.btn_send = ctk.CTkButton(
            self.tab_pass, 
            text="Send Now", 
            height=38,
            corner_radius=19,
            fg_color=config.COLOR_BTN_PRIMARY_BG,
            text_color=config.COLOR_BTN_PRIMARY_FG,
            hover_color=config.COLOR_BTN_PRIMARY_HOVER,
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.start_passcode_send, 
            state="disabled"
        )
        self.btn_send.pack(pady=8)

    def select_file(self):
        path = filedialog.askopenfilename(parent=self.controller.root)
        if path:
            self.filepath = path
            filename = os.path.basename(path)
            self.lbl_file.configure(text=f"Selected File: {filename}", text_color=config.COLOR_TEXT_PRIMARY)
            self.btn_send.configure(state="normal")
            self._update_web_sender_if_active()

    def select_folder(self):
        path = filedialog.askdirectory(parent=self.controller.root)
        if path:
            self.filepath = path
            foldername = os.path.basename(path) or path
            self.lbl_file.configure(text=f"Selected Folder: {foldername}", text_color=config.COLOR_TEXT_PRIMARY)
            self.btn_send.configure(state="normal")
            self._update_web_sender_if_active()

    def _update_tab_styles(self):
        try:
            sb = self.tabview._segmented_button
            cur = self.tabview.get()
            for name, btn in sb._buttons_dict.items():
                if name == cur:
                    btn.configure(
                        fg_color=config.COLOR_TEXT_PRIMARY,
                        text_color="#f3efe6",
                        hover_color="#2b2623"
                    )
                else:
                    btn.configure(
                        fg_color="#e2dcd0",
                        text_color=config.COLOR_TEXT_PRIMARY,
                        hover_color="#d5cebf"
                    )
        except Exception:
            pass

    def _on_tab_changed(self):
        self._update_tab_styles()
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
            port=config.DEFAULT_WEB_PORT,
            on_status_callback=self.update_status,
            on_progress_callback=self.update_progress,
            on_complete_callback=self.on_complete
        )
        self.controller.web_sender.start()
        
        url = self.controller.web_sender.url
        self.url_var.set(url)
        
        pil_img = generate_qr_image(url)
        if pil_img:
            self.ctk_qr_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(140, 140))
            self.lbl_qr_image.configure(image=self.ctk_qr_img)

    def start_passcode_send(self):
        passcode = self.passcode_entry.get().strip()
        target_ip = self.ip_entry.get().strip() or None
        
        if len(passcode) != 4 or not passcode.isdigit():
            messagebox.showerror("Error", "Passcode must be a 4-digit number.")
            return
            
        if not self.filepath:
            messagebox.showerror("Error", "Please select a file or folder first.")
            return
            
        self.btn_send.configure(state="disabled")
        self.passcode_entry.configure(state="disabled")
        self.ip_entry.configure(state="disabled")
        
        self.controller.sender = Sender(
            on_status_callback=self.update_status,
            on_progress_callback=self.update_progress,
            on_complete_callback=self.on_complete
        )
        self.controller.sender.discover_and_send(self.filepath, passcode, target_ip)

    def update_status(self, msg):
        self.controller.root.after(0, lambda: self.status_var.set(msg))

    def update_progress(self, percent, speed_str):
        self.controller.root.after(0, lambda: self.progress_bar.set(percent / 100.0))
        self.controller.root.after(0, lambda: self.speed_var.set(speed_str))
        
    def on_complete(self, success, reason=None):
        def reset_ui():
            self.btn_send.configure(state="normal")
            self.passcode_entry.configure(state="normal")
            self.ip_entry.configure(state="normal")
            
            if not success and reason == "DISCOVERY_FAILED":
                messagebox.showwarning(
                    "College Wi-Fi Notice (Discovery Failed)",
                    "Automatic discovery could not locate the Receiver laptop.\n\n"
                    "Why this happens:\n"
                    "Enterprise/College Wi-Fi networks (like VIT Bhopal) block UDP Broadcast packets.\n\n"
                    "How to fix:\n"
                    "1. Ask the Receiver laptop for their IP address (shown on their Receive screen).\n"
                    "2. Type their IP in the 'Receiver IP' box above and click 'Send Now'.\n"
                    "3. Or connect both laptops to a Mobile Hotspot!"
                )
        self.controller.root.after(0, reset_ui)
