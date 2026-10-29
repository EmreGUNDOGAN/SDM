"""Public download-window API shared by the app and browser integration."""
from batch_dialog import BatchDialog
from capture_dialog import CapturePrompt
from completion_dialog import CompletionDialog

def foreground(window):
    window.deiconify();window.lift();window.focus_force()
    window.attributes('-topmost',True)
    window.after(500,lambda:window.attributes('-topmost',False) if window.winfo_exists() else None)
