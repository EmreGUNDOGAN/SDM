import json
import os
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox
import ttkbootstrap as tb
from utils import clean_filename, format_bytes, get_unique_filepath


def foreground(window):
    window.deiconify()
    window.lift()
    window.attributes('-topmost',True)
    window.after(500,lambda:window.attributes('-topmost',False) if window.winfo_exists() else None)
    window.focus_force()


class CapturePrompt(tb.Toplevel):
    def __init__(self,parent,request,decision):
        super().__init__(parent)
        self.parent=parent;self.request=request;self.decision=decision
        self.title('SDM · Yeni indirme');self.geometry('650x350');self.minsize(580,330)
        self.protocol('WM_DELETE_WINDOW',lambda:self.choose('cancel'))
        frame=tb.Frame(self,padding=24);frame.pack(fill='both',expand=True)
        video=request['kind']=='video'
        name=clean_filename(request.get('filename') or 'Video')
        if video:name+= '.mp3' if request.get('audio') else '.mkv'
        self.name=tk.StringVar(value=name)
        self.folder=tk.StringVar(value=parent.settings['download_dir'])
        tb.Label(frame,text='İndirmeyi nasıl başlatalım?',font=('Segoe UI',18,'bold')).pack(anchor='w',pady=(0,16))
        tb.Label(frame,text='Dosya adı').pack(anchor='w');tb.Entry(frame,textvariable=self.name).pack(fill='x',pady=(5,10))
        group=tb.Frame(frame);group.pack(fill='x')
        tb.Entry(group,textvariable=self.folder).pack(side='left',fill='x',expand=True)
        tb.Button(group,text='Gözat',bootstyle='secondary-outline',command=self.browse).pack(side='right',padx=(8,0))
        quality=('MP3' if request.get('audio') else f'{request.get("height")}p · Video + ses') if video else 'Dosya'
        size=format_bytes(request.get('filesize',0)) if request.get('filesize') else 'Boyut henüz bilinmiyor'
        tb.Label(frame,text=f'{quality}   ·   {size}'+(' (tahmini)' if video else '')).pack(anchor='w',pady=15)
        actions=tb.Frame(frame);actions.pack(fill='x',side='bottom')
        self.buttons={}
        for label,choice,style in [('Şimdi indir','start','primary'),('Kuyruğa ekle','queue','secondary-outline'),('İptal et','cancel','secondary-outline')]:
            button=tb.Button(actions,text=label,bootstyle=style,command=lambda c=choice:self.choose(c))
            button.pack(side='left',padx=(0,9),ipady=5);self.buttons[choice]=button
        if not video:
            tb.Button(actions,text='Tarayıcıda indir',bootstyle='secondary-link',command=lambda:self.choose('browser')).pack(side='right')
        foreground(self)

    def browse(self):
        folder=filedialog.askdirectory(parent=self,initialdir=self.folder.get())
        if folder:self.folder.set(folder)

    def choose(self,action):
        if action in ('start','queue'):
            try:
                filename=clean_filename(self.name.get())
                dest=get_unique_filepath(self.folder.get(),filename)
                did=self.parent.add_download_from_dialog(self.request['url'],filename,str(dest),
                    is_video=self.request['kind']=='video',auto_start=action=='start',
                    video_quality='Yalnızca Ses (MP3)' if self.request.get('audio') else 'En İyi',
                    selected_height=self.request.get('height'),from_browser=action=='start')
                if did is None:action='cancel'
            except Exception as error:
                messagebox.showerror('İndirme eklenemedi',str(error),parent=self);return
        self.decision(self.request['ticket'],action)
        self.destroy()


class CompletionDialog(tb.Toplevel):
    def __init__(self,parent,record):
        super().__init__(parent);self.parent=parent;self.record=record;self.title('SDM · İndirme tamamlandı');self.geometry('610x335')
        content=tb.Frame(self,padding=24);content.pack(fill='both',expand=True)
        tb.Label(content,text='Dosyan hazır',font=('Segoe UI',20,'bold')).pack(anchor='w')
        tb.Label(content,text=record['filename'],wraplength=455,font=('Segoe UI',12,'bold')).pack(anchor='w',pady=(18,6))
        tb.Label(content,text=format_bytes(record['filesize'])).pack(anchor='w')
        buttons=tb.Frame(content);buttons.pack(fill='x',pady=22)
        for label,target in [('Aç',record['filepath']),('Klasörü göster',str(Path(record['filepath']).parent))]:
            tb.Button(buttons,text=label,command=lambda p=target:self.open(p)).pack(side='left',padx=(0,10))
        tb.Button(buttons,text='Kapat',bootstyle='secondary-outline',command=self.destroy).pack(side='right')
        self.scan_button=tb.Button(buttons,text='Virüs tarat',bootstyle='secondary-outline',command=self.scan)
        self.scan_button.pack(side='left')
        self.scan_status=tk.StringVar(value='Tarama yalnızca Virüs tarat’a basınca başlar.')
        tb.Label(content,textvariable=self.scan_status,wraplength=550).pack(anchor='w')
        foreground(self)

    def scan(self):
        self.scan_button.configure(state='disabled');self.scan_status.set('Kaspersky ile taranıyor…')
        def work():
            try:
                from antivirus import scan_file
                result,report=scan_file(self.record['filepath'])
            except Exception as error:result=str(error)
            self.parent.post_ui(lambda:self.scan_done(result) if self.winfo_exists() else None)
        threading.Thread(target=work,daemon=True).start()

    def scan_done(self,result):self.scan_status.set(result);self.scan_button.configure(state='normal')

    def open(self,path):
        if Path(path).exists():os.startfile(path)
        else:messagebox.showwarning('Dosya bulunamadı','Dosya taşınmış veya silinmiş olabilir.',parent=self)


