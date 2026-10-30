"""Shared form controls for both designs. All variable traces have an owner.

Tk Entry/Text keep editing and selection native; surrounding surfaces are PIL.
Controls only edit their variables. Saving/applying preferences belongs to callers.
"""
import tkinter as tk
from PIL import Image, ImageDraw
from theme_widgets import Button, background
from ui_surface import surface, photo, icon, text_on, font, ellipsize
from ui_tokens import SIZES, RADII, SURFACE_SCALE, FONT_FAMILY, MONO_FAMILY, text_px, dimensions


def watch(widget, variable, callback):
    trace = variable.trace_add('write', lambda *args: callback())
    def dispose(event):
        if event.widget is widget:
            try:
                variable.trace_remove('write', trace)
            except tk.TclError:
                pass
    widget.bind('<Destroy>', dispose, add='+')


class Switch(Button):
    def __init__(self, master, variable=None, command=None, palette=None, **kwargs):
        self.variable = variable if variable is not None else tk.BooleanVar(master, False)
        self.on_change = command
        super().__init__(master, command=self.toggle, palette=palette, kind='ghost',
                         width=SIZES['switch_width'] + 8, **kwargs)
        watch(self, self.variable, self.draw)

    def toggle(self):
        self.variable.set(not self.variable.get())
        if self.on_change:
            self.on_change()

    def draw(self):
        if not self.winfo_exists():
            return
        w = max(self.winfo_width(), int(self.cget('width')))
        h = int(self.cget('height'))
        scale = SURFACE_SCALE
        image = Image.new('RGB', (w*scale, h*scale), self.cget('bg'))
        draw = ImageDraw.Draw(image)
        sizes=dimensions(self.p.get('design','atlas'));sw,sh=sizes['switch_width'],sizes['switch_height']
        x, y = (w-sw)//2, (h-sh)//2
        selected = self.variable.get()
        fill = self.p['accent'] if selected else self.p['input_border']
        if self.hover:
            fill = self.p['accent_text'] if selected else self.p['muted']
        square=self.p.get('design')=='yorunge'
        draw.rounded_rectangle((x*scale, y*scale, (x+sw)*scale, (y+sh)*scale),
                               radius=0 if square else sh*scale/2, fill=self.p['card'] if square else fill,
                               outline=fill if square else None,width=scale)
        knob = sh-4
        kx = x+sw-knob-2 if selected else x+2
        shape=draw.rectangle if square else draw.ellipse
        shape((kx*scale, (y+2)*scale, (kx+knob)*scale, (y+2+knob)*scale),
              fill=(self.p['accent'] if selected else self.p['dim']) if square else self.p['on_accent'] if selected else self.p['card'])
        self.display(image.resize((w,h), Image.Resampling.LANCZOS))


