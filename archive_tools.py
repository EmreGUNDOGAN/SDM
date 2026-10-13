"""Extract into a new directory, rejecting traversal, links and device names."""
from pathlib import Path,PureWindowsPath
import shutil
import stat
import subprocess
import zipfile
from file_tools import tool_path,NO_WINDOW,ensure_space
from utils import get_unique_filepath

def safe_member(root,name):
    name=name.replace('\\','/')
    path=PureWindowsPath(name)
    if path.is_absolute() or path.drive or any(part in ('..','.') or ':' in part for part in name.split('/')):raise ValueError('Arşivde güvenli olmayan dosya yolu var.')
    for part in path.parts:
        if part.rstrip(' .')!=part or part.split('.')[0].upper() in {'CON','PRN','AUX','NUL',*[f'COM{i}' for i in range(1,10)],*[f'LPT{i}' for i in range(1,10)]}:raise ValueError('Arşivde geçersiz dosya adı var.')
    target=(root/Path(name)).resolve()
    if not target.is_relative_to(root.resolve()) or target==root.resolve():raise ValueError('Arşiv yolu hedef dışına çıkıyor.')
    return target

def extract_archive(source,folder=None):
    source=Path(source).resolve()
    parent=Path(folder).resolve() if folder else source.parent
    root=get_unique_filepath(parent,source.stem+' · çıkarıldı')
    root.mkdir(parents=True,exist_ok=False)
    try:
        if source.suffix.lower()=='.zip':
            with zipfile.ZipFile(source) as archive:
                members=archive.infolist()
                if len(members)>100000:raise ValueError('Arşiv çok fazla dosya içeriyor.')
                targets=[safe_member(root,item.filename.rstrip('/')) for item in members]
                if len({str(target).casefold() for target in targets})!=len(targets):raise ValueError('Arşivde çakışan dosya adları var.')
                total=sum(item.file_size for item in members);ensure_space(root/'output',total,1)
                for item,target in zip(members,targets):
                    if stat.S_ISLNK(item.external_attr>>16):raise ValueError('Arşiv bağlantıları desteklenmiyor.')
                    if item.flag_bits&1:raise ValueError('Parolalı arşiv; önce parolayla elle açmalısın.')
                    if item.is_dir():target.mkdir(parents=True,exist_ok=True);continue
                    target.parent.mkdir(parents=True,exist_ok=True)
                    with archive.open(item) as inp,target.open('xb') as out:shutil.copyfileobj(inp,out,1024*1024)
        elif source.suffix.lower()=='.rar':
            executable=tool_path('7z')
            listing=subprocess.run([executable,'l','-slt','-ba','-sccUTF-8','--',str(source)],capture_output=True,text=True,encoding='utf-8',timeout=90,creationflags=NO_WINDOW)
            if listing.returncode:raise ValueError('RAR okunamadı; bozuk veya parolalı olabilir.')
            entries=[]
            for block in listing.stdout.split('\n\n'):
                data=dict(line.split(' = ',1) for line in block.splitlines() if ' = ' in line)
                if 'Path' not in data:continue
                if data.get('Encrypted')=='+' or any('link' in k.lower() for k in data):raise ValueError('Parolalı veya bağlantı içeren RAR desteklenmiyor.')
                entries.append((data,safe_member(root,data['Path'])))
            if not entries or len(entries)>100000:raise ValueError('RAR dosya listesi doğrulanamadı.')
            if len({str(target).casefold() for _,target in entries})!=len(entries):raise ValueError('Arşivde çakışan yollar var.')
            ensure_space(root/'output',sum(int(d.get('Size','0')) for d,_ in entries),1)
            for data,target in entries:
                if data.get('Folder')=='+':target.mkdir(parents=True,exist_ok=True);continue
                target.parent.mkdir(parents=True,exist_ok=True)
                with target.open('xb') as out:
                    result=subprocess.run([executable,'x','-so','-y','-spd','--',str(source),data['Path']],stdout=out,stderr=subprocess.DEVNULL,timeout=600,creationflags=NO_WINDOW)
                if result.returncode or target.stat().st_size!=int(data.get('Size','0')):raise ValueError('RAR çıkarma tamamlanamadı.')
        else:raise ValueError('Otomatik çıkarma ZIP ve RAR içindir.')
        return root
    except Exception:
        # Only the freshly created, verified destination is removed.
        if root.resolve().parent==parent and root!=parent:shutil.rmtree(root)
        raise
