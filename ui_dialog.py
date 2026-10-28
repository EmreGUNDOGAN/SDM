"""Shared themed window/card primitives for Atlas and Odak app windows."""
import tkinter as tk
import ttkbootstrap as tb
from theme_widgets import Button,Panel
from ui_surface import TextLabel
from ui_tokens import SIZES


class ScrollBody(tk.Frame):
    def __init__(self,master,palette):
        super().__init__(master,bg=palette['dialog'])
        self.canvas=tk.Canvas(self,bg=palette['dialog'],highlightthickness=0)
        self.bar=tb.Scrollbar(self,orient='vertical',command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scroll)
        self.canvas.pack(side='left',fill='both',expand=True)
        self.content=tk.Frame(self.canvas,bg=palette['dialog'])
        self.item=self.canvas.create_window(0,0,window=self.content,anchor='nw')
        self.content.bind('<Configure>',lambda e:self.canvas.configure(scrollregion=self.canvas.bbox('all')))
        self.canvas.bind('<Configure>',lambda e:self.canvas.itemconfigure(self.item,width=e.width))
        self.canvas.bind('<MouseWheel>',lambda e:self.canvas.yview_scroll(-3 if e.delta>0 else 3,'units'))

    def scroll(self,*args):
        self.bar.set(*args)
        if float(args[0])<=0 and float(args[1])>=1:self.bar.pack_forget()
        elif not self.bar.winfo_manager():self.bar.pack(side='right',fill='y')


class AppWindow(tb.Toplevel):
    def __init__(self,parent,title,width=760,height=760,description=''):
        super().__init__(parent);self.parent=parent;self.p=parent.palette;self._owned_timers=set()
        self.title('SDM · '+title);self.configure(bg=self.p['dialog'])
        self.geometry(f'{min(width,self.winfo_screenwidth()-80)}x{min(height,self.winfo_screenheight()-100)}')
        self.minsize(min(560,self.winfo_screenwidth()-80),min(420,self.winfo_screenheight()-100))
        self.header=tk.Frame(self,bg=self.p['dialog']);self.header.pack(fill='x',padx=24,pady=(20,16))
        Button(self.header,'×',self.close,palette=self.p,kind='icon',width=34).pack(side='right')
        TextLabel(self.header,title,size=18,weight='Bold',fg=self.p['text'],max_width=width-110).pack(anchor='w')
        if description:TextLabel(self.header,description,size=13,fg=self.p['muted'],max_width=width-100).pack(anchor='w',pady=(6,0))
        self.footer=tk.Frame(self,bg=self.p['footer']);self.footer.pack(side='bottom',fill='x')
        tk.Frame(self.footer,bg=self.p['line'],height=1).pack(fill='x')
        self.actionbar=tk.Frame(self.footer,bg=self.p['footer']);self.actionbar.pack(fill='x',padx=24,pady=12)
        self.scroll=ScrollBody(self,self.p);self.scroll.pack(fill='both',expand=True)
        self.body=self.scroll.content
        self.error=tk.StringVar(self,value='')
        self.error_label=TextLabel(self.footer,textvariable=self.error,size=12,fg=self.p['danger_fg'],max_width=width-48)
        self._error_trace=self.error.trace_add('write',self.sync_error)
        self.bind('<Escape>',lambda e:self.close())
        self.bind('<Destroy>',self.dispose,add='+');self.protocol('WM_DELETE_WINDOW',self.close)

    def later(self,delay,callback):
        token=None
        def run():
            self._owned_timers.discard(token)
            if self.winfo_exists():callback()
        token=self.after(delay,run);self._owned_timers.add(token);return token

    def sync_error(self,*args):
        if self.error.get():self.error_label.pack(anchor='w',padx=24,pady=(0,8))
        else:self.error_label.pack_forget()

    def dispose(self,event):
        if event.widget is self:
            for token in self._owned_timers:self.after_cancel(token)
            self._owned_timers.clear()
            self.error.trace_remove('write',self._error_trace)

    def close(self):self.destroy()


class AutoCard(Panel):
    def __init__(self,master,palette,padding=16):
        super().__init__(master,dict(palette,panel=palette['card']),padding=padding,radius=12)
        self.pack(fill='x',padx=24,pady=(0,16))
        self.content.bind('<Configure>',self.fit,add='+')

    def resize(self,event):
        super().resize(event)
        # A zero canvas-window height follows its frame's requested size. New
        # rows/section editors then generate Configure instead of being clipped
        # inside the previous fixed-height content window.
        self.itemconfigure(self.window,height=0)

    def fit(self,event=None):
        target=self.content.winfo_reqheight()+2*self.padding
        if int(self.cget('height'))!=target:self.configure(height=target)


def label(parent,text='',variable=None,palette=None,size=13,weight='Regular',muted=False):
    return TextLabel(parent,text,textvariable=variable,size=size,weight=weight,
                     fg=palette['muted'] if muted else palette['text'])


def action(parent,text,command,palette,kind='secondary',side='right'):
    button=Button(parent,text,command,palette=palette,kind=kind,height=SIZES['button'])
    button.pack(side=side,padx=(8,0));return button


def field(parent,title,variable,palette,width=240):
    from ui_controls import TextInput
    row=tk.Frame(parent,bg=parent.cget('bg'));row.pack(fill='x',pady=6)
    label(row,title,palette=palette,muted=True).pack(side='left')
    widget=TextInput(row,variable=variable,palette=palette,width=width)
    widget.pack(side='right',fill='x',expand=True,padx=(20,0));return widget
