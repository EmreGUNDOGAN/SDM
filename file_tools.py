"""Local, cancellable media tools and safe file organization."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import threading
import time
from utils import get_category_by_extension,get_unique_filepath

NO_WINDOW=getattr(subprocess,'CREATE_NO_WINDOW',0)

def tool_path(name):
    path=Path(getattr(sys,'_MEIPASS',Path(__file__).parent))/'tools'/f'{name}.exe'
    if path.is_file():return str(path)
    found=shutil.which(name)
    if not found:raise ValueError(f'{name} bulunamadı. SDM kurulumu eksik olabilir.')
    return found

def ensure_space(target,size=0,multiplier=2,already=0):
    folder=Path(target).resolve().parent
    while not folder.exists():folder=folder.parent
    free=shutil.disk_usage(folder).free
    needed=max(0,int(size)*multiplier-int(already))+64*1024*1024
    if free<needed:raise OSError(28,f'Disk alanı yetersiz. En az {needed/1024**3:.2f} GB boş alan gerekiyor.')
    return free

def media_duration(path):
    result=subprocess.run([tool_path('ffprobe'),'-v','error','-protocol_whitelist','file,pipe','-show_entries','format=duration','-of','json',str(path)],capture_output=True,text=True,timeout=30,creationflags=NO_WINDOW)
    if result.returncode:raise ValueError('Medya dosyası okunamadı.')
    return float(json.loads(result.stdout)['format']['duration'])

def seconds(value):
    parts=str(value).strip().split(':')
    if not 1<=len(parts)<=3:raise ValueError('Zaman SS, DD:SS veya SS:DD:SS biçiminde olmalı.')
    values=[float(v) for v in parts]
    if any(v<0 for v in values) or any(v>=60 for v in values[1:]):raise ValueError('Geçersiz zaman.')
    total=0
    for value in values:total=total*60+value
    if not __import__('math').isfinite(total):raise ValueError('Geçersiz zaman.')
    return total

AUDIO_BITRATES=(128,192,256,320)

def process_media(source,destination,kind,start='',end='',cancel=None,progress=lambda p:None,bitrate=192):
    if bitrate not in AUDIO_BITRATES:raise ValueError('Desteklenmeyen ses kalitesi.')
    source=Path(source).resolve();destination=Path(destination).resolve()
    if source==destination or destination.exists():raise ValueError('Çıktı yeni bir dosya olmalı; mevcut dosya üzerine yazılmaz.')
    duration=media_duration(source)
    if not __import__('math').isfinite(duration) or duration<=0:raise ValueError('Medya süresi doğrulanamadı.')
    ensure_space(destination,source.stat().st_size,multiplier=3)
    partial=destination.with_name(destination.stem+'.sdm-converting'+destination.suffix)
    if partial.exists():raise ValueError('Bu çıktı için başka işlem sürüyor.')
    args=[tool_path('ffmpeg'),'-hide_banner','-loglevel','error','-nostdin','-n','-protocol_whitelist','file,pipe','-i',str(source)]
    length=duration
    if kind=='cut':
        beginning=seconds(start);ending=seconds(end)
        if not 0<=beginning<ending<=duration+.1:raise ValueError('Kesme aralığı dosya süresi içinde olmalı.')
        length=ending-beginning;args+=['-ss',str(beginning),'-t',str(length)]
    extension=destination.suffix.lower()
    if extension=='.mp3':args+=['-vn','-c:a','libmp3lame','-b:a',f'{bitrate}k']
    elif extension=='.wav':args+=['-vn','-c:a','pcm_s16le']
    elif extension=='.m4a':args+=['-vn','-c:a','aac','-b:a',f'{bitrate}k']
    elif extension in ('.mp4','.mkv'):args+=['-c:v','libx264','-preset','fast','-crf','23','-c:a','aac']
    else:raise ValueError('Desteklenen çıktılar: MP4, MKV, MP3, M4A, WAV.')
    args+=['-progress','pipe:1',str(partial)]
    cancel=cancel or threading.Event()
    error_path=partial.with_suffix(partial.suffix+'.log')
    try:
        with error_path.open('wb') as error:
            process=subprocess.Popen(args,stdout=subprocess.PIPE,stderr=error,creationflags=NO_WINDOW)
            def stop():
                while process.poll() is None:
                    if cancel.wait(.1):
                        process.terminate();return
            watcher=threading.Thread(target=stop,daemon=True);watcher.start()
            for line in process.stdout:
                if line.startswith(b'out_time_us='):
                    try:progress(min(99,float(line.split(b'=')[1])/1e6/length*100))
                    except ValueError:pass
            code=process.wait();process.stdout.close();watcher.join(1)
        if cancel.is_set():raise ValueError('İşlem iptal edildi; kaynak dosya korundu.')
        if code:raise ValueError('Dönüştürme tamamlanamadı. Dosyanın biçimini ve disk alanını kontrol et.')
        if destination.exists():raise ValueError('Çıktı yolu başka bir dosya tarafından kullanılıyor.')
        partial.rename(destination);progress(100)
        return destination
    finally:
        partial.unlink(missing_ok=True);error_path.unlink(missing_ok=True)

def organization_plan(folder,excluded=()):
    root=Path(folder).resolve();excluded={Path(p).resolve() for p in excluded}
    plan=[];reserved=set()
    for source in sorted(root.iterdir()):
        if not source.is_file() or source.is_symlink() or source.resolve() in excluded or '.sdm-' in source.name or source.name.endswith(('.part','.temp_final')):continue
        category=get_category_by_extension(source.name)
        target=get_unique_filepath(root/category,source.name)
        if not target.resolve().is_relative_to(root):raise ValueError('Kategori klasörü seçilen klasörün dışına yönleniyor.')
        count=1
        while target in reserved:
            target=root/category/f'{source.stem} ({count}){source.suffix}';count+=1
        reserved.add(target);plan.append((source,target))
    return plan

def move_plan(plan):
    moved=[]
    for source,target in plan:
        source=Path(source);target=Path(target)
        if not source.is_file() or source.is_symlink() or target.exists():raise ValueError('Dosyalar değişti; önizlemeyi yenile.')
        target.parent.mkdir(parents=True,exist_ok=True)
        source.rename(target);moved.append((source,target))
    return moved
