"""
main.py - Application entry point, single-instance verification, system tray and lifecycle management.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
import socket
import sys
import threading
from typing import Optional

try:
    import pystray
    from pystray import MenuItem as item
except ImportError:
    pystray = None

from assets.icon import create_default_icon_image
from clipboard_monitor import ClipboardMonitor
from gui import MainWindow
from utils import ensure_config_dir, load_settings
from browser_bridge import BrowserBridge
from utils import clean_filename, get_unique_filepath

# Setup Logging
log_dir = ensure_config_dir()
log_file = log_dir / "sdm.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] (%(threadName)s) %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout) if sys.stdout is not None else logging.NullHandler(),
        logging.FileHandler(str(log_file), encoding="utf-8"),
    ],
)
logger = logging.getLogger("SDM.Main")

# Single Instance Lock using local port binding
SINGLE_INSTANCE_PORT = int(os.environ.get('SDM_INSTANCE_PORT', '49281'))
_instance_socket: Optional[socket.socket] = None


def check_single_instance() -> bool:
    """Ensure only one instance of the application runs simultaneously."""
    global _instance_socket
    try:
        _instance_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        _instance_socket.bind(("127.0.0.1", SINGLE_INSTANCE_PORT))
        _instance_socket.listen(1)
        return True
    except socket.error:
        logger.warning("Another instance of SDM is already running.")
        return False


class TrayManager:
    """Manages system tray icon using pystray."""

    def __init__(self, main_window: MainWindow):
        self.window = main_window
        self.icon: Optional[pystray.Icon] = None
        self._setup_tray()

    def _setup_tray(self) -> None:
        if pystray is None:
            logger.warning("pystray not installed; system tray disabled.")
            return

        icon_image = create_default_icon_image(64)
        menu = (
            item("Göster / Gizle", self.toggle_window, default=True),
            item("Yeni İndirme", self.open_new_download),
            pystray.Menu.SEPARATOR,
            item("Çıkış", self.quit_app),
        )
        self.icon = pystray.Icon(
            "SDM", icon_image, "SDM", menu
        )

    def start(self) -> None:
        if self.icon:
            threading.Thread(target=self.icon.run, daemon=True).start()

    def stop(self) -> None:
        if self.icon:
            self.icon.stop()

    def toggle_window(self, icon=None, item=None) -> None:
        self.window.after(0, self._toggle_window_main)

    def _toggle_window_main(self) -> None:
        if self.window.state() == "withdrawn" or not self.window.winfo_viewable():
            self.window.deiconify()
            self.window.lift()
            self.window.focus_force()
        else:
            self.window.withdraw()

    def open_new_download(self, icon=None, item=None) -> None:
        self.window.after(0, lambda: (self.window.deiconify(), self.window.open_add_dialog()))

    def quit_app(self, icon=None, item=None) -> None:
        self.window.after(0, self._exit_app)

    def _exit_app(self) -> None:
        if self.icon:
            self.icon.stop()
        self.window.engine.stop_engine()
        self.window.destroy()
        sys.exit(0)


def main() -> None:
    if sys.platform == 'win32':
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('SDM.DownloadManager')
    if "--smoke-test" in sys.argv:
        app = MainWindow()
        assert app._icon_photo.width() == 64, 'SDM window icon was not loaded'
        app.after(1200, app.destroy)
        try:
            app.mainloop()
        finally:
            app.engine.stop_engine()
        return
    if not check_single_instance():
        print("SDM zaten çalışıyor.")
        sys.exit(0)

    logger.info("Starting SDM...")
    settings = load_settings()

    app = MainWindow()

    bridge = BrowserBridge()
    bridge.start()

    def process_browser_queue():
        while not bridge.pending.empty():
            request = bridge.pending.get_nowait()
            if request.get('kind')=='file':
                path=get_unique_filepath(app.settings['download_dir'],request['filename'])
                app.add_download_from_dialog(url=request['url'],filename=path.name,dest_path=str(path))
                app.deiconify()
                continue
            filename = 'Browser video.mp3' if request['audio'] else 'Browser video.mkv'
            app.add_download_from_dialog(
                url=request['url'], filename=filename,
                dest_path=str(Path(app.settings['download_dir']) / filename),
                is_video=True,
                video_quality='Yalnızca Ses (MP3)' if request['audio'] else 'En İyi',
                selected_height=request['height'] if not request['audio'] else None,
            )
            app.deiconify()
        app.after(200, process_browser_queue)

    app.after(200, process_browser_queue)

    # System tray setup
    tray = TrayManager(app)
    tray.start()

    # Clipboard monitor
    def on_clipboard_url(url: str):
        if settings.get("clipboard_monitoring", True):
            app.after(0, lambda: (app.deiconify(), app.open_add_dialog(initial_url=url)))

    clip_monitor = ClipboardMonitor(
        on_url_detected=on_clipboard_url,
        monitored_extensions=settings.get("monitored_extensions", []),
    )
    if settings.get("clipboard_monitoring", True):
        clip_monitor.start()

    # If start minimized
    if settings.get("start_minimized", False) or '--background' in sys.argv:
        app.withdraw()

    try:
        app.mainloop()
    finally:
        clip_monitor.stop()
        bridge.stop()
        tray.stop()
        app.engine.stop_engine()
        for task in app.video_tasks.values():
            task.cancel()
        if _instance_socket:
            _instance_socket.close()


if __name__ == "__main__":
    main()
