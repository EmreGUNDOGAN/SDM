"""Two-way timeline/clock section editor; uses the existing validator."""
import tkinter as tk
from ui_controls import Switch,SegmentedControl,TextInput
from ui_indicators import SectionTimeline
from ui_surface import TextLabel
from theme_catalog import palette as resolve_palette


class SectionFields:
    def __init__(self,parent,duration=None,palette=None,command=None):
        self.p=palette or getattr(parent.winfo_toplevel(),'p',None) or resolve_palette('atlas_light')
        self.enabled=tk.BooleanVar(parent,False);self.start=tk.StringVar(parent,'00:00:00')
        self.end=tk.StringVar(parent,'00:00:30');self.exact=tk.BooleanVar(parent,False)
        self.duration=duration;self.command=command;self._syncing=False;self._traces=[]
        self.box=tk.Frame(parent,bg=self.p['card']);self.box.pack(fill='x',pady=8)
        head=tk.Frame(self.box,bg=self.p['card']);head.pack(fill='x')
        TextLabel(head,'Yalnız bir bölümü indir',weight='SemiBold',fg=self.p['text']).pack(side='left')
        Switch(head,variable=self.enabled,palette=self.p).pack(side='right')
        self.content=tk.Frame(self.box,bg=self.p['card'])
        self.timeline=None
        self.timeline_host=tk.Frame(self.content,bg=self.p['card']);self.timeline_host.pack(fill='x')
        row=tk.Frame(self.content,bg=self.p['card']);row.pack(fill='x',pady=8)
        self.inputs=[]
        for text,var in (('Başlangıç',self.start),('Bitiş',self.end)):
            TextLabel(row,text,fg=self.p['muted']).pack(side='left',padx=(0,8))
            field=TextInput(row,variable=var,palette=self.p,width=112);field.pack(side='left',padx=(0,12));self.inputs.append(field)
        SegmentedControl(self.content,{False:'Hızlı kesim',True:'Hassas kesim'},self.exact,palette=self.p).pack(anchor='e')
        self.hint=TextLabel(self.content,'',size=12,fg=self.p['muted']);self.hint.pack(anchor='w',pady=8)
        self.problem=TextLabel(self.content,'',size=12,fg=self.p['danger_fg']);self.problem.pack(anchor='w')
        for var in (self.enabled,self.start,self.end,self.exact):self._traces.append((var,var.trace_add('write',self.changed)))
        self.box.bind('<Destroy>',self.dispose);self.set_duration(duration);self.changed()

    @staticmethod
    def clock(value):
        value=round(value);return f'{value//3600:02d}:{value//60%60:02d}:{value%60:02d}'

    def set_duration(self,duration):
        self.duration=duration if duration and duration>0 else None
        if self.timeline:self.timeline.destroy();self.timeline=None
        if self.duration:
            from video_section import parse_time
            try:end=min(self.duration,parse_time(self.end.get()))
            except ValueError:end=min(self.duration,30)
            self._syncing=True;self.end.set(self.clock(end));self._syncing=False
            self.timeline=SectionTimeline(self.timeline_host,palette=self.p,duration=self.duration,start=0,end=end,command=self.from_timeline)
            self.timeline.pack(fill='x',pady=12)
        self.changed()

    def from_timeline(self,start,end):
        self._syncing=True;self.start.set(self.clock(start));self.end.set(self.clock(end));self._syncing=False;self.changed()

    def changed(self,*args):
        if self._syncing:return
        if self.enabled.get():self.content.pack(fill='x',pady=12)
        else:self.content.pack_forget()
        try:
            result=self.collect();self.problem.configure(text='')
            for field in self.inputs:field.set_error('')
            if result and self.timeline:self.timeline.set_range(result['start'],result['end'])
        except ValueError as error:
            self.problem.configure(text=str(error));result=None
            for field in self.inputs:field.set_error(str(error))
        self.hint.configure(text='Hassas kesim yeniden kodlar ve daha fazla işlemci kullanır.' if self.exact.get() else 'Hızlı kesim birkaç saniye sapabilir.')
        if self.command:self.command()

    def collect(self):
        from video_section import parse_time,validate_section
        return validate_section(dict(start=parse_time(self.start.get()),end=parse_time(self.end.get()),exact=self.exact.get()),self.duration) if self.enabled.get() else None

    def dispose(self,event):
        if event.widget is self.box:
            for var,token in self._traces:var.trace_remove('write',token)
            self._traces=[]
