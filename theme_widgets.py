"""Solid, rounded controls with mouse and keyboard state feedback."""
import tkinter as tk
from tkinter import font
from ui_tokens import SIZES,RADII,FOCUS_WIDTH,FOCUS_GAP,DISABLED_OPACITY,text_px,YORUNGE_MONO_FAMILY

def background(master,palette):
    try:return master.cget('bg')
    except tk.TclError:return palette['bg']

def rounded(canvas,x,y,w,h,r=7,**kw):
    """Compatibility helper: antialiased PIL surfaces, never smoothed polygons."""
    from ui_surface import surface,photo
    images=getattr(canvas,'_rounded_images',{})
    alive=set(canvas.find_all());images={key:value for key,value in images.items() if key in alive}
    picture=photo(surface(w,h,canvas.cget('bg'),kw.pop('fill',canvas.cget('bg')),
                          kw.pop('outline',None) or None,r),canvas)
    item=canvas.create_image(x,y,image=picture,anchor='nw',**kw)
    images[item]=picture;canvas._rounded_images=images
    return item

class Button(tk.Canvas):
    def __init__(self,master,text='',command=None,palette=None,image=None,primary=False,quiet=False,width=None,kind=None,**kwargs):
        self.p=palette;self.text=text;self.command=command;self.image=image;self.primary=primary;self.quiet=quiet
        self.selected=False;self.disabled=False;self.hover=False;self.pressed=False;self.focused=False
        self._mouse_focus=False
        self.kind=kind or ('primary' if primary else 'ghost' if quiet else 'secondary')
        self.radius=RADII[palette.get('design','atlas')]['button']
        self.underline=False;self.side_accent=False
        self.text_family=YORUNGE_MONO_FAMILY if palette.get('design')=='yorunge' else 'Inter'
        self.font=font.Font(family=self.text_family,size=text_px(15))
        self._auto_width=width is None
        from ui_surface import font as measure_font
        width=width or round(measure_font(13,'SemiBold' if primary else 'Regular',self.text_family).getlength(self.label_text(text)))+(52 if image else 28)
        height=kwargs.pop('height',SIZES['button'])
        super().__init__(master,width=width,height=height,bg=background(master,palette),highlightthickness=0,takefocus=1,cursor='hand2',**kwargs)
        self.bind('<Configure>',lambda e:self.draw())
        self.bind('<Enter>',lambda e:self.state('hover',True));self.bind('<Leave>',lambda e:(self.state('hover',False),self.state('pressed',False)))
        self.bind('<ButtonPress-1>',self.press);self.bind('<ButtonRelease-1>',self.release)
        self.bind('<FocusIn>',self.focus_in);self.bind('<FocusOut>',self.blur)
        self.bind('<space>',self.key_invoke);self.bind('<Return>',self.key_invoke);self.draw()
    def focus_in(self,event):
        mouse=self._mouse_focus;self._mouse_focus=False;self.state('focused',not mouse)
    def key_invoke(self,event):
        self.invoke();return 'break'
    def state(self,key,value):setattr(self,key,value);self.draw()
    def press(self,event):
        if not self.disabled:
            self._mouse_focus=self.focus_get() is not self;self.focus_set();self.state('focused',False);self.state('pressed',True)
    def blur(self,event):self._mouse_focus=False;self.state('focused',False)
    def release(self,event):
        pressed=self.pressed;self.state('pressed',False)
        if pressed and 0<=event.x<self.winfo_width() and 0<=event.y<self.winfo_height():self.invoke()
    def invoke(self):
        if not self.disabled and self.command:self.command()
    def label_text(self,text):
        return text.replace('i','İ').replace('ı','I').upper() if self.p.get('design')=='yorunge' else text
    def configure(self,cnf=None,**kw):
        if 'text' in kw and 'width' not in kw and self._auto_width:
            from ui_surface import font as measure_font
            title=self.label_text(kw['text'])
            kw['width']=round(measure_font(13,'SemiBold' if self.primary else 'Regular',self.text_family).getlength(title))+(52 if self.image or getattr(self,'icon_name',None) else 28)
        for key in ('text','image','command'):
            if key in kw:setattr(self,key,kw.pop(key))
        if 'state' in kw:
            self.disabled=kw.pop('state')=='disabled'
            kw['takefocus']=0 if self.disabled else 1
            if self.disabled:self.pressed=False;self.hover=False
        kw.pop('bootstyle',None)
        result=super().configure(cnf,**kw);self.draw();return result
    config=configure
    def draw(self):
        if not self.winfo_exists():return
        from ui_surface import surface,font as text_font,photo,icon,text_on,ellipsize
        from PIL import Image,ImageDraw
        p=self.p;w=max(1,self.winfo_width() if self.winfo_width()>1 else int(self.cget('width')));h=int(self.cget('height'))
        signature=(w,h,self.cget('bg'),self.text,str(self.image),self.kind,self.radius,
                   self.selected,self.disabled,self.hover,self.pressed,self.focused,
                   self.underline,self.side_accent,getattr(self,'status_badge',False),
                   getattr(self,'icon_name',None),getattr(self,'segment_choice',False),tuple(sorted(p.items())))
        signature+=(getattr(self,'icon_only',False),getattr(self,'shortcut',''),getattr(self,'centered',False))
        if getattr(self,'_draw_signature',None)==signature:return
        self._draw_signature=signature
        kind=self.kind
        design=p.get('design','atlas');family=self.text_family
        # Local wrappers keep measurement, truncation and drawing on one font.
        base_font,base_text,base_ellipsize=text_font,text_on,ellipsize
        text_font=lambda size=13,weight='Regular':base_font(size,weight,family)
        text_on=lambda *args,**kw:base_text(*args,**kw,family=family)
        ellipsize=lambda *args,**kw:base_ellipsize(*args,**kw,family=family)
        title=self.label_text(self.text)
        solid=kind in ('primary','danger_solid','start')
        bg=p['accent'] if kind=='primary' else p['danger_solid'] if kind=='danger_solid' else p['subtle'] if kind=='soft' else self.cget('bg') if kind in ('ghost','link','danger_ghost','icon') else p['control']
        fg=p['on_accent'] if kind=='primary' else p['on_danger'] if kind=='danger_solid' else p['accent'] if kind=='link' else p['danger_fg'] if kind=='danger_ghost' else p['text_2']
        if kind=='start':bg=p.get('start',p['accent']);fg=p.get('on_start',p['on_accent'])
        from PIL import ImageColor
        def mix(a,b,amount):
            return '#'+''.join(f'{round(x*(1-amount)+y*amount):02x}' for x,y in zip(ImageColor.getrgb(a),ImageColor.getrgb(b)))
        if self.selected and not self.underline:bg=p['accent_nav'];fg=p['accent_text']
        if self.selected and getattr(self,'segment_choice',False):bg=p['segment_selected'];fg=p['text']
        if self.hover:bg=mix(bg,fg,0.08) if solid else p['subtle']
        if self.pressed:bg=mix(bg,fg,0.16) if solid else p['accent_soft']
        if self.disabled:fg=p['muted']
        if getattr(self,'status_badge',False):
            enabled='kapalı' not in self.text
            bg=p['success_bg'] if enabled else p['queued_bg']
            fg=p['success_fg'] if enabled else p['queued_fg']
        edge=p['input_border'] if kind in ('secondary','segment') else None
        if design=='yorunge':
            if kind in ('outline_accent','danger_outline'):
                edge=p['danger'] if kind=='danger_outline' else p['accent'];fg=edge;bg=p['accent_soft'] if kind=='outline_accent' else self.cget('bg')
            elif kind in ('secondary','segment','icon'):edge=p['input_border']
            if self.selected and getattr(self,'segment_choice',False):edge=p['accent'];fg=p['accent']
            if self.disabled and kind=='primary':bg=p['disabled_accent'];fg=p['disabled_on_accent']
        if design=='pano' and kind=='secondary':bg=p['well'] if self.cget('bg')==p['card'] else p['card'];edge=None
        if design=='yorunge' and kind in ('primary','start','danger_solid'):
            from ui_surface import chamfered_surface
            image=chamfered_surface(w,h,self.cget('bg'),bg,edge)
        else:image=surface(w,h,self.cget('bg'),bg,edge,min(self.radius,h/2))
        d=ImageDraw.Draw(image)
        if self.selected and self.underline:d.rectangle((0,h-3,w,h),fill=p['accent'])
        elif self.selected and self.side_accent:d.rectangle((0,7,3,h-7),fill=p['accent'])
        name=getattr(self,'icon_name',None)
        x=13 if self.quiet else 14
        shortcut=getattr(self,'shortcut','')
        if (shortcut or getattr(self,'centered',False)) and name and not getattr(self,'icon_only',False):
            # Wide action: icon, label and any muted shortcut centred as one group.
            group=26+text_font(13,'SemiBold' if solid else 'Regular').getlength(title)+(10+text_font(11).getlength(shortcut) if shortcut else 0)
            x=max(x,round((w-group)/2))
        if name:
            glyph_x=(w-18)//2 if not self.text or getattr(self,'icon_only',False) else x
            image.paste(icon(name,18,fg),(glyph_x,(h-18)//2),icon(name,18,fg));x+=26
        elif self.image:x+=24
        face=text_font(13,'SemiBold' if solid or self.selected else 'Regular')
        dropdown=title.endswith(' ▾')
        display_text=title.lstrip('● ')[:-2] if dropdown else title.lstrip('● ')
        if getattr(self,'icon_only',False):display_text=''
        # Dropdowns read like inputs: value on the left, chevron on the right.
        if not name and not self.image and not dropdown:x=round((w-face.getlength(display_text))/2)
        if getattr(self,'status_badge',False):
            d.ellipse((11,h//2-4,19,h//2+4),fill=fg);x=26
        display_text=ellipsize(display_text,max(0,w-x-(24 if dropdown else 8)),13,'SemiBold' if solid or self.selected else 'Regular')
        weight='SemiBold' if solid or self.selected else 'Regular'
        if design=='yorunge':
            # Mono's ascender/descender midpoint is above its capital ink.
            # Anchor capitals by their baseline; keep the invariant per label.
            cap=-text_font(13,weight).getbbox('H',anchor='ls')[1]
            text_on(image,(x,h/2+cap/2),display_text,13,weight,fg,'ls')
        else:text_on(image,(x,h/2),display_text,13,weight,fg,'lm')
        if shortcut and display_text:
            after=x+face.getlength(display_text)+10
            text_on(image,(after,h/2),shortcut,11,fill=mix(fg,bg,0.3),anchor='lm')
        if dropdown:
            glyph=icon('chevron',12,fg);image.paste(glyph,(w-20,(h-12)//2),glyph)
        self.display(image)

    def display(self,image):
        from PIL import Image,ImageDraw
        from ui_surface import photo
        p=self.p;w,h=image.size
        # Layout can briefly shrink a focused control below the ring's width.
        # Keep its focus state; the next Configure redraws the ring at full size.
        if self.focused and min(w,h)>FOCUS_WIDTH:
            overlay=Image.new('RGBA',(w*3,h*3));focus_draw=ImageDraw.Draw(overlay)
            inset=FOCUS_WIDTH/2
            focus_draw.rounded_rectangle((inset*3,inset*3,(w-inset)*3-1,(h-inset)*3-1),radius=(self.radius+FOCUS_GAP)*3,outline=p['accent'],width=FOCUS_WIDTH*3)
            overlay=overlay.resize((w,h),Image.Resampling.LANCZOS);image.paste(overlay,(0,0),overlay)
        if self.disabled:image=Image.blend(Image.new('RGB',image.size,self.cget('bg')),image,DISABLED_OPACITY)
        self._surface=photo(image,self);self.delete('all');self.create_image(0,0,image=self._surface,anchor='nw')

class Search(tk.Canvas):
    def __init__(self,master,var,palette,placeholder='İndirmelerde ara…',text_size=15):
        self.p=palette;self.var=var;self.focused=False;self.placeholder_text=placeholder
        super().__init__(master,bg=master.cget('bg'),height=40,width=320,highlightthickness=0)
        self.entry=tk.Entry(self,textvariable=var,bg=palette['control'],fg=palette['text'],insertbackground=palette['text'],relief='flat',borderwidth=0,font=('Inter',text_px(text_size)))
        self.entry.place(x=38,y=12,relwidth=1,width=-70,height=18)
        from ui_surface import TextLabel
        self.placeholder=TextLabel(self,text=placeholder,size=text_size,fg=palette['muted']);self.placeholder.configure(bg=palette['control'])
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
        image=surface(w,40,self.cget('bg'),p['control'],p['accent'] if self.focused else p['line'],20 if p.get('design')=='pano' else 0 if p.get('design')=='yorunge' else 7)
        if p.get('design')=='yorunge':
            from ui_surface import text_on
            text_on(image,(12,20),'>',13,fill=p['accent'],anchor='lm',family='JetBrains Mono')
        else:
            glyph=icon('search',18,p['muted']);image.paste(glyph,(12,11),glyph)
        if self.var.get():
            self.placeholder.place_forget();glyph=icon('x',16,p['muted']);image.paste(glyph,(w-27,12),glyph)
        else:self.placeholder.place(x=38,y=10)
        self._image=photo(image,self);self.delete('surface');self.create_image(0,0,image=self._image,anchor='nw',tags='surface');self.tag_lower('surface')

class Panel(tk.Canvas):
    def __init__(self,master,palette,padding=12,radius=None):
        self.p=palette;self.padding=padding;self.focused=False
        # Yörünge: brackets mark a featured panel; stripe is a 3 px left status bar.
        self.brackets=True;self.stripe=None
        design=palette.get('design','atlas')
        if design=='yorunge':self.radius=0
        elif radius is not None:self.radius=radius
        else:self.radius=RADII['pano']['card'] if design=='pano' else 8
        self.inset=4 if design=='pano' and palette['panel']==palette['card'] and self.radius>=20 else 0
        super().__init__(master,bg=master.cget('bg'),width=200,height=90,highlightthickness=0)
        self.content=tk.Frame(self,bg=palette['panel'])
        self.window=self.create_window(padding+self.inset,padding+self.inset,window=self.content,anchor='nw')
        self.bind('<Configure>',self.resize)
    def resize(self,event):
        from ui_surface import surface,photo
        image=surface(max(1,event.width),max(1,event.height),self.cget('bg'),self.p['panel'],
            self.p['accent'] if self.focused else self.p['line'],self.radius,border_width=FOCUS_WIDTH if self.focused else 1)
        if self.inset and not self.focused:
            from ui_surface import pano_tile_surface
            image=pano_tile_surface(event.width,event.height,self.cget('bg'),self.p['panel'],self.radius)
        if self.p.get('design')=='yorunge':
            from PIL import ImageDraw
            d=ImageDraw.Draw(image);w,h=image.size
            if self.brackets:
                d.line((0,12,0,0,12,0),fill=self.p['accent'],width=2)
                d.line((w-13,h-1,w-1,h-1,w-1,h-13),fill=self.p['accent'],width=2)
            if self.stripe:d.rectangle((0,0,2,h-1),fill=self.stripe)
        self._surface=photo(image,self)
        self.delete('surface');self.create_image(0,0,image=self._surface,anchor='nw',tags='surface')
        self.tag_lower('surface');self.itemconfigure(self.window,width=max(1,event.width-2*(self.padding+self.inset)),height=max(1,event.height-2*(self.padding+self.inset)))

    def set_focused(self,value):
        self.focused=value
        from types import SimpleNamespace
        self.resize(SimpleNamespace(width=self.winfo_width(),height=self.winfo_height()))
