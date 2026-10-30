"""Antialiased, data-only indicators shared by dialogs, panels and card rows."""
import math
import tkinter as tk
from PIL import Image, ImageDraw
from ui_surface import surface, photo, icon, text_on, ellipsize, font
from theme_widgets import background
from ui_tokens import SIZES, RADII, SURFACE_SCALE, status_colors, file_tile_colors


def fraction(value):
    if value is None:return None
    number=float(value)
    if not math.isfinite(number):raise ValueError('Progress must be finite')
    return max(0.0,min(1.0,number))


class Indicator(tk.Canvas):
    def __init__(self,master,palette,width=160,height=32,**kwargs):
        self.p=palette;self._signature=None
        super().__init__(master,width=width,height=height,bg=background(master,palette),
                         highlightthickness=0,**kwargs)
        self.bind('<Configure>',lambda e:self.draw())

    def size(self):
        return (self.winfo_width() if self.winfo_width()>1 else int(self.cget('width')),
                self.winfo_height() if self.winfo_height()>1 else int(self.cget('height')))

    def present(self,image):
        self._image=photo(image,self);self.delete('all');self.create_image(0,0,image=self._image,anchor='nw')


class StatusBadge(Indicator):
    def __init__(self,master,status,palette,**kwargs):
        # Without a width the badge hugs its text, so a header badge keeps its edge.
        self.status=status;self.fit='width' not in kwargs
        super().__init__(master,palette,height=SIZES['badge'],width=kwargs.pop('width',self.fitted(status)),**kwargs);self.draw()

    @staticmethod
    def fitted(status):return round(font(12,'Medium').getlength(status))+35

    def set(self,status):
        if self.status!=status:
            self.status=status
            if self.fit:self.configure(width=self.fitted(status))
            self.draw()

    def draw(self):
        w,h=self.size();p=self.p
        _,bg,fg=status_colors(self.status,p.get('mode','light'),p.get('design','atlas'))
        image=surface(w,h,self.cget('bg'),bg,radius=h/2)
        d=ImageDraw.Draw(image);d.ellipse((10,h//2-3,16,h//2+3),fill=fg)
        text_on(image,(23,h/2),ellipsize(self.status,w-29,12),12,'Medium',fg,'lm')
        self.present(image)


class FileTile(Indicator):
    def __init__(self,master,extension,kind='other',palette=None,size=None,**kwargs):
        self.extension=extension.upper()[:4];self.kind=kind;size=size or SIZES['file_tile']
        super().__init__(master,palette,width=size,height=size,**kwargs);self.draw()

    def draw(self):
        w,h=self.size();bg,fg=file_tile_colors(self.kind,self.p.get('mode','light'),self.p.get('design','atlas'))
        image=surface(w,h,self.cget('bg'),bg,fg if self.p.get('design')=='yorunge' else None,radius=RADII[self.p.get('design','atlas')]['tile'])
        text_on(image,(w/2,h/2),self.extension,10,'Bold',fg,'mm');self.present(image)


class ProgressBar(Indicator):
    def __init__(self,master,palette,value=0,status='İndiriliyor',show_text=True,thickness=None,**kwargs):
        self.value=fraction(value);self.status=status;self.show_text=show_text
        self.thickness=thickness or SIZES['progress']
        super().__init__(master,palette,**kwargs);self.draw()

    def set(self,value,status=None):
        value=fraction(value);status=status or self.status
        if (value,status)!=(self.value,self.status):self.value=value;self.status=status;self.draw()

    def draw(self):
        w,h=self.size();p=self.p;scale=SURFACE_SCALE
        image=Image.new('RGB',(w*scale,h*scale),self.cget('bg'));d=ImageDraw.Draw(image)
        bar=max(1,w-(46 if self.show_text else 0));y=(h-self.thickness)//2
        if p.get('design')=='yorunge':
            cells=20;gap=2;cell=max(0,(bar-gap*(cells-1))/cells)
            filled=round((self.value or 0)*cells)
            color=status_colors(self.status,p.get('mode','dark'),'yorunge')[0]
            for index in range(cells):
                x=index*(cell+gap)
                if cell>0:d.rectangle((x*scale,y*scale,(x+cell)*scale,(y+self.thickness)*scale),fill=color if index<filled else p['track'])
            image=image.resize((w,h),Image.Resampling.LANCZOS)
            if self.show_text:text_on(image,(w,h/2),'—' if self.value is None else f'{self.value:.0%}',12,fill=p['text'],anchor='rm',family='JetBrains Mono')
            self.present(image);return
        d.rounded_rectangle((0,y*scale,bar*scale,(y+self.thickness)*scale),radius=self.thickness*scale/2,fill=p['track'])
        value=self.value
        if value:
            color=status_colors(self.status,p.get('mode','light'),p.get('design','atlas'))[0]
            d.rounded_rectangle((0,y*scale,max(1,bar*value)*scale,(y+self.thickness)*scale),radius=min(self.thickness/2,bar*value/2)*scale,fill=color)
        image=image.resize((w,h),Image.Resampling.LANCZOS)
        if self.show_text:text_on(image,(w,h/2),'—' if value is None else f'{value:.0%}',12,fill=p['text'],anchor='rm')
        self.present(image)


class ProgressRing(Indicator):
    def __init__(self,master,palette,value=0,size=None,stroke=None,**kwargs):
        self.value=fraction(value);self.stroke=stroke or SIZES['ring_stroke'];self._angle=0;self._timer=None
        size=size or SIZES['ring'];super().__init__(master,palette,width=size,height=size,**kwargs)
        self.bind('<Destroy>',self.dispose);self.set(value,force=True)

    def set(self,value,force=False):
        value=fraction(value)
        if force or self.value!=value:
            self.value=value
            if self._timer:self.after_cancel(self._timer);self._timer=None
            self.draw()
            if value is None:self._timer=self.after(80,self.spin)

    def spin(self):
        self._timer=None;self._angle=(self._angle+18)%360;self.draw()
        if self.value is None:self._timer=self.after(80,self.spin)

    def dispose(self,event):
        if event.widget is self and self._timer:self.after_cancel(self._timer);self._timer=None

    def draw(self):
        w,h=self.size();s=SURFACE_SCALE
        image=Image.new('RGB',(w*s,h*s),self.cget('bg'));d=ImageDraw.Draw(image)
        stroke=self.stroke*s;inset=stroke/2+s
        box=(inset,inset,w*s-inset,h*s-inset)
        d.ellipse(box,outline=self.p['track'],width=stroke)
        start=-90 if self.value is not None else self._angle
        extent=360*self.value if self.value is not None else 90
        if extent>0:
            d.arc(box,start,start+extent,fill=self.p['accent'],width=stroke)
            radius=(min(w,h)*s-stroke-2*s)/2
            for angle in (start,start+extent):
                a=math.radians(angle);x=w*s/2+radius*math.cos(a);y=h*s/2+radius*math.sin(a)
                d.ellipse((x-stroke/2,y-stroke/2,x+stroke/2,y+stroke/2),fill=self.p['accent'])
        image=image.resize((w,h),Image.Resampling.LANCZOS)
        if self.value is not None:
            compact=min(w,h)<96
            text_on(image,(w/2,h/2-(0 if compact else 5)),f'{self.value:.0%}',
                    min(28,round(min(w,h)*0.23)),'Bold',self.p['text'],'mm')
            if not compact:text_on(image,(w/2,h/2+22),'tamamlandı',11,fill=self.p['muted'],anchor='mm')
        self.present(image)


class SpeedChart(Indicator):
    """Timestamps/bytes-per-second only; caller supplies SpeedHistory samples."""
    def __init__(self,master,palette,points=(),average=None,axes=True,formatter=None,**kwargs):
        self.points=tuple(points);self.average=average;self.axes=axes;self.formatter=formatter or (lambda value:value)
        super().__init__(master,palette,height=kwargs.pop('height',160),**kwargs);self.draw()

    def set(self,points,average=None):
        points=tuple(points)
        if (points,average)!=(self.points,self.average):self.points=points;self.average=average;self.draw()

    def draw(self):
        w,h=self.size();s=SURFACE_SCALE;p=self.p
        image=Image.new('RGB',(w*s,h*s),self.cget('bg'));d=ImageDraw.Draw(image)
        left,bottom=(40,22) if self.axes else (0,0);top=8 if self.axes else 1
        right=max(left+1,w-4);base=max(top+1,h-bottom);span_y=base-top
        peak=max(1,*[max(0,value) for _,value in self.points],self.average or 0)
        if self.axes:
            for step in range(4):
                y=base-span_y*step/3
                d.line((left*s,y*s,right*s,y*s),fill=p['line_soft'],width=s)
        if len(self.points)>1:
            first=self.points[0][0];duration=max(1,self.points[-1][0]-first)
            coords=[((left+(stamp-first)/duration*(right-left))*s,(base-max(0,value)/peak*span_y)*s) for stamp,value in self.points]
            if self.axes:
                tint=Image.new('RGBA',image.size);td=ImageDraw.Draw(tint)
                td.polygon([(left*s,base*s),*coords,(right*s,base*s)],fill=p['accent']+'20')
                image.paste(tint,(0,0),tint);d=ImageDraw.Draw(image)
            d.line(coords,fill=p['accent'],width=2*s,joint='curve')
        if self.average is not None and self.axes:
            y=(base-max(0,self.average)/peak*span_y)*s
            for x in range(left*s,right*s,8*s):d.line((x,y,min(x+4*s,right*s),y),fill=p['muted'],width=s)
        image=image.resize((w,h),Image.Resampling.LANCZOS)
        if self.axes:
            precision=2 if peak<1048576 else 1
            for step in range(4):text_on(image,(left-6,base-span_y*step/3),self.formatter(f'{peak*step/3/1048576:.{precision}f}'),11,fill=p['muted'],anchor='rm')
            text_on(image,(left,h-12),'MB/sn',11,fill=p['muted'])
            text_on(image,(right,h-12),'şimdi',11,fill=p['muted'],anchor='rt')
        self.present(image)


class Sparkline(SpeedChart):
    def __init__(self,master,palette,**kwargs):
        super().__init__(master,palette,axes=False,width=kwargs.pop('width',60),height=kwargs.pop('height',16),**kwargs)


class PartMap(Indicator):
    """rows: (label, metadata, iterable of 0..1 fractions); no engine dependency."""
    def __init__(self,master,palette,rows=(),**kwargs):
        self.rows=tuple((a,b,tuple(values)) for a,b,values in rows)
        super().__init__(master,palette,height=kwargs.pop('height',92),**kwargs);self.draw()

    def set(self,rows):
        rows=tuple((a,b,tuple(values)) for a,b,values in rows)
        if rows!=self.rows:self.rows=rows;self.draw()

    def draw(self):
        w,h=self.size();s=SURFACE_SCALE;p=self.p
        image=Image.new('RGB',(w*s,h*s),self.cget('bg'));d=ImageDraw.Draw(image)
        row_h=max(1,h/max(1,len(self.rows)));labels=[]
        for index,(label,metadata,parts) in enumerate(self.rows):
            y=index*row_h+4;left=min(134,w//3);right=max(left+1,w-38)
            cell=(right-left)/max(1,len(parts));gap=min(3,cell/3)
            for j,value in enumerate(parts):
                value=fraction(value) or 0;x=left+j*cell;cw=max(1,cell-gap)
                d.rounded_rectangle((x*s,y*s,(x+cw)*s,(y+22)*s),radius=3*s,fill=p['track'])
                if value:d.rounded_rectangle((x*s,y*s,(x+cw*value)*s,(y+22)*s),radius=min(3,cw*value/2)*s,fill=p['accent'])
            labels.append((y,label,metadata,sum(parts)/len(parts) if parts and all(value is not None for value in parts) else None))
        image=image.resize((w,h),Image.Resampling.LANCZOS)
        for y,label,metadata,value in labels:
            text_on(image,(0,y),ellipsize(label,min(124,w//3-8)),fill=p['text'])
            text_on(image,(0,y+17),ellipsize(metadata,min(124,w//3-8),11),11,fill=p['muted'])
            text_on(image,(w,y+11),'—' if value is None else f'{value:.0%}',12,fill=p['text'],anchor='rm')
        self.present(image)


class Summary(tk.Frame):
    def __init__(self,master,label,variable,palette):
        super().__init__(master,bg=palette['card'])
        from ui_surface import TextLabel
        TextLabel(self,label,size=12,fg=palette['muted']).pack(anchor='w',padx=12,pady=(10,4))
        TextLabel(self,textvariable=variable,size=17,weight='SemiBold',fg=palette['text']).pack(anchor='w',padx=12,pady=(0,10))


class SectionTimeline(Indicator):
    """Keyboard or drag selection. Clock fields can call set_range and on_change."""
    def __init__(self,master,palette,duration,start=0,end=None,command=None,**kwargs):
        if not math.isfinite(duration) or duration<=0:raise ValueError('Known positive duration required')
        self.duration=duration;self.start=start;self.end=duration if end is None else end
        self.command=command;self.active='start';self.dragging=False
        from video_section import validate_section
        validate_section(dict(start=self.start,end=self.end),duration)
        super().__init__(master,palette,height=76,takefocus=1,**kwargs)
        self.bind('<ButtonPress-1>',self.press);self.bind('<B1-Motion>',self.drag)
        self.bind('<ButtonRelease-1>',lambda e:setattr(self,'dragging',False))
        self.bind('<Left>',lambda e:self.nudge(-1));self.bind('<Right>',lambda e:self.nudge(1))
        self.bind('<Up>',lambda e:self.choose_handle('start'));self.bind('<Down>',lambda e:self.choose_handle('end'))
        self.bind('<FocusIn>',lambda e:self.draw());self.bind('<FocusOut>',lambda e:self.draw());self.draw()

    def choose_handle(self,value):
        self.active=value;self.draw();return 'break'

    def set_range(self,start,end,notify=False):
        from video_section import validate_section
        validate_section(dict(start=start,end=end),self.duration)
        self.start,self.end=start,end;self.draw()
        if notify and self.command:self.command(start,end)

    def press(self,event):
        self.focus_set();self.dragging=True
        w,_=self.size();value=max(0,min(1,(event.x-10)/max(1,w-20)))*self.duration
        self.active='start' if abs(value-self.start)<=abs(value-self.end) else 'end';self.drag(event)

    def drag(self,event):
        if not self.dragging:return
        w,_=self.size();value=round(max(0,min(1,(event.x-10)/max(1,w-20)))*self.duration,2)
        self.change(value)

    def nudge(self,step):
        self.change(getattr(self,self.active)+step);return 'break'

    def change(self,value):
        epsilon=min(1,self.duration/100)
        if self.active=='start':self.set_range(max(0,min(value,self.end-epsilon)),self.end,True)
        else:self.set_range(self.start,min(self.duration,max(value,self.start+epsilon)),True)

    def draw(self):
        w,h=self.size();p=self.p;s=SURFACE_SCALE
        image=Image.new('RGB',(w*s,h*s),self.cget('bg'));d=ImageDraw.Draw(image)
        left=10;right=w-10;y=16;th=SIZES['timeline']
        d.rounded_rectangle((left*s,y*s,right*s,(y+th)*s),radius=6*s,fill=p['track'])
        for x in range(left,right,8):d.line((x*s,y*s,x*s,(y+th)*s),fill=p['line_soft'],width=s)
        x1=left+self.start/self.duration*(right-left);x2=left+self.end/self.duration*(right-left)
        d.rectangle((x1*s,y*s,x2*s,(y+th)*s),fill=p['accent_soft'],outline=p['accent'],width=2*s)
        for key,x in (('start',x1),('end',x2)):
            d.rounded_rectangle(((x-5)*s,(y-6)*s,(x+5)*s,(y+th+6)*s),radius=4*s,fill=p['accent'])
            if self.focus_get() is self and self.active==key:
                d.rounded_rectangle(((x-8)*s,(y-9)*s,(x+8)*s,(y+th+9)*s),radius=5*s,outline=p['accent'],width=2*s)
        image=image.resize((w,h),Image.Resampling.LANCZOS)
        for step in range(5):
            seconds=round(self.duration*step/4);label=f'{seconds//60}:{seconds%60:02}'
            text_on(image,(left+(right-left)*step/4,h-12),label,11,fill=p['muted'],anchor='lm' if step==0 else 'rm' if step==4 else 'mm')
        self.present(image)
