"""Yörünge instruments must use live rows, measured counts and saved columns."""
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from atlas_view import column_preferences
from yorunge_view import gauge_limit,telemetry,target
from preferences import export_settings,import_settings,validate_settings
from utils import DEFAULT_SETTINGS


class YorungeViewTests(unittest.TestCase):
    def app(self):
        task=SimpleNamespace(status='İndiriliyor',filesize=1000,segments=[SimpleNamespace(downloaded_bytes=250)],
            current_speed=2048,eta=12,transfer_snapshot=lambda:dict(rows=(),observed=False,active_count=None))
        app=SimpleNamespace(settings=dict(language='tr'),video_tasks={},engine=SimpleNamespace(get_task=lambda did:task if did==1 else None))
        record=dict(id=1,filename='synthetic.bin',filesize=900,downloaded_bytes=10,status='Kuyrukta',category='Diğer',date_added='',queue_name='Synthetic queue')
        return app,task,record

    def test_gauge_scales_in_complete_fifty_megabyte_steps(self):
        for speed,peak,expected in ((0,0,50),(50,0,50),(50.01,0,100),(1,151,200),(100,50,100)):
            self.assertEqual(gauge_limit(speed*1048576,peak*1048576),expected)

    def test_target_prefers_live_rows_and_retains_unknown_size(self):
        app,task,record=self.app();view=target(app,record)
        self.assertEqual(view['progress'],.25);self.assertEqual(view['queue'],'Synthetic queue')
        self.assertEqual(view['speed'],'2,00 KB/sn');self.assertIsNone(view['connections'])
        task.filesize=0;self.assertIsNone(target(app,record)['progress'])
        app.engine.get_task=lambda did:None;record.update(status='Tamamlandı',filesize=0)
        self.assertEqual(target(app,record)['progress'],1)

    def test_unknown_connections_are_never_manufactured(self):
        app,task,record=self.app()
        self.assertEqual(telemetry(app,[record]),dict(active=1,connections=None))
        task.transfer_snapshot=lambda:dict(rows=(),observed=True,active_count=3)
        self.assertEqual(telemetry(app,[record]),dict(active=1,connections=3))
        task.status='Duraklatıldı';self.assertEqual(telemetry(app,[record]),dict(active=0,connections=0))

    def test_columns_are_independent_and_survive_validated_backup(self):
        key,columns=column_preferences('yorunge');self.assertEqual(key,'yorunge_visible_columns')
        self.assertNotIn('size',columns);self.assertEqual(column_preferences('atlas')[0],'visible_columns')
        settings=dict(DEFAULT_SETTINGS,**{key:['filename','progress']})
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'settings.json';export_settings(path,settings)
            self.assertEqual(import_settings(path)[key],['filename','progress'])
        for value in ('filename',[1],['x'*81]):
            with self.assertRaises(ValueError):validate_settings({key:value})

    def test_preview_report_rejects_stale_pixels_sources_and_false_geometry(self):
        import copy,hashlib,json
        from PIL import Image
        from theme_catalog import palette
        from tools.report_yorunge_previews import SOURCES,STATES,validate_previews
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);sources={};previews={}
            for name in SOURCES:
                path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b'fixture')
                sources[name]=hashlib.sha256(b'fixture').hexdigest()
            for state in STATES:
                image=Image.new('RGB',(1080,640),palette('yorunge_dark')['bg'])
                for x in range(64):image.putpixel((x,20),(x,0,0))
                path=root/f'yorunge-{state}.png';image.save(path);previews[state]=hashlib.sha256(path.read_bytes()).hexdigest()
            geometry=dict(viewport=[1080,640],telemetry=[800,440],list=[800,440])
            data=dict(sources=sources,previews=previews,header_center_errors=[0,0,0],gauge_center_error=0,active_progress_cells=5,
                wide=dict(geometry,right_visible=True),compact=dict(geometry,right_visible=False))
            report=root/'yorunge-layout.json';report.write_text(json.dumps(data))
            self.assertEqual(len(validate_previews(root,root)[0]),7)
            for key,value in (('header_center_errors',[float('nan')]*3),('gauge_center_error',2),('active_progress_cells',1),('wide',dict(geometry,right_visible=False))):
                bad=copy.deepcopy(data);bad[key]=value;report.write_text(json.dumps(bad))
                with self.assertRaises(ValueError):validate_previews(root,root)
            report.write_text(json.dumps(data));(root/'yorunge_view.py').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'sources'):validate_previews(root,root)
            (root/'yorunge_view.py').write_bytes(b'fixture');(root/'yorunge-main.png').write_bytes(b'corrupt')
            with self.assertRaisesRegex(ValueError,'PNG'):validate_previews(root,root)


if __name__=='__main__':unittest.main()
