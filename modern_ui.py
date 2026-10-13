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
        self.ui_theme = effective_theme(self.settings)
        self.after_idle(self.sync_caption)
        dark = self.ui_theme == 'dark'
        self.style.theme_use('darkly' if dark else 'cosmo')
        self.palette = {'bg':'#151d29' if dark else '#ffffff',
            'panel':'#111925' if dark else '#f8fafd', 'text':'#e8eef7' if dark else '#172331',
            'muted':'#8fa2bd' if dark else '#728097', 'selected':'#1c3049' if dark else '#e7effb',
            'line':'#2a374a' if dark else '#e4e9f0'}
        p=self.palette
        self.configure(background=p['bg'])
        self.style.configure('.',font=('Segoe UI',10),foreground=p['text'],background=p['bg'])
        self.style.configure('TLabel',foreground=p['text'],background=p['bg'])
        self.style.configure('TEntry',foreground=p['text'],fieldbackground=p['panel'])
        self.style.configure('SDM.Treeview',foreground=p['text'],background=p['bg'],fieldbackground=p['bg'],rowheight=54,font=('Segoe UI',10),borderwidth=0)
        self.style.configure('SDM.Treeview.Heading',foreground=p['muted'],background=p['panel'],font=('Segoe UI',9,'bold'),padding=(6,12))
        self.style.map('SDM.Treeview',foreground=[('selected',p['text'])],background=[('selected',p['selected'])])
        self.style.configure('SDM.Side.TFrame',background=p['panel'])
        self.style.configure('SDM.Side.TLabel',background=p['panel'],foreground=p['muted'])
        self.style.configure('SDM.HUD.TLabel',background=p['panel'],foreground=p['text'],font=('Segoe UI',14,'bold'))
        root=Path(getattr(sys,'_MEIPASS',Path(__file__).parent))
        self.icon_images={i:tk.PhotoImage(master=self,file=str(root/'assets/icons'/self.ui_theme/f'{i:02}.png')) for i in range(18)}
        self._sidebar_logo=ImageTk.PhotoImage(Image.open(root/'assets/logo.png').resize((42,42)),master=self)
        body=tb.Frame(self);body.pack(fill='both',expand=True)
        sidebar=tb.Frame(body,width=220,padding=18,style='SDM.Side.TFrame')
        sidebar.pack(side='left',fill='y');sidebar.pack_propagate(False)
        brand=tb.Frame(sidebar,style='SDM.Side.TFrame');brand.pack(fill='x',pady=(10,25))
        tb.Label(brand,image=self._sidebar_logo,style='SDM.Side.TLabel').pack(side='left',padx=(0,12))
        tb.Label(brand,text='SDM',font=('Segoe UI',23,'bold'),style='SDM.Side.TLabel').pack(side='left')
        tb.Label(sidebar,text='İNDİRMELER',font=('Segoe UI',9,'bold'),style='SDM.Side.TLabel').pack(anchor='w',pady=(0,12))
        self.category_buttons={}
        categories=[('Tümü',7),('Devam Edenler',14),('Tamamlananlar',15),('Belgeler',8),('Resimler',9),('Müzik',10),('Video',11),('Arşivler',12),('Programlar',13),('Diğer',7)]
        for index,(name,icon) in enumerate(categories):
            if index == 3:
                tb.Label(sidebar,text='KATEGORİLER',font=('Segoe UI',9,'bold'),style='SDM.Side.TLabel').pack(anchor='w',pady=(25,12))
            label='Tüm indirmeler' if name=='Tümü' else name
            button=tb.Button(sidebar,text='  '+label,image=self.icon_images[icon],compound='left',bootstyle='secondary-link',command=lambda c=name:self.select_category(c))
            button.pack(fill='x',pady=3,ipady=4);self.category_buttons[name]=button
        tb.Button(sidebar,text='  Ayarlar',image=self.icon_images[5],compound='left',bootstyle='secondary-link',command=self.open_settings_dialog).pack(side='bottom',fill='x',pady=8)
        tb.Button(sidebar,text='İndirme araçları',bootstyle='secondary-link',command=self.open_tools).pack(side='bottom',fill='x')
        tb.Button(sidebar,text='Küçük masaüstü HUD’u',bootstyle='secondary-link',command=self.show_mini_hud).pack(side='bottom',fill='x')
        main=tb.Frame(body,padding=(26,22));main.pack(side='left',fill='both',expand=True)
        heading=tb.Frame(main);heading.pack(fill='x')
        tb.Label(heading,text='İndirme merkezi',font=('Segoe UI',23,'bold')).pack(side='left')
        self.capture_label=tb.Button(heading,text='Yakalama açık',bootstyle='success-outline',command=self.toggle_capture)
        self.capture_label.pack(side='right')
        tb.Label(main,text='Tüm dosyaların, tek bir düzenli çalışma alanında.',foreground=p['muted']).pack(anchor='w',pady=(6,24))
        toolbar=tb.Frame(main);toolbar.pack(fill='x',pady=(0,20))
        tb.Button(toolbar,text=' Yeni indirme',image=self.icon_images[0],compound='left',bootstyle='primary',command=self.open_add_dialog).pack(side='left',ipady=5,padx=(0,14))
        for icon,action in [(1,self.resume_selected),(2,self.pause_selected),(3,self.cancel_selected),(4,self.delete_selected)]:
            tb.Button(toolbar,image=self.icon_images[icon],bootstyle='secondary-outline',command=action).pack(side='left',padx=3,ipady=4)
        tb.Button(toolbar,text='Kuyruk',bootstyle='secondary-outline',command=self.show_queue_menu).pack(side='left',padx=10,ipady=5)
        self.relax_button=tb.Button(toolbar,text='Rahatlat: açık' if self.settings.get('relax_mode') else 'İnterneti rahatlat',bootstyle='secondary-outline',command=self.toggle_relax)
        self.relax_button.pack(side='left',ipady=5)
        tb.Button(toolbar,text=' Sütunlar',image=self.icon_images[6],compound='left',bootstyle='secondary-outline',command=self.show_column_menu).pack(side='right',padx=(10,0),ipady=4)
        self.search_var=tk.StringVar(value=getattr(self,'search_term',''))
        self.search_var.trace_add('write',lambda *args:self._on_search_change())
        tb.Entry(toolbar,textvariable=self.search_var,width=22).pack(side='right',ipady=5)
        hud=tb.Frame(main,padding=12,style='SDM.Side.TFrame');hud.pack(fill='x',pady=(0,20))
        self.hud_active=tk.StringVar(value='0 indirme');self.hud_speed=tk.StringVar(value='0 KB/s');self.hud_received=tk.StringVar(value='0 B')
        for label,var in [('AKTİF',self.hud_active),('TOPLAM HIZ',self.hud_speed),('BU OTURUM',self.hud_received)]:
            group=tb.Frame(hud,style='SDM.Side.TFrame');group.pack(side='left',fill='x',expand=True)
            tb.Label(group,text=label,style='SDM.Side.TLabel',font=('Segoe UI',9,'bold')).pack(side='left',padx=(0,18))
            tb.Label(group,textvariable=var,style='SDM.HUD.TLabel').pack(side='left')
        listing=tb.Frame(main);listing.pack(fill='both',expand=True)
        self.tree=tb.Treeview(listing,columns=tuple(c[0] for c in COLUMNS),show='tree headings',selectmode='extended',style='SDM.Treeview')
        self.tree.column('#0',width=38,minwidth=38,stretch=False)
        for name,label,width in COLUMNS:
            self.tree.heading(name,text=label,command=self.show_column_menu)
            self.tree.column(name,width=300 if name=='filename' else width,anchor='w' if name=='filename' else 'center')
        self.apply_visible_columns()
        ys=tb.Scrollbar(listing,orient='vertical',command=self.tree.yview)
        xs=tb.Scrollbar(listing,orient='horizontal',command=self.tree.xview)
        self.tree.configure(yscrollcommand=ys.set,xscrollcommand=xs.set)
        self.tree.grid(row=0,column=0,sticky='nsew');ys.grid(row=0,column=1,sticky='ns');xs.grid(row=1,column=0,sticky='ew')
        listing.rowconfigure(0,weight=1);listing.columnconfigure(0,weight=1)
        self.tree.bind('<Double-1>',self._on_tree_double_click);self.tree.bind('<Button-3>',self._on_tree_right_click)
        self.tree.bind('<Configure>',lambda e:self.after_idle(self.paint_progress))
        self.context_menu=tk.Menu(self,tearoff=0)
        priority=tk.Menu(self.context_menu,tearoff=0)
        for label,value in [('Yüksek',1),('Normal',0),('Düşük',-1)]:priority.add_command(label=label,command=lambda v=value:self.change_priority(v))
        self.context_menu.add_cascade(label='İndirme önceliği',menu=priority)
        self.context_menu.add_command(label='Hız grafiği',command=self.show_speed_graph)
        for label,command in [('Devam et',self.resume_selected),('Sıfırdan indir',self.restart_selected),('Kuyruğa ekle',self.queue_selected),('Duraklat',self.pause_selected),('İptal et',self.cancel_selected),('Dosyayı aç',self.open_file),('Klasörü göster',self.open_folder),('SHA-256 kontrolü',self.verify_selected),('Listeden kaldır',self.delete_selected),('Dosyayla birlikte sil',lambda:self.delete_selected(True)),('İndirme ayrıntıları',self.show_selected_details)]:
            self.context_menu.add_command(label=label,command=command)
        self.statusbar=tb.Frame(main,padding=(0,12,0,0));self.statusbar.pack(fill='x')
        self.lbl_status_summary=tb.Label(self.statusbar,text='SDM hazır',foreground=p['muted']);self.lbl_status_summary.pack(side='left')
        self.lbl_status_info=tb.Label(self.statusbar,text='Sağ tık ile diğer işlemler',foreground=p['muted']);self.lbl_status_info.pack(side='right')
        self._progress_canvases={}
        self.select_category(getattr(self,'current_category','Tümü'))

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
            canvas.place(x=x+8,y=y+h-11,width=max(1,w-16),height=6)
            canvas.delete('all');canvas.create_rectangle(0,0,w-16,6,fill=self.palette['line'],outline='')
            canvas.create_rectangle(0,0,max(0,w-16)*pct,6,fill='#49a57b' if values[8]=='Tamamlandı' else '#3c7bc8',outline='')

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
