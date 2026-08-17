import customtkinter as ctk

import config
from ui import HomeFrame, ReceiveFrame, SendFrame

# Global CustomTkinter appearance and theme settings
ctk.set_appearance_mode(config.APPEARANCE_MODE)
ctk.set_default_color_theme(config.COLOR_THEME)

class LocalDropApp:
    def __init__(self, root):
        self.root = root
        self.root.title(config.APP_TITLE)
        self.root.geometry(config.WINDOW_GEOMETRY)
        self.root.resizable(False, False)
        self.root.configure(fg_color=config.COLOR_BG)
        
        # Active transfer instances
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

if __name__ == "__main__":
    root = ctk.CTk()
    app = LocalDropApp(root)
    root.mainloop()
