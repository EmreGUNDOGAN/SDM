"""Capture a process-owned Tk client inside the screen bounds, even occluded.

Pillow's HWND grab reads a window device context with BitBlt; it does not ask
the owner to render the window. Offscreen pixels can remain stale even with
PrintWindow; reject those targets rather than returning an unreliable image.
"""
import ctypes
from ctypes import wintypes
import os
from PIL import Image


class BitmapInfoHeader(ctypes.Structure):
    _fields_=[('size',wintypes.DWORD),('width',wintypes.LONG),('height',wintypes.LONG),
              ('planes',wintypes.WORD),('bit_count',wintypes.WORD),
              ('compression',wintypes.DWORD),('image_size',wintypes.DWORD),
              ('x_pixels',wintypes.LONG),('y_pixels',wintypes.LONG),
              ('colors_used',wintypes.DWORD),('colors_important',wintypes.DWORD)]


def capture_client(widget):
    if os.name!='nt':raise OSError('Native window capture requires Windows')
    # Native resize/expose events are not serviced by update_idletasks().
    widget.update()
    user=ctypes.WinDLL('user32',use_last_error=True)
    gdi=ctypes.WinDLL('gdi32',use_last_error=True)
    user.GetWindowThreadProcessId.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.DWORD)]
    user.GetWindowThreadProcessId.restype=wintypes.DWORD
    user.GetClientRect.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.RECT)]
    user.GetClientRect.restype=wintypes.BOOL
    user.GetDC.argtypes=[wintypes.HWND];user.GetDC.restype=wintypes.HDC
    user.ReleaseDC.argtypes=[wintypes.HWND,wintypes.HDC];user.ReleaseDC.restype=ctypes.c_int
    user.RedrawWindow.argtypes=[wintypes.HWND,ctypes.c_void_p,ctypes.c_void_p,wintypes.UINT]
    user.RedrawWindow.restype=wintypes.BOOL
    user.PrintWindow.argtypes=[wintypes.HWND,wintypes.HDC,wintypes.UINT]
    user.PrintWindow.restype=wintypes.BOOL
    gdi.CreateCompatibleDC.argtypes=[wintypes.HDC];gdi.CreateCompatibleDC.restype=wintypes.HDC
    gdi.CreateDIBSection.argtypes=[wintypes.HDC,ctypes.POINTER(BitmapInfoHeader),
                                 wintypes.UINT,ctypes.POINTER(ctypes.c_void_p),wintypes.HANDLE,wintypes.DWORD]
    gdi.CreateDIBSection.restype=wintypes.HBITMAP
    gdi.SelectObject.argtypes=[wintypes.HDC,wintypes.HANDLE];gdi.SelectObject.restype=wintypes.HANDLE
    gdi.DeleteObject.argtypes=[wintypes.HANDLE];gdi.DeleteObject.restype=wintypes.BOOL
    gdi.DeleteDC.argtypes=[wintypes.HDC];gdi.DeleteDC.restype=wintypes.BOOL
    gdi.GdiFlush.argtypes=[];gdi.GdiFlush.restype=wintypes.BOOL

    if widget.winfo_toplevel() is not widget:
        raise ValueError('Capture target must be a Tk top-level window')
    # Tk's inner client HWND does not paint its empty background for WM_PRINT.
    # The wm frame is the actual native top-level; PW_CLIENTONLY excludes chrome
    # while preserving both Tk's background and all child controls.
    hwnd=int(widget.tk.call('wm','frame',widget._w),0);pid=wintypes.DWORD()
    user.GetWindowThreadProcessId(hwnd,ctypes.byref(pid))
    if pid.value!=os.getpid():raise ValueError('Capture target must belong to this test process')
    rect=wintypes.RECT()
    if not user.GetClientRect(hwnd,ctypes.byref(rect)):raise ctypes.WinError(ctypes.get_last_error())
    width,height=rect.right-rect.left,rect.bottom-rect.top
    if width<=0 or height<=0:raise ValueError('Capture target has no client area')
    x,y=widget.winfo_rootx(),widget.winfo_rooty()
    if x<0 or y<0 or x+width>widget.winfo_screenwidth() or y+height>widget.winfo_screenheight():
        raise ValueError('Capture target must fit entirely inside the Tk screen')
    screen=user.GetDC(hwnd)
    if not screen:raise ctypes.WinError(ctypes.get_last_error())
    memory=bitmap=previous=None
    try:
        memory=gdi.CreateCompatibleDC(screen)
        if not memory:raise ctypes.WinError(ctypes.get_last_error())
        header=BitmapInfoHeader()
        header.size=ctypes.sizeof(header);header.width=width;header.height=-height
        header.planes=1;header.bit_count=32
        pixels=ctypes.c_void_p()
        bitmap=gdi.CreateDIBSection(screen,ctypes.byref(header),0,ctypes.byref(pixels),None,0)
        if not bitmap or not pixels.value:raise ctypes.WinError(ctypes.get_last_error())
        previous=gdi.SelectObject(memory,bitmap)
        if not previous:raise ctypes.WinError(ctypes.get_last_error())
        # No expected palette is passed to this function or painted into the bitmap.
        ctypes.memset(pixels,0,width*height*4)
        if not user.RedrawWindow(hwnd,None,None,0x0001|0x0004|0x0080|0x0100):
            raise ctypes.WinError(ctypes.get_last_error())
        # WM_PAINT can queue Tk events/idle drawing after native invalidation.
        # Settle those before PrintWindow reads the native window backing store.
        widget.update()
        if not user.PrintWindow(hwnd,memory,1):raise ctypes.WinError(ctypes.get_last_error())
        # CreateDIBSection exposes CPU memory while GDI may still batch drawing.
        # Its documented contract requires completion before ANY pointer access.
        if not gdi.GdiFlush():raise OSError('GDI draw completion failed before bitmap read')
        return Image.frombytes('RGB',(width,height),ctypes.string_at(pixels,width*height*4),'raw','BGRX')
    finally:
        if previous:gdi.SelectObject(memory,previous)
        if bitmap:gdi.DeleteObject(bitmap)
        if memory:gdi.DeleteDC(memory)
        user.ReleaseDC(hwnd,screen)
