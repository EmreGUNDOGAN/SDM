"""Shared themed window/card primitives for Atlas and Odak app windows."""
import tkinter as tk
import ttkbootstrap as tb
from theme_widgets import Button,Panel
from ui_surface import TextLabel
from ui_tokens import SIZES,YORUNGE_MONO_FAMILY

SCROLL_TAG='SDMScrollBody'
OWN_WHEEL=('Text','Listbox','Treeview')


class ScrollBody(tk.Frame):
    def __init__(self,master,palette):
        super().__init__(master,bg=palette['dialog'])
        self.canvas=tk.Canvas(self,bg=palette['dialog'],highlightthickness=0)
        self.bar=tb.Scrollbar(self,orient='vertical',command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scroll)
        self.canvas.pack(side='left',fill='both',expand=True)
        self.content=tk.Frame(self.canvas,bg=palette['dialog'])
        self.item=self.canvas.create_window(0,0,window=self.content,anchor='nw')
        self.content.bind('<Configure>',self.content_changed)
        self.canvas.bind('<Configure>',lambda e:self.canvas.itemconfigure(self.item,width=e.width))
        # Fields and cards cover the canvas, so wheel/middle-drag are bound on a
        # tag every descendant carries (bind_all would be lost: ttkbootstrap's
        # ScrolledFrame calls unbind_all). Text and lists keep their own wheel.
        root=self._root()
        if not getattr(root,'_sdm_scroll_bound',False):
            root._sdm_scroll_bound=True
            root.bind_class(SCROLL_TAG,'<MouseWheel>',ScrollBody.wheel)
            root.bind_class(SCROLL_TAG,'<ButtonPress-2>',ScrollBody.grab)
            root.bind_class(SCROLL_TAG,'<B2-Motion>',ScrollBody.drag)
        self.canvas.bindtags((SCROLL_TAG,)+self.canvas.bindtags())
        # Rows swapped in without a size change get tagged when the pointer arrives.
        self.bind('<Enter>',lambda e:self.tag_descendants(),add='+')

    def content_changed(self,event):
        self.canvas.configure(scrollregion=self.canvas.bbox('all'));self.tag_descendants()

    def tag_descendants(self):
        stack=[self.content]
        while stack:
            widget=stack.pop();tags=widget.bindtags()
            if widget.winfo_class() not in OWN_WHEEL and SCROLL_TAG not in tags:widget.bindtags((SCROLL_TAG,)+tags)
            stack.extend(widget.winfo_children())

    @staticmethod
    def owner(widget):
        """Nearest ScrollBody around `widget` that can actually scroll."""
        while widget is not None:
            if isinstance(widget,ScrollBody) and widget.bar.winfo_manager():return widget
            widget=getattr(widget,'master',None)
        return None

    @staticmethod
    def wheel(event):
        body=ScrollBody.owner(event.widget)
        if body:body.canvas.yview_scroll(-3 if event.delta>0 else 3,'units');return 'break'

    @staticmethod
    def grab(event):
        body=ScrollBody.owner(event.widget)
        if body:body.canvas.scan_mark(0,event.y_root);return 'break'

    @staticmethod
    def drag(event):
        body=ScrollBody.owner(event.widget)
        if body:body.canvas.scan_dragto(0,event.y_root,gain=1);return 'break'

    def scroll(self,*args):
        self.bar.set(*args)
        if float(args[0])<=0 and float(args[1])>=1:self.bar.pack_forget()
        elif not self.bar.winfo_manager():self.bar.pack(side='right',fill='y')


