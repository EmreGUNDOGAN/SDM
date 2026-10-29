"""Odak B01–B07: rail, card list, live drawer and shared settings page."""
from collections import deque
import time
import tkinter as tk
import ttkbootstrap as tb
from layout_atlas import AtlasWorkspace,NavButton
from theme_widgets import Button,Panel,Search
from ui_controls import Select
from ui_indicators import SpeedChart
from ui_dialog import label
from ui_surface import TextLabel
from ui_overlays import PopupMenu,ToastManager,Tooltip
from atlas_view import matches_status,available_actions,number
from list_display import COLUMNS
from ui_tokens import SIZES


class OdakWorkspace(AtlasWorkspace):
    def __init__(self,app):
        self.app=app;self.p=app.palette;self.alive=True;self.menu=None;self.tooltips=[];self.drawer=None;self.dismissed=None;self.settings_page=None
        app.current_status_filter=getattr(app,'current_status_filter','Tümü');app.current_queue_filter=getattr(app,'current_queue_filter',None)
        self.speed_points=deque(maxlen=120);app._atlas_workspace=self;p=self.p
        self.body=tk.Frame(app,bg=p['bg']);self.body.pack(fill='both',expand=True);self.body.bind('<Destroy>',self.dispose)
        self.rail=tk.Frame(self.body,bg=p['side'],width=68);self.rail.pack(side='left',fill='y');self.rail.pack_propagate(False)
        logo=label(self.rail,'SDM',palette=p,size=16,weight='Bold');logo.pack(pady=24)
        self.rail_buttons={}
        for key,title,glyph in [('downloads','İndirmeler','download'),('queues','Kuyruklar','queue'),('video','Video','video'),('tools','Araçlar','wrench'),('hud','Masaüstü HUD','monitor'),('settings','Ayarlar','settings')]:
            b=Button(self.rail,'',lambda k=key:self.navigate(k),palette=p,kind='icon',width=44,height=44);b.icon_name=glyph;b.pack(pady=6);b.draw();self.rail_buttons[key]=b;self.tooltips.append(Tooltip(b,title,p))
        self.rail_buttons['downloads'].selected=True
        self.shell=tk.Frame(self.body,bg=p['bg']);self.shell.pack(side='left',fill='both',expand=True)
        self.main=tk.Frame(self.shell,bg=p['bg']);self.main.pack(fill='both',expand=True)
        header=tk.Frame(self.main,bg=p['bg']);header.pack(fill='x',padx=24,pady=20)
        Button(header,'Yeni indirme',app.open_add_dialog,palette=p,kind='primary',height=SIZES['input']).pack(side='right')
        app.capture_label=Button(header,'Yakalama açık',app.toggle_capture,palette=p,kind='soft',width=146,height=SIZES['input']);app.capture_label.status_badge=True;app.capture_label.pack(side='right',padx=10)
        app.search_var=tk.StringVar(app,getattr(app,'search_term',''));self.search_trace=app.search_var.trace_add('write',lambda *args:app._on_search_change())
        app.search_control=Search(header,app.search_var,p,placeholder='Dosya adı veya adres ara',text_size=13);app.search_control.configure(width=220);app.search_control.pack(side='right')
        label(header,'İndirmeler',palette=p,size=20,weight='Bold').pack(side='left')
        self.search_binding=app.bind('<Control-f>',self.focus_search,add='+');self.search_upper_binding=app.bind('<Control-F>',self.focus_search,add='+')
        self.escape_binding=app.bind('<Escape>',lambda e:self.drawer.close() if self.drawer else None,add='+')
        row=tk.Frame(self.main,bg=p['bg']);row.pack(fill='x',padx=20,pady=(0,16))
        self.metrics={}
        for col,title,var,weight in [(0,'Toplam hız',app.hud_speed,2),(1,'Aktif',app.hud_active,1),(2,'Bu oturum',app.hud_received,1)]:
            row.columnconfigure(col,weight=weight,uniform='summary');card=Panel(row,dict(p,panel=p['card']),padding=16,radius=16);card.configure(height=136);card.grid(row=0,column=col,sticky='nsew',padx=4)
            label(card.content,title,palette=p,size=12,muted=True).pack(anchor='w');label(card.content,variable=var,palette=p,size=26,weight='Bold').pack(anchor='w',pady=6)
            if col==0:self.summary_chart=SpeedChart(card.content,p,height=46,axes=False);self.summary_chart.pack(fill='x')
            elif col==1:self.active_hint=label(card.content,'',palette=p,size=12,muted=True);self.active_hint.pack(anchor='w')
        filters=tk.Frame(self.main,bg=p['bg']);filters.pack(fill='x',padx=24,pady=(0,8))
        for name,title in [('Tümü','Tümü'),('Devam Edenler','Aktif'),('Tamamlananlar','Tamamlanan'),('Hatalı','Hatalı')]:
            b=NavButton(filters,title,lambda n=name:app.select_status_filter(n),dict(p,side=p['bg']),color='accent');b.configure(width=156);b.pack(side='left',padx=2);app.status_buttons[name]=b
        self.sort=tk.StringVar(app,'added');Select(filters,{'added':'Eklenme','name':'Dosya adı','size':'Boyut','status':'Durum'},self.sort,palette=p,width=150,command=app.refresh_downloads).pack(side='right')
        categories=tk.Frame(self.main,bg=p['bg']);categories.pack(fill='x',padx=24,pady=(0,16))
        for name in ('Tümü','Video','Müzik','Belgeler','Arşivler','Resimler','Programlar','Diğer'):
            b=Button(categories,name,lambda n=name:app.select_category(n),palette=p,kind='soft',height=28);b.pack(side='left',padx=3);app.category_buttons[name]=b
        footer=tk.Frame(self.main,bg=p['footer']);footer.pack(side='bottom',fill='x')
        app.lbl_status_summary=label(footer,'Hazır',palette=p,size=12,muted=True);app.lbl_status_summary.pack(side='left',padx=24,pady=8)
        app.lbl_status_info=label(footer,'',palette=p,size=12,muted=True);app.lbl_status_info.max_width=420;app.lbl_status_info.pack(side='right',padx=24)
        app.relax_button=Button(footer,'İnterneti rahatlat',app.toggle_relax,palette=p,kind='ghost');app.relax_button.pack(side='right')
        self.toolbar=tk.Frame(self.main,bg=p['footer']);self.selection_label=label(self.toolbar,'',palette=p,size=12);self.selection_label.pack(side='left',padx=16)
        self.actions={}
        for key,title,command in [('resume','Devam',app.resume_selected),('pause','Duraklat',app.pause_selected),('cancel','İptal',app.cancel_selected),('remove','Kaldır ▾',app.show_remove_menu),('folder','Klasör',app.open_folder)]:
            b=Button(self.toolbar,title,command,palette=p,kind='ghost');b.pack(side='left',padx=3,pady=8);self.actions[key]=b;app.action_buttons.append(b)
        self.content=tk.Frame(self.main,bg=p['bg']);self.content.pack(fill='both',expand=True)
        self.listing=tk.Frame(self.content,bg=p['bg']);self.listing.pack(side='left',fill='both',expand=True,padx=24)
        app.style.configure('SDM.Treeview',rowheight=112,background=p['bg'],fieldbackground=p['bg'],borderwidth=0)
        app.tree=tb.Treeview(self.listing,columns=tuple(c[0] for c in COLUMNS),show='tree',selectmode='extended',style='SDM.Treeview')
        app.tree.column('#0',width=0,minwidth=0,stretch=False)
        for name,title,width in COLUMNS:app.tree.heading(name,text=title);app.tree.column(name,width=width,stretch=name=='filename')
        app.tree.column('filename',width=500,minwidth=100);app.tree.configure(displaycolumns=('filename',))
        self.ys=tb.Scrollbar(self.listing,orient='vertical',command=app.tree.yview);app.tree.configure(yscrollcommand=self.scroll_y)
        app.tree.grid(row=0,column=0,sticky='nsew');self.ys.grid(row=0,column=1,sticky='ns');self.listing.rowconfigure(0,weight=1);self.listing.columnconfigure(0,weight=1)
        from odak_cards import CardSurface
        app.data_view=CardSurface(app);app.context_menu=None;app._progress_canvases={};app._status_canvases={}
        app.tree.bind('<Button-3>',app._on_tree_right_click);app.tree.bind('<Double-1>',app._on_tree_double_click)
        app.tree.bind('<<TreeviewSelect>>',lambda e:app.update_action_states());app.tree.bind('<Return>',lambda e:self.open_selected())
        self.build_empty();self.toast_manager=ToastManager(app,p,self.desktop_notify)
        app.refresh_downloads();app.update_action_states()
    def sort_records(self,records):
        key=self.sort.get();return sorted(records,key=lambda r:r['filename'].casefold() if key=='name' else r['filesize'] if key=='size' else r['status'] if key=='status' else r['id'],reverse=key in ('added','size'))
    def sync(self,records,all_records):
        app=self.app
        for name,button in app.status_buttons.items():button.selected=name==app.current_status_filter;button.set_count(sum(matches_status(r['status'],name) for r in all_records));button.draw()
        for name,button in app.category_buttons.items():button.selected=name==app.current_category;button.draw()
        if records:
            self.empty.pack_forget()
            if not self.content.winfo_manager():self.content.pack(fill='both',expand=True)
        else:
            if self.drawer:self.drawer.close()
            self.content.pack_forget();self.empty.pack(fill='both',expand=True)
            app.empty_label.configure(text='Aramanızla eşleşen indirme bulunamadı' if app.search_term else 'Bu görünümde henüz indirme yok' if app.current_category!='Tümü' or app.current_status_filter!='Tümü' or app.current_queue_filter else 'Henüz indirme yok')
            if app.search_term:app.empty_clear.pack(side='left',padx=6)
            else:app.empty_clear.pack_forget()
        self.update_selection()
    def update_selection(self):
        if not self.alive:return
        app=self.app;items=app.tree.selection();caps=self.capabilities()
        for key,button in self.actions.items():button.configure(state='normal' if caps[key] else 'disabled')
        if len(items)>1:
            if self.drawer:self.drawer.close()
            self.selection_label.configure(text=f'{len(items)} seçili');self.toolbar.pack(side='bottom',fill='x',before=self.content if self.content.winfo_manager() else None)
        else:self.toolbar.pack_forget()
        if len(items)==1:
            did=int(app.tree.item(items[0],'values')[0])
            if did!=self.dismissed and (not self.drawer or self.drawer.download_id!=did):self.open_detail(did)
        elif not items and self.drawer:self.drawer.close()
    def open_selected(self):
        ids=self.app._get_selected_ids()
        if len(ids)==1:self.open_detail(ids[0])
        return 'break'
    def open_detail(self,did):
        if self.settings_page and not self.leave_settings():return
        if not self.alive:return self.app.show_download_details(did)
        if self.settings_page:self.settings_page.destroy();self.settings_page=None;self.main.pack(fill='both',expand=True)
        item='download-'+str(did)
        if self.app.tree.exists(item):self.app.tree.selection_set(item)
        if self.drawer and self.drawer.download_id==did:return self.drawer
        if self.drawer:self.drawer.close()
        self.dismissed=None
        from odak_drawer import TransferDrawer
        self.drawer=TransferDrawer(self,did);return self.drawer
    def card_action(self,did):
        record=self.app.db.get_download(did)
        if not record:return
        task=self.app.video_tasks.get(did) or self.app.engine.get_task(did);state=task.status if task else record['status']
        if state in ('Birleştiriliyor','Dönüştürülüyor'):return
        if state=='Tamamlandı':self.app.tree.selection_set('download-'+str(did));self.app.open_file()
        elif state in ('İndiriliyor','Bekliyor'):self.app.pause_download(did)
        else:self.app.resume_download(did)
    def leave_settings(self):
        if not self.settings_page or not self.settings_page.change_count.get():return True
        from ui_messages import choose
        answer=choose(self.app,'Değişiklikler kaydedilsin mi?','Kaydedilmemiş ayar değişiklikleri var.',(('save','Kaydet','primary'),('discard','Kaydetme','secondary'),('cancel','Vazgeç','ghost')))
        if answer=='save':return self.settings_page.save()
        if answer=='discard':self.settings_page.cancel_preview();return True
        return answer=='discard'
    def navigate(self,key):
        if key=='settings' and self.settings_page:return
        if not self.leave_settings():return
        if not self.alive:
            workspace=self.app._atlas_workspace
            if isinstance(workspace,OdakWorkspace):return workspace.navigate(key)
            if key=='tools':return self.app.open_tools()
            if key=='video':return self.app.select_category('Video')
            return
        if self.settings_page:self.settings_page.destroy();self.settings_page=None
        self.main.pack(fill='both',expand=True)
        for name,button in self.rail_buttons.items():button.selected=name==key;button.draw()
        if key=='settings':
            if self.drawer:self.drawer.close()
            self.main.pack_forget()
            from modern_settings import SettingsContent
            self.settings_page=SettingsContent(self.shell,self.app,embedded=True);self.settings_page.pack(fill='both',expand=True)
        elif key=='queues':self.queue_menu()
        elif key=='video':self.app.select_category('Video')
        elif key=='downloads':self.app.select_category('Tümü')
        elif key=='tools':self.app.open_tools()
        elif key=='hud':
            hud=getattr(self.app,'_mini_hud',None)
            if hud and hud.winfo_exists():hud.close()
            else:self.app.show_mini_hud()
    def open_settings_section(self,section):
        self.navigate('settings')
        if self.settings_page:self.settings_page.show_section(section)
    def queue_menu(self):
        menu=PopupMenu(self.app,self.p)
        for queue in self.app.settings['queues']:
            name=queue['name'];menu.add_item(name,submenu=lambda child,n=name:self.queue_items(child,n));menu.add_item(name+' · filtrele',lambda n=name:self.select_queue(n))
        menu.add_separator();menu.add_item('Kuyruk ve zamanlama ayarları',lambda:self.open_settings_section('Kuyruk'))
        return self.popup(menu,x=self.rail.winfo_rootx()+68,y=self.rail_buttons['queues'].winfo_rooty())
    def update_hud(self,speed):
        self.speed_points.append((time.monotonic(),speed));self.summary_chart.set(tuple(self.speed_points))
        self.active_hint.configure(text='Eşzamanlı sınır: '+str(self.app.settings['max_simultaneous_downloads']))
        self.app.relax_button.configure(text='Rahatlatıldı' if self.app.settings.get('relax_mode') else 'İnterneti rahatlat')
        self.update_selection()
    def dispose(self,event):
        if event.widget is self.body and self.alive:self.app.unbind('<Escape>',self.escape_binding)
        super().dispose(event)


def build(app):return OdakWorkspace(app)
