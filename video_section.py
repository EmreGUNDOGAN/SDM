"""Fetch only a supported media time range with cancellable FFmpeg."""
import json
import math
import subprocess
import threading
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
    """Download [start,end) in resumable, stream-copied parts.

    Every part keeps source timestamps (-copyts) and is trimmed to [head,stop):
    head is the last video keyframe at or before the part's start (separate DASH
    audio otherwise starts ~10 s early with no picture) and, on pause, stop is
    the last keyframe all streams reached, so the next part starts exactly there
    and the parts join without gaps. Exact cuts and MP3 are encoded locally from
    the joined copy, so pausing never throws away media already downloaded.
    """
    from video_downloader import tool_options
    section=validate_section(task.section,info.get('duration'))
    if info.get('is_live') or not info.get('duration'):raise ValueError('Bölüm indirme için süresi bilinen, tamamlanmış bir video seçin.')
    streams=info.get('requested_formats') or [info]
    start,end=section['start'],section['end'];duration=end-start
    ext='.mp3' if task.is_audio_only else '.mkv'
    target=staging/(clean_filename(info.get('title','Video'))+'-bolum'+ext)
    ffmpeg=Path(tool_options().get('ffmpeg_location','tools'))/'ffmpeg.exe'
    ffprobe=ffmpeg.with_name('ffprobe.exe')
    if not ffmpeg.exists() or not ffprobe.exists():raise RuntimeError('Bölüm indirme için FFmpeg bulunamadı.')
    encode=task.is_audio_only or section['exact']
    # Copied frames just before a cut may reference later ones, so an exact cut
    # downloads a little past the end and leaves the trimming to the encoder.
    until=min(info['duration'],end+1) if encode else end
    inputs=[]
    for stream in streams:
        protocol=stream.get('protocol','')
        if protocol not in ('http','https','m3u8_native','m3u8'):raise ValueError('Bu kaynak bölüm indirmeyi desteklemiyor.')
        headers=dict(stream.get('http_headers') or {})
        if protocol in ('http','https'):
            with requests.get(stream['url'],headers=dict(headers,Range='bytes=0-0'),stream=True,timeout=(10,15)) as response:
                if response.status_code!=206:raise ValueError('Kaynak aralıklı erişimi desteklemiyor; önce tam indirip Araçlar’dan kesebilirsiniz.')
        inputs.append((stream['url'],''.join(f'{k}: {v}\r\n' for k,v in headers.items())))
    video=next((i for i,s in enumerate(streams) if s.get('vcodec')!='none'),None)
    audio=next((i for i,s in enumerate(streams) if s.get('acodec')!='none'),None)
    task.unobserved_method='FFmpeg · Hassas bölüm' if section['exact'] else 'FFmpeg · Hızlı bölüm'
    key=dict(start=start,end=end,exact=section['exact'],audio=bool(task.is_audio_only),formats=[str(s.get('format_id') or s.get('url')) for s in streams])
    parts=_load_parts(staging,key)
    approx=sum(s.get('filesize') or s.get('filesize_approx') or 0 for s in streams)*(until-start)/info['duration']
    position=parts[-1]['next'] if parts else start
    if position<until-.05:
        # NUT keeps pts and dts as read; Matroska re-derives dts and bends B-frame timestamps.
        part=staging/f'section-part-{len(parts)+1}.nut'
        args=[str(ffmpeg),'-hide_banner','-loglevel','error','-y']
        for url,headers in inputs:
            args+=['-ss',str(position)]
            if headers:args+=['-headers',headers]
            args+=['-i',url]
        if video is not None and not task.is_audio_only:args+=['-map',f'{video}:v:0']
        if audio is not None:args+=['-map',f'{audio}:a:0']
        args+=['-copyts','-start_at_zero','-to',str(until),'-c','copy','-progress','pipe:1',str(part)]
        done=sum(p['duration'] for p in parts)
        stopped=_run_part(task,args,staging,part,parts,done,until-start,approx,position)
        if stopped and not task._paused:
            _clear_parts(staging);raise RuntimeError('Bölüm indirme iptal edildi')
        piece=_finish_part(ffmpeg,ffprobe,part,position,until,stopped) if part.exists() and part.stat().st_size else None
        if piece:parts.append(piece);_save_parts(staging,key,parts)
        else:part.unlink(missing_ok=True)
        if stopped:raise RuntimeError('Bölüm indirme duraklatıldı')
    if not parts:raise RuntimeError('Bölüm çıktısı oluşturulamadı.')
    if not encode:
        _join_parts(ffmpeg,staging,parts,target);_clear_parts(staging)
        info['requested_downloads']=[{'filepath':str(target)}];return info
    joined=staging/'section-part-joined.mkv'
    _join_parts(ffmpeg,staging,parts,joined)
    task.status='Dönüştürülüyor';task._notify_status(task.status)
    args=[str(ffmpeg),'-hide_banner','-loglevel','error','-y','-ss',f'{start-parts[0]["head"]:.6f}','-i',str(joined),'-t',str(duration)]
    args+=['-vn','-c:a','libmp3lame','-b:a',f"{task.audio['bitrate']}k"] if task.is_audio_only else ['-map','0','-c:v','libx264','-preset','fast','-crf','20','-c:a','aac']
    args+=['-progress','pipe:1',str(target)]
    stopped=_run_part(task,args,staging,target,parts,0,duration,0,0,converting=True)
    joined.unlink(missing_ok=True)
    if stopped:
        target.unlink(missing_ok=True)
        if task._paused:raise RuntimeError('Bölüm dönüştürme duraklatıldı')
        _clear_parts(staging);raise RuntimeError('Bölüm indirme iptal edildi')
    _clear_parts(staging)
    info['requested_downloads']=[{'filepath':str(target)}]
    return info


