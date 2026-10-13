"""Explicit, local Kaspersky file scan; never infer safety from exit code alone."""
import os
from pathlib import Path
import re
import subprocess
import uuid
from file_tools import NO_WINDOW
from utils import ensure_config_dir

def find_kaspersky():
    for base in (os.environ.get('ProgramFiles(x86)','C:/Program Files (x86)'),os.environ.get('ProgramFiles','C:/Program Files')):
        root=Path(base)/'Kaspersky Lab'
        if root.is_dir():
            for folder in sorted(root.iterdir(),reverse=True):
                if 'vpn' in folder.name.lower() or 'password' in folder.name.lower():continue
                candidate=folder/'avp.com'
                if candidate.is_file():return candidate
    raise ValueError('Kaspersky bulunamadı. Desteklenen Kaspersky Windows uygulamasını kurmalısın.')

def parse_report(text,code):
    fields={name:int(value) for name,value in re.findall(r';\s*(Processed objects|Total OK|Total detected|Suspicions|Total skipped|Password protected|Corrupted|Errors):\s*(\d+)',text)}
    if fields.get('Total detected',0) or fields.get('Suspicions',0):return 'Tehdit veya şüpheli nesne bulundu. Kaspersky uygulamasındaki raporu incele.'
    required={'Processed objects','Total OK','Total detected','Suspicions','Total skipped','Password protected','Corrupted','Errors'}
    if code!=0 or not required.issubset(fields) or not fields.get('Processed objects') or fields.get('Total OK',0)!=fields['Processed objects'] or any(fields.get(k,0) for k in ('Total skipped','Password protected','Corrupted','Errors')):
        return 'Tarama sonucu tam doğrulanamadı. Kaspersky raporunu incele; dosya temiz olarak işaretlenmedi.'
    return 'Taranan nesnelerde tehdit bulunmadı. Arşiv içeriğinin taranması Kaspersky ayarlarına bağlıdır.'

def scan_file(path):
    path=Path(path).resolve()
    if not path.is_file():raise ValueError('Dosya bulunamadı; taşınmış veya silinmiş olabilir.')
    folder=ensure_config_dir()/'scan-reports';folder.mkdir(exist_ok=True)
    report=folder/f'{uuid.uuid4().hex}.txt'
    result=subprocess.run([str(find_kaspersky()),'SCAN',str(path),'/i0','/fa','/iChecker=off','/iSwift=off',f'/RA:{report}'],capture_output=True,timeout=3600,creationflags=NO_WINDOW)
    if not report.is_file():raise ValueError('Kaspersky taraması başlatılamadı. Kaspersky izinlerini ve uygulama durumunu kontrol et.')
    raw=report.read_bytes()
    text=raw.decode('utf-16') if raw.startswith((b'\xff\xfe',b'\xfe\xff')) else raw.decode('utf-8-sig',errors='replace')
    return parse_report(text,result.returncode),report
