"""A14–A16 themed UI; measurement and tool workers stay in their existing APIs."""
from pathlib import Path
import time
import tkinter as tk
import ttkbootstrap as tb
from ui_dialog import AppWindow,AutoCard,label,action,field,step,caption
from ui_controls import SegmentedControl,RadioCard,ToolCard,TextInput,Select
from ui_indicators import SpeedChart,ProgressRing,ProgressBar,Sparkline,Summary,FileTile
from theme_widgets import Button
from ui_surface import TextLabel
from utils import format_speed,format_bytes,format_eta,save_settings,get_category_by_extension
from atlas_view import number,file_kind
from file_tools import AUDIO_BITRATES
from ui_tokens import SIZES,TEXT_SCALE,HUD_TEXT_SIZES,text_px,YORUNGE_MONO_FAMILY

# Tool list width follows the text size so descriptions are not cut.
SIDE=round(268*TEXT_SCALE)


class SpeedGraph(AppWindow):
    def __init__(self,parent,did):
        record=parent.db.get_download(did)
        super().__init__(parent,'Hız grafiği',760,440,record['filename'] if record else 'Gerçek aktarım ölçümleri',kicker='HIZ TELEMETRİSİ')
        orbit=self.p.get('design')=='yorunge';pano=self.p.get('design') in ('pano','yorunge')
        self.did=did;self.span=tk.StringVar(self,'300')
        # A16: the span choice sits on the file-name line, right-aligned.
        line=tk.Frame(self.header,bg=self.p['dialog']);line.pack(fill='x',pady=(6,0))
        if orbit:
            # F16: the file name is the heading; spans share the title row.
            line=self.title_label.master;self.title_label.configure(text=record['filename'] if record else 'Gerçek aktarım ölçümleri')
            self.title_label.max_width=520
        else:
            # Re-packed into a later sibling, the label must be raised above it.
            self.description_label.pack_forget();self.description_label.pack(in_=line,side='left');tk.Misc.tkraise(self.description_label,line)
        spans=SegmentedControl(self.header,{'60':'1 dk','300':'5 dk','all':'Tümü'},self.span,palette=self.p);spans.pack(in_=line,side='right',padx=(0,8) if orbit else 0)
        if pano and not orbit:
            line.bind('<Configure>',lambda event:(setattr(self.description_label,'max_width',max(1,event.width-spans.winfo_reqwidth()-12)),self.description_label.draw()),add='+')
        stats=tk.Frame(self.body,bg=self.p['dialog']);stats.pack(fill='x',padx=24,pady=(0,16))
        self.stats={};self.stat_cards=[]
        for key,title in (('now','Şimdi'),('average','Ortalama'),('peak','En yüksek'),('active','Aktif süre')):
            self.stats[key]=tk.StringVar(self,'—')
            if pano:
                holder=tk.Frame(stats,bg=self.p['dialog']);card=AutoCard(holder,self.p,padding=12);card.radius=0 if orbit else 18
                card.pack_configure(padx=0,pady=0,fill='both',expand=True);self.stat_cards.append(card)
                if orbit:
                    card.brackets=False;card.stripe=self.p[{'now':'accent','average':'violet','peak':'success','active':'warning'}[key]]
                    TextLabel(card.content,caption(title)[3:],size=10,fg=self.p['muted'],family=YORUNGE_MONO_FAMILY).pack(anchor='w')
                    TextLabel(card.content,textvariable=self.stats[key],size=16,weight='Bold',fg=self.p['text'],family=YORUNGE_MONO_FAMILY).pack(anchor='w',pady=(4,0))
                else:
                    label(card.content,title,palette=self.p,size=12,muted=True).pack(anchor='w')
                    label(card.content,variable=self.stats[key],palette=self.p,size=16,weight='Bold').pack(anchor='w',pady=(4,0))
            else:Summary(stats,title,self.stats[key],self.p).pack(side='left',fill='x',expand=True)
        if pano:
            def arrange(event):
                columns=2 if event.width<640 else 4
                for index in range(4):stats.columnconfigure(index,weight=1 if index<columns else 0,uniform='graph' if index<columns else '')
                for index,card in enumerate(self.stat_cards):
                    left=8*(index%columns)//columns;inset=8*(columns-1)//columns
                    card.master.grid(row=index//columns,column=index%columns,sticky='nsew',padx=(left,inset-left),pady=(0,8))
            stats.bind('<Configure>',arrange)
        chart_parent=self.body
        if pano:
            self.chart_card=AutoCard(self.body,self.p);self.chart_card.radius=0 if orbit else 22;chart_parent=self.chart_card.content
        self.chart=SpeedChart(chart_parent,self.p,width=700,height=220,formatter=lambda text:number(parent,text));self.chart.pack(fill='both',expand=True,padx=0 if pano else 24)
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
        size=lambda base:round(base*HUD_TEXT_SIZES.get(parent.settings.get('hud_text_size'),1.0))
        # P15: Pano's HUD is light tiles without a file list (approved: HUD stays simple).
        self.pano=parent.palette.get('design')=='pano';self.orbit=parent.palette.get('design')=='yorunge'
        if self.pano:self.build_pano(size)
        elif self.orbit:self.build_orbit(size)
        else:
            head=tk.Frame(self,bg=self.p['hud']);head.pack(fill='x',padx=16,pady=(16,10))
            self.ring=ProgressRing(head,self.p,size=48,stroke=5,value=0);self.ring.pack(side='left',padx=(0,14))
            info=tk.Frame(head,bg=self.p['hud']);info.pack(side='left',fill='x',expand=True)
            self.speed=label(info,'0 KB/sn',palette=self.p,size=size(20),weight='Bold');self.speed.pack(anchor='w')
            self.status=label(info,'Aktif indirme yok',palette=self.p,size=size(12),muted=True);self.status.pack(anchor='w')
            self.spark=Sparkline(head,self.p,width=80,height=24);self.spark.pack(side='right')
            self.files=tk.Frame(self,bg=self.p['hud']);self.files.pack(fill='x',padx=16,pady=8)
            self.file_rows=[]
            for _ in range(3):
                row=tk.Frame(self.files,bg=self.p['hud'])  # packed by tick() only while a file is active
                text=label(row,'',palette=self.p,size=size(12));text.max_width=304;text.pack(fill='x')
                bar=ProgressBar(row,self.p,width=304,height=10,thickness=3,show_text=False);bar.pack(fill='x')
                self.file_rows.append((row,text,bar))
            self.more=label(self.files,'',palette=self.p,size=size(12),muted=True)
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
        self.speed.configure(text=number(app,format_speed(speed)))
        eta=format_eta(max(0,total-received)/speed) if known and speed else 'Boyut bilinmiyor' if records and not known else '—'
        if self.pano or self.orbit:
            self.total_bar.set(min(1,received/total) if known else None if records else 0)
            self.percent.configure(text=f'{min(100,round(received/total*100))}%' if known else '—')
            self.eta.configure(text='Bilinmiyor' if records and not known else eta)
            self.count.configure(text=f'● {len(records)} AKTİF' if self.orbit else f'{len(records)} etkin')
            self.arrange_speed()
            return self.fit_and_repeat()
        self.ring.set(min(1,received/total) if known else None if records else 0)
        self.status.configure(text=f'{len(records)} aktif · {eta}' if records else 'Aktif indirme yok')
        for index,(row,text,bar) in enumerate(self.file_rows):
            if index<len(records):
                record=records[index];row.pack(fill='x',pady=3);text.configure(text=record['filename']);bar.set(min(1,record['downloaded_bytes']/record['filesize']) if record['filesize'] else None,record['status'])
            else:row.pack_forget()
        if len(records)>3:self.more.configure(text=f'+{len(records)-3} daha');self.more.pack(anchor='w')
        else:self.more.pack_forget()
        self.fit_and_repeat()

    def fit_and_repeat(self):
        # Fit the shown rows; a fixed height left an empty block with no downloads.
        self.update_idletasks()
        # F15's card sizes itself from its content only on a later Configure.
        if self.orbit:self.tiles[0].fit();self.update_idletasks()
        height=self.winfo_reqheight()
        if self.winfo_ismapped() and height!=self.winfo_height():self.geometry(f'340x{height}')
        self._timer=self.after(1000,self.tick)

    def fit_pano(self,event=None):
        height=self.winfo_reqheight()
        if self.winfo_ismapped() and height!=self.winfo_height():
            self.geometry(f'340x{height}+{self.winfo_x()}+{max(0,min(self.winfo_y(),self.winfo_screenheight()-height))}')

    def build_pano(self,size):
        p=self.p=dict(self.parent.palette,hud=self.parent.palette['bg']);self.configure(bg=p['bg'])
        self.attributes('-alpha',1.0)
        self.bind('<Configure>',self.round_pano,add='+')
        grid=tk.Frame(self,bg=p['bg']);grid.pack(fill='x',padx=10,pady=10);grid.columnconfigure((0,1),weight=1,uniform='hud')
        grid.bind('<Configure>',self.fit_pano)
        self.tiles=[]
        def tile(row,column,span=1):
            cell=tk.Frame(grid,bg=p['bg']);cell.grid(row=row,column=column,columnspan=span,sticky='nsew',padx=((0,4) if column==0 and span==1 else (4,0) if column==1 else 0),pady=(0,8))
            card=AutoCard(cell,p,padding=12);card.radius=16;card.pack_configure(padx=0,pady=0,fill='both',expand=True)
            self.tiles.append(card);return card.content
        top=tile(0,0,2);self.speed_host=top;top.columnconfigure(0,weight=1)
        info=tk.Frame(top,bg=p['card']);info.grid(row=0,column=0,sticky='w')
        label(info,'TOPLAM HIZ',palette=p,size=size(11),weight='SemiBold',muted=True).pack(anchor='w')
        self.speed=label(info,'0 KB/sn',palette=p,size=size(22),weight='Bold');self.speed.pack(anchor='w',pady=(2,0))
        self.spark=Sparkline(top,p,width=84,height=34);self.spark.grid(row=0,column=1,sticky='e',padx=(12,0))
        top.bind('<Configure>',lambda event:self.arrange_speed(),add='+')
        left=tile(1,0);label(left,'Toplam',palette=p,size=size(11),muted=True).pack(anchor='w')
        self.percent=label(left,'—',palette=p,size=size(17),weight='Bold');self.percent.pack(anchor='w',pady=(2,6))
        self.total_bar=ProgressBar(left,p,width=130,height=8,thickness=5,show_text=False);self.total_bar.pack(fill='x')
        right=tile(1,1);label(right,'Kalan',palette=p,size=size(11),muted=True).pack(anchor='w')
        self.eta=label(right,'—',palette=p,size=size(17),weight='Bold');self.eta.max_width=130;self.eta.pack(anchor='w',pady=(2,2))
        self.count=label(right,'Aktif indirme yok',palette=p,size=size(11),muted=True);self.count.max_width=130;self.count.pack(anchor='w')
        foot=tk.Frame(self,bg=p['bg']);foot.pack(fill='x',padx=10,pady=(0,10))
        Button(foot,'Tümünü duraklat',self.pause_all,palette=p,kind='primary').pack(side='left',fill='x',expand=True)
        Button(foot,'SDM’yi aç',self.show_main,palette=p,kind='secondary').pack(side='left',fill='x',expand=True,padx=6)
        Button(foot,'×',self.close,palette=p,kind='icon',width=34).pack(side='right')

    def build_orbit(self,size):
        """F15: one bracketed panel; speed with chart, 30 tiles, total and remaining."""
        p=self.p=dict(self.parent.palette,hud=self.parent.palette['bg']);self.configure(bg=p['bg'])
        def mono(parent,text,base,fg=None,weight='Regular'):
            return TextLabel(parent,text,size=size(base),weight=weight,fg=fg or p['muted'],family=YORUNGE_MONO_FAMILY)
        panel=AutoCard(self,p,padding=14);panel.pack_configure(padx=0,pady=0,fill='both',expand=True);self.tiles=[panel]
        # The card grows after its content; refit on either size change.
        body=panel.content;body.bind('<Configure>',self.fit_pano,add='+');panel.bind('<Configure>',self.fit_pano,add='+')
        head=tk.Frame(body,bg=p['card']);head.pack(fill='x')
        mono(head,'// SDM · CANLI',10).pack(side='left')
        self.count=mono(head,'● 0 AKTİF',10,p['success'],'SemiBold');self.count.pack(side='right')
        top=tk.Frame(body,bg=p['card']);top.pack(fill='x',pady=(10,8));self.speed_host=top;top.columnconfigure(0,weight=1)
        self.speed=mono(top,'0 KB/sn',22,p['text'],'Bold');self.speed.grid(row=0,column=0,sticky='w')
        self.spark=Sparkline(top,p,width=96,height=34);self.spark.grid(row=0,column=1,sticky='e',padx=(12,0))
        top.bind('<Configure>',lambda event:self.arrange_speed(),add='+')
        self.total_bar=ProgressBar(body,p,width=300,height=12,thickness=10,show_text=False,cells=30);self.total_bar.pack(fill='x')
        row=tk.Frame(body,bg=p['card']);row.pack(fill='x',pady=(8,12))
        mono(row,'TOPLAM ',11).pack(side='left');self.percent=mono(row,'—',11,p['text'],'Bold');self.percent.pack(side='left')
        self.eta=mono(row,'—',11,p['text'],'Bold');self.eta.pack(side='right');mono(row,'KALAN ',11).pack(side='right')
        foot=tk.Frame(body,bg=p['card']);foot.pack(fill='x')
        Button(foot,'Tümünü duraklat',self.pause_all,palette=p,kind='outline_accent').pack(side='left',fill='x',expand=True)
        Button(foot,'SDM’yi aç',self.show_main,palette=p,kind='secondary').pack(side='left',fill='x',expand=True,padx=6)
        Button(foot,'×',self.close,palette=p,kind='icon',width=34).pack(side='right')

    def arrange_speed(self):
        # Keep the actual speed and units readable at all HUD text sizes. A large
        # value moves the chart below it instead of squeezing either control.
        stacked=self.speed.winfo_reqwidth()+12+84>self.speed_host.winfo_width()
        self.spark.grid_configure(row=1 if stacked else 0,column=0 if stacked else 1,
            columnspan=2 if stacked else 1,padx=0 if stacked else (12,0),pady=(6,0) if stacked else 0)

    def round_pano(self,event):
        if event.widget is not self:return
        import sys
        if sys.platform!='win32':return
        size=(event.width,event.height)
        if size==getattr(self,'_region_size',None):return
        import ctypes
        from ctypes import wintypes
        user=ctypes.WinDLL('user32',use_last_error=True);gdi=ctypes.WinDLL('gdi32',use_last_error=True)
        gdi.CreateRoundRectRgn.argtypes=[ctypes.c_int]*6;gdi.CreateRoundRectRgn.restype=wintypes.HANDLE
        gdi.DeleteObject.argtypes=[wintypes.HANDLE];gdi.DeleteObject.restype=wintypes.BOOL
        user.SetWindowRgn.argtypes=[wintypes.HWND,wintypes.HANDLE,wintypes.BOOL];user.SetWindowRgn.restype=ctypes.c_int
        region=gdi.CreateRoundRectRgn(0,0,event.width+1,event.height+1,44,44)
        if not region:raise ctypes.WinError(ctypes.get_last_error())
        hwnd=int(self.tk.call('wm','frame',self._w),0)
        if not user.SetWindowRgn(hwnd,region,True):
            error=ctypes.get_last_error();gdi.DeleteObject(region);raise ctypes.WinError(error)
        # Successful SetWindowRgn transfers region ownership to Windows.
        self._region_size=size

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


TOOLS=(('Biçim dönüştürme','Biçim dönüştür','MP4, MKV, MP3, M4A, WAV',('MP3','program')),
       ('Video / ses kesme','Video / ses kes','Bir aralığı ayrı dosya yap',('CUT','video')),
       ('Bağlantı kontrolü','Bağlantı kontrolü','Listedeki adresleri sına',('URL','image')),
       ('Klasörü düzenleme','Klasörü düzenle','Dosyaları türe göre ayır',('DIR','archive')),
       ('Altyazı indirme','Altyazı indir','Videonun altyazı dillerini al',('CC','audio')))
MEDIA_TOOLS=('Biçim dönüştürme','Video / ses kesme')


def build_tools(window,parent):
    """Create A14 fields while retaining ToolsDialog's cancellable workers."""
    p=window.p;orbit=p.get('design')=='yorunge'
    # Yörünge F14 keeps Pano's P14 cards; it swaps step discs for '// CAPTION'.
    pano=p.get('design') in ('pano','yorunge');round_=22 if p.get('design')=='pano' else 0
    window.cancel=__import__('threading').Event();window.busy=False
    window.mode=tk.StringVar(window,'Biçim dönüştürme');window.input=tk.StringVar(window,'');window.output=tk.StringVar(window,'')
    window.start=tk.StringVar(window,'00:00');window.end=tk.StringVar(window,'00:30');window.format=tk.StringVar(window,'mp4')
    window.bitrate=tk.StringVar(window,'192');window.duration=None
    if pano:
        side=tk.Frame(window.body,bg=p['dialog']);side.pack(fill='x',padx=20,pady=(0,16))
        window.description_label.pack_forget()
        window.description_label=tk.Label(window.header,bg=p['dialog'],fg=p['muted'],font=('Inter',text_px(13)),justify='left',anchor='w',wraplength=852,padx=0,pady=0,bd=0)
        window.header.bind('<Configure>',lambda event:window.description_label.configure(wraplength=event.width),add='+')
    else:
        side=tk.Frame(window,bg=p['side'],width=SIDE);side.pack(side='left',fill='y',before=window.header);side.pack_propagate(False)
        label(side,'Araçlar',palette=p,size=18,weight='Bold').pack(anchor='w',padx=24,pady=24)
    window.mode_buttons={}
    for index,(name,title,description,tile) in enumerate(TOOLS):
        if pano:
            title=(('Dönüştür','Kes','Bağlantı','Klasör','Altyazı') if orbit else ('Dönüştür','Kes','Bağlantılar','Klasörler','Altyazı'))[index]
            description=('MP4, MKV, MP3,\nM4A, WAV','Aralığı ayrı\ndosya yap','Listedeki\nadresleri sına','Dosyaları türe\ngöre ayır','Video altyazı\ndillerini indir')[index]
        button=ToolCard(side,name,window.mode,tile,text=title,description=description,palette=p,width=160 if pano else SIDE-24,**({'height':132} if pano else {}))
        if orbit:button.number=index+1
        if not pano:button.pack(fill='x',padx=12,pady=2)
        window.mode_buttons[name]=button
    if pano:
        def arrange_tools(event):
            columns=5 if event.width>=800 else 3 if event.width>=650 else 2
            for index in range(5):side.columnconfigure(index,weight=1 if index<columns else 0,uniform='tools' if index<columns else '')
            for index,button in enumerate(window.mode_buttons.values()):button.grid(row=index//columns,column=index%columns,sticky='ew',padx=4,pady=4)
        side.bind('<Configure>',arrange_tools)
    # Steps lie on the window; only the source file and the result are cards (A14).
    def section(number,title):
        if pano and number in (1,3):
            outer=AutoCard(window.body,p);outer.radius=round_;frame=outer.content
            # F14: only the running-job panel is featured.
            if orbit and number==1:outer.brackets=False
        else:
            frame=tk.Frame(window.body,bg=p['dialog']);frame.pack(fill='x',padx=24,pady=(0,20))
        if orbit:
            frame.step=tk.Frame(frame,bg=frame.cget('bg'))
            frame.step.title=TextLabel(frame.step,'',size=10,fg=p['muted'],family=YORUNGE_MONO_FAMILY);frame.step.title.pack(anchor='w')
            frame.step.title.configure(text=caption(title))
        else:frame.step=step(frame,number,title,p)
        frame.step.pack(anchor='w',pady=(0,10));return frame
    source=section(1,'Kaynak')
    window.source_card=AutoCard(source,p,padding=0 if pano else 14);window.source_card.pack_forget()
    if pano:window.source_card.radius=0;window.source_card.p=dict(window.source_card.p,line=p['card'])
    card=window.source_card.content
    window.source_tile=FileTile(card,'FILE',palette=p,size=40);window.source_tile.pack(side='left')
    Button(card,'Değiştir',window.browse_file,palette=p,kind='soft',height=SIZES['small_button']).pack(side='right')
    text=tk.Frame(card,bg=p['card']);text.pack(side='left',fill='x',expand=True,padx=(12,8))
    window.source_name=label(text,palette=p,size=14,weight='SemiBold');window.source_name.max_width=420;window.source_name.pack(anchor='w')
    window.source_meta=label(text,palette=p,size=12,muted=True);window.source_meta.pack(anchor='w',pady=(2,0))
    window.source_input=field(source,'Dosya / klasör / video bağlantısı',window.input,p,
                              actions=[('Dosya seç',window.browse_file),('Klasör seç',window.browse_folder)])
    window.source_box=window.source_input.master.master
    hint='Dosya sürükleyip bırakabilir veya bir video bağlantısı yapıştırabilirsin.'
    if pano:
        window.source_hint=tk.Label(source,text=hint,bg=p['card'],fg=p['muted'],font=('Inter',text_px(12)),wraplength=800,justify='left',anchor='w',padx=0,pady=0,bd=0)
        source.bind('<Configure>',lambda event:window.source_hint.configure(wraplength=event.width),add='+')
        def fit_source(event):
            for item in (window.source_name,window.source_meta):item.max_width=event.width;item.draw()
        text.bind('<Configure>',fit_source)
    else:window.source_hint=label(source,hint,palette=p,size=12,muted=True)
    window.source_hint.pack(anchor='w',pady=(8,0))
    output=section(2,'Çıktı biçimi');window.output_step=output.step
    options_parent=output;settings_parent=output
    if pano:
        window.output_cards=tk.Frame(output,bg=p['dialog']);window.output_cards.pack(fill='x')
        format_holder=tk.Frame(window.output_cards,bg=p['dialog']);settings_holder=tk.Frame(window.output_cards,bg=p['dialog'])
        format_card=AutoCard(format_holder,p);format_card.radius=round_;format_card.pack_configure(padx=0,pady=0,fill='both',expand=True)
        settings_card=AutoCard(settings_holder,p);settings_card.radius=round_;settings_card.pack_configure(padx=0,pady=0,fill='both',expand=True)
        if orbit:format_card.brackets=settings_card.brackets=False
        options_parent=format_card.content;settings_parent=settings_card.content
        def arrange_output(event=None):
            media=window.mode.get() in MEDIA_TOOLS;wide=media and window.output_cards.winfo_width()>=760
            window.output_cards.columnconfigure(0,weight=3 if wide else 1);window.output_cards.columnconfigure(1,weight=2 if wide else 0)
            if media:format_holder.grid(row=0,column=0,sticky='nsew',padx=(0,8) if wide else 0,pady=(0,0 if wide else 12))
            else:format_holder.grid_remove()
            settings_holder.grid(row=0 if wide or not media else 1,column=1 if wide else 0,sticky='nsew',padx=(8,0) if wide else 0)
        window.arrange_pano_output=arrange_output;window.output_cards.bind('<Configure>',arrange_output)
    options=tk.Frame(options_parent,bg=options_parent.cget('bg'));options.pack(fill='x',pady=(0,12))
    window.format_host=options
    for index,fmt in enumerate(('mp4','mkv','mp3','m4a','wav')):
        RadioCard(options,fmt,window.format,text=fmt.upper(),description=('Kayıpsız' if pano else 'Kayıpsız ses') if fmt=='wav' else 'Ses' if fmt in ('mp3','m4a') else 'Video',
                  palette=p,width=82,align='center').pack(side='left',expand=True,fill='x',padx=(8 if index else 0,0))
    window.output_row=tk.Frame(settings_parent,bg=settings_parent.cget('bg'));window.output_row.pack(fill='x')
    window.quality_box=tk.Frame(window.output_row,bg=window.output_row.cget('bg'))
    label(window.quality_box,'Ses kalitesi',palette=p,muted=True).pack(side='left' if pano else 'top',anchor='w',pady=0 if pano else (0,6))
    Select(window.quality_box,{str(rate):f'{rate} kb/sn' for rate in AUDIO_BITRATES},window.bitrate,palette=p,
           width=180,height=SIZES['input']).pack(side='right' if pano else 'top',anchor='w')
    window.output_input=field(window.output_row,'Çıktı klasörü',window.output,p,actions=[('Değiştir',window.browse_output)],
                              side=None if pano else 'left',placeholder='Kaynakla aynı klasör')
    window.output_box=window.output_input.master.master
    window.cut_fields=tk.Frame(output,bg=p['dialog'])
    window.timeline_host=tk.Frame(window.cut_fields,bg=p['dialog']);window.timeline_host.pack(fill='x')
    window.timeline=None;window._probe_token=None;window._probe_revision=0;window._range_sync=False
    times=tk.Frame(window.cut_fields,bg=p['dialog']);times.pack(fill='x')
    field(times,'Başlangıç',window.start,p,width=120,side='left');field(times,'Bitiş',window.end,p,width=120,side='left')
    window.subtitle_host=tk.Frame(output,bg=p['dialog']);window.subtitle_host.pack(fill='x')
    window.description_label.max_width=900-48 if pano else 900-SIDE-48
    result=section(3,'Sonuç');window.result_step=result.step
    card=AutoCard(result,p,padding=0 if pano else 16);card.pack_configure(padx=0,pady=0);content=card.content
    if pano:card.radius=0;card.p=dict(card.p,line=p['card'])
    top=tk.Frame(content,bg=p['card']);top.pack(fill='x')
    window.job_name=label(top,palette=p,size=14,weight='SemiBold');window.job_name.max_width=360;window.job_name.pack(side='left')
    window.job_percent=label(top,palette=p,size=14,weight='Bold');window.job_percent.pack(side='right')
    window.job_time=label(top,palette=p,size=12,muted=True);window.job_time.pack(side='right',padx=(0,12))
    if pano:
        def fit_job(event=None):
            window.job_name.max_width=max(1,top.winfo_width()-window.job_percent.winfo_reqwidth()-window.job_time.winfo_reqwidth()-24);window.job_name.draw()
        for item in (top,window.job_percent,window.job_time):item.bind('<Configure>',fit_job,add='+')
    window.progress=ProgressBar(content,p,show_text=False,thickness=SIZES['detail_progress'],height=20,cells=40);window.progress.pack(fill='x',pady=(8,4))
    window.job_meta=label(content,palette=p,size=12,muted=True);window.job_meta.pack(anchor='w')
    window.status=tk.StringVar(window,'');label(content,variable=window.status,palette=p,size=12).pack(anchor='w',pady=(4,0))
    # Link check types into this list, so it needs an input's visible edge.
    window.list=tk.Text(content,height=6,bg=p['card'],fg=p['text'],insertbackground=p['text'],font=('Inter',text_px(12)),relief='flat',
                        highlightthickness=1,highlightbackground=p['input_border'],highlightcolor=p['accent'],padx=10,pady=8)
    window.run_button=action(window.actionbar,'Dönüştür',window.run,p,'primary')
    # Durdur only means something while a job runs (A14).
    window.stop_button=action(window.actionbar,'Durdur',window.cancel.set,p,'danger_ghost');window.stop_button.configure(state='disabled')
    if pano:
        window.footer_note=tk.Label(window.footer,text='İşlem bitince dosya klasörde seçili olarak açılır.',bg=p['footer'],fg=p['muted'],font=('Inter',text_px(12)),wraplength=852,justify='left',anchor='w',padx=0,pady=0,bd=0)
        window.footer.bind('<Configure>',lambda event:window.footer_note.configure(wraplength=max(1,event.width-48)),add='+')
    else:window.footer_note=label(window.actionbar,'İşlem bitince dosya klasörde seçili olarak açılır.',palette=p,muted=True)
    window.mode.trace_add('write',lambda *args:window.update_mode());window.update_mode()
    def source_changed(*args):
        window._probe_revision+=1;revision=window._probe_revision;source=window.input.get().strip()
        for child in window.subtitle_host.winfo_children():child.destroy()
        window.run_button.configure(command=window.run);window.duration=None
        if window.timeline:window.timeline.destroy();window.timeline=None
        if window._probe_token:
            window.after_cancel(window._probe_token);window._owned_timers.discard(window._probe_token)
        path=Path(source)
        # A media tool shows the chosen file as a card; links and folders keep the input.
        if source and path.is_file() and window.mode.get() in MEDIA_TOOLS:
            window.source_tile.extension=path.suffix.lstrip('.').upper()[:4] or 'FILE'
            window.source_tile.kind=file_kind(dict(filename=path.name,category=get_category_by_extension(path.name)))
            window.source_tile.draw();window.source_name.configure(text=path.name)
            window.source_meta.configure(text=number(parent,format_bytes(path.stat().st_size)))
            window.source_box.pack_forget();window.source_card.pack(fill='x',before=window.source_hint)
        else:
            window.source_card.pack_forget();window.source_box.pack(fill='x',pady=6,before=window.source_hint)
        def probe():
            window._probe_token=None
            if not path.is_file():return
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
                    window.duration=duration
                    window.source_meta.configure(text=number(parent,format_bytes(path.stat().st_size))+' · '+format_eta(duration))
                    def choose(start,end):
                        window._range_sync=True;window.start.set(SectionFields.clock(start));window.end.set(SectionFields.clock(end));window._range_sync=False
                    try:start=parse_time(window.start.get());end=min(duration,parse_time(window.end.get()))
                    except ValueError:start=0;end=min(duration,30)
                    window.timeline=SectionTimeline(window.timeline_host,palette=p,duration=duration,start=min(start,max(0,end-1)),end=end,command=choose)
                    window.timeline.pack(fill='x',pady=8)
                window.deliver(done)
            __import__('threading').Thread(target=work,daemon=True).start()
        window._probe_token=window.later(300,probe)
    def range_changed(*args):
        if window.timeline and not window._range_sync:
            from video_section import parse_time
            try:window.timeline.set_range(parse_time(window.start.get()),parse_time(window.end.get()))
            except ValueError:pass
    traces=[(variable,variable.trace_add('write',callback)) for variable,callback in ((window.input,source_changed),(window.mode,source_changed),(window.start,range_changed),(window.end,range_changed),(window.format,lambda *args:window.update_mode()))]
    def dispose(event):
        if event.widget is window:
            for variable,token in traces:variable.trace_remove('write',token)
    window.bind('<Destroy>',dispose,add='+')
    window.protocol('WM_DELETE_WINDOW',window.close)
    from tkinterdnd2 import DND_FILES
    window.drop_target_register(DND_FILES);window.dnd_bind('<<Drop>>',lambda e:window.input.set(window.tk.splitlist(e.data)[0]))
