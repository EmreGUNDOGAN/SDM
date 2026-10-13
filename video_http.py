"""Use SDM byte-range transfers for eligible yt-dlp HTTP video/audio streams."""
import hashlib
import time
from pathlib import Path
from yt_dlp.downloader.http import HttpFD
from download_engine import DownloadTask
from transfer_details import stream_label

class ObservedHttpFD(HttpFD):
    """Observe the native single HTTP fallback without changing its transport."""
    def real_download(self,filename,info_dict):
        owner=self.params.get('sdm_task')
        key=self.params.get('sdm_details_key') or filename
        if owner and not self.params.get('sdm_fragment'):
            owner.transfer_details.begin(key,'Tek HTTP bağlantısı',stream_label(info_dict),self.params.get('sdm_fallback_reason',''))
        self._observed_last=None
        try:return super().real_download(filename,info_dict)
        finally:
            if owner and self._observed_last:
                row_key,index,received,total,state=self._observed_last
                if state!='Tamamlandı':state='Duraklatıldı' if owner._cancel_flag.is_set() else 'Hata'
                owner.transfer_details.progress(key,row_key,index,received,total,False,state)
    def _hook_progress(self,status,info_dict):
        owner=self.params.get('sdm_task')
        if owner:
            filename=status.get('filename','')
            self._observed_last=(filename,self.params.get('sdm_fragment_index',1),status.get('downloaded_bytes',0) or 0,status.get('total_bytes',0) or 0,'Tamamlandı' if status.get('status')=='finished' else 'İndiriliyor')
            owner.transfer_details.progress(self.params.get('sdm_details_key') or filename,filename,
                self.params.get('sdm_fragment_index',1),status.get('downloaded_bytes',0) or 0,
                status.get('total_bytes',0) or 0,status.get('status')=='downloading',
                'Tamamlandı' if status.get('status')=='finished' else 'İndiriliyor')
        super()._hook_progress(status,info_dict)

def native_http(downloader,filename,info_dict,reason):
    fallback=ObservedHttpFD(downloader.ydl,dict(downloader.params,sdm_fallback_reason=reason))
    fallback._progress_hooks=list(downloader._progress_hooks)
    return fallback.real_download(filename,info_dict)


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
        task.request_chunk_size=max(0,int(info_dict.get('downloader_options',{}).get('http_chunk_size') or 0))
        if not task.inspect_remote_file():return native_http(self,filename,info_dict,'Paralel aktarım ön kontrolü tamamlanamadı.')
        if not task.supports_ranges:return native_http(self,filename,info_dict,'Sunucu HTTP Range desteği vermiyor.')
        if task.filesize < 1024 * 1024:return native_http(self,filename,info_dict,'Akış küçük veya boyutu bilinmiyor; tek bağlantı kullanılıyor.')
        owner.transfer_details.begin(filename,'HTTP Range',stream_label(info_dict),task=task)
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
            return native_http(self,filename,info_dict,'Sunucu paralel aktarımı tamamlayamadı; normal HTTP’ye dönüldü.')
        self.try_rename(str(target), filename)
        self._hook_progress({'status':'finished', 'downloaded_bytes':task.filesize,
                             'total_bytes':task.filesize, 'filename':filename}, info_dict)
        return True


def install_video_http_downloader():
    from yt_dlp.downloader import PROTOCOL_MAP
    PROTOCOL_MAP['http'] = SDMHttpFD
    PROTOCOL_MAP['https'] = SDMHttpFD
    from video_fragments import ObservedHlsFD,ObservedDashFD
    PROTOCOL_MAP['m3u8_native']=ObservedHlsFD
    PROTOCOL_MAP['http_dash_segments']=ObservedDashFD
    PROTOCOL_MAP['http_dash_segments_generator']=ObservedDashFD
