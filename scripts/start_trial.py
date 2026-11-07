"""Start one foreground PTDS process on loopback with explicit installation paths."""
import argparse
import runpy
from pathlib import Path
import socket
import sys

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', required=True, type=Path)
    parser.add_argument('--config', required=True, type=Path)
    parser.add_argument('--port', type=int, default=0)
    args = parser.parse_args()
    if not args.root.is_dir() or not args.config.is_file():
        parser.error('Create the data space and run the installer first.')
    if not 0 <= args.port <= 65535:
        parser.error('Invalid port.')
    port = args.port
    if port == 0:
        with socket.socket() as probe:
            probe.bind(('127.0.0.1', 0))
            port = probe.getsockname()[1]
    app = Path(__file__).resolve().parents[1] / 'app/server.py'
    print(f'Open http://127.0.0.1:{port}/ after the server reports ready.', flush=True)
    sys.path.insert(0,str(app.parent))
    sys.argv=[str(app),'--root',str(args.root),'--config',str(args.config),'--port',str(port)]
    runpy.run_path(str(app),run_name='__main__')
if __name__ == '__main__':
    main()
