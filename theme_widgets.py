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
        self._mouse_focus=False
        self.underline=False;self.side_accent=False
        self.font=font.Font(family='Inter',size=-15)
        from ui_surface import font as measure_font
        width=width or round(measure_font(15,'Medium' if primary else 'Regular').getlength(text))+(52 if image else 28)
        super().__init__(master,width=width,height=40,bg=master.cget('bg'),highlightthickness=0,takefocus=1,cursor='hand2')
        self.bind('<Configure>',lambda e:self.draw())
        self.bind('<Enter>',lambda e:self.state('hover',True));self.bind('<Leave>',lambda e:(self.state('hover',False),self.state('pressed',False)))
        self.bind('<ButtonPress-1>',self.press);self.bind('<ButtonRelease-1>',self.release)
        self.bind('<FocusIn>',lambda e:self.state('focused',not self._mouse_focus));self.bind('<FocusOut>',self.blur)
        self.bind('<space>',lambda e:self.invoke());self.bind('<Return>',lambda e:self.invoke());self.draw()
    def state(self,key,value):setattr(self,key,value);self.draw()
    def press(self,event):
        if not self.disabled:self._mouse_focus=True;self.focus_set();self.state('focused',False);self.state('pressed',True)
    def blur(self,event):self._mouse_focus=False;self.state('focused',False)
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
        from ui_surface import surface,font as text_font,photo,icon
        from PIL import Image,ImageDraw
        p=self.p;w=max(1,self.winfo_width() if self.winfo_width()>1 else int(self.cget('width')));h=int(self.cget('height'))
        bg=p['accent'] if self.primary else p['selected'] if self.selected and not self.underline else p['hover'] if self.hover else self.cget('bg') if self.quiet else p['control']
        if self.primary and self.hover:bg=p['accent_hover']
        if self.pressed:bg=p['accent_pressed'] if self.primary else p['selected']
        if self.disabled:bg=self.cget('bg') if self.quiet else p['disabled_bg']
        fg=p['disabled_text'] if self.disabled else '#ffffff' if self.primary else p['accent'] if self.selected else p['text']
        if getattr(self,'status_badge',False):
            enabled='kapalı' not in self.text
            bg='#eaf9ee' if enabled else p['panel']
            if p['bg'] in ('#111c2b','#17212b','#222529'):bg='#19382a' if enabled else p['panel']
            fg='#55d67d' if p['bg'] in ('#111c2b','#17212b','#222529') else '#198849'
        edge=p['accent'] if self.focused else p['line'] if not self.quiet and not self.primary else None
        if getattr(self,'status_badge',False):edge='#285b3c' if p['bg'] in ('#111c2b','#17212b','#222529') else '#a6dfb3' 
        image=surface(w,h,self.cget('bg'),bg,edge,7)
        d=ImageDraw.Draw(image)
        if self.selected and self.underline:d.rectangle((0,h-3,w,h),fill=p['accent'])
        elif self.selected and self.side_accent:d.rectangle((0,7,3,h-7),fill=p['accent'])
        name=getattr(self,'icon_name',None)
        x=13 if self.quiet else 14
        if name:
            image.paste(icon(name,18,fg),(x,(h-18)//2),icon(name,18,fg));x+=26
        elif self.image:x+=24
        face=text_font(15,'Medium' if self.primary or self.selected else 'Regular')
        dropdown=self.text.endswith(' ▾')
        display_text=self.text.lstrip('● ')[:-2] if dropdown else self.text.lstrip('● ')
        if not name and not self.image:x=round((w-face.getlength(display_text))/2)
        if getattr(self,'status_badge',False):
            d.ellipse((11,h//2-4,19,h//2+4),fill=fg);x=26
        d.text((x,(h-15)//2-1),display_text,font=face,fill=fg,anchor='lt')
        if dropdown:
            glyph=icon('chevron',12,fg);image.paste(glyph,(w-20,(h-12)//2),glyph)
        self._surface=photo(image,self);self.delete('all');self.create_image(0,0,image=self._surface,anchor='nw')

class Search(tk.Canvas):
    def __init__(self,master,var,palette,placeholder='İndirmelerde ara…'):
        self.p=palette;self.var=var;self.focused=False;self.placeholder_text=placeholder
        super().__init__(master,bg=master.cget('bg'),height=40,width=320,highlightthickness=0)
        self.entry=tk.Entry(self,textvariable=var,bg=palette['control'],fg=palette['text'],insertbackground=palette['text'],relief='flat',borderwidth=0,font=('Inter',-15))
        self.entry.place(x=38,y=12,relwidth=1,width=-70,height=18)
        from ui_surface import TextLabel
        self.placeholder=TextLabel(self,text=placeholder,size=15,fg=palette['muted']);self.placeholder.configure(bg=palette['control'])
        self.placeholder.bind('<Button-1>',lambda e:self.entry.focus_set())
        self.bind('<Configure>',lambda e:self.draw());self.bind('<Button-1>',self.click)
        self.entry.bind('<FocusIn>',lambda e:self.focus(True));self.entry.bind('<FocusOut>',lambda e:self.focus(False))
        self._trace=var.trace_add('write',lambda *args:self.draw());self.bind('<Destroy>',self.dispose);self.draw()
    def dispose(self,event):
        if event.widget is self:
            try:self.var.trace_remove('write',self._trace)
            except tk.TclError:pass
    def focus(self,value):self.focused=value;self.draw()
    def click(self,event):
        if self.var.get() and event.x>self.winfo_width()-32:self.var.set('')
        self.entry.focus_set()
    def draw(self):
        from ui_surface import surface,photo,icon
        p=self.p;w=max(40,self.winfo_width() if self.winfo_width()>1 else 320)
        image=surface(w,40,self.cget('bg'),p['control'],p['accent'] if self.focused else p['line'],7)
        glyph=icon('search',18,p['muted']);image.paste(glyph,(12,11),glyph)
        if self.var.get():
            self.placeholder.place_forget();glyph=icon('x',16,p['muted']);image.paste(glyph,(w-27,12),glyph)
        else:self.placeholder.place(x=38,y=10)
        self._image=photo(image,self);self.delete('surface');self.create_image(0,0,image=self._image,anchor='nw',tags='surface');self.tag_lower('surface')

class Panel(tk.Canvas):
    def __init__(self,master,palette,padding=12,radius=8):
        self.p=palette;self.padding=padding;self.radius=radius
        super().__init__(master,bg=master.cget('bg'),width=200,height=90,highlightthickness=0)
        self.content=tk.Frame(self,bg=palette['panel'])
        self.window=self.create_window(padding,padding,window=self.content,anchor='nw')
        self.bind('<Configure>',self.resize)
    def resize(self,event):
        from ui_surface import surface,photo
        self._surface=photo(surface(max(1,event.width),max(1,event.height),self.cget('bg'),self.p['panel'],self.p['line'],self.radius),self)
        self.delete('surface');self.create_image(0,0,image=self._surface,anchor='nw',tags='surface')
        self.tag_lower('surface');self.itemconfigure(self.window,width=max(1,event.width-2*self.padding),height=max(1,event.height-2*self.padding))
