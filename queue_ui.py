"""Named queue editor; validation and scheduling remain in queue_rules."""
import copy
from datetime import datetime,timedelta
import tkinter as tk
from ttkbootstrap.widgets import DateEntry
from queue_rules import default_queue,validate_queues
from theme_widgets import Button
from ui_controls import Switch,CheckBox,Select
from ui_dialog import AutoCard,label,field


class QueueList(tk.Frame):
    def __init__(self,parent,names,palette,command):
        super().__init__(parent,bg=palette['dialog']);self.p=palette;self.command=command;self.index=0;self.buttons=[];self.configure(values=names)
    def configure(self,cnf=None,**kwargs):
        values=kwargs.pop('values',None)
        if values is not None:
            for button in self.buttons:button.destroy()
            self.buttons=[]
            for index,name in enumerate(values):
                button=Button(self,name,lambda n=index:self.choose(n),palette=self.p,kind='ghost',width=160)
                button.pack(fill='x',pady=2);self.buttons.append(button)
            self.current(min(self.index,len(self.buttons)-1))
        return super().configure(cnf,**kwargs)
    def current(self,index=None):
        if index is None:return self.index
        self.index=index
        for n,button in enumerate(self.buttons):button.selected=n==index;button.draw()
    def choose(self,index):self.current(index);self.command()


