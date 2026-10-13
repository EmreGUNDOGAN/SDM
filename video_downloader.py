"""
video_downloader.py - yt-dlp wrapper for multimedia and streaming video downloads in SDM.
"""
from __future__ import annotations

import logging
from pathlib import Path
import re
import threading
import sys
import time
from progress_meter import ProgressMeter
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("SDM.Video")

try:
    import yt_dlp
except ImportError:
    yt_dlp = None

QUALITY_FORMAT_MAP = {
    "En İyi": "bestvideo+bestaudio/best",
    "4K (2160p)": "bestvideo[height<=2160]+bestaudio/best[height<=2160]",
    "1080p": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
    "720p": "bestvideo[height<=720]+bestaudio/best[height<=720]",
    "480p": "bestvideo[height<=480]+bestaudio/best[height<=480]",
    "Yalnızca Ses (MP3)": "bestaudio/best",
}


def tool_options():
    root = Path(getattr(sys, '_MEIPASS', Path(__file__).parent))
    tools = root / 'tools'
    options = {'ffmpeg_location': str(tools)} if (tools / 'ffmpeg.exe').exists() else {}
    if (tools / 'deno.exe').exists():
        options['js_runtimes'] = {'deno': {'path': str(tools / 'deno.exe')}}
    return options


def format_options(info):
    def size_of(fmt):
        size=fmt.get('filesize') or fmt.get('filesize_approx') or 0
        if not size and info.get('duration') and fmt.get('tbr'):size=info['duration']*fmt['tbr']*1000/8
        return max(0,int(size))
    heights = sorted({int(f['height']) for f in info.get('formats', [])
                      if f.get('height') and f.get('vcodec') != 'none'
                      and not f.get('has_drm')}, reverse=True)
    if not heights and info.get('height') and not info.get('has_drm'):
        heights = [int(info['height'])]
    qualities = []
    for height in heights:
        formats = [f for f in info.get('formats',[]) if f.get('height') == height and not f.get('has_drm')]
        audio_sizes = [size_of(f) for f in info.get('formats',[])
                       if f.get('vcodec') == 'none' and not f.get('has_drm')]
        candidate = max(formats,key=lambda f:f.get('tbr') or 0,default={})
        size = size_of(candidate)
        if candidate.get('acodec') == 'none' and size:
            size += max(audio_sizes,default=0)
        qualities.append({'height':height,'label':f'{height}p','filesize':size,
                          'extension':candidate.get('ext','mkv'),'estimated':True})
    return {'title': info.get('title', 'Video'),
            'audio_filesize':int((info.get('duration') or 0)*192000/8),
            'qualities': qualities,
            'audio': any(f.get('acodec') not in (None, 'none') and not f.get('has_drm')
                         for f in info.get('formats', []))}


def fetch_video_formats(url):
    if yt_dlp is None:
        raise RuntimeError('yt-dlp unavailable')
    opts = {'quiet': True, 'no_warnings': True, 'noplaylist': True,
            'skip_download': True, 'socket_timeout': 20, **tool_options()}
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
        if not info or info.get('has_drm'):
            raise ValueError('Video unavailable')
        return format_options(info)


def is_video_site(url: str) -> bool:
    """Check if the URL belongs to popular video platforms supported by yt-dlp."""
    if not url:
        return False
    video_domains = [
        "youtube.com", "youtu.be", "vimeo.com", "dailymotion.com",
        "tiktok.com", "facebook.com", "instagram.com", "twitter.com",
        "x.com", "twitch.tv", "bilibili.com", "soundcloud.com"
    ]
    url_lower = url.lower()
    return any(domain in url_lower for domain in video_domains)


def fetch_video_info(url: str) -> Optional[Dict[str, Any]]:
    """Extract metadata (title, formats, thumbnail, duration) from URL without downloading."""
    if yt_dlp is None:
        return None

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": "in_playlist",
        "skip_download": True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if not info:
                return None
            return {
                "title": info.get("title", "Video"),
                "duration": info.get("duration", 0),
                "thumbnail": info.get("thumbnail"),
                "uploader": info.get("uploader", ""),
                "is_playlist": info.get("_type") == "playlist" or "entries" in info,
                "entries_count": len(info.get("entries", [])) if "entries" in info else 1,
            }
    except Exception as e:
        logger.error(f"Failed to fetch video info: {e}")
        return None


