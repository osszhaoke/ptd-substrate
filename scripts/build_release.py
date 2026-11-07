"""Build an unsigned, deterministic ZIP from a verified release directory."""
import argparse
from pathlib import Path
import re
import subprocess
import sys
import zipfile
def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--out',type=Path,required=True,help='New ZIP path outside the repository')
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    out=args.out.resolve()
    tag=re.search(r'^## (v[^\s]+)$',(root/'CHANGELOG.md').read_text(),re.M)[1]
    if out.is_relative_to(root) or args.out.is_symlink() or out.exists():parser.error('Choose an unused location outside the source tree.')
    for program in ['verify_release.py','check_publication.py']:
        subprocess.run([sys.executable,'-B','-I',str(root/'scripts'/program)],check=True)
    paths=['SHA256SUMS']+[line.split('  ',1)[1] for line in (root/'SHA256SUMS').read_text().splitlines()]
    with zipfile.ZipFile(out,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as bundle:
        for n in sorted(paths):
            entry=zipfile.ZipInfo('ptd-substrate-'+tag+'/'+n,date_time=(2026,11,7,0,0,0))
            entry.create_system=3
            entry.external_attr=((0o100755 if n=='scripts/verify_release.sh' else 0o100644)<<16)
            bundle.writestr(entry,(root/n).read_bytes(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
if __name__=='__main__':main()
