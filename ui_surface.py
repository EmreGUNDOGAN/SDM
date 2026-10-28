"""Deterministic Inter typography and antialiased vector UI surfaces."""
from functools import lru_cache
from pathlib import Path
import sys
import tkinter as tk
from PIL import Image,ImageDraw,ImageFont,ImageTk
from ui_tokens import SURFACE_SCALE

ROOT=Path(getattr(sys,'_MEIPASS',Path(__file__).parent))
def register_fonts():
    if sys.platform=='win32':
        import ctypes
        for path in (ROOT/'assets/fonts').glob('*.ttf'):
            ctypes.windll.gdi32.AddFontResourceExW(str(path),0x10,0)

@lru_cache(maxsize=80)
def font(size=13,weight='Regular'):
    return ImageFont.truetype(str(ROOT/'assets/fonts'/f'Inter-{weight}.ttf'),round(size))

def photo(image,master):return ImageTk.PhotoImage(image,master=master)
@lru_cache(maxsize=96)
def _surface(w,h,bg,fill,border,radius,scale):
    image=Image.new('RGB',(max(1,w)*scale,max(1,h)*scale),bg)
    draw=ImageDraw.Draw(image)
    draw.rounded_rectangle((scale/2,scale/2,w*scale-scale/2,h*scale-scale/2),radius=radius*scale,fill=fill,outline=border,width=scale if border else 1)
    return image.resize((max(1,w),max(1,h)),Image.Resampling.LANCZOS)

def surface(w,h,bg,fill,border=None,radius=7,scale=SURFACE_SCALE):
    return _surface(max(1,round(w)),max(1,round(h)),bg,fill,border,radius,scale).copy()


def text_on(image,xy,text,size=13,weight='Regular',fill='#111827',anchor='lt'):
    """Supersample text independently of its canvas/surface (no Tk text raster)."""
    scale=SURFACE_SCALE
    layer=Image.new('RGBA',(image.width*scale,image.height*scale))
    ImageDraw.Draw(layer).text(tuple(round(v*scale) for v in xy),str(text),
                              font=font(round(size*scale),weight),fill=fill,anchor=anchor)
    layer=layer.resize(image.size,Image.Resampling.LANCZOS)
    image.paste(layer,(0,0),layer)


def ellipsize(text,width,size=13,weight='Regular'):
    face=font(size,weight)
    if face.getlength(text)<=width:return text
    if face.getlength('…')>width:return ''
    low,high=0,len(text)
    while low<high:
        mid=(low+high+1)//2
        if face.getlength(text[:mid]+'…')<=width:low=mid
        else:high=mid-1
    return text[:low]+'…'


