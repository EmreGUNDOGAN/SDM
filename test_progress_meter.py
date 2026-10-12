import unittest
from concurrent.futures import ThreadPoolExecutor
from progress_meter import ProgressMeter


class MeterTests(unittest.TestCase):
    def test_constant_rate_and_warmup(self):
        clock=[0]
        meter=ProgressMeter(lambda:clock[0])
        for second in range(1,11):
            clock[0]=second
            speed,eta=meter.update(second*1000,100000)
            self.assertAlmostEqual(speed,1000)
            if second<3:self.assertIsNone(eta)
        self.assertAlmostEqual(eta,90)

    def test_burst_does_not_become_instantaneous_rate(self):
        clock=[0]
        meter=ProgressMeter(lambda:clock[0])
        for second in range(1,8):
            clock[0]=second
            meter.update(second*1000,100000)
        clock[0]=8
        speed,eta=meter.update(28000,100000)
        self.assertLess(speed,4000)
        self.assertGreater(speed,1000)

    def test_concurrent_calls_are_consistent(self):
        clock=[0]
        meter=ProgressMeter(lambda:clock[0])
        clock[0]=5
        with ThreadPoolExecutor(max_workers=8) as pool:
            values=list(pool.map(lambda _:meter.update(5000,100000),range(32)))
        self.assertEqual(len(set(values)),1)

    def test_resume_excludes_old_bytes(self):
        clock=[10]
        meter=ProgressMeter(lambda:clock[0])
        meter.reset(500000)
        clock[0]=11
        speed,eta=meter.update(501000,1000000)
        self.assertEqual(speed,1000)
        self.assertIsNone(eta)
