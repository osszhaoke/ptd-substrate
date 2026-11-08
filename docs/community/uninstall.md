# 卸载与本机数据清理

[English](uninstall.en.md)

保留数据时，只退出程序并移除解压出来的程序目录。完全卸载会删除所选数据空间的历史和原件。需要保留时先按[更新与备份](updates.md)制作副本。

## 1. 辨认这次安装

在终端把 APP_DIR、SPACE_ROOT、TRIAL_CONFIG 和 SPACE_ID 设置为你安装时选定的实际值。SPACE_ID 是实例 ID，与显示名称和安装器的目标键分开。核对下表与列出的路径，遇到陌生路径就停下。

```sh
: "${APP_DIR:?Set the absolute extracted release directory}" &&
: "${SPACE_ROOT:?Set the absolute data root used at launch}" &&
: "${TRIAL_CONFIG:?Set the absolute settings path used at launch}" &&
: "${SPACE_ID:?Set the exact installed instance ID}" &&
printf '%s\n' "$APP_DIR" "$SPACE_ROOT" "$SPACE_ID" "$TRIAL_CONFIG"
```

| 位置 | 保存的内容 |
| --- | --- |
| APP_DIR | 解压的程序、随包虚构样例和说明。 |
| SPACE_ROOT/SPACE_ID | instance.json、星炬与星轨数据库及 SQLite 侧文件、交换与历史记录。文件导入会在其中生成批次文件；基因原件和位点库在 startorch/gene 下。Oura 记录属于所选空间。 |
| 实例的 startorch/originals 与 startorch/.partner-ocr-review | 确认过的化验单副本、识别登记和待核对草稿。草稿最长保留 30 分钟。 |
| SPACE_ROOT/ptds-app.log 与 TRIAL_CONFIG | 整个数据根的运行日志，以及本人指定位置的启动配置。 |
| OCR 缓存、私人凭据、浏览器 | 见第 2 至 4 步。 |

## 2. 清理浏览器并退出

保留标签页时先记下地址和端口。若要清除浏览器偏好，在浏览器开发者工具的存储面板选择该 PTDS 页面对应的源（例如本机地址及其端口）。在本地存储和会话存储中，只删除名字以 ptds- 开头的键，例如 ptds-language、ptds-theme。对使用过的每个浏览器配置和端口重复。要清理浏览历史或缓存，可在浏览器中另行处理；先确认没有选中同一主机上其他程序的数据。关闭页面。在启动程序的终端按 Ctrl+C，等终端重新显示提示符。

## 3. 核对并移除所选文件

请本人在同一个终端展开并粘贴下面的函数。它只接受下面列出的角色。每项先列出物理路径及全部条目；若有不认识的文件，请输入 KEEP。输入 MOVE 后，原对象暂时移到同一父目录下一处打印出来的私人目录。再输入 DELETE 才删除，第二步输入其他内容会尝试原位归还。单文件只删除经核对的普通文件，空目录只在确实为空时移除。软链接、硬链接文件、特殊文件和不一致的身份会中止操作。

对于程序和数据空间，函数会在私人目录先制作并完整核对一份仅本人可读的 recovery.tar，再逐项删除列出的内容。允许的空间必须专用于 PTDS；本人逐项核对名称，其他项目的文件请先移出。请留出至少相当于该目录内容大小加归档开销的同卷空间。归档临时包含本机数据，只有全部成功才删除。终端关闭、磁盘满、目录变化或其他错误时，停止使用该空间，保留打印的私人目录。若原位置完整，核对后再处理残留；若删除已开始，先保留并核对 recovery.tar，再将它解压到另一个新私有目录。归档保存目录、普通文件内容、权限和时间；需要保留其他元数据时先做完整备份。

<details>
<summary>在终端定义卸载函数（macOS，使用启动 PTDS 的 Python）</summary>

