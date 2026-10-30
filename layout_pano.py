"""P01/P02 tiled workspace, sharing Atlas actions and native Treeview selection."""
from collections import deque
import tkinter as tk
import time
import ttkbootstrap as tb
from ttkbootstrap.widgets.scrolled import ScrolledFrame
from layout_atlas import AtlasWorkspace, NavButton
from theme_widgets import Button, Panel, Search
from ui_surface import TextLabel, icon, photo, surface, font, text_on
from ui_indicators import ProgressBar, SpeedChart, StatusBadge, FileTile
from ui_overlays import Tooltip, ToastManager
from atlas_view import CATEGORY_TILES
from list_display import COLUMNS
from pano_view import current_transfer, transfer_counts, SUMMARY_FILTERS


class PanoCount(Button):
    """Large count and caption; existing Button owns focus, keys and clicks."""
    def __init__(self,master,caption,command,palette):
        self.count='0';self.caption=caption
        super().__init__(master,'',command,palette=palette,kind='ghost',width=120,height=72)

    def set_count(self,value):
        if self.count==str(value):return
        self.count=str(value);self._draw_signature=None;self.draw()

    def display(self,image):
        width,height=image.size;count_y=26
        cap=-font(28,'Bold').getbbox('H',anchor='ls')[1]
        text_on(image,(width/2,count_y+cap/2),self.count,28,'Bold',self.p['text'],'ms')
        text_on(image,(width/2,52),self.caption,12,fill=self.p['muted'],anchor='mm')
        super().display(image)


