"""Reference-styled table renderer retaining the native Treeview data/selection API."""
import tkinter as tk
from PIL import Image,ImageDraw
from ui_surface import font,photo,icon

class TableSurface(tk.Canvas):
    def __init__(self,app):
        self.app=app;self.tree=app.tree;self.pending=None
        super().__init__(self.tree,bg=app.palette['bg'],highlightthickness=0)
        self.place(x=0,y=0,relwidth=1,relheight=1)
        self.bind('<Configure>',lambda e:self.schedule())
        self.bind('<Destroy>',self.dispose)
        self.bind('<Button-1>',self.select);self.bind('<Double-1>',lambda e:(self.select(e),app.show_selected_details()))
        self.bind('<Button-3>',self.context);self.bind('<MouseWheel>',self.wheel)
        self.bind('<Shift-MouseWheel>',lambda e:(self.tree.xview_scroll(-1 if e.delta>0 else 1,'units'),self.schedule()))
        self._keyboard_focus=False;self._mouse_focus=False
        self.tree.bind('<FocusIn>',self.focus_in,add='+')
        self.tree.bind('<FocusOut>',lambda e:self.schedule(),add='+')
        self.tree.bind('<KeyPress>',self.key_pressed,add='+')
    def focus_in(self,event):
        self._keyboard_focus=not self._mouse_focus;self._mouse_focus=False;self.schedule()
    def key_pressed(self,event):self._keyboard_focus=True;self.schedule()
    def wheel(self,event):self.tree.yview_scroll(-3 if event.delta>0 else 3,'units');self.schedule();return 'break'
    def select(self,event):
        self._mouse_focus=True;self._keyboard_focus=False
        self.tree.focus_set();item=self.tree.identify_row(event.y)
        if item:
            if event.state&0x4:
                if item in self.tree.selection():self.tree.selection_remove(item)
                else:self.tree.selection_add(item)
            elif event.state&0x1 and self.tree.selection():
                rows=list(self.tree.get_children());a=rows.index(self.tree.selection()[0]);b=rows.index(item);self.tree.selection_set(rows[min(a,b):max(a,b)+1])
            else:self.tree.selection_set(item)
            self.tree.focus(item)
        elif self.tree.identify_region(event.x,event.y)=='heading':self.app.show_column_menu()
        else:self.tree.selection_remove(self.tree.selection())
        self.schedule()
    def context(self,event):
        item=self.tree.identify_row(event.y)
        if item and item not in self.tree.selection():self.select(event)
        self.app._on_tree_right_click(event)
    def schedule(self):
        if self.pending is None:self.pending=self.after_idle(self.paint)
    def dispose(self,event):
        if event.widget is self and self.pending:
            self.after_cancel(self.pending);self.pending=None
    def paint(self):
        self.pending=None
        if not self.winfo_exists():return
        app=self.app;p=app.palette;tree=self.tree;w=max(1,self.winfo_width());h=max(1,self.winfo_height())
        columns=list(tree.cget('displaycolumns'));head_h=40
        visible=[(item,tree.bbox(item)) for item in tree.get_children() if tree.bbox(item)]
        if visible:head_h=visible[0][1][1] if visible[0][1][1]<70 else 40
        if app.theme_family in ('atlas','odak'):
            signature=(w,h,head_h,tuple(columns),tuple(tree.selection()),tree.xview(),tree.yview(),
                self._keyboard_focus and tree.focus_get() is tree,
                tuple((item,box,tree.item(item,'values'),getattr(app,'_visible_records',{}).get(int(tree.item(item,'values')[0]),{})) for item,box in visible))
            if signature==getattr(self,'_atlas_signature',None):return
            self._atlas_signature=signature
            if app.theme_family=='odak':from odak_cards import render
            else:from atlas_table import render
            self._image=photo(render(app,w,h,visible,head_h),self)
            if not hasattr(self,'_atlas_item'):self._atlas_item=self.create_image(0,0,image=self._image,anchor='nw')
            else:self.itemconfigure(self._atlas_item,image=self._image)
            return
        image=Image.new('RGB',(w*2,h*2),p['bg']);draw=ImageDraw.Draw(image)
        def rect(box,fill,outline=None,radius=0):draw.rounded_rectangle(tuple(round(v*2) for v in box),radius=radius*2,fill=fill,outline=outline,width=2)
        def text(x,y,value,size=14,color=None,weight='Regular',limit=None):
            value=str(value);face=font(size*2,weight)
            if limit:
                while value and face.getlength(value)/2>limit:value=value[:-1]
            draw.text((round(x*2),round(y*2)),value,font=face,fill=color or p['text'],anchor='lt')
        draw.rectangle((0,0,w*2,head_h*2),fill=p['panel'] if app.theme_family=='atlas' else p['bg'])
        header_x=tree.column('#0','width')
        for col in columns:
            cell=tree.bbox(visible[0][0],col) if visible else None
            cx=cell[0] if cell else header_x;cw=cell[2] if cell else tree.column(col,'width')
            text(cx+8,head_h/2-6,tree.heading(col,'text'),13,p['muted'],limit=max(1,cw-16));header_x+=cw
            if app.theme_family=='atlas':draw.line(((cx+cw)*2,0,(cx+cw)*2,head_h*2),fill=p['line'],width=1)
        for item,box in visible:
            x,y,rw,rh=box;values=tree.item(item,'values');selected=item in tree.selection()
            if selected:rect((3,y+3,w-4,y+rh-3),p['selected'],p['accent'] if app.theme_family=='nova' else None,7)
            if app.theme_family=='atlas':draw.line((0,(y+rh)*2,w*2,(y+rh)*2),fill=p['line'],width=1)
            else:draw.line((10,(y+rh)*2,(w-10)*2,(y+rh)*2),fill=p['line'],width=1)
            for col in columns:
                cell=tree.bbox(item,col)
                if not cell:continue
                cx,cy,cw,ch=cell
                if app.theme_family=='atlas':draw.line(((cx+cw)*2,y*2,(cx+cw)*2,(y+rh)*2),fill=p['line'],width=1)
                if col=='filename':
                    glyph=icon('file',40,p['text']);image.paste(glyph,(round(cx*2),round((y+rh/2-10)*2)),glyph)
                    text(cx+28,y+rh/2-7,values[1],15,weight='Medium' if app.theme_family!='atlas' else 'Regular',limit=max(1,cw-32))
                elif col=='progress':
                    pct=float(values[5].rstrip('%'))/100;bar=max(12,cw-52);yy=y+rh/2
                    rect((cx+8,yy-8,cx+8+bar,yy+8),p['line'],radius=4)
                    if pct>0:rect((cx+8,yy-8,cx+8+max(2,bar*pct),yy+8),p['accent'],radius=4)
                    text(cx+bar+16,yy-7,f'{pct*100:.0f}%',13)
                elif col=='status':
                    state=values[8];done=state=='Tamamlandı';active=state=='İndiriliyor'
                    fill=('#183d2c' if app.ui_theme=='dark' else '#e5f5e8') if done else p['selected'] if active else p['panel']
                    fg=('#67cd91' if app.ui_theme=='dark' else '#198849') if done else p['accent'] if active else p['muted']
                    rect((cx+6,y+rh/2-14,cx+cw-6,y+rh/2+14),fill,radius=12)
                    draw.ellipse(((cx+13)*2,(y+rh/2-3)*2,(cx+19)*2,(y+rh/2+3)*2),fill=fg)
                    text(cx+25,y+rh/2-7,state,12,fg,limit=max(1,cw-31))
                else:
                    index=list(tree.cget('columns')).index(col);value=values[index]
                    if col in ('size','downloaded','remaining','speed') and app.settings.get('language','tr')=='tr':value=value.replace('.',',')
                    text(cx+4,y+rh/2-7,value,14,limit=max(1,cw-8))
        self._image=photo(image.resize((w,h),Image.Resampling.LANCZOS),self);self.delete('all');self.create_image(0,0,image=self._image,anchor='nw')