```sh
retire_ptds() {
  local script
  script=$(cat <<'PTDS_PRIVATE_UNINSTALL'
import contextlib, ctypes, hashlib, json, os, re, secrets, stat, sys, tarfile

role, app, data, conf, ident, home, binary, private, temp = sys.argv[1:]
uid = os.getuid()
DIR = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
FILE = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
def check(ok, why):
    if not ok:
        raise ValueError(why)

def physical(s):
    parts = s.split("/")
    check(parts[0] == "" and len(parts) > 1 and all(x not in ("", ".", "..") for x in parts[1:]), "Ambiguous path")
    if parts[1] in ("tmp", "var") and os.path.islink("/" + parts[1]):
        alias = "/" + parts[1]
        expected = "/private" + alias
        check(sys.platform == "darwin" and os.lstat(alias).st_uid == 0 and
              os.readlink(alias) in (expected, expected[1:]) and
              all(stat.S_ISDIR(os.lstat(p).st_mode) and os.lstat(p).st_uid == 0
                  for p in ("/private", expected)), "Unverified system alias")
        parts.insert(1, "private")
    return "/".join(parts)
check(bool(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", ident)), "Check instance ID")
if temp.endswith("/") and temp != "/": temp=temp[:-1]
app, data, conf, home, binary, private, temp = map(physical, (app,data,conf,home,binary,private,temp))
space = data + "/" + ident
vision = binary + "/partner-vision"
preview = temp + "/ptds-vision-preview-" + str(uid)
targets = {"space":("tree",space), "app":("tree",app), "config":("file",conf),
 "log":("file",data+"/ptds-app.log"), "empty-root":("empty",data),
 "vision":("file",vision+"/ocr_vision"), "preview":("file",preview+"/source.pdf"),
 "token":("file",private+"/ptds-oura-"+ident), "client":("file",private+"/ptds-oura-client-secret."+ident),
 "empty-preview":("empty",preview), "empty-vision":("empty",vision),
 "empty-secrets":("empty",home+"/.ptds/secrets"), "empty-bin":("empty",home+"/.ptds/bin"),
 "empty-ptds":("empty",home+"/.ptds")}
kind, path = targets[role]
check(not any(p == home or home.startswith(p+"/") or p.count("/") < 2 for p in (app,data,conf)), "Protected installation path")
check(not (app == data or data.startswith(app+"/") or app.startswith(data+"/") or
           conf == data or conf == app or conf.startswith(app+"/") or conf == space or conf.startswith(space+"/")),
      "Overlapping targets")
check(all(k == role or p != path for k, (_,p) in targets.items()), "Two roles claim the same path")
parent, leaf = path.rsplit("/",1)
@contextlib.contextmanager
def directory(path, start=None):
    fd=os.open("/", DIR) if start is None else os.dup(start)
    try:
        for s in path.split("/"):
            if s:
                nxt=os.open(s, DIR, dir_fd=fd);os.close(fd);fd=nxt
        yield fd
    finally:
        os.close(fd)
def sig(st):
    return (st.st_dev,st.st_ino,st.st_mode,st.st_uid,st.st_nlink,st.st_size,st.st_mtime_ns)
def snapshot(parentfd, name):
    items={}
    def visit(fd, entry, rel):
        s=os.stat(entry,dir_fd=fd,follow_symlinks=False)
        check(s.st_uid==uid and s.st_dev==os.fstat(parentfd).st_dev,"Foreign owner or volume")
        items[rel]=sig(s)
        if stat.S_ISDIR(s.st_mode):
            with directory(entry,fd) as d:
                check(sig(os.fstat(d))==sig(s),"Directory changed")
                for sub in sorted(os.listdir(d)):visit(d,sub,rel+"/"+sub if rel else sub)
                check(sig(os.fstat(d))==sig(s),"Directory changed")
        else:
            check(stat.S_ISREG(s.st_mode) and s.st_nlink==1,"Linked or special entry")
    visit(parentfd,name,"")
    return items
def file_at(d, n, expected=None):
    f=os.fdopen(os.open(n,FILE,dir_fd=d),"rb")
    try:
        s=os.fstat(f.fileno())
        check(stat.S_ISREG(s.st_mode) and s.st_nlink==1 and s.st_uid==uid and
              (expected is None or sig(s)==expected),"File changed")
    except BaseException:
        f.close();raise
    return f
def digest(f):
    h=hashlib.sha256()
    for block in iter(lambda:f.read(1024*1024),b""):h.update(block)
    return h.hexdigest()
def verify_role(pfd, entries):
    top=entries[""]
    check(stat.S_ISREG(top[2]) if kind=="file" else stat.S_ISDIR(top[2]),"Wrong target type")
    if kind=="empty":check(len(entries)==1,"Directory is not empty")
    if role=="log":
        check(set(os.listdir(pfd))=={leaf},"The data root still has another entry")
    if role in ("app","space"):
        with directory(leaf,pfd) as d:
            if role=="space":
                check(all(n in entries and stat.S_ISDIR(entries[n][2]) for n in ("startorch","startrack","exchange")),"Unknown space")
                with file_at(d,"instance.json",entries["instance.json"]) as f:
                    check(json.load(f).get("instance_id")==ident,"Wrong space")
            else:
                with file_at(d,"SHA256SUMS",entries["SHA256SUMS"]) as f:
                    check(digest(f)=="d1503ea0c4dc10e551868227576a23d0c3cc15673b9d11d23ddb470c919580e5",
                          "Use the verified alpha.2 release")
                    f.seek(0); listing={n:h for h,n in (line.decode().rstrip("\n").split("  ",1) for line in f)}
                expected={"","SHA256SUMS"}
                for n, value in listing.items():
                    branch,_,last=n.rpartition("/")
                    with directory(branch,d) as fd, file_at(fd,last,entries[n]) as f:
                        check(digest(f)==value,"Program file changed")
                    while n:expected.add(n);n=n.rpartition("/")[0]
                check(expected==set(entries),"Unlisted program entry")
    if role=="config":
        with file_at(pfd,leaf,top) as f:c=json.load(f)
        check([s.get("id") for s in c.get("instances",[])]==[ident],"Wrong settings target")
    if role=="preview":
        import fcntl
        check(stat.S_IMODE(os.fstat(pfd).st_mode)==0o700 and os.fstat(pfd).st_uid==uid,"Unsafe preview directory")
        fcntl.flock(pfd,fcntl.LOCK_EX|fcntl.LOCK_NB)
def exclusive(a,n,b,m):
    c=ctypes.CDLL(None,use_errno=True)
    if c.renameatx_np(a,os.fsencode(n),b,os.fsencode(m),4):
        code=ctypes.get_errno();raise OSError(code,os.strerror(code))
def archive(hfd, entries):
    name="recovery.tar"
    filefd=os.open(name,os.O_RDWR|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=hfd)
    hashes={}
    with os.fdopen(filefd,"w+b") as recovery, directory("item",hfd) as top:
        with tarfile.open(fileobj=recovery,mode="w") as package:
            for rel,v in entries.items():
                h=tarfile.TarInfo("item"+("/"+rel if rel else ""));h.mode=stat.S_IMODE(v[2]);h.mtime=v[-1]/1e9
                if stat.S_ISDIR(v[2]):
                    h.type=tarfile.DIRTYPE;package.addfile(h);continue
                branch,_,n=rel.rpartition("/")
                with directory(branch,top) as fd,file_at(fd,n,v) as f:
                    hashes[h.name]=digest(f);f.seek(0);h.size=v[5];package.addfile(h,f)
        recovery.flush();os.fsync(recovery.fileno());recovery.seek(0)
        with tarfile.open(fileobj=recovery,mode="r") as package:
            members=package.getmembers()
            check(len(members)==len(entries) and {m.name for m in members}=={"item"+("/"+n if n else "") for n in entries},"Recovery list mismatch")
            for m in members:
                if m.isfile():
                    with package.extractfile(m) as f:check(digest(f)==hashes[m.name],"Recovery copy mismatch")
    return sig(os.stat(name,dir_fd=hfd,follow_symlinks=False))
def purge(hfd,entries):
    def erase(pfd,name,rel):
        s=os.stat(name,dir_fd=pfd,follow_symlinks=False)
        check(sig(s)==entries[rel],"Selected item changed")
        if stat.S_ISDIR(s.st_mode):
            with directory(name,pfd) as d:
                check(sig(os.fstat(d))==entries[rel],"Selected directory changed")
                for child in sorted(os.listdir(d)):
                    key=rel+"/"+child if rel else child
                    check(key in entries,"Unlisted entry; keeping recovery copy")
                    erase(d,child,key)
                check(not os.listdir(d),"Unlisted entry")
            check(sig(os.stat(name,dir_fd=pfd,follow_symlinks=False))[:4]==entries[rel][:4],"Directory replaced")
            os.rmdir(name,dir_fd=pfd)
        else:
            # Validate the *moved* object before the terminal unlink.
            disposable=".selected-"+secrets.token_hex(16)
            exclusive(pfd,name,hfd,disposable)
            check(sig(os.stat(disposable,dir_fd=hfd,follow_symlinks=False))==entries[rel],"File replaced in private holder")
            os.unlink(disposable,dir_fd=hfd)
    erase(hfd,"item","")
def run(pfd):
    try:os.stat(leaf,dir_fd=pfd,follow_symlinks=False)
    except FileNotFoundError:print("Absent",path);return
    # Check expected type before inspecting any contents of a mistyped leaf.
    first=os.stat(leaf,dir_fd=pfd,follow_symlinks=False)
    check(stat.S_ISREG(first.st_mode) if kind=="file" else stat.S_ISDIR(first.st_mode),"Wrong target type")
    entries=snapshot(pfd,leaf);verify_role(pfd,entries)
    print("Selected",json.dumps(path))
    for rel,v in entries.items():print("DIR" if stat.S_ISDIR(v[2]) else "FILE",v[5],json.dumps(rel or "."))
    if input("Type MOVE: ")!="MOVE":print("Cancelled before the move.");sys.exit(2)
    with directory(parent) as again:
        check(sig(os.fstat(pfd))[:4]==sig(os.fstat(again))[:4],"Parent changed")
    check(snapshot(pfd,leaf)==entries,"Changed during review")
    if role=="log":check(set(os.listdir(pfd))=={leaf},"The data root changed during review")
    name=".ptds-retire-"+secrets.token_hex(16)
    os.mkdir(name,0o700,dir_fd=pfd);print("Private holder",json.dumps(parent+"/"+name),flush=True)
    moved=False;started=False;recovery=None
    with directory(name,pfd) as holder:
        try:
            exclusive(pfd,leaf,holder,"item");moved=True
            check(snapshot(holder,"item")==entries,"Different object after move")
            if input("Type DELETE to remove the listed items: ")!="DELETE":
                print("Cancelled. Restoring the selected item.");sys.exit(2)
            with directory(parent) as again:
                check(sig(os.fstat(pfd))[:4]==sig(os.fstat(again))[:4],"Parent changed")
            try: os.stat(leaf,dir_fd=pfd,follow_symlinks=False)
            except FileNotFoundError: pass
            else: raise ValueError("The original name was occupied after review")
            check(snapshot(holder,"item")==entries,"Changed after move")
            if role=="log":check(set(os.listdir(pfd))=={name},"The data root changed after move")
            if kind=="tree":
                recovery=archive(holder,entries)
                check(snapshot(holder,"item")==entries,"Changed while copying")
            started=True;purge(holder,entries);moved=False
            if recovery:
                check(sig(os.stat("recovery.tar",dir_fd=holder,follow_symlinks=False))==recovery,"Recovery object changed")
                os.unlink("recovery.tar",dir_fd=holder)
        finally:
            if moved and not started:
                exclusive(holder,"item",pfd,leaf)
            if not os.listdir(holder):
                check(sig(os.stat(name,dir_fd=pfd,follow_symlinks=False))[:4]==sig(os.fstat(holder))[:4],"Holder changed")
                os.rmdir(name,dir_fd=pfd)
            else:
                print("Retained objects in private holder; stop and inspect.",file=sys.stderr)
try:
    with contextlib.ExitStack() as stack:
        try:fd=stack.enter_context(directory(parent))
        except FileNotFoundError:
            print("Absent",json.dumps(path));sys.exit(0)
        run(fd)
except FileNotFoundError as e:
    print("Missing path component or changed entry; stopped.",file=sys.stderr);sys.exit(1)
except EOFError:
    print("Confirmation input ended; the operation stopped.",file=sys.stderr);sys.exit(2)
except (ValueError,KeyError,OSError) as e:
    print("Stopped:",str(e),file=sys.stderr);sys.exit(1)
PTDS_PRIVATE_UNINSTALL
) || return $?
  [ -n "$script" ] || return 1
  python3 -IB -c "$script" "$1" "${APP_DIR:?}" "${SPACE_ROOT:?}" "${TRIAL_CONFIG:?}" "${SPACE_ID:?}"     "$HOME" "${PTDS_BIN:-$HOME/.ptds/bin}" "${PTDS_SECRETS:-$HOME/.ptds/secrets}" "${TMPDIR:-/tmp}"
}
```

