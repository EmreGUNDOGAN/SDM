import copy
import hashlib
from pathlib import Path
import tempfile
import unittest
from tools.report_pano_previews import SOURCES,validate_measurements


class PanoReportTests(unittest.TestCase):
    def test_source_drift_and_geometry_regressions_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            for name in SOURCES:
                path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b'fixture')
            data=dict(sources={name:hashlib.sha256(b'fixture').hexdigest() for name in SOURCES},
                count_center_errors=[0,.5,1,1.5],metric_baseline_spread=0,
                wide=dict(viewport=[1440,900],hero=[670,400],list=[1000,350]),
                compact=dict(viewport=[1080,640],hero=[1000,400],list=[1000,350]))
            self.assertIs(validate_measurements(data,root),data)
            for field,value in (('count_center_errors',[0,0,0,2]),('count_center_errors',[0,0,0,float('nan')]),
                    ('count_center_errors',[]),('metric_baseline_spread',4),('metric_baseline_spread',None),
                    ('wide',dict(viewport=[1440,900],hero=[1800,400],list=[1000,350]))):
                bad=copy.deepcopy(data);bad[field]=value
                with self.subTest(field=field,value=value),self.assertRaises(ValueError):validate_measurements(bad,root)
            (root/SOURCES[0]).write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'Stale'):validate_measurements(data,root)


if __name__=='__main__':unittest.main()
