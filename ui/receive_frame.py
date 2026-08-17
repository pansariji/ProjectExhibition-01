import customtkinter as ctk
import os
import subprocess

import config
from utils import generate_passcode, generate_qr_image
from p2p import Receiver
from web import WebReceiver

class ReceiveFrame(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color=config.COLOR_BG)
        self.controller = controller
        
        self.passcode = generate_passcode()
        self.received_filepath = None
        self.ctk_qr_img = None
        
        # Top Bar
        top_bar = ctk.CTkFrame(self, fg_color="transparent")
        top_bar.pack(fill="x", padx=20, pady=(15, 5))
        
        btn_back = ctk.CTkButton(
            top_bar, 
            text="← Back", 
            width=80,
            height=32,
            corner_radius=16,
            fg_color=config.COLOR_BTN_SEC_BG,
            text_color=config.COLOR_TEXT_PRIMARY,
            hover_color=config.COLOR_BTN_SEC_HOVER,
            border_width=1,
            border_color=config.COLOR_BORDER,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self.controller.show_home_screen
        )
        btn_back.pack(side="left")
        
        lbl_header = ctk.CTkLabel(
            top_bar, 
            text="Receive Route", 
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=config.COLOR_TEXT_PRIMARY
        )
        lbl_header.pack(side="left", padx=20)
        
        # Segmented Tab View
        self.tabview = ctk.CTkTabview(
            self, 
            corner_radius=16,
            fg_color=config.COLOR_CARD,
            segmented_button_fg_color="#eae4d7",
            segmented_button_selected_color="#1c1917",
            segmented_button_selected_text_color="#f3efe6",
            segmented_button_unselected_color="#eae4d7",
            segmented_button_unselected_text_color="#1c1917"
        )
        self.tabview.pack(fill="both", expand=True, padx=20, pady=10)
        
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
        
        self.status_var = ctk.StringVar(value="Select receive mode above")
        lbl_status = ctk.CTkLabel(
            self.status_card, 
            textvariable=self.status_var, 
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=config.COLOR_TEXT_PRIMARY,
            wraplength=420
        )
        lbl_status.pack(pady=(12, 4))
        
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
        lbl_speed.pack(pady=(0, 4))
        
        self.btn_open = ctk.CTkButton(
            self.status_card, 
            text="Show Received Item", 
            height=38,
            corner_radius=19,
            fg_color=config.COLOR_GREEN,
            text_color="#ffffff",
            hover_color=config.COLOR_GREEN_HOVER,
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.open_file, 
            state="disabled"
        )
        self.btn_open.pack(pady=(4, 12))
        
        self.tabview.configure(command=self._on_tab_changed)
        self._start_web_receiver()

    def _setup_qr_tab(self):
        lbl_inst = ctk.CTkLabel(
            self.tab_qr, 
            text="Scan with mobile camera to upload:", 
            font=ctk.CTkFont(size=12),
            text_color=config.COLOR_TEXT_MUTED
        )
        lbl_inst.pack(pady=(10, 5))
        
        self.qr_card = ctk.CTkFrame(
            self.tab_qr, 
            corner_radius=14, 
            fg_color="#faf7f0", 
            width=200, 
            height=200,
            border_width=1,
            border_color="#d8d0c0"
        )
        self.qr_card.pack(pady=5)
        self.qr_card.pack_propagate(False)
        
        self.lbl_qr_image = ctk.CTkLabel(self.qr_card, text="")
        self.lbl_qr_image.pack(expand=True)
        
        self.url_var = ctk.StringVar(value="Starting Web Server...")
        lbl_url = ctk.CTkLabel(
            self.tab_qr, 
            textvariable=self.url_var, 
            font=ctk.CTkFont(family="Consolas", size=13, weight="bold"),
            text_color=config.COLOR_GREEN
        )
        lbl_url.pack(pady=8)

    def _setup_passcode_tab(self):
        lbl_inst = ctk.CTkLabel(
            self.tab_pass, 
            text="Tell sender laptop to enter this passcode:", 
            font=ctk.CTkFont(size=13),
            text_color=config.COLOR_TEXT_MUTED
        )
        lbl_inst.pack(pady=(35, 10))
        
        pass_card = ctk.CTkFrame(
            self.tab_pass, 
            corner_radius=16, 
            fg_color="#f3efe6",
            border_width=1,
            border_color="#d8d0c0"
        )
        pass_card.pack(padx=40, pady=10)
        
        lbl_pass = ctk.CTkLabel(
            pass_card, 
            text=self.passcode, 
            font=ctk.CTkFont(family="Consolas", size=44, weight="bold"),
            text_color=config.COLOR_TEXT_PRIMARY
        )
        lbl_pass.pack(padx=40, pady=18)

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
                port=config.DEFAULT_WEB_PORT,
                on_status_callback=self.update_status,
                on_progress_callback=self.update_progress,
                on_complete_callback=self.on_complete
            )
            self.controller.web_receiver.start()
            
        url = self.controller.web_receiver.url
        self.url_var.set(url)
        
        pil_img = generate_qr_image(url)
        if pil_img:
            self.ctk_qr_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(180, 180))
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
