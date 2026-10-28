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
    def text(x,y,value,size=13,fill=None,bold=False,limit=None):
        value=str(value);weight='SemiBold' if bold else 'Regular'
        if limit is not None:value=ellipsize(value,max(0,limit),size,weight)
        draw.text((round(x*s),round(y*s)),value,font=font(size*s,weight),fill=fill or p['text'],anchor='lt')
    for item,(_,y,_,row_height) in visible:
        values=app.tree.item(item,'values');record=app._visible_records.get(int(values[0]),{})
        selected=item in app.tree.selection();state=values[8];bar,bg,fg=status_colors(state,p['mode'])
        rect((2,y+5,width-3,y+row_height-5),p['accent_soft'] if selected else p['card'],p['accent'] if selected else p['line'],16)
        tile_bg,tile_fg=file_tile_colors(file_kind(record),p['mode']);rect((18,y+23,60,y+65),tile_bg,radius=10)
        ext=Path(values[1]).suffix.lstrip('.').upper()[:4] or 'FILE';text(22,y+38,ext,10,tile_fg,True,34)
        compact=width<620;limit=max(40,width-250)
        text(76,y+18,values[1],14,bold=True,limit=limit)
        text(76,y+42,subtitle(record),11,p['muted'],limit=max(20,width-270))
        action='Aç' if state=='Tamamlandı' else 'İşleniyor' if state in ('Birleştiriliyor','Dönüştürülüyor') else 'Duraklat' if state in ('İndiriliyor','Bekliyor') else 'Devam'
        ax=width-136;rect((ax,y+22,width-48,y+58),p['subtle'],radius=10);text(ax+10,y+33,action,12,p['text_2'])
        for x in (width-32,width-26,width-20):draw.ellipse(((x-1)*s,(y+39)*s,(x+1)*s,(y+41)*s),fill=p['muted'])
        left=76;right=max(left+10,width-20);rect((left,y+72,right,y+77),p['track'],radius=2)
        fraction=float(values[5].rstrip('%'))/100
        if fraction:rect((left,y+72,left+(right-left)*fraction,y+77),bar,radius=2)
        text(left,y+86,number(app,values[3])+' / '+number(app,values[2]),11,p['muted'],limit=max(30,width//2-75))
        detail=state if compact else state+' · '+number(app,values[6])+' · '+values[7]
        text(max(left,width//2),y+86,detail,11,fg,limit=width//2-20)
    return image.resize((width,height),Image.Resampling.LANCZOS)


class CardSurface(TableSurface):
    def select(self,event):
        item=self.tree.identify_row(event.y);workspace=self.app._atlas_workspace
        if item:
            box=self.tree.bbox(item);w=self.winfo_width()
            if box[1]+20<=event.y<=box[1]+62 and event.x>=w-140:
                self.tree.selection_set(item);self.tree.focus(item)
                if event.x>w-48:return workspace.context_menu(event)
                return workspace.card_action(int(self.tree.item(item,'values')[0]))
            workspace.dismissed=None
        super().select(event);workspace.update_selection()
