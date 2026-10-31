"""Public download-window API shared by the app and browser integration."""
from batch_dialog import BatchDialog
from capture_dialog import CapturePrompt
from completion_dialog import CompletionDialog

def activate(window):
    """Bring a window in front of the browser that asked for it.

    Windows refuses SetForegroundWindow to a process that is not in front;
    joining the foreground thread's input for this call is the documented
    way for an app the user just acted on (the browser button) to answer.
    """
    import sys
    if sys.platform!='win32':return
    import ctypes
    from ctypes import wintypes
    user32=ctypes.windll.user32;kernel32=ctypes.windll.kernel32
    user32.GetWindowThreadProcessId.argtypes=(wintypes.HWND,ctypes.POINTER(wintypes.DWORD))
    user32.AttachThreadInput.argtypes=(wintypes.DWORD,wintypes.DWORD,wintypes.BOOL)
    for name in ('SetForegroundWindow','BringWindowToTop'):getattr(user32,name).argtypes=(wintypes.HWND,)
    window.update_idletasks();hwnd=int(window.wm_frame(),16)
    current=kernel32.GetCurrentThreadId();other=user32.GetWindowThreadProcessId(user32.GetForegroundWindow(),None)
    attached=bool(other and other!=current and user32.AttachThreadInput(other,current,True))
    try:user32.BringWindowToTop(hwnd);user32.SetForegroundWindow(hwnd)
    finally:
        if attached:user32.AttachThreadInput(other,current,False)


def foreground(window,keep_on_top=False):
    """Show `window` in front; a decision window can stay on top until it closes."""
    window.deiconify();window.lift()
    window.attributes('-topmost',True)
    # Joining another thread's input is kept to the windows the browser or a
    # finished download asks for; with it, Tk once fired a <Leave> binding
    # without its event (package self-test, another app in front).
    if keep_on_top:activate(window)
    window.focus_force()
    if not keep_on_top:
        window.after(500,lambda:window.attributes('-topmost',False) if window.winfo_exists() else None)
