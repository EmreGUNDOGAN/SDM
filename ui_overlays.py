"""Shared popup menus, modal shells and timed notifications. No business logic."""
import time
import tkinter as tk
from theme_widgets import Button, Panel, background
from ui_surface import TextLabel
from ui_tokens import SIZES, RADII, TOAST_DURATION, TOAST_ACTION_DURATION, TOAST_LIMIT


class PopupMenu(tk.Toplevel):
    def __init__(self,master,palette,parent_menu=None):
        super().__init__(master)
        self.withdraw();self.overrideredirect(True);self.p=palette
        self.parent_menu=parent_menu;self.child_menu=None;self.items=[];self.active=-1
        self._previous_focus=None;self._previous_grab=None;self._closing=False;self._focus_check=None
        self.configure(bg=palette['card'])
        self.panel=Panel(self,palette,padding=SIZES['menu_padding'],radius=RADII[palette.get('design','atlas')]['menu'])
        self.panel.pack(fill='both',expand=True)
        self.panel.content.configure(bg=palette['card'])
        self.bind('<Escape>',lambda e:self.close_root())
        self.bind('<Down>',lambda e:self.move(1));self.bind('<Up>',lambda e:self.move(-1))
        self.bind('<Right>',lambda e:self.open_submenu());self.bind('<Left>',self.back)
        self.bind('<Return>',lambda e:self.activate());self.bind('<space>',lambda e:self.activate())
        self.bind('<ButtonPress-1>',self.outside,add='+')
        self.bind('<FocusOut>',self.lost_focus,add='+')

    def add_item(self,label,command=None,disabled=False,danger=False,shortcut='',
                 submenu=None,variable=None,value=None,description=''):
        index=len(self.items)
        prefix=('● ' if variable.get()==value else '   ') if variable is not None else ''
        suffix='  ›' if submenu is not None else '  '+shortcut if shortcut else ''
        button=Button(self.panel.content,prefix+label+suffix,lambda:self.activate(index),
                      palette=self.p,kind='danger_ghost' if danger else 'ghost',
                      width=max(SIZES['menu_width'],len(label+suffix)*8+24),
                      height=SIZES['menu_row']+(18 if description else 0))
        button.pack(fill='x');button.configure(takefocus=0,state='disabled' if disabled else 'normal')
        item=dict(button=button,command=command,submenu=submenu,variable=variable,value=value)
        self.items.append(item)
        button.bind('<Enter>',lambda e,i=index:self.highlight(i),add='+')
        if description:
            # Description is retained for callers and testing; separate text keeps wrapping native.
            hint=TextLabel(self.panel.content,description,size=12,fg=self.p['muted'])
            hint.pack(fill='x',padx=12,pady=(0,4))
        return button

    def add_separator(self):
        tk.Frame(self.panel.content,bg=self.p['line'],height=1).pack(fill='x',pady=5)

    def popup(self,x,y):
        self._previous_focus=self.master.focus_get();self._previous_grab=self.grab_current()
        self.update_idletasks()
        width=max(SIZES['menu_width'],self.panel.content.winfo_reqwidth()+2*SIZES['menu_padding'])
        height=self.panel.content.winfo_reqheight()+2*SIZES['menu_padding']
        x,y=self.fit_position(x,y,width,height,self.winfo_screenwidth(),self.winfo_screenheight())
        self.geometry(f'{width}x{height}+{x}+{y}');self.deiconify();self.lift()
        self.grab_set();self.focus_force();self.move(1)

    @staticmethod
    def fit_position(x,y,width,height,screen_width,screen_height):
        return max(0,min(x,screen_width-width)),max(0,min(y,screen_height-height))

    def highlight(self,index):
        if self.items[index]['button'].disabled:return
        self.active=index
        for i,item in enumerate(self.items):item['button'].selected=i==index;item['button'].draw()
        if self.child_menu and self.child_menu.winfo_exists():self.child_menu.close(restore=False)
        if self.items[index]['submenu'] is not None:self.open_submenu()

    def move(self,direction):
        enabled=[i for i,item in enumerate(self.items) if not item['button'].disabled]
        if enabled:
            position=enabled.index(self.active) if self.active in enabled else (-1 if direction>0 else 0)
            self.highlight(enabled[(position+direction)%len(enabled)])
        return 'break'

    def activate(self,index=None):
        index=self.active if index is None else index
        if index<0:return 'break'
        item=self.items[index]
        if item['button'].disabled:return 'break'
        self.active=index
        if item['submenu'] is not None:return self.open_submenu()
        variable,value,command=item['variable'],item['value'],item['command']
        self.close_root()
        if variable is not None:variable.set(value)
        if command:command()
        return 'break'

    def open_submenu(self):
        if self.active<0:return 'break'
        item=self.items[self.active]
        if item['submenu'] is None:return 'break'
        if self.child_menu and self.child_menu.winfo_exists():return 'break'
        self.child_menu=PopupMenu(self,self.p,parent_menu=self)
        item['submenu'](self.child_menu)
        row=item['button'];self.child_menu.update_idletasks()
        width=max(SIZES['menu_width'],self.child_menu.panel.content.winfo_reqwidth()+12)
        x=self.winfo_rootx()+self.winfo_width()
        if x+width>self.winfo_screenwidth():x=self.winfo_rootx()-width
        self.child_menu.popup(x,row.winfo_rooty())
        return 'break'

    def back(self,event=None):
        if self.parent_menu:
            parent=self.parent_menu;self.close(restore=False);parent.grab_set();parent.focus_force()
        return 'break'

    def outside(self,event):
        menu=self
        while menu.parent_menu:menu=menu.parent_menu
        current=menu
        while current and current.winfo_exists():
            if (current.winfo_rootx()<=event.x_root<current.winfo_rootx()+current.winfo_width() and
                current.winfo_rooty()<=event.y_root<current.winfo_rooty()+current.winfo_height()):return
            current=current.child_menu
        self.close_root();return 'break'

    def lost_focus(self,event):
        if not self._closing:
            if self._focus_check:self.after_cancel(self._focus_check)
            self._focus_check=self.after_idle(self.check_focus)

    def check_focus(self):
        self._focus_check=None
        if not self.winfo_exists() or self._closing:return
        current=self.focus_get()
        if current is None:self.close_root()

    def close_root(self):
        menu=self
        while menu.parent_menu:menu=menu.parent_menu
        menu.close();return 'break'

    def close(self,restore=True):
        if self._closing:return
        self._closing=True
        if self._focus_check:self.after_cancel(self._focus_check);self._focus_check=None
        if self.child_menu and self.child_menu.winfo_exists():self.child_menu.close(restore=False)
        if self.grab_current() is self:self.grab_release()
        previous_focus,previous_grab=self._previous_focus,self._previous_grab
        self.destroy()
        if restore:
            if previous_grab and previous_grab.winfo_exists():previous_grab.grab_set()
            if previous_focus and previous_focus.winfo_exists():previous_focus.focus_set()


