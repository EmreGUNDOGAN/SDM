"""Music mode: audio quality, Artist/Album layout and ID3 tags with cover art.

Tags are written by SDM after the MP3 exists (not by yt-dlp postprocessors) so
whole and section downloads get the same result. A failed tag or cover never
fails the download; the MP3 is already complete at that point.
"""
from io import BytesIO
from pathlib import Path

from file_tools import AUDIO_BITRATES
from utils import clean_filename

DEFAULT_BITRATE = 192


def validate_audio(audio):
    """Normalise the stored audio options: bitrate, album layout, track number."""
    audio = dict(audio or {})
    bitrate = int(audio.get('bitrate') or DEFAULT_BITRATE)
    if bitrate not in AUDIO_BITRATES:raise ValueError('Desteklenmeyen ses kalitesi.')
    track = audio.get('track')
    track = int(track) if track not in (None, '') else None
    if track is not None and not 1 <= track <= 9999:raise ValueError('Geçersiz parça numarası.')
    return dict(bitrate=bitrate, album=bool(audio.get('album')), track=track)


def tags(info, track=None):
    """Song facts from yt-dlp info; YouTube Music fills artist/album/track."""
    artists = info.get('artists') or []
    artist = info.get('artist') or (artists[0] if artists else None) or info.get('creator') or info.get('uploader') or info.get('channel')
    artist = str(artist).split(',')[0].strip() if artist else ''
    number = track or info.get('track_number')
    return dict(title=info.get('track') or info.get('title') or '', artist=artist, album=info.get('album') or '',
                track=int(number) if number else None, year=str(info.get('release_year') or '')[:4])


def album_path(folder, info, track=None):
    """Artist/Album/NN - Title.mp3 under `folder`; flat when artist or album is unknown."""
    facts = tags(info, track);folder = Path(folder)
    title = clean_filename(facts['title'] or 'Ses')
    if not (facts['artist'] and facts['album']):return folder / f'{title}.mp3'
    name = f"{facts['track']:02d} - {title}.mp3" if facts['track'] else f'{title}.mp3'
    return folder / clean_filename(facts['artist']) / clean_filename(facts['album']) / name


def cover_jpeg(data):
    """Thumbnail bytes (webp/png/jpg) as a square JPEG, centre-cropped like album art."""
    from PIL import Image
    image = Image.open(BytesIO(data)).convert('RGB');side = min(image.size)
    left, top = (image.width - side) // 2, (image.height - side) // 2
    image = image.crop((left, top, left + side, top + side))
    if side > 1000:image = image.resize((1000, 1000), Image.Resampling.LANCZOS)
    out = BytesIO();image.save(out, 'JPEG', quality=90);return out.getvalue()


def fetch_cover(info, get=None):
    url = info.get('thumbnail')
    if not url:return None
    if get is None:
        import requests
        get = lambda address: requests.get(address, timeout=15)
    response = get(url);response.raise_for_status()
    return cover_jpeg(response.content)


def write_tags(path, info, track=None, cover=None):
    """Write ID3v2.3 title/artist/album/track/year and an optional front cover."""
    from mutagen.id3 import ID3, ID3NoHeaderError, APIC, TALB, TDRC, TIT2, TPE1, TRCK
    facts = tags(info, track)
    try:tag = ID3(path)
    except ID3NoHeaderError:tag = ID3()
    for frame, value in ((TIT2, facts['title']), (TPE1, facts['artist']), (TALB, facts['album']), (TDRC, facts['year'])):
        if value:tag.setall(frame.__name__, [frame(encoding=3, text=value)])
    if facts['track']:tag.setall('TRCK', [TRCK(encoding=3, text=str(facts['track']))])
    if cover:tag.setall('APIC', [APIC(encoding=3, mime='image/jpeg', type=3, desc='Cover', data=cover)])
    tag.save(path, v2_version=3)
