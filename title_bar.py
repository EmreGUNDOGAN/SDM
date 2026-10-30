"""Paint the Windows title bar in the design's colours.

Windows 11 (build 22000+) accepts a caption and caption-text colour through
DWM; Windows 10 only honours the dark-mode flag, which still keeps a dark
window from wearing a white bar. Windows without a system frame (HUD, menus,
toasts) are skipped. The colour comes from the palette, not cget('bg'): a
ttkbootstrap Toplevel reports its theme grey even when design surfaces cover it.
"""
import os
import tkinter as tk

DARK_MODE, CAPTION_COLOR, TEXT_COLOR = 20, 35, 36


def _colorref(widget, color):
    r, g, b = (value // 257 for value in widget.winfo_rgb(color))
    return r | g << 8 | b << 16


def match(window, background, text):
    """Colour `window`'s title bar; returns the caption COLORREF or None."""
    if os.name != 'nt' or not window.winfo_exists() or window.overrideredirect():return None
    import ctypes
    from ctypes import wintypes
    user = ctypes.WinDLL('user32');user.GetParent.argtypes = [wintypes.HWND];user.GetParent.restype = wintypes.HWND
    dwm = ctypes.WinDLL('dwmapi');dwm.DwmSetWindowAttribute.argtypes = [wintypes.HWND, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD]
    hwnd = user.GetParent(window.winfo_id())
    if not hwnd:return None
    r, g, b = (value // 257 for value in window.winfo_rgb(background))
    dark = wintypes.BOOL(.2126 * r + .7152 * g + .0722 * b < 128)
    dwm.DwmSetWindowAttribute(hwnd, DARK_MODE, ctypes.byref(dark), ctypes.sizeof(dark))
    caption = wintypes.DWORD(_colorref(window, background));title = wintypes.DWORD(_colorref(window, text))
    dwm.DwmSetWindowAttribute(hwnd, CAPTION_COLOR, ctypes.byref(caption), ctypes.sizeof(caption))
    dwm.DwmSetWindowAttribute(hwnd, TEXT_COLOR, ctypes.byref(title), ctypes.sizeof(title))
    return caption.value


def refresh(app):
    """Re-colour the main window and every open window after a theme change."""
    for window in [app] + [w for w in app.winfo_children() if isinstance(w, tk.Toplevel)]:
        _paint(app, window)


def _paint(app, window):
    # Main window: page background; other windows: their dialog surface.
    palette = app.palette if window is app else getattr(window, 'p', None) or app.palette
    try:match(window, palette['bg' if window is app else 'dialog'], palette['text'])
    except (OSError, tk.TclError, KeyError):pass


def install(app):
    """Colour each window as it first appears, then the open ones."""
    for kind in ('Tk', 'Toplevel'):app.bind_class(kind, '<Map>', lambda event: _paint(app, event.widget), add='+')
    refresh(app)
