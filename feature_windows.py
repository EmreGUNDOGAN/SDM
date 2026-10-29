"""A14–A16 themed UI; measurement and tool workers stay in their existing APIs."""
from pathlib import Path
import time
import tkinter as tk
import ttkbootstrap as tb
from ui_dialog import AppWindow,AutoCard,label,action,field
from ui_controls import SegmentedControl,RadioCard,TextInput,Select
from ui_indicators import SpeedChart,ProgressRing,ProgressBar,Sparkline,Summary
from theme_widgets import Button
from ui_surface import TextLabel
from utils import format_speed,format_bytes,format_eta,save_settings
from atlas_view import number


class SpeedGraph(AppWindow):
    def __init__(self,parent,did):
        record=parent.db.get_download(did)
        super().__init__(parent,'Hız grafiği',760,440,record['filename'] if record else 'Gerçek aktarım ölçümleri')
        self.did=did;self.span=tk.StringVar(self,'300')
        # A16: the span choice sits on the file-name line, right-aligned.
        line=tk.Frame(self.header,bg=self.p['dialog']);line.pack(fill='x',pady=(6,0))
        # Re-packed into a later sibling, the label must be raised above it.
        self.description_label.pack_forget();self.description_label.pack(in_=line,side='left');tk.Misc.tkraise(self.description_label,line)
        SegmentedControl(self.header,{'60':'1 dk','300':'5 dk','all':'Tümü'},self.span,palette=self.p).pack(in_=line,side='right')
        stats=tk.Frame(self.body,bg=self.p['dialog']);stats.pack(fill='x',padx=24,pady=(0,16))
        self.stats={}
        for key,title in (('now','Şimdi'),('average','Ortalama'),('peak','En yüksek'),('active','Aktif süre')):
            self.stats[key]=tk.StringVar(self,'—');Summary(stats,title,self.stats[key],self.p).pack(side='left',fill='x',expand=True)
        self.chart=SpeedChart(self.body,self.p,width=700,height=220,formatter=lambda text:number(parent,text));self.chart.pack(fill='both',expand=True,padx=24)
        self.canvas=self.chart
        label(self.actionbar,'Anlık hız · kesikli çizgi: gerçek aktarım ortalaması',palette=self.p,size=12,muted=True).pack(side='left')
        self.tick()

    def tick(self):
        history=self.parent.speed_history.get(self.did);points=tuple(history.points) if history else ()
        if points and self.span.get()!='all':points=tuple((t,v) for t,v in points if t>=points[-1][0]-int(self.span.get()))
        self.chart.set(points,history.average if history else None)
        for key,value in dict(now=format_speed(points[-1][1]) if points else '—',average=format_speed(history.average) if history else '—',peak=format_speed(max((v for _,v in points),default=0)) if points else '—',active=f'{history.active_seconds:.0f} sn' if history else '—').items():self.stats[key].set(number(self.parent,value))
        self.later(1000,self.tick)