class PanoWorkspace(AtlasWorkspace):
    def __init__(self,app):
        self.app=app;self.p=app.palette;self.alive=True;self.menu=None;self.tooltips=[]
        self._disk_due=0;self._disk_busy=False;self.speed_points=deque(maxlen=301)
        self.current_id=None;self._layout=None;self._empty_layout=None;self._list_empty=None;app._atlas_workspace=self;p=self.p
        self.body=tk.Frame(app,bg=p['bg']);self.body.pack(fill='both',expand=True)
        self.body.bind('<Destroy>',self.dispose)
        self.main=self.body
        self.build_header();self.build_footer()
        app.style.configure('Pano.Scroll.TFrame',background=p['bg'])
        self.scroll=ScrolledFrame(self.body,auto_hide=True,style='Pano.Scroll.TFrame')
        self.scroll.pack(fill='both',expand=True,padx=24,pady=(0,24))
        self.scroll._canvas.configure(bg=p['bg'])
        self.dashboard=tk.Frame(self.scroll,bg=p['bg']);self.dashboard.pack(fill='both',expand=True)
        for column in range(4):self.dashboard.columnconfigure(column,weight=1,uniform='pano')
        self.hero=self.card();self.speed_card=self.card();self.summary_card=self.card()
        self.disk_card=self.card();self.list_card=self.card();self.navigation_card=self.card()
        self.build_current();self.build_speed();self.build_summary();self.build_disk()
        self.build_listing();self.build_navigation();self.build_empty()
        self.toast_manager=ToastManager(app,p,self.desktop_notify)
        self.body.bind('<Configure>',self.resize,add='+')
        app.refresh_downloads();app.update_action_states()

    def card(self):
        return Panel(self.dashboard,self.p,padding=20)

    def title(self,parent,text):
        view=TextLabel(parent,text,size=12,weight='SemiBold',fg=self.p['muted'])
        view.pack(anchor='w',pady=(0,12));return view

    def build_header(self):
        app=self.app;p=self.p
        header=tk.Frame(self.body,bg=p['bg']);header.pack(fill='x',padx=24,pady=16)
        mark=surface(32,32,p['bg'],p['accent'],radius=10)
        glyph=icon('download',18,p['on_accent']);mark.paste(glyph,(7,7),glyph)
        app._atlas_logo=photo(mark,app);tk.Label(header,image=app._atlas_logo,bg=p['bg']).pack(side='left')
        TextLabel(header,'SDM',size=17,weight='Bold',fg=p['text']).pack(side='left',padx=(10,24))
        self.new_button=Button(header,'Yeni indirme',app.open_add_dialog,palette=p,kind='start',height=40,width=round(font(13,'SemiBold').getlength('Yeni indirme'))+52)
        self.new_button.icon_name='plus';self.new_button.draw();self.new_button.pack(side='right')
        self.bottom_buttons={}
        for title,glyph,command in (('Ayarlar','settings',app.open_settings_dialog),('Masaüstü HUD','monitor',app.show_mini_hud),('Araçlar','wrench',app.open_tools)):
            button=Button(header,'',command,palette=p,kind='icon',width=40,height=40)
            button.icon_name=glyph;button.draw();button.pack(side='right',padx=(0,8))
            self.bottom_buttons[title]=button;self.tooltips.append(Tooltip(button,title,p))
        app.capture_label=Button(header,'Yakalama açık',app.toggle_capture,palette=p,kind='soft',width=148,height=40)
        app.capture_label.status_badge=True;app.capture_label.pack(side='right',padx=(12,8))
        self.capture_tip=Tooltip(app.capture_label,'Yakalama açık',p);self.tooltips.append(self.capture_tip)
        app.search_var=tk.StringVar(app,getattr(app,'search_term',''))
        self.search_trace=app.search_var.trace_add('write',lambda *args:app._on_search_change())
        search_host=tk.Frame(header,bg=p['bg'],height=40);search_host.pack(side='left',fill='x',expand=True)
        app.search_control=Search(search_host,app.search_var,p,placeholder='Dosya adı veya adres ara',text_size=13)
        app.search_control.place(relx=.5,rely=.5,anchor='center',width=320,height=40)
        search_host.bind('<Configure>',lambda event:app.search_control.place_configure(width=min(480,event.width)))
        self.search_binding=app.bind('<Control-f>',self.focus_search,add='+')
        self.search_upper_binding=app.bind('<Control-F>',self.focus_search,add='+')

    def build_footer(self):
        # Pano presents speed/session/disk in its tiles instead of a second footer.
        pass

    def build_current(self):
        box=self.hero.content;p=self.p
        header=tk.Frame(box,bg=p['panel']);header.pack(fill='x')
        TextLabel(header,'ŞU AN',size=12,weight='SemiBold',fg=p['muted']).pack(side='left')
        self.app.lbl_status_summary=TextLabel(header,'0 aktif',size=12,fg=p['muted'])
        self.app.lbl_status_summary.pack(side='right',padx=(12,0))
        self.current_status=StatusBadge(header,'Bekliyor',p);self.current_status.pack(side='right')
        file_row=tk.Frame(box,bg=p['panel']);file_row.pack(fill='x',pady=(12,0))
        self.current_tile=FileTile(file_row,'FILE',palette=p,size=52);self.current_tile.pack(side='left',padx=(0,16))
        file_text=tk.Frame(file_row,bg=p['panel']);file_text.pack(side='left',fill='x',expand=True)
        self.current_name=TextLabel(file_text,'Etkin indirme yok',size=17,weight='SemiBold',fg=p['text'],max_width=440)
        self.current_name.pack(anchor='w',pady=(0,4))
        self.current_subtitle=TextLabel(file_text,'',size=12,fg=p['muted'],max_width=440);self.current_subtitle.pack(anchor='w')
        row=tk.Frame(box,bg=p['panel']);row.pack(fill='x',pady=(12,0))
        self.current_percent=TextLabel(row,'—',size=56,weight='Bold',fg=p['text']);self.current_percent.pack(side='left')
        self.current_bytes=TextLabel(row,'',size=12,fg=p['muted']);self.current_bytes.pack(side='right')
        self.current_progress=ProgressBar(box,p,0,show_text=False,thickness=12,height=20)
        self.current_progress.pack(fill='x',pady=(2,12))
        metrics=tk.Frame(box,bg=p['panel']);metrics.pack(fill='x')
        self.current_metrics={}
        for column,name in enumerate(('Hız','Kalan','Bağlantı')):
            metrics.columnconfigure(column,weight=1,uniform='metric')
            cell=Panel(metrics,dict(p,panel=p['subtle']),padding=10,radius=14)
            cell.configure(height=70);cell.grid(row=0,column=column,sticky='ew',padx=(0,6 if column<2 else 0))
            TextLabel(cell.content,name,size=12,fg=p['muted']).pack(anchor='w')
            value=TextLabel(cell.content,'—',size=14,weight='SemiBold',fg=p['text']);value.pack(anchor='w',pady=(2,0))
            self.current_metrics[name]=value
        footer=tk.Frame(box,bg=p['panel']);footer.pack(fill='x',side='bottom',pady=(12,0))
        self.current_pause=Button(footer,'Duraklat',self.pause_current,palette=p,kind='primary',height=36)
        self.current_pause.pack(side='right')
        self.current_details=Button(footer,'Ayrıntılar',self.show_current,palette=p,kind='soft',height=36)
        self.current_details.pack(side='right',padx=8)
        self.next_label=TextLabel(footer,'',size=12,fg=p['muted'],max_width=180);self.next_label.pack(side='left')

    def build_speed(self):
        box=self.speed_card.content;p=self.p
        self.title(box,'TOPLAM HIZ')
        self.app.relax_button=Button(box,'Hız sınırı: Yok',self.app.toggle_relax,palette=p,kind='soft',height=30)
        self.app.relax_button.place(relx=1,y=0,anchor='ne')
        self.total_speed=TextLabel(box,textvariable=self.app.hud_speed,size=28,weight='Bold',fg=p['text'])
        self.total_speed.pack(anchor='w')
        self.chart=SpeedChart(box,p,axes=False,height=60);self.chart.pack(fill='both',expand=True)

    def build_summary(self):
        box=self.summary_card.content;p=self.p;self.summary_buttons={}
        for index,(name,title) in enumerate(SUMMARY_FILTERS):
            box.columnconfigure(index%2,weight=1,uniform='count');box.rowconfigure(index//2,weight=1)
            button=PanoCount(box,title,lambda value=name:self.select_status(value),p)
            button.grid(row=index//2,column=index%2,sticky='nsew',padx=2,pady=2)
            self.summary_buttons[name]=(button,title)

    def build_disk(self):
        box=self.disk_card.content;p=self.p
        self.title(box,'İNDİRİLENLER')
        self.disk_value=TextLabel(box,'Disk bilgisi bekleniyor',size=16,weight='SemiBold',fg=p['text'],max_width=250)
        self.disk_value.pack(anchor='w')
        self.app.lbl_status_info=self.disk_value
        TextLabel(box,self.app.settings['download_dir'],size=12,fg=p['muted'],max_width=250).pack(anchor='w',pady=(4,8))
        self.disk_session=TextLabel(box,'Bu oturum 0 B',size=13,fg=p['muted']);self.disk_session.pack(anchor='w')
        Button(box,'Kayıt klasörünü değiştir',lambda:self.open_settings_section('Genel'),palette=p,kind='soft',height=36).pack(side='bottom',fill='x')
        self.disk_progress=ProgressBar(box,p,0,show_text=False,height=16)
        self.disk_progress.pack(side='bottom',fill='x',pady=(12,8))

    def build_listing(self):
        app=self.app;p=self.p;box=self.list_card.content
        self.list_title=TextLabel(box,textvariable=app.page_title,size=15,weight='Bold',fg=p['text'])
        self.list_title.pack(anchor='w')
        self.toolbar=tk.Frame(box,bg=p['panel']);self.toolbar.pack(fill='x',pady=(8,12))
        self.filters=tk.Frame(self.toolbar,bg=p['panel']);self.filters.pack(side='left')
        for name,title in (('Tümü','Tümü'),('Etkin','Etkin'),('Tamamlananlar','Bitti'),('Duraklatılanlar','Durdu'),('Hatalı','Hatalı')):
            button=Button(self.filters,title,lambda value=name:self.select_status(value),palette=p,kind='soft',height=32)
            button.pack(side='left',padx=(0,4));app.status_buttons[name]=button
        self.action_group=tk.Frame(self.toolbar,bg=p['panel']);self.actions={}
        for key,title,glyph,command in (('resume','Devam','play',app.resume_selected),('pause','Duraklat','pause',app.pause_selected),('cancel','İptal','x',app.cancel_selected),('remove','Kaldır ▾','trash',app.show_remove_menu),('folder','Klasör','folder',app.open_folder)):
            button=Button(self.action_group,title,command,palette=p,kind='soft',height=32)
            button.icon_name=glyph;button.draw();button.pack(side='left',padx=(0,4))
            self.actions[key]=button;app.action_buttons.append(button)
        self.queue_button=Button(self.action_group,'Kuyruk ▾',app.show_queue_menu,palette=p,kind='soft',height=32)
        self.queue_button.pack(side='left')
        self.columns_button=Button(self.toolbar,'',app.show_column_menu,palette=p,kind='icon',width=32,height=32)
        self.columns_button.icon_name='columns';self.columns_button.draw();self.columns_button.pack(side='right')
        self.tooltips.append(Tooltip(self.columns_button,'Sütunlar',p))
        self.content=tk.Frame(box,bg=p['panel']);self.content.pack(fill='both',expand=True)
        self.listing=tk.Frame(self.content,bg=p['panel']);self.listing.pack(fill='both',expand=True)
        app.style.configure('SDM.Treeview',rowheight=54)
        app.tree=tb.Treeview(self.listing,columns=(*tuple(c[0] for c in COLUMNS),'actions'),show='headings',selectmode='extended',style='SDM.Treeview',height=6)
        app.tree.column('#0',width=0,minwidth=0,stretch=False)
        widths={'filename':300,'progress':160,'size':105,'status':150}
        for name,title,width in COLUMNS:
            app.tree.heading(name,text=title,command=app.show_column_menu)
            app.tree.column(name,width=widths.get(name,width),minwidth=80,stretch=name=='filename')
        app.tree.heading('actions',text='')
        app.tree.column('actions',width=36,minwidth=36,stretch=False)
        app.apply_visible_columns()
        self.ys=tb.Scrollbar(self.listing,orient='vertical',command=app.tree.yview)
        self.xs=tb.Scrollbar(self.listing,orient='horizontal',command=app.tree.xview)
        app.tree.configure(yscrollcommand=self.scroll_y,xscrollcommand=self.scroll_x)
        app.tree.grid(row=0,column=0,sticky='nsew');self.ys.grid(row=0,column=1,sticky='ns');self.xs.grid(row=1,column=0,sticky='ew')
        self.listing.rowconfigure(0,weight=1);self.listing.columnconfigure(0,weight=1)
        app.tree.bind('<Double-1>',app._on_tree_double_click);app.tree.bind('<Button-3>',app._on_tree_right_click)
        app.tree.bind('<Return>',lambda e:self.invoke_open());app.tree.bind('<<TreeviewSelect>>',lambda e:app.update_action_states())
        from ui_table_surface import TableSurface
        app.data_view=TableSurface(app);app.context_menu=None;app._progress_canvases={};app._status_canvases={}

    def build_navigation(self):
        box=self.navigation_card.content;p=self.p
        self.title(box,'KUYRUKLAR');self.queue_buttons={};self.queue_start_buttons={}
        for queue in self.app.settings['queues']:
            row=tk.Frame(box,bg=p['panel']);row.pack(fill='x')
            name=queue['name']
            start=Button(row,'',lambda value=name:self.app.start_queue(value),palette=p,kind='icon',width=34,height=34)
            start.icon_name='play';start.draw();start.pack(side='right');self.queue_start_buttons[name]=start
            self.tooltips.append(Tooltip(start,name+' · Başlat',p))
            button=NavButton(row,name,lambda value=name:self.select_queue(value),dict(p,side=p['panel']),glyph='queue')
            button.pack(side='left',fill='x',expand=True);self.queue_buttons[name]=button
        self.title(box,'KATEGORİLER')
        categories=tk.Frame(box,bg=p['panel']);categories.pack(fill='x')
        for column in (0,1):categories.columnconfigure(column,weight=1,uniform='category')
        for index,name in enumerate(CATEGORY_TILES):
            button=Button(categories,name,lambda value=name:self.app.select_category(value),palette=p,kind='soft',height=32)
            button.grid(row=index//2,column=index%2,sticky='ew',padx=2,pady=2);self.app.category_buttons[name]=button
        Button(box,'Tüm kategoriler',lambda:self.app.select_category('Tümü'),palette=p,kind='link').pack(anchor='w')

    def build_empty(self):
        app=self.app;p=self.p
        self.empty=tk.Frame(self.list_card.content,bg=p['panel'])
        center=tk.Frame(self.empty,bg=p['panel']);center.place(relx=.5,rely=.5,anchor='center')
        tile=surface(72,72,p['panel'],p['accent_nav'],radius=22)
        glyph=icon('download',30,p['accent']);tile.paste(glyph,(21,21),glyph)
        self.empty_icon=photo(tile,app);tk.Label(center,image=self.empty_icon,bg=p['panel']).pack(pady=(0,20))
        app.empty_label=TextLabel(center,'Henüz indirme yok',size=18,weight='SemiBold',fg=p['text']);app.empty_label.pack()
        TextLabel(center,'Bir bağlantı yapıştır, dosyayı buraya sürükle veya',size=13,fg=p['muted']).pack(pady=(16,4))
        TextLabel(center,'tarayıcıdaki indirmeleri SDM’ye yönlendir.',size=13,fg=p['muted']).pack()
        row=tk.Frame(center,bg=p['panel']);row.pack(pady=24)
        Button(row,'Yeni indirme',app.open_add_dialog,palette=p,kind='start').pack(side='left',padx=6)
        Button(row,'Panodan yapıştır',self.paste,palette=p,kind='soft').pack(side='left',padx=6)
        app.empty_clear=Button(row,'Aramayı temizle',lambda:app.search_var.set(''),palette=p,kind='ghost')
        self.drop_zone=tk.Canvas(center,width=460,height=64,bg=p['panel'],highlightthickness=0)
        self.drop_zone.pack()
        self.drop_zone.create_rectangle(1,1,459,63,outline=p['input_border'],dash=(3,3))
        from ui_tokens import text_px
        self.drop_zone.create_text(230,32,text='Dosya veya bağlantıyı buraya bırak',fill=p['muted'],font=('Inter',text_px(13)))
        self.extension_button=Button(center,'Tarayıcı eklentisini kur',self.extension_help,palette=p,kind='link')
        self.extension_button.pack(pady=(12,0))

    def sync(self,records,all_records):
        if not self.alive:return
        app=self.app;state=getattr(app,'current_status_filter','Tümü');queue=getattr(app,'current_queue_filter',None)
        app.page_title.set(' · '.join(v for v in (queue,app.current_category,state) if v and v!='Tümü') or 'Tüm indirmeler')
        for name,button in app.status_buttons.items():button.selected=name==state and not queue;button.draw()
        for name,button in app.category_buttons.items():button.selected=name==app.current_category;button.draw()
        for name,button in self.queue_buttons.items():button.selected=name==queue;button.set_count(sum(r.get('queue_name')==name for r in all_records));button.draw()
        self.update_counts(all_records)
        if records:
            self.empty.pack_forget();self.content.pack(fill='both',expand=True)
        else:
            self.content.pack_forget();self.empty.pack(fill='both',expand=True)
            app.empty_label.configure(text='Aramanızla eşleşen indirme bulunamadı' if app.search_term else 'Bu görünümde henüz indirme yok' if all_records else 'Henüz indirme yok')
            if app.search_term:app.empty_clear.pack(side='left',padx=6)
            else:app.empty_clear.pack_forget()
        if all_records:
            if not self.toolbar.winfo_manager():self.toolbar.pack(fill='x',pady=(8,12),before=self.content if records else self.empty)
            if not self.list_title.winfo_manager():self.list_title.pack(anchor='w',before=self.toolbar)
        else:self.list_title.pack_forget();self.toolbar.pack_forget()
        self.update_current(all_records);self.update_selection();self.arrange(self.body.winfo_width())

    def update_current(self,records):
        view=current_transfer(self.app,records);self.current_id=view['id'] if view else None
        self.current_tile.extension=view['extension'] if view else 'FILE'
        self.current_tile.kind=view['kind'] if view else 'other';self.current_tile.draw()
        self.current_name.configure(text=view['name'] if view else 'Şu an aktif indirme yok')
        self.current_subtitle.configure(text=view['subtitle'] if view else 'Başlatmak için kuyruğu seçebilirsiniz.')
        self.current_percent.configure(text=f'{view["progress"]:.0%}' if view else '—')
        self.current_bytes.configure(text=f'{view["received"]} / {view["total"]}' if view else '')
        self.current_progress.set(view['progress'] if view else 0,view['status'] if view else 'Bekliyor')
        self.current_status.set(view['status'] if view else 'Bekliyor')
        for key,value in (('Hız','speed'),('Kalan','eta'),('Bağlantı','connections')):self.current_metrics[key].configure(text=view[value] if view else '—')
        self.next_label.configure(text='Sırada · '+view['next_name'] if view else '')
        self.current_details.configure(state='normal' if view else 'disabled')
        from atlas_view import available_actions
        can_pause=view and available_actions((view['status'],))['pause']
        pending=any(r['status'] not in ('Tamamlandı','İptal Edildi') for r in records)
        self.current_pause.configure(text='Duraklat' if view else 'Kuyruğu başlat',
            command=self.pause_current if view else self.start_current_queue,
            state='normal' if can_pause or (not view and pending) else 'disabled')

    def start_current_queue(self):
        self.app.start_queue(getattr(self.app,'current_queue_filter',None))

    def update_counts(self,records):
        counts=transfer_counts(self.app,records)
        for name,(button,title) in self.summary_buttons.items():button.set_count(counts[name])

    def show_current(self):
        if self.current_id is not None:self.app.show_download_details(self.current_id)

    def pause_current(self):
        if self.current_id is None:return
        # Operate on this card's explicit transfer, without changing a multi-selection.
        self.app.pause_download(self.current_id)

    def update_selection(self):
        if not self.alive:return
        selected=bool(self.app.tree.selection());caps=self.capabilities()
        for key,button in self.actions.items():button.configure(state='normal' if caps[key] else 'disabled')
        self.queue_button.configure(state='normal' if caps['queue'] else 'disabled')
        if selected:self.filters.pack_forget();self.action_group.pack(side='left')
        else:self.action_group.pack_forget();self.filters.pack(side='left')

    def update_hud(self,speed):
        # Share capture/rate controls and the disk worker without building Atlas's footer.
        self.update_capture_and_rate();self.update_disk();self.update_selection()
        from capture_policy import capture_enabled
        self.app.capture_label.configure(text='Yakalama açık' if capture_enabled(self.app.settings) else 'Yakalama kapalı')
        self.app.lbl_status_summary.configure(text=self.app.hud_active.get()+' aktif')
        self.disk_session.configure(text='Bu oturum '+self.app.hud_received.get())
        now=time.monotonic()
        self.speed_points.append((now,speed))
        while self.speed_points and self.speed_points[0][0]<now-300:self.speed_points.popleft()
        self.chart.set(tuple(self.speed_points))
        usage=getattr(self,'disk_usage',None)
        if usage:self.disk_progress.set(usage.used/usage.total if usage.total else 0)
        self.update_current(getattr(self.app,'_all_records',()))
        self.update_counts(getattr(self.app,'_all_records',()))

    def resize(self,event):
        if event.widget is not self.body:return
        self.arrange(event.width)

    def arrange(self,width):
        compact=width<1280;empty=not getattr(self.app,'_all_records',())
        list_empty=not getattr(self.app,'_visible_records',{})
        self.current_name.max_width=max(180,width//2-168);self.current_name.draw()
        self.current_subtitle.max_width=self.current_name.max_width;self.current_subtitle.draw()
        for button in self.actions.values():button.icon_only=compact;button.configure(width=36 if compact else round(font(13).getlength(button.text))+52)
        if (compact,empty,list_empty)==(self._layout,self._empty_layout,self._list_empty):return
        self._layout=compact;self._empty_layout=empty;self._list_empty=list_empty
        for card in (self.hero,self.speed_card,self.summary_card,self.disk_card,self.list_card,self.navigation_card):card.grid_forget()
        for column in range(4):
            active=column<(2 if compact else 4)
            self.dashboard.columnconfigure(column,weight=1 if active else 0,minsize=0,uniform='pano' if active else '')
        if empty:
            self.list_card.configure(height=560 if compact else 760)
            self.list_card.grid(row=0,column=0,columnspan=2 if compact else 3,rowspan=1 if compact else 2,sticky='nsew',padx=8,pady=8)
            for card,row,column,height in ((self.speed_card,1 if compact else 0,0 if compact else 3,230),(self.disk_card,1,1 if compact else 3,300)):
                card.configure(height=height);card.grid(row=row,column=column,sticky='nsew',padx=8,pady=8)
            return
        navigation_height=max(350,302+34*len(self.app.settings['queues']))
        positions=((self.hero,0,0,2,400),(self.speed_card,1 if compact else 0,0 if compact else 2,2,190),
            (self.summary_card,2 if compact else 1,0 if compact else 2,1,225),(self.disk_card,2 if compact else 1,1 if compact else 3,1,225),
            (self.list_card,3 if compact else 2,0,2 if compact else 3,560 if list_empty else 350),(self.navigation_card,4 if compact else 2,0 if compact else 3,2 if compact else 1,navigation_height))
        for card,row,column,span,height in positions:
            card.configure(height=height)
            card.grid(row=row,column=column,columnspan=span,rowspan=2 if card is self.hero and not compact else 1,sticky='nsew',padx=8,pady=8)


def build(app):return PanoWorkspace(app)
