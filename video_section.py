"""Fetch only a supported media time range with cancellable FFmpeg."""
import math
import subprocess
import time
from pathlib import Path
import requests
from utils import clean_filename

def parse_time(text):
    parts=str(text).strip().split(':')
    if len(parts) not in (2,3) or any(not p.isdigit() for p in parts):raise ValueError('Zamanı SS:DD:SN veya DD:SN biçiminde girin.')
    numbers=list(map(int,parts))
    if any(n>=60 for n in numbers[1:]):raise ValueError('Dakika ve saniye 0–59 arasında olmalı.')
    return sum(n*60**i for i,n in enumerate(reversed(numbers)))

def validate_section(section,duration=None):
    if not section:return None
    start=section.get('start');end=section.get('end');exact=section.get('exact',False)
    if type(start) not in (int,float) or type(end) not in (int,float) or not math.isfinite(start) or not math.isfinite(end) or start<0 or end<=start:raise ValueError('Bitiş zamanı başlangıçtan büyük olmalı.')
    if type(exact) is not bool:raise ValueError('Kesim seçimi geçersiz.')
    if duration is not None and (not math.isfinite(duration) or duration<=0 or start>=duration or end>duration):raise ValueError('Seçilen aralık video süresini aşıyor veya süre bilinmiyor.')
    return dict(start=start,end=end,exact=exact)

def download_section(task,info,staging):
    from video_downloader import tool_options
    section=validate_section(task.section,info.get('duration'))
    if info.get('is_live') or not info.get('duration'):raise ValueError('Bölüm indirme için süresi bilinen, tamamlanmış bir video seçin.')
    streams=info.get('requested_formats') or [info]
    duration=section['end']-section['start']
    target=staging/(clean_filename(info.get('title','Video'))+'-bolum'+('.mp3' if task.is_audio_only else '.mkv'))
    ffmpeg=Path(tool_options().get('ffmpeg_location','tools'))/'ffmpeg.exe'
    if not ffmpeg.exists():raise RuntimeError('Bölüm indirme için FFmpeg bulunamadı.')
    args=[str(ffmpeg),'-hide_banner','-loglevel','error','-y','-nostdin']
    for stream in streams:
        protocol=stream.get('protocol','')
        if protocol not in ('http','https','m3u8_native','m3u8'):raise ValueError('Bu kaynak bölüm indirmeyi desteklemiyor.')
        headers=dict(stream.get('http_headers') or {})
        if protocol in ('http','https'):
            with requests.get(stream['url'],headers=dict(headers,Range='bytes=0-0'),stream=True,timeout=(10,15)) as response:
                if response.status_code!=206:raise ValueError('Kaynak aralıklı erişimi desteklemiyor; önce tam indirip Araçlar’dan kesebilirsiniz.')
        args+=['-ss',str(section['start'])]
        if headers:args+=['-headers',''.join(f'{k}: {v}\r\n' for k,v in headers.items())]
        args+=['-i',stream['url']]
    video=next((i for i,s in enumerate(streams) if s.get('vcodec')!='none'),None)
    audio=next((i for i,s in enumerate(streams) if s.get('acodec')!='none'),None)
    if video is not None and not task.is_audio_only:args+=['-map',f'{video}:v:0']
    if audio is not None:args+=['-map',f'{audio}:a:0']
    args+=['-t',str(duration)]
    if task.is_audio_only:args+=['-vn','-c:a','libmp3lame','-b:a','192k']
    elif section['exact']:args+=['-c:v','libx264','-preset','fast','-crf','20','-c:a','aac']
    else:args+=['-c','copy']
    args+=['-progress','pipe:1',str(target)]
    task.unobserved_method='FFmpeg · Hassas bölüm' if section['exact'] else 'FFmpeg · Hızlı bölüm'
    log=staging/'section-error.log'
    with log.open('wb') as err,subprocess.Popen(args,stdout=subprocess.DEVNULL,stderr=err,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0)) as process:
        while process.poll() is None:
            if task._cancel_flag.wait(.2):
                process.terminate()
                try:process.wait(5)
                except subprocess.TimeoutExpired:process.kill();process.wait()
                raise RuntimeError('Bölüm indirme duraklatıldı veya iptal edildi')
            size=target.stat().st_size if target.exists() else 0
            if task.progress_callback:task.progress_callback(task.download_id,size,0,0,0,'İndiriliyor')
            task.downloaded_bytes=size
        if process.returncode:raise RuntimeError('Bölüm indirilemedi. Kaynak erişimi veya medya biçimi desteklenmiyor.')
    if not target.exists() or not target.stat().st_size:raise RuntimeError('Bölüm çıktısı oluşturulamadı.')
    info['requested_downloads']=[{'filepath':str(target)}]
    return info

class SectionFields:
    def __init__(self,parent):
        import tkinter as tk
        import ttkbootstrap as tb
        self.enabled=tk.BooleanVar(value=False);self.start=tk.StringVar(value='00:00:00');self.end=tk.StringVar(value='00:00:30');self.exact=tk.BooleanVar(value=False)
        box=tb.Frame(parent);box.pack(fill='x',pady=8)
        tb.Checkbutton(box,text='Belirli video / ses bölümünü indir',variable=self.enabled).pack(anchor='w')
        row=tb.Frame(box);row.pack(fill='x',pady=6)
        for title,var in [('Başlangıç',self.start),('Bitiş',self.end)]:
            tb.Label(row,text=title).pack(side='left',padx=(0,5));tb.Entry(row,textvariable=var,width=11).pack(side='left',padx=(0,12))
        tb.Radiobutton(box,text='Hızlı kesim — birkaç saniye sapabilir',variable=self.exact,value=False).pack(anchor='w')
        tb.Radiobutton(box,text='Hassas kesim — yeniden kodlar, daha fazla işlemci kullanır',variable=self.exact,value=True).pack(anchor='w')
    def collect(self):
        return validate_section(dict(start=parse_time(self.start.get()),end=parse_time(self.end.get()),exact=self.exact.get())) if self.enabled.get() else None
