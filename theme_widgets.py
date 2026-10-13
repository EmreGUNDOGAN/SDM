"""Solid, rounded controls with mouse and keyboard state feedback."""
import tkinter as tk
from tkinter import font

def rounded(canvas,x,y,w,h,r=7,**kw):
    points=[x+r,y,x+w-r,y,x+w,y,x+w,y+r,x+w,y+h-r,x+w,y+h,x+w-r,y+h,x+r,y+h,x,y+h,x,y+h-r,x,y+r,x,y]
    return canvas.create_polygon(points,smooth=True,**kw)

class Button(tk.Canvas):
    def __init__(self,master,text='',command=None,palette=None,image=None,primary=False,quiet=False,width=None,**kwargs):
        self.p=palette;self.text=text;self.command=command;self.image=image;self.primary=primary;self.quiet=quiet
        self.selected=False;self.disabled=False;self.hover=False;self.pressed=False;self.focused=False
        self.underline=False;self.side_accent=False
        self.font=font.Font(family='Segoe UI',size=10)
        width=width or self.font.measure(text)+(40 if image else 28)
        super().__init__(master,width=width,height=38,bg=master.cget('bg'),highlightthickness=0,takefocus=1,cursor='hand2')
        self.bind('<Configure>',lambda e:self.draw())
        self.bind('<Enter>',lambda e:self.state('hover',True));self.bind('<Leave>',lambda e:(self.state('hover',False),self.state('pressed',False)))
        self.bind('<ButtonPress-1>',self.press);self.bind('<ButtonRelease-1>',self.release)
        self.bind('<FocusIn>',lambda e:self.state('focused',True));self.bind('<FocusOut>',lambda e:self.state('focused',False))
        self.bind('<space>',lambda e:self.invoke());self.bind('<Return>',lambda e:self.invoke());self.draw()
    def state(self,key,value):setattr(self,key,value);self.draw()
    def press(self,event):
        if not self.disabled:self.focus_set();self.state('pressed',True)
    def release(self,event):
        pressed=self.pressed;self.state('pressed',False)
        if pressed and 0<=event.x<self.winfo_width() and 0<=event.y<self.winfo_height():self.invoke()
    def invoke(self):
        if not self.disabled and self.command:self.command()
    def configure(self,cnf=None,**kw):
        for key in ('text','image'):
            if key in kw:setattr(self,key,kw.pop(key))
        if 'state' in kw:self.disabled=kw.pop('state')=='disabled'
        kw.pop('bootstyle',None)
        result=super().configure(cnf,**kw);self.draw();return result
    config=configure
    def draw(self):
        if not self.winfo_exists():return
        p=self.p;self.delete('all');w=max(self.winfo_width(),int(self.cget('width')));h=38
        bg=p['accent'] if self.primary else p['selected'] if self.selected else p['hover'] if self.hover else self.cget('bg') if self.quiet else p['panel']
        if self.primary and self.hover:
            color=p['accent'].lstrip('#');bg='#'+''.join(f'{min(255,int(color[i:i+2],16)+18):02x}' for i in (0,2,4))
        if self.disabled:bg=p['line']
        if self.pressed:bg=p['selected'] if not self.primary else '#ce5527' if p['accent']=='#f26b2f' else '#0566c5'
        fg=p['muted'] if self.disabled else '#ffffff' if self.primary else p['accent'] if self.selected else p['text']
        rounded(self,1,1,w-2,h-2,fill=bg,outline=p['accent'] if self.focused or self.selected else '' if self.quiet else p['line'],width=1)
        if self.selected and self.underline:
            self.delete('all');self.create_rectangle(0,h-3,w,h,fill=p['accent'],outline='')
        elif self.selected and self.side_accent:self.create_rectangle(1,5,4,h-5,fill=p['accent'],outline='')
        if self.image:self.create_image(16,h/2,image=self.image,anchor='center')
        self.create_text(30 if self.image else w/2,h/2+int(self.pressed),text=self.text,fill=fg,font=self.font,anchor='w' if self.image else 'center')

class Search(tk.Frame):
    def __init__(self,master,var,palette,placeholder='İndirmelerde ara…'):
        p=palette;super().__init__(master,bg=p['line'],padx=1,pady=1)
        inner=tk.Frame(self,bg=p['panel']);inner.pack(fill='both',expand=True)
        tk.Label(inner,text='⌕',bg=p['panel'],fg=p['muted'],font=('Segoe UI',16)).pack(side='left',padx=(10,4))
        self.entry=tk.Entry(inner,textvariable=var,bg=p['panel'],fg=p['text'],insertbackground=p['text'],relief='flat',font=('Segoe UI',10),width=25)
        self.entry.pack(side='left',fill='x',expand=True,pady=9)
        self.placeholder=tk.Label(inner,text=placeholder,bg=p['panel'],fg=p['muted'],font=('Segoe UI',10),cursor='xterm')
        self.placeholder.place(x=32,y=9);self.placeholder.bind('<Button-1>',lambda e:self.entry.focus_set())
        self.clear=tk.Label(inner,text='×',bg=p['panel'],fg=p['muted'],cursor='hand2',font=('Segoe UI',13))
        self.clear.bind('<Button-1>',lambda e:var.set(''))
        def update(*args):
            if var.get():self.placeholder.place_forget();self.clear.pack(side='right',padx=9)
            else:self.clear.pack_forget();self.placeholder.place(x=32,y=9)
        var.trace_add('write',update);update()
        self.entry.bind('<FocusIn>',lambda e:self.configure(bg=p['accent']))
        self.entry.bind('<FocusOut>',lambda e:self.configure(bg=p['line']))

class Panel(tk.Canvas):
    def __init__(self,master,palette):
        self.p=palette
        super().__init__(master,bg=master.cget('bg'),height=90,highlightthickness=0)
        self.content=tk.Frame(self,bg=palette['panel'])
        self.window=self.create_window(12,10,window=self.content,anchor='nw')
        self.bind('<Configure>',self.resize)
    def resize(self,event):
        self.delete('surface')
        rounded(self,1,1,event.width-2,event.height-2,8,fill=self.p['panel'],outline=self.p['line'],tags='surface')
        self.tag_lower('surface');self.itemconfigure(self.window,width=max(1,event.width-24),height=max(1,event.height-20))
