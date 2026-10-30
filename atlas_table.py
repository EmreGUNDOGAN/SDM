"""Atlas/Pano table image using native Treeview bounds for headers and rows."""
from pathlib import Path
from PIL import Image,ImageDraw
from ui_surface import font,ellipsize
from ui_tokens import ATLAS,SIZES,SURFACE_SCALE,status_colors,file_tile_colors
from atlas_view import file_kind,subtitle,number


def render(app,width,height,visible,head_height):
    tree=app.tree;p=app.palette;s=SURFACE_SCALE;pano=p.get('design')=='pano';yorunge=p.get('design')=='yorunge'
    image=Image.new('RGB',(width*s,height*s),p['panel'] if pano or yorunge else p['bg']);d=ImageDraw.Draw(image)
    def rect(box,fill,radius=0):
        d.rounded_rectangle(tuple(round(v*s) for v in box),radius=round(radius*s),fill=fill)
    def text(x,y,value,size=13,weight='Regular',color=None,limit=None,anchor='ls',family=None):
        family=family or ('JetBrains Mono' if yorunge else 'Inter')
        value=str(value)
        if limit is not None:value=ellipsize(value,max(0,limit),size,weight,family)
        d.text((round(x*s),round(y*s)),value,font=font(size*s,weight,family),fill=color or p['text'],anchor=anchor)
    columns=tuple(tree.cget('displaycolumns'));total=sum(tree.column(c,'width') for c in columns)
    cursor=-tree.xview()[0]*total
    for column in columns:
        cell=tree.bbox(visible[0][0],column) if visible else None
        x,cw=(cell[0],cell[2]) if cell else (cursor,tree.column(column,'width'))
        right=column in ('size','downloaded','remaining','speed','eta')
        pad=ATLAS['file_padding'] if column=='filename' else ATLAS['cell_padding']
        text(x+cw-pad if right else x+pad,head_height/2,tree.heading(column,'text'),
             12,color=p['muted'],limit=cw-2*pad,anchor='rm' if right else 'lm')
        cursor+=cw
    rect((0,head_height-1,width,head_height),p['line'])
    for item,box in visible:
        _,y,_,rh=box;values=tree.item(item,'values');selected=item in tree.selection()
        if selected:
            rect((0,y,width,y+rh),p['accent_soft'])
            rect((0,y,ATLAS['selection_mark'],y+rh),p['accent'])
        rect((0,y+rh-1,width,y+rh),p['line_soft'])
        record=getattr(app,'_visible_records',{}).get(int(values[0]),{})
        for column in columns:
            cell=tree.bbox(item,column)
            if not cell:continue
            x,_,cw,_=cell;pad=ATLAS['cell_padding']
            if column=='actions' and pano:
                for offset in (-5,0,5):
                    cx=x+cw/2+offset;cy=y+rh/2
                    d.ellipse(((cx-1.5)*s,(cy-1.5)*s,(cx+1.5)*s,(cy+1.5)*s),fill=p['muted'])
            elif column=='filename':
                if yorunge:text(x+6,y+rh/2,f'{tree.index(item)+1:02}',9,color=p['dim'],anchor='lm')
                size=34 if pano else 30 if yorunge else SIZES['file_tile'];tx=x+ATLAS['file_padding'];ty=y+(rh-size)/2
                bg,fg=file_tile_colors(file_kind(record),app.ui_theme,p.get('design','atlas'))
                if yorunge:d.rectangle((tx*s,ty*s,(tx+size)*s,(ty+size)*s),outline=fg,width=s)
                else:rect((tx,ty,tx+size,ty+size),bg,8)
                extension=Path(str(values[1])).suffix.lstrip('.').upper()[:4] or 'FILE'
                text(tx+size/2,ty+size/2,extension,9 if yorunge else 10,'Bold',fg,anchor='mm')
                if pano or yorunge:text(x+ATLAS['file_text_offset'],y+rh/2,values[1],13,'Medium',limit=cw-ATLAS['file_text_offset']-pad,anchor='lm',family='Inter')
                else:
                    text(x+ATLAS['file_text_offset'],y+ATLAS['row_title_baseline'],values[1],13,'Medium',limit=cw-ATLAS['file_text_offset']-pad)
                    text(x+ATLAS['file_text_offset'],y+ATLAS['row_subtitle_baseline'],subtitle(record),12,color=p['muted'],limit=cw-ATLAS['file_text_offset']-pad)
            elif column=='progress':
                # Leave room for '100%' and a 12 px gap; a fixed 58 px let them touch.
                value=min(1,max(0,float(str(values[5]).rstrip('%'))/100));bar=max(1,cw-2*pad-round(font(12).getlength('100%'))-12)
                yy=y+rh/2;thick=SIZES['progress']
                if yorunge:
                    cell=max(0,(bar-2*19)/20);color=status_colors(values[8],app.ui_theme,'yorunge')[0]
                    for index in range(20):
                        left=x+pad+index*(cell+2)
                        if cell:rect((left,yy-5,left+cell,yy+5),color if index<round(value*20) else p['line_soft'])
                else:
                    rect((x+pad,yy-thick/2,x+pad+bar,yy+thick/2),p['track'],thick/2)
                    if value:rect((x+pad,yy-thick/2,x+pad+bar*value,yy+thick/2),status_colors(values[8],app.ui_theme,p.get('design','atlas'))[0],min(thick/2,bar*value/2))
                text(x+cw-pad,yy,f'{value:.0%}',12,anchor='rm')
            elif column=='status':
                state=values[8];_,bg,fg=status_colors(state,app.ui_theme,p.get('design','atlas'))
                bw=min(cw-2*pad,font(12,'Medium','JetBrains Mono' if yorunge else 'Inter').getlength(state)+28);bh=SIZES['badge']
                if not pano and not yorunge:rect((x+pad,y+(rh-bh)/2,x+pad+bw,y+(rh+bh)/2),bg,bh/2)
                d.ellipse(((x+pad+8)*s,(y+rh/2-3)*s,(x+pad+14)*s,(y+rh/2+3)*s),fill=fg)
                text(x+pad+20,y+rh/2,state,12,'Medium',fg,bw-24,'lm')
            else:
                index=tuple(tree.cget('columns')).index(column);value=values[index]
                right=column in ('size','downloaded','remaining','speed','eta')
                if column in ('size','downloaded','remaining','speed'):value=number(app,value)
                text(x+cw-pad if right else x+pad,y+rh/2,value,13,limit=cw-2*pad,anchor='rm' if right else 'lm')
    if app.data_view._keyboard_focus and tree.focus_get() is tree:
        d.rectangle((s,s,(width-1)*s,(height-1)*s),outline=p['accent'],width=2*s)
    return image.resize((width,height),Image.Resampling.LANCZOS)
