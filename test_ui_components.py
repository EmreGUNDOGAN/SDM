"""Explicit native Tk integration/visual fixture; never runs during discovery."""


def main():
    import os
    import time
    import tkinter as tk
    from pathlib import Path
    from unittest.mock import patch
    from PIL import ImageColor
    from tools.window_capture import capture_client
    from theme_catalog import THEMES,palette
    from theme_widgets import Button,Panel
    from ui_surface import register_fonts,TextLabel
    from ui_controls import (Switch,CheckBox,SegmentedControl,RadioCard,Select,
                             TextInput,ChipInput,FormRow)
    from ui_indicators import (StatusBadge,FileTile,ProgressBar,ProgressRing,
                               SpeedChart,Sparkline,PartMap,Summary,SectionTimeline)
    from ui_overlays import PopupMenu,MessageDialog,Drawer,ToastManager,Tooltip
    root=tk.Tk()
    # Fit both axes on the runner desktop; overflowing windows can retain stale
    # pixels outside the visible area. Scrollbars keep every control reachable.
    width=min(int(os.environ.get('SDM_COMPONENT_VIEWPORT_WIDTH','1080')),root.winfo_screenwidth()-100)
    height=min(int(os.environ.get('SDM_COMPONENT_VIEWPORT_HEIGHT','840')),root.winfo_screenheight()-100)
    root.geometry(f'{width}x{height}+20+20');root.title('SDM 0.5.0 · Shared components')
    register_fonts();errors=[]
    root.report_callback_exception=lambda *args:errors.append(args)
    Path('build').mkdir(exist_ok=True)
    native_environment=dict(tcl=str(root.tk.call('info','patchlevel')),
                            tk=str(root.tk.call('package','provide','Tk')),
                            screen_depth=root.winfo_screendepth(),
                            screen=(root.winfo_screenwidth(),root.winfo_screenheight()),
                            requested_viewport=(width,height))
    print('Native UI environment:',native_environment,flush=True)

    def wait_for(predicate,message):
        """Wait for Tk's asynchronous mapping/focus; never skip an assertion."""
        deadline=time.monotonic()+2
        while True:
            root.update()
            if predicate():return
            if time.monotonic()>=deadline:raise AssertionError(message)
            time.sleep(.01)

    # A pending dark-theme paint used to leave white pixels in a window-DC grab.
    # Capture must ask the owning top-level to render the current palette now.
    root.configure(bg='#ffffff');root.update()
    assert 0<=root.winfo_rootx() and root.winfo_rootx()+root.winfo_width()<=root.winfo_screenwidth()
    assert 0<=root.winfo_rooty() and root.winfo_rooty()+root.winfo_height()<=root.winfo_screenheight()
    root.configure(bg='#0e1116')
    pending=capture_client(root)
    pending_pixel=pending.getpixel((pending.width-10,10))
    assert pending_pixel==(14,17,22),dict(actual=pending_pixel,expected=(14,17,22),
                                         native=native_environment,size=pending.size,
                                         widget_background=root.cget('bg'))

    for theme in THEMES:
        p=palette(theme);root.configure(bg=p['bg'])
        marker=tk.Canvas(root,width=8,height=8,bg=p['accent'],highlightthickness=0)
        marker.place(x=0,y=0)
        gallery=tk.Frame(root,bg=p['bg']);gallery.pack(fill='both',expand=True,padx=20,pady=16)
        viewport=tk.Canvas(gallery,bg=p['bg'],highlightthickness=0)
        vertical=tk.Scrollbar(gallery,orient='vertical',command=viewport.yview)
        horizontal=tk.Scrollbar(gallery,orient='horizontal',command=viewport.xview)
        viewport.configure(yscrollcommand=vertical.set,xscrollcommand=horizontal.set)
        viewport.grid(row=0,column=0,sticky='nsew');vertical.grid(row=0,column=1,sticky='ns')
        horizontal.grid(row=1,column=0,sticky='ew')
        gallery.rowconfigure(0,weight=1);gallery.columnconfigure(0,weight=1)
        frame=tk.Frame(viewport,bg=p['bg'])
        content=viewport.create_window(0,0,window=frame,anchor='nw')
        frame.bind('<Configure>',lambda e:viewport.configure(scrollregion=viewport.bbox('all')))
        viewport.bind('<Configure>',lambda e:viewport.itemconfigure(content,width=max(e.width,frame.winfo_reqwidth())))

        def reveal(widget):
            wait_for(widget.winfo_ismapped,f'{theme}: target is not mapped')
            top=widget.winfo_rooty()-frame.winfo_rooty()
            bottom=top+widget.winfo_height()
            visible_top=viewport.canvasy(0);visible_bottom=visible_top+viewport.winfo_height()
            total=max(1,frame.winfo_height())
            if bottom>visible_bottom:viewport.yview_moveto(max(0,bottom-viewport.winfo_height())/total)
            elif top<visible_top:viewport.yview_moveto(top/total)
            root.update()
            assert widget.winfo_ismapped(),f'{theme}: target is not mapped'
            assert viewport.winfo_rooty()<=widget.winfo_rooty(),f'{theme}: target above viewport'
            assert widget.winfo_rooty()+widget.winfo_height()<=viewport.winfo_rooty()+viewport.winfo_height(),f'{theme}: target below viewport'
        TextLabel(frame,theme,size=20,weight='Bold',fg=p['text']).pack(anchor='w',pady=(0,12))
        bar=tk.Frame(frame,bg=p['bg']);bar.pack(fill='x')
        calls=[]
        button=Button(bar,'Şimdi indir',lambda:calls.append('click'),palette=p,primary=True)
        button.pack(side='left',padx=(0,8))
        for kind,label in (('secondary','Kuyruğa ekle'),('soft','Değiştir'),('ghost','İptal'),('danger_solid','Dosyaları sil')):
            Button(bar,label,palette=p,kind=kind).pack(side='left',padx=4)
        boolean=tk.BooleanVar(root,False)
        switch=Switch(bar,variable=boolean,palette=p);switch.pack(side='left',padx=8)
        check=CheckBox(bar,'Seç',variable=boolean,palette=p);check.pack(side='left')
        row=tk.Frame(frame,bg=p['bg']);row.pack(fill='x',pady=12)
        mode=tk.StringVar(root,'light')
        segment=SegmentedControl(row,{'light':'Açık','dark':'Koyu','system':'Sistem'},mode,palette=p)
        segment.pack(side='left')
        choice=tk.StringVar(root,'1080p')
        select=Select(row,{'1080p':'1080p','720p':'720p','MP3':'Yalnız ses'},choice,palette=p,width=180)
        select.pack(side='left',padx=12)
        radio=RadioCard(row,'1080p',choice,text='1080p',description='Kalite seçimi',palette=p)
        radio.pack(side='left')
        path=tk.StringVar(root,'temporary-profile/downloads')
        FormRow(frame,'Klasör',path,p,command=lambda:calls.append('folder')).pack(fill='x',pady=6)
        inputs=tk.Frame(frame,bg=p['bg']);inputs.pack(fill='x',pady=6)
        entry=TextInput(inputs,palette=p,placeholder='Bağlantı girin',width=300);entry.pack(side='left')
        unit=TextInput(inputs,palette=p,unit='KB/sn',width=240);unit.pack(side='left',padx=12)
        multi=TextInput(frame,palette=p,multiline=True,placeholder='Her satıra bir bağlantı',height=64)
        multi.pack(fill='x',pady=6)
        chips=ChipInput(frame,['zip','mp4'],palette=p);chips.pack(fill='x',pady=6)
        indicators=tk.Frame(frame,bg=p['bg']);indicators.pack(fill='x',pady=6)
        for state in ('İndiriliyor','Tamamlandı','Duraklatıldı','Kuyrukta','Hata'):
            StatusBadge(indicators,state,palette=p,width=120).pack(side='left',padx=4)
        FileTile(indicators,'MP4','video',p).pack(side='left',padx=8)
        bar_value=ProgressBar(frame,palette=p,value=.38);bar_value.pack(fill='x',pady=6)
        charts=tk.Frame(frame,bg=p['bg']);charts.pack(fill='x',pady=6)
        ring=ProgressRing(charts,palette=p,value=.38);ring.pack(side='left')
        spinner=ProgressRing(charts,palette=p,value=None,size=64,stroke=5);spinner.pack(side='left',padx=8)
        graph=SpeedChart(charts,palette=p,points=[(0,1e6),(1,2e6),(2,1.5e6),(3,3e6)],average=1.8e6,width=380,height=128)
        graph.pack(side='left',padx=12)
        spark=Sparkline(charts,palette=p,points=[(0,1),(1,3),(2,2)],width=70,height=30);spark.pack(side='left')
        Summary(charts,'Aktif',tk.StringVar(root,'2'),p).pack(side='left',padx=12)
        parts=PartMap(frame,palette=p,rows=[('Görüntü','itag 399',[1,.8,.2,0]),('Ses','itag 251',[1,.5,0])],height=80)
        parts.pack(fill='x',pady=4)
        events=[]
        timeline=SectionTimeline(frame,palette=p,duration=120,start=10,end=80,command=lambda a,b:events.append((a,b)))
        timeline.pack(fill='x')
        root.update();root.focus_force();button.focus_set();root.update()
        assert button.focused
        button.event_generate('<Return>');root.update();assert calls==['click']
        button.event_generate('<ButtonPress-1>',x=10,y=10);root.update();assert button.pressed and not button.focused
        button.event_generate('<ButtonRelease-1>',x=-10,y=-10);root.update();assert calls==['click'] and not button.pressed
        # After mouse focus leaves and Tab returns, the keyboard ring must return.
        switch.focus_set();root.update();button.focus_set();root.update();assert button.focused
        button.configure(state='disabled');button.invoke();assert calls==['click']
        assert int(button.cget('takefocus'))==0;button.configure(state='normal')
        # A no-op refresh must reuse the same rendered PhotoImage.
        image_id=str(button._surface);button.draw();assert str(button._surface)==image_id
        switch.invoke();assert boolean.get();check.invoke();assert not boolean.get()
        boolean.set(True);assert switch.variable.get() and check.variable.get()
        segment.move(1);assert mode.get()=='dark'
        select.step(1);assert choice.get()=='720p'
        radio.invoke();assert choice.get()=='1080p'
        select.configure(state='disabled');select.step(1);assert choice.get()=='1080p';select.configure(state='normal')
        entry.variable.set('https://example.invalid/file');entry.set_error('Geçersiz bağlantı');root.update()
        wait_for(entry.error_label.winfo_ismapped,f'{theme}: inline error label is not mapped')
        assert entry.error_label.winfo_ismapped();entry.set_error('')
        multi.variable.set('first\nsecond');assert multi.entry.get('1.0','end-1c')=='first\nsecond'
        multi.entry.insert('end','\nthird');root.update();assert multi.variable.get().endswith('third')
        chips.input.variable.set('.mkv');chips.add_from_entry();assert chips.values==['zip','mp4','mkv']
        chips.remove('mp4');assert chips.values==['zip','mkv']
        timeline.set_range(20,90);timeline.choose_handle('end');timeline.nudge(-1)
        assert events[-1]==(20,89)
        reveal(timeline)
        # Acquire the test top-level before dispatching a key. Desktop activation
        # can change while the earlier form checks process native window events.
        root.focus_force();timeline.focus_set()
        wait_for(lambda:root.focus_get() is timeline,f'{theme}: timeline did not receive keyboard focus')
        assert root.focus_get() is timeline,f'{theme}: keyboard focus is {root.focus_get()}'
        timeline.event_generate('<Left>');root.update()
        assert timeline.end==88 and events[-1]==(20,88)
        try:timeline.set_range(90,20);raise AssertionError('Invalid range accepted')
        except ValueError:pass
        actions=[];menu=PopupMenu(root,p)
        menu.add_item('Disabled',lambda:actions.append('wrong'),disabled=True)
        menu.add_item('Run',lambda:actions.append('run'))
        menu.add_separator();menu.add_item('More',submenu=lambda child:child.add_item('Child',lambda:actions.append('child')))
        menu.popup(root.winfo_screenwidth()-2,root.winfo_screenheight()-2);root.update()
        assert menu.active==1 and menu.winfo_rootx()+menu.winfo_width()<=root.winfo_screenwidth()
        menu.activate(0);assert actions==[]
        menu.activate(1);root.update();assert actions==['run'] and not menu.winfo_exists()
        menu=PopupMenu(root,p);menu.add_item('More',submenu=lambda child:child.add_item('Child',lambda:actions.append('child')))
        menu.popup(50,50);root.update()
        assert menu.child_menu is None
        menu.event_generate('<Right>');root.update();assert menu.child_menu.winfo_exists()
        menu.child_menu.activate(0);root.update();assert actions[-1]=='child' and not menu.winfo_exists()
        dialog=MessageDialog(root,'Hata','İşlem tamamlanamadı',p,technical='Synthetic HTTP error')
        dialog.add_action('retry','Tekrar dene','primary');dialog.show();root.update()
        dialog.toggle_details();root.update();assert dialog.details.winfo_ismapped()
        dialog.toggle_details();dialog.actions['retry'].invoke();assert dialog.result=='retry'
        # Popup closure must restore a pre-existing modal grab.
        modal=MessageDialog(root,'Karar','Geçici test',p);modal.add_action('ok','Tamam');modal.show();root.update()
        menu=PopupMenu(modal,p);menu.add_item('Item');menu.popup(100,100);root.update();menu.close();root.update()
        assert root.grab_current() is modal;modal.finish('ok')
        host=tk.Toplevel(root);host.geometry('900x500');host.configure(bg=p['bg'])
        listing=tk.Frame(host,bg=p['bg']);listing.pack(side='left',fill='both',expand=True)
        root.update();old_width=listing.winfo_width()
        drawer=Drawer(host,p,title='Ayrıntı');drawer.open(before=listing);root.update()
        assert drawer.winfo_ismapped() and listing.winfo_width()<old_width
        assert listing.winfo_rootx()+listing.winfo_width()<=drawer.winfo_rootx()
        drawer.close();root.update();assert not drawer.winfo_manager() and listing.winfo_width()==old_width
        host.destroy()
        manager=ToastManager(root,p)
        for i in range(4):manager.show('Bildirim',f'Test {i}')
        root.update();assert len(manager.toasts)==3
        toast=manager.toasts[-1];toast.pause();assert toast._timer is None and toast._remaining>0
        toast.resume();assert toast._timer is not None
        with patch.object(root,'state',return_value='iconic'):
            notify=[];manager.windows_notify=lambda a,b:notify.append((a,b))
            assert manager.show('Title','Text') is None and notify==[('Title','Text')]
        manager.close();root.update();assert not manager.toasts
        tip=Tooltip(button,'Yeni indirme',p);tip.show();root.update();tip.hide()
        # Freeze just the fixture spinner for a stable screenshot; no runtime setting changes.
        spinner.set(.5);root.update()
        # Capture both scroll positions while a synthetic topmost window fully
        # covers the fixture. The owner renders the requested window directly.
        for suffix,at_top in (('',True),('-timeline',False)):
            if at_top:viewport.yview_moveto(0);root.update()
            else:reveal(timeline)
            cover=tk.Toplevel(root);cover.overrideredirect(True);cover.configure(bg='#ff00ff')
            cover.geometry(f'{root.winfo_width()}x{root.winfo_height()}+{root.winfo_rootx()}+{root.winfo_rooty()}')
            cover.attributes('-topmost',True);cover.lift();root.update()
            try:preview=capture_client(root)
            finally:cover.destroy();root.update()
            assert preview.size==(root.winfo_width(),root.winfo_height()),preview.size
            actual_bg=preview.getpixel((preview.width-10,10));actual_accent=preview.getpixel((4,4))
            assert actual_bg==ImageColor.getrgb(p['bg']),(theme,suffix,'background',actual_bg,p['bg'])
            assert actual_accent==ImageColor.getrgb(p['accent']),(theme,suffix,'accent',actual_accent,p['accent'])
            preview.save(Path('build')/f'phase1-components-{theme}{suffix}.png')
        trace_before=len(boolean.trace_info());assert trace_before==2
        marker.destroy();gallery.destroy();root.update();assert len(boolean.trace_info())==0
        assert spinner._timer is None
        assert not errors,errors
    root.destroy()
    print('Four native component palettes: keyboard/mouse, disabled state, forms, menus, modal grabs, timers, indicators and screenshots: OK')


if __name__=='__main__':main()