class DialogShell(tk.Toplevel):
    def __init__(self,master,title,palette,description='',width=560,height=440):
        super().__init__(master);self.withdraw();self.p=palette;self.result=None
        self._previous_focus=master.focus_get();self._previous_grab=self.grab_current()
        self.title('SDM · '+title);self.configure(bg=palette['dialog'])
        self.geometry(f'{width}x{height}');self.transient(master.winfo_toplevel())
        self.header=tk.Frame(self,bg=palette['dialog']);self.header.pack(fill='x',padx=24,pady=(20,12))
        Button(self.header,'×',lambda:self.finish(None),palette=palette,kind='icon',width=34).pack(side='right')
        TextLabel(self.header,title,size=18,weight='Bold',fg=palette['text']).pack(anchor='w')
        if description:TextLabel(self.header,description,size=13,fg=palette['muted']).pack(anchor='w',pady=(6,0))
        self.footer=tk.Frame(self,bg=palette['footer']);self.footer.pack(side='bottom',fill='x')
        self.body=tk.Frame(self,bg=palette['dialog']);self.body.pack(fill='both',expand=True,padx=24,pady=12)
        self.actions={};self.protocol('WM_DELETE_WINDOW',lambda:self.finish(None))
        self.bind('<Escape>',lambda e:self.finish(None))

    def add_action(self,key,label,kind='secondary'):
        button=Button(self.footer,label,lambda:self.finish(key),palette=self.p,kind=kind)
        button.pack(side='right',padx=8,pady=12);self.actions[key]=button
        return button

    def show(self):
        self.deiconify();self.update_idletasks();self.grab_set()
        if self.actions:next(iter(self.actions.values())).focus_set()
        return self

    def finish(self,result):
        self.result=result
        if self.grab_current() is self:self.grab_release()
        self.destroy()
        if self._previous_grab and self._previous_grab.winfo_exists():self._previous_grab.grab_set()
        if self._previous_focus and self._previous_focus.winfo_exists():self._previous_focus.focus_set()