class VideoDownloadTask:
    """Manages yt-dlp download in a background thread with progress reporting."""

    def __init__(
        self,
        download_id: int,
        url: str,
        dest_folder: str | Path,
        quality: str = "En İyi",
        is_audio_only: bool = False,
        progress_callback: Optional[Callable[[int, int, int, float, float, str], None]] = None,
        status_callback: Optional[Callable[[int, str, str], None]] = None,
        metadata_callback: Optional[Callable[[int, str, str, int, str], None]] = None,
        selected_height: Optional[int] = None,
        connections: int = 8,
        output_name: Optional[str] = None,
    ):
        self.download_id = download_id
        self.url = url
        self.dest_folder = Path(dest_folder)
        self.quality = quality
        self.selected_height = selected_height
        self.connections = max(1, min(32, connections))
        self.output_name = output_name
        self.is_audio_only = is_audio_only or ("Ses" in quality)

        self.progress_callback = progress_callback
        self.status_callback = status_callback
        self.metadata_callback = metadata_callback

        self.status = "Bekliyor"
        self.error_message = ""
        self._cancel_flag = threading.Event()
        self._thread: Optional[threading.Thread] = None

        self.downloaded_bytes = 0
        self.total_bytes = 0
        self.current_speed = 0.0
        self.eta = 0.0
        self.target_filepath = ""
        self.meter = ProgressMeter()
        self._last_report = 0.0
        self._stream_name = None
        self._paused = False
        self._streams = {}
        self._expected_total = 0
        self._range_active = False
        from transfer_details import TransferDetails
        self.transfer_details=TransferDetails()
        self.unobserved_method='Video motoru · ön kontrol'
        self._access_retries=0

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return False
        self._paused = False
        self._cancel_flag.clear()
        self._access_retries=0
        from transfer_details import TransferDetails
        self.transfer_details=TransferDetails()
        self.status = "İndiriliyor"
        self._notify_status("İndiriliyor")
        self._thread = threading.Thread(
            target=self._run, name=f"VideoDownload-{self.download_id}", daemon=True
        )
        self._thread.start()
        return True

    def cancel(self) -> None:
        self._paused = False
        self._cancel_flag.set()
        self.status = "İptal Edildi"
        self._notify_status("İptal Edildi")

    def pause(self):
        self._paused = True
        self._cancel_flag.set()
        self.status = 'Duraklatıldı'
        self._notify_status(self.status)

    def _notify_status(self, status: str, error: str = "") -> None:
        if self.status_callback:
            try:
                self.status_callback(self.download_id, status, error or self.error_message)
            except Exception as e:
                logger.debug(f"Video status callback error: {e}")

    def _progress_hook(self, d: Dict[str, Any]) -> None:
        if self._cancel_flag.is_set():
            raise Exception("İndirme kullanıcı tarafından iptal edildi.")

        status = d.get("status")
        if status == "downloading":
            stream_name = d.get('filename')
            if stream_name != self._stream_name:
                self._stream_name = stream_name
            now = time.monotonic()
            if now - self._last_report < 0.5:
                return
            self._last_report = now
            previous=self.downloaded_bytes
            self._streams[stream_name] = (d.get('downloaded_bytes', 0) or 0,
                                          d.get('total_bytes') or d.get('total_bytes_estimate') or 0)
            self.downloaded_bytes = sum(v[0] for v in self._streams.values())
            self.total_bytes = max(self._expected_total, sum(v[1] for v in self._streams.values()))
            if not self._range_active:
                from transfer_control import GLOBAL_LIMITER
                GLOBAL_LIMITER.consume(max(0,self.downloaded_bytes-previous),self._cancel_flag.is_set)

            # --- YÜZDE HESAPLAMA EKLENTİSİ ---
            if self.total_bytes > 0:
                self.progress = (self.downloaded_bytes / self.total_bytes) * 100
            else:
                p_str = d.get("_percent_str", "0%").strip().replace("%", "")
                try:
                    self.progress = float(p_str)
                except ValueError:
                    self.progress = 0.0

            self.speed = d.get("speed", 0) or 0
            if self._cancel_flag.is_set():raise RuntimeError('İndirme duraklatıldı veya iptal edildi')
            changed=self.status!='İndiriliyor'
            self.status = "İndiriliyor"
            if changed:self._notify_status("İndiriliyor")

        status = d.get("status")
        if status == "downloading":
            self.current_speed, self.eta = self.meter.update(self.downloaded_bytes, self.total_bytes)

            # File name notification if available
            filename = d.get("filename")
            if filename and not self.target_filepath:
                p = Path(filename)
                p = self.dest_folder / p.name
                self.target_filepath = str(p)
                if self.metadata_callback:
                    cat = "Müzik" if self.is_audio_only else "Video"
                    self.metadata_callback(self.download_id, p.name, str(p), self.total_bytes, cat)

            if self.progress_callback:
                try:
                    self.progress_callback(
                        self.download_id,
                        self.downloaded_bytes,
                        self.total_bytes,
                        self.current_speed,
                        self.eta,
                        "İndiriliyor",
                    )
                except Exception as e:
                    logger.debug(f"Video progress hook callback error: {e}")

        elif status == "finished":
            stream_name = d.get('filename')
            size = d.get('total_bytes') or d.get('downloaded_bytes') or 0
            self._streams[stream_name] = (size, size)
            self.downloaded_bytes = sum(v[0] for v in self._streams.values())
            self.status = "Dönüştürülüyor"
            self._notify_status("Dönüştürülüyor")

    def _run(self) -> None:
        if yt_dlp is None:
            self.status = "Hata"
            self.error_message = "yt-dlp kütüphanesi yüklü değil."
            self._notify_status("Hata", self.error_message)
            return

        fmt = QUALITY_FORMAT_MAP.get(self.quality, "bestvideo+bestaudio/best")
        if self.selected_height:
            h = int(self.selected_height)
            fmt = f'bestvideo[height={h}]+bestaudio/best[height={h}]'
        self.dest_folder.mkdir(parents=True, exist_ok=True)
        staging = self.dest_folder / f'.sdm-video-{self.download_id}'
        staging.mkdir(parents=True, exist_ok=True)
        outtmpl = str(staging / "%(title)s [%(id)s].%(ext)s")

        ydl_opts: Dict[str, Any] = {
            "sdm_task": self,
            "concurrent_fragment_downloads": self.connections,
            "format": fmt,
            "outtmpl": outtmpl,
            "progress_hooks": [self._progress_hook],
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "ignoreerrors": False,
            "windowsfilenames": True,
            "merge_output_format": "mkv",
            **tool_options(),

            # --- ALTYAZI DÜZELTMESİ ---
            "writesubtitles": False,
            "writeautomaticsub": False,
            "subtitleslangs": ["tr", "en", "tr-TR", "en-US", "tr.*", "en.*"],
            "convertsubtitles": "srt",  # Otomatik VTT altyazıları SRT'ye dönüştürür
            "postprocessors": [],
            "encoding": "utf-8",
        }

        if self.is_audio_only:
            ydl_opts["format"] = "bestaudio/best"
            ydl_opts["postprocessors"] = [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ]

        try:
            from video_http import install_video_http_downloader
            install_video_http_downloader()
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(self.url, download=False)
                formats = info.get('requested_formats') or info.get('requested_downloads') or [info]
                self._expected_total = sum(f.get('filesize') or f.get('filesize_approx') or 0 for f in formats)
                self.total_bytes = self._expected_total
                self.unobserved_method=' / '.join(dict.fromkeys(str(f.get('protocol') or 'Video motoru') for f in formats))
                from file_tools import ensure_space
                existing=sum(p.stat().st_size for p in staging.rglob('*') if p.is_file())
                exact_total=sum(f.get('filesize') or 0 for f in formats) if all(f.get('filesize') for f in formats) else 0
                ensure_space(staging/'output',exact_total,3 if self.is_audio_only else 2,existing)
                if self.metadata_callback:
                    preview=Path(ydl.prepare_filename(info))
                    name=(Path(self.output_name).stem if self.output_name else preview.stem)+('.mp3' if self.is_audio_only else '.mkv' if len(formats)>1 else preview.suffix)
                    self.metadata_callback(self.download_id,name,str(self.dest_folder/name),self._expected_total,'Müzik' if self.is_audio_only else 'Video')
                self.meter.reset(self.downloaded_bytes)
                info = ydl.process_ie_result(info, download=True)
                if info:
                    final_path = Path(ydl.prepare_filename(info))
                    for processed in info.get('requested_downloads', []):
                        if processed.get('filepath'):
                            final_path = Path(processed['filepath'])
                    if self.is_audio_only:
                        final_path = final_path.with_suffix('.mp3')
                    if not final_path.exists():
                        final_path = final_path.with_suffix('.mkv')
                    if not final_path.exists():
                        raise RuntimeError('İndirme çıktı dosyası bulunamadı')
                    if self._cancel_flag.is_set():
                        raise RuntimeError('İndirme iptal edildi')
                    from utils import get_unique_filepath
                    destination = get_unique_filepath(self.dest_folder,
                        (Path(self.output_name).stem + final_path.suffix) if self.output_name else final_path.name)
                    final_path.replace(destination)
                    final_path = destination
                    self.target_filepath=str(final_path)
                    final_name = final_path.name
                    if self.metadata_callback:
                        cat = "Müzik" if self.is_audio_only else "Video"
                        filesize = self.total_bytes or (
                            final_path.stat().st_size if final_path.exists() else 0
                        )
                        self.metadata_callback(
                            self.download_id, final_name, str(final_path), filesize, cat
                        )

            if not self._cancel_flag.is_set():
                self.total_bytes = final_path.stat().st_size
                self.downloaded_bytes = self.total_bytes
                self.status = "Tamamlandı"
                if self.progress_callback:
                    self.progress_callback(
                        self.download_id,
                        self.total_bytes or self.downloaded_bytes,
                        self.total_bytes or self.downloaded_bytes,
                        0.0,
                        0.0,
                        "Tamamlandı",
                    )
                self._notify_status("Tamamlandı")

        except Exception as e:
            if self._cancel_flag.is_set():
                self.status = 'Duraklatıldı' if self._paused else 'İptal Edildi'
                self._notify_status(self.status)
            else:
                if ('403' in str(e) or 'Forbidden' in str(e)) and self._access_retries<1:
                    self._access_retries+=1;self._range_active=False
                    self.unobserved_method='Erişim bağlantısı bir kez yenileniyor'
                    logger.warning('Video access was denied; re-extracting the page once before reporting failure.')
                    self._run();return
                logger.error(f"yt-dlp execution error: {e}")
                self.status = "Hata"
                self.error_message = str(e)
                self._notify_status("Hata", str(e))
