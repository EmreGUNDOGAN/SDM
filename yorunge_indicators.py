"""Static Yörünge telemetry instruments, using shared indicator lifecycle."""
import math
from PIL import Image,ImageDraw,ImageFilter
from ui_indicators import Indicator
from ui_surface import text_on,font
from ui_tokens import SURFACE_SCALE
from yorunge_view import gauge_limit


class SpeedGauge(Indicator):
    def __init__(self,master,palette,formatter):
        self.speed=0;self.peak=0;self.limit=50;self.formatter=formatter
        super().__init__(master,palette,width=300,height=200);self.draw()

    def set(self,speed,peak):
        values=(max(0,speed),max(0,peak))
        if values==(self.speed,self.peak):return
        self.speed,self.peak=values;self.limit=gauge_limit(*values);self.draw()

    def draw(self):
        w,h=self.size();s=SURFACE_SCALE;p=self.p
        image=Image.new('RGB',(w*s,h*s),self.cget('bg'))
        radius=max(1,min(w/2-20,h-48));cx=w/2;cy=radius+14;stroke=10
        box=((cx-radius)*s,(cy-radius)*s,(cx+radius)*s,(cy+radius)*s)
        d=ImageDraw.Draw(image);d.arc(box,180,360,fill=p['track'],width=stroke*s)
        extent=180*min(1,self.speed/1048576/self.limit)
        if extent:
            layer=Image.new('RGBA',image.size);ld=ImageDraw.Draw(layer)
            ld.arc(box,180,180+extent,fill=p['accent'],width=stroke*s)
            glow=layer.filter(ImageFilter.GaussianBlur(3*s));image.paste(glow,(0,0),glow);image.paste(layer,(0,0),layer);d=ImageDraw.Draw(image)
        for index in range(11):
            angle=math.pi+index*math.pi/10
            points=[((cx+r*math.cos(angle))*s,(cy+r*math.sin(angle))*s) for r in (radius-16,radius-23)]
            d.line(points,fill=p['accent'] if index/10<=extent/180 else p['input_border'],width=s)
        image=image.resize((w,h),Image.Resampling.LANCZOS)
        value=self.formatter(f'{self.speed/1048576:.1f}')
        bounds=font(34*s,'Bold','JetBrains Mono').getbbox(value,anchor='ms')
        baseline=cy-38-(bounds[1]+bounds[3])/(2*s)
        text_on(image,(cx,baseline),value,34,'Bold',p['text'],'ms',family='JetBrains Mono')
        text_on(image,(cx,cy-8),'MB/SN',10,fill=p['muted'],anchor='mm',family='JetBrains Mono')
        text_on(image,(cx-radius,cy+18),'0',10,fill=p['muted'],anchor='lm',family='JetBrains Mono')
        text_on(image,(cx+radius,cy+18),str(self.limit),10,fill=p['muted'],anchor='rm',family='JetBrains Mono')
        self.present(image)


class Radar(Indicator):
    def __init__(self,master,palette):super().__init__(master,palette,width=180,height=180);self.draw()
    def draw(self):
        w,h=self.size();s=SURFACE_SCALE;p=self.p;cx=w/2;cy=h/2;r=min(w,h)/2-3
        image=Image.new('RGB',(w*s,h*s),self.cget('bg'));d=ImageDraw.Draw(image)
        for ratio in (1,.7,.4):d.ellipse(((cx-r*ratio)*s,(cy-r*ratio)*s,(cx+r*ratio)*s,(cy+r*ratio)*s),outline=p['line'],width=s)
        d.line(((cx-r)*s,cy*s,(cx+r)*s,cy*s),fill=p['line'],width=s)
        d.line((cx*s,(cy-r)*s,cx*s,(cy+r)*s),fill=p['line'],width=s)
        d.line((cx*s,cy*s,(cx+r*.7)*s,(cy-r*.7)*s),fill=p['accent'],width=s)
        d.polygon([(cx*s,(cy-7)*s),((cx+7)*s,cy*s),(cx*s,(cy+7)*s),((cx-7)*s,cy*s)],outline=p['accent'],width=s)
        self.present(image.resize((w,h),Image.Resampling.LANCZOS))


class ConnectionColumns(Indicator):
    """One vertical column per observed part; no manufactured connections."""
    def __init__(self,master,palette):
        self.rows=();super().__init__(master,palette,height=58);self.draw()
    def set(self,rows):
        rows=tuple(rows)
        if rows!=self.rows:self.rows=rows;self.draw()
    def draw(self):
        w,h=self.size();p=self.p;s=SURFACE_SCALE
        image=Image.new('RGB',(w*s,h*s),self.cget('bg'));d=ImageDraw.Draw(image)
        if self.rows:
            # F01 draws eight slim columns; fewer parts keep that width, left-aligned.
            width=w/max(8,len(self.rows));gap=min(4,width/3)
            for index,row in enumerate(self.rows):
                left=index*width;ratio=min(1,max(0,row['received']/row['total'])) if row['total'] else 0
                d.rectangle((left*s,0,(left+width-gap)*s,h*s),fill=p['track'])
                if ratio:d.rectangle((left*s,h*(1-ratio)*s,(left+width-gap)*s,h*s),fill=p['success'] if row['state']=='Tamamlandı' else p['accent'])
        image=image.resize((w,h),Image.Resampling.LANCZOS)
        if not self.rows:text_on(image,(w/2,h/2),'Henüz ölçülmedi',11,fill=p['muted'],anchor='mm',family='JetBrains Mono')
        self.present(image)
