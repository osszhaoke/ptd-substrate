# 更新与备份

[English](updates.en.md)

本试用版由你决定何时更新。可在[仓库](https://github.com/osszhaoke/ptd-substrate)选择 **Watch → Custom → Releases** 接收通知，也可查看[发布页](https://github.com/osszhaoke/ptd-substrate/releases)。程序本身不会自动联网检查更新。

## 1. 停止旧版并备份

先读新版对数据格式的要求。涉及重建或迁移时按该版本说明处理。在旧服务终端按 Ctrl+C 并等进程退出，也停止使用同一数据根的其他 PTDS 进程。保留已经校验的旧程序。以下代码块在同一终端依次运行，每一步出现错误就停止。用安装时选择的专属数据根、配置和程序目录的物理绝对路径。避免经过软链接的路径，备份、下载和恢复副本分开存放。

第一个代码块在当前终端定义复制和核验步骤。它检查目录内的普通文件、隐藏文件和数据库侧文件，保留数据根内的硬链接关系，并拒绝指向根外的硬链接、软链接或特殊文件。备份包含健康数据，请选择本人控制的私有父目录，按原件一样保护。钥匙串仍由系统管理。

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

确认服务器都已退出后，将 BACKUP_DIR 设置为尚不存在的路径。核对终端列出的完整位置后，本人输入 **BACKUP**。数据根和配置的副本核验一致后才会生成有效的 READY.json。任何被中断的副本留在原位置，重试时换一个新目录。

```sh
: "${SPACE_ROOT:?Set the existing data root}"
: "${TRIAL_CONFIG:?Set the existing settings file}"
: "${OLD_APP:?Set the verified old program directory}"
: "${BACKUP_DIR:?Choose an unused private backup directory}"
ptds_snapshot backup "$SPACE_ROOT" "$TRIAL_CONFIG" "$OLD_APP" "$BACKUP_DIR"
```

## 2. 核验并解压新版

从同一 Release 把 ZIP 和外部 SHA256SUMS 下载到专用目录，随后可以离线。ZIP_NAME 只填发布页的确切文件名，例如 ptd-substrate-v0.3.0-alpha.2.zip。NEW_PARENT 的父目录必须是你已有的私有目录，NEW_PARENT 本身须尚不存在。先检查外部摘要与压缩包路径，再在全新目录解压并运行包内校验器。失败时保留原版和备份。

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

## 3. 用新版打开原空间

用核验后的新程序、原数据根和原配置启动。打开本次终端打印的回环地址。核对空间名、一条已有记录及其来源。如曾导入基因文件或化验单，再核对一项原件属性。核对前暂缓新增数据。

```sh
ptds_snapshot new "$SPACE_ROOT" "$TRIAL_CONFIG" "$OLD_APP" "$BACKUP_DIR" "$NEW_APP"
```

## 4. 需要回退时

先退出新版并等所有使用同一数据根的进程结束。保留 SPACE_ROOT 和 TRIAL_CONFIG 在备份时使用的原路径，即使现用配置已经损坏或移走。恢复会核对原路径、旧程序和备份回执，并在备份副本中验证实例身份与文件。只使用自己建立并保管的备份。需要独立核对时，将 BACKUP_RECEIPT_SHA256 设为创建备份时终端打印、由你另行保管的回执摘要。RESTORE_DIR 必须是已有私有父目录下的**全新路径**，位于原空间、配置、程序和备份之外。核对提示后输入 **PREPARE**。此步只把备份复制到 RESTORE_DIR/data-root 和 RESTORE_DIR/settings.json 并复核，原空间与现用配置继续保留在原位。准备失败或中断时，原空间和备份均保持原状，另选新目录重试。

```sh
: "${RESTORE_DIR:?Choose a new private restore directory}"
ptds_snapshot restore "$SPACE_ROOT" "$TRIAL_CONFIG" "$OLD_APP" "$BACKUP_DIR" "$RESTORE_DIR"
```

核对恢复副本的位置及备份时间。若要使用它，本人输入 **START**，旧程序才会用副本启动。打开终端显示的本机地址，核对数据和来源。以后继续使用恢复副本时，在[启动步骤](../../AGENT_INSTALL.md)中选择这两个新路径。原空间中升级后增加的数据继续保留在那里。不要同时启动两个副本。可选设备同步须单独核对。

```sh
ptds_snapshot activate "$SPACE_ROOT" "$TRIAL_CONFIG" "$OLD_APP" "$BACKUP_DIR" "$RESTORE_DIR"
```
