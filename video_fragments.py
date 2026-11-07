"""Observe native HLS/DASH fragment workers without replacing their download logic."""
from pathlib import Path
from yt_dlp.downloader.hls import HlsFD
from yt_dlp.downloader.dash import DashSegmentsFD
from video_http import ObservedHttpFD
from transfer_details import stream_label

class FragmentDetailsMixin:
    def real_download(self,filename,info_dict):
        owner=self.params.get('sdm_task')
        if owner:owner.transfer_details.begin(filename,self.details_method,stream_label(info_dict))
        self._stream_context=None
        try:return super().real_download(filename,info_dict)
        finally:
            # A denied fragment/key can unwind the native downloader before its
            # normal completion path closes the partial output (Windows locks).
            if self._stream_context:
                stream=self._stream_context.get('dest_stream')
                if stream is not None and not stream.closed:stream.close()

    def _prepare_frag_download(self,ctx):
        result=super()._prepare_frag_download(ctx)
        if getattr(self.params.get('sdm_task'),'stream',None) is not None:self._stream_context=ctx
        return result
    def _download_fragment(self,ctx,frag_url,info_dict,headers=None,request_data=None):
        owner=self.params.get('sdm_task')
        if not owner:return super()._download_fragment(ctx,frag_url,info_dict,headers,request_data)
        key=ctx['filename'];index=ctx['fragment_index'];filename=f"{ctx['tmpfilename']}-Frag{index}"
        owner.transfer_details.ensure(key,self.details_method,stream_label(info_dict))
        # Concurrent yt-dlp workers already receive a copy of ctx. A private HTTP
        # downloader for each worker keeps byte counters and hooks attributable.
        original=ctx['dl']
        monitored=ObservedHttpFD(self.ydl,dict(original.params,sdm_task=owner,sdm_fragment=True,
            sdm_details_key=key,sdm_fragment_index=index,sdm_stream_label=stream_label(info_dict)))
        monitored._progress_hooks=list(original._progress_hooks);ctx['dl']=monitored
        owner.transfer_details.progress(key,filename,index,0,0,False,'Bağlanıyor')
        success=False
        try:
            success=super()._download_fragment(ctx,frag_url,info_dict,headers,request_data)
            return success
        finally:
            rows=next((s['rows'] for s in owner.transfer_details.snapshot() if s['key']==key),[])
            row=next((r for r in rows if r['index']==index),{})
            received=row.get('received',0);total=row.get('total',0)
            if success and Path(filename).is_file():received=Path(filename).stat().st_size;total=total or received
            owner.transfer_details.progress(key,filename,index,received,total,False,'Tamamlandı' if success else 'Duraklatıldı' if owner._cancel_flag.is_set() else 'Hata')

class GuardedHlsFD(FragmentDetailsMixin,HlsFD):
    details_method='HLS parçaları'

    @staticmethod
    def can_download(manifest, info_dict, allow_unplayable_formats=False):
        from stream_media import StreamDRMError, StreamValidationError
        from yt_dlp.downloader.hls import Cryptodome
        if HlsFD._has_drm(manifest):raise StreamDRMError()
        # Native-only: FFmpeg network fallback would bypass pinned DNS. Keep
        # ordinary site downloads' existing fallback behavior unchanged.
        if (not HlsFD.can_download(manifest, info_dict, False)
                or (not Cryptodome.AES and '#EXT-X-KEY:METHOD=AES-128' in manifest)):
            raise StreamValidationError('Bu HLS listesi yerel indirmeyi desteklemiyor')
        return True


class ObservedHlsFD(FragmentDetailsMixin,HlsFD):
    details_method='HLS parçaları'

    def real_download(self, filename, info_dict):
        if getattr(self.params.get('sdm_task'), 'stream', None) is not None:
            guarded=GuardedHlsFD(self.ydl,self.params)
            guarded._progress_hooks=list(self._progress_hooks)
            return guarded.real_download(filename,info_dict)
        return super().real_download(filename,info_dict)

class ObservedDashFD(FragmentDetailsMixin,DashSegmentsFD):details_method='DASH parçaları'