class MessageDialog(DialogShell):
    def __init__(self,master,title,message,palette,technical='',items=(),**kwargs):
        super().__init__(master,title,palette,**kwargs)
        tk.Label(self.body,text=message,wraplength=480,justify='left',anchor='w',
                 bg=palette['dialog'],fg=palette['text'],font=('Inter',-13)).pack(fill='x')
        if items:
            listing=tk.Text(self.body,height=min(6,len(items)),wrap='word',bg=palette['card'],
                            fg=palette['text'],relief='flat',font=('Inter',-12))
            listing.insert('1.0','\n'.join(items));listing.configure(state='disabled');listing.pack(fill='x',pady=12)
        self.details=None
        if technical:
            Button(self.body,'Teknik ayrıntı ▾',self.toggle_details,palette=palette,kind='ghost').pack(anchor='w',pady=(12,0))
            self.details=tk.Text(self.body,height=4,wrap='word',bg=palette['card'],fg=palette['text'],font=('Consolas',-12))
            self.details.insert('1.0',technical);self.details.configure(state='disabled')

    def toggle_details(self):
        if self.details.winfo_manager():self.details.pack_forget()
        else:self.details.pack(fill='both',expand=True,pady=8)


class Drawer(tk.Frame):
    """A packed sibling shrinks the list; it never places over list content."""
    def __init__(self,master,palette,title='',command=None,width=None):
        super().__init__(master,bg=palette['dialog'],width=width or SIZES['detail_drawer'])
        self.pack_propagate(False);self.on_close=command
        head=tk.Frame(self,bg=self.cget('bg'));head.pack(fill='x',padx=20,pady=16)
        Button(head,'×',self.close,palette=palette,kind='icon',width=34).pack(side='right')
        TextLabel(head,title,size=16,weight='SemiBold',fg=palette['text']).pack(side='left')
        self.content=tk.Frame(self,bg=self.cget('bg'));self.content.pack(fill='both',expand=True,padx=20)

    def open(self,before=None):
        self.pack(side='right',fill='y',before=before) if before else self.pack(side='right',fill='y')

    def close(self):
        self.pack_forget()
        if self.on_close:self.on_close()


