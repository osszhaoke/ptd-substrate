"""Verify every release file, reject extras and links. Exclude only the manifest and VCS metadata."""
from pathlib import Path, PurePosixPath
import hashlib
import os
import re
import sys
def verify(root):
    root=root.resolve()
    listing=root/'SHA256SUMS'
    if listing.is_symlink() or not listing.is_file():raise ValueError('Missing or unsafe manifest')
    expected={}
    for raw in listing.read_text().splitlines():
        m=re.fullmatch(r'([a-f0-9]{64})  (.+)',raw)
        if not m:raise ValueError('Invalid manifest line')
        sha,name=m.groups();p=PurePosixPath(name)
        if p.is_absolute() or '..' in p.parts or p.as_posix()!=name or name in expected or name=='SHA256SUMS' or '.git' in p.parts:raise ValueError('Invalid or repeated path')
        expected[name]=sha
    actual={}
    for base,dirs,files in os.walk(root):
        for d in list(dirs):
            sub=Path(base)/d
            if sub.is_symlink():raise ValueError('Unexpected link')
            if sub==root/'.git':dirs.remove(d)
        for f in files:
            path=Path(base)/f;name=path.relative_to(root).as_posix()
            if path.is_symlink() or not path.is_file():raise ValueError('Unexpected special file')
            if name not in ('SHA256SUMS','.git'):actual[name]=hashlib.sha256(path.read_bytes()).hexdigest()
    if not expected or actual!=expected:raise ValueError('Unexpected, missing or changed files')
    return len(actual)
if __name__=='__main__':
    try:print(f'Verified {verify(Path(__file__).resolve().parents[1])} files')
    except (ValueError,OSError) as error:print(error,file=sys.stderr);sys.exit(1)
