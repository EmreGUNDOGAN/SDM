"""Read-only inspection adapter for per-link UI cards; no download decisions."""
def inspect_url(url,force_video=False):
    from video_downloader import is_video_site,format_options,tool_options
    if not force_video and not is_video_site(url):
        from browser_files import prepare_transfer
        return prepare_transfer(url)
    import yt_dlp
    with yt_dlp.YoutubeDL(dict(quiet=True,no_warnings=True,skip_download=True,
            extract_flat='in_playlist',playlistend=100,socket_timeout=12,**tool_options())) as ydl:
        info=ydl.extract_info(url,download=False)
    if not info or info.get('has_drm'):raise ValueError('Kaynak incelenemedi veya korumalı.')
    entries=info.get('entries')
    if entries:
        links=[]
        for entry in entries:
            if not entry:continue
            link=entry.get('webpage_url') or entry.get('url')
            if link and not link.startswith('http') and entry.get('id'):link='https://www.youtube.com/watch?v='+entry['id']
            if link:links.append((link,entry.get('title','Video')))
        return dict(kind='playlist',entries=links,title=info.get('title') or '')
    return dict(kind='video',duration=info.get('duration'),thumbnail=info.get('thumbnail'),**format_options(info))
