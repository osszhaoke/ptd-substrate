# Uninstall and remove local data

[Read in Chinese](uninstall.md)

To keep your data, quit the app and remove only the extracted program directory. A full uninstall removes the selected space, including its history and saved originals. First make a copy if you want to keep it. See [Updates and backups](updates.en.md).

## 1. Identify this installation

In Terminal, set APP_DIR, SPACE_ROOT, TRIAL_CONFIG and SPACE_ID to the actual values for this installation. SPACE_ID is the instance ID. The display name and the target key are separate. Check the table and the listed paths. Stop if any location is unfamiliar.

```sh
: "${APP_DIR:?Set the absolute extracted release directory}" &&
: "${SPACE_ROOT:?Set the absolute data root used at launch}" &&
: "${TRIAL_CONFIG:?Set the absolute settings path used at launch}" &&
: "${SPACE_ID:?Set the exact installed instance ID}" &&
printf '%s\n' "$APP_DIR" "$SPACE_ROOT" "$SPACE_ID" "$TRIAL_CONFIG"
```

| Location | What it contains |
| --- | --- |
| APP_DIR | Extracted program, fictional examples and guides. |
| SPACE_ROOT/SPACE_ID | instance.json, StarTorch and StarTrack databases with SQLite side files, exchange files and history. Imports can create batch files here. Raw genetic files and the locus database are under startorch/gene. Oura records belong to the selected space. |
| startorch/originals and startorch/.partner-ocr-review in the space | Saved copies of lab reports, recognition records and drafts awaiting review. Drafts expire after 30 minutes. |
| SPACE_ROOT/ptds-app.log and TRIAL_CONFIG | The log for the whole data root and the startup settings at the location you chose. |
| OCR cache, private credentials and browser | See steps 2 to 4. |

## 2. Clear browser data and quit

Keep the tab open long enough to note its address and port. To clear browser preferences, select the origin for this PTDS page in the browser developer tools storage panel. The origin includes the loopback address and port. In local storage and session storage, remove only the keys starting with ptds-, such as ptds-language and ptds-theme. Repeat for each browser profile and port you used. For browsing history or cache, review the browser options separately and check that other apps on this host are excluded. Close the page. Press Ctrl+C in the Terminal window that started PTDS and wait for the prompt.

## 3. Review and remove selected items

In the same Terminal window, expand and paste the function below yourself. It accepts only the roles listed in this guide. It lists the physical path and every entry. Type KEEP if an item is unfamiliar. Typing MOVE moves the selected object to a private directory in its parent and prints the location. Type DELETE to remove it. Any other response at the second prompt attempts to put it back. File roles remove a checked regular file. Empty directory roles remove an empty directory. Links, special files and changed identities stop the operation.

For the program and data space, the function makes an owner-only recovery.tar in the private directory and verifies every member before removing the listed entries individually. A data space must be dedicated to PTDS. Check every name yourself and move unrelated files out first. Allow free space on the same volume for the contents plus archive overhead. The temporary archive contains local data and is removed only after success. If Terminal closes, the disk fills or a path changes, stop using the space and keep the printed private directory. If the original is intact, check it before cleaning up any residue. If removal had started, retain and check recovery.tar first and extract it into another new private directory. It preserves directories, regular file contents, permissions and modification times. Make a full backup first if you need other metadata.

<details>
<summary>Define the Terminal uninstall function (macOS, using the Python that runs PTDS)</summary>

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

Use the installation paths and instance ID you chose. The program must match the complete v0.3.0-alpha.2 release tree. Extra files or empty directories stop removal. The settings must point only to the selected instance. The first action below removes only the program and keeps the space and its settings. Paste one complete block at a time. The next item runs only after the previous item completes or is already absent. A cancelled confirmation or end of input returns status 2. If a later item fails, earlier confirmed removals have already taken place. Subsequent items keep their current state. After any error, read the message and review the current paths before continuing.

```sh
retire_ptds app
```

**Optional: remove this space and its settings.** These separate commands remove the selected space, including history and originals, and its configuration. Skip this block to keep your data.

```sh
retire_ptds space &&
retire_ptds config
```

Only after confirming this was the last installation using the data root, remove its shared log and the empty root. Keep the root if other spaces, directories or files remain.

```sh
retire_ptds log &&
retire_ptds empty-root
```

Quit all PTDS processes sharing the cache and check that you no longer need it. Use the PTDS_BIN and TMPDIR values from startup. Absent means the item is already missing. If a run was interrupted, identify any temporary ptds-vision-build- or ptds-vision-run- directories individually from that run’s records.

```sh
retire_ptds vision &&
retire_ptds preview &&
retire_ptds empty-vision &&
retire_ptds empty-preview
```

## 4. Remove Oura credentials for this space

Keep credentials if another installation shares this instance ID. If you used Keychain, check each service and account name and type DELETE for each item you want to remove. A missing keychain item reports that it was not found and stops the block. If only the second account remains, remove that specific account yourself in Keychain Access. Review access errors in Keychain Access. Manage your provider authorization in Oura.

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

If this installation used a PTDS_SECRETS private directory instead, use these two file roles. Each requires a single-link regular file.

```sh
retire_ptds token &&
retire_ptds client
```

## 5. Check the result

Confirm cleanup of these empty default directories only if they belonged to this installation. You manage the parents of custom locations. The three selected paths should then report Absent. Review any downloads, old programs, exports, backups, Time Machine copies and external originals you chose to upload separately. File removal does not guarantee forensic erasure on an SSD.

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
