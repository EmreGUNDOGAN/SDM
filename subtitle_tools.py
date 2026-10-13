from pathlib import Path
import tempfile
import yt_dlp
from video_downloader import tool_options
from browser_bridge import validate_url
from utils import get_unique_filepath

def subtitle_choices(url):
    validate_url(url)
    with yt_dlp.YoutubeDL({'quiet':True,'skip_download':True,'noplaylist':True,'socket_timeout':20,**tool_options()}) as ydl:info=ydl.extract_info(url,download=False)
    return [(language,automatic) for automatic,key in [(False,'subtitles'),(True,'automatic_captions')] for language,formats in (info.get(key) or {}).items() if formats and language!='live_chat']

def download_subtitle(url,folder,language,automatic,extension,cancel):
    validate_url(url)
    if extension not in ('srt','vtt'):raise ValueError('Geçersiz altyazı biçimi.')
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.sdm-subtitle-',dir=folder) as temporary:
        def hook(_):
            if cancel.is_set():raise ValueError('Altyazı indirme iptal edildi.')
        opts={'quiet':True,'skip_download':True,'noplaylist':True,'socket_timeout':20,'writesubtitles':not automatic,'writeautomaticsub':automatic,'subtitleslangs':['^'+__import__('re').escape(language)+'$'],'subtitlesformat':'vtt/best','outtmpl':str(Path(temporary)/'%(title)s.%(ext)s'),'windowsfilenames':True,'progress_hooks':[hook],**tool_options()}
        if extension=='srt':opts['postprocessors']=[{'key':'FFmpegSubtitlesConvertor','format':'srt','when':'before_dl'}]
        with yt_dlp.YoutubeDL(opts) as ydl:ydl.download([url])
        if cancel.is_set():raise ValueError('Altyazı indirme iptal edildi.')
        paths=[]
        for path in Path(temporary).glob('*.'+extension):
            target=get_unique_filepath(folder,path.name);path.rename(target);paths.append(target)
        if not paths:raise ValueError('Seçilen dil bu biçimde indirilemedi.')
        return paths
