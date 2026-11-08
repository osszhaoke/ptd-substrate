# Updates and backups

[Read in Chinese](updates.md)

You choose when to update the partner trial. Select **Watch → Custom → Releases** in the [repository](https://github.com/osszhaoke/ptd-substrate) for notifications or visit the [Releases page](https://github.com/osszhaoke/ptd-substrate/releases). The app does not check for updates online automatically.

## 1. Stop the old version and make a backup

Read the new release notes for data format requirements. Follow that version's instructions if it requires a rebuild or migration. Press Ctrl+C in the old server terminal and wait for it to exit. Stop any other PTDS processes using the same data root. Keep the verified old program. Run the blocks below in the same terminal. Stop if a step fails. Use physical absolute paths for the dedicated data root, settings and program you chose at installation. Avoid paths through symbolic links. Keep backups, downloads and restored copies in separate locations.

The first block defines the copy and verification steps for this terminal. It checks regular files, hidden files and database side files. It preserves hard links within the data root and refuses links outside it, symbolic links and special files. A backup contains health data. Use a private parent directory you control and protect the copy like your originals. The system still manages the keychain.

```sh
ptds_snapshot() {
  PTDS_EXPECTED_BACKUP_SHA256="${BACKUP_RECEIPT_SHA256-}" PTDS_UPDATE_DOWNLOAD="${NEW_DOWNLOAD-}" PTDS_UPDATE_PARENT="${NEW_PARENT-}" PTDS_UPDATE_APP="${NEW_APP-}" python3 -I -B - "$@" 3<&0 <<'PYTHON'
from contextlib import contextmanager
from pathlib import Path
import hashlib, json, os, shutil, stat, subprocess, sys

mode, *values = sys.argv[1:]
root, config, app, backup = map(Path, values[:4])
extra = list(map(Path, values[4:]))
def require(ok, msg):
    if not ok: raise SystemExit(msg)
def absolute(p):
    require(p.is_absolute() and '..' not in p.parts and p != Path('/'), 'Use a specific absolute path')
    require(p.resolve(strict=False) == p, 'Use the physical path; links are refused: ' + str(p))
def apart(a, b):
    require(not a.is_relative_to(b) and not b.is_relative_to(a), 'Overlapping locations: ' + str(a) + ' and ' + str(b))
@contextmanager
def directory(path):
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
    try:
        for name in path.parts[1:]:
            child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd); fd = child
        yield fd
    finally: os.close(fd)
def file(path, create=False):
    with directory(path.parent) as fd:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL if create else os.O_RDONLY | os.O_NONBLOCK
        f = os.open(path.name, flags | os.O_NOFOLLOW, 0o600, dir_fd=fd)
        if not stat.S_ISREG(os.fstat(f).st_mode):
            os.close(f); raise SystemExit('Expected a regular file: ' + str(path))
        return os.fdopen(f, 'wb' if create else 'rb')
def read_marker(path):
    with file(path) as src:
        require(os.fstat(src.fileno()).st_nlink == 1, 'Unexpected completion marker link')
        return json.load(src)
def hash_file(path):
    with file(path) as stream: return hashlib.file_digest(stream, 'sha256').hexdigest()
def mkdir(path):
    with directory(path.parent) as fd: os.mkdir(path.name, mode=0o700, dir_fd=fd)
def vacant(path):
    absolute(path)
    with directory(path.parent) as fd:
        parent = os.fstat(fd)
        require(parent.st_uid == os.getuid() and not parent.st_mode & 0o022, 'Choose a private parent you own')
    require(not os.path.lexists(path), 'Choose a new unused destination: ' + str(path))
def inventory(base):
    dirs, files, known, entries = [], {}, {}, []
    def scan(path):
        with directory(path) as fd:
            for name in sorted(os.listdir(fd)):
                p = path/name; key = p.relative_to(base).as_posix()
                s = os.stat(name, dir_fd=fd, follow_symlinks=False)
                if stat.S_ISDIR(s.st_mode):
                    dirs.append(key); scan(p)
                else:
                    require(stat.S_ISREG(s.st_mode), 'Unexpected link or special file: ' + str(p))
                    identity = (s.st_dev, s.st_ino)
                    links = known.setdefault(identity, [s.st_nlink, []])
                    links[1].append(key)
                    entries.append((key, identity, s.st_nlink, links[1][0]))
    scan(base)
    require(all(count == len(paths) for count, paths in known.values()), 'A file has links outside the data root')
    for key, identity, count, first in entries:
        with file(base/key) as stream:
            st = os.fstat(stream.fileno())
            require((st.st_dev,st.st_ino,st.st_nlink) == (*identity,count), 'Source changed during inventory')
            files[key] = (hashlib.file_digest(stream,'sha256').hexdigest(), first)
    return dirs, files
def mirror(src, dest, copied):
    dirs, files = copied
    mkdir(dest)
    for name in dirs: mkdir(dest/name)
    for name, (_, first) in files.items():
        to = dest/name
        if first == name:
            with file(src/name) as r, file(to, True) as w: shutil.copyfileobj(r, w)
        else:
            original = dest/first
            with directory(original.parent) as a, directory(to.parent) as b:
                os.link(original.name, to.name, src_dir_fd=a, dst_dir_fd=b, follow_symlinks=False)
def summary(tree, cfg):
    layout = inventory(tree)
    fingerprint = hashlib.sha256(json.dumps(layout, sort_keys=True, ensure_ascii=True).encode()).hexdigest()
    return layout, [fingerprint, hash_file(cfg)]
def prompt(text):
    print('Selected paths:', *(str(p) for p in [root, config, app, backup, *extra]), sep='\n', flush=True)
    print('Type ' + text + ' to continue:', flush=True)
    with os.fdopen(os.dup(3)) as reply: require(reply.readline().strip() == text, 'Cancelled')
def check_settings(tree, cfg):
    require(cfg.lstat().st_nlink == 1, 'Settings must have a single link')
    with file(cfg) as src: options = json.load(src)
    specs = options.get('instances')
    require(isinstance(specs, list) and bool(specs), 'Expected installed PTDS settings')
    for item in specs:
        name = item.get('id')
        require(isinstance(name, str) and name not in ('', '.', '..') and '/' not in name and '\\' not in name and 'root' not in item, 'Unexpected instance location')
        with file(tree/name/'instance.json') as source: meta = json.load(source)
        require(meta.get('instance_id') == name, 'Data root does not match settings')
for p in (root, config, app, backup, *extra): absolute(p)
for p in (root, app, backup, *extra):
    require(not Path.home().is_relative_to(p), 'Do not select your home or its parent')
apart(root, app); apart(config, app); apart(backup, root); apart(backup, app); apart(backup, config)
with file(app/'scripts/start_trial.py'): pass
if mode in ('backup', 'new'):
    check_settings(root, config)
else:
    # Check the roles of any live objects without opening damaged settings or data.
    require(config != root and not root.is_relative_to(config), 'Unexpected original settings location')
    for path, is_root in ((root, True), (config, False)):
        try: current = path.lstat()
        except FileNotFoundError: continue
        require(stat.S_ISDIR(current.st_mode) if is_root else
                stat.S_ISREG(current.st_mode) and current.st_nlink == 1,
                'Unexpected live path type or link: ' + str(path))
# Keep verified old code and an identity for its original files.
def check_app(path):
    for rel in ('scripts/start_trial.py','scripts/verify_release.sh','scripts/verify_release.py','SHA256SUMS'):
        with file(path/rel) as f: require(os.fstat(f.fileno()).st_nlink == 1, 'Unexpected program link')
    subprocess.run(['sh', str(path/'scripts/verify_release.sh')], cwd=path, check=True)
check_app(app)
old_code = hash_file(app/'SHA256SUMS')
if mode == 'backup':
    vacant(backup)
    layout, marker = summary(root, config)
    origin, settings, target = root, config, backup
    prompt('BACKUP')
elif mode in ('restore', 'activate', 'new'):
    require(len(extra) == 1, 'Choose one target')
    target = extra[0]
    for p in (root, config, app, backup): apart(target, p)
    if mode != 'new':
        for key in ('PTDS_UPDATE_DOWNLOAD','PTDS_UPDATE_PARENT','PTDS_UPDATE_APP'):
            if os.environ.get(key):
                protected = Path(os.environ[key]); absolute(protected); apart(target,protected)
    proof = read_marker(backup/'READY.json')
    expected_receipt = os.environ.get('PTDS_EXPECTED_BACKUP_SHA256')
    if expected_receipt and mode in ('restore', 'activate'):
        require(hash_file(backup/'READY.json') == expected_receipt, 'The backup receipt differs from your saved digest')
    require(proof['root'] == str(root) and proof['config'] == str(config) and proof['program'] == old_code, 'Backup belongs to another installation')
    origin, settings = backup/'data-root', backup/'settings.json'
    check_settings(origin, settings)
    layout, marker = summary(origin, settings)
    require(proof['contents'] == marker, 'The backup is incomplete or has changed')
    if mode == 'activate':
        ready = read_marker(target/'READY.json')
        require(ready == proof, 'Restored copy is incomplete or belongs to another backup')
        check_settings(target/'data-root', target/'settings.json')
        require(summary(target/'data-root',target/'settings.json')[1] == marker,'Restored files have changed')
        prompt('START')
        absolute(target); absolute(app)
        check_app(app)
        require(hash_file(app/'SHA256SUMS') == old_code and read_marker(target/'READY.json') == proof and summary(target/'data-root',target/'settings.json')[1] == marker, 'Selection changed during confirmation')
        os.execv(sys.executable, [sys.executable,'-B',str(app/'scripts/start_trial.py'),'--root',str(target/'data-root'),'--config',str(target/'settings.json')])
    if mode == 'new':
        require(summary(root,config)[1] == marker, 'Live files changed since backup')
        check_app(target)
        os.execv(sys.executable, [sys.executable,'-B',str(target/'scripts/start_trial.py'),'--root',str(root),'--config',str(config)])
    vacant(target)
    prompt('PREPARE')
else: raise SystemExit('Unknown operation')
# Create-only writes. A failed or interrupted copy has no valid completion marker.
mkdir(target)
mirror(origin, target/'data-root', layout)
with file(settings) as r, file(target/'settings.json',True) as w: shutil.copyfileobj(r,w)
require(summary(origin,settings)[1] == marker == summary(target/'data-root',target/'settings.json')[1], 'Copy verification failed')
with file(target/'READY.json',True) as w:
    w.write(json.dumps(dict(root=str(root),config=str(config),program=old_code,contents=marker)).encode())
print('Verified copy:', target)
print('Receipt SHA-256:', hash_file(target/'READY.json'))
PYTHON
}
```

After all servers have exited, set BACKUP_DIR to an unused path. Check the full locations printed in Terminal before typing **BACKUP** yourself. A valid READY.json is created after the copied data and settings pass verification. Leave an interrupted copy where it is and choose a fresh directory for another attempt.

```sh
: "${SPACE_ROOT:?Set the existing data root}"
: "${TRIAL_CONFIG:?Set the existing settings file}"
: "${OLD_APP:?Set the verified old program directory}"
: "${BACKUP_DIR:?Choose an unused private backup directory}"
ptds_snapshot backup "$SPACE_ROOT" "$TRIAL_CONFIG" "$OLD_APP" "$BACKUP_DIR"
```

## 2. Verify and extract the update

Download the ZIP and external SHA256SUMS from the same release into a dedicated directory. You can then go offline. Set ZIP_NAME to the exact published filename, such as ptd-substrate-v0.3.0-alpha.2.zip. Choose an existing private parent and an unused NEW_PARENT below it. The command checks the external checksum and archive paths, extracts into a new directory and runs the internal verifier. Keep both the previous version and backup if it fails.

```sh
: "${NEW_DOWNLOAD:?Set the download directory}"
: "${NEW_PARENT:?Choose an unused extraction directory}"
: "${ZIP_NAME:?Set the exact published archive name}"
if python3 -I -B - "$NEW_DOWNLOAD" "$NEW_PARENT" "$SPACE_ROOT" "$TRIAL_CONFIG" "$OLD_APP" "$BACKUP_DIR" "$ZIP_NAME" <<'PYTHON'
from pathlib import Path, PurePosixPath
import hashlib, os, re, shutil, stat, subprocess, sys, zipfile
download, parent, root, config, app, backup = map(Path, sys.argv[1:7])
name = sys.argv[7]; package = name[:-4]
def check(ok, reason):
    if not ok: raise SystemExit(reason)
def disjoint(a, b):
    return not a.is_relative_to(b) and not b.is_relative_to(a)
for p in (download, parent, root, config, app, backup):
    check(p.is_absolute() and '..' not in p.parts and p != Path('/') and p.resolve(strict=False) == p, 'Use physical absolute paths')
check(re.fullmatch(r'ptd-substrate-v[0-9]+\.[0-9]+\.[0-9]+(?:-[A-Za-z0-9.-]+)?\.zip', name), 'Use the exact published filename')
check(not os.path.lexists(parent) and parent.parent.is_dir(), 'Choose a new extraction directory under an existing parent')
s = parent.parent.stat()
check(s.st_uid == os.getuid() and not s.st_mode & 0o022, 'Choose a private parent you own')
for source in (download, root, config, app, backup): check(disjoint(parent,source), 'Overlapping extraction directory')
for protected in (root,config,app,backup): check(disjoint(download,protected), 'Keep downloads separate')
paths = [download/name, download/'SHA256SUMS']
for p in paths:
    st = p.lstat()
    check(stat.S_ISREG(st.st_mode) and st.st_nlink == 1, 'Expected regular release assets')
listed = (download/'SHA256SUMS').read_text().splitlines()
check(len(listed) == 1 and re.fullmatch(r'[0-9a-f]{64}  '+re.escape(name), listed[0]), 'Unexpected external checksum list')
with (download/name).open('rb') as image:
    check(hashlib.file_digest(image,'sha256').hexdigest() == listed[0][:64], 'External checksum failed')
    image.seek(0)
    with zipfile.ZipFile(image) as z:
        entries = z.infolist(); seen = set()
        for item in entries:
            entry = PurePosixPath(item.filename)
            check(item.filename == entry.as_posix() and len(entry.parts) > 1 and entry.parts[0] == package and '..' not in entry.parts, 'Unexpected archive path')
            check(not item.is_dir() and stat.S_IFMT(item.external_attr >> 16) in (0,stat.S_IFREG), 'Unexpected archive file type')
            check(item.filename not in seen, 'Duplicate archive entry'); seen.add(item.filename)
        check(package+'/scripts/verify_release.sh' in seen, 'Missing verifier')
        parent.mkdir(mode=0o700)
        for item in entries:
            dest = parent/item.filename
            dest.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            check(dest.parent.resolve(strict=True) == dest.parent, 'Unexpected extraction link')
            with z.open(item) as r, dest.open('xb') as w: shutil.copyfileobj(r,w)
subprocess.run(['sh','scripts/verify_release.sh'], cwd=parent/package, check=True)
PYTHON
then NEW_APP="$NEW_PARENT/${ZIP_NAME%.zip}"; else unset NEW_APP; false; fi
```

## 3. Open your existing space in the update

Start the verified new program with your existing data root and settings. Open the loopback address printed for this run. Check the space name, an existing record and its source. If you have imported genetic files or lab reports, check the properties of an original too. Wait until you have checked the data before entering new records.

```sh
ptds_snapshot new "$SPACE_ROOT" "$TRIAL_CONFIG" "$OLD_APP" "$BACKUP_DIR" "$NEW_APP"
```

## 4. Restore if needed

Exit the updated program and wait for all processes that use this data root to stop. Keep SPACE_ROOT and TRIAL_CONFIG set to their original paths from the backup, even if the live settings have been damaged or moved. Recovery checks the original paths, old program and backup receipt. It verifies the instance identity and files inside the backup. Use a backup you made and kept in a trusted location. For an independent check, set BACKUP_RECEIPT_SHA256 to the receipt digest printed when you made the backup and kept separately. Set RESTORE_DIR to a **new path** under a private parent directory that already exists. Keep it outside the live space, settings, program and backup. Check the prompt before typing **PREPARE**. This step copies the backup to RESTORE_DIR/data-root and RESTORE_DIR/settings.json and verifies it. Your current data and settings stay in their original locations. Failed or interrupted preparation leaves the original space and backup as they were. Choose a fresh directory to try again.

```sh
: "${RESTORE_DIR:?Choose a new private restore directory}"
ptds_snapshot restore "$SPACE_ROOT" "$TRIAL_CONFIG" "$OLD_APP" "$BACKUP_DIR" "$RESTORE_DIR"
```

Check the location of the restored copy and the time of the backup. To use this copy, type **START** yourself. The old program then starts with the restored data and settings. Open the local address printed in Terminal to check your records and sources. For later [starts](../../AGENT_INSTALL.en.md) select these two new paths if you want to keep using the restored copy. Records added after the update are still in the original space. Run only one copy at a time. Check optional device sync separately.

```sh
ptds_snapshot activate "$SPACE_ROOT" "$TRIAL_CONFIG" "$OLD_APP" "$BACKUP_DIR" "$RESTORE_DIR"
```
