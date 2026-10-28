"""Two real source process/tray lifecycles, inside the runner's fake profile."""
def main():
    import json,os,subprocess,sys
    from pathlib import Path
    from utils import ensure_config_dir
    root=ensure_config_dir()
    for index in range(2):
        data=root/f'desktop-{index}';data.mkdir();downloads=data/'downloads';downloads.mkdir()
        (data/'config.json').write_text(json.dumps(dict(download_dir=str(downloads),clipboard_monitoring=False,notifications_enabled=False,update_check_on_start=False,mini_hud=False)),encoding='utf-8')
        subprocess.run([sys.executable,'main.py','--package-self-test'],env=dict(os.environ,SDM_DATA_DIR=str(data)),check=True,timeout=90)
        result=json.loads((data/'package-result.json').read_text(encoding='utf-8'))
        assert result['views']==['atlas_light','atlas_dark','odak_light','odak_dark'] and result['tray_visible']
    print('Real source desktop four-view checks, native system tray complete exit and second process reopen: OK')

if __name__=='__main__':main()
