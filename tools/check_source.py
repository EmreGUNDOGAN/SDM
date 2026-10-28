"""Local/CI source checks over Git's exact index, with no external service.

Compiles tracked Python, parses JavaScript via node --check, scans for high
confidence credential signatures and forbidden artifacts, then checks manifest.
This is a source scan, not a claim that all possible secrets can be detected.
"""
import re
from pathlib import Path
import subprocess
import sys
import tempfile

from source_manifest import MANIFEST,git,index_files,run

SIGNATURES = (
    ('GitHub token',r'\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{50,})\b'),
    ('AWS access key',r'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b'),
    ('OpenAI secret key',r'\bsk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{40,}\b'),
    ('private key',r'-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----'),
    ('Slack token',r'\bxox[baprs]-[A-Za-z0-9-]{20,}\b'),
)


def main():
    root=Path(git(Path.cwd(),'rev-parse','--show-toplevel').decode().strip())
    files=index_files(root);failures=[];python_count=0;js_count=0
    for path,oid in files.items():
        name=Path(path).name.lower();suffix=Path(path).suffix.lower()
        if suffix in ('.db','.sqlite','.sqlite3','.pem','.key') or name in (
                '.env','browser-token.txt','github-update-token.bin','config.json'):
            failures.append(f'{path}: forbidden credential/user-data artifact')
        content=git(root,'cat-file','blob',oid)
        if suffix=='.py':
            try:compile(content,path,'exec');python_count+=1
            except SyntaxError as error:failures.append(f'{path}:{error.lineno}: syntax error')
        if suffix in ('.js','.cjs','.mjs'):
            # Node needs a filename; this temporary file contains only a staged blob.
            with tempfile.TemporaryDirectory() as folder:
                temporary=Path(folder)/('check'+suffix);temporary.write_bytes(content)
                result=subprocess.run(['node','--check',str(temporary)],capture_output=True)
                if result.returncode:failures.append(f'{path}: JavaScript syntax error')
                else:js_count+=1
        if b'\0' not in content:
            text=content.decode('utf-8',errors='replace')
            for label,pattern in SIGNATURES:
                if re.search(pattern,text):failures.append(f'{path}: possible {label} (value withheld)')
    if failures:
        print('\n'.join(failures),file=sys.stderr);return 1
    print(f'Source syntax OK: {python_count} Python, {js_count} JavaScript files.')
    print(f'Credential/artifact scan OK: {len(files)} staged Git files; no signature matches.')
    return run('check',root)


if __name__=='__main__':
    try:raise SystemExit(main())
    except (OSError,ValueError) as error:
        print(f'Source check FAILED: {error}',file=sys.stderr);raise SystemExit(1)
