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
    heights = sorted({int(f['height']) for f in info.get('formats', [])
                      if f.get('height') and f.get('vcodec') != 'none'
                      and not f.get('has_drm')}, reverse=True)
    if not heights and info.get('height') and not info.get('has_drm'):
        heights = [int(info['height'])]
    return {'title': info.get('title', 'Video'),
            'qualities': [{'height': h, 'label': f'{h}p'} for h in heights],
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
    ):
        self.download_id = download_id
        self.url = url
        self.dest_folder = Path(dest_folder)
        self.quality = quality
        self.selected_height = selected_height
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

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return False
        self._paused = False
        self._cancel_flag.clear()
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
                self.meter.reset(d.get('downloaded_bytes', 0) or 0)
            now = time.monotonic()
            if now - self._last_report < 0.5:
                return
            self._last_report = now
            self.downloaded_bytes = d.get("downloaded_bytes", 0) or 0
            self.total_bytes = (
                d.get("total_bytes") or d.get("total_bytes_estimate") or self.total_bytes or 0
            )

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
            self.status = "İndiriliyor"
            self._notify_status("İndiriliyor")

        status = d.get("status")
        if status == "downloading":
            self.downloaded_bytes = d.get("downloaded_bytes", 0) or 0
            self.total_bytes = (
                d.get("total_bytes") or d.get("total_bytes_estimate") or self.total_bytes or 0
            )
            self.current_speed, self.eta = self.meter.update(self.downloaded_bytes, self.total_bytes)

            # File name notification if available
            filename = d.get("filename")
            if filename and not self.target_filepath:
                self.target_filepath = filename
                p = Path(filename)
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
        outtmpl = str(self.dest_folder / "%(title)s [%(id)s].%(ext)s")

        ydl_opts: Dict[str, Any] = {
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
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(self.url, download=True)
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
                logger.error(f"yt-dlp execution error: {e}")
                self.status = "Hata"
                self.error_message = str(e)
                self._notify_status("Hata", str(e))