</details>

程序和空间以本人选定的安装路径和实例 ID 为准。程序必须是内容完全一致的 v0.3.0-alpha.2 解压树；额外文件或空目录也会阻止删除。配置必须只指向本次选定的实例。下方第一个命令只移除程序，保留空间与配置。每次粘贴一个完整代码块。只有上一项成功或已经不存在，才继续下一项。取消确认或确认输入结束时返回状态 2。后一步失败时，前面已确认并完成的移除已经生效；后续项目会保留原状。遇到错误时先读清提示，核对现场路径后再继续。

```sh
retire_ptds app
```

**另选：删除这个空间及其配置。** 下面的两条命令会移除所选空间的原件、历史和配置。要保留数据，请跳过整块。

```sh
retire_ptds space &&
retire_ptds config
```

只有确认这是最后一个使用该数据根的安装，才移除共用日志和空根目录。仍有其他空间、目录或不属于你的文件时保留数据根。

```sh
retire_ptds log &&
retire_ptds empty-root
```

退出所有共用缓存的 PTDS 进程并确认缓存不用后，再处理以下 OCR 文件。沿用启动时的 PTDS_BIN、TMPDIR。缺失目标会显示 Absent，不需要创建。意外中断的 ptds-vision-build- 或 ptds-vision-run- 私人目录只按本次运行记录逐个核实。

