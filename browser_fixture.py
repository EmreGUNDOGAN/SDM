"""Isolated test server for the browser integration test; not packaged."""
import json
from pathlib import Path
from unittest.mock import patch
from browser_bridge import BrowserBridge, PORT

def fake_formats(url):
    return {'title': 'Browser integration test', 'qualities': [
        {'height': 1080, 'label': '1080p'}, {'height': 720, 'label': '720p'}], 'audio': True}

with patch('video_downloader.fetch_video_formats', side_effect=fake_formats):
    bridge = BrowserBridge()
    bridge.start()
    print(json.dumps({'token': bridge.token, 'port': PORT}), flush=True)
    try:
        while True:
            item = bridge.pending.get()
            print(json.dumps(item), flush=True)
    except KeyboardInterrupt:
        bridge.stop()