class AppWindow(tb.Toplevel):
    def __init__(self,parent,title,width=760,height=760,description='',kicker=''):
        super().__init__(parent);self.parent=parent;self.p=parent.palette;self._owned_timers=set()
        # Yörünge heads a window with a '// KICKER' line and no description.
        orbit=self.p.get('design')=='yorunge' and bool(kicker)
        self.title('SDM · '+title);self.configure(bg=self.p['dialog'])
        self._size=(min(width,self.winfo_screenwidth()-80),min(height,self.winfo_screenheight()-100))
        self.geometry('%dx%d'%self._size)
        self.minsize(min(560,self.winfo_screenwidth()-80),min(420,self.winfo_screenheight()-100))
        self.header=tk.Frame(self,bg=self.p['dialog']);self.header.pack(fill='x',padx=24,pady=(20,16))
        if orbit:
            self.kicker_label=TextLabel(self.header,'// '+kicker,size=10,fg=self.p['muted'],family=YORUNGE_MONO_FAMILY)
            self.kicker_label.pack(anchor='w',pady=(0,2))
        # × shares the title's row; packed beside the whole header it slid
        # between the title and the description line.
        top=tk.Frame(self.header,bg=self.p['dialog']);top.pack(fill='x')
        Button(top,'×',self.close,palette=self.p,kind='icon',width=34).pack(side='right')
        self.title_label=TextLabel(top,title,size=18,weight='Bold',fg=self.p['text'],max_width=width-110);self.title_label.pack(side='left')
        self.description_label=TextLabel(self.header,description,size=13,fg=self.p['muted'],max_width=width-100)
        if description and not orbit:self.description_label.pack(anchor='w',pady=(6,0))
        if orbit:tk.Frame(self,bg=self.p['line'],height=1).pack(fill='x',pady=(0,16))
        self._fit_pending=None
        self.footer=tk.Frame(self,bg=self.p['footer']);self.footer.pack(side='bottom',fill='x')
        tk.Frame(self.footer,bg=self.p['line'],height=1).pack(fill='x')
        self.actionbar=tk.Frame(self.footer,bg=self.p['footer']);self.actionbar.pack(fill='x',padx=24,pady=12)
        self.scroll=ScrollBody(self,self.p);self.scroll.pack(fill='both',expand=True)
        self.body=self.scroll.content
        # Content added later (probed qualities, found links) can grow the window too.
        self.body.bind('<Configure>',lambda e:self.schedule_fit(),add='+');self.schedule_fit()
        self.error=tk.StringVar(self,value='')
        self.error_label=TextLabel(self.footer,textvariable=self.error,size=12,fg=self.p['danger_fg'],max_width=width-48)
        self._error_trace=self.error.trace_add('write',self.sync_error)
        self.bind('<Escape>',lambda e:self.close())
        self.bind('<Destroy>',self.dispose,add='+');self.protocol('WM_DELETE_WINDOW',self.close)

    def schedule_fit(self):
        if self._fit_pending is None:self._fit_pending=self.after_idle(self.fit_height)

    def fit_height(self):
        """Grow to the content's natural height (within the screen) so the body never scrolls needlessly."""
        self._fit_pending=None
        if not self.winfo_exists():return
        self.update_idletasks()
        needed=self.header.winfo_reqheight()+36+self.body.winfo_reqheight()+self.footer.winfo_reqheight()
        limit=self.winfo_screenheight()-100
        # Before the window is mapped winfo_* report 1x1; use the designed size.
        width,height=(self.winfo_width(),self.winfo_height()) if self.winfo_ismapped() else self._size
        # Follow the content both ways (a narrow first layout stacks cards and
        # looks taller), never below the designed height and never after the
        # user has resized the window.
        target=max(self._size[1],min(needed,limit))
        if self.winfo_ismapped() and height not in (self._size[1],getattr(self,'_fitted',None)):return
        if height!=target:
            height=target;self._fitted=target;top=self.winfo_y() if self.winfo_ismapped() else None
            # Growing downwards must not push the footer below the screen.
            if top is not None and top+height>self.winfo_screenheight()-60:
                self.geometry(f'{width}x{height}+{self.winfo_x()}+{max(20,self.winfo_screenheight()-60-height)}')
            else:self.geometry(f'{width}x{height}')

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
            if self._fit_pending is not None:self.after_cancel(self._fit_pending);self._fit_pending=None
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


def step(parent,number,text,palette):
    """A14 numbered step heading: accent disc with the step number, then its title."""
    from ui_surface import surface,photo,text_on,font
    row=tk.Frame(parent,bg=parent.cget('bg'))
    disc=tk.Canvas(row,width=20,height=20,bg=row.cget('bg'),highlightthickness=0)
    image=surface(20,20,row.cget('bg'),palette['accent'],radius=10)
    # Centre the digit's ink; digits have no descender, so 'mm' sits high.
    _,top,_,bottom=font(11,'Bold').getbbox(str(number),anchor='ls')
    text_on(image,(10,10-(top+bottom)/2),str(number),11,'Bold',palette['on_accent'],'ms')
    disc.image=photo(image,disc);disc.create_image(0,0,image=disc.image,anchor='nw');disc.pack(side='left')
    row.title=label(row,text,palette=palette,size=14,weight='Bold');row.title.pack(side='left',padx=(8,0))
    return row


def field(parent,title,variable,palette,width=240,actions=(),side=None,hint='',placeholder=''):
    """Label above its input, with any buttons on the input's own row.

    A label beside the input moved every input by its label's width, and the
    buttons packed below it landed left or right depending on the caller.
    `side` packs the whole field into a row of fields (Başlangıç / Bitiş).
    """
    from ui_controls import TextInput
    box=tk.Frame(parent,bg=parent.cget('bg'))
    if side:box.pack(side=side,fill='x',expand=True,pady=6,padx=(12 if parent.pack_slaves() else 0,0))
    else:box.pack(fill='x',pady=6)
    label(box,title,palette=palette,muted=True).pack(anchor='w',pady=(0,6))
    row=tk.Frame(box,bg=box.cget('bg'));row.pack(fill='x')
    widget=TextInput(row,variable=variable,palette=palette,width=width,placeholder=placeholder)
    widget.buttons=[]
    for text,command in reversed(actions):
        button=Button(row,text,command,palette=palette,kind='soft',height=SIZES['input'])
        button.pack(side='right',padx=(8,0));widget.buttons.insert(0,button)
    widget.pack(side='left',fill='x',expand=True)
    if hint:label(box,hint,palette=palette,size=12,muted=True).pack(anchor='w',pady=(6,0))
    return widget
