"""Validated settings backups, excluding all credentials and download history."""
import json
from pathlib import Path
from capture_policy import normalize_domain
from utils import DEFAULT_SETTINGS


def validate_settings(data):
    if not isinstance(data,dict):raise ValueError('Ayar dosyası geçersiz.')
    result={}
    for key,value in data.items():
        if key not in DEFAULT_SETTINGS:continue
        if key=='capture_paused_until':
            import math
            if type(value) not in (int,float) or not math.isfinite(value) or value < -1:raise ValueError('Geçersiz yakalama süresi.')
            result[key]=value
            continue
        default=DEFAULT_SETTINGS[key]
        if type(value) is not type(default):raise ValueError(f'Geçersiz ayar: {key}')
        result[key]=value
    if 'excluded_sites' in result:
        result['excluded_sites']=sorted(set(normalize_domain(d) for d in result['excluded_sites']))
    for key in ('capture_extensions','monitored_extensions','visible_columns'):
        if key in result and any(not isinstance(v,str) or len(v)>80 for v in result[key]):raise ValueError('Geçersiz liste.')
    for key,minimum,maximum in [('default_connections',1,32),('max_simultaneous_downloads',1,10),('speed_limit_kbs',0,1000000)]:
        if key in result and not minimum<=result[key]<=maximum:raise ValueError(f'Geçersiz ayar: {key}')
    if 'theme' in result and result['theme'] not in ('light','dark','system','cosmo'):raise ValueError('Geçersiz tema.')
    return result


def export_settings(path,settings):
    data={k:v for k,v in settings.items() if k in DEFAULT_SETTINGS}
    data['capture_paused_until']=0
    Path(path).write_text(json.dumps({'format':'sdm-settings-v1','settings':data},ensure_ascii=False,indent=2),encoding='utf-8')


def import_settings(path):
    if Path(path).stat().st_size>1024*1024:raise ValueError('Ayar yedeği çok büyük.')
    data=json.loads(Path(path).read_text(encoding='utf-8'))
    if data.get('format')!='sdm-settings-v1':raise ValueError('Bu dosya bir SDM ayar yedeği değil.')
    return validate_settings(data['settings'])