class MiniHUD(tb.Toplevel):
    def __init__(self,parent):
        super().__init__(parent);self.parent=parent;self.withdraw();self.overrideredirect(True);self.attributes('-topmost',True);self.attributes('-alpha',.94)
        self.p=dict(parent.palette,bg=parent.palette['hud'],card=parent.palette['hud'],text=parent.palette['toast_text'],text_2=parent.palette['toast_text'],muted=parent.palette['toast_muted'],accent=parent.palette['hud_accent'])
        # The HUD stays dark in light mode; light-mode control fills made its
        # white button labels unreadable ('Tümünü duraklat' as a blank box).
        from PIL import ImageColor
        def tint(amount):
            return '#'+''.join(f'{round(a*(1-amount)+b*amount):02x}' for a,b in zip(ImageColor.getrgb(self.p['hud']),ImageColor.getrgb(self.p['toast_text'])))
        self.p.update(subtle=tint(.1),control=tint(.06),accent_soft=tint(.18),input_border=tint(.2),track=tint(.14))
        self.configure(bg=self.p['hud']);self._timer=None;self._drag=None;self.points=[]
        head=tk.Frame(self,bg=self.p['hud']);head.pack(fill='x',padx=16,pady=(16,10))
        self.ring=ProgressRing(head,self.p,size=48,stroke=5,value=0);self.ring.pack(side='left',padx=(0,14))
        info=tk.Frame(head,bg=self.p['hud']);info.pack(side='left',fill='x',expand=True)
        self.speed=label(info,'0 KB/sn',palette=self.p,size=20,weight='Bold');self.speed.pack(anchor='w')
        self.status=label(info,'Aktif indirme yok',palette=self.p,size=12,muted=True);self.status.pack(anchor='w')
        self.spark=Sparkline(head,self.p,width=80,height=24);self.spark.pack(side='right')
        self.files=tk.Frame(self,bg=self.p['hud']);self.files.pack(fill='x',padx=16,pady=8)
        self.file_rows=[]
        for _ in range(3):
            row=tk.Frame(self.files,bg=self.p['hud'])  # packed by tick() only while a file is active
            text=label(row,'',palette=self.p,size=12);text.max_width=304;text.pack(fill='x')
            bar=ProgressBar(row,self.p,width=304,height=10,thickness=3,show_text=False);bar.pack(fill='x')
            self.file_rows.append((row,text,bar))
        self.more=label(self.files,'',palette=self.p,size=12,muted=True)
        foot=tk.Frame(self,bg=self.p['hud']);foot.pack(fill='x',padx=12,pady=(0,12))
        Button(foot,'Tümünü duraklat',self.pause_all,palette=self.p,kind='soft').pack(side='left')
        Button(foot,'SDM’yi aç',self.show_main,palette=self.p,quiet=True).pack(side='left',padx=4)
        Button(foot,'×',self.close,palette=self.p,kind='icon',width=30).pack(side='right')
        self.bind('<ButtonPress-1>',self.drag_start);self.bind('<B1-Motion>',self.drag_move);self.bind('<ButtonRelease-1>',self.drag_end)
        self.bind('<Destroy>',self.dispose,add='+');self.protocol('WM_DELETE_WINDOW',self.close)
        self.geometry('340x280');self.update_idletasks()
        position=parent.settings.get('hud_position',[])
        x,y=position if len(position)==2 else (self.winfo_screenwidth()-356,self.winfo_screenheight()-self.winfo_reqheight()-56)
        self.geometry(f'340x{self.winfo_reqheight()}+{max(0,min(x,self.winfo_screenwidth()-340))}+{max(0,y)}')
        self.deiconify();self.tick()

    def tick(self):
        app=self.parent
        records=[r for r in app.db.get_all_downloads() if r['status'] in ('İndiriliyor','Birleştiriliyor','Dönüştürülüyor')]
        speed=app.engine.get_total_speed()+sum(v.current_speed for v in app.video_tasks.values() if v.status=='İndiriliyor')
        self.points=(self.points+[(time.monotonic(),speed)])[-60:];self.spark.set(self.points)
        total=sum(r['filesize'] for r in records);received=sum(r['downloaded_bytes'] for r in records)
        known=bool(records) and all(r['filesize']>0 for r in records)
        self.ring.set(min(1,received/total) if known else None if records else 0)
        self.speed.configure(text=number(app,format_speed(speed)))
        eta=format_eta(max(0,total-received)/speed) if known and speed else 'Boyut bilinmiyor' if records and not known else '—'
        self.status.configure(text=f'{len(records)} aktif · {eta}' if records else 'Aktif indirme yok')
        for index,(row,text,bar) in enumerate(self.file_rows):
            if index<len(records):
                record=records[index];row.pack(fill='x',pady=3);text.configure(text=record['filename']);bar.set(min(1,record['downloaded_bytes']/record['filesize']) if record['filesize'] else None,record['status'])
            else:row.pack_forget()
        if len(records)>3:self.more.configure(text=f'+{len(records)-3} daha');self.more.pack(anchor='w')
        else:self.more.pack_forget()
        # Fit the shown rows; a fixed height left an empty block with no downloads.
        self.update_idletasks();height=self.winfo_reqheight()
        if self.winfo_ismapped() and height!=self.winfo_height():self.geometry(f'340x{height}')
        self._timer=self.after(1000,self.tick)

    def pause_all(self):
        for record in self.parent.db.get_all_downloads():
            if record['status'] in ('Bekliyor','İndiriliyor','Birleştiriliyor','Dönüştürülüyor'):self.parent.pause_download(record['id'])
    def show_main(self):self.parent.deiconify();self.parent.lift()
    def close(self):self.parent._mini_hud=None;self.destroy()
    def dispose(self,event):
        if event.widget is self and self._timer:self.after_cancel(self._timer);self._timer=None
    def drag_start(self,event):
        if not isinstance(event.widget,Button):self._drag=(event.x_root,event.y_root,self.winfo_x(),self.winfo_y())
    def drag_move(self,event):
        if self._drag:
            x,y,oldx,oldy=self._drag;self.geometry(f'+{max(0,min(oldx+event.x_root-x,self.winfo_screenwidth()-340))}+{max(0,min(oldy+event.y_root-y,self.winfo_screenheight()-self.winfo_height()))}')
    def drag_end(self,event):
        if self._drag and tuple(self._drag[2:])!=(self.winfo_x(),self.winfo_y()):self.parent.settings['hud_position']=[self.winfo_x(),self.winfo_y()];save_settings(self.parent.settings)
        self._drag=None


