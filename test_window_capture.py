"""Model deferred native GDI writes; pixel access must wait for completion."""
import ctypes
from ctypes import wintypes
import os
from types import SimpleNamespace
import unittest
from unittest.mock import Mock,patch
from tools.window_capture import capture_client


@unittest.skipUnless(os.name=='nt','Windows capture contract')
class WindowCaptureTests(unittest.TestCase):
    def backend(self,flush_ok=True,owner=None):
        # The print call queues drawing. Only GdiFlush makes its bytes visible,
        # matching the asynchronous DIB access contract rather than call timing.
        buffer=ctypes.create_string_buffer(16);queued=[]
        user=SimpleNamespace(**{name:Mock(return_value=1) for name in (
            'GetWindowThreadProcessId','GetClientRect','GetDC','ReleaseDC',
            'RedrawWindow','PrintWindow')})
        gdi=SimpleNamespace(**{name:Mock(return_value=1) for name in (
            'CreateCompatibleDC','CreateDIBSection','SelectObject','DeleteObject',
            'DeleteDC','GdiFlush')})
        def process(hwnd,pid):
            ctypes.cast(pid,ctypes.POINTER(wintypes.DWORD)).contents.value=os.getpid() if owner is None else owner
            return 1
        def dimensions(hwnd,rect):
            value=ctypes.cast(rect,ctypes.POINTER(wintypes.RECT)).contents
            value.right=2;value.bottom=2;return 1
        def allocate(dc,header,usage,bits,section,offset):
            ctypes.cast(bits,ctypes.POINTER(ctypes.c_void_p)).contents.value=ctypes.addressof(buffer)
            return 1
        def draw(hwnd,dc,flags):
            queued.append(bytes((22,17,14,0))*4);return 1
        def flush():
            if not flush_ok:return 0
            for data in queued:ctypes.memmove(buffer,data,len(data))
            queued.clear();return 1
        user.GetWindowThreadProcessId.side_effect=process;user.GetClientRect.side_effect=dimensions
        user.PrintWindow.side_effect=draw;gdi.CreateDIBSection.side_effect=allocate
        gdi.GdiFlush.side_effect=flush
        widget=SimpleNamespace(update_idletasks=Mock(),update=Mock(),_w='.',tk=SimpleNamespace(call=Mock(return_value='0x1')))
        widget.winfo_toplevel=lambda:widget
        widget.winfo_rootx=widget.winfo_rooty=lambda:0
        widget.winfo_screenwidth=widget.winfo_screenheight=lambda:2
        return widget,user,gdi,buffer

    def test_deferred_drawing_is_visible_before_cpu_pixel_read(self):
        widget,user,gdi,buffer=self.backend()
        with patch('tools.window_capture.ctypes.WinDLL',side_effect=[user,gdi]):
            image=capture_client(widget)
        self.assertEqual(image.getpixel((0,0)),(14,17,22))
        self.assertEqual(image.getpixel((1,1)),(14,17,22))
        self.assertEqual(image.size,(2,2))
        gdi.DeleteObject.assert_called_once();gdi.DeleteDC.assert_called_once();user.ReleaseDC.assert_called_once()

    def test_failed_draw_completion_is_an_error_and_releases_handles(self):
        widget,user,gdi,buffer=self.backend(flush_ok=False)
        with patch('tools.window_capture.ctypes.WinDLL',side_effect=[user,gdi]):
            with self.assertRaises(OSError):capture_client(widget)
        gdi.DeleteObject.assert_called_once();gdi.DeleteDC.assert_called_once();user.ReleaseDC.assert_called_once()

    def test_redraw_generated_native_events_are_processed_before_print(self):
        widget,user,gdi,buffer=self.backend()
        queued={'pending':False,'painted':False}
        def invalidate(*args):
            queued['pending']=True;return 1
        def dispatch():
            if queued['pending']:queued['painted']=True
        original_draw=user.PrintWindow.side_effect
        def print_current(*args):
            if queued['painted']:return original_draw(*args)
            ctypes.memset(buffer,255,16);return 1
        user.RedrawWindow.side_effect=invalidate;widget.update.side_effect=dispatch
        user.PrintWindow.side_effect=print_current
        with patch('tools.window_capture.ctypes.WinDLL',side_effect=[user,gdi]):
            image=capture_client(widget)
        self.assertEqual(image.getpixel((1,1)),(14,17,22))

    def test_other_process_windows_are_rejected_before_getting_a_dc(self):
        widget,user,gdi,buffer=self.backend(owner=os.getpid()+1)
        with patch('tools.window_capture.ctypes.WinDLL',side_effect=[user,gdi]):
            with self.assertRaisesRegex(ValueError,'belong'):capture_client(widget)
        user.GetDC.assert_not_called()

    def test_partly_offscreen_target_is_rejected_before_capture(self):
        widget,user,gdi,buffer=self.backend()
        widget.winfo_rootx=lambda:1
        with patch('tools.window_capture.ctypes.WinDLL',side_effect=[user,gdi]):
            with self.assertRaisesRegex(ValueError,'fit entirely'):capture_client(widget)
        user.GetDC.assert_not_called();user.PrintWindow.assert_not_called()


if __name__=='__main__':unittest.main()
