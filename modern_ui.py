"""Approved SDM alternative B: light/dark sidebar, toolbar and compact HUD."""
import os
import sys
import tkinter as tk
from pathlib import Path
import ttkbootstrap as tb
from PIL import Image, ImageTk
from list_display import COLUMNS, row_values
from utils import format_bytes, format_speed
from capture_policy import capture_enabled


def effective_theme(settings):
    choice = settings.get('theme','light')
    if choice == 'system' and os.name == 'nt':
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,r'Software\Microsoft\Windows\CurrentVersion\Themes\Personalize') as key:
                return 'light' if winreg.QueryValueEx(key,'AppsUseLightTheme')[0] else 'dark'
        except OSError:
            return 'light'
    return 'dark' if choice == 'dark' else 'light'


class ModernUI:
    def _build_ui(self):
        from theme_layouts import build_ui
        build_ui(self)

    def update_action_states(self):
        selected=bool(self.tree.selection())
        for button in self.action_buttons:button.configure(state='normal' if selected else 'disabled')
        self.paint_progress()

    def select_status_filter(self,value):
        self.current_status_filter=value
        for name,button in self.status_buttons.items():button.selected=name==value;button.draw()
        self.refresh_downloads()

    def show_remove_menu(self):
        if not self._get_selected_ids():return
        p=self.palette
        menu=tk.Menu(self,tearoff=0,bg=p['panel'],fg=p['text'],activebackground=p['selected'],activeforeground=p['text'])
        menu.add_command(label='Listeden kaldır — Dosya korunur',command=self.delete_selected)
        menu.add_command(label='Dosyaları da kaldır',command=lambda:self.delete_selected(True))
        menu.tk_popup(self.winfo_pointerx(),self.winfo_pointery())

    def paint_progress(self):
        if not hasattr(self,'_progress_canvases') or not self.tree.winfo_exists():return
        alive=set(self.tree.get_children())
        for key in list(self._progress_canvases):
            if key not in alive:self._progress_canvases.pop(key).destroy()
        for item in alive:
            box=self.tree.bbox(item,'progress')
            canvas=self._progress_canvases.get(item)
            if not box:
                if canvas:canvas.place_forget()
                continue
            if not canvas:
                canvas=tk.Canvas(self.tree,highlightthickness=0,height=7)
                canvas.bind('<Button-1>',lambda event,i=item:self.tree.selection_set(i))
                canvas.bind('<Double-1>',lambda event,i=item:(self.tree.selection_set(i),self.show_selected_details()))
                self._progress_canvases[item]=canvas
            x,y,w,h=box
            values=self.tree.item(item,'values');pct=float(values[5].rstrip('%'))/100
            selected=item in self.tree.selection();canvas.configure(bg=self.palette['selected'] if selected else self.palette['bg'])
            from theme_widgets import rounded
            canvas.place(x=x+8,y=y+h//2-12,width=max(1,w-16),height=24)
            canvas.delete('all');bar=max(1,w-63)
            rounded(canvas,0,8,bar,8,4,fill=self.palette['line'],outline='')
            if pct>0:rounded(canvas,0,8,max(2,bar*pct),8,min(4,bar*pct/2),fill='#49a57b' if values[8]=='Tamamlandı' else self.palette['accent'],outline='')
            canvas.create_text(w-18,12,text=f'{pct*100:.0f}%',fill=self.palette['text'],font=('Segoe UI',9),anchor='e')
        self.paint_status_badges(alive)

    def paint_status_badges(self,alive):
        from theme_widgets import rounded
        for key in list(self._status_canvases):
            if key not in alive:self._status_canvases.pop(key).destroy()
        for item in alive:
            box=self.tree.bbox(item,'status');canvas=self._status_canvases.get(item)
            if not box:
                if canvas:canvas.place_forget()
                continue
            if not canvas:
                canvas=tk.Canvas(self.tree,highlightthickness=0);canvas.bind('<Button-1>',lambda e,i=item:self.tree.selection_set(i));canvas.bind('<Double-1>',lambda e,i=item:self.show_selected_details())
                self._status_canvases[item]=canvas
            x,y,w,h=box;state=self.tree.item(item,'values')[8];p=self.palette
            canvas.configure(bg=p['selected'] if item in self.tree.selection() else p['bg']);canvas.place(x=x+4,y=y+h//2-15,width=max(1,w-8),height=30);canvas.delete('all')
            done=state=='Tamamlandı';fg='#49a57b' if done else p['accent'] if state=='İndiriliyor' else p['muted']
            rounded(canvas,2,2,max(1,w-12),26,10,fill=p['panel'],outline='');canvas.create_text((w-8)/2,15,text=state,fill=fg,font=('Segoe UI',9))

    def sync_caption(self):
        if os.name!='nt':return
        import ctypes
        from ctypes import wintypes
        user=ctypes.WinDLL('user32');user.GetParent.argtypes=[wintypes.HWND];user.GetParent.restype=wintypes.HWND
        hwnd=user.GetParent(self.winfo_id())
        dark=wintypes.BOOL(self.ui_theme=='dark')
        dwm=ctypes.WinDLL('dwmapi');dwm.DwmSetWindowAttribute.argtypes=[wintypes.HWND,wintypes.DWORD,ctypes.c_void_p,wintypes.DWORD]
        dwm.DwmSetWindowAttribute(hwnd,20,ctypes.byref(dark),ctypes.sizeof(dark))

    def update_hud(self):
        videos=[v for v in self.video_tasks.values() if v.status in ('İndiriliyor','Dönüştürülüyor')]
        self.hud_active.set(f'{self.engine.get_active_count()+len(videos)} indirme')
        self.hud_speed.set(format_speed(self.engine.get_total_speed()+sum(v.current_speed for v in videos)))
        self.hud_received.set(format_bytes(sum(self._session_received.values())))
        enabled=capture_enabled(self.settings)
        self.capture_label.configure(text='Yakalama açık' if enabled else 'Yakalama kapalı',bootstyle='success-outline' if enabled else 'secondary-outline')
        mapping={'Belgeler':8,'Resimler':9,'Müzik':10,'Video':11,'Arşivler':12,'Programlar':13}
        for item in self.tree.get_children():
            values=self.tree.item(item,'values');self.tree.item(item,image=self.icon_images[mapping.get(values[9],7)])
        self.paint_progress()
