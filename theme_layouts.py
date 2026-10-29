"""Shared theme preparation and routing for Atlas and Odak."""
import tkinter as tk
import ttkbootstrap as tb
from theme_catalog import theme_key,palette,migrate_settings
from ui_surface import register_fonts,icon,photo,ICON_NAMES
from ui_tokens import text_px

def build_ui(app):
    app.settings=migrate_settings(app.settings);key=theme_key(app.settings)
    design,mode=key.split('_');app.theme_family=design;app.ui_theme=mode;app.palette=palette(key);p=app.palette
    register_fonts()
    from tkinter import font as tkfont
    for named in ('TkDefaultFont','TkTextFont','TkMenuFont','TkHeadingFont'):
        tkfont.nametofont(named,root=app).configure(family='Inter',size=text_px(13))
    app.style.theme_use('darkly' if mode=='dark' else 'cosmo');app.configure(bg=p['bg']);app.after_idle(app.sync_caption)
    app.style.configure('.',font=('Inter',text_px(13)),foreground=p['text'],background=p['bg'])
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
    app.style.configure('SDM.Treeview',foreground=p['text'],background=p['bg'],fieldbackground=p['bg'],rowheight=62,font=('Inter',text_px(13)),borderwidth=0)
    app.style.configure('SDM.Treeview.Heading',foreground=p['muted'],background=p['panel'],font=('Inter',text_px(12)),padding=(8,12))
    app.style.map('SDM.Treeview',foreground=[('selected',p['text'])],background=[('selected',p['selected'])])
    app.style.configure('SDM.Side.TFrame',background=p['panel']);app.style.configure('SDM.Side.TLabel',background=p['panel'],foreground=p['muted'])
    app.icon_images={i:photo(icon(name,18,p['text']),app) for i,name in enumerate(ICON_NAMES)}
    app.category_buttons={};app.status_buttons={};app.action_buttons=[]
    app.hud_active=tk.StringVar(value='0');app.hud_speed=tk.StringVar(value='0 KB/sn');app.hud_received=tk.StringVar(value='0 B')
    app.filter_summary=tk.StringVar();app.page_title=tk.StringVar()
    app._atlas_workspace=None
    if design=='odak':
        from layout_odak import build
        return build(app)
    if design=='atlas':
        from layout_atlas import build
        return build(app)
