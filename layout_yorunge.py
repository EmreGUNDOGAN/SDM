"""F01/F02 control workspace; Atlas owns actions, menus and disk worker."""
from collections import deque
import time
import tkinter as tk
import ttkbootstrap as tb
from ttkbootstrap.widgets.scrolled import ScrolledFrame
from layout_atlas import AtlasWorkspace
from theme_widgets import Button,Panel,Search
from ui_surface import TextLabel,photo,surface,icon,text_on,ellipsize
from ui_indicators import ProgressRing,SpeedChart
from ui_overlays import ToastManager,Tooltip
from ui_tokens import text_px,file_tile_colors
from atlas_view import CATEGORY_TILES,matches_status,number,domain
from list_display import COLUMNS
from yorunge_view import telemetry,target
from yorunge_indicators import SpeedGauge,Radar,ConnectionColumns


class CircuitGrid(tk.Canvas):
    def __init__(self,master,palette):
        self.p=palette
        super().__init__(master,bg=palette['bg'],highlightthickness=0)
        self.bind('<Configure>',self.resize)
    def resize(self,event):
        if event.widget is not self:return
        self.delete('grid')
        for x in range(0,event.width,40):self.create_line(x,0,x,event.height,fill=self.p['grid_line'],tags='grid')
        for y in range(0,event.height,40):self.create_line(0,y,event.width,y,fill=self.p['grid_line'],tags='grid')


