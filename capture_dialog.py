"""A04 browser decisions with live quality cards and validated section fields."""
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog
from ui_dialog import AppWindow,AutoCard,action,label,field
from ui_controls import RadioCard
from ui_indicators import FileTile
from theme_widgets import Button
from utils import clean_filename,format_bytes,get_unique_filepath
from atlas_view import domain


class CapturePrompt(AppWindow):
    def __init__(self,parent,request,decision):
        video=request['kind']=='video'
        super().__init__(parent,'İndirmeyi nasıl başlatalım?',720,800 if video else 450)
        self.request=dict(request);self.decision=decision;self.buttons={};self._done=False
        if request.get('audio'):self.request['audio_filesize']=request.get('audio_filesize') or request.get('filesize',0)
        self.name=tk.StringVar(self,clean_filename(request.get('filename') or 'Video'))
        if video:self.name.set(self.name.get()+('.mp3' if request.get('audio') else '.mkv'))
        self.folder=tk.StringVar(self,parent.settings['download_dir'])
        self.quality=tk.StringVar(self,'audio' if request.get('audio') else str(request.get('height') or 'best'))
        self.formats=[];self.duration=request.get('duration');self.estimate=tk.StringVar(self,'')
        summary=AutoCard(self.body,self.p);row=summary.content
        if video:
            from ui_thumbnail import Thumbnail
            self.thumbnail=Thumbnail(row,parent,self.p,width=208,height=117,source=request.get('thumbnail'));self.thumbnail.pack(side='left',padx=(0,16))
        else:FileTile(row,Path(self.name.get()).suffix.lstrip('.') or 'FILE',palette=self.p,size=64).pack(side='left',padx=(0,16))
        info=tk.Frame(row,bg=self.p['card']);info.pack(fill='x',expand=True)
        label(info,'Tarayıcıdan yakalandı · '+domain(request),palette=self.p,size=12,muted=True).pack(anchor='w')
        title=label(info,request.get('filename') or 'Video',palette=self.p,size=16,weight='SemiBold');title.max_width=340 if video else 460;title.pack(anchor='w',pady=8)
        label(info,variable=self.estimate,palette=self.p,size=12,muted=True).pack(anchor='w')
        self.quality_host=None;self.section_fields=None
        if video:
            quality=AutoCard(self.body,self.p);label(quality.content,'Kalite · Boyutlar tahminidir',palette=self.p,weight='SemiBold').pack(anchor='w',pady=(0,12))
            self.quality_host=tk.Frame(quality.content,bg=self.p['card']);self.quality_host.pack(fill='x')
            self.render_qualities()
            section=AutoCard(self.body,self.p)
            from video_section import SectionFields
            self.section_fields=SectionFields(section.content,duration=self.duration,palette=self.p,command=self.validate)
        save=AutoCard(self.body,self.p);label(save.content,'Kaydet',palette=self.p,weight='SemiBold').pack(anchor='w')
        self.name_input=field(save.content,'Dosya adı',self.name,self.p)
        field(save.content,'Klasör',self.folder,self.p)
        Button(save.content,'Değiştir',self.browse,palette=self.p,kind='soft').pack(anchor='e')
        self.buttons['start']=action(self.actionbar,'Şimdi indir',lambda:self.choose('start'),self.p,'primary')
        self.buttons['queue']=action(self.actionbar,'Kuyruğa ekle',lambda:self.choose('queue'),self.p)
        self.buttons['cancel']=action(self.actionbar,'İptal',lambda:self.choose('cancel'),self.p,'ghost')
        if not video:action(self.actionbar,'Tarayıcıda indir',lambda:self.choose('browser'),self.p,'link','left')
        self.protocol('WM_DELETE_WINDOW',lambda:self.choose('cancel'))
        self.bind('<Escape>',lambda e:self.choose('cancel'))
        self._quality_trace=self.quality.trace_add('write',self.quality_changed)
        self._name_trace=self.name.trace_add('write',lambda *args:self.validate())
        self.bind('<Destroy>',self.cleanup,add='+');self.validate();self.update_estimate()
        if video:
            def inspect():
                try:
                    from dialog_inspection import inspect_url
                    result=inspect_url(request['url'],True)
                    parent.post_ui(lambda:self.got_formats(result) if self.winfo_exists() else None)
                except Exception:pass # The captured quality remains a valid fallback.
            threading.Thread(target=inspect,daemon=True).start()

    def render_qualities(self):
        for child in self.quality_host.winfo_children():child.destroy()
        values=[(str(q['height']),str(q['height'])+'p',q.get('filesize',0)) for q in self.formats]
        current=str(self.request.get('height') or 'best')
        if not values:values=[(current,'En iyi' if current=='best' else current+'p',self.request.get('filesize',0))]
        values.append(('audio','MP3',self.request.get('audio_filesize',0)))
        self.quality_cards=[]
        for index,(key,text,size) in enumerate(values):
            button=RadioCard(self.quality_host,key,self.quality,text=text,description='~'+format_bytes(size) if size else 'Boyut bilinmiyor',palette=self.p,width=145)
            button.grid(row=index//4,column=index%4,sticky='ew',padx=3,pady=4);self.quality_cards.append(button)
        for column in range(4):self.quality_host.columnconfigure(column,weight=1)

    def got_formats(self,result):
        if result.get('kind')!='video':return
        self.formats=result['qualities'];self.duration=result.get('duration')
        self.thumbnail.set_source(result.get('thumbnail'))
        self.request['audio_filesize']=result.get('audio_filesize',0)
        if self.section_fields:self.section_fields.set_duration(self.duration)
        self.render_qualities();self.update_estimate()

    def quality_changed(self,*args):
        audio=self.quality.get()=='audio'
        name=self.name.get();stem=Path(name).stem if Path(name).suffix.lower() in ('.mkv','.mp3','.mp4','.webm') else name
        self.name.set(stem+('.mp3' if audio else '.mkv'));self.update_estimate()

    def update_estimate(self):
        size=self.request.get('filesize',0)
        if self.quality.get()=='audio':size=self.request.get('audio_filesize',0)
        else:size=next((q.get('filesize',0) for q in self.formats if str(q['height'])==self.quality.get()),size)
        self.selected_size=size
        text=('~' if self.request['kind']=='video' else '')+format_bytes(size) if size else 'Boyut bilinmiyor'
        try:
            section=self.section_fields.collect() if self.section_fields else None
            if section and self.duration and size:text+=' · seçilen bölüm ~'+format_bytes(size*(section['end']-section['start'])/self.duration)
        except ValueError:pass
        self.estimate.set(text)

    def validate(self):
        try:
            if not self.name.get().strip():raise ValueError('Dosya adı gerekli.')
            if self.section_fields:self.section_fields.collect()
            self.error.set('');valid=True
        except ValueError as error:self.error.set(str(error));valid=False
        for key in ('start','queue'):
            if key in self.buttons:self.buttons[key].configure(state='normal' if valid else 'disabled')
        if hasattr(self,'estimate'):self.update_estimate()
        return valid

    def browse(self):
        folder=filedialog.askdirectory(parent=self,initialdir=self.folder.get())
        if folder:self.folder.set(folder)

    def close(self):self.choose('cancel')

    def choose(self,action):
        if self._done:return
        if action in ('start','queue'):
            if not self.validate():return
            try:
                filename=clean_filename(self.name.get());dest=get_unique_filepath(self.folder.get(),filename)
                audio=self.quality.get()=='audio';height=int(self.quality.get()) if self.quality.get().isdigit() else self.request.get('height')
                did=self.parent.add_download_from_dialog(self.request['url'],filename,str(dest),
                    is_video=self.request['kind']=='video',auto_start=action=='start',video_quality='Yalnızca Ses (MP3)' if audio else 'En İyi',selected_height=height,
                    from_browser=action=='start',expected_size=0 if self.section_fields and self.section_fields.enabled.get() else self.selected_size,section=self.section_fields.collect() if self.section_fields else None)
                if did is None:action='cancel'
            except Exception as error:self.error.set(str(error));return
        self._done=True;self.decision(self.request['ticket'],action);self.destroy()

    def cleanup(self,event):
        if event.widget is self:
            self.quality.trace_remove('write',self._quality_trace);self.name.trace_remove('write',self._name_trace)
