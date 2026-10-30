"""A03 per-link cards with automatic, bounded, disposable inspection workers."""
import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog
from ui_dialog import AppWindow,AutoCard,action,label,field
from theme_widgets import Button
from ui_controls import TextInput,CheckBox,Select,SegmentedControl,Switch
from file_tools import AUDIO_BITRATES
from ui_indicators import FileTile
from ui_surface import TextLabel
from utils import is_valid_url,clean_filename,extract_filename_from_url,format_bytes
from video_downloader import is_video_site
from atlas_view import domain,file_kind,number


class BatchDialog(AppWindow):
    def __init__(self,parent,initial=''):
        super().__init__(parent,'Yeni indirme',760,820,'Bağlantıları yapıştır; SDM her birini inceleyip boyutunu ve kalitelerini gösterir.')
        self.items={};self.inspection_attempted=set();self._results={};self._requested=set();self.inspecting=False;self._debounce=None
        self._closed=threading.Event();self._jobs=queue.Queue();self._workers=[]
        self.folder=tk.StringVar(self,parent.settings['download_dir'])
        self.queue_name=tk.StringVar(self,parent.settings['queues'][0]['name'])
        self.video=tk.BooleanVar(self,False);self.audio=tk.BooleanVar(self,False);self.quality=tk.StringVar(self,'En İyi')
        self.links=tk.StringVar(self,initial);self.url_input=TextInput(self.body,variable=self.links,palette=self.p,multiline=True,height=130)
        self.url_input.pack(fill='x',padx=24,pady=(0,10));self.urls=self.url_input.entry
        Button(self.body,'Panodan yapıştır',self.paste,palette=self.p,kind='soft').pack(anchor='e',padx=24,pady=(0,16))
        head=tk.Frame(self.body,bg=self.p['dialog']);head.pack(fill='x',padx=24,pady=(0,12))
        self.status=tk.StringVar(self,'Bulunanlar · 0 bağlantı');label(head,variable=self.status,palette=self.p,weight='SemiBold').pack(side='left')
        Button(head,'Tümünü seç',self.select_all,palette=self.p,kind='link').pack(side='right')
        self.found=tk.Frame(self.body,bg=self.p['dialog']);self.found.pack(fill='x')
        save=AutoCard(self.body,self.p)
        field(save.content,'Klasör',self.folder,self.p,actions=[('Değiştir',self.browse)])
        label(save.content,'Kuyruk',palette=self.p,muted=True).pack(anchor='w',pady=(8,4))
        Select(save.content,{q['name']:q['name'] for q in parent.settings['queues']},self.queue_name,palette=self.p,width=260).pack(fill='x')
        # Applies to every link saved as MP3; same options as the YouTube Music button.
        self.bitrate=tk.StringVar(self,'192');self.album=tk.BooleanVar(self,False)
        audio_row=tk.Frame(save.content,bg=self.p['card']);audio_row.pack(fill='x',pady=(12,0))
        label(audio_row,'MP3 kalitesi',palette=self.p,muted=True).pack(side='left',padx=(0,10))
        Select(audio_row,{str(rate):f'{rate} kb/sn' for rate in AUDIO_BITRATES},self.bitrate,palette=self.p,width=150).pack(side='left')
        Switch(audio_row,self.album,palette=self.p).pack(side='right')
        label(audio_row,'Sanatçı / Albüm klasörü',palette=self.p).pack(side='right',padx=(0,8))
        self.total=tk.StringVar(self,'0 öğe seçili');label(self.actionbar,variable=self.total,palette=self.p,size=12).pack(side='left')
        self.buttons={}
        self.buttons['start']=action(self.actionbar,'Şimdi indir',lambda:self.submit(True),self.p,'primary')
        self.buttons['queue']=action(self.actionbar,'Kuyruğa ekle',lambda:self.submit(False),self.p)
        action(self.actionbar,'İptal',self.close,self.p,'ghost')
        self._links_trace=self.links.trace_add('write',self.schedule_inspection)
        self.bind('<Destroy>',self.cancel_inspection,add='+')
        for _ in range(3):
            worker=threading.Thread(target=self.work,daemon=True);worker.start();self._workers.append(worker)
        from tkinterdnd2 import DND_TEXT,DND_FILES
        self.urls.drop_target_register(DND_TEXT,DND_FILES)
        self.urls.dnd_bind('<<Drop>>',self.drop)
        self.update_total()
        self.schedule_inspection()

    def paste(self):
        try:value=self.clipboard_get()
        except tk.TclError:return
        self.links.set(self.links.get().rstrip()+'\n'+value if self.links.get().strip() else value)

    def drop(self,event):
        values=self.tk.splitlist(event.data);links=[]
        for value in values:
            if is_valid_url(value):links.append(value)
            elif Path(value).suffix.lower() in ('.url','.txt') and Path(value).is_file() and Path(value).stat().st_size<1024*1024:
                links.extend(line.removeprefix('URL=').strip() for line in Path(value).read_text(encoding='utf-8-sig',errors='replace').splitlines() if is_valid_url(line.removeprefix('URL=').strip()))
        if links:self.links.set(self.links.get().rstrip()+'\n'+'\n'.join(links))
        return event.action

    def browse(self):
        folder=filedialog.askdirectory(parent=self,initialdir=self.folder.get())
        if folder:self.folder.set(folder)

    def schedule_inspection(self,*args):
        if self._debounce:
            self.after_cancel(self._debounce);self._owned_timers.discard(self._debounce)
        self._debounce=self.later(250,self.inspect)

    def inspect(self):
        self._debounce=None
        lines=list(dict.fromkeys(line.strip() for line in self.urls.get('1.0','end').splitlines() if line.strip()))
        valid=[url for url in lines if is_valid_url(url)]
        self.url_input.set_error('Geçersiz bağlantılar: '+', '.join(str(i+1) for i,line in enumerate(lines) if not is_valid_url(line)) if len(valid)!=len(lines) else '')
        for url in list(self.items):
            item=self.items[url]
            if url not in valid and item.get('source') not in valid:item['card'].destroy();del self.items[url]
        for url in valid:
            if url not in self.items:
                self.make_item(url)
                if url in self._results:self.deliver(url,self._results[url])
                elif url not in self._requested:self._requested.add(url);self._jobs.put((url,self.video.get() or self.audio.get()))
        self.update_total()

    def make_item(self,url,title='',source=None):
        card=AutoCard(self.found,self.p,padding=12);row=card.content
        selected=tk.BooleanVar(self,True);item=dict(url=url,source=source,card=card,selected=selected,title=title or extract_filename_from_url(url),kind='pending',size=0,mode=tk.StringVar(self,'video'),quality=tk.StringVar(self,'best'),formats=[])
        self.items[url]=item
        CheckBox(row,variable=selected,palette=self.p,command=self.update_total).pack(side='left',anchor='n',padx=(0,12),pady=8)
        item['tile']=FileTile(row,Path(item['title']).suffix.lstrip('.') or 'URL',palette=self.p);item['tile'].pack(side='left',anchor='n',padx=(0,12),pady=8)
        content=tk.Frame(row,bg=self.p['card']);content.pack(side='left',fill='x',expand=True)
        item['name_label']=label(content,item['title'],palette=self.p,weight='SemiBold');item['name_label'].max_width=460;item['name_label'].pack(anchor='w')
        item['info']=label(content,'İnceleniyor…',palette=self.p,size=12,muted=True);item['info'].pack(anchor='w',pady=(4,0))
        item['options']=tk.Frame(content,bg=self.p['card'])
        item['section_host']=content
        item['selected_trace']=selected.trace_add('write',lambda *args:self.update_total())
        card.bind('<Destroy>',lambda e:selected.trace_remove('write',item['selected_trace']) if e.widget is card else None,add='+')
        return item

    def work(self):
        while not self._closed.is_set():
            try:url,force=self._jobs.get(timeout=.2)
            except queue.Empty:continue
            if self._closed.is_set():return
            try:
                from dialog_inspection import inspect_url
                result=inspect_url(url,force)
            except Exception as error:result=dict(kind='error',error=str(error))
            if not self._closed.is_set():self.parent.post_ui(lambda u=url,r=result:self.deliver(u,r))

    def deliver(self,url,result):
        if self._closed.is_set() or url not in self.items:return
        self.inspection_attempted.add(url);self._results[url]=result;item=self.items[url]
        if result['kind']=='playlist':
            item['card'].destroy();del self.items[url]
            for child,title in result['entries']:
                if child not in self.items:
                    self.make_item(child,title,source=url)
                    if child in self._results:self.deliver(child,self._results[child])
                    elif child not in self._requested:self._requested.add(child);self._jobs.put((child,True))
            self.update_total();return
        item.update(result);item['resolved_url']=item.get('url',url);item['url']=url
        if result['kind']=='file':
            item['title']=result['filename'];item['size']=result.get('filesize',0)
            item['info'].configure(text=('Devam ettirilebilir · en çok '+str(self.parent.settings['default_connections'])+' bağlantı' if result.get('supports_ranges') else 'Devam desteği doğrulanmadı')+' · '+(number(self.parent,format_bytes(item['size'])) if item['size'] else 'Boyut bilinmiyor'))
        elif result['kind']=='video':
            from ui_thumbnail import Thumbnail
            item['tile'].destroy();item['tile']=Thumbnail(item['card'].content,self.parent,self.p,source=result.get('thumbnail'))
            item['tile'].pack(side='left',anchor='n',before=item['section_host'],padx=(0,12))
            item['title']=result['title'];item['formats']=result['qualities'];choices={str(q['height']):str(q['height'])+'p' for q in result['qualities']}
            choices=choices or {'best':'En iyi'}
            preferred='1080' if '1080' in choices else next(iter(choices));item['quality'].set(preferred)
            item['options'].pack(fill='x',pady=(6,0))
            SegmentedControl(item['options'],{'video':'Video','audio':'MP3'},item['mode'],palette=self.p,command=lambda *args:self.item_changed(item)).pack(side='left')
            Select(item['options'],choices,item['quality'],palette=self.p,width=120,command=lambda *args:self.item_changed(item)).pack(side='left',padx=6)
            Button(item['options'],'Bölüm seç',lambda:self.show_section(item),palette=self.p,kind='link').pack(side='left')
            self.item_changed(item)
        else:item['info'].configure(text='İncelenemedi · yine de indirilebilir')
        item['name_label'].configure(text=item['title'])
        from utils import get_category_by_extension
        item['tile'].extension=Path(item['title']).suffix.lstrip('.').upper()[:4] or 'VID'
        item['tile'].kind=file_kind(dict(filename=item['title'],category=get_category_by_extension(item['title'])))
        item['tile'].draw();self.update_total()

    def item_changed(self,item):
        if item['mode'].get()=='audio':item['size']=item.get('audio_filesize',0)
        else:item['size']=next((q['filesize'] for q in item['formats'] if str(q['height'])==item['quality'].get()),0)
        item['info'].configure(text=('~'+number(self.parent,format_bytes(item['size'])) if item['size'] else 'Boyut bilinmiyor')+' · '+domain(item))
        self.update_total()

    def show_section(self,item):
        if 'section' not in item:
            from video_section import SectionFields
            item['section']=SectionFields(item['section_host'],duration=item.get('duration'),palette=self.p,command=self.update_total)
        item['section'].enabled.set(not item['section'].enabled.get())

    def select_all(self):
        for item in self.items.values():item['selected'].set(True)

    def update_total(self):
        selected=[item for item in self.items.values() if item['selected'].get()]
        pending=sum(item['kind']=='pending' for item in self.items.values())
        self.inspecting=bool(pending);self.status.set(f'Bulunanlar · {len(self.items)} bağlantı')
        self.total.set(f'{len(selected)} öğe seçili · ~{number(self.parent,format_bytes(sum(item.get("size",0) for item in selected)))} · {pending} inceleniyor')
        valid=bool(selected) and not pending
        for item in selected:
            if 'section' in item:
                try:item['section'].collect()
                except ValueError:valid=False
        for button in self.buttons.values():button.configure(state='normal' if valid else 'disabled')

    def preview_size(self):return sum(item.get('size',0) for item in self.items.values() if item['selected'].get())

    def submit(self,immediate):
        selected=[item for item in self.items.values() if item['selected'].get()]
        if not selected:return self.error.set('Geçerli bir bağlantı seç.')
        if any(item['kind']=='pending' for item in selected):return self.error.set('Bağlantılar inceleniyor…')
        try:
            for item in selected:
                video=item['kind']=='video' or is_video_site(item['url']) or self.video.get() or self.audio.get()
                audio=item['mode'].get()=='audio' or self.audio.get()
                name=clean_filename(item['title'])
                if video:
                    extension='.mp3' if audio else '.mkv'
                    name=str(Path(name).with_suffix(extension)) if Path(name).suffix.lower() in ('.mkv','.mp4','.mp3','.webm','.m4a') else name+extension
                section=item['section'].collect() if 'section' in item else None
                did=self.parent.add_download_from_dialog(item['url'],name,str(Path(self.folder.get())/name),is_video=video,
                    video_quality='Yalnızca Ses (MP3)' if audio else 'En İyi',selected_height=int(item['quality'].get()) if item['quality'].get().isdigit() else None,
                    auto_start=immediate,expected_size=0 if section else item.get('size',0),section=section,
                    audio=dict(bitrate=int(self.bitrate.get()),album=self.album.get()) if video and audio else None)
                if did is not None:self.parent.db.set_queue(did,self.queue_name.get())
            self.close()
        except Exception as error:self.error.set(str(error))

    def cancel_inspection(self,event):
        if event.widget is self:
            self._closed.set()
            try:self.links.trace_remove('write',self._links_trace)
            except tk.TclError:pass
