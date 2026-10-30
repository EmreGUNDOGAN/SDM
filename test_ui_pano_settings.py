"""P08–P13: bounded native counters and settings transactions in a fake profile."""


def main(design='pano'):
    import copy,hashlib,json,time
    from pathlib import Path
    from types import SimpleNamespace
    from unittest.mock import patch
    from tkinter import font as tkfont
    from gui import MainWindow
    from modern_settings import SettingsDialog,BOUNDS
    from preferences import export_settings
    from utils import ensure_config_dir,CONFIG_FILE
    from tools.window_capture import capture_client
    from tools.report_settings_previews import PANO_SOURCES,YORUNGE_SOURCES,PANO_STATES
    app=MainWindow();app.engine.stop_engine();errors=[]
    app.report_callback_exception=lambda *args:errors.append(args)
    app.apply_settings(dict(app.settings,design=design,color_mode='system'))
    before=copy.deepcopy(app.settings);disk=CONFIG_FILE.read_bytes();data={}

    def settle():
        for _ in range(5):app.update();time.sleep(.02)
        assert not errors,errors

    def snapshot(window,state):
        window.geometry('+30+30');settle();image=capture_client(window);image.save(Path(f'build/{design}-settings-{state}.png'));return image

    try:
        clients={'Chrome':dict(seen=time.monotonic(),version='synthetic-current'),'Opera':dict(seen=time.monotonic()-120,version='synthetic-old')}
        with patch.object(app,'_browser_bridge',SimpleNamespace(client_snapshot=lambda:clients),create=True),patch('antivirus.find_kaspersky',side_effect=ValueError('Synthetic absence')):
            dialog=SettingsDialog(app);editor=dialog.content;settle()
            assert len(editor.tabs)==6 and editor.change_count.get()==0
            assert editor.vars['color_mode'].get()=='system' and editor.display_color_mode.get()==('dark' if design=='yorunge' else 'light')
            assert all(button.disabled for button in editor.color_selector.buttons.values())
            data['control_center_errors']=[]
            for key,control in editor.steppers.items():
                if design=='yorunge':
                    from ui_tokens import YORUNGE_MONO_FAMILY
                    assert tkfont.Font(font=control.entry.cget('font')).actual('family')==YORUNGE_MONO_FAMILY
                low,high=BOUNDS[key];control.variable.set(str(low));settle()
                assert control.minus.disabled and not control.plus.disabled
                control.plus.invoke();assert control.variable.get()==str(low+1)
                control.variable.set(str(high));settle();assert control.plus.disabled
                control.plus.invoke();assert control.variable.get()==str(high)
                editor.focus_widget(control.entry);settle();control.entry.event_generate('<Down>');settle();assert control.variable.get()==str(high-1)
                control.entry.event_generate('<Enter>');control.entry.event_generate('<MouseWheel>',delta=120);settle();assert control.variable.get()==str(high)
                control.edit();control.entry.delete(0,'end');control.entry.insert(0,'0');settle()
                assert editor.save_button.disabled and control.error and control.variable.get()=='0'
                assert app.settings==before and CONFIG_FILE.read_bytes()==disk
                control.entry.delete(0,'end');control.entry.insert(0,str(low));control.lock();settle()
                assert control.entry.cget('state')=='readonly'
                assert control.entry.winfo_height()>=tkfont.Font(font=control.entry.cget('font')).metrics('linespace'),'Counter text clipped'
                center=control.entry.winfo_rooty()+control.entry.winfo_height()/2
                data['control_center_errors'].extend(abs(button.winfo_rooty()+button.winfo_height()/2-center) for button in (control.minus,control.plus))
            assert max(data['control_center_errors'])<=.5,data
            editor.revert();settle();assert editor.collect()==editor.baseline
            assert 'Bağlı' in editor.client_status['Chrome'].cget('text') and 'doğrulanmadı' in editor.client_status['Opera'].cget('text')
            editor.queue_editor.add();editor.queue_editor.name.set('Synthetic Pano queue')
            editor.queue_editor.limit.set('0');settle();assert editor.save_button.disabled and editor.queue_editor.limit_stepper.error
            editor.queue_editor.limit.set('2');editor.queue_editor.quick_date(1);settle();assert not editor.save_button.disabled
            assert editor.collect()['queues'][-1]['once']
            editor.revert();settle()
            data['nav_text_x']=[]
            for index,section in enumerate(editor.tabs):
                editor.show_section(section);settle();editor.tabs[section].canvas.yview_moveto(0)
                assert editor.nav[section].kind==('ghost' if design=='yorunge' else 'primary')
                image=snapshot(dialog,str(index))
                from PIL import ImageColor
                button=editor.nav[section]
                x=button.winfo_rootx()-dialog.winfo_rootx();y=button.winfo_rooty()-dialog.winfo_rooty()+button.winfo_height()//2
                assert image.getpixel((x+8,y))[:3]==ImageColor.getrgb(editor.p['accent_nav'] if design=='yorunge' else editor.p['accent']),'Selected section fill mismatch'
                if design=='yorunge':
                    assert button.text.startswith(f'{index+1:02}') and button.side_accent
                    assert image.getpixel((x+1,y))[:3]==ImageColor.getrgb(editor.p['accent']),'Missing selected section stripe'
                    ink=[px-x for px in range(x+8,x+100) for py in range(y-12,y+12) if image.getpixel((px,py))[1]>100 and image.getpixel((px,py))[2]>120]
                    assert ink and 14<=min(ink)<=18,('Numbered navigation is not left aligned',section,min(ink) if ink else None)
                    data['nav_text_x'].append(min(ink))
                    from ui_dialog import AutoCard
                    def square_cards(widget):
                        for child in widget.winfo_children():
                            if isinstance(child,AutoCard):assert child.radius==0
                            square_cards(child)
                    square_cards(editor.tabs[section])
            if design=='yorunge':assert max(data['nav_text_x'])-min(data['nav_text_x'])<=1
            editor.show_section('Genel');settle();editor.tabs['Genel'].canvas.yview_moveto(0);editor.nav['Genel'].focus_force();settle()
            control=editor.steppers['default_connections'];canvas=editor.tabs['Genel'].canvas
            for _ in range(60):
                if app.focus_get() is control.entry:break
                app.focus_get().event_generate('<Tab>');settle()
            assert app.focus_get() is control.entry,'Tab did not reach the numeric field'
            assert canvas.winfo_rooty()<=control.entry.winfo_rooty()<canvas.winfo_rooty()+canvas.winfo_height(),('Focused counter is outside viewport',
                str(app.focus_get()),str(control.entry),canvas.winfo_rooty(),canvas.winfo_height(),control.entry.winfo_rooty(),canvas.yview(),editor.tabs['Genel'].content.winfo_reqheight())
            snapshot(dialog,'counters')
            dialog.geometry('760x700+30+30');editor.show_section('Kuyruk');settle();snapshot(dialog,'compact')
            from theme_widgets import Button
            def controls_fit(widget,canvas):
                for child in widget.winfo_children():
                    if isinstance(child,Button) and child.winfo_ismapped():
                        assert canvas.winfo_rootx()<=child.winfo_rootx() and child.winfo_rootx()+child.winfo_width()<=canvas.winfo_rootx()+canvas.winfo_width(),('Button clipped horizontally',child.text)
                    controls_fit(child,canvas)
            for section,state in (('Güncelleme','compact-update'),('Yedekleme','compact-backup')):
                editor.show_section(section);settle();editor.tabs[section].canvas.yview_moveto(0);settle()
                controls_fit(editor.tabs[section].content,editor.tabs[section].canvas);snapshot(dialog,state)
            if design=='yorunge':
                for section in editor.tabs:
                    editor.show_section(section);settle();editor.tabs[section].canvas.yview_moveto(0);settle()
                    controls_fit(editor.tabs[section].content,editor.tabs[section].canvas)
            editor.chips.input.variable.set('.zip');editor.chips.add_from_entry();editor.new_site.set('https://example.invalid/path');editor.add_site();settle()
            backup=ensure_config_dir()/'pano-synthetic-backup.json';export_settings(backup,dict(before,default_connections=12,github_token='synthetic-omitted'))
            assert 'github_token' not in json.loads(backup.read_text(encoding='utf-8'))['settings']
            with patch('modern_settings.filedialog.askopenfilename',return_value=str(backup)):editor.restore()
            settle();assert editor.vars['default_connections'].get()=='12'
            assert app.settings==before and CONFIG_FILE.read_bytes()==disk
            editor.cancel();settle();assert app.settings==before and CONFIG_FILE.read_bytes()==disk
        dialog=SettingsDialog(app);settle();editor=dialog.content;editor.vars['default_connections'].set('12');settle()
        assert editor.save();settle();assert app.engine.default_connections==12
        assert json.loads(CONFIG_FILE.read_text(encoding='utf-8'))['default_connections']==12
        data['sources']={name:hashlib.sha256(Path(name).read_bytes()).hexdigest() for name in (YORUNGE_SOURCES if design=='yorunge' else PANO_SOURCES)}
        data['previews']={state:hashlib.sha256(Path(f'build/{design}-settings-{state}.png').read_bytes()).hexdigest() for state in PANO_STATES}
        Path(f'build/{design}-settings-layout.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
        print(f'{design} settings: six pages, counter bounds/keys/wheel/edit/height, fixed mode, queue/backup draft, cancel/save and focus visibility: OK')
    finally:app.engine.stop_engine();app.destroy()


if __name__=='__main__':main()
