"""Bounded access refresh; cancellation must never restart a download."""
import tempfile
import unittest
from unittest.mock import patch
from video_downloader import VideoDownloadTask

class AccessTests(unittest.TestCase):
    def run_failure(self,error,cancel=False):
        with tempfile.TemporaryDirectory() as folder:
            task=VideoDownloadTask(1,'https://example.com/video',folder)
            if cancel:task._cancel_flag.set()
            with patch('video_downloader.yt_dlp.YoutubeDL') as factory:
                factory.return_value.__enter__.return_value.extract_info.side_effect=RuntimeError(error)
                task._run()
                return task,factory.call_count
    def test_forbidden_refreshes_only_once(self):
        task,count=self.run_failure('HTTP Error 403: Forbidden')
        self.assertEqual(count,2)
        self.assertEqual(task.status,'Hata')
    def test_other_error_does_not_refresh(self):
        task,count=self.run_failure('HTTP Error 401: Unauthorized')
        self.assertEqual(count,1)
        self.assertEqual(task.status,'Hata')
    def test_cancellation_does_not_refresh(self):
        task,count=self.run_failure('HTTP Error 403: Forbidden',cancel=True)
        self.assertEqual(count,1)
        self.assertEqual(task.status,'İptal Edildi')