class OrbitNav(Button):
    def __init__(self,master,text,command,palette,prefix='',color=None):
        self.prefix=prefix;self.count='';self.color=color
        super().__init__(master,text,command,palette=palette,kind='ghost',height=34,width=196)
    def set_count(self,value):
        if self.count==str(value):return
        self.count=str(value);self._draw_signature=None;self.draw()
    def draw(self):
        if not self.winfo_exists():return
        from PIL import ImageDraw
        p=self.p;w=max(1,self.winfo_width() if self.winfo_width()>1 else int(self.cget('width')));h=int(self.cget('height'))
        signature=(w,h,self.text,self.count,self.selected,self.hover,self.focused)
        if signature==getattr(self,'_draw_signature',None):return
        self._draw_signature=signature
        image=surface(w,h,self.cget('bg'),p['accent_soft'] if self.selected or self.hover else self.cget('bg'),radius=0)
        d=ImageDraw.Draw(image)
        if self.selected:d.rectangle((0,0,1,h),fill=p['accent'])
        if self.color:d.rectangle((12,h//2-3,18,h//2+3),fill=self.color)
        else:text_on(image,(12,h/2),self.prefix,10,fill=p['muted'],anchor='lm',family='JetBrains Mono')
        title=self.label_text(self.text);fg=p['accent'] if self.selected else p['text_2']
        text_on(image,(38,h/2),ellipsize(title,w-88,11,family='JetBrains Mono'),11,fill=fg,anchor='lm',family='JetBrains Mono')
        text_on(image,(w-10,h/2),self.count,10,fill=fg,anchor='rm',family='JetBrains Mono')
        self.display(image)


class YorungeWorkspace(AtlasWorkspace):
    def __init__(self,app):
        self.app=app;self.p=app.palette;self.alive=True;self.menu=None;self.tooltips=[]
        self._disk_due=0;self._disk_busy=False;self.speed_points=deque(maxlen=301);self._compact=None
        self.target_snapshot=None;app._atlas_workspace=self;p=self.p
        self.body=tk.Frame(app,bg=p['bg']);self.body.pack(fill='both',expand=True);self.body.bind('<Destroy>',self.dispose)
        self.build_header();self.build_footer()
        self.workspace=tk.Frame(self.body,bg=p['bg']);self.workspace.pack(fill='both',expand=True)
        self.workspace.rowconfigure(0,weight=1);self.workspace.columnconfigure(1,weight=1)
        self.build_side()
        app.style.configure('Orbit.Scroll.TFrame',background=p['bg'])
        self.scroll=ScrolledFrame(self.workspace,auto_hide=True,style='Orbit.Scroll.TFrame')
        self.scroll.grid(row=0,column=1,sticky='nsew');self.scroll._canvas.configure(bg=p['bg'])
        self.dashboard=CircuitGrid(self.scroll,p);self.dashboard.pack(fill='both',expand=True);self.dashboard.columnconfigure(0,weight=1)
        self.telemetry=Panel(self.dashboard,p,padding=16);self.telemetry.grid(row=0,column=0,sticky='ew',padx=18,pady=(18,0))
        self.build_telemetry()
        self.list_card=Panel(self.dashboard,p,padding=12);self.list_card.configure(height=440)
        self.list_card.grid(row=1,column=0,sticky='nsew',padx=18,pady=16);self.dashboard.rowconfigure(1,weight=1)
        self.main=self.list_card.content
        self.build_listing();self.build_empty();self.build_target()
        self.toast_manager=ToastManager(app,p,self.desktop_notify)
        self.body.bind('<Configure>',self.resize,add='+')
        app.refresh_downloads();app.update_action_states();self.update_hud(0)

    def label(self,parent,text='',size=11,muted=False,mono=True,**kwargs):
        item=TextLabel(parent,text,size=size,fg=kwargs.pop('fg',self.p['muted'] if muted else self.p['text']),family='JetBrains Mono' if mono else 'Inter',**kwargs)
        return item

    def build_header(self):
        app=self.app;p=self.p
        header=tk.Frame(self.body,bg=p['side']);header.pack(fill='x',padx=18,pady=12)
        mark=surface(36,36,p['side'],p['side'],radius=0)
        from PIL import ImageDraw
        d=ImageDraw.Draw(mark);d.polygon([(18,1),(35,18),(18,35),(1,18)],outline=p['accent'],width=1)
        glyph=icon('download',16,p['accent']);mark.paste(glyph,(10,10),glyph);app._atlas_logo=photo(mark,app)
        tk.Label(header,image=app._atlas_logo,bg=p['side']).pack(side='left')
        brand=tk.Frame(header,bg=p['side']);brand.pack(side='left',padx=(10,24))
        self.label(brand,'SDM',size=16,weight='Bold').pack(anchor='w');self.label(brand,'İNDİRME KONTROL',size=9,muted=True).pack(anchor='w')
        self.new_button=Button(header,'Yeni indirme',app.open_add_dialog,palette=p,kind='primary',height=40)
        self.new_button.pack(side='right')
        settings=Button(header,'',app.open_settings_dialog,palette=p,kind='icon',width=36,height=36)
        settings.icon_name='settings';settings.draw();settings.pack(side='right',padx=10);self.tooltips.append(Tooltip(settings,'Ayarlar',p))
        app.capture_label=Button(header,'Yakalama kapalı',app.toggle_capture,palette=p,kind='ghost',width=180,height=36)
        app.capture_label.status_badge=True;app.capture_label.pack(side='right',padx=(10,0))
        self.capture_tip=Tooltip(app.capture_label,'Tarayıcı yakalama',p);self.tooltips.append(self.capture_tip)
        app.search_var=tk.StringVar(app,getattr(app,'search_term',''))
        self.search_trace=app.search_var.trace_add('write',lambda *args:app._on_search_change())
        host=tk.Frame(header,bg=p['side'],height=40);host.pack(side='left',fill='x',expand=True)
        app.search_control=Search(host,app.search_var,p,placeholder='Dosya adı veya adres ara · Ctrl+K',text_size=12)
        app.search_control.place(x=0,rely=.5,anchor='w',relwidth=1,height=40)
        self.search_binding=app.bind('<Control-f>',self.focus_search,add='+');self.search_upper_binding=app.bind('<Control-F>',self.focus_search,add='+')
        self.command_bindings=[(sequence,app.bind(sequence,self.focus_search,add='+')) for sequence in ('<Control-k>','<Control-K>')]
        tk.Frame(self.body,bg=p['line'],height=1).pack(fill='x')

    def build_footer(self):
        app=self.app;p=self.p
        footer=tk.Frame(self.body,bg=p['side']);footer.pack(side='bottom',fill='x')
        tk.Frame(footer,bg=p['line'],height=1).pack(fill='x')
        row=tk.Frame(footer,bg=p['side']);row.pack(fill='x',padx=18,pady=7)
        self.label(row,'● SİSTEM HAZIR',size=10,fg=p['success']).pack(side='left',padx=(0,20))
        app.lbl_status_summary=self.label(row,'0 AKTİF',size=10);app.lbl_status_summary.pack(side='left',padx=(0,20))
        self.received_label=self.label(row,'BU OTURUM 0 B',size=10,muted=True);self.received_label.pack(side='left')
        from app_version import VERSION
        self.label(row,'SDM '+VERSION,size=10,muted=True).pack(side='right')
        app.lbl_status_info=self.label(row,'Disk bilgisi bekleniyor',size=10,muted=True,max_width=260)
        app.lbl_status_info.pack(side='right',padx=16)

    def build_side(self):
        app=self.app;p=self.p
        side=tk.Frame(self.workspace,bg=p['side'],width=220);side.grid(row=0,column=0,sticky='ns');side.pack_propagate(False)
        bottom=tk.Frame(side,bg=p['side']);bottom.pack(side='bottom',fill='x',padx=10,pady=10)
        self.bottom_buttons={}
        for text,glyph,command in (('Araçlar','wrench',app.open_tools),('İstatistik','chart',app.open_stats),('Masaüstü HUD','monitor',app.show_mini_hud),('Ayarlar','settings',app.open_settings_dialog)):
            button=Button(bottom,'> '+text,command,palette=p,kind='link',height=30);button.pack(fill='x');self.bottom_buttons[text]=button
        app.style.configure('Orbit.Side.TFrame',background=p['side'])
        app.sidebar_scroll=ScrolledFrame(side,width=218,auto_hide=True,style='Orbit.Side.TFrame');app.sidebar_scroll.pack(fill='both',expand=True)
        app.sidebar_scroll._canvas.configure(bg=p['side']);self.nav=tk.Frame(app.sidebar_scroll,bg=p['side']);self.nav.pack(fill='x',padx=10)
        def caption(text):self.label(self.nav,'// '+text,size=10,muted=True).pack(anchor='w',padx=8,pady=(16,8))
        caption('DURUM')
        for index,(key,title) in enumerate((('Tümü','Tümü'),('Etkin','Etkin'),('Kuyrukta','Kuyruk'),('Tamamlananlar','Tamam'),('Hatalı','Hata')),1):
            button=OrbitNav(self.nav,title,lambda value=key:self.select_status(value),p,prefix=f'{index:02}')
            button.pack(fill='x');button.bind('<FocusIn>',self.reveal_nav,add='+');app.status_buttons[key]=button
        caption('TÜR')
        for key,(_,kind) in CATEGORY_TILES.items():
            button=OrbitNav(self.nav,key,lambda value=key:app.select_category(value),p,color=file_tile_colors(kind,'dark','yorunge')[1])
            button.pack(fill='x');button.bind('<FocusIn>',self.reveal_nav,add='+');app.category_buttons[key]=button
        Button(self.nav,'Tüm türler',lambda:app.select_category('Tümü'),palette=p,kind='link',height=30).pack(fill='x')
        caption('KUYRUK');self.queue_buttons={}
        self.queue_selector=Button(self.nav,'Kuyruklar ▾',app.show_queue_menu,palette=p,kind='secondary',height=34);self.queue_selector.pack(fill='x')
        for queue in app.settings['queues']:
            name=queue['name'];button=OrbitNav(self.nav,name,lambda value=name:self.select_queue(value),p,prefix='>')
            button.pack(fill='x');button.bind('<FocusIn>',self.reveal_nav,add='+');self.queue_buttons[name]=button

    def build_telemetry(self):
        p=self.p;box=self.telemetry.content
        self.gauge=SpeedGauge(box,p,lambda value:number(self.app,value))
        self.chart_box=tk.Frame(box,bg=p['panel']);self.label(self.chart_box,'// SON 5 DAKİKA',size=10,muted=True).pack(anchor='w')
        self.chart=SpeedChart(self.chart_box,p,axes=False,height=120);self.chart.pack(fill='both',expand=True,pady=(8,10))
        self.metric_box=tk.Frame(self.chart_box,bg=p['panel']);self.metric_box.pack(fill='x')
        self.metrics={}
        for column,key in enumerate(('AKTİF','BAĞLANTI','BU OTURUM','EN YÜKSEK')):
            self.metric_box.columnconfigure(column,weight=1,uniform='telemetry')
            cell=tk.Frame(self.metric_box,bg=p['panel']);cell.grid(row=0,column=column,sticky='nsew',padx=5)
            tk.Frame(cell,bg=p['violet'] if key=='BU OTURUM' else p['accent'],width=2).pack(side='left',fill='y',padx=(0,8))
            self.label(cell,key,size=9,muted=True).pack(anchor='w')
            self.metrics[key]=self.label(cell,'—',size=14,weight='Bold',max_width=145);self.metrics[key].pack(anchor='w',pady=(5,0))

    def build_listing(self):
        app=self.app;p=self.p;box=self.main
        header=tk.Frame(box,bg=p['panel']);header.pack(fill='x',pady=(0,12))
        self.list_title=self.label(header,'// AKTARIMLAR',size=10,muted=True);self.list_title.pack(side='left')
        app.relax_button=Button(header,'Hız sınırı: Yok',app.toggle_relax,palette=p,kind='secondary',height=30)
        app.relax_button.pack(side='right')
        self.columns_button=Button(header,'Sütunlar',app.show_column_menu,palette=p,kind='secondary',height=30)
        self.columns_button.pack(side='right',padx=8)
        self.compact_actions=tk.Frame(box,bg=p['panel']);self.compact_actions.pack(fill='x')
        self.content=tk.Frame(box,bg=p['panel']);self.content.pack(fill='both',expand=True)
        self.listing=tk.Frame(self.content,bg=p['panel']);self.listing.pack(fill='both',expand=True)
        app.style.configure('SDM.Treeview',rowheight=44)
        app.tree=tb.Treeview(self.listing,columns=tuple(c[0] for c in COLUMNS),show='headings',selectmode='extended',style='SDM.Treeview',height=8)
        widths={'filename':220,'progress':160,'size':92,'speed':140,'eta':110,'status':180}
        app.tree.column('#0',width=0,minwidth=0,stretch=False)
        for key,title,width in COLUMNS:
            app.tree.heading(key,text=title,command=app.show_column_menu)
            app.tree.column(key,width=widths.get(key,width),minwidth=60,stretch=key=='filename')
        app.apply_visible_columns()
        self.ys=tb.Scrollbar(self.listing,orient='vertical',command=app.tree.yview);self.xs=tb.Scrollbar(self.listing,orient='horizontal',command=app.tree.xview)
        app.tree.configure(yscrollcommand=self.scroll_y,xscrollcommand=self.scroll_x)
        app.tree.grid(row=0,column=0,sticky='nsew');self.ys.grid(row=0,column=1,sticky='ns');self.xs.grid(row=1,column=0,sticky='ew')
        self.listing.rowconfigure(0,weight=1);self.listing.columnconfigure(0,weight=1)
        app.tree.bind('<Double-1>',app._on_tree_double_click);app.tree.bind('<Button-3>',app._on_tree_right_click)
        app.tree.bind('<Return>',lambda event:self.invoke_open());app.tree.bind('<<TreeviewSelect>>',lambda event:app.update_action_states())
        from ui_table_surface import TableSurface
        app.data_view=TableSurface(app);app.context_menu=None;app._progress_canvases={};app._status_canvases={}

    def build_empty(self):
        app=self.app;p=self.p
        self.empty=tk.Frame(self.main,bg=p['panel'])
        center=tk.Frame(self.empty,bg=p['panel']);center.pack(fill='both',expand=True,pady=24)
        Radar(center,p).pack(pady=(0,16));self.label(center,'// SİSTEM BEKLEMEDE',size=10,fg=p['accent']).pack()
        app.empty_label=self.label(center,'Henüz indirme yok',size=18,mono=False,weight='Bold');app.empty_label.pack(pady=12)
        text=tk.Label(center,text='Bir bağlantı yapıştır, dosyayı buraya sürükle veya tarayıcıdaki indirmeleri SDM’ye yönlendir.',
            bg=p['panel'],fg=p['text_3'],font=('Inter',text_px(13)),wraplength=540,justify='center');text.pack(fill='x')
        text.bind('<Configure>',lambda event:text.configure(wraplength=max(80,event.width-24)))
        row=tk.Frame(center,bg=p['panel']);row.pack(pady=18)
        Button(row,'Yeni indirme',app.open_add_dialog,palette=p,kind='primary').pack(side='left',padx=6)
        Button(row,'Panodan yapıştır',self.paste,palette=p,kind='secondary').pack(side='left',padx=6)
        app.empty_clear=Button(center,'Aramayı temizle',lambda:app.search_var.set(''),palette=p,kind='link')
        self.drop_zone=tk.Label(center,text='[ DOSYA VEYA BAĞLANTIYI BURAYA BIRAK ]',bg=p['panel'],fg=p['muted'],font=('JetBrains Mono',text_px(11)),highlightthickness=1,highlightbackground=p['input_border'],pady=16)
        self.drop_zone.pack(fill='x',padx=24,pady=(0,12))
        self.extension_button=Button(center,'> Tarayıcı eklentisini kur',self.extension_help,palette=p,kind='link');self.extension_button.pack()

    def build_target(self):
        p=self.p;app=self.app
        self.right=tk.Frame(self.workspace,bg=p['side'],width=340);self.right.grid(row=0,column=2,sticky='ns');self.right.pack_propagate(False)
        self.right_footer=tk.Frame(self.right,bg=p['side']);self.right_footer.pack(side='bottom',fill='x',padx=16,pady=16)
        self.single_actions=tk.Frame(self.right_footer,bg=p['side']);self.single_actions.pack(fill='x')
        self.primary=Button(self.single_actions,'Duraklat',palette=p,kind='outline_accent',width=132,height=36);self.primary.pack(side='left')
        self.detail_button=Button(self.single_actions,'Ayrıntı',app.show_selected_details,palette=p,width=105,height=36);self.detail_button.pack(side='left',padx=6)
        self.more=Button(self.single_actions,'⋯',self.selected_menu,palette=p,width=36,height=36);self.more.pack(side='right')
        commands=(('resume','Devam',app.resume_selected),('pause','Duraklat',app.pause_selected),('cancel','İptal',app.cancel_selected),('remove','Kaldır ▾',app.show_remove_menu),('folder','Klasör',app.open_folder),('queue','Kuyruk ▾',app.show_queue_menu))
        # Each bar belongs to its real viewport. Repositioning one root-owned
        # frame across the scroll boundary lets off-screen buttons cover the footer.
        self.action_bars={}
        for compact,host,columns in ((False,self.right_footer,3),(True,self.compact_actions,6)):
            group=tk.Frame(host,bg=host.cget('bg'));buttons={}
            for index,(key,title,command) in enumerate(commands):
                button=Button(group,title,command,palette=p,kind='secondary',height=34,width=90)
                button.grid(row=index//columns,column=index%columns,sticky='ew',padx=2,pady=3)
                group.columnconfigure(index%columns,weight=1,uniform='actions')
                button.bind('<FocusIn>',self.reveal_action,add='+');buttons[key]=button
            self.action_bars[compact]=(group,buttons)
        self.action_group,self.actions=self.action_bars[False];self.queue_button=self.actions['queue']
        self.system=tk.Frame(self.right,bg=p['side']);self.system.pack(fill='both',expand=True,padx=18,pady=18)
        self.label(self.system,'// SİSTEM',size=10,muted=True).pack(anchor='w',pady=(0,16));self.system_values={}
        for title in ('TOPLAM HIZ','AKTİF','DİSK BOŞ','BU OTURUM'):
            card=Panel(self.system,p,padding=12);card.configure(height=80);card.pack(fill='x',pady=(0,12))
            self.label(card.content,title,size=9,muted=True).pack(anchor='w')
            value=self.label(card.content,'—',size=18,weight='Bold',max_width=270);value.pack(anchor='w',pady=(5,0));self.system_values[title]=value
        self.selection=tk.Frame(self.right,bg=p['side'])
        self.target_title=self.label(self.selection,'// HEDEF',size=10,muted=True);self.target_title.pack(anchor='w')
        self.target_name=self.label(self.selection,'',size=14,mono=False,weight='Bold',max_width=300);self.target_name.pack(anchor='w',pady=(16,4))
        self.target_domain=self.label(self.selection,'',size=10,muted=True,max_width=300);self.target_domain.pack(anchor='w')
        self.target_measurements=tk.Frame(self.selection,bg=p['side']);self.target_measurements.pack(fill='x')
        self.ring=ProgressRing(self.target_measurements,p,0,size=182,stroke=9);self.ring.pack(pady=(16,0))
        self.amount=self.label(self.target_measurements,'',size=10,muted=True,max_width=300);self.amount.pack(pady=(0,14))
        self.parts=ConnectionColumns(self.target_measurements,p);self.parts.pack(fill='x',pady=12)
        self.target_fields={}
        for title in ('HIZ','KALAN','KUYRUK','BAĞLANTI'):
            row=tk.Frame(self.target_measurements,bg=p['side']);row.pack(fill='x',pady=4)
            self.label(row,title,size=10,muted=True).pack(side='left');value=self.label(row,'—',size=11,max_width=205);value.pack(side='right');self.target_fields[title]=value

    def selected_menu(self):
        from types import SimpleNamespace
        return self.context_menu(SimpleNamespace(x_root=self.more.winfo_rootx(),y_root=self.more.winfo_rooty()+self.more.winfo_height()))

    def queue_menu(self):
        from ui_overlays import PopupMenu
        menu=PopupMenu(self.app,self.p)
        for queue in self.app.settings['queues']:
            name=queue['name'];menu.add_item(name,submenu=lambda child,n=name:self.queue_items(child,n))
        menu.add_separator();menu.add_item('Kuyruk ve zamanlama ayarları',lambda:self.open_settings_section('Kuyruk'))
        return self.popup(menu,self.queue_selector)

    def sync(self,records,all_records):
        if not self.alive:return
        app=self.app;state=getattr(app,'current_status_filter','Tümü');queue=getattr(app,'current_queue_filter',None)
        app.page_title.set(' · '.join(value for value in (queue,app.current_category,state) if value and value!='Tümü') or 'Tüm indirmeler')
        self.list_title.configure(text='// AKTARIMLAR · '+str(len(records)))
        for name,button in app.status_buttons.items():
            button.selected=name==state and not queue;button.set_count(sum(matches_status(record['status'],name) for record in all_records));button.draw()
        for name,button in app.category_buttons.items():
            button.selected=name==app.current_category;button.set_count(sum(record['category']==name for record in all_records));button.draw()
        for name,button in self.queue_buttons.items():button.selected=name==queue;button.set_count(sum(record.get('queue_name')==name for record in all_records));button.draw()
        if records:self.empty.pack_forget();self.content.pack(fill='both',expand=True)
        else:
            self.content.pack_forget();self.empty.pack(fill='both',expand=True)
            app.empty_label.configure(text='Aramanızla eşleşen indirme bulunamadı' if app.search_term else 'Bu görünümde henüz indirme yok' if all_records else 'Henüz indirme yok')
            if app.search_term:app.empty_clear.pack(before=self.drop_zone,pady=8)
            else:app.empty_clear.pack_forget()
            self.scroll.yview_moveto(0)
        self.telemetry.grid_remove() if not records else self.telemetry.grid()
        self.list_card.configure(height=600 if not records else 440)
        self.update_selection()

    def update_selection(self):
        if not self.alive or not hasattr(self,'action_group'):return
        app=self.app;items=app.tree.selection();caps=self.capabilities()
        changed=items!=getattr(self,'_selection_key',None);self._selection_key=items
        records=[app._visible_records[int(app.tree.item(item,'values')[0])] for item in items if int(app.tree.item(item,'values')[0]) in app._visible_records]
        self.action_group,self.actions=self.action_bars[bool(self._compact)];self.queue_button=self.actions['queue']
        app.action_buttons=list(self.actions.values())
        for group,buttons in self.action_bars.values():
            group.pack_forget()
            for key,button in buttons.items():button.configure(state='normal' if caps[key] else 'disabled')
        self.detail_button.configure(state='normal' if caps['details'] else 'disabled');self.more.configure(state='normal' if records else 'disabled')
        self.single_actions.pack_forget()
        if records:
            self.system.pack_forget();self.selection.pack(fill='both',expand=True,padx=18,pady=18)
            if len(records)==1:
                self.target_measurements.pack(fill='x')
                self.target_snapshot=view=target(app,records[0]);self.target_title.configure(text='// HEDEF · '+str(view['id']))
                self.target_name.configure(text=view['name']);self.target_domain.configure(text=domain(records[0]));self.ring.set(view['progress']);self.amount.configure(text=view['amount']);self.parts.set(view['rows'])
                for key,value in (('HIZ',view['speed']),('KALAN',view['eta']),('KUYRUK',view['queue']),('BAĞLANTI','Henüz ölçülmedi' if view['connections'] is None else str(view['connections']))):self.target_fields[key].configure(text=value)
                action='open' if caps['open'] else 'pause' if caps['pause'] else 'resume'
                self.primary.configure(text={'open':'Aç','pause':'Duraklat','resume':'Devam'}[action],command={'open':app.open_file,'pause':app.pause_selected,'resume':app.resume_selected}[action],state='normal' if caps[action] else 'disabled')
            else:
                self.target_snapshot=None;self.target_title.configure(text='// '+str(len(records))+' HEDEF SEÇİLİ');self.target_name.configure(text='Toplu eylemler');self.target_domain.configure(text='');self.ring.set(0);self.target_measurements.pack_forget();self.amount.configure(text='');self.parts.set(())
                for value in self.target_fields.values():value.configure(text='—')
            if self._compact or len(records)>1:
                self.action_group.pack(fill='x',pady=(0,8))
                if self._compact and changed:
                    self.action_group.update_idletasks();self.reveal_action(widget=self.actions['pause'])
            else:
                self.single_actions.pack(fill='x');app.action_buttons=[self.primary,self.detail_button,self.more]
        else:
            self.primary.configure(state='disabled')
            self.target_snapshot=None;self.selection.pack_forget();self.system.pack(fill='both',expand=True,padx=18,pady=18);self.ring.set(0)

    def reveal_action(self,event=None,widget=None):
        if not self.alive or not self._compact:return
        widget=widget if widget is not None else event.widget
        canvas=self.scroll._canvas;top=widget.winfo_rooty()-canvas.winfo_rooty()
        if top<0 or top+widget.winfo_height()>canvas.winfo_height():
            offset=widget.winfo_rooty()-self.dashboard.winfo_rooty()
            self.scroll.yview_moveto(offset/max(1,self.dashboard.winfo_height()))

    def update_hud(self,speed):
        self.update_capture_and_rate();self.update_disk();self.update_selection()
        app=self.app;now=time.monotonic();self.speed_points.append((now,speed))
        from capture_policy import capture_enabled
        app.capture_label.configure(text='Yakalama açık' if capture_enabled(app.settings) else 'Yakalama kapalı')
        while self.speed_points and self.speed_points[0][0]<now-300:self.speed_points.popleft()
        peak=max((value for _,value in self.speed_points),default=0)
        self.gauge.set(speed,peak);self.chart.set(tuple(self.speed_points))
        values=telemetry(app,getattr(app,'_all_records',()))
        self.metrics['AKTİF'].configure(text=str(values['active'])+' / '+str(app.settings['max_simultaneous_downloads']))
        self.metrics['BAĞLANTI'].configure(text='—' if values['connections'] is None else str(values['connections']))
        self.metrics['BU OTURUM'].configure(text=app.hud_received.get())
        self.metrics['EN YÜKSEK'].configure(text=number(app,f'{peak/1048576:.1f}')+' MB/sn')
        app.lbl_status_summary.configure(text=str(values['active'])+' AKTİF');self.received_label.configure(text='BU OTURUM '+app.hud_received.get())
        for key,value in (('TOPLAM HIZ',app.hud_speed.get()),('AKTİF',self.metrics['AKTİF'].text),('DİSK BOŞ',app.lbl_status_info.text),('BU OTURUM',app.hud_received.get())):self.system_values[key].configure(text=value)

    def resize(self,event):
        if event.widget is not self.body or not hasattr(self,'right'):return
        compact=event.width<1280
        if compact==self._compact:return
        self._compact=compact
        self._selection_key=None
        if compact:self.right.grid_remove()
        else:self.right.grid()
        self.gauge.grid_forget();self.chart_box.grid_forget()
        self.telemetry.content.columnconfigure(0,weight=1 if compact else 0);self.telemetry.content.columnconfigure(1,weight=0 if compact else 1)
        self.gauge.grid(row=0,column=0,sticky='n' if compact else 'ns')
        self.chart_box.grid(row=1 if compact else 0,column=0 if compact else 1,sticky='nsew',padx=0 if compact else (12,0))
        self.telemetry.content.update_idletasks()
        self.telemetry.configure(height=self.telemetry.content.winfo_reqheight()+2*self.telemetry.padding)
        self.update_selection()

    def dispose(self,event):
        if event.widget is self.body and self.alive:
            for sequence,identifier in self.command_bindings:self.app.unbind(sequence,identifier)
        super().dispose(event)


def build(app):return YorungeWorkspace(app)