STATE='section-parts.json'

def _load_parts(staging,key):
    path=staging/STATE
    try:state=json.loads(path.read_text(encoding='utf-8'))
    except (OSError,ValueError):state={}
    if state.get('key')==key and all((staging/p['file']).is_file() for p in state.get('parts',[])):return state['parts']
    _clear_parts(staging);return []

def _save_parts(staging,key,parts):
    (staging/STATE).write_text(json.dumps({'key':key,'parts':parts}),encoding='utf-8')

def _clear_parts(staging):
    for path in list(staging.glob('section-part-*'))+[staging/STATE,staging/'section-join.txt']:path.unlink(missing_ok=True)

def _run_part(task,args,staging,part,parts,done,duration,approx,origin,converting=False):
    """Run FFmpeg, report real progress, and stop it cleanly ('q') on pause."""
    state={'time':0.0};started=time.monotonic();last=(started,0);speed=0.0;shown=0.0
    earlier=sum((staging/p['file']).stat().st_size for p in parts)
    def read(stream):
        for raw in stream:
            name,_,value=raw.decode('ascii','replace').strip().partition('=')
            if name in ('out_time_us','out_time_ms') and value.lstrip('-').isdigit():state['time']=int(value)/1e6
    flags=getattr(subprocess,'CREATE_NO_WINDOW',0)
    with (staging/'section-error.log').open('wb') as err,subprocess.Popen(args,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=err,creationflags=flags) as process:
        reader=threading.Thread(target=read,args=(process.stdout,),daemon=True);reader.start()
        stopped=False
        while process.poll() is None:
            if task._cancel_flag.wait(.25):
                stopped=True
                try:process.stdin.write(b'q');process.stdin.flush()
                except OSError:pass
                try:process.wait(10 if task._paused else 3)
                except subprocess.TimeoutExpired:
                    process.terminate()
                    try:process.wait(5)
                    except subprocess.TimeoutExpired:process.kill();process.wait()
                break
            now=time.monotonic()
            gained=max(0.0,state['time']-origin);fraction=min(1.0,(done+gained)/duration)
            if converting:total=earlier;got=round(fraction*total)  # sized by the downloaded copy; the share shows encoding
            else:
                size=earlier+(part.stat().st_size if part.exists() else 0)
                # Muxers may buffer small outputs, so while nothing is on disk the media
                # time and the format size estimate still give a real percentage.
                total=max(size,round(size/fraction)) if fraction>.03 and size else max(size,round(approx))
                got=size or round(fraction*total)
                # Size and media time advance in steps; never let the bar step back within a part.
                if total and got/total<shown:total=max(got,round(got/shown))
                shown=got/total if total else shown
                if now-last[0]>=1:speed=(got-last[1])/(now-last[0])*.4+speed*.6;last=(now,got)
            rate=gained/(now-started) if now>started else 0
            eta=(duration-done-gained)/rate if rate>0 else 0
            task.downloaded_bytes,task.total_bytes,task.current_speed,task.eta=got,total,speed,eta
            if task.progress_callback:task.progress_callback(task.download_id,got,total,speed,eta,'Dönüştürülüyor' if converting else 'İndiriliyor')
        reader.join(2)
        if not stopped and process.returncode:
            raise RuntimeError('Bölüm dönüştürülemedi. Disk alanını kontrol edin.' if converting else 'Bölüm indirilemedi. Kaynak erişimi veya medya biçimi desteklenmiyor.')
    return stopped

