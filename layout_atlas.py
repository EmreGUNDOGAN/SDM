"""Atlas A01/A02 workspace. Existing application actions remain the authority."""
from collections import deque
from pathlib import Path
import shutil
import threading
import time
import tkinter as tk
import ttkbootstrap as tb
from PIL import ImageDraw
from ttkbootstrap.widgets.scrolled import ScrolledFrame
from theme_widgets import Button,Search
from ui_surface import TextLabel,surface,icon,photo,text_on,ellipsize
from ui_indicators import Sparkline
from ui_overlays import PopupMenu,ToastManager,Tooltip
from ui_tokens import SIZES,ATLAS,TEXT_SCALE,file_tile_colors,text_px
from list_display import COLUMNS
from atlas_view import CATEGORY_TILES,DEFAULT_COLUMNS,available_actions,matches_status,number
from atlas_details import AtlasDetails


class NavButton(Button):
    def __init__(self,master,text,command,palette,kind=None,glyph=None,color=None):
        self.count='';self.tile_kind=kind;self.glyph=glyph;self.dot_color=color
        super().__init__(master,text,command,palette=palette,quiet=True,height=ATLAS['nav_row'])

    def set_count(self,value):
        if str(value)!=self.count:self.count=str(value);self._draw_signature=None;self.draw()

    def draw(self):
        if not self.winfo_exists():return
        p=self.p;w=self.winfo_width() if self.winfo_width()>1 else int(self.cget('width'));h=int(self.cget('height'))
        signature=(w,h,self.text,self.count,self.selected,self.focused,self.hover,self.pressed)
        if signature==getattr(self,'_draw_signature',None):return
        self._draw_signature=signature
        bg=p['accent_nav'] if self.selected else p['subtle'] if self.hover else p['side']
        fg=p['accent_text'] if self.selected else p['text_2']
        image=surface(w,h,p['side'],bg,radius=8);d=ImageDraw.Draw(image);left=28
        if self.tile_kind:
            label,kind=self.tile_kind;tile_bg,tile_fg=file_tile_colors(kind,p['mode'])
            d.rounded_rectangle((10,9,32,27),radius=4,fill=tile_bg)
            text_on(image,(21,18),label,9,'Bold',tile_fg,'mm');left=42
        elif self.glyph:
            glyph=icon(self.glyph,16,fg);image.paste(glyph,(10,(h-16)//2),glyph);left=34
        else:d.ellipse((10,h//2-4,18,h//2+4),fill=p[self.dot_color or 'accent'])
        text_on(image,(left,h/2),ellipsize(self.text,w-left-42,13,'SemiBold' if self.selected else 'Regular'),13,
                'SemiBold' if self.selected else 'Regular',fg,'lm')
        text_on(image,(w-10,h/2),self.count,12,fill=p['muted'],anchor='rm')
        self.display(image)


class AtlasWorkspace:
    def __init__(self,app):
        self.app=app;self.p=app.palette;self.alive=True;self.menu=None;self.tooltips=[]
        self._disk_due=0;self._disk_busy=False;self.speed_points=deque(maxlen=60)
        app._atlas_workspace=self;p=self.p
        self.body=tk.Frame(app,bg=p['bg']);self.body.pack(fill='both',expand=True)
        self.body.bind('<Destroy>',self.dispose)
        side=tk.Frame(self.body,bg=p['side'],width=SIZES['sidebar']-1);side.pack(side='left',fill='y');side.pack_propagate(False)
        tk.Frame(self.body,bg=p['line'],width=1).pack(side='left',fill='y')
        self.main=tk.Frame(self.body,bg=p['bg']);self.main.pack(fill='both',expand=True)
        brand=tk.Frame(side,bg=p['side']);brand.pack(fill='x',padx=ATLAS['sidebar_padding']+6,pady=(ATLAS['sidebar_top'],ATLAS['group_gap']))
        logo=surface(ATLAS['brand'],ATLAS['brand'],p['side'],p['accent'],radius=8)
        glyph=icon('download',18,p['on_accent']);logo.paste(glyph,(6,6),glyph)
        app._atlas_logo=photo(logo,app)
        tk.Label(brand,image=app._atlas_logo,bg=p['side']).pack(side='left',padx=(0,ATLAS['brand_gap']))
        TextLabel(brand,'SDM',size=18,weight='Bold',fg=p['text']).pack(side='left')
        self.new_button=Button(side,'Yeni indirme',app.open_add_dialog,palette=p,primary=True,height=40)
        self.new_button.icon_name='plus';self.new_button.shortcut='Ctrl+N';self.new_button.draw();self.new_button.pack(fill='x',padx=ATLAS['sidebar_padding'],pady=(0,ATLAS['group_gap']))
        bottom=tk.Frame(side,bg=p['side']);bottom.pack(side='bottom',fill='x',padx=ATLAS['sidebar_padding'],pady=(0,ATLAS['sidebar_top']))
        tk.Frame(bottom,bg=p['line'],height=1).pack(fill='x',pady=(0,12))
        self.bottom_buttons={}
        for label,glyph,command in (('Araçlar','wrench',app.open_tools),('İstatistik','chart',app.open_stats),('Masaüstü HUD','monitor',app.show_mini_hud),('Ayarlar','settings',app.open_settings_dialog)):
            b=NavButton(bottom,label,command,p,glyph=glyph);b.pack(fill='x');self.bottom_buttons[label]=b
        app.style.configure('Atlas.Side.TFrame',background=p['side'])
        app.sidebar_scroll=ScrolledFrame(side,height=340,width=SIZES['sidebar']-2*ATLAS['sidebar_padding'],auto_hide=False,style='Atlas.Side.TFrame')
        app.sidebar_scroll.pack(fill='both',expand=True,padx=ATLAS['sidebar_padding']);app.sidebar_scroll._canvas.configure(bg=p['side'])
        nav=tk.Frame(app.sidebar_scroll,bg=p['side']);nav.pack(fill='both',expand=True)
        self.nav=nav;app.sidebar_scroll._canvas.bind('<Configure>',self.update_sidebar_scrollbar,add='+')
        self.caption(nav,'İNDİRMELER')
        for name,title,color in (('Tümü','Tümü','accent'),('Devam Edenler','Devam edenler','accent'),('Tamamlananlar','Tamamlananlar','success'),('Hatalı','Hatalı','danger')):
            b=NavButton(nav,title,lambda value=name:self.select_status(value),p,color=color)
            b.pack(fill='x',pady=ATLAS['nav_gap']/2);b.bind('<FocusIn>',self.reveal_nav,add='+');app.status_buttons[name]=b
        self.caption(nav,'KATEGORİLER',True)
        for name,tile in CATEGORY_TILES.items():
            b=NavButton(nav,name,lambda value=name:app.select_category(value),p,kind=tile)
            b.pack(fill='x',pady=ATLAS['nav_gap']/2);b.bind('<FocusIn>',self.reveal_nav,add='+');app.category_buttons[name]=b
        self.caption(nav,'KUYRUKLAR',True);self.queue_buttons={}
        for queue in app.settings['queues']:
            name=queue['name'];b=NavButton(nav,name,lambda value=name:self.select_queue(value),p,glyph='clock' if queue.get('once') or queue.get('enabled') else 'queue')
            b.pack(fill='x',pady=ATLAS['nav_gap']/2);b.bind('<FocusIn>',self.reveal_nav,add='+');self.queue_buttons[name]=b
        self.build_header();self.build_footer();self.build_listing();self.build_empty()
        self.main.bind('<Configure>',self.resize)
        self.toast_manager=ToastManager(app,p,self.desktop_notify)
        app.refresh_downloads();app.update_action_states()

    def caption(self,parent,text,gap=False):
        TextLabel(parent,text,size=11,weight='Medium',fg=self.p['muted']).pack(anchor='w',padx=10,pady=(ATLAS['group_gap'] if gap else 0,6))

    def build_header(self):
        app=self.app;p=self.p
        header=tk.Frame(self.main,bg=p['bg'],height=ATLAS['header']);header.pack(fill='x');header.pack_propagate(False)
        app.capture_label=Button(header,'Tarayıcı yakalama açık',app.toggle_capture,palette=p,quiet=True,width=ATLAS['capture_width'],height=SIZES['toolbar_button'])
        app.capture_label.status_badge=True;app.capture_label.pack(side='right',padx=(12,SIZES['content_padding']))
        app.search_var=tk.StringVar(app,value=getattr(app,'search_term',''))
        self.search_trace=app.search_var.trace_add('write',lambda *args:app._on_search_change())
        app.search_control=Search(header,app.search_var,p,placeholder='Dosya adı veya adres ara')
        app.search_control.configure(width=ATLAS['search_width']);app.search_control.pack(side='right')
        self.title_label=TextLabel(header,textvariable=app.page_title,size=20,weight='Bold',fg=p['text'],max_width=ATLAS['wide_title'])
        self.title_label.pack(side='left',padx=(SIZES['content_padding'],10))
        self.count_label=TextLabel(header,'0 öğe',size=12,fg=p['muted']);self.count_label.pack(side='left')
        tk.Frame(self.main,bg=p['line'],height=1).pack(fill='x')
        self.search_binding=app.bind('<Control-f>',self.focus_search,add='+')
        self.search_upper_binding=app.bind('<Control-F>',self.focus_search,add='+')

    def focus_search(self,event=None):
        self.app.search_control.entry.focus_set();self.app.search_control.entry.selection_range(0,'end');return 'break'

    def button(self,parent,text,command,glyph=None,width=None):
        b=Button(parent,text,command,palette=self.p,width=width,height=SIZES['toolbar_button'])
        if glyph:b.icon_name=glyph;b.draw()
        b.pack(side='left',padx=(0,ATLAS['toolbar_gap']));return b

    def build_listing(self):
        app=self.app;p=self.p
        self.toolbar=tk.Frame(self.main,bg=p['bg'],height=ATLAS['toolbar']);self.toolbar.pack(fill='x');self.toolbar.pack_propagate(False)
        group=tk.Frame(self.toolbar,bg=p['bg']);group.pack(side='left',padx=(SIZES['content_padding'],0))
        self.actions={}
        for key,label,glyph,command,size in (('resume','Devam','play',app.resume_selected,'toolbar_resume'),('pause','Duraklat','pause',app.pause_selected,'toolbar_pause'),('cancel','İptal','x',app.cancel_selected,'toolbar_cancel'),('remove','Kaldır ▾','trash',app.show_remove_menu,'toolbar_remove'),('folder','Klasörü aç','folder',app.open_folder,'toolbar_folder')):
            self.actions[key]=self.button(group,label,command,glyph,ATLAS[size]);app.action_buttons.append(self.actions[key])
            self.tooltips.append(Tooltip(self.actions[key],label,p))
        right=tk.Frame(self.toolbar,bg=p['bg']);right.pack(side='right',padx=(0,SIZES['content_padding']-ATLAS['toolbar_gap']))
        self.queue_button=self.button(right,'Kuyruk ▾',app.show_queue_menu,width=ATLAS['toolbar_queue'])
        app.relax_button=self.button(right,'Hız sınırı: Yok',app.toggle_relax,width=ATLAS['toolbar_limit'])
        self.columns_button=self.button(right,'',app.show_column_menu,'columns',SIZES['icon_button'])
        self.tooltips.extend((Tooltip(self.columns_button,'Sütunlar',p),Tooltip(app.relax_button,'Hız sınırı · İnterneti rahatlat',p),Tooltip(app.search_control,'Dosya adı veya adres ara · Ctrl+F',p)))
        self.capture_tip=Tooltip(app.capture_label,app.capture_label.text,p);self.tooltips.append(self.capture_tip)
        self.content=tk.Frame(self.main,bg=p['bg']);self.content.pack(fill='both',expand=True)
        self.details=AtlasDetails(self.content,app)
        self.listing=tk.Frame(self.content,bg=p['bg']);self.listing.pack(side='left',fill='both',expand=True)
        app.style.configure('SDM.Treeview',rowheight=SIZES['table_row'])
        app.style.configure('SDM.Treeview.Heading',font=('Inter',text_px(12)),padding=(8,10))
        app.tree=tb.Treeview(self.listing,columns=tuple(c[0] for c in COLUMNS),show='headings',selectmode='extended',style='SDM.Treeview')
        widths={'filename':285,'size':94,'progress':145,'speed':100,'eta':84,'status':130}
        app.tree.column('#0',width=0,minwidth=0,stretch=False)
        for name,label,width in COLUMNS:
            app.tree.heading(name,text='Dosya' if name=='filename' else 'Kalan' if name=='eta' else label,command=app.show_column_menu)
            app.tree.column(name,width=widths.get(name,width) if name=='filename' else round(widths.get(name,width)*TEXT_SCALE),minwidth=80 if name!='filename' else 200,stretch=name=='filename')
        app.apply_visible_columns()
        self.ys=tb.Scrollbar(self.listing,orient='vertical',command=app.tree.yview)
        self.xs=tb.Scrollbar(self.listing,orient='horizontal',command=app.tree.xview)
        app.tree.configure(yscrollcommand=self.scroll_y,xscrollcommand=self.scroll_x)
        app.tree.grid(row=0,column=0,sticky='nsew');self.ys.grid(row=0,column=1,sticky='ns');self.xs.grid(row=1,column=0,sticky='ew')
        self.listing.rowconfigure(0,weight=1);self.listing.columnconfigure(0,weight=1)
        app.tree.bind('<Double-1>',app._on_tree_double_click);app.tree.bind('<Button-3>',app._on_tree_right_click)
        app.tree.bind('<Return>',lambda e:self.invoke_open());app.tree.bind('<Configure>',lambda e:app.paint_progress())
        app.tree.bind('<<TreeviewSelect>>',lambda e:app.update_action_states())
        from ui_table_surface import TableSurface
        app.data_view=TableSurface(app);app.context_menu=None
        app._progress_canvases={};app._status_canvases={}

    def scroll_y(self,*args):
        self.ys.set(*args)
        if float(args[0])<=0 and float(args[1])>=1:self.ys.grid_remove()
        else:self.ys.grid()
        if hasattr(self.app,'data_view'):self.app.data_view.schedule()

    def scroll_x(self,*args):
        self.xs.set(*args)
        if float(args[0])<=0 and float(args[1])>=1:self.xs.grid_remove()
        else:self.xs.grid()
        if hasattr(self.app,'data_view'):self.app.data_view.schedule()

    def build_footer(self):
        app=self.app;p=self.p
        foot=tk.Frame(self.main,bg=p['side'],height=SIZES['status_bar']);foot.pack(side='bottom',fill='x');foot.pack_propagate(False)
        tk.Frame(foot,bg=p['line'],height=1).pack(side='top',fill='x')
        app.lbl_status_summary=TextLabel(foot,'0 aktif',size=12,fg=p['text']);app.lbl_status_summary.pack(side='left',padx=(SIZES['content_padding'],16))
        self.sparkline=Sparkline(foot,p,width=ATLAS['footer_sparkline'],height=24);self.sparkline.pack(side='left')
        self.speed_label=TextLabel(foot,'0 KB/sn',size=12,weight='SemiBold',fg=p['text']);self.speed_label.pack(side='left',padx=(8,20))
        self.received_label=TextLabel(foot,'Bu oturum 0 B',size=12,fg=p['muted']);self.received_label.pack(side='left')
        app.lbl_status_info=TextLabel(foot,'Hazır',size=12,fg=p['muted']);app.lbl_status_info.pack(side='right',padx=SIZES['content_padding'])

    def build_empty(self):
        app=self.app;p=self.p
        self.empty=tk.Frame(self.main,bg=p['bg'])
        center=tk.Frame(self.empty,bg=p['bg']);center.place(relx=.5,rely=.48,anchor='center')
        tile=surface(64,64,p['bg'],p['accent_nav'],radius=16);glyph=icon('download',28,p['accent']);tile.paste(glyph,(18,18),glyph)
        self.empty_icon=photo(tile,app);tk.Label(center,image=self.empty_icon,bg=p['bg']).pack(pady=(0,20))
        app.empty_label=TextLabel(center,'Henüz indirme yok',size=18,weight='SemiBold',fg=p['text']);app.empty_label.pack()
        self.empty_description=TextLabel(center,'Bir bağlantı yapıştır, dosyayı buraya sürükle veya tarayıcıdaki',size=13,fg=p['muted']);self.empty_description.pack(pady=(16,4))
        self.empty_description2=TextLabel(center,"indirmeleri SDM’ye yönlendir.",size=13,fg=p['muted']);self.empty_description2.pack()
        row=tk.Frame(center,bg=p['bg']);row.pack(pady=24)
        Button(row,'Yeni indirme',app.open_add_dialog,palette=p,primary=True).pack(side='left',padx=6)
        Button(row,'Panodan yapıştır',self.paste,palette=p).pack(side='left',padx=6)
        app.empty_clear=Button(row,'Aramayı temizle',lambda:app.search_var.set(''),palette=p,quiet=True)
        self.drop_zone=tk.Canvas(center,width=ATLAS['empty_width'],height=58,bg=p['bg'],highlightthickness=0)
        self.drop_zone.pack()
        self.drop_zone.create_rectangle(1,1,ATLAS['empty_width']-1,57,outline=p['input_border'],dash=(3,3))
        self.drop_zone.create_text(ATLAS['empty_width']/2,29,text='Dosya veya bağlantıyı buraya bırak',fill=p['muted'],font=('Inter',text_px(13)))
        self.extension_button=Button(center,'Tarayıcı eklentisini kur',self.extension_help,palette=p,kind='link')
        self.extension_button.pack(pady=(12,0))

    def paste(self):
        try:value=self.app.clipboard_get()
        except tk.TclError:value=''
        self.app.open_add_dialog(value)

    def extension_help(self):
        self.open_settings_section('Tarayıcı')

    def open_settings_section(self,section):
        self.app.open_settings_dialog()
        from modern_settings import SettingsDialog
        for child in reversed(self.app.winfo_children()):
            if isinstance(child,SettingsDialog):
                child.tabs[section].master.select(child.tabs[section])
                break

    def resize(self,event):
        if event.widget is not self.main:return
        compact=event.width<ATLAS['compact_workspace']
        for key in ('resume','pause','cancel','folder'):
            button=self.actions[key];button.icon_only=compact
            button.configure(width=SIZES['icon_button'] if compact else ATLAS['toolbar_'+key])
        self.app.search_control.configure(width=ATLAS['compact_search'] if compact else ATLAS['search_width'])
        self.app.capture_label.configure(width=SIZES['icon_button'] if compact else ATLAS['capture_width'])
        self.title_label.max_width=ATLAS['compact_title'] if compact else ATLAS['wide_title'];self.title_label.draw()

    def update_sidebar_scrollbar(self,event=None):
        if self.nav.winfo_reqheight()>self.app.sidebar_scroll._canvas.winfo_height():self.app.sidebar_scroll.show_scrollbars()
        else:self.app.sidebar_scroll.hide_scrollbars()

    def reveal_nav(self,event):
        canvas=self.app.sidebar_scroll._canvas;widget=event.widget
        top=widget.winfo_rooty()-self.nav.winfo_rooty();bottom=top+widget.winfo_height()
        visible_top=canvas.canvasy(0);visible_bottom=visible_top+canvas.winfo_height()
        if top<visible_top:self.app.sidebar_scroll.yview_moveto(top/max(1,self.nav.winfo_height()))
        elif bottom>visible_bottom:self.app.sidebar_scroll.yview_moveto((bottom-canvas.winfo_height())/max(1,self.nav.winfo_height()))

    def select_status(self,value):
        self.app.current_queue_filter=None;self.app.select_status_filter(value)

    def select_queue(self,name):
        self.app.current_queue_filter=name;self.app.refresh_downloads()

    def sync(self,records,all_records):
        if not self.alive:return
        app=self.app;state=getattr(app,'current_status_filter','Tümü');queue=getattr(app,'current_queue_filter',None)
        title=' · '.join(v for v in (queue,app.current_category,state) if v and v!='Tümü') or 'Tüm indirmeler'
        app.page_title.set(title);self.count_label.configure(text=f'{len(records)} öğe')
        for name,b in app.status_buttons.items():
            b.selected=name==state and not queue;b.set_count(sum(matches_status(r['status'],name) for r in all_records));b.draw()
        for name,b in app.category_buttons.items():b.set_count(sum(r['category']==name for r in all_records))
        for name,b in self.queue_buttons.items():
            setting=next(q for q in app.settings['queues'] if q['name']==name)
            scheduled=(setting.get('once','')[-5:] or setting.get('start','')) if setting.get('enabled') or setting.get('once') else ''
            b.selected=name==queue;b.set_count(scheduled or sum(r.get('queue_name')==name for r in all_records));b.draw()
        if records:
            self.empty.pack_forget()
            if not self.toolbar.winfo_manager():self.toolbar.pack(fill='x',before=self.content if self.content.winfo_manager() else None)
            if not self.content.winfo_manager():self.content.pack(fill='both',expand=True)
        else:
            self.toolbar.pack_forget();self.content.pack_forget();self.empty.pack(fill='both',expand=True)
            searching=bool(app.search_term);filtered=app.current_category!='Tümü' or state!='Tümü' or bool(queue)
            app.empty_label.configure(text='Aramanızla eşleşen indirme bulunamadı' if searching else 'Bu görünümde henüz indirme yok' if filtered else 'Henüz indirme yok')
            if searching:app.empty_clear.pack(side='left',padx=6)
            else:app.empty_clear.pack_forget()
        self.update_selection()

    def update_selection(self):
        if not self.alive:return
        app=self.app;items=app.tree.selection();values=[app.tree.item(item,'values') for item in items]
        actions=available_actions(value[8] for value in values)
        for key,button in self.actions.items():button.configure(state='normal' if actions[key] else 'disabled')
        records=[getattr(app,'_visible_records',{}).get(int(value[0])) for value in values]
        records=[r for r in records if r]
        if records:
            if not self.details.winfo_manager():self.details.pack(side='right',fill='y',before=self.listing)
            self.details.sync(records,values)
        else:self.details.pack_forget()

    def invoke_open(self):
        if self.capabilities()['open']:self.app.open_file()
        return 'break'

    def capabilities(self):return available_actions(self.app.tree.item(item,'values')[8] for item in self.app.tree.selection())

    def popup(self,menu,anchor=None,x=None,y=None):
        if self.menu and self.menu.winfo_exists():self.menu.close_root()
        self.menu=menu
        if anchor:x,y=anchor.winfo_rootx(),anchor.winfo_rooty()+anchor.winfo_height()
        menu.popup(self.app.winfo_pointerx() if x is None else x,self.app.winfo_pointery() if y is None else y)
        return menu

    def remove_menu(self):
        menu=PopupMenu(self.app,self.p);disabled=not self.capabilities()['remove']
        menu.add_item('Listeden kaldır',self.app.delete_selected,disabled=disabled,description='Dosyalar diskte kalır')
        menu.add_item('Dosyalarla birlikte kaldır',lambda:self.app.delete_selected(True),disabled=disabled,danger=True,description='İndirilen dosyalar da silinir · onay istenir')
        return self.popup(menu,self.actions['remove'])

    def queue_menu(self):
        menu=PopupMenu(self.app,self.p)
        for queue in self.app.settings['queues']:
            name=queue['name'];menu.add_item(name,submenu=lambda child,n=name:self.queue_items(child,n))
        menu.add_separator();menu.add_item('Kuyruk ve zamanlama ayarları',lambda:self.open_settings_section('Kuyruk'))
        return self.popup(menu,self.queue_button)

    def queue_items(self,menu,name):
        menu.add_item('Başlat',lambda:self.app.start_queue(name))
        menu.add_item('Duraklat',lambda:self.app.pause_queue(name))
        menu.add_item('Seçilileri bu kuyruğa taşı',lambda:self.app.queue_selected(name),disabled=not self.capabilities()['queue'])

    def column_menu(self):
        menu=PopupMenu(self.app,self.p);menu.add_caption('GÖRÜNÜR SÜTUNLAR')
        visible=set(self.app.tree.cget('displaycolumns'));self.app.column_vars={}
        for name,label,width in COLUMNS:
            variable=tk.BooleanVar(self.app,value=name in visible);self.app.column_vars[name]=variable
            menu.add_item(label,self.app.save_columns,variable=variable,check=True,disabled=name=='filename',shortcut='her zaman' if name=='filename' else '')
        menu.add_separator();menu.add_item('Varsayılana dön',self.reset_columns)
        return self.popup(menu,self.columns_button)

    def reset_columns(self):
        from utils import save_settings
        from atlas_view import column_preferences
        key,defaults=column_preferences(self.app.theme_family)
        self.app.settings[key]=list(defaults);save_settings(self.app.settings);self.app.apply_visible_columns();self.app.data_view.schedule()

    def context_menu(self,event):
        app=self.app;caps=self.capabilities();menu=PopupMenu(app,self.p)
        for label,key,command,shortcut in (('Dosyayı aç','open',app.open_file,'Enter'),('Klasörü göster','folder',app.open_folder,''),('İndirme ayrıntıları','details',app.show_selected_details,'Çift tık')):
            menu.add_item(label,command,disabled=not caps[key],shortcut=shortcut)
        menu.add_separator()
        for label,key,command in (('Devam et','resume',app.resume_selected),('Duraklat','pause',app.pause_selected),('İptal et','cancel',app.cancel_selected),('Sıfırdan indir','restart',app.restart_selected)):
            menu.add_item(label,command,disabled=not caps[key])
        menu.add_separator()
        menu.add_item('Kuyruğa ekle',submenu=self.move_queue_items,disabled=not caps['queue'])
        menu.add_item('İndirme önceliği',submenu=self.priority_items,disabled=not caps['priority'])
        menu.add_item('Hız grafiği',app.show_speed_graph,disabled=not caps['graph'])
        menu.add_item('SHA-256 kontrolü',app.verify_selected,disabled=not caps['verify'])
        menu.add_separator();menu.add_item('Listeden kaldır',app.delete_selected,disabled=not caps['remove'],shortcut='Del')
        menu.add_item('Dosyalarla birlikte kaldır',lambda:app.delete_selected(True),disabled=not caps['remove'],danger=True)
        app.context_menu=menu;return self.popup(menu,x=event.x_root,y=event.y_root)

    def move_queue_items(self,menu):
        for queue in self.app.settings['queues']:
            name=queue['name'];menu.add_item(name,lambda n=name:self.app.queue_selected(n))

    def priority_items(self,menu):
        values=[self.app.tree.item(item,'values')[-1] for item in self.app.tree.selection()]
        selected=values[0] if len(set(values))==1 else ''
        variable=tk.StringVar(self.app,value=selected)
        for title,value in (('Yüksek',1),('Normal',0),('Düşük',-1)):
            menu.add_item(title,lambda v=value:self.app.change_priority(v),variable=variable,value=title)

    def update_hud(self,speed):
        app=self.app
        self.update_capture_and_rate()
        app.lbl_status_summary.configure(text=app.hud_active.get()+' aktif')
        self.speed_label.configure(text=app.hud_speed.get())
        self.received_label.configure(text='Bu oturum '+app.hud_received.get())
        self.speed_points.append((time.monotonic(),speed));self.sparkline.set(tuple(self.speed_points))
        self.update_selection();self.update_disk()

    def update_capture_and_rate(self):
        app=self.app
        app.capture_label.configure(text='Tarayıcı yakalama açık' if __import__('capture_policy').capture_enabled(app.settings) else 'Tarayıcı yakalama kapalı')
        self.capture_tip.text=app.capture_label.text
        rate=app.settings.get('speed_limit_kbs',0)
        if app.settings.get('relax_mode'):label='Rahatlatıldı · '+number(app,app.settings['relax_limit_kbs'])+' KB/sn'
        else:label='Hız sınırı: '+(number(app,rate)+' KB/sn' if rate else 'Yok')
        app.relax_button.configure(text=label)
    def update_disk(self):
        app=self.app
        now=time.monotonic()
        if now>=self._disk_due and not self._disk_busy:
            self._disk_busy=True;self._disk_due=now+ATLAS['disk_refresh_seconds']
            folder=app.settings['download_dir']
            def work():
                try:
                    from utils import format_bytes
                    usage=shutil.disk_usage(folder)
                    value='Disk: '+number(app,format_bytes(usage.free))+' boş'
                except OSError:usage=None;value='Hazır'
                def done():
                    self._disk_busy=False
                    self.disk_usage=usage
                    if self.alive:app.lbl_status_info.configure(text=value)
                app.post_ui(done)
            threading.Thread(target=work,daemon=True).start()

    def desktop_notify(self,title,message):
        if self.app.settings.get('notifications_enabled',True):
            from gui import show_desktop_notification
            threading.Thread(target=show_desktop_notification,args=(title,message),daemon=True).start()

    def dispose(self,event):
        if event.widget is not self.body or not self.alive:return
        self.alive=False
        if self.menu and self.menu.winfo_exists():self.menu.close_root()
        if hasattr(self,'toast_manager'):self.toast_manager.close()
        for binding,identifier in (('<Control-f>',self.search_binding),('<Control-F>',self.search_upper_binding)):
            self.app.unbind(binding,identifier)
        try:self.app.search_var.trace_remove('write',self.search_trace)
        except tk.TclError:pass


def build(app):
    return AtlasWorkspace(app)
