"""Pixel and geometry alignment regressions for shared controls; native Tk, never runs during discovery.

Each check pins a defect seen in 0.5.0 previews: ink-top text placement (labels
and menu rows at different heights per word), forms whose inputs moved with the
label width, clipped last letters, a × between title and description, footer
buttons on the window edge and centred dropdown values.
"""


def main():
    import tkinter as tk
    from types import SimpleNamespace
    import ui_surface
    from theme_catalog import palette
    from theme_widgets import Button
    from ui_surface import register_fonts,font,TextLabel
    from ui_controls import Select
    from ui_dialog import field
    from ui_overlays import PopupMenu,MessageDialog
    from atlas_view import number
    root=tk.Tk();root.geometry('900x600+20+20');register_fonts();errors=[]
    root.report_callback_exception=lambda *args:errors.append(args)
    drawn={}
    original=ui_surface.photo
    def capture(image,master):
        drawn[master]=image.convert('RGB');return original(image,master)
    ui_surface.photo=capture

    def ink(image,box):
        """Rows/columns inside box that differ clearly from the box's left-middle fill."""
        left,top,right,bottom=box;fill=image.getpixel((left,(top+bottom)//2))
        def far(x,y):return sum(abs(a-b) for a,b in zip(image.getpixel((x,y)),fill))>150
        rows=[y for y in range(top,bottom) if any(far(x,y) for x in range(left,right))]
        cols=[x for x in range(left,right) if any(far(x,y) for y in range(top,bottom))]
        return rows,cols

    cap=-font(13).getbbox('H',anchor='ls')[1]
    try:
        for mode in ('light','dark'):
            p=palette('atlas_'+mode);root.configure(bg=p['bg'])
            frame=tk.Frame(root,bg=p['bg']);frame.pack(fill='both',expand=True)
            # 1. Button labels share one baseline whatever their letters ('İ', capitals) and sit centred.
            #    Words without descenders, so the lowest ink row is the baseline.
            for kind in ('secondary','primary'):
                baselines={}
                for text in ('Devam','Duraklat','İndir','Kaldır','Önizle','Tümü'):
                    button=Button(frame,text,palette=p,kind=kind,width=120);button.pack();root.update()
                    image=drawn[button];w,h=image.size
                    rows,_=ink(image,(8,3,w-8,h-3));baselines[text]=max(rows)
                    centre=max(rows)-cap/2
                    assert abs(centre-h/2)<=1.5,(mode,kind,text,'label not vertically centred',centre,h/2)
                assert len(set(baselines.values()))==1,(mode,kind,'button labels on different baselines',baselines)
            # 2. Menu rows: same baseline for every label.
            menu=PopupMenu(root,p)
            for text in ('Devam et','Duraklat','İndirme hızı','Sıfırdan indir','SHA-256 kontrolü'):menu.add_item(text,lambda:None)
            root.update();baselines={}
            for entry in menu.items:
                item=entry['button'];item._draw_signature=None;item.draw();image=drawn[item];w,h=image.size
                rows,_=ink(image,(8,2,w-100,h-2));baselines[item.text.strip()]=max(rows)
            assert len(set(baselines.values()))==1,(mode,'menu labels on different baselines',baselines)
            menu.destroy()
            # 3. Labels are wide enough for their last letter.
            for text,size,weight in (('Yalnız bir bölümü indir',13,'SemiBold'),('~29,30 KB · seçilen bölüm ~2,44 KB',12,'Regular'),('Tamamlanan',13,'SemiBold')):
                item=TextLabel(frame,text,size=size,weight=weight,fg=p['text']);item.pack();root.update()
                image=drawn[item];_,cols=ink(image,(0,0,image.width,image.height))
                assert max(cols)<image.width-1,(mode,text,'last letter clipped',max(cols),image.width)
            # 4. Form rows: label and input share x; actions sit on the input's row at its height.
            for child in frame.winfo_children():child.destroy()  # measure on-screen, not below the window
            card=tk.Frame(frame,bg=p['card']);card.pack(fill='x',padx=20)
            first=field(card,'Kayıt klasörü',tk.StringVar(root,'C:/İndirilenler'),p,actions=[('Klasör seç',lambda:None)])
            second=field(card,'Arşiv çıktı klasörü · boş = dosyanın yanı',tk.StringVar(root,''),p)
            root.update()
            assert first.winfo_rootx()==second.winfo_rootx(),(mode,'inputs start at different x')
            caption=first.master.master.pack_slaves()[0]
            assert caption.winfo_rootx()==first.winfo_rootx(),(mode,'label and input not aligned')
            action=first.buttons[0]
            assert action.winfo_rooty()==first.winfo_rooty() and action.winfo_height()==first.winfo_height(),(mode,'action button off the input row')
            # 5. Dropdown values are left-aligned like inputs.
            select=Select(frame,{'tr':'Türkçe (1,5)','en':'English (1.5)'},palette=p,width=260);select.pack();root.update()
            image=drawn[select];_,cols=ink(image,(4,4,image.width-30,image.height-4))
            assert min(cols)<=18,(mode,'dropdown value is not left-aligned',min(cols))
            frame.destroy()
            # 6. Dialog shell: × on the title row, body in the title column, footer 24 px from the edge.
            dialog=MessageDialog(root,'Dosyalar silinsin mi?','Geçici test dosyaları',p,description='İki dosya',tone='error')
            dialog.add_action('delete','Dosyaları sil','danger_solid');dialog.add_action('cancel','Vazgeç','ghost');dialog.show();root.update()
            close=dialog.header.pack_slaves()[0];title=dialog.heading.pack_slaves()[0]
            assert title.winfo_rooty()<=close.winfo_rooty()+close.winfo_height()//2<=dialog.heading.winfo_rooty()+dialog.heading.winfo_height(),(mode,'× not on the heading')
            assert abs(dialog.body.winfo_rootx()-title.winfo_rootx())<=1,(mode,'message body not in the title column')
            last=dialog.actions['delete']
            gap=dialog.winfo_rootx()+dialog.winfo_width()-(last.winfo_rootx()+last.winfo_width())
            assert gap==24,(mode,'footer button not 24 px from the edge',gap)
            dialog.finish(None)
        # 7. Display numbers: decimal comma and 'KB/sn' exactly once.
        app=SimpleNamespace(settings={'language':'tr'})
        for raw,shown in (('48.83 KB/s','48,83 KB/sn'),('12,06 KB/sn','12,06 KB/sn'),('976.56 KB','976,56 KB'),('0 KB/s','0 KB/sn')):
            assert number(app,raw)==shown,(raw,number(app,raw))
        assert number(SimpleNamespace(settings={'language':'en'}),'48.83 KB/s')=='48.83 KB/s'
        assert not errors,errors
        print('Alignment: shared baselines, centred labels, unclipped text, form rows, dialog edges and number formats: OK')
    finally:
        ui_surface.photo=original;root.destroy()


if __name__=='__main__':main()
