import tempfile
import unittest
from theme_catalog import THEMES,theme_key,theme_name,palette,migrate_settings
from video_section import parse_time,validate_section
from preferences import validate_settings

class ThemeTests(unittest.TestCase):
    def test_four_design_mode_combinations_and_names(self):
        self.assertEqual(len(THEMES),4)
        for key in THEMES:
            design,mode=key.split('_')
            values=validate_settings({'design':design,'color_mode':mode})
            self.assertEqual(theme_key(values),key)
            self.assertIn('Açık' if mode=='light' else 'Koyu',theme_name(key,'tr'))
            self.assertIn(mode.title(),theme_name(key,'en'))
            self.assertIn('Pro' if design=='atlas' else 'Akışı',theme_name(key,'en'))
        self.assertEqual(theme_key({'theme':'dark'}),'atlas_dark')
        self.assertEqual(palette('atlas_dark')['accent'],palette('odak_dark')['accent'])
        self.assertNotEqual(palette('atlas_light')['bg'],palette('atlas_dark')['bg'])
    def test_time_bounds(self):
        self.assertEqual(parse_time('02:00:00'),7200)
        self.assertEqual(parse_time('03:00:00'),10800)
        for text in ('02:99:00','a:b','-1:00'):
            with self.assertRaises(ValueError):parse_time(text)
        for section in ({'start':5,'end':5},{'start':float('nan'),'end':6},{'start':0,'end':20}):
            with self.assertRaises(ValueError):validate_section(section,10)
        self.assertEqual(validate_section({'start':2,'end':4,'exact':True},8)['end'],4)

if __name__=='__main__':unittest.main()
