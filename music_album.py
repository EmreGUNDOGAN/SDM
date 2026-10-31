"""A YouTube Music album or list as one download: its songs run one after another."""
import json
import logging
from pathlib import Path

from video_downloader import VideoDownloadTask

logger = logging.getLogger('SDM.Music')
ALBUM_LIMIT = 200  # yt-dlp lists longer than this are cut by the inspection step anyway


def validate_entries(entries):
    """Stored song addresses of one list: http(s) strings only, bounded."""
    if not isinstance(entries, list) or not 0 < len(entries) <= ALBUM_LIMIT:
        raise ValueError('Albüm parça listesi geçersiz.')
    if not all(isinstance(url, str) and url.startswith(('https://', 'http://')) and len(url) <= 2048 for url in entries):
        raise ValueError('Albüm parça adresi geçersiz.')
    return list(entries)


def video_task(download_id, url, dest_folder, audio=None, **kwargs):
    """The right task for a stored video/music download."""
    if audio and audio.get('entries'):
        return AlbumDownloadTask(download_id, url, dest_folder, audio=audio, **kwargs)
    return VideoDownloadTask(download_id, url, dest_folder, audio=audio, **kwargs)


class AlbumDownloadTask(VideoDownloadTask):
    """One row, one progress, one completion for a whole list.

    Each song is an ordinary VideoDownloadTask run in this task's thread, so the
    music engine (bitrate, Artist/Album layout, tags, cover) is unchanged. The
    number of finished songs is kept in SDM's data folder, so pause, restart and
    resume continue with the next song.
    """

    def __init__(self, download_id, url, dest_folder, audio=None, **kwargs):
        # The row's path becomes the Artist/Album folder; songs keep the chosen download folder.
        super().__init__(download_id, url, audio.get('folder') or dest_folder, audio=audio, **kwargs)
        self.entries = validate_entries(audio['entries'])
        self.numbered = bool(audio.get('numbered'))
        self.album_folder = None
        self._song = None

    def _state_path(self):
        from utils import ensure_config_dir
        return ensure_config_dir() / 'staging' / f'album-{int(self.download_id)}.json'

    def _load_done(self):
        try:
            state = json.loads(self._state_path().read_text(encoding='utf-8'))
            if state.get('entries') == self.entries:
                return max(0, min(len(self.entries), int(state.get('done', 0)))), state.get('bytes', 0), state.get('folder')
        except (OSError, ValueError, TypeError):
            pass
        return 0, 0, None

    def _save_done(self, done, finished):
        path = self._state_path();path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(dict(entries=self.entries, done=done, bytes=finished, folder=self.album_folder)), encoding='utf-8')

    def pause(self):
        super().pause()
        if self._song:self._song._paused = True;self._song._cancel_flag.set()

    def cancel(self):
        super().cancel()
        if self._song:self._song._cancel_flag.set()

    def _name(self):
        # Artist/Album/ folder from the music engine: "Artist – Album · 12 parça".
        folder = Path(self.album_folder) if self.album_folder else None
        title = f'{folder.parent.name} – {folder.name}' if folder else 'YouTube Music'
        return f'{title} · {len(self.entries)} parça'

    def _run(self):
        done, finished, folder = self._load_done()
        self.album_folder = folder
        count = len(self.entries)
        for index in range(done, count):
            if self._cancel_flag.is_set():
                return
            song = VideoDownloadTask(self.download_id, self.entries[index], self.dest_folder, quality=self.quality,
                                     connections=self.connections,
                                     audio=dict(bitrate=self.audio['bitrate'], album=True, track=index + 1 if self.numbered else None),
                                     progress_callback=lambda did, got, total, speed, eta, status, i=index, f=finished:
                                         self._song_progress(i, f, got, total, speed, eta),
                                     status_callback=self._song_status, metadata_callback=self._song_metadata)
            self._song = song
            song._run()  # in this task's thread: one song at a time
            self._song = None
            if self._cancel_flag.is_set():
                return  # pause()/cancel() already reported the row's state
            if song.status != 'Tamamlandı':
                self.status = 'Hata';self.error_message = f'{index + 1}. parça indirilemedi: {song.error_message}'
                self._notify_status('Hata', self.error_message)
                return
            finished += song.total_bytes or 0
            self._save_done(index + 1, finished)
        self._finish(finished)

    def _finish(self, finished):
        self.downloaded_bytes = self.total_bytes = finished
        self.target_filepath = self.album_folder or str(self.dest_folder)
        if self.metadata_callback:
            self.metadata_callback(self.download_id, self._name(), self.target_filepath, finished, 'Müzik')
        self._state_path().unlink(missing_ok=True)
        self.status = 'Tamamlandı'
        if self.progress_callback:
            self.progress_callback(self.download_id, finished, finished, 0.0, 0.0, 'Tamamlandı')
        self._notify_status('Tamamlandı')

    def _song_progress(self, index, finished, got, total, speed, eta):
        # Whole-list estimate: finished songs plus this one, scaled by the songs left.
        count = len(self.entries)
        self.downloaded_bytes = finished + got
        self.total_bytes = max(self.downloaded_bytes, round((finished + max(total, got)) / (index + 1) * count))
        self.current_speed = speed
        self.eta = eta + (count - index - 1) * (eta + 5 if eta else 0)
        self.unobserved_method = f'Parça {index + 1}/{count}'
        if self.progress_callback:
            self.progress_callback(self.download_id, self.downloaded_bytes, self.total_bytes, speed, self.eta, 'İndiriliyor')

    def _song_status(self, did, status, error):
        # Only the row's own transitions reach SDM; a song's "Tamamlandı" is not the album's.
        if status in ('İndiriliyor', 'Dönüştürülüyor') and status != self.status and not self._cancel_flag.is_set():
            self.status = status;self._notify_status(status)

    def _song_metadata(self, did, filename, filepath, filesize, category):
        parent = Path(filepath).parent
        if parent != self.dest_folder and not self.album_folder:
            self.album_folder = str(parent)
            if self.metadata_callback:
                self.metadata_callback(self.download_id, self._name(), self.album_folder, self.total_bytes, 'Müzik')
