"""Reference-styled table renderer retaining the native Treeview data/selection API."""
import tkinter as tk
from ui_surface import photo

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
        column=self.tree.identify_column(event.x)
        if item and self.app.theme_family=='pano' and column and self.tree.column(column,'id')=='actions':
            if item not in self.tree.selection():self.tree.selection_set(item)
            self.tree.focus(item);self.app._on_tree_right_click(event);self.schedule();return
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
        # Mid-layout the surface can be a few pixels wide; card/row boxes would invert.
        # The next <Configure> repaints at the real size.
        if w<32 or h<32:return
        columns=list(tree.cget('displaycolumns'));head_h=40
        visible=[(item,tree.bbox(item)) for item in tree.get_children() if tree.bbox(item)]
        if visible:head_h=visible[0][1][1] if visible[0][1][1]<70 else 40
        if app.theme_family in ('atlas','odak','pano'):
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
