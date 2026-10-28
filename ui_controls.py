"""Shared form controls for both designs. All variable traces have an owner.

Tk Entry/Text keep editing and selection native; surrounding surfaces are PIL.
Controls only edit their variables. Saving/applying preferences belongs to callers.
"""
import tkinter as tk
from PIL import Image, ImageDraw
from theme_widgets import Button, background
from ui_surface import surface, photo, icon, text_on, font, ellipsize
from ui_tokens import SIZES, RADII, SURFACE_SCALE, FONT_FAMILY, MONO_FAMILY


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
        sw, sh = SIZES['switch_width'], SIZES['switch_height']
        x, y = (w-sw)//2, (h-sh)//2
        selected = self.variable.get()
        fill = self.p['accent'] if selected else self.p['input_border']
        if self.hover:
            fill = self.p['accent_text'] if selected else self.p['muted']
        draw.rounded_rectangle((x*scale, y*scale, (x+sw)*scale, (y+sh)*scale),
                               radius=sh*scale/2, fill=fill)
        knob = sh-4
        kx = x+sw-knob-2 if selected else x+2
        draw.ellipse((kx*scale, (y+2)*scale, (kx+knob)*scale, (y+2+knob)*scale),
                     fill=self.p['on_accent'] if selected else self.p['card'])
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
                       None if selected else p['input_border'],4)
        if selected:
            glyph = icon('check-small',size,p['on_accent']);mark.paste(glyph,(0,0),glyph)
        image.paste(mark,(6,(h-size)//2))
        text_on(image,(size+14,(h-13)//2-1),ellipsize(self.text,w-size-20),fill=p['text_2'])
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
    def __init__(self,master,value,variable,text='',description='',palette=None,command=None,**kwargs):
        self.value=value;self.variable=variable;self.description=description;self.on_change=command
        super().__init__(master,text,command=self.choose,palette=palette,height=kwargs.pop('height',58),
                         width=kwargs.pop('width',160),**kwargs)
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
        image=surface(w,h,self.cget('bg'),p['accent_soft'] if selected else p['subtle'] if self.hover else p['card'],
                      p['accent'] if selected else p['input_border'],self.radius)
        text_on(image,(12,10),ellipsize(self.text,w-24,14,'SemiBold'),14,'SemiBold',p['accent_text'] if selected else p['text'])
        text_on(image,(12,32),ellipsize(self.description,w-24,12),12,fill=p['muted'])
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
        options=dict(bg=palette['card'],fg=palette['text'],insertbackground=palette['text'],
                     relief='flat',borderwidth=0,font=(MONO_FAMILY if multiline else FONT_FAMILY,-13),
                     highlightthickness=0)
        self.entry=tk.Text(self.canvas,wrap='word',**options) if multiline else tk.Entry(self.canvas,textvariable=self.variable,**options)
        self.entry.place(x=12,y=10,relwidth=1,width=-24-(64 if unit else 0),relheight=1,height=-20)
        self.unit=unit
        if unit:
            self.unit_label=tk.Label(self.canvas,text=unit,bg=palette['subtle'],fg=palette['muted'],font=(FONT_FAMILY,-12))
            self.unit_label.place(relx=1,x=-64,y=1,width=63,relheight=1,height=-2)
        self.placeholder=tk.Label(self.canvas,text=placeholder,bg=palette['card'],fg=palette['muted'],font=(FONT_FAMILY,-13))
        self.placeholder.bind('<Button-1>',lambda e:self.entry.focus_set())
        self.error_label=tk.Label(self,text='',bg=self.cget('bg'),fg=palette['danger_fg'],font=(FONT_FAMILY,-12),anchor='w')
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
        image=surface(w,h,self.cget('bg'),p['card'],p['danger'] if self.error else p['accent'] if self.focused else p['input_border'],RADII[p.get('design','atlas')]['input'])
        self._image=photo(image,self.canvas);self.canvas.delete('surface')
        self.canvas.create_image(0,0,image=self._image,anchor='nw',tags='surface');self.canvas.tag_lower('surface')
        if not self.variable.get() and not self.focused:self.placeholder.place(x=12,y=10)
        else:self.placeholder.place_forget()


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
