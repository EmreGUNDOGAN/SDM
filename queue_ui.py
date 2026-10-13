"""Calendar and time selectors for named queues."""
from datetime import datetime
import tkinter as tk
from tkinter import messagebox
import ttkbootstrap as tb
from ttkbootstrap.widgets import DateEntry
from queue_rules import default_queue,validate_queues

class QueueEditor(tb.Frame):
    def __init__(self,parent,queues):
        super().__init__(parent);self.queues=[dict(q) for q in queues];self.index=0;self.renames={}
        row=tb.Frame(self);row.pack(fill='x')
        self.names=tb.Combobox(row,state='readonly',values=[q['name'] for q in self.queues]);self.names.pack(side='left',fill='x',expand=True);self.names.current(0);self.names.bind('<<ComboboxSelected>>',self.select)
        tb.Button(row,text='+ Kuyruk',command=self.add).pack(side='left',padx=8)
        tb.Button(row,text='Kaldır',command=self.remove,bootstyle='secondary-outline').pack(side='left')
        self.name=tk.StringVar();self.limit=tk.StringVar();self.enabled=tk.BooleanVar();self.once_enabled=tk.BooleanVar()
        for label,var in [('Kuyruk adı',self.name),('Aynı anda indirilecek dosya',self.limit)]:
            r=tb.Frame(self);r.pack(fill='x',pady=8);tb.Label(r,text=label).pack(side='left')
            widget=tb.Combobox(r,textvariable=var,values=list(range(1,11)),state='readonly',width=7) if var is self.limit else tb.Entry(r,textvariable=var,width=30)
            widget.pack(side='right')
        tb.Checkbutton(self,text='Seçilen günlerde tekrarla',variable=self.enabled).pack(anchor='w',pady=8)
        self.days=[];daysrow=tb.Frame(self);daysrow.pack(fill='x')
        for day in ['Pzt','Sal','Çar','Per','Cum','Cmt','Paz']:
            var=tk.BooleanVar();self.days.append(var);tb.Checkbutton(daysrow,text=day,variable=var).pack(side='left',padx=4)
        timerow=tb.Frame(self);timerow.pack(fill='x',pady=12)
        self.times={}
        for key,label in [('start','Başlangıç'),('stop','Durma')]:
            tb.Label(timerow,text=label).pack(side='left',padx=(0,6))
            hour=tk.StringVar();minute=tk.StringVar();self.times[key]=(hour,minute)
            for var,values in [(hour,[f'{i:02}' for i in range(24)]),(minute,[f'{i:02}' for i in range(60)])]:tb.Combobox(timerow,textvariable=var,values=values,state='readonly',width=3).pack(side='left',padx=(0,8))
        tb.Separator(self).pack(fill='x',pady=8)
        tb.Checkbutton(self,text='Bir defa seçilen tarihte başlat',variable=self.once_enabled).pack(anchor='w')
        date_row=tb.Frame(self);date_row.pack(fill='x',pady=8)
        self.date=DateEntry(date_row,dateformat='%d.%m.%Y',firstweekday=0,width=14);self.date.pack(side='left')
        self.date_text=tk.StringVar(value=self.date.entry.get());self.date.entry.configure(textvariable=self.date_text)
        self.once_hour=tk.StringVar(value='22');self.once_minute=tk.StringVar(value='00')
        for var,values in [(self.once_hour,[f'{i:02}' for i in range(24)]),(self.once_minute,[f'{i:02}' for i in range(60)])]:tb.Combobox(date_row,textvariable=var,values=values,state='readonly',width=3).pack(side='left',padx=6)
        for label,offset in [('Bugün',0),('Yarın',1)]:tb.Button(date_row,text=label,command=lambda d=offset:self.quick_date(d),bootstyle='secondary-outline').pack(side='left',padx=4)
        tb.Label(self,text='Durma saatinde indirmeler duraklatılır; sonraki aralıkta devam eder.\nGece yarısını geçen saatler desteklenir. Zamanlama için SDM açık olmalı.',wraplength=620).pack(anchor='w',pady=10)
        self.summary=tb.Label(self);self.summary.pack(anchor='w');self.load()
        tb.Button(self,text='Zamanlamayı temizle',bootstyle='secondary-outline',command=lambda:(self.enabled.set(False),self.once_enabled.set(False))).pack(anchor='w',pady=5)
        self.date_text.trace_add('write',lambda *args:self.update_summary())
        for variable in [self.name,self.enabled,self.once_enabled,self.once_hour,self.once_minute,*[v for pair in self.times.values() for v in pair]]:variable.trace_add('write',lambda *args:self.update_summary())
    def quick_date(self,days):
        from datetime import timedelta
        self.date.entry.delete(0,'end');self.date.entry.insert(0,(datetime.now()+timedelta(days=days)).strftime('%d.%m.%Y'));self.once_enabled.set(True);self.update_summary()
    def update_summary(self):
        text=f"{self.name.get()} · {self.times['start'][0].get()}:{self.times['start'][1].get()} → {self.times['stop'][0].get()}:{self.times['stop'][1].get()}" if self.enabled.get() else 'Tekrarlayan zamanlama kapalı.'
        if self.once_enabled.get():text+=f'\nBir defa: {self.date.entry.get()} {self.once_hour.get()}:{self.once_minute.get()}'
        self.summary.configure(text=text)
    def store(self):
        queue=dict(name=self.name.get().strip(),limit=int(self.limit.get()),enabled=self.enabled.get(),days=[i for i,v in enumerate(self.days) if v.get()],start=':'.join(v.get() for v in self.times['start']),stop=':'.join(v.get() for v in self.times['stop']),once='')
        if self.once_enabled.get():queue['once']=datetime.strptime(self.date.entry.get(),'%d.%m.%Y').strftime('%Y-%m-%d')+f' {self.once_hour.get()}:{self.once_minute.get()}'
        validate_queues([queue])
        old=self.queues[self.index]['name']
        if old!=queue['name']:
            for original,current in list(self.renames.items()):
                if current==old:self.renames[original]=queue['name']
            self.renames[old]=queue['name']
        self.queues[self.index]=queue
    def load(self):
        queue=self.queues[self.index];self.name.set(queue['name']);self.limit.set(str(queue['limit']));self.enabled.set(queue['enabled'])
        for i,var in enumerate(self.days):var.set(i in queue['days'])
        for key,pair in self.times.items():
            for var,value in zip(pair,queue[key].split(':')):var.set(value)
        self.once_enabled.set(bool(queue.get('once')))
        if queue.get('once'):
            dt=datetime.strptime(queue['once'],'%Y-%m-%d %H:%M');self.date.entry.delete(0,'end');self.date.entry.insert(0,dt.strftime('%d.%m.%Y'));self.once_hour.set(dt.strftime('%H'));self.once_minute.set(dt.strftime('%M'))
        self.update_summary()
    def select(self,event=None):
        target=self.names.current()
        try:self.store();self.names.configure(values=[q['name'] for q in self.queues]);self.names.current(target);self.index=target;self.load()
        except Exception as error:self.names.current(self.index);messagebox.showerror('Kuyruk',str(error),parent=self)
    def add(self):
        try:self.store()
        except Exception as error:return messagebox.showerror('Kuyruk',str(error),parent=self)
        name=f'Kuyruk {len(self.queues)+1}'
        while any(q['name']==name for q in self.queues):name+=' yeni'
        self.queues.append(default_queue(name));self.index=len(self.queues)-1;self.names.configure(values=[q['name'] for q in self.queues]);self.names.current(self.index);self.load()
    def remove(self):
        if len(self.queues)==1:return
        self.queues.pop(self.index);self.index=0;self.names.configure(values=[q['name'] for q in self.queues]);self.names.current(0);self.load()
    def collect(self):self.store();return validate_queues(self.queues)
