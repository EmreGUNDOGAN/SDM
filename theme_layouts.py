"""Atlas sidebar, Orbit upper navigation/right rail, Nova full-width workspace."""
import sys
import tkinter as tk
from pathlib import Path
import ttkbootstrap as tb
from PIL import Image,ImageTk
from theme_catalog import theme_key,palette,migrate_settings
from theme_widgets import Button,Search,Panel
from list_display import COLUMNS
from ui_surface import register_fonts,TextLabel,icon,photo,ICON_NAMES

CATEGORIES=[('Tümü',7),('Belgeler',8),('Resimler',9),('Müzik',10),('Video',11),('Arşivler',12),('Programlar',13),('Diğer',7)]
STATUS=[('Tümü',7),('Devam Edenler',14),('Tamamlananlar',15)]

def build_ui(app):
    app.settings=migrate_settings(app.settings);key=theme_key(app.settings)
    design,mode=key.split('_');app.theme_family=design;app.ui_theme=mode;app.palette=palette(key);p=app.palette
    # Staged migration: Odak's full card/rail layout arrives in phase 5.
    # Keep the existing renderer available until its replacement is verified.
    family='orbit' if design=='odak' else design
    register_fonts()
    from tkinter import font as tkfont
    for named in ('TkDefaultFont','TkTextFont','TkMenuFont','TkHeadingFont'):
        tkfont.nametofont(named,root=app).configure(family='Inter',size=-13)
    app.style.theme_use('darkly' if mode=='dark' else 'cosmo');app.configure(bg=p['bg']);app.after_idle(app.sync_caption)
    app.style.configure('.',font=('Inter',-13),foreground=p['text'],background=p['bg'])
    for style in ('TFrame','TLabel'):app.style.configure(style,background=p['bg'],foreground=p['text'])
    app.style.configure('TEntry',foreground=p['text'],fieldbackground=p['panel'])
    app.style.configure('TCombobox',foreground=p['text'],fieldbackground=p['panel'])
    for style in ('TButton','primary.TButton','secondary.TButton','secondary.Outline.TButton','secondary.Link.TButton'):
        app.style.configure(style,foreground=p['text'],background=p['panel'],bordercolor=p['line'],focuscolor=p['accent'],padding=(12,8))
        app.style.map(style,foreground=[('disabled',p['muted']),('!disabled',p['text'])],background=[('pressed',p['selected']),('active',p['hover']),('!disabled',p['panel'])])
        def without_dots(nodes):
            result=[]
            for name,options in nodes:
                options=dict(options)
                if 'children' in options:options['children']=without_dots(options['children'])
                if name.endswith('.focus'):result.extend(options.get('children',[]))
                else:result.append((name,options))
            return result
        app.style.layout(style,without_dots(app.style.layout(style)))
    app.style.configure('SDM.Treeview',foreground=p['text'],background=p['bg'],fieldbackground=p['bg'],rowheight=62,font=('Inter',-13),borderwidth=0)
    app.style.configure('SDM.Treeview.Heading',foreground=p['muted'],background=p['panel'],font=('Inter',-12),padding=(8,12))
    app.style.map('SDM.Treeview',foreground=[('selected',p['text'])],background=[('selected',p['selected'])])
    app.style.configure('SDM.Side.TFrame',background=p['panel']);app.style.configure('SDM.Side.TLabel',background=p['panel'],foreground=p['muted'])
    root=Path(getattr(sys,'_MEIPASS',Path(__file__).parent))
    app.icon_images={i:photo(icon(name,18,p['text']),app) for i,name in enumerate(ICON_NAMES)}
    app._sidebar_logo=ImageTk.PhotoImage(Image.open(root/'assets/logo.png').resize((36,36)),master=app)
    app.category_buttons={};app.status_buttons={};app.action_buttons=[]
    app.hud_active=tk.StringVar(value='0');app.hud_speed=tk.StringVar(value='0 KB/s');app.hud_received=tk.StringVar(value='0 B')
    app.filter_summary=tk.StringVar();app.page_title=tk.StringVar()
    app._atlas_workspace=None
    if design=='odak':
        from layout_odak import build
        return build(app)
    if family=='atlas':
        from layout_atlas import build
        return build(app)
    def frame(parent,bg=None,**pack):
        widget=tk.Frame(parent,bg=bg or parent.cget('bg'));widget.pack(**pack);return widget
    def label(parent,text='',var=None,size=10,color=None,bold=False,**pack):
        w=TextLabel(parent,text=text,textvariable=var,size=round(size*1.5),weight='SemiBold' if bold else 'Regular',fg=color or p['text']);w.pack(**pack);return w
    def button(parent,text,command,icon=None,primary=False,quiet=False,**pack):
        w=Button(parent,text,command,palette=p,image=app.icon_images[icon] if icon is not None else None,primary=primary,quiet=quiet)
        w.icon_name=ICON_NAMES[icon] if icon is not None else None
        w.pack(**pack);return w
    def brand(parent):
        tk.Label(parent,image=app._sidebar_logo,bg=parent.cget('bg')).pack(side='left',padx=(0,10))
        TextLabel(parent,'SDM',size=30,weight='Bold',fg=p['text']).pack(side='left')
    def categories(parent,vertical=False,items=CATEGORIES,store=None):
        for name,icon in items:
            text='Tüm indirmeler' if name=='Tümü' and vertical else name
            w=button(parent,text,lambda c=name:app.select_category(c),icon,quiet=True,**({'fill':'x','pady':3} if vertical else {'side':'left','padx':2}))
            w.underline=family=='orbit';w.side_accent=vertical
            if name=='Tümü':w.icon_name='download'
            (store if store is not None else app.category_buttons)[name]=w
    def status_filters(parent):
        for name,icon in STATUS:
            w=button(parent,name,lambda c=name:app.select_status_filter(c),quiet=True,side='left',padx=2)
            w.selected=name==getattr(app,'current_status_filter','Tümü');w.draw();app.status_buttons[name]=w
    def new_button(parent):button(parent,'Yeni indirme',app.open_add_dialog,0,primary=True,side='left',padx=(0,10))
    def actions(parent):
        for text,icon,command in [('Devam',1,app.resume_selected),('Duraklat',2,app.pause_selected),('İptal',3,app.cancel_selected),('Kaldır ▾',4,app.show_remove_menu)]:
            b=button(parent,text,command,icon,quiet=True,side='left',padx=2);app.action_buttons.append(b)
        if family!='atlas':app.action_buttons.append(button(parent,'Klasörü aç',app.open_folder,7,quiet=True,side='left',padx=2))
    def relax(parent):
        app.relax_button=button(parent,'İnterneti rahatlat',app.toggle_relax,quiet=True,side='left',padx=5)
    def search(parent,fill=False):
        button(parent,'Sütunlar',app.show_column_menu,6,side='right',padx=(8,0))
        app.search_var=tk.StringVar(value=getattr(app,'search_term',''));app.search_var.trace_add('write',lambda *args:app._on_search_change())
        app.search_control=Search(parent,app.search_var,p);app.search_control.pack(side='right',fill='x',expand=fill)
    def capture(parent):
        app.capture_label=button(parent,'● Yakalama açık',app.toggle_capture,quiet=True,side='right',padx=8)
        app.capture_label.status_badge=True;app.capture_label.configure(height=32)
    def metrics(parent,cards=False,vertical=False):
        for title,var,icon_id in [('Aktif indirmeler',app.hud_active,14),('Toplam indirme hızı',app.hud_speed,16),('Bu oturumda indirilen',app.hud_received,7)]:
            if cards:
                panel=Panel(parent,dict(p,panel=p['control']));panel.pack(side='left',fill='x',expand=True,padx=4)
                group=panel.content
            else:group=frame(parent,**({'fill':'x','pady':12} if vertical else {'side':'left','fill':'x','expand':True,'padx':4}))
            if cards:
                glyph=photo(icon({'Aktif indirmeler':'download','Toplam indirme hızı':'speed','Bu oturumda indirilen':'database'}[title],28,p['accent']),app)
                picture=tk.Label(group,image=glyph,bg=group.cget('bg'));picture._glyph=glyph;picture.pack(side='left',padx=(0,12))
            label(group,title,size=9,color=p['muted'],anchor='w');label(group,var=var,size=19,bold=True,anchor='w')
    body=frame(app,fill='both',expand=True)
    if family in ('atlas','nova'):
        sidebar=frame(body,bg=p['panel'],side='left',fill='y');sidebar.configure(width=204,padx=16,pady=18);sidebar.pack_propagate(False)
        brand(frame(sidebar,fill='x',pady=(0,22)))
        button(sidebar,'Ayarlar',app.open_settings_dialog,5,quiet=True,side='bottom',fill='x',pady=8)
        from ttkbootstrap.widgets.scrolled import ScrolledFrame
        app.sidebar_scroll=ScrolledFrame(sidebar,height=340,width=174,auto_hide=False,style='SDM.Side.TFrame');app.sidebar_scroll.pack(fill='both',expand=True);app.sidebar_scroll._canvas.configure(bg=p['panel'])
        # Interior is ttk; a normal frame gives canvas controls their true background.
        interior=tk.Frame(app.sidebar_scroll,bg=p['panel']);interior.pack(fill='both',expand=True)
        categories(interior,True,STATUS);label(interior,'Kategoriler',size=9,color=p['muted'],anchor='w',pady=(18,8))
        categories(interior,True,CATEGORIES[1:])
        tk.Frame(interior,bg=p['line'],height=1).pack(fill='x',pady=(18,12))
        tools_button=button(interior,'İndirme araçları',app.open_tools,7,quiet=True,fill='x',pady=(0,4));tools_button.icon_name='wrench'
        hud_button=button(interior,'Masaüstü HUD',app.show_mini_hud,7,quiet=True,fill='x');hud_button.icon_name='monitor'
        main=frame(body,side='left',fill='both',expand=True);main.configure(padx=20,pady=18)
        header=frame(main,fill='x',pady=(0,12));label(header,'İndirmeler',size=18,bold=True,side='left');capture(header)
        label(main,var=app.filter_summary,size=9,color=p['muted'],anchor='w',pady=(0,12))
        toolbar=frame(main,fill='x',pady=(0,12));new_button(toolbar)
        if family=='atlas':actions(toolbar)
        button(toolbar,'Kuyruk',app.show_queue_menu,icon=7 if family=='nova' else None,quiet=True,side='left');relax(toolbar)
        search(frame(main,fill='x',pady=(0,14)),True)
        if family=='atlas':metrics(frame(main,fill='x',pady=(0,16)),cards=True)
        else:
            compact=frame(main,fill='x',pady=(0,16))
            for title,var in [('Aktif',app.hud_active),('Toplam hız',app.hud_speed),('Bu oturum',app.hud_received)]:
                group=frame(compact,side='left',padx=(0,22));label(group,title,size=9,color=p['muted'],side='left',padx=(0,7));label(group,var=var,size=10,bold=True,side='left')
    else:
        nav=frame(body,fill='x',padx=20,pady=12);brand(nav)
        active_nav=button(nav,'İndirmeler',lambda:app.select_category('Tümü'),quiet=True,side='left',padx=(22,8));active_nav.selected=True;active_nav.underline=True
        button(nav,'Araçlar',app.open_tools,quiet=True,side='left')
        button(nav,'Ayarlar',app.open_settings_dialog,quiet=True,side='left')
        theme_toggle=Button(nav,'',app.toggle_theme,palette=p,quiet=True,width=42);theme_toggle.icon_name='moon' if mode=='light' else 'sun';theme_toggle.pack(side='right',padx=(8,0))
        capture(nav)
        if family=='orbit':categories(frame(body,fill='x',padx=20,pady=8))
        else:
            app.search_var=tk.StringVar(value=getattr(app,'search_term',''));app.search_var.trace_add('write',lambda *args:app._on_search_change())
            app.search_control=Search(nav,app.search_var,p);app.search_control.pack(side='right',padx=8)
        workspace=frame(body,fill='both',expand=True,padx=20,pady=(8,0))
        if family=='orbit':
            rail=frame(workspace,bg=p['panel'],side='right',fill='y',padx=(16,0));rail.configure(width=204,padx=16,pady=14);rail.pack_propagate(False)
            label(rail,'Oturum',bold=True,anchor='w');metrics(rail,vertical=True)
            label(rail,'Kuyruk',bold=True,anchor='w',pady=(12,4));button(rail,'Kuyruğu aç',app.show_queue_menu,fill='x',pady=6)
            app.relax_button=button(rail,'İnterneti rahatlat',app.toggle_relax,quiet=True,fill='x',pady=6)
            button(rail,'Masaüstü HUD',app.show_mini_hud,quiet=True,fill='x',pady=6)
        main=frame(workspace,side='left',fill='both',expand=True)
        head=frame(main,fill='x',pady=(0,12));label(head,var=app.page_title,size=16,bold=True,side='left');label(head,var=app.filter_summary,size=9,color=p['muted'],side='left',padx=12)
        if family=='orbit':new_button(frame(head,side='right'))
        else:
            for title,var in [('Bu oturum',app.hud_received),('Toplam hız',app.hud_speed),('Aktif',app.hud_active)]:
                group=frame(head,side='right',padx=10);label(group,title,size=9,color=p['muted'],side='left',padx=4);label(group,var=var,size=10,side='left')
            tool=frame(main,fill='x',pady=(0,12));new_button(tool);button(tool,'Kuyruk',app.show_queue_menu,quiet=True,side='left');relax(tool);button(tool,'Masaüstü HUD',app.show_mini_hud,quiet=True,side='right')
        filterbar=frame(main,fill='x',pady=(0,14))
        if family=='orbit':
            group=Panel(filterbar,p,padding=3);group.configure(width=325,height=46);group.pack(side='left',padx=(0,12));status_filters(group.content)
            search(filterbar,True)
        else:
            status_filters(filterbar)
            categories(frame(main,fill='x',pady=(0,10)))
            button(filterbar,'Sütunlar',app.show_column_menu,6,side='right')
    footer=frame(main,side='bottom',fill='x',pady=(8,8));app.lbl_status_summary=label(footer,'Hazır',color=p['muted'],side='left');app.lbl_status_info=label(footer,'',color=p['muted'],side='right')
    if family!='atlas':
        actionbar=frame(main,side='bottom',fill='x',pady=12)
        if family=='nova':
            pill=Panel(actionbar,p,padding=10,radius=12);pill.configure(width=690,height=64);pill.pack();actions(pill.content)
        else:center=frame(actionbar);actions(center)
    listing=frame(main,fill='both',expand=True)
    app.tree=tb.Treeview(listing,columns=tuple(c[0] for c in COLUMNS),show='tree headings',selectmode='extended',style='SDM.Treeview')
    app.tree.column('#0',width=0,minwidth=0,stretch=False)
    for name,title,width in COLUMNS:
        app.tree.heading(name,text=title,command=app.show_column_menu);app.tree.column(name,width=260 if name=='filename' else width,anchor='w' if name=='filename' else 'center')
    app.tree.column('progress',width=150)
    for column,width in {'filename':180,'size':80,'downloaded':100,'remaining':100,'progress':135,'speed':100,'eta':85,'status':120}.items():
        app.tree.column(column,width=width,minwidth=width,stretch=column=='filename')
    app.apply_visible_columns()
    ys=tb.Scrollbar(listing,orient='vertical',command=app.tree.yview);xs=tb.Scrollbar(listing,orient='horizontal',command=app.tree.xview)
    app.tree.configure(yscrollcommand=lambda *args:(ys.set(*args),app.data_view.schedule() if hasattr(app,'data_view') and app.data_view.winfo_exists() else None),xscrollcommand=lambda *args:(xs.set(*args),app.data_view.schedule() if hasattr(app,'data_view') and app.data_view.winfo_exists() else None));app.tree.grid(row=0,column=0,sticky='nsew');ys.grid(row=0,column=1,sticky='ns');xs.grid(row=1,column=0,sticky='ew')
    listing.rowconfigure(0,weight=1);listing.columnconfigure(0,weight=1)
    app.empty_label=tk.Label(listing,bg=p['bg'],fg=p['muted'],font=('Inter',-15),text='')
    app.empty_clear=Button(listing,'Aramayı temizle',lambda:app.search_var.set(''),palette=p,quiet=True)
    app.tree.bind('<Double-1>',app._on_tree_double_click);app.tree.bind('<Button-3>',app._on_tree_right_click)
    app.tree.bind('<Configure>',lambda e:app.after_idle(app.paint_progress));app.tree.bind('<<TreeviewSelect>>',lambda e:app.update_action_states())
    from ui_table_surface import TableSurface
    app.data_view=TableSurface(app)
    app.context_menu=tk.Menu(app,tearoff=0,bg=p['panel'],fg=p['text'],activebackground=p['selected'],activeforeground=p['text'])
    priority=tk.Menu(app.context_menu,tearoff=0)
    for title,value in [('Yüksek',1),('Normal',0),('Düşük',-1)]:priority.add_command(label=title,command=lambda v=value:app.change_priority(v))
    app.context_menu.add_cascade(label='İndirme önceliği',menu=priority);app.context_menu.add_command(label='Hız grafiği',command=app.show_speed_graph)
    for title,command in [('Devam et',app.resume_selected),('Sıfırdan indir',app.restart_selected),('Kuyruğa ekle',app.queue_selected),('Duraklat',app.pause_selected),('İptal et',app.cancel_selected),('Dosyayı aç',app.open_file),('Klasörü göster',app.open_folder),('SHA-256 kontrolü',app.verify_selected),('Listeden kaldır',app.delete_selected),('Dosyaları da kaldır',lambda:app.delete_selected(True)),('İndirme ayrıntıları',app.show_selected_details)]:app.context_menu.add_command(label=title,command=command)
    app._progress_canvases={};app._status_canvases={};app.select_category(getattr(app,'current_category','Tümü'));app.update_action_states()
