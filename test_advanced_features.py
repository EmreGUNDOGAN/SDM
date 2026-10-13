import unittest
import tempfile
import threading
import zipfile
import stat
from pathlib import Path
from datetime import datetime
from unittest.mock import patch
from queue_rules import default_queue,scheduled_active,validate_queues,ordered_records
from archive_tools import extract_archive,safe_member
from antivirus import parse_report
from feature_ui import SpeedHistory
from file_tools import ensure_space,organization_plan,move_plan,seconds

class AdvancedFeatureTests(unittest.TestCase):
    def test_overnight_uses_start_day_and_exact_stop(self):
        q=dict(default_queue(),enabled=True,days=[0],start='23:00',stop='06:00')
        self.assertTrue(scheduled_active(q,datetime(2026,10,12,23,30)))
        self.assertTrue(scheduled_active(q,datetime(2026,10,13,5,59)))
        self.assertFalse(scheduled_active(q,datetime(2026,10,13,6,0)))
        self.assertFalse(scheduled_active(q,datetime(2026,10,14,2,0)))
    def test_queue_validation_and_priority(self):
        with self.assertRaises(ValueError):validate_queues([default_queue(),default_queue()])
        records=[{'id':1,'priority':0},{'id':2,'priority':1},{'id':3,'priority':-1}]
        self.assertEqual([r['id'] for r in ordered_records(records)],[2,1,3])
    def test_zip_extraction_preserves_archive_and_nested_content(self):
        with tempfile.TemporaryDirectory() as folder:
            source=Path(folder)/'test.zip'
            with zipfile.ZipFile(source,'w') as z:z.writestr('sub/a.txt',b'contents')
            target=extract_archive(source)
            self.assertEqual((target/'sub/a.txt').read_bytes(),b'contents');self.assertTrue(source.exists())
    def test_archive_rejects_traversal_device_and_symlink(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            for name in ('../escape','C:/escape','//host/share','a:stream','CON.txt','a/../../escape','a. /file'):
                with self.subTest(name=name),self.assertRaises(ValueError):safe_member(root,name)
            source=root/'link.zip';info=zipfile.ZipInfo('link');info.external_attr=(stat.S_IFLNK|0o777)<<16
            with zipfile.ZipFile(source,'w') as z:z.writestr(info,'../escape')
            with self.assertRaises(ValueError):extract_archive(source)
            self.assertEqual(list(root.iterdir()),[source])
    def test_kaspersky_requires_verified_counters(self):
        self.assertIn('doğrulanamadı',parse_report('',0))
        self.assertIn('doğrulanamadı',parse_report('; Processed objects: 1\n; Total OK: 0\n; Total skipped: 1',0))
        self.assertIn('şüpheli',parse_report('; Total detected: 1',0))
        self.assertIn('tehdit bulunmadı',parse_report('; Processed objects: 1\n; Total OK: 1\n; Total detected: 0\n; Suspicions: 0\n; Total skipped: 0\n; Password protected: 0\n; Corrupted: 0\n; Errors: 0',0))
    def test_speed_average_excludes_pauses_and_restart_baseline(self):
        h=SpeedHistory();h.sample(0,1000,100,True);h.sample(1,1100,100,True);h.sample(2,1100,0,False);h.sample(10,1100,100,True);h.sample(11,1300,200,True)
        self.assertEqual(h.average,150);self.assertEqual(h.active_seconds,2)
    def test_disk_check_fails_before_writing(self):
        with tempfile.TemporaryDirectory() as folder,patch('file_tools.shutil.disk_usage',return_value=type('Usage',(),{'free':100})()):
            with self.assertRaises(OSError):ensure_space(Path(folder)/'file',1000)
    def test_organization_excludes_active_and_temp(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);active=root/'active.mp4';active.write_bytes(b'a');(root/'done.zip').write_bytes(b'd');(root/'done.zip.sdm-1.part.0').write_bytes(b't')
            plan=organization_plan(root,[active]);self.assertEqual(len(plan),1);move_plan(plan)
            self.assertTrue(active.exists());self.assertTrue((root/'Arşivler/done.zip').exists())
    def test_media_time_input(self):
        self.assertEqual(seconds('02:15'),135)
        for value in ('-1','00:90','nan'):
            with self.assertRaises(ValueError):seconds(value)

    def test_named_queue_limits_and_priority_dispatch(self):
        from advanced_actions import AdvancedActions
        from unittest.mock import MagicMock
        q1=dict(default_queue('Video'),limit=1);q2=dict(default_queue('Dosya'),limit=2)
        records=[dict(id=1,priority=0,queue_name='Video',status='Kuyrukta'),dict(id=2,priority=1,queue_name='Video',status='Kuyrukta'),dict(id=3,priority=-1,queue_name='Dosya',status='Kuyrukta')]
        app=AdvancedActions();app.settings=dict(queues=[q1,q2],max_simultaneous_downloads=3,shutdown_after_queue=False)
        app.db=MagicMock();app.db.get_all_downloads.return_value=records;app.engine=MagicMock();app.engine.tasks={};app.video_tasks={}
        app._running_queues={'Video','Dosya'};app._scheduled_queues=set();app._queue_ids=set();app.resume_download=MagicMock(return_value=True)
        app.queue_tick_once()
        self.assertEqual([call.args[0] for call in app.resume_download.call_args_list],[2,3])
        self.assertEqual(records[0]['status'],'Kuyrukta')

if __name__=='__main__':unittest.main()
