"""Run native UI checks sequentially in separate disposable, synthetic profiles."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parent.parent
DEFAULT=('test_ui_components.py','test_ui_alignment.py','test_ui_design_foundations.py','test_ui_031.py','test_ui_themes.py','test_ui_theme_preview.py','test_ui_atlas.py','test_ui_pano.py','test_ui_dialogs.py','test_ui_pano_completion.py','test_ui_pano_hud.py','test_ui_settings.py','test_ui_window_frame.py','test_ui_stats.py','test_ui_odak.py',
         'test_gui_transfer.py','test_cancel_remove_ui.py','test_ui_compatibility.py','test_source_desktop.py','test_ui_pano_dialogs.py','test_ui_pano_utilities.py','test_ui_pano_details.py','test_ui_pano_tools.py','test_ui_yorunge_dialogs.py','test_ui_yorunge_details.py','test_ui_yorunge_utilities.py','test_ui_yorunge_hud.py','test_ui_pano_settings.py','test_ui_yorunge_settings.py','test_ui_yorunge.py')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('scripts',nargs='*',default=list(DEFAULT))
    args=parser.parse_args();(ROOT/'build').mkdir(exist_ok=True)
    for name in args.scripts:
        script=ROOT/name
        if script.parent!=ROOT or not script.name.startswith('test_') or script.suffix!='.py':
            raise ValueError('Only root-level Python test scripts are allowed')
        with tempfile.TemporaryDirectory(prefix='sdm-ui-',dir=ROOT/'build') as folder:
            data=Path(folder);downloads=data/'downloads';downloads.mkdir()
            (data/'config.json').write_text(json.dumps(dict(
                download_dir=str(downloads),clipboard_monitoring=False,
                notifications_enabled=False,update_check_on_start=False,mini_hud=False,
                duplicate_warning=False)),encoding='utf-8')
            env=dict(os.environ,SDM_DATA_DIR=str(data),PYTHONIOENCODING='utf-8')
            print(f'Running {name} in a disposable profile',flush=True)
            subprocess.run([sys.executable,str(script)],cwd=ROOT,env=env,check=True,timeout=150)
    return 0


if __name__=='__main__':raise SystemExit(main())
