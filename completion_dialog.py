"""A06 completion actions, opt-out preference and explicit antivirus scan."""
import os
import threading
import tkinter as tk
from pathlib import Path
from ui_dialog import AppWindow,AutoCard,label,action
from ui_indicators import FileTile,Summary
from ui_controls import CheckBox
from theme_widgets import Button
from utils import format_bytes,format_speed,save_settings
from atlas_view import file_kind,number


class CompletionDialog(AppWindow):
    def __init__(self,parent,record):
        super().__init__(parent,'İndirme tamamlandı',560,440);self.record=record
        card=AutoCard(self.body,self.p)
        FileTile(card.content,Path(record['filename']).suffix.lstrip('.') or 'FILE',file_kind(record),self.p,size=54).pack(side='left',padx=(0,16))
        label(card.content,record['filename'],palette=self.p,size=15,weight='SemiBold').pack(anchor='w')
        history=getattr(parent,'speed_history',{}).get(record['id'])
        row=tk.Frame(self.body,bg=self.p['dialog']);row.pack(fill='x',padx=24,pady=(0,16))
        for title,value in (('Boyut',number(parent,format_bytes(record['filesize']))),('Süre',f'{history.active_seconds:.0f} sn' if history and history.active_seconds else '—'),('Ortalama hız',number(parent,format_speed(history.average)) if history and history.active_seconds else '—')):
            Summary(row,title,tk.StringVar(self,value),self.p).pack(side='left',fill='x',expand=True)
        row=tk.Frame(self.body,bg=self.p['dialog']);row.pack(fill='x',padx=24,pady=(0,16))
        media=Path(record['filename']).suffix.lower() in ('.mp4','.mkv','.webm','.avi','.mp3','.m4a','.wav','.flac')
        Button(row,'Oynat' if media else 'Aç',lambda:self.open(record['filepath']),palette=self.p,primary=True).pack(side='left',fill='x',expand=True,padx=(0,8))
        Button(row,'Klasörde göster',lambda:self.open(str(Path(record['filepath']).parent)),palette=self.p).pack(side='left',fill='x',expand=True)
        scan=AutoCard(self.body,self.p);self.scan_status=tk.StringVar(self,'Henüz taranmadı · tarama yalnız sen başlatınca yapılır.')
        self.scan_button=Button(scan.content,'Virüs tarat',self.scan,palette=self.p,kind='soft');self.scan_button.pack(side='right')
        label(scan.content,variable=self.scan_status,palette=self.p,size=12,muted=True).pack(side='left')
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

    def scan_done(self,result):self.scan_status.set(result);self.scan_button.configure(state='normal')

    def open(self,path):
        if Path(path).exists():os.startfile(path)
        else:
            from ui_messages import show_error
            show_error(self,'Dosya bulunamadı','Dosya taşınmış veya silinmiş olabilir.')