def _probe(ffprobe,path,*entries):
    result=subprocess.run([str(ffprobe),'-v','error',*entries,'-of','csv=p=0',str(path)],capture_output=True,text=True,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    return [line.split(',') for line in result.stdout.split() if line]

def _finish_part(ffmpeg,ffprobe,part,position,until,stopped):
    """Trim a copied part to [head,stop) and return {'file','head','duration','next'}, or None."""
    rows=[r for r in _probe(ffprobe,part,'-show_entries','packet=codec_type,pts_time,flags') if len(r)>2 and r[1]!='N/A']
    video=sorted(float(r[1]) for r in rows if r[0]=='video' and 'K' in r[2])
    audio=sorted(float(r[1]) for r in rows if r[0]=='audio')
    keys=video or audio  # every audio packet is a sync point
    if not keys:return None
    head=max([t for t in keys if t<=position+.0005] or keys[:1])
    stop=until
    if stopped:
        # Resume at the last keyframe that every stream has already passed.
        reached=min(audio[-1] if video and audio else math.inf,keys[-1])
        stop=max([t for t in keys if t<=reached+.0005] or [head])
        if stop-head<.5:return None
    # Keep source timestamps and drop every packet outside [head,stop): the audio
    # read before the first keyframe, and frames decoded past the cut whose B-frames
    # are missing. Parts cut this way share one timeline and join without gaps.
    trimmed=part.with_name(part.stem+'-t'+part.suffix)
    subprocess.run([str(ffmpeg),'-hide_banner','-loglevel','error','-y','-i',str(part),'-map','0','-c','copy','-copyts',
                    '-bsf',f'noise=drop=lt(pts*tb\\,{head-.0005:.6f})+gte(pts*tb\\,{stop-.0005:.6f})',str(trimmed)],
                   check=True,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    trimmed.replace(part)
    return {'file':part.name,'head':head,'duration':stop-head,'next':stop}

def _join_parts(ffmpeg,staging,parts,target):
    # Parts carry source timestamps; inpoint/duration map them onto one zero-based timeline.
    listing=staging/'section-join.txt'
    listing.write_text(''.join("file '"+p['file'].replace("'","'\\''")+f"'\ninpoint {p['head']:.6f}\nduration {p['duration']:.6f}\n" for p in parts),encoding='utf-8')
    subprocess.run([str(ffmpeg),'-hide_banner','-loglevel','error','-y','-f','concat','-safe','0','-i',str(listing),'-map','0','-c','copy',str(target)],
                   check=True,cwd=staging,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))

from section_fields_ui import SectionFields
