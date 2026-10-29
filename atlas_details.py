"""A01's selection panel; all values come from the selected real records/tasks."""
from pathlib import Path
import tkinter as tk
from PIL import Image,ImageDraw
from theme_widgets import Button
from ui_surface import font,photo,ellipsize
from ui_tokens import SIZES,ATLAS,SURFACE_SCALE,file_tile_colors,status_colors
from atlas_view import domain,file_kind,number,observed_parts,available_actions


class AtlasDetails(tk.Frame):
    def __init__(self,master,app):
        self.app=app;self.p=app.palette;self.records=[];self.values=[];self.snapshot={};self._signature=None
        super().__init__(master,bg=self.p['dialog'],width=SIZES['detail_panel'])
        self.pack_propagate(False)
        tk.Frame(self,bg=self.p['line'],width=1).pack(side='left',fill='y')
        self.canvas=tk.Canvas(self,bg=self.p['dialog'],highlightthickness=0)
        self.canvas.pack(fill='both',expand=True)
        self.canvas.bind('<Configure>',lambda e:self.draw())
        footer=tk.Frame(self,bg=self.p['dialog']);footer.pack(fill='x',padx=ATLAS['detail_padding'],pady=ATLAS['detail_padding'])
        self.primary=Button(footer,'Duraklat',palette=self.p,width=128,command=app.pause_selected)
        self.primary.pack(side='left')
        self.secondary=Button(footer,'Hız grafiği',palette=self.p,width=128,command=app.show_speed_graph)
        self.secondary.pack(side='right')

    def sync(self,records,values):
        self.records=records;self.values=values
        actions=available_actions(value[8] for value in values)
        pause=actions['pause']
        self.primary.command=self.app.pause_selected if pause else self.app.resume_selected
        self.primary.configure(text='Duraklat' if pause else 'Devam et',state='normal' if pause or actions['resume'] else 'disabled')
        multi=len(records)>1
        self.secondary.command=self.app.cancel_selected if multi else self.app.show_speed_graph
        self.secondary.configure(text='İptal et' if multi else 'Hız grafiği',state='normal' if (actions['cancel'] if multi else actions['graph']) else 'disabled')
        self.draw()

    def draw(self):
        if not self.records or not self.winfo_exists():return
        app=self.app;p=self.p;s=SURFACE_SCALE
        w=max(1,self.canvas.winfo_width());h=max(1,self.canvas.winfo_height())
        if w<=2*ATLAS['detail_padding'] or h<=1:return
        record=self.records[0];values=self.values[0];multi=len(self.records)>1
        rows,active=observed_parts(app,record) if not multi else ((),None)
        received=sum(int(r['downloaded_bytes']) for r in self.records)
        total=sum(int(r['filesize']) for r in self.records)
        known=all(r['filesize']>0 for r in self.records)
        if not multi:
            task=app.video_tasks.get(record['id']) or app.engine.get_task(record['id'])
            if task:
                received=getattr(task,'downloaded_bytes',None)
                if received is None:received=sum(part.downloaded_bytes for part in getattr(task,'segments',()))
                total=getattr(task,'total_bytes',getattr(task,'filesize',total)) or total
                known=total>0
        value=min(1,received/total) if known else None
        if not multi and values[8]=='Tamamlandı':value=1
        title=f'{len(self.records)} öğe seçili' if multi else record['filename']
        from utils import format_bytes
        amount=number(app,format_bytes(received))+' / '+(number(app,format_bytes(total)) if known else 'Bilinmiyor')
        fields=[('Hız',number(app,values[6]) if not multi else '—'),
            ('Kalan süre',values[7] if not multi else '—'),
            ('Kuyruk',record.get('queue_name','Ana kuyruk') if not multi else 'Toplu seçim'),
            ('Klasör',str(Path(record['filepath']).parent) if not multi else 'Birden fazla öğe'),
            ('Eklendi',record.get('date_added','—') if not multi else '—')]
        signature=(w,h,title,amount,value,tuple(fields),tuple(tuple(sorted(r.items())) for r in rows),active,values[8])
        if signature==self._signature:return
        self._signature=signature
        self.snapshot=dict(title=title,received=received,total=total if known else None,
                           progress=value,rows=rows,active_count=active,fields=dict(fields))
        image=Image.new('RGB',(w*s,h*s),p['dialog']);d=ImageDraw.Draw(image);pad=ATLAS['detail_padding']
        def text(x,y,value,size=13,weight='Regular',color=None,limit=None,anchor='lt'):
            value=str(value)
            if limit is not None:value=ellipsize(value,max(0,limit),size,weight)
            d.text((round(x*s),round(y*s)),value,font=font(size*s,weight),fill=color or p['text'],anchor=anchor)
        def rect(box,fill,radius=0):d.rounded_rectangle(tuple(round(v*s) for v in box),radius=round(radius*s),fill=fill)
        tile=ATLAS['detail_tile'];bg,fg=file_tile_colors(file_kind(record),app.ui_theme)
        rect((pad,pad,pad+tile,pad+tile),bg,8)
        text(pad+tile/2,pad+tile/2,'Σ' if multi else Path(record['filename']).suffix.lstrip('.').upper()[:4] or 'FILE',10,'Bold',fg,anchor='mm')
        available=w-2*pad-tile-12;cut=ellipsize(title,available,14,'SemiBold')
        text(pad+tile+12,pad,title if cut==title else cut,14,'SemiBold',limit=available)
        rest=title[len(cut.rstrip('…')):] if cut!=title else ''
        text(pad+tile+12,pad+20,rest or domain(record),12,color=p['muted'],limit=available)
        y=pad+tile+ATLAS['detail_gap']
        text(pad,y,'—' if value is None else f'{value:.0%}',28,'Bold')
        text(w-pad,y+14,amount,12,color=p['muted'],limit=w-2*pad-70,anchor='rm')
        y+=38;track=w-2*pad;thickness=SIZES['detail_progress']
        rect((pad,y,w-pad,y+thickness),p['track'],thickness/2)
        if value:rect((pad,y,pad+track*value,y+thickness),status_colors(values[8],app.ui_theme)[0],min(thickness/2,track*value/2))
        y+=28
        text(pad,y,'Toplu eylemler' if multi else 'Bağlantılar · '+('Henüz ölçülmedi' if active is None else str(active)+' aktif'),12,color=p['muted'])
        y+=22
        if rows:
            cell=track/len(rows);gap=min(3,cell/3)
            for index,row in enumerate(rows):
                x=pad+index*cell;cw=cell-gap;ratio=min(1,row['received']/row['total']) if row['total'] else 0
                rect((x,y,x+cw,y+28),p['track'],min(3,cw/2))
                if ratio:rect((x,y+28*(1-ratio),x+cw,y+28),p['success'] if row['state']=='Tamamlandı' else p['accent'],min(3,cw/2))
            y+=46
        else:y+=16
        for label,value_text in fields:
            text(pad,y,label,13,color=p['muted'])
            text(w-pad,y,value_text,13,limit=w-2*pad-92,anchor='rt');y+=24
        self._image=photo(image.resize((w,h),Image.Resampling.LANCZOS),self.canvas)
        self.canvas.delete('all');self.canvas.create_image(0,0,image=self._image,anchor='nw')