@lru_cache(maxsize=256)
def _icon(name,size,color):
    """Native vector geometry, matching the reference's thin rounded strokes."""
    scale=4;image=Image.new('RGBA',(size*scale,size*scale));d=ImageDraw.Draw(image)
    unit=size*scale/24;stroke=max(1,round(unit*1.65))
    def line(points,closed=False):
        pts=[(x*unit,y*unit) for x,y in points]
        if closed:pts.append(pts[0])
        d.line(pts,fill=color,width=stroke,joint='curve')
        for x,y in (pts[0],pts[-1]):d.ellipse((x-stroke/2,y-stroke/2,x+stroke/2,y+stroke/2),fill=color)
    def box(x,y,w,h,r=2):d.rounded_rectangle((x*unit,y*unit,(x+w)*unit,(y+h)*unit),radius=r*unit,outline=color,width=stroke)
    def circle(x,y,r):d.ellipse(((x-r)*unit,(y-r)*unit,(x+r)*unit,(y+r)*unit),outline=color,width=stroke)
    if name=='plus':line([(12,5),(12,19)]);line([(5,12),(19,12)])
    elif name=='play':line([(7,4),(19,12),(7,20)],True)
    elif name=='pause':line([(8,5),(8,19)]);line([(16,5),(16,19)])
    elif name=='x':line([(6,6),(18,18)]);line([(6,18),(18,6)])
    elif name=='chevron':line([(6,9),(12,15),(18,9)])
    elif name=='trash':line([(4,6),(20,6)]);box(7,6,10,15);line([(10,3),(14,3)]);line([(10,10),(10,17)]);line([(14,10),(14,17)])
    elif name=='folder':line([(3,8),(3,20),(21,20),(21,7),(11,7),(9,4),(3,4),(3,8)])
    elif name=='file':line([(5,3),(14,3),(19,8),(19,21),(5,21)],True);line([(14,3),(14,8),(19,8)]);line([(8,12),(16,12)]);line([(8,16),(14,16)])
    elif name=='image':box(3,3,18,18);circle(8,8,1.3);line([(3,17),(10,11),(14,15),(17,12),(21,16)])
    elif name=='music':line([(10,17),(10,6),(20,4),(20,15)]);line([(10,9),(20,7)]);circle(6.5,18,3);circle(16.5,16,3)
    elif name=='archive':box(4,8,16,13);box(3,3,18,5,1);line([(10,12),(14,12)])
    elif name=='program':box(4,7,16,14);line([(8,7),(8,3),(16,3),(16,7)])
    elif name=='download':line([(12,3),(12,16)]);line([(7,11),(12,16),(17,11)]);line([(4,16),(4,21),(20,21),(20,16)])
    elif name=='speed':d.arc((3*unit,3*unit,21*unit,21*unit),180,360,fill=color,width=stroke);line([(4,16),(4,18),(20,18),(20,16)]);line([(12,13),(17,7)]);circle(12,13,1.5)
    elif name=='database':d.ellipse((4*unit,3*unit,20*unit,9*unit),outline=color,width=stroke);line([(4,6),(4,19)]);line([(20,6),(20,19)]);d.arc((4*unit,13*unit,20*unit,22*unit),0,180,fill=color,width=stroke);d.arc((4*unit,7*unit,20*unit,16*unit),0,180,fill=color,width=stroke)
    elif name=='columns':box(3,4,18,16);line([(9,4),(9,20)]);line([(15,4),(15,20)])
    elif name=='search':circle(10,10,6);line([(15,15),(21,21)])
    elif name=='check':circle(12,12,9);line([(7,12),(11,16),(17,9)])
    elif name=='more':
        for x in (5,12,19):d.ellipse(((x-1)*unit,11*unit,(x+1)*unit,13*unit),fill=color)
    elif name=='monitor':box(3,3,18,14);line([(12,17),(12,21)]);line([(8,21),(16,21)])
    elif name=='moon':
        d.arc((3*unit,3*unit,21*unit,21*unit),45,290,fill=color,width=stroke);d.arc((9*unit,-3*unit,27*unit,15*unit),60,190,fill=color,width=stroke)
    elif name=='sun':
        import math
        circle(12,12,4)
        for angle in range(0,360,45):
            a=math.radians(angle);line([(12+7*math.cos(a),12+7*math.sin(a)),(12+10*math.cos(a),12+10*math.sin(a))])
    elif name=='wrench':line([(15,3),(13,7),(17,11),(21,9),(21,14),(17,16),(14,15),(7,22),(3,18),(10,11),(9,8),(10,4),(15,3)])
    elif name=='settings':
        import math
        points=[]
        for index in range(24):
            radius=9 if index%4 in (1,2) else 7
            angle=index*math.pi/12;points.append((12+radius*math.cos(angle),12+radius*math.sin(angle)))
        line(points,True);circle(12,12,3)
    elif name=='queue':
        for y in (6,12,18):line([(5,y),(20,y)])
    elif name=='copy':box(8,8,13,13);line([(16,8),(16,3),(3,3),(3,16),(8,16)])
    elif name=='clipboard':box(5,4,14,17);box(9,2,6,4,1)
    elif name in ('shield','shield-check'):
        line([(12,2),(21,6),(20,14),(17,19),(12,22),(7,19),(4,14),(3,6),(12,2)])
        if name=='shield-check':line([(7,12),(10,15),(17,8)])
    elif name=='globe':
        circle(12,12,9);line([(3,12),(21,12)]);d.ellipse((8*unit,3*unit,16*unit,21*unit),outline=color,width=stroke)
    elif name=='scissors':
        circle(6,6,3);circle(6,18,3);line([(8,8),(21,21)]);line([(8,16),(21,3)])
    elif name=='video':box(3,5,13,14);line([(16,9),(22,6),(22,18),(16,15)])
    elif name=='refresh':
        d.arc((3*unit,3*unit,21*unit,21*unit),-60,240,fill=color,width=stroke)
        line([(21,3),(21,9),(15,9)])
    elif name=='upload':
        line([(12,17),(12,3)]);line([(7,8),(12,3),(17,8)]);line([(4,17),(4,21),(20,21),(20,17)])
    elif name=='arrow-right':line([(3,12),(21,12)]);line([(15,6),(21,12),(15,18)])
    elif name in ('info','alert-circle'):
        circle(12,12,9)
        line([(12,11),(12,17)] if name=='info' else [(12,6),(12,12)])
        y=7 if name=='info' else 17;d.ellipse((11*unit,(y-1)*unit,13*unit,(y+1)*unit),fill=color)
    elif name=='chevron-up':line([(6,15),(12,9),(18,15)])
    elif name=='check-small':line([(5,12),(10,17),(19,6)])
    elif name=='play-circle':circle(12,12,9);line([(10,8),(16,12),(10,16)],True)
    else:circle(12,12,9);line([(12,6),(12,12),(16,14)])
    return image.resize((size,size),Image.Resampling.LANCZOS)


