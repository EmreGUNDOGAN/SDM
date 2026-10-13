"""Use SDM byte-range transfers for eligible yt-dlp HTTP video/audio streams."""
import hashlib
import time
from pathlib import Path
from yt_dlp.downloader.http import HttpFD
from download_engine import DownloadTask


class SDMHttpFD(HttpFD):
    def real_download(self, filename, info_dict):
        owner = self.params.get('sdm_task')
        if not owner or filename == '-' or self.params.get('test'):
            return super().real_download(filename, info_dict)
        target = Path(self.temp_name(filename))
        # Stable identity across pause/resume; the containing video folder is per-download.
        identity = int(hashlib.sha256(str(target).encode()).hexdigest()[:8], 16)
        task = DownloadTask(identity, info_dict['url'], target,
                            num_connections=owner.connections, headers=info_dict.get('http_headers'))
        if not task.inspect_remote_file() or not task.supports_ranges or task.filesize < 1024 * 1024:
            return super().real_download(filename, info_dict)
        def progress(did, received, total, speed, eta, state):
            if owner._cancel_flag.is_set():
                task.pause()
                return
            self._hook_progress({'status':'downloading', 'downloaded_bytes':received,
                'total_bytes':total, 'filename':filename, 'tmpfilename':str(target),
                'speed':speed, 'eta':eta}, info_dict)
        task.progress_callback = progress
        owner._range_active=True
        task.start()
        while task._worker.is_alive():
            if owner._cancel_flag.is_set():
                task.pause()
            task._worker.join(.1)
        owner._range_active=False
        if owner._cancel_flag.is_set():
            raise RuntimeError('İndirme duraklatıldı veya iptal edildi')
        if task.status != 'Tamamlandı':
            # A host may advertise ranges then reject them. Retry with yt-dlp's native HTTP path.
            task._cleanup_parts()
            return super().real_download(filename, info_dict)
        self.try_rename(str(target), filename)
        self._hook_progress({'status':'finished', 'downloaded_bytes':task.filesize,
                             'total_bytes':task.filesize, 'filename':filename}, info_dict)
        return True


def install_video_http_downloader():
    from yt_dlp.downloader import PROTOCOL_MAP
    PROTOCOL_MAP['http'] = SDMHttpFD
    PROTOCOL_MAP['https'] = SDMHttpFD
