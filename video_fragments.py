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
        return super().real_download(filename,info_dict)
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

class ObservedHlsFD(FragmentDetailsMixin,HlsFD):details_method='HLS parçaları'
class ObservedDashFD(FragmentDetailsMixin,DashSegmentsFD):details_method='DASH parçaları'