def icon(name,size,color):
    return _icon(name,size,color).copy()


NEW_ICON_NAMES=('copy','clipboard','shield','shield-check','globe','scissors','video',
                'refresh','upload','arrow-right','info','alert-circle','chevron-up',
                'check-small','play-circle')

ICON_NAMES=['plus','play','pause','x','trash','settings','columns','folder','file','image','music','play','archive','program','clock','check','speed','database']

class TextLabel(tk.Canvas):
    def __init__(self,parent,text='',textvariable=None,size=13,weight='Regular',fg='#172331',**kwargs):
        self.text=text;self.var=textvariable;self.size=size;self.weight=weight;self.fg=fg
        super().__init__(parent,bg=parent.cget('bg'),highlightthickness=0,height=size+6)
        self._trace=textvariable.trace_add('write',lambda *args:self.draw()) if textvariable is not None else None
        self.bind('<Configure>',lambda e:self.draw());self.bind('<Destroy>',self.dispose);self.draw()
    def dispose(self,event):
        if event.widget is self and self._trace:
            try:self.var.trace_remove('write',self._trace)
            except tk.TclError:pass
            self._trace=None
    def configure(self,cnf=None,**kwargs):
        if 'text' in kwargs:self.text=kwargs.pop('text')
        for key in ('foreground','fg'):
            if key in kwargs:self.fg=kwargs.pop(key)
        result=super().configure(cnf,**kwargs);self.draw();return result
    config=configure
    def draw(self):
        text=self.var.get() if self.var is not None else self.text
        face=font(self.size,self.weight);w=max(1,round(face.getlength(text))+2);h=self.size+7
        super().configure(width=w,height=h)
        image=Image.new('RGB',(w*3,h*3),self.cget('bg'));d=ImageDraw.Draw(image);d.text((0,2*3),text,font=font(self.size*3,self.weight),fill=self.fg,anchor='lt')
        self._image=photo(image.resize((w,h),Image.Resampling.LANCZOS),self);self.delete('all');self.create_image(0,0,image=self._image,anchor='nw')
