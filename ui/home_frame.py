import customtkinter as ctk
import config

class HomeFrame(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color=config.COLOR_BG)
        self.controller = controller
        
        # Main Hero Card
        hero_card = ctk.CTkFrame(
            self, 
            corner_radius=22, 
            fg_color=config.COLOR_CARD,
            border_width=1,
            border_color=config.COLOR_BORDER
        )
        hero_card.pack(fill="x", padx=28, pady=(45, 25))
        
        # Status / Routing Pill Badge
        badge_frame = ctk.CTkFrame(
            hero_card, 
            corner_radius=100, 
            fg_color=config.COLOR_CARD_ALT, 
            border_width=1, 
            border_color="#d8d0c0"
        )
        badge_frame.pack(pady=(24, 8))
        
        lbl_tag = ctk.CTkLabel(
            badge_frame,
            text="((o)) ROUTING  •  LAN ACTIVE",
            font=ctk.CTkFont(family="Consolas", size=11, weight="bold"),
            text_color=config.COLOR_GREEN
        )
        lbl_tag.pack(padx=14, pady=3)

        lbl_title = ctk.CTkLabel(
            hero_card, 
            text=config.APP_TITLE, 
            font=ctk.CTkFont(family="Space Grotesk", size=40, weight="bold"),
            text_color=config.COLOR_TEXT_PRIMARY
        )
        lbl_title.pack(pady=(0, 4))
        
        lbl_subtitle = ctk.CTkLabel(
            hero_card, 
            text="Cross-device file & folder transfers in route.", 
            font=ctk.CTkFont(size=13),
            text_color=config.COLOR_TEXT_MUTED
        )
        lbl_subtitle.pack(pady=(0, 16))
        
        # Inline Tags Container (Subtle Non-Clickable Feature Badges)
        tags_container = ctk.CTkFrame(hero_card, fg_color="transparent")
        tags_container.pack(pady=(0, 24))
        
        tag1 = ctk.CTkLabel(
            tags_container, 
            text="⚡ P2P Direct", 
            font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
            text_color=config.COLOR_TEXT_MUTED,
            fg_color=config.COLOR_CARD_ALT,
            corner_radius=8
        )
        tag1.pack(side="left", padx=4, pady=2)
        
        tag2 = ctk.CTkLabel(
            tags_container, 
            text="🛡️ Zero Cloud", 
            font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
            text_color=config.COLOR_TEXT_MUTED,
            fg_color=config.COLOR_CARD_ALT,
            corner_radius=8
        )
        tag2.pack(side="left", padx=4, pady=2)
        
        tag3 = ctk.CTkLabel(
            tags_container, 
            text="📱 QR Web", 
            font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
            text_color=config.COLOR_TEXT_MUTED,
            fg_color=config.COLOR_CARD_ALT,
            corner_radius=8
        )
        tag3.pack(side="left", padx=4, pady=2)

        # Primary Action Buttons
        btn_send = ctk.CTkButton(
            self,
            text="Send File or Folder  →",
            font=ctk.CTkFont(size=16, weight="bold"),
            height=58,
            corner_radius=29,
            fg_color=config.COLOR_BTN_PRIMARY_BG,
            text_color=config.COLOR_BTN_PRIMARY_FG,
            hover_color=config.COLOR_BTN_PRIMARY_HOVER,
            command=self.controller.show_send_screen
        )
        btn_send.pack(fill="x", padx=28, pady=(10, 12))
        
        btn_receive = ctk.CTkButton(
            self,
            text="Receive File or Folder  ↓",
            font=ctk.CTkFont(size=16, weight="bold"),
            height=58,
            corner_radius=29,
            fg_color=config.COLOR_BTN_SEC_BG,
            text_color=config.COLOR_BTN_SEC_FG,
            hover_color=config.COLOR_BTN_SEC_HOVER,
            border_width=1,
            border_color="#d8d0c0",
            command=self.controller.show_receive_screen
        )
        btn_receive.pack(fill="x", padx=28, pady=0)

        # Footer metadata
        lbl_info = ctk.CTkLabel(
            self, 
            text=f"LOCAL COMPANION  •  VERSION {config.APP_VERSION}", 
            font=ctk.CTkFont(family="Consolas", size=10),
            text_color=config.COLOR_TEXT_MUTED
        )
        lbl_info.pack(side="bottom", pady=25)