class Toast(tk.Toplevel):
    def __init__(self,manager,title,message,action=None):
        super().__init__(manager.owner);self.withdraw();self.overrideredirect(True)
        self.manager=manager;self.p=manager.p;self._timer=None;self._deadline=0;self._remaining=0
        self.attributes('-topmost',True);self.configure(bg=self.p['toast'])
        body=tk.Frame(self,bg=self.p['toast']);body.pack(fill='both',expand=True,padx=14,pady=12)
        if action:
            label,callback=action
            action_palette=dict(self.p,text_2=self.p['toast_text'],subtle=self.p['toast'],card=self.p['toast'])
            Button(body,label,lambda:self.perform(callback),palette=action_palette,kind='ghost').pack(side='right',padx=(10,0))
        TextLabel(body,title,size=13,weight='SemiBold',fg=self.p['toast_text']).pack(anchor='w')
        TextLabel(body,message,size=12,fg=self.p['toast_muted']).pack(anchor='w',pady=(4,0))
        self.bind('<Enter>',lambda e:self.pause());self.bind('<Leave>',lambda e:self.resume())
        self.bind('<Destroy>',self.dispose,add='+')
        self._remaining=TOAST_ACTION_DURATION if action else TOAST_DURATION
        self.deiconify();self.resume()

    def perform(self,callback):
        self.close();callback()

    def pause(self):
        if self._timer:
            self.after_cancel(self._timer);self._timer=None
            self._remaining=max(1,round((self._deadline-time.monotonic())*1000))

    def resume(self):
        if self._timer:return
        self._deadline=time.monotonic()+self._remaining/1000
        self._timer=self.after(self._remaining,self.close)

    def dispose(self,event):
        if event.widget is self:
            if self._timer:self.after_cancel(self._timer);self._timer=None
            if self in self.manager.toasts:self.manager.toasts.remove(self);self.manager.reflow()

    def close(self):
        self.destroy()


class ToastManager:
    def __init__(self,owner,palette,windows_notify=None):
        self.owner=owner;self.p=palette;self.windows_notify=windows_notify;self.toasts=[]
        self._configure=owner.bind('<Configure>',lambda e:self.reflow() if e.widget is owner else None,add='+')
        self._destroy=owner.bind('<Destroy>',lambda e:self.close() if e.widget is owner else None,add='+')

    def show(self,title,message,action=None):
        if self.owner.state()=='iconic':
            if self.windows_notify:self.windows_notify(title,message)
            return None
        while len(self.toasts)>=TOAST_LIMIT:self.toasts[0].close()
        toast=Toast(self,title,message,action);self.toasts.append(toast);self.reflow();return toast

    def reflow(self):
        if not self.owner.winfo_exists():return
        bottom=self.owner.winfo_rooty()+self.owner.winfo_height()-16
        right=self.owner.winfo_rootx()+self.owner.winfo_width()-16
        for toast in reversed(self.toasts):
            toast.update_idletasks();w=max(320,toast.winfo_reqwidth());h=toast.winfo_reqheight()
            bottom-=h;toast.geometry(f'{w}x{h}+{max(0,right-w)}+{max(0,bottom)}');bottom-=8

    def close(self):
        for toast in list(self.toasts):toast.close()
        if self.owner.winfo_exists():
            self.owner.unbind('<Configure>',self._configure);self.owner.unbind('<Destroy>',self._destroy)


class Tooltip:
    def __init__(self,widget,text,palette):
        self.widget=widget;self.text=text;self.p=palette;self.window=None;self.timer=None
        widget.bind('<Enter>',self.schedule,add='+');widget.bind('<Leave>',self.hide,add='+')
        widget.bind('<FocusIn>',self.schedule,add='+');widget.bind('<FocusOut>',self.hide,add='+')
        widget.bind('<Destroy>',self.hide,add='+')

    def schedule(self,event=None):
        self.hide();self.timer=self.widget.after(500,self.show)

    def show(self):
        self.timer=None;self.window=tk.Toplevel(self.widget);self.window.overrideredirect(True)
        tk.Label(self.window,text=self.text,bg=self.p['toast'],fg=self.p['toast_text'],font=('Inter',-12),padx=8,pady=6).pack()
        self.window.geometry(f'+{self.widget.winfo_rootx()}+{self.widget.winfo_rooty()+self.widget.winfo_height()+4}')

    def hide(self,event=None):
        if self.timer:self.widget.after_cancel(self.timer);self.timer=None
        if self.window:self.window.destroy();self.window=None
