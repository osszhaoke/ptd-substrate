#!/usr/bin/env python3
"""Offline publication policy. A violation prints its rule and location only."""
from pathlib import Path
import argparse
import hashlib
import os
import re
import stat
import struct
import zlib
import subprocess
import sys

def digest(data):
    return hashlib.sha256(data).hexdigest()

def paths(root):
    if (root/'.git').exists():
        output=subprocess.check_output(['git','-C',str(root),'ls-files','-z','--cached','--others','--exclude-standard'])
        return sorted({os.fsdecode(name) for name in output.split(b'\0') if name})
    return sorted(p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_symlink() or not p.is_dir())

REPOSITORY='https://github.com/'+'ossz'+'haoke/ptd-substrate'
BAD_PATH=re.compile(r'(?:^|/)(?:runtime|instances|evidence|delivery|\.stage|\.workspaces|\.ai-context|__pycache__|DerivedData|\.git)(?:/|$)|(?:^|/)\.env(?:\..*)?$|\.(?:db[^/]*|sqlite[0-9]*|log|pyc|pem|p12|pfx|crt|cer|der|key|keystore|jks)$|(?:-wal|-shm|-journal)$',re.I)
TOKEN=re.compile(r'(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{25,}|(?:AKIA|ASIA)[0-9A-Z]{16}|sk-(?:proj-|svcacct-)?[A-Za-z0-9_\-]{20,}|-----BEGIN (?:[A-Z0-9]+ )*PRIVATE KEY-----)')
MAIL=re.compile(r'[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}')
HOME=re.compile(r'/(?:Users|home)/[^\s/]+')
SECRET_VALUE=re.compile(r'''(?i)(?:client_secret|access_token|refresh_token|api_key)\s*[:=]\s*["'][^"']{8,}''')
# The immutable release policy contains three exact lines rejecting legacy installation identities.
REJECTIONS={17: '35886f3e9fa7b9db979089fa97668374d7594acf7fc5de5a0546ea934db1bc78', 18: 'f2c96103e8ca6ef4b1a8cbd99e288b2c7ef837fe9327a2c742027f58fed50b79', 47: 'af623ead9efa0dfc4caae85d75d71627e91b40961cf2102706620e9d6ac46624'}
PERSONAL=re.compile(r'\b(?:live[_-]'+r'real|live-'+r'replay|eld'+r'er)\b|-wal-'+r'20261106',re.I)
OWNER_PATTERN=re.compile(r'ossz' + r'haoke|\bO' + r'ss\b|\u8d75',re.I)
APPROVED_URL=re.compile(re.escape(REPOSITORY)+r'(?=/|[\s?#)\]<>"]|$)')
BAD_KEY_USE=re.compile(r'''(?ix)(?:[?&]key=|(?:instance_key|selected_key|key)\s*["']?\s*[:=]\s*["']|\.get\(\s*["']key["']\s*,\s*["'])live(?=\b|["'])''')

def png_pixels_only(raw):
    # Public screenshots permit pixel data and minimal numeric rendering metadata.
    if raw[:8] != b'\x89PNG\r\n\x1a\n':
        return False
    offset=8
    seen=[]
    chunks=[]
    while offset+12<=len(raw):
        size,kind=struct.unpack_from('>I4s',raw,offset)
        end=offset+12+size
        if end>len(raw) or kind not in {b'IHDR',b'IDAT',b'IEND',b'sRGB',b'pHYs',b'gAMA',b'cHRM'}:
            return False
        payload=raw[offset+8:end-4]
        if zlib.crc32(kind+payload)!=struct.unpack_from('>I',raw,end-4)[0]:return False
        dimensions={b'IHDR':13,b'IEND':0,b'sRGB':1,b'pHYs':9,b'gAMA':4,b'cHRM':32}
        if kind in dimensions and len(payload)!=dimensions[kind]:return False
        if kind==b'IDAT':chunks.append(payload)
        seen.append(kind);offset=end
        if kind==b'IEND':break
    if not (offset==len(raw) and seen[:1]==[b'IHDR'] and seen[-1:]==[b'IEND'] and chunks):return False
    pixels=zlib.decompressobj()
    try:
        pixels.decompress(b''.join(chunks),80_000_001)
    except zlib.error:return False
    return pixels.eof and not pixels.unused_data and not pixels.unconsumed_tail

def scan(path,label):
    failures=[]
    if BAD_PATH.search(label):failures.append(('forbidden path',label,0))
    if path.is_symlink() or not path.is_file() or not stat.S_ISREG(path.stat().st_mode):
        return failures+[('not a regular file',label,0)]
    data=path.read_bytes()
    if path.suffix.lower()=='.png':
        return failures if png_pixels_only(data) else failures+[('unexpected image metadata or content',label,0)]
    for n,raw in enumerate(data.splitlines(),1):
        line=raw.decode('utf-8',errors='replace')
        if label=='app/trial_target.py' and digest(raw)==REJECTIONS.get(n):continue
        line=APPROVED_URL.sub('REPO',line)
        for rule,pattern in [('credential',TOKEN),('credential literal',SECRET_VALUE),('email',MAIL),('personal home',HOME),('personal account',OWNER_PATTERN),('personal identity',PERSONAL),('personal default',BAD_KEY_USE)]:
            if pattern.search(line):failures.append((rule,label,n))
    return failures

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--extra',action='append',type=Path,default=[])
    args=parser.parse_args();root=args.root.resolve()
    failures=[finding for n in paths(root) for finding in scan(root/n,n)]
    for p in args.extra:failures.extend(scan(p,p.name))
    for code,path,line in failures:print(f'{path}:{line}: {code}')
    print(f'{len(failures)} publication findings')
    return int(bool(failures))
if __name__=='__main__':raise SystemExit(main())
