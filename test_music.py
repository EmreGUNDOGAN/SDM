"""Music mode: options, Artist/Album layout, ID3 tags and cover art, and a real
yt-dlp + FFmpeg MP3 download from a local HTTP server (no network, no user data)."""
import http.server
import subprocess
import tempfile
import threading
import unittest
from functools import partial
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from PIL import Image

import music
from file_tools import NO_WINDOW, tool_path

YTM = dict(title='Song (Official Audio)', track='Song', artists=['Artist One', 'Feat Two'], album='Album: Live',
           release_year=2024, track_number=4)


def image_bytes(fmt, size=(320, 180), color=(200, 30, 60)):
    out = BytesIO();Image.new('RGB', size, color).save(out, fmt);return out.getvalue()


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):pass


class Response:
    def __init__(self, content):self.content = content
    def raise_for_status(self):pass


class MusicOptionsTest(unittest.TestCase):
    def test_validate_audio_defaults_and_limits(self):
        self.assertEqual(music.validate_audio(None), dict(bitrate=192, album=False, track=None))
        self.assertEqual(music.validate_audio(dict(bitrate='320', album=1, track='7')), dict(bitrate=320, album=True, track=7))
        for bad in (dict(bitrate=64), dict(bitrate=999), dict(track=0), dict(track=10000)):
            with self.assertRaises(ValueError):music.validate_audio(bad)

    def test_tags_prefer_music_fields(self):
        facts = music.tags(YTM)
        self.assertEqual((facts['title'], facts['artist'], facts['album'], facts['track'], facts['year']), ('Song', 'Artist One', 'Album: Live', 4, '2024'))
        self.assertEqual(music.tags(YTM, track=9)['track'], 9)  # playlist position wins over site data
        plain = music.tags(dict(title='Clip', uploader='Channel, Topic'))
        self.assertEqual((plain['artist'], plain['album'], plain['track']), ('Channel', '', None))

    def test_album_path_layout_and_fallback(self):
        root = Path('C:/Music')
        self.assertEqual(music.album_path(root, YTM), root / 'Artist One' / 'Album_ Live' / '04 - Song.mp3')
        self.assertEqual(music.album_path(root, dict(YTM, track_number=None)), root / 'Artist One' / 'Album_ Live' / 'Song.mp3')
        self.assertEqual(music.album_path(root, dict(title='A/B?')), root / 'A_B_.mp3')  # no album: stay flat

    def test_cover_is_square_jpeg_from_webp(self):
        data = music.cover_jpeg(image_bytes('WEBP', (1280, 720)))
        image = Image.open(BytesIO(data))
        self.assertEqual((image.format, image.size), ('JPEG', (720, 720)))
        self.assertIsNone(music.fetch_cover(dict(title='x')))
        self.assertEqual(Image.open(BytesIO(music.fetch_cover(dict(thumbnail='u'), get=lambda url: Response(image_bytes('PNG'))))).format, 'JPEG')


