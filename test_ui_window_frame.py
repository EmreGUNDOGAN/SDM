"""Window frame checks in the runner's fake profile: wheel/middle-drag scrolling
over child widgets and the Windows title bar painted in the design colours."""
def main():
    import ctypes,sys,time
    from ctypes import wintypes
    from unittest.mock import patch
    from PIL import ImageGrab
    from gui import MainWindow
    from modern_settings import SettingsDialog
    from ui_dialog import ScrollBody,SCROLL_TAG
    app=MainWindow();app.engine.stop_engine();errors=[]
    app.report_callback_exception=lambda *args:errors.append(args)
    def descendants(widget):
        for child in widget.winfo_children():
            yield child;yield from descendants(child)
    def disable_fixture_transitions(window):
        # Per-window test setup; do not change the user's animation settings.
        window.update_idletasks()
        dwm=ctypes.WinDLL('dwmapi')
        dwm.DwmSetWindowAttribute.argtypes=[wintypes.HWND,wintypes.DWORD,ctypes.c_void_p,wintypes.DWORD]
        disabled=wintypes.BOOL(True)
        result=dwm.DwmSetWindowAttribute(int(window.tk.call('wm','frame',window._w),0),3,
            ctypes.byref(disabled),ctypes.sizeof(disabled))
        assert result==0,('Could not disable fixture transitions',result)
    def title_bar_rgb(window):
        """Colour of the system caption between the title text and the buttons."""
        # Lift alone leaves an iconic window at (-32000, -32000), with no
        # caption pixels. Restore this process-owned fixture before measuring.
        window.deiconify();window.attributes('-topmost',True);window.lift();window.update()
        user=ctypes.WinDLL('user32',use_last_error=True)
        user.GetWindowRect.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.RECT)]
        user.GetWindowRect.restype=wintypes.BOOL
        try:
            handle=int(window.tk.call('wm','frame',window._w),0)
            deadline=time.monotonic()+2
            while True:
                window.update();rect=wintypes.RECT()
                if not user.GetWindowRect(handle,ctypes.byref(rect)):raise ctypes.WinError(ctypes.get_last_error())
                top=window.winfo_rooty()-rect.top
                if window.state()=='normal' and window.winfo_ismapped() and rect.right>rect.left and top>0:break
                assert time.monotonic()<deadline,(
                    'Caption fixture is not visible',window.state(),(rect.left,rect.top,rect.right,rect.bottom),top)
                time.sleep(.01)
            assert ctypes.WinDLL('dwmapi').DwmFlush()==0,'DWM composition did not complete'
            image=ImageGrab.grab((rect.left,rect.top,rect.right,rect.top+top),all_screens=True)
        finally:window.attributes('-topmost',False)
        return image.getpixel((round(image.width*.55),image.height//2))[:3]
    def close(rgb,color):
        expected=tuple(v//257 for v in app.winfo_rgb(color))
        return all(abs(a-b)<=6 for a,b in zip(rgb,expected)),(rgb,expected)
    try:
        disable_fixture_transitions(app)
        for mode in ('light','dark'):
            app.apply_settings(dict(app.settings,design='atlas',color_mode=mode));app.update()
            dialog=SettingsDialog(app);disable_fixture_transitions(dialog);dialog.geometry('960x520+40+40');app.update()
            body=next(w for w in dialog.tabs.values() if isinstance(w,ScrollBody) and w.winfo_ismapped())
            app.update();assert body.bar.winfo_manager(),'Fixture must overflow to test scrolling'
            # A field deep inside the page, not the bare canvas the old binding needed.
            target=next(w for w in descendants(body.content) if w.winfo_class()=='Canvas' and w.winfo_ismapped())
            assert SCROLL_TAG in target.bindtags()
            body.canvas.yview_moveto(0);app.update()
            target.event_generate('<MouseWheel>',delta=-120,x=5,y=5);app.update()
            after_wheel=body.canvas.yview()[0];assert after_wheel>0,'Wheel over a child did not scroll'
            x,y=target.winfo_rootx()+5,target.winfo_rooty()+5
            target.event_generate('<ButtonPress-2>',x=5,y=5,rootx=x,rooty=y)
            target.event_generate('<B2-Motion>',x=5,y=5,rootx=x,rooty=y+120);app.update()
            assert body.canvas.yview()[0]<after_wheel,'Middle-drag did not scroll'
            # Multi-line text keeps its own wheel instead of moving the page.
            texts=[w for page in dialog.tabs.values() for w in descendants(page) if w.winfo_class()=='Text']
            assert texts and all(SCROLL_TAG not in w.bindtags() for w in texts)
            if sys.getwindowsversion().build>=22000:
                ok,detail=close(title_bar_rgb(dialog),app.palette['dialog']);assert ok,('Settings title bar',mode,detail)
            dialog.destroy();app.update()
            if sys.getwindowsversion().build>=22000:
                # Reproduce the zero-height capture precondition explicitly.
                app.iconify();app.update();assert app.state()=='iconic'
                # Restoration is asynchronous on Windows. Force that delay so
                # a single update() cannot accidentally satisfy the fixture.
                restore=app.deiconify
                with patch.object(app,'deiconify',side_effect=lambda:app.after(500,restore)):
                    ok,detail=close(title_bar_rgb(app),app.palette['bg']);assert ok,('Main title bar',mode,detail)
                assert app.state()=='normal' and app.winfo_ismapped()
        assert not errors,errors
        print('Window frame: wheel and middle-drag over child widgets, Text keeps its wheel, title bar in design colours: OK')
    finally:
        app.engine.stop_engine();app.destroy()


if __name__=='__main__':main()
