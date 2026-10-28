"""Explicit native Tk integration/visual fixture; never runs during discovery."""


def main():
    import tkinter as tk
    from pathlib import Path
    from unittest.mock import patch
    from PIL import ImageGrab,ImageColor
    from theme_catalog import THEMES,palette
    from theme_widgets import Button,Panel
    from ui_surface import register_fonts,TextLabel
    from ui_controls import (Switch,CheckBox,SegmentedControl,RadioCard,Select,
                             TextInput,ChipInput,FormRow)
    from ui_indicators import (StatusBadge,FileTile,ProgressBar,ProgressRing,
                               SpeedChart,Sparkline,PartMap,Summary,SectionTimeline)
    from ui_overlays import PopupMenu,MessageDialog,Drawer,ToastManager,Tooltip
    root=tk.Tk();root.geometry('1080x840+20+20');root.title('SDM 0.5.0 · Shared components')
    register_fonts();errors=[]
    root.report_callback_exception=lambda *args:errors.append(args)
    Path('build').mkdir(exist_ok=True)
    for theme in THEMES:
        p=palette(theme);root.configure(bg=p['bg'])
        frame=tk.Frame(root,bg=p['bg']);frame.pack(fill='both',expand=True,padx=20,pady=16)
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
        assert entry.error_label.winfo_ismapped();entry.set_error('')
        multi.variable.set('first\nsecond');assert multi.entry.get('1.0','end-1c')=='first\nsecond'
        multi.entry.insert('end','\nthird');root.update();assert multi.variable.get().endswith('third')
        chips.input.variable.set('.mkv');chips.add_from_entry();assert chips.values==['zip','mp4','mkv']
        chips.remove('mp4');assert chips.values==['zip','mkv']
        timeline.set_range(20,90);timeline.choose_handle('end');timeline.nudge(-1)
        assert events[-1]==(20,89)
        timeline.focus_set();root.update();timeline.event_generate('<Left>');root.update();assert timeline.end==88
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
        menu.popup(50,50);root.update();assert menu.child_menu.winfo_exists()
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
        # Capture this HWND, not the desktop rectangle behind an occluded window.
        preview=ImageGrab.grab(window=root.winfo_id())
        assert preview.size==(root.winfo_width(),root.winfo_height()),preview.size
        assert preview.getpixel((preview.width-10,10))==ImageColor.getrgb(p['bg'])
        preview.save(Path('build')/f'phase1-components-{theme}.png')
        trace_before=len(boolean.trace_info());assert trace_before==2
        frame.destroy();root.update();assert len(boolean.trace_info())==0
        assert spinner._timer is None
        assert not errors,errors
    root.destroy()
    print('Four native component palettes: keyboard/mouse, disabled state, forms, menus, modal grabs, timers, indicators and screenshots: OK')


if __name__=='__main__':main()