def build_tools(window,parent):
    """Create A14 fields while retaining ToolsDialog's cancellable workers."""
    window.cancel=__import__('threading').Event();window.busy=False
    window.mode=tk.StringVar(window,'Biçim dönüştürme');window.input=tk.StringVar(window,'');window.output=tk.StringVar(window,'')
    window.start=tk.StringVar(window,'00:00');window.end=tk.StringVar(window,'00:30');window.format=tk.StringVar(window,'mp4')
    side=tk.Frame(window,bg=window.p['side'],width=244);side.pack(side='left',fill='y',before=window.header);side.pack_propagate(False)
    label(side,'Araçlar',palette=window.p,size=18,weight='Bold').pack(anchor='w',padx=24,pady=24)
    window.mode_buttons={}
    for name,title,description in (('Biçim dönüştürme','Biçim dönüştür','MP4, MKV, MP3, M4A, WAV'),('Video / ses kesme','Video / ses kes','Bir aralığı ayrı dosya yap'),('Bağlantı kontrolü','Bağlantı kontrolü','Listedeki adresleri sına'),('Klasörü düzenleme','Klasörü düzenle','Dosyaları türe göre ayır'),('Altyazı indirme','Altyazı indir','Videonun altyazı dilleri')):
        button=RadioCard(side,name,window.mode,text=title,description=description,palette=window.p,width=220)
        button.pack(fill='x',padx=12,pady=4);window.mode_buttons[name]=button
    source=AutoCard(window.body,window.p);label(source.content,'1  Kaynak',palette=window.p,weight='SemiBold').pack(anchor='w')
    window.source_input=field(source.content,'Dosya / klasör / video bağlantısı',window.input,window.p,
                              actions=[('Dosya seç',window.browse_file),('Klasör seç',window.browse_folder)])
    output=AutoCard(window.body,window.p);label(output.content,'2  Çıktı',palette=window.p,weight='SemiBold').pack(anchor='w')
    options=tk.Frame(output.content,bg=window.p['card']);options.pack(fill='x',pady=12)
    window.format_host=options
    for fmt in ('mp4','mkv','mp3','m4a','wav'):
        RadioCard(options,fmt,window.format,text=fmt.upper(),description='Ses' if fmt in ('mp3','m4a','wav') else 'Video',palette=window.p,width=82).pack(side='left',expand=True,fill='x',padx=2)
    field(output.content,'Çıktı klasörü',window.output,window.p,actions=[('Klasör seç',window.browse_output)])
    window.cut_fields=tk.Frame(output.content,bg=window.p['card'])
    window.timeline_host=tk.Frame(window.cut_fields,bg=window.p['card']);window.timeline_host.pack(fill='x')
    window.timeline=None;window._probe_token=None;window._probe_revision=0;window._range_sync=False
    times=tk.Frame(window.cut_fields,bg=window.p['card']);times.pack(fill='x')
    field(times,'Başlangıç',window.start,window.p,width=120,side='left');field(times,'Bitiş',window.end,window.p,width=120,side='left')
    window.subtitle_host=tk.Frame(output.content,bg=window.p['card']);window.subtitle_host.pack(fill='x')
    window.description_label.max_width=900-244-48
    result=AutoCard(window.body,window.p);label(result.content,'3  Sonuç',palette=window.p,weight='SemiBold').pack(anchor='w')
    # Link check types into this list, so it needs an input's visible edge.
    window.list=tk.Text(result.content,height=6,bg=window.p['card'],fg=window.p['text'],insertbackground=window.p['text'],font=('Inter',-12),relief='flat',
                        highlightthickness=1,highlightbackground=window.p['input_border'],highlightcolor=window.p['accent'],padx=10,pady=8)
    window.progress=tb.Progressbar(result.content,maximum=100);window.progress.pack(fill='x',pady=12)
    window.status=tk.StringVar(window,'');label(result.content,variable=window.status,palette=window.p,size=12).pack(anchor='w')
    window.run_button=action(window.actionbar,'Dönüştür',window.run,window.p,'primary')
    # Durdur only means something while a job runs (A14).
    window.stop_button=action(window.actionbar,'Durdur',window.cancel.set,window.p,'danger_ghost');window.stop_button.configure(state='disabled')
    window.mode.trace_add('write',lambda *args:window.update_mode());window.update_mode()
    def source_changed(*args):
        window._probe_revision+=1;revision=window._probe_revision;source=window.input.get().strip()
        for child in window.subtitle_host.winfo_children():child.destroy()
        window.run_button.configure(command=window.run)
        if window.timeline:window.timeline.destroy();window.timeline=None
        if window._probe_token:
            window.after_cancel(window._probe_token);window._owned_timers.discard(window._probe_token)
        def probe():
            window._probe_token=None
            if not Path(source).is_file():return
            def work():
                try:
                    from file_tools import media_duration
                    duration=media_duration(source)
                except Exception:return
                def done():
                    if revision!=window._probe_revision or not duration:return
                    from ui_indicators import SectionTimeline
                    from video_section import parse_time
                    from section_fields_ui import SectionFields
                    def choose(start,end):
                        window._range_sync=True;window.start.set(SectionFields.clock(start));window.end.set(SectionFields.clock(end));window._range_sync=False
                    try:start=parse_time(window.start.get());end=min(duration,parse_time(window.end.get()))
                    except ValueError:start=0;end=min(duration,30)
                    window.timeline=SectionTimeline(window.timeline_host,palette=window.p,duration=duration,start=min(start,max(0,end-1)),end=end,command=choose)
                    window.timeline.pack(fill='x',pady=8)
                window.deliver(done)
            __import__('threading').Thread(target=work,daemon=True).start()
        window._probe_token=window.later(300,probe)
    def range_changed(*args):
        if window.timeline and not window._range_sync:
            from video_section import parse_time
            try:window.timeline.set_range(parse_time(window.start.get()),parse_time(window.end.get()))
            except ValueError:pass
    traces=[(variable,variable.trace_add('write',callback)) for variable,callback in ((window.input,source_changed),(window.mode,source_changed),(window.start,range_changed),(window.end,range_changed))]
    def dispose(event):
        if event.widget is window:
            for variable,token in traces:variable.trace_remove('write',token)
    window.bind('<Destroy>',dispose,add='+')
    window.protocol('WM_DELETE_WINDOW',window.close)
    from tkinterdnd2 import DND_FILES
    window.drop_target_register(DND_FILES);window.dnd_bind('<<Drop>>',lambda e:window.input.set(window.tk.splitlist(e.data)[0]))
