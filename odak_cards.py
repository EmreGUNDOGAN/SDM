"""B01 cards use native row positions and stable Treeview selection/scroll."""
from pathlib import Path
from PIL import Image,ImageDraw
from ui_surface import font,icon,ellipsize
from ui_tokens import SURFACE_SCALE,status_colors,file_tile_colors
from atlas_view import file_kind,subtitle,number
from ui_table_surface import TableSurface


def render(app,width,height,visible,head_height=0):
    p=app.palette;s=SURFACE_SCALE;image=Image.new('RGB',(width*s,height*s),p['bg']);draw=ImageDraw.Draw(image)
    def rect(box,fill,edge=None,radius=0):draw.rounded_rectangle(tuple(round(n*s) for n in box),radius=radius*s,fill=fill,outline=edge,width=s)
    def text(x,y,value,size=13,fill=None,bold=False,limit=None,anchor='ls'):
        # Baseline ('ls') or centre anchors: ink-top placement moved each word by its letters.
        value=str(value);weight='SemiBold' if bold else 'Regular'
        if limit is not None:value=ellipsize(value,max(0,limit),size,weight)
        draw.text((round(x*s),round(y*s)),value,font=font(size*s,weight),fill=fill or p['text'],anchor=anchor)
    for item,(_,y,_,row_height) in visible:
        values=app.tree.item(item,'values');record=app._visible_records.get(int(values[0]),{})
        selected=item in app.tree.selection();state=values[8];bar,bg,fg=status_colors(state,p['mode'])
        # B01 card: tile | name · site over a thin bar and the numbers | action, ⋯.
        rect((2,y+5,width-3,y+row_height-5),p['accent_soft'] if selected else p['card'],p['accent'] if selected else p['line'],12)
        middle=y+row_height/2
        tile_bg,tile_fg=file_tile_colors(file_kind(record),p['mode']);rect((16,middle-20,56,middle+20),tile_bg,radius=10)
        ext=Path(values[1]).suffix.lstrip('.').upper()[:4] or 'FILE';text(36,middle,ext,10,tile_fg,True,34,'mm')
        left=72;right=max(left+10,width-112)
        status_width=round(font(12,'SemiBold').getlength(state))
        name_width=min(round(font(14,'SemiBold').getlength(values[1])),max(40,(right-left-status_width-16)*2//3))
        text(left,middle-11,values[1],14,bold=True,limit=name_width)
        text(left+name_width+10,middle-11,subtitle(record),12,p['muted'],limit=max(0,right-left-name_width-status_width-26))
        text(right,middle-11,state,12,fg,True,anchor='rs')
        rect((left,middle-3,right,middle),p['track'],radius=1.5)
        fraction=float(values[5].rstrip('%'))/100
        if fraction:rect((left,middle-3,left+(right-left)*fraction,middle),bar,radius=1.5)
        numbers=number(app,values[3])+' / '+number(app,values[2])
        if state=='İndiriliyor':numbers+='    '+number(app,values[6])+'    '+values[7]
        text(left,middle+19,numbers,12,p['muted'],limit=right-left)
        glyph='file' if state=='Tamamlandı' else 'clock' if state in ('Birleştiriliyor','Dönüştürülüyor') else 'pause' if state in ('İndiriliyor','Bekliyor') else 'play'
        ax=width-92;rect((ax,middle-18,ax+36,middle+18),p['subtle'],p['line'],8)
        mark=icon(glyph,16*s,p['text_2']);image.paste(mark,(round((ax+10)*s),round((middle-8)*s)),mark)
        for x in (width-38,width-32,width-26):draw.ellipse(((x-1)*s,(middle-1)*s,(x+1)*s,(middle+1)*s),fill=p['muted'])
    return image.resize((width,height),Image.Resampling.LANCZOS)


class CardSurface(TableSurface):
    def select(self,event):
        item=self.tree.identify_row(event.y);workspace=self.app._atlas_workspace
        if item:
            box=self.tree.bbox(item);w=self.winfo_width()
            middle=box[1]+box[3]/2
            if middle-18<=event.y<=middle+18 and event.x>=w-92:
                self.tree.selection_set(item);self.tree.focus(item)
                if event.x>w-52:return workspace.context_menu(event)
                return workspace.card_action(int(self.tree.item(item,'values')[0]))
            workspace.dismissed=None
        super().select(event);workspace.update_selection()