class BatchDialog(tb.Toplevel):
    def __init__(self,parent,initial=''):
        super().__init__(parent);self.parent=parent;self.title('SDM · Yeni indirme');self.geometry('680x550')
        frame=tb.Frame(self,padding=22);frame.pack(fill='both',expand=True)
        tb.Label(frame,text='Bağlantı ekle',font=('Segoe UI',20,'bold')).pack(anchor='w')
        tb.Label(frame,text='Bir veya birden fazla bağlantıyı ayrı satırlara yapıştır.').pack(anchor='w',pady=10)
        self.urls=tk.Text(frame,height=5,background=parent.palette['panel'],foreground=parent.palette['text'],insertbackground=parent.palette['text'],relief='flat',font=('Segoe UI',11))
        self.urls.pack(fill='x');self.urls.insert('1.0',initial)
        controls=tb.Frame(frame);controls.pack(fill='x',pady=10)
        self.video=tk.BooleanVar(value=False);tb.Checkbutton(controls,text='Video / ses',variable=self.video).pack(side='left')
        self.audio=tk.BooleanVar(value=False);tb.Checkbutton(controls,text='Yalnızca MP3',variable=self.audio).pack(side='left',padx=15)
        self.quality=tk.StringVar(value='En İyi')
        self.combo=tb.Combobox(controls,textvariable=self.quality,values=['En İyi','1080p','720p','480p'],state='readonly',width=18)
        self.combo.pack(side='right')
        self.status=tk.StringVar(value='');tb.Label(frame,textvariable=self.status,wraplength=620).pack(anchor='w',pady=6)
        tb.Button(frame,text='Video kalitelerini / listeyi incele',bootstyle='secondary-outline',command=self.inspect).pack(anchor='w')
        self.list=tb.Treeview(frame,columns=('title',),show='headings',selectmode='extended',height=5)
        self.list.heading('title',text='Video listesi · İndirmek istediklerini seç');self.list.pack(fill='both',expand=True,pady=10)
        self.entries={};self.heights={}
        buttons=tb.Frame(frame);buttons.pack(fill='x')
        for label,immediate in [('Şimdi indir',True),('Kuyruğa ekle',False)]:
            tb.Button(buttons,text=label,command=lambda now=immediate:self.submit(now)).pack(side='left',padx=(0,10))
        tb.Button(buttons,text='İptal',bootstyle='secondary-outline',command=self.destroy).pack(side='right')

    def inspect(self):
        urls=self.urls.get('1.0','end').strip().splitlines()
        if len(urls)!=1:return self.status.set('Liste incelemek için tek bir video veya oynatma listesi bağlantısı gir.')
        self.status.set('Bilgiler alınıyor…')
        def work():
            try:
                from video_downloader import fetch_video_formats,tool_options
                import yt_dlp
                with yt_dlp.YoutubeDL({'quiet':True,'extract_flat':'in_playlist','skip_download':True,'playlistend':100,**tool_options()}) as ydl:
                    info=ydl.extract_info(urls[0],download=False)
                entries=info.get('entries') or []
                formats=None if entries else fetch_video_formats(urls[0])
                self.parent.post_ui(lambda:self.inspected(entries,formats) if self.winfo_exists() else None)
            except Exception:
                self.parent.post_ui(lambda:self.status.set('Bilgiler alınamadı. Bağlantıyı ve site erişimini kontrol et.') if self.winfo_exists() else None)
        threading.Thread(target=work,daemon=True).start()

    def inspected(self,entries,formats):
        self.video.set(True);self.entries={};self.list.delete(*self.list.get_children())
        if entries:
            for entry in entries:
                url=entry.get('webpage_url') or entry.get('url')
                if url and not url.startswith('http') and entry.get('id'):url='https://www.youtube.com/watch?v='+entry['id']
                if url:
                    item=self.list.insert('','end',values=(entry.get('title','Video'),));self.entries[item]=(url,entry.get('title','Video'))
            self.list.selection_set(self.list.get_children())
            self.status.set('En fazla 100 video listelendi. İndirmek istediklerini seç.')
        else:
            self.heights={}
            labels=[]
            for quality in formats['qualities']:
                size=' · ~'+format_bytes(quality['filesize']) if quality['filesize'] else ''
                label=f'{quality["height"]}p · {quality["extension"]}'+size
                self.heights[label]=quality['height'];labels.append(label)
            self.combo.configure(values=labels)
            if labels:self.quality.set(labels[0])
            self.status.set(formats['title'])

    def submit(self,immediate):
        from utils import is_valid_url,extract_filename_from_url
        from video_downloader import is_video_site
        entries=[self.entries[item] for item in self.list.selection()] if self.entries else [(url.strip(),'') for url in self.urls.get('1.0','end').splitlines() if url.strip()]
        if not entries or any(not is_valid_url(url) for url,_ in entries):
            return messagebox.showerror('Bağlantı gerekli','Geçerli http/https bağlantıları girin.',parent=self)
        for url,title in entries:
            video=self.video.get() or is_video_site(url) or self.audio.get()
            filename=clean_filename(title or ('Video.mp3' if self.audio.get() else 'Video.mkv')) if video else extract_filename_from_url(url)
            if video and not Path(filename).suffix:filename+='.mp3' if self.audio.get() else '.mkv'
            dest=get_unique_filepath(self.parent.settings['download_dir'],filename)
            self.parent.add_download_from_dialog(url,filename,str(dest),is_video=video,
                video_quality='Yalnızca Ses (MP3)' if self.audio.get() else self.quality.get() if not self.heights else 'En İyi',
                selected_height=self.heights.get(self.quality.get()),auto_start=immediate)
        self.destroy()