class QueueEditor(tk.Frame):
    def __init__(self,parent,queues,palette=None,command=None):
        self.p=palette or parent.winfo_toplevel().p
        super().__init__(parent,bg=self.p['dialog']);self.queues=copy.deepcopy(queues);self.index=0;self.renames={};self.command=command;self._loading=True;self._traces=[]
        side=tk.Frame(self,bg=self.p['dialog'],width=176);side.pack(side='left',fill='y',padx=(0,8))
        self.names=QueueList(side,[q['name'] for q in self.queues],self.p,self.select);self.names.pack(fill='x')
        Button(side,'+ Yeni kuyruk',self.add,palette=self.p,kind='soft',width=160).pack(fill='x',pady=8)
        body=tk.Frame(self,bg=self.p['dialog']);body.pack(side='left',fill='both',expand=True)
        self.name=tk.StringVar(self);self.limit=tk.StringVar(self);self.enabled=tk.BooleanVar(self);self.once_enabled=tk.BooleanVar(self)
        self.problem=tk.StringVar(self,'')
        info=AutoCard(body,self.p,padding=12);field(info.content,'Kuyruk adı',self.name,self.p,width=180)
        row=tk.Frame(info.content,bg=self.p['card']);row.pack(fill='x',pady=8);label(row,'Aynı anda',palette=self.p).pack(side='left');Select(row,{str(n):str(n) for n in range(1,11)},self.limit,palette=self.p,width=80).pack(side='right')
        daily=AutoCard(body,self.p,padding=12);head=tk.Frame(daily.content,bg=self.p['card']);head.pack(fill='x',pady=(0,8))
        label(head,'Seçilen günlerde tekrarla',palette=self.p,weight='SemiBold').pack(side='left');Switch(head,self.enabled,palette=self.p).pack(side='right')
        self.days=[];self.day_buttons=[];daysrow=tk.Frame(daily.content,bg=self.p['card']);daysrow.pack(fill='x')
        for name in ('Pzt','Sal','Çar','Per','Cum','Cmt','Paz'):
            var=tk.BooleanVar(self);self.days.append(var)
            button=Button(daysrow,name,lambda v=var:v.set(not v.get()),palette=self.p,kind='soft',width=46)
            button.pack(side='left',padx=(0,4));self.day_buttons.append(button)
        self.times={}
        for key,title in (('start','Başlangıç'),('stop','Durma')):
            row=tk.Frame(daily.content,bg=self.p['card']);row.pack(fill='x',pady=6);label(row,title,palette=self.p).pack(side='left')
            pair=(tk.StringVar(self),tk.StringVar(self));self.times[key]=pair
            self.time_controls(row,*pair)
        once=AutoCard(body,self.p,padding=12);head=tk.Frame(once.content,bg=self.p['card']);head.pack(fill='x')
        label(head,'Bir defa, seçilen tarihte başlat',palette=self.p,weight='SemiBold').pack(side='left');Switch(head,self.once_enabled,palette=self.p).pack(side='right')
        self.date=DateEntry(once.content,dateformat='%d.%m.%Y',firstweekday=0,width=14);self.date.pack(anchor='w',pady=8)
        self.date_text=tk.StringVar(self,self.date.entry.get());self.date.entry.configure(textvariable=self.date_text)
        self.once_hour=tk.StringVar(self,'22');self.once_minute=tk.StringVar(self,'00');row=tk.Frame(once.content,bg=self.p['card']);row.pack(fill='x');self.time_controls(row,self.once_hour,self.once_minute)
        row=tk.Frame(once.content,bg=self.p['card']);row.pack(fill='x',pady=8)
        for title,days in [('Bugün',0),('Yarın',1)]:Button(row,title,lambda d=days:self.quick_date(d),palette=self.p,kind='soft').pack(side='left',padx=(0,8))
        footer=AutoCard(body,self.p,padding=12);self.summary=label(footer.content,'',palette=self.p,size=12,muted=True);self.summary.max_width=420;self.summary.pack(anchor='w')
        problem=label(footer.content,variable=self.problem,palette=self.p,size=12);problem.fg=self.p['danger_fg'];problem.pack(anchor='w')
        Button(footer.content,'Zamanlamayı temizle',lambda:(self.enabled.set(False),self.once_enabled.set(False)),palette=self.p,kind='ghost').pack(anchor='w',pady=8)
        Button(footer.content,'Kuyruğu kaldır',self.remove,palette=self.p,kind='danger_ghost').pack(anchor='w')
        self.load()
        for var in (self.name,self.limit,self.enabled,self.once_enabled,self.date_text,self.once_hour,self.once_minute,*self.days,*[v for pair in self.times.values() for v in pair]):self._traces.append((var,var.trace_add('write',self.changed)))
        self.bind('<Destroy>',self.dispose,add='+')
    def time_controls(self,parent,hour,minute):
        for var,maximum in ((minute,60),(hour,24)):Select(parent,{f'{i:02}':f'{i:02}' for i in range(maximum)},var,palette=self.p,width=70).pack(side='right',padx=3)
    def changed(self,*args):
        if self._loading:return
        self.update_summary()
        if self.command:self.command()
    def quick_date(self,days):self.date_text.set((datetime.now()+timedelta(days=days)).strftime('%d.%m.%Y'));self.once_enabled.set(True)
    def update_summary(self):
        for var,button in zip(self.days,self.day_buttons):button.selected=var.get();button.configure(state='normal' if self.enabled.get() else 'disabled')
        text=f"{self.name.get()} · {self.times['start'][0].get()}:{self.times['start'][1].get()} → {self.times['stop'][0].get()}:{self.times['stop'][1].get()}" if self.enabled.get() else 'Tekrarlayan zamanlama kapalı.'
        if self.once_enabled.get():text+=f' · Bir defa: {self.date_text.get()} {self.once_hour.get()}:{self.once_minute.get()}'
        self.summary.configure(text=text+' · Durma saatinde duraklar. Zamanlama için SDM açık olmalı.')
    def store(self):
        queue=dict(name=self.name.get().strip(),limit=int(self.limit.get()),enabled=self.enabled.get(),days=[i for i,var in enumerate(self.days) if var.get()],start=':'.join(v.get() for v in self.times['start']),stop=':'.join(v.get() for v in self.times['stop']),once='')
        if self.once_enabled.get():queue['once']=datetime.strptime(self.date_text.get(),'%d.%m.%Y').strftime('%Y-%m-%d')+f' {self.once_hour.get()}:{self.once_minute.get()}'
        validate_queues([queue]);old=self.queues[self.index]['name']
        if old!=queue['name']:
            for original,current in list(self.renames.items()):
                if current==old:self.renames[original]=queue['name']
            self.renames[old]=queue['name']
        self.queues[self.index]=queue
        self.names.buttons[self.index].configure(text=queue['name'])
    def load(self):
        self._loading=True;queue=self.queues[self.index];self.name.set(queue['name']);self.limit.set(str(queue['limit']));self.enabled.set(queue['enabled'])
        for i,var in enumerate(self.days):var.set(i in queue['days'])
        for key,pair in self.times.items():
            for var,value in zip(pair,queue[key].split(':')):var.set(value)
        self.once_enabled.set(bool(queue.get('once')))
        if queue.get('once'):
            dt=datetime.strptime(queue['once'],'%Y-%m-%d %H:%M');self.date_text.set(dt.strftime('%d.%m.%Y'));self.once_hour.set(dt.strftime('%H'));self.once_minute.set(dt.strftime('%M'))
        self._loading=False;self.update_summary();self.problem.set('')
    def select(self,event=None):
        target=self.names.current()
        try:self.store();self.names.configure(values=[q['name'] for q in self.queues]);self.names.current(target);self.index=target;self.load();self.changed()
        except (ValueError,TypeError) as error:self.names.current(self.index);self.problem.set(str(error))
    def add(self):
        try:self.store()
        except (ValueError,TypeError) as error:self.problem.set(str(error));return
        if len(self.queues)>=30:self.problem.set('En çok 30 kuyruk tanımlanabilir.');return
        name=f'Kuyruk {len(self.queues)+1}'
        while any(q['name']==name for q in self.queues):name+=' yeni'
        self.queues.append(default_queue(name));self.index=len(self.queues)-1;self.names.configure(values=[q['name'] for q in self.queues]);self.names.current(self.index);self.load();self.changed()
    def remove(self):
        if len(self.queues)==1:self.problem.set('En az bir kuyruk kalmalı.');return
        removed=self.queues.pop(self.index)['name'];fallback=self.queues[0]['name']
        for original,current in list(self.renames.items()):
            if current==removed:self.renames[original]=fallback
        self.renames[removed]=fallback
        self.index=0;self.names.configure(values=[q['name'] for q in self.queues]);self.names.current(0);self.load();self.changed()
    def replace(self,queues):self.queues=copy.deepcopy(queues);self.renames={};self.index=0;self.names.configure(values=[q['name'] for q in queues]);self.names.current(0);self.load()
    def collect(self):self.store();return validate_queues(copy.deepcopy(self.queues))
    def dispose(self,event):
        if event.widget is self:
            for var,token in self._traces:var.trace_remove('write',token)
