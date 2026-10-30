"""A06 completion actions, opt-out preference and explicit antivirus scan."""
import os
import threading
import tkinter as tk
from pathlib import Path
from ui_dialog import AppWindow,AutoCard,label,action
from ui_indicators import FileTile
from ui_controls import CheckBox
from ui_surface import TextLabel,surface,photo,icon,ellipsize
from ui_tokens import SIZES
from theme_widgets import Button
from utils import format_bytes,format_speed,save_settings
from atlas_view import file_kind,number


class CompletionDialog(AppWindow):
    def __init__(self,parent,record):
        pano=parent.palette.get('design')=='pano'
        super().__init__(parent,'İndirme tamamlandı',560,500 if pano else 440);self.record=record;p=self.p
        # A06 header: tile with a success mark, a green caption and the file name.
        top=self.title_label.master;self.title_label.pack_forget()
        if pano:
            self.minsize(560,500);top.pack_forget()
            self.header.pack_configure(padx=0,pady=(10,4))
            self.file_card=AutoCard(self.header,p,padding=16)
            self.file_card.pack_configure(padx=14,pady=0);top=self.file_card.content
        header_bg=p['card'] if pano else p['dialog']
        tile=FileTile(top,Path(record['filename']).suffix.lstrip('.') or 'FILE',file_kind(record),p,size=54);tile.pack(side='left',padx=(0,18),pady=(0,4))
        mark=tk.Canvas(top,width=22,height=22,bg=header_bg,highlightthickness=0)
        image=surface(22,22,header_bg,p['success'],header_bg,7);glyph=icon('check-small',14,p['on_accent']);image.paste(glyph,(4,4),glyph)
        mark.image=photo(image,mark);mark.create_image(0,0,image=mark.image,anchor='nw');mark.place(in_=tile,relx=1,rely=1,x=6,y=6,anchor='se')
        text=tk.Frame(top,bg=header_bg);text.pack(side='left',fill='x',expand=True)
        TextLabel(text,'İNDİRME TAMAMLANDI' if pano else 'İndirme tamamlandı',size=12,weight='SemiBold',fg=p['success_fg']).pack(anchor='w')
        if pano:
            filename=record['filename'];prefix=ellipsize(filename,380,14,'SemiBold')
            self.name_lines=[]
            if prefix!=filename:
                cut=len(prefix.removesuffix('…'))
                boundary=max(filename.rfind(' ',0,cut),filename.rfind('-',0,cut)+1,filename.rfind('_',0,cut)+1)
                if boundary>cut//2:cut=boundary
                names=(filename[:cut],filename[cut:].lstrip())
            else:names=(filename,)
            for value in names:
                name=label(text,value,palette=p,size=14,weight='SemiBold');name.max_width=380
                name.pack(anchor='w',pady=(2,0));self.name_lines.append(name)
        else:
            name=label(text,record['filename'],palette=p,size=16,weight='Bold');name.max_width=380;name.pack(anchor='w',pady=(2,0))
        history=getattr(parent,'speed_history',{}).get(record['id'])
        duration=f'{history.active_seconds:.0f} sn' if history and history.active_seconds else '—'
        if pano and history and history.active_seconds:
            hours,remaining=divmod(round(history.active_seconds),3600);minutes,seconds=divmod(remaining,60)
            duration=' '.join(part for part in (f'{hours} sa' if hours else '',f'{minutes} dk' if minutes else '',
                f'{seconds:02} sn' if hours or minutes else f'{seconds} sn') if part)
        # P06 has three separate cards; Atlas/Odak retain the shared hairline card.
        self.stat_cards=[]
        if pano:
            stats=tk.Frame(self.body,bg=p['dialog']);stats.pack(fill='x',padx=10,pady=(8,12))
        else:
            stats=AutoCard(self.body,p,padding=12);cells=stats.content
        for index,(title,value) in enumerate((('Boyut',number(parent,format_bytes(record['filesize']))),('Süre',duration),('Ortalama hız',number(parent,format_speed(history.average)) if history and history.active_seconds else '—'))):
            if pano:
                stats.columnconfigure(index,weight=1,uniform='completion')
                holder=tk.Frame(stats,bg=p['dialog']);holder.grid(row=0,column=index,sticky='nsew',padx=4)
                card=AutoCard(holder,p,padding=12);card.pack_configure(fill='both',expand=True,padx=0,pady=0)
                self.stat_cards.append(card);cell=card.content
                if title=='Ortalama hız':title='Ortalama'
            else:
                if index:tk.Frame(cells,bg=p['line'],width=1).pack(side='left',fill='y')
                cell=tk.Frame(cells,bg=p['card']);cell.pack(side='left',fill='x',expand=True,padx=(14 if index else 4,14))
            label(cell,title,palette=p,size=12,muted=True).pack(anchor='w')
            label(cell,value,palette=p,size=15,weight='Bold').pack(anchor='w',pady=(4,0))
        row=tk.Frame(self.body,bg=p['dialog']);row.pack(fill='x',padx=14 if pano else 24,pady=(0,12 if pano else 16))
        media=Path(record['filename']).suffix.lower() in ('.mp4','.mkv','.webm','.avi','.mp3','.m4a','.wav','.flac')
        for index,(text,glyph,command,kind) in enumerate(((('Oynat' if media else 'Aç'),'play' if media else 'file',lambda:self.open(record['filepath']),'primary'),
                                                           ('Klasörde göster','folder',lambda:self.open(str(Path(record['filepath']).parent)),'secondary'))):
            button=Button(row,text,command,palette=p,kind=kind,height=44);button.icon_name=glyph;button.centered=True;button.draw()
            button.pack(side='left',fill='x',expand=True,padx=(8 if index else 0,0))
        scan_bg=p['card'] if pano else p['subtle']
        scan=AutoCard(self.body,dict(p,card=scan_bg,line=scan_bg),padding=14)
        if pano:scan.pack_configure(padx=14,pady=(0,12))
        self.scan_button=Button(scan.content,'Virüs tarat',self.scan,palette=p,kind='secondary',height=SIZES['small_button']+2);self.scan_button.pack(side='right')
        shield=tk.Canvas(scan.content,width=32,height=32,bg=scan_bg,highlightthickness=0)
        image=surface(32,32,scan_bg,p['subtle'] if pano else p['card'],p['line'],8);glyph=icon('shield',16,p['text_2']);image.paste(glyph,(8,8),glyph)
        shield.image=photo(image,shield);shield.create_image(0,0,image=shield.image,anchor='nw');shield.pack(side='left',padx=(0,12))
        lines=tk.Frame(scan.content,bg=scan_bg);lines.pack(side='left',fill='x',expand=True)
        self.scan_status=tk.StringVar(self,'Henüz taranmadı')
        self.scan_title=TextLabel(lines,textvariable=self.scan_status,size=13,weight='SemiBold',fg=p['text']);self.scan_title.pack(anchor='w')
        self.scan_detail=TextLabel(lines,'Kaspersky ile tarama yalnız sen başlatınca yapılır.',size=12,fg=p['muted']);self.scan_detail.pack(anchor='w',pady=(2,0))
        # Scanner messages are long; both lines end before the button instead of running under it.
        lines.bind('<Configure>',lambda e:self.fit_scan(e.width))
        self.hide_next=tk.BooleanVar(self,False)
        CheckBox(self.actionbar,'Bu pencereyi bir daha gösterme',self.hide_next,palette=self.p,command=self.toggle_popup).pack(side='left')
        action(self.actionbar,'Kapat',self.close,self.p,'ghost')

    def toggle_popup(self):
        self.parent.settings['completion_popup']=not self.hide_next.get();save_settings(self.parent.settings)

    def scan(self):
        self.scan_button.configure(state='disabled');self.scan_status.set('Kaspersky ile taranıyor…')
        def work():
            try:
                from antivirus import scan_file
                result,_=scan_file(self.record['filepath'])
            except Exception as error:result=str(error)
            self.parent.post_ui(lambda:self.scan_done(result) if self.winfo_exists() else None)
        threading.Thread(target=work,daemon=True).start()

    def fit_scan(self,width):
        for line in (self.scan_title,self.scan_detail):line.max_width=width;line.draw()

    def scan_done(self,result):
        # First sentence is the verdict; the rest is the detail line.
        head,_,rest=result.partition('. ')
        self.scan_status.set(head+'.' if rest else head);self.scan_detail.configure(text=rest);self.scan_button.configure(state='normal')

    def open(self,path):
        if Path(path).exists():os.startfile(path)
        else:
            from ui_messages import show_error
            show_error(self,'Dosya bulunamadı','Dosya taşınmış veya silinmiş olabilir.')