class MusicFileTest(unittest.TestCase):
    def setUp(self):
        self.folder = Path(tempfile.mkdtemp(prefix='sdm-music-'))
        self.addCleanup(lambda: __import__('shutil').rmtree(self.folder, ignore_errors=True))
        self.source = self.folder / 'web' / 'tone.wav';self.source.parent.mkdir()
        subprocess.run([tool_path('ffmpeg'), '-v', 'error', '-f', 'lavfi', '-i', 'sine=frequency=440:duration=2', str(self.source)],
                       check=True, creationflags=NO_WINDOW)
        (self.source.parent / 'cover.webp').write_bytes(image_bytes('WEBP', (640, 360)))

    def read_tags(self, path):
        from mutagen.id3 import ID3
        tag = ID3(path)
        return {key: str(tag[key]) for key in ('TIT2', 'TPE1', 'TALB', 'TRCK', 'TDRC') if key in tag}, tag.getall('APIC')

    def test_write_tags_keeps_audio_and_adds_cover(self):
        mp3 = self.folder / 'tone.mp3'
        subprocess.run([tool_path('ffmpeg'), '-v', 'error', '-i', str(self.source), '-c:a', 'libmp3lame', '-b:a', '128k', str(mp3)],
                       check=True, creationflags=NO_WINDOW)
        music.write_tags(mp3, YTM, cover=music.cover_jpeg(image_bytes('PNG')))
        values, covers = self.read_tags(mp3)
        self.assertEqual(values, dict(TIT2='Song', TPE1='Artist One', TALB='Album: Live', TRCK='4', TDRC='2024'))
        self.assertEqual((len(covers), covers[0].mime, covers[0].type), (1, 'image/jpeg', 3))
        music.write_tags(mp3, YTM, cover=music.cover_jpeg(image_bytes('PNG')))  # re-tagging replaces, never stacks
        self.assertEqual(len(self.read_tags(mp3)[1]), 1)

    def test_real_download_uses_bitrate_album_layout_and_tags(self):
        from video_downloader import VideoDownloadTask
        server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), partial(QuietHandler, directory=str(self.source.parent)))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close);self.addCleanup(server.shutdown)
        base = f'http://127.0.0.1:{server.server_port}/'
        import yt_dlp
        real = yt_dlp.YoutubeDL.extract_info
        def extract(ydl, url, *args, **kwargs):
            # The generic extractor knows no artist/album; add what YouTube Music reports.
            info = real(ydl, url, *args, **kwargs)
            return dict(info, **YTM, thumbnail=base + 'cover.webp') if kwargs.get('download') is False else info
        out = self.folder / 'out';done = []
        task = VideoDownloadTask(1, base + 'tone.wav', out, quality='Yalnızca Ses (MP3)', audio=dict(bitrate=128, album=True, track=2),
                                 status_callback=lambda did, status, message: done.append((status, message)))
        profile = self.folder / 'profile'
        with patch.object(yt_dlp.YoutubeDL, 'extract_info', extract), patch('utils.CONFIG_DIR', profile):
            task._run()
        target = out / 'Artist One' / 'Album_ Live' / '02 - Song.mp3'
        self.assertTrue(target.is_file(), (done, sorted(p.relative_to(out) for p in out.rglob('*'))))
        # The work folder lives in SDM's data folder and is removed after success.
        self.assertEqual(sorted(p.relative_to(out) for p in out.rglob('*') if p.is_file()), [target.relative_to(out)])
        self.assertTrue((profile / 'staging').is_dir() and not any((profile / 'staging').iterdir()))
        probe = subprocess.run([tool_path('ffprobe'), '-v', 'error', '-select_streams', 'a:0', '-show_entries', 'stream=bit_rate',
                                '-of', 'csv=p=0', str(target)], capture_output=True, text=True, creationflags=NO_WINDOW)
        self.assertEqual(probe.stdout.strip(), '128000')
        values, covers = self.read_tags(target)
        self.assertEqual((values['TPE1'], values['TALB'], values['TRCK']), ('Artist One', 'Album: Live', '2'))
        self.assertEqual(Image.open(BytesIO(covers[0].data)).size, (360, 360))

    def test_album_is_one_row_songs_in_order_and_resumes(self):
        import json
        from music_album import video_task, AlbumDownloadTask
        server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), partial(QuietHandler, directory=str(self.source.parent)))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close);self.addCleanup(server.shutdown)
        base = f'http://127.0.0.1:{server.server_port}/'
        import yt_dlp
        real = yt_dlp.YoutubeDL.extract_info
        def extract(ydl, url, *args, **kwargs):
            info = real(ydl, url, *args, **kwargs)
            return dict(info, **YTM, thumbnail=base + 'cover.webp') if kwargs.get('download') is False else info
        out = self.folder / 'out';profile = self.folder / 'profile';entries = [base + 'tone.wav?1', base + 'tone.wav?2', base + 'tone.wav?3']
        events = [];metadata = []
        audio = dict(bitrate=128, album=True, track=None, entries=entries, numbered=True, folder=str(out))
        def task():
            # The stored row path is the album folder after the first song; the songs still use `folder`.
            return video_task(7, base + 'list', out / 'Artist One' / 'Album_ Live', quality='Yalnızca Ses (MP3)', audio=audio,
                              status_callback=lambda did, status, message: events.append(status),
                              metadata_callback=lambda did, name, path, size, cat: metadata.append((name, path, cat)))
        album = out / 'Artist One' / 'Album_ Live'
        with patch.object(yt_dlp.YoutubeDL, 'extract_info', extract), patch('utils.CONFIG_DIR', profile):
            first = task();self.assertIsInstance(first, AlbumDownloadTask)
            # Pause after the first song: the row stays paused and remembers one finished song.
            original = first._save_done
            def pause_after(done, finished):
                original(done, finished)
                if done == 1:first.pause()
            first._save_done = pause_after;first._run()
            self.assertEqual(first.status, 'Duraklatıldı')
            self.assertEqual(json.loads((profile / 'staging' / 'album-7.json').read_text(encoding='utf-8'))['done'], 1)
            self.assertEqual(sorted(p.name for p in album.iterdir()), ['01 - Song.mp3'])
            events.clear();second = task();second._run()
        self.assertEqual(second.status, 'Tamamlandı')
        self.assertEqual(sorted(p.name for p in album.iterdir()), ['01 - Song.mp3', '02 - Song.mp3', '03 - Song.mp3'])
        self.assertEqual(events.count('Tamamlandı'), 1)   # one completion for the whole list, not one per song
        self.assertEqual(metadata[-1], ('Artist One – Album_ Live · 3 parça', str(album), 'Müzik'))
        self.assertEqual(self.read_tags(album / '03 - Song.mp3')[0]['TRCK'], '3')
        self.assertFalse((profile / 'staging' / 'album-7.json').exists())
        self.assertEqual(list((profile / 'staging').iterdir()), [])
        with self.assertRaises(ValueError):video_task(8, base, out, quality='Yalnızca Ses (MP3)', audio=dict(audio, entries=['file:///C:/x']))


if __name__ == '__main__':
    unittest.main()