```sh
retire_ptds vision &&
retire_ptds preview &&
retire_ptds empty-vision &&
retire_ptds empty-preview
```

## 4. 按实例处理 Oura 凭据

若其他安装共用同一实例 ID，请保留凭据。使用过钥匙串的本人可逐项核对服务名和账户名，各输入 DELETE。钥匙串条目不存在时会报告未找到，并停止该块。如果只有第二项仍在，可由本人在钥匙串访问中删除那一项。遇到访问错误时请本人核实。授权由本人在 Oura 管理。

```sh
(
  case "${SPACE_ID:-}" in ''|[!A-Za-z0-9]*|*[!A-Za-z0-9_.-]*) exit 1 ;; esac
  for account in "$SPACE_ID" "client-secret.$SPACE_ID"; do
    printf 'Service ptds-oura, account %s. Type DELETE to remove: ' "$account" || exit $?
    IFS= read -r reply || exit 2
    [ "$reply" = DELETE ] || exit 2
    security delete-generic-password -s ptds-oura -a "$account" || exit $?
  done
)
```

只有当本次安装实际使用 PTDS_SECRETS 私人目录时，改用以下文件分支。只处理两个指定的单链接普通文件。

```sh
retire_ptds token &&
retire_ptds client
```

## 5. 核对结果

只有这些默认目录专用于本次安装时，才逐个确认清理空目录。自定义父目录由本人管理。最后列出的三个路径应为 Absent。请另行核对自己保留的下载包、旧程序、导出、备份和 Time Machine，以及你上传时选中的外部原件；这套流程不会保证 SSD 取证擦除。

```sh
retire_ptds empty-secrets &&
retire_ptds empty-bin &&
retire_ptds empty-ptds &&
(
  for item in "$APP_DIR" "$SPACE_ROOT/$SPACE_ID" "$TRIAL_CONFIG"; do
    if [ -e "$item" ] || [ -L "$item" ]; then
      printf 'Present: %s\n' "$item" || exit $?
      exit 1
    fi
    printf 'Absent: %s\n' "$item" || exit $?
  done
)
```