class CheckBox(Button):
    def __init__(self, master, text='', variable=None, command=None, palette=None, **kwargs):
        self.variable = variable if variable is not None else tk.BooleanVar(master, False)
        self.on_change = command
        width = kwargs.pop('width', round(font(13).getlength(text)) + SIZES['checkbox'] + 28)
        super().__init__(master, text=text, command=self.toggle, palette=palette,
                         width=width, kind='ghost', **kwargs)
        watch(self, self.variable, self.draw)

    def toggle(self):
        self.variable.set(not self.variable.get())
        if self.on_change:
            self.on_change()

    def draw(self):
        w = self.winfo_width() if self.winfo_width()>1 else int(self.cget('width'))
        h = int(self.cget('height')); p = self.p
        image = Image.new('RGB', (w,h), p['subtle'] if self.hover else self.cget('bg'))
        size = SIZES['checkbox']; selected = self.variable.get()
        mark = surface(size,size,image.getpixel((0,0)),p['accent'] if selected else p['card'],
                       None if selected else p['input_border'],0 if p.get('design')=='yorunge' else 4)
        if selected:
            glyph = icon('check-small',size,p['on_accent']);mark.paste(glyph,(0,0),glyph)
        image.paste(mark,(6,(h-size)//2))
        text_on(image,(size+14,h/2),ellipsize(self.text,w-size-20),fill=p['text_2'],anchor='lm')
        self.display(image)


class SegmentedControl(tk.Frame):
    def __init__(self, master, choices, variable=None, command=None, palette=None, **kwargs):
        super().__init__(master, bg=palette['subtle'], **kwargs)
        self.choices = dict(choices) if hasattr(choices, 'items') else {v:v for v in choices}
        if not self.choices:
            raise ValueError('At least one segment is required')
        self.variable = variable if variable is not None else tk.StringVar(self,next(iter(self.choices)))
        self.command = command;self.buttons = {}
        for key,label in self.choices.items():
            button = Button(self,label,lambda value=key:self.select(value),palette=palette,kind='ghost',height=34)
            button.segment_choice=True
            button.pack(side='left',fill='x',expand=True,padx=2,pady=2)
            self.buttons[key] = button
            for event,step in (('<Left>',-1),('<Right>',1),('<Up>',-1),('<Down>',1)):
                button.bind(event,lambda e,n=step:self.move(n))
        watch(self,self.variable,self.refresh);self.refresh()

    def select(self,key):
        if self.buttons[key].disabled:
            return
        self.variable.set(key)
        if self.command:self.command()

    def move(self,step):
        keys=[key for key,button in self.buttons.items() if not button.disabled]
        if not keys:return 'break'
        old=self.variable.get();index=keys.index(old) if old in keys else 0
        key=keys[(index+step)%len(keys)];self.select(key);self.buttons[key].focus_set()
        return 'break'

    def refresh(self):
        for key,button in self.buttons.items():
            button.selected=key==self.variable.get();button.draw()

    def set_enabled(self,enabled):
        for button in self.buttons.values():button.configure(state='normal' if enabled else 'disabled')


class RadioCard(Button):
    def __init__(self,master,value,variable,text='',description='',palette=None,command=None,align='left',**kwargs):
        self.value=value;self.variable=variable;self.description=description;self.on_change=command;self.align=align
        super().__init__(master,text,command=self.choose,palette=palette,height=kwargs.pop('height',58),
                         width=kwargs.pop('width',160),**kwargs)
        if palette.get('design')=='pano':self.radius=RADII['pano']['card']
        watch(self,variable,self.refresh);self.refresh()

    def choose(self):
        self.variable.set(self.value)
        if self.on_change:self.on_change()

    def refresh(self):
        self.selected=self.variable.get()==self.value;self.draw()

    def draw(self):
        w=self.winfo_width() if self.winfo_width()>1 else int(self.cget('width'))
        h=int(self.cget('height'));p=self.p
        selected=self.variable.get()==self.value
        filled=selected and p.get('design')=='pano'
        image=surface(w,h,self.cget('bg'),p['accent'] if filled else p['accent_soft'] if selected else p['subtle'] if self.hover else p['card'],
                      p['accent'] if selected else p['input_border'],self.radius)
        # Short choices (MP4 / Video) sit centred in their card (A14).
        x,anchor=(w/2,'ma') if self.align=='center' else (12,'la')
        text_on(image,(x,10),ellipsize(self.text,w-24,14,'SemiBold'),14,'SemiBold',p['on_accent'] if filled else p['accent_text'] if selected else p['text'],anchor)
        text_on(image,(x,32),ellipsize(self.description,w-24,12),12,fill=p['on_accent'] if filled else p['muted'],anchor=anchor)
        self.display(image)


class ToolCard(RadioCard):
    """A14 tool list entry: file-type tile, name and description.

    Only the selected tool is raised as a card; the rest lie flat on the side panel.
    """
    def __init__(self,master,value,variable,tile,**kwargs):
        if kwargs.get('palette',{}).get('design')=='pano':kwargs.setdefault('height',132)
        self.tile=tile;super().__init__(master,value,variable,**kwargs)

    def draw(self):
        from ui_tokens import file_tile_colors
        w=self.winfo_width() if self.winfo_width()>1 else int(self.cget('width'))
        h=int(self.cget('height'));p=self.p;bg=self.cget('bg')
        selected=self.variable.get()==self.value
        if p.get('design')=='pano':
            fill=p['accent'] if selected else p['card']
            image=surface(w,h,bg,fill,radius=20);draw=ImageDraw.Draw(image)
            tile_text,kind=self.tile;tile_bg,tile_fg=file_tile_colors(kind,p['mode'],'pano')
            draw.rounded_rectangle((12,12,48,48),radius=12,fill=p['card'] if selected else tile_bg)
            text_on(image,(30,30),tile_text,10,'Bold',p['accent'] if selected else tile_fg,'mm')
            text_on(image,(12,58),ellipsize(self.text,w-24,13,'Bold'),13,'Bold',p['on_accent'] if selected else p['text'])
            for index,line in enumerate(self.description.splitlines()[:2]):
                text_on(image,(12,84+16*index),ellipsize(line,w-24,11),11,fill=p['on_accent'] if selected else p['muted'])
            self.display(image);return
        fill=p['card'] if selected else p['subtle'] if self.hover else bg
        image=surface(w,h,bg,fill,p['line'] if selected else fill,self.radius)
        label,kind=self.tile;tile_bg,tile_fg=file_tile_colors(kind,p['mode'],p.get('design','atlas'))
        top=(h-32)//2
        ImageDraw.Draw(image).rounded_rectangle((12,top,48,top+32),radius=RADII[p.get('design','atlas')]['tile'],fill=tile_bg)
        text_on(image,(30,top+16),label,10,'Bold',tile_fg,'mm')
        text_on(image,(60,10),ellipsize(self.text,w-72,14,'SemiBold'),14,'SemiBold',p['text'])
        text_on(image,(60,32),ellipsize(self.description,w-72,12),12,fill=p['muted'])
        self.display(image)


class DesignCard(RadioCard):
    """A08 design choice: a miniature of that design above "Name · description".

    The miniature uses the design's own palette (Atlas light, Odak dark), so it
    looks the same whichever design is currently active.
    """
    def __init__(self,master,value,variable,**kwargs):
        super().__init__(master,value,variable,height=kwargs.pop('height',110),**kwargs)

    def draw(self):
        from theme_catalog import palette
        from ui_tokens import FIXED_MODES
        w=self.winfo_width() if self.winfo_width()>1 else int(self.cget('width'))
        h=int(self.cget('height'));p=self.p
        selected=self.variable.get()==self.value
        image=surface(w,h,self.cget('bg'),p['accent_soft'] if selected else p['subtle'] if self.hover else p['card'],
                      p['accent'] if selected else p['input_border'],self.radius)
        mini=palette(self.value+'_'+FIXED_MODES.get(self.value,'light' if self.value=='atlas' else 'dark'));right,bottom=w-12,h-42
        rail=round((right-12)*(.3 if self.value=='atlas' else .12))
        thumb=surface(right-12,bottom-12,p['card'],mini['card' if self.value=='atlas' else 'bg'],mini['line'],6)
        ImageDraw.Draw(thumb).rectangle((1,1,rail,thumb.height-2),fill=mini['side'])
        td=ImageDraw.Draw(thumb)
        if self.value=='pano':
            td.rectangle((1,1,thumb.width-2,thumb.height-2),fill=mini['bg'])
            gap=4;tw=(thumb.width-3*gap)//2;th=(thumb.height-3*gap)//2
            for col,row in ((0,0),(1,0),(0,1),(1,1)):
                x=gap+col*(tw+gap);y=gap+row*(th+gap)
                td.rounded_rectangle((x,y,x+tw,y+th),radius=5,fill=mini['card'])
            td.rounded_rectangle((gap+4,gap+4,gap+tw-4,gap+7),radius=1,fill=mini['accent'])
        elif self.value=='yorunge':
            for x in range(0,thumb.width,12):td.line((x,0,x,thumb.height),fill=mini['grid_line'])
            for y in range(0,thumb.height,12):td.line((0,y,thumb.width,y),fill=mini['grid_line'])
            td.rectangle((5,5,thumb.width-6,thumb.height-6),outline=mini['accent'])
            td.line((thumb.width//3,6,thumb.width//3,thumb.height-7),fill=mini['line'])
        image.paste(thumb,(12,12))
        title=ellipsize(self.text,w-24,13,'Bold');rest=ellipsize(' · '+self.description,w-24-font(13,'Bold').getlength(title),12)
        text_on(image,(12,h-14),title,13,'Bold',p['text'],'ls')
        text_on(image,(12+font(13,'Bold').getlength(title),h-14),rest,12,fill=p['muted'],anchor='ls')
        self.display(image)


class Select(Button):
    """Labelled value map; key storage is independent of translated labels."""
    def __init__(self,master,choices,variable=None,palette=None,command=None,**kwargs):
        self.choices=dict(choices) if hasattr(choices,'items') else {v:v for v in choices}
        if not self.choices:raise ValueError('At least one choice is required')
        self.variable=variable if variable is not None else tk.StringVar(master,next(iter(self.choices)))
        self.on_change=command;self.menu=None;self._prefix='';self._type_timer=None
        super().__init__(master,palette=palette,command=self.open_menu,**kwargs)
        watch(self,self.variable,self.refresh);self.refresh()
        self.bind('<Down>',lambda e:self.step(1));self.bind('<Up>',lambda e:self.step(-1))
        self.bind('<KeyPress>',self.type_search,add='+')
        self.bind('<Destroy>',self.dispose,add='+')

    def refresh(self):
        self.configure(text=self.choices.get(self.variable.get(),'Seç…')+' ▾')

    def choose(self,value):
        if self.disabled:return
        self.variable.set(value)
        if self.on_change:self.on_change()

    def step(self,direction):
        if self.disabled:return 'break'
        values=list(self.choices);old=self.variable.get();index=values.index(old) if old in values else 0
        self.choose(values[(index+direction)%len(values)]);return 'break'

    def type_search(self,event):
        if self.disabled or not event.char or not event.char.isprintable() or event.char.isspace():return
        self._prefix+=event.char.casefold()
        if self._type_timer:self.after_cancel(self._type_timer)
        self._type_timer=self.after(700,self.clear_prefix)
        for key,label in self.choices.items():
            if label.casefold().startswith(self._prefix):self.choose(key);break

    def clear_prefix(self):
        self._prefix='';self._type_timer=None

    def open_menu(self):
        from ui_overlays import PopupMenu
        if self.menu and self.menu.winfo_exists():self.menu.close()
        self.menu=PopupMenu(self,self.p)
        for value,label in self.choices.items():
            self.menu.add_item(label,lambda key=value:self.choose(key),variable=self.variable,value=value)
        self.menu.popup(self.winfo_rootx(),self.winfo_rooty()+self.winfo_height())

    def dispose(self,event):
        if event.widget is self:
            if self._type_timer:self.after_cancel(self._type_timer)
            if self.menu and self.menu.winfo_exists():self.menu.close(restore=False)


class TextInput(tk.Frame):
    def __init__(self,master,variable=None,palette=None,multiline=False,unit='',placeholder='',**kwargs):
        width=kwargs.pop('width',320);height=kwargs.pop('height',120 if multiline else SIZES['input'])
        super().__init__(master,bg=background(master,palette),**kwargs)
        self.p=palette;self.error='';self.focused=False;self.multiline=multiline
        self.variable=variable if variable is not None else tk.StringVar(self,'')
        self.canvas=tk.Canvas(self,width=width,height=height,bg=self.cget('bg'),highlightthickness=0)
        self.canvas.pack(fill='both',expand=True)
        fill=palette.get('well',palette['card'])
        options=dict(bg=fill,fg=palette['text'],insertbackground=palette['text'],
                     relief='flat',borderwidth=0,font=(MONO_FAMILY if multiline else FONT_FAMILY,text_px(13)),
                     highlightthickness=0)
        self.entry=tk.Text(self.canvas,wrap='word',**options) if multiline else tk.Entry(self.canvas,textvariable=self.variable,**options)
        self.entry.place(x=12,y=10,relwidth=1,width=-24-(64 if unit else 0),relheight=1,height=-20)
        self.unit=unit
        if unit:
            self.unit_label=tk.Label(self.canvas,text=unit,bg=palette['subtle'],fg=palette['muted'],font=(FONT_FAMILY,text_px(12)))
            self.unit_label.place(relx=1,x=-64,y=1,width=63,relheight=1,height=-2)
        self.placeholder=tk.Label(self.canvas,text=placeholder,bg=fill,fg=palette['muted'],font=(FONT_FAMILY,text_px(13)))
        self.placeholder.bind('<Button-1>',lambda e:self.entry.focus_set())
        self.error_label=tk.Label(self,text='',bg=self.cget('bg'),fg=palette['danger_fg'],font=(FONT_FAMILY,text_px(12)),anchor='w')
        self.entry.bind('<FocusIn>',lambda e:self.focus(True));self.entry.bind('<FocusOut>',lambda e:self.focus(False))
        self.canvas.bind('<Configure>',lambda e:self.draw())
        if multiline:
            self.entry.insert('1.0',self.variable.get());self.entry.edit_modified(False)
            self.entry.bind('<<Modified>>',self.edited)
        watch(self,self.variable,self.sync);self.draw()

    def edited(self,event):
        if self.entry.edit_modified():
            self.variable.set(self.entry.get('1.0','end-1c'));self.entry.edit_modified(False)

    def sync(self):
        if self.multiline and self.entry.get('1.0','end-1c')!=self.variable.get():
            self.entry.delete('1.0','end');self.entry.insert('1.0',self.variable.get());self.entry.edit_modified(False)
        self.draw()

    def focus(self,value):
        self.focused=value;self.draw()

    def set_error(self,message):
        self.error=message;self.error_label.configure(text=message)
        if message:self.error_label.pack(fill='x',pady=(4,0))
        else:self.error_label.pack_forget()
        self.draw()

    def set_enabled(self,enabled):
        self.entry.configure(state='normal' if enabled else 'disabled',takefocus=int(enabled))

    def draw(self):
        p=self.p;w=max(self.canvas.winfo_width(),int(self.canvas.cget('width')) if self.canvas.winfo_width()<=1 else 1)
        h=max(self.canvas.winfo_height(),int(self.canvas.cget('height')) if self.canvas.winfo_height()<=1 else 1)
        edge=p['danger'] if self.error else p['accent'] if self.focused else None if p.get('design')=='pano' else p['input_border']
        image=surface(w,h,self.cget('bg'),p.get('well',p['card']),edge,RADII[p.get('design','atlas')]['input'])
        self._image=photo(image,self.canvas);self.canvas.delete('surface')
        self.canvas.create_image(0,0,image=self._image,anchor='nw',tags='surface');self.canvas.tag_lower('surface')
        if not self.variable.get() and not self.focused:self.placeholder.place(x=12,y=10)
        else:self.placeholder.place_forget()


class NumberStepper(tk.Frame):
    """Bounded draft number: buttons/keys/wheel, double-click for native editing."""
    def __init__(self,master,variable,palette,minimum,maximum):
        super().__init__(master,bg=master.cget('bg'));self.variable=variable;self.minimum=minimum;self.maximum=maximum;self.error=''
        row=tk.Frame(self,bg=self.cget('bg'));row.pack()
        self.minus=Button(row,'−',lambda:self.adjust(-1),palette=palette,kind='soft',width=34,height=34);self.minus.pack(side='left')
        self.input=TextInput(row,variable=variable,palette=dict(palette,well=self.cget('bg')),width=112,height=54)
        self.input.pack(side='left',padx=8);self.entry=self.input.entry
        self.entry.configure(justify='center',font=(FONT_FAMILY,text_px(26),'bold'),state='readonly',readonlybackground=self.cget('bg'))
        from tkinter import font as tkfont
        self.input.canvas.configure(height=max(54,tkfont.Font(font=self.entry.cget('font')).metrics('linespace')+20))
        self.plus=Button(row,'+',lambda:self.adjust(1),palette=palette,kind='soft',width=34,height=34);self.plus.pack(side='left')
        self.problem=tk.Label(self,text='',bg=self.cget('bg'),fg=palette['danger_fg'],font=(FONT_FAMILY,text_px(12)),wraplength=200,justify='center')
        self.entry.bind('<Double-Button-1>',self.edit)
        self.entry.bind('<Return>',self.lock);self.entry.bind('<FocusOut>',self.lock,add='+')
        for widget in (self,self.minus,self.plus,self.input.canvas,self.entry):
            widget.bind('<Up>',lambda event:self.adjust(1))
            widget.bind('<Down>',lambda event:self.adjust(-1))
            widget.bind('<MouseWheel>',lambda event:self.adjust(1 if event.delta>0 else -1))
            # ScrollBody adds its wheel tag first. A hovered number consumes its
            # own wheel before the page; other controls retain page scrolling.
            widget.bind('<Enter>',lambda event:self.wheel_first(event.widget),add='+')
        watch(self,variable,self.refresh);self.refresh()

    @staticmethod
    def wheel_first(widget):widget.bindtags((str(widget),)+tuple(tag for tag in widget.bindtags() if tag!=str(widget)))

    def edit(self,event=None):
        self.entry.configure(state='normal');self.entry.focus_set();self.entry.selection_range(0,'end');return 'break'

    def lock(self,event=None):self.entry.configure(state='readonly');return 'break' if event and event.type==tk.EventType.KeyPress else None

    def adjust(self,step):
        try:value=int(self.variable.get())
        except (ValueError,TypeError,tk.TclError):return 'break'
        if self.minimum<=value<=self.maximum:self.variable.set(str(max(self.minimum,min(self.maximum,value+step))))
        return 'break'

    def refresh(self):
        try:value=int(self.variable.get());valid=self.minimum<=value<=self.maximum
        except (ValueError,TypeError,tk.TclError):value=0;valid=False
        self.minus.configure(state='normal' if valid and value>self.minimum else 'disabled')
        self.plus.configure(state='normal' if valid and value<self.maximum else 'disabled')

    def set_error(self,message):
        self.error=message;self.input.error=message;self.input.draw();self.problem.configure(text=message)
        if message:self.problem.pack(fill='x',pady=(4,0))
        else:self.problem.pack_forget()


class ChipInput(tk.Frame):
    def __init__(self,master,values=(),palette=None,command=None,**kwargs):
        super().__init__(master,bg=background(master,palette),**kwargs)
        self.p=palette;self.command=command;self.values=list(dict.fromkeys(values));self.chips=[]
        self.chip_frame=tk.Frame(self,bg=self.cget('bg'));self.chip_frame.pack(fill='x')
        self.input=TextInput(self,palette=palette,placeholder='uzantı ekle…',width=160)
        self.input.pack(fill='x');self.input.entry.bind('<Return>',self.add_from_entry)
        self.refresh()

    def add_from_entry(self,event=None):
        value=self.input.variable.get().strip().lower().lstrip('.')
        if value and value not in self.values:
            self.values.append(value);self.refresh()
            if self.command:self.command()
        self.input.variable.set('');return 'break'

    def remove(self,value):
        self.values.remove(value);self.refresh()
        if self.command:self.command()

    def refresh(self):
        for child in self.chip_frame.winfo_children():child.destroy()
        self.chips=[]
        # Wrapping grid avoids horizontal overflow for long extension lists.
        for index,value in enumerate(self.values):
            chip=Button(self.chip_frame,value+' ×',lambda item=value:self.remove(item),
                        palette=self.p,kind='soft',height=SIZES['chip'])
            chip.grid(row=index//5,column=index%5,padx=2,pady=2,sticky='w');self.chips.append(chip)


class FormRow(tk.Frame):
    def __init__(self,master,label,variable,palette,command=None,action='Değiştir'):
        super().__init__(master,bg=palette['card'])
        from ui_surface import TextLabel
        TextLabel(self,label,size=12,fg=palette['muted']).pack(side='left',padx=12,pady=10)
        if command:Button(self,action,command,palette=palette,kind='soft',height=SIZES['small_button']).pack(side='right',padx=8)
        TextLabel(self,textvariable=variable,size=13,fg=palette['text']).pack(side='left',fill='x',expand=True,padx=8)
