"""基因位点库：把已纳管的原始数据文件逐行写进一个统一的 SQLite（每个实例一个 genotypes.db），
供以后按 rs 号或染色体位置调取。只搬运文件里写着的内容（rs 号、染色体、位置、基因型），不解读。

原始文件仍是唯一原件；库里每一行都带来源文件的指纹（file_sha），可以回到原件核对。
"""
from __future__ import annotations

import gzip
import io
import sqlite3
import threading
import zipfile
from pathlib import Path

import gene_profile

SCHEMA = """
CREATE TABLE IF NOT EXISTS gene_file (
  file_id INTEGER PRIMARY KEY, file_sha TEXT UNIQUE NOT NULL, file_name TEXT, stored_as TEXT, format_code TEXT, vendor TEXT, build TEXT,
  rows INTEGER, loaded_at TEXT, loader TEXT);
CREATE TABLE IF NOT EXISTS genotype (
  file_id INTEGER NOT NULL REFERENCES gene_file(file_id), rsid TEXT, chrom TEXT, pos INTEGER, genotype TEXT, ref TEXT, alt TEXT, raw TEXT, line INTEGER);
CREATE INDEX IF NOT EXISTS genotype_rsid ON genotype(rsid);
CREATE INDEX IF NOT EXISTS genotype_locus ON genotype(chrom, pos);
CREATE INDEX IF NOT EXISTS genotype_file ON genotype(file_id);
"""
LOADER = "gene-db-0.1"
LOADABLE = ("RAW_23ANDME", "RAW_ANCESTRY", "RAW_CSV", "VCF")
LOCK = threading.Lock()  # 上传和启动补齐可能同时写同一份文件


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(path), timeout=30)
    con.executescript(SCHEMA)
    return con


def _lines(path: Path):
    with open(path, "rb") as f:
        magic = f.read(4)
    if magic[:2] == b"\x1f\x8b":
        stream = gzip.open(path, "rb")
    elif magic == b"PK\x03\x04":
        z = zipfile.ZipFile(path)
        members = [i for i in z.infolist() if not i.is_dir() and not i.filename.startswith("__MACOSX/")]
        stream = z.open(max(members, key=lambda i: i.file_size)) if members else io.BytesIO(b"")
    else:
        stream = open(path, "rb")
    with stream:
        for raw in stream:
            try:
                yield raw.decode("utf-8").rstrip("\r\n")
            except UnicodeDecodeError:
                yield raw.decode("gb18030", errors="replace").rstrip("\r\n")


def _int(x: str):
    try:
        return int(x)
    except ValueError:
        return None


def _rows(path: Path, prof: dict):
    """逐行产出 (rsid, chrom, pos, genotype, ref, alt, raw, line)。"""
    code = prof.get("format_code")
    header = [h.lower() for h in prof.get("header") or []]
    delim = {"制表符": "\t", "逗号": ","}.get(prof.get("delimiter"))
    for n, line in enumerate(_lines(path), start=1):
        if not line.strip() or line.startswith("#") or line.startswith("﻿#"):
            continue
        cols = line.split(delim) if delim else line.split()
        if delim == ",":
            cols = [c.strip().strip('"') for c in cols]
        if code == "VCF":
            if len(cols) < 5:
                continue
            gt = cols[9].split(":", 1)[0] if len(cols) > 9 else ""
            alleles = [cols[3]] + cols[4].split(",")
            parts = gt.replace("|", "/").split("/") if gt else []
            bases = "".join(alleles[int(a)] if a.isdigit() and int(a) < len(alleles) else "-" for a in parts) if parts else ""
            yield (cols[2] if cols[2] != "." else None, gene_profile.chrom(cols[0]), _int(cols[1]), bases or None,
                   cols[3], cols[4], gt or None, n)
            continue
        if header and cols[0].lower() == header[0]:
            continue  # 无 # 的表头行
        if len(cols) < 4:
            continue
        if code == "RAW_ANCESTRY":
            gt = cols[3] + cols[4] if len(cols) > 4 else cols[3]
        else:
            gt = cols[3]
        yield cols[0], gene_profile.chrom(cols[1]), _int(cols[2]), gt, None, None, None, n


def load(db_path: Path, file_path: Path, receipt: dict, now: str) -> dict:
    """把一份已纳管文件写进位点库。同一份文件（同指纹）只写一次。返回 {status, rows}。"""
    prof = receipt.get("profile") or {}
    if prof.get("format_code") not in LOADABLE:
        return {"status": "NOT_LOADABLE", "rows": 0, "why": prof.get("format_code") or "NO_PROFILE"}
    with LOCK:
        return _load(db_path, file_path, receipt, now, prof)


def _load(db_path: Path, file_path: Path, receipt: dict, now: str, prof: dict) -> dict:
    con = connect(db_path)
    try:
        got = con.execute("SELECT rows FROM gene_file WHERE file_sha = ?", (receipt["sha256"],)).fetchone()
        if got:
            return {"status": "ALREADY_LOADED", "rows": got[0]}
        sha, count, batch = receipt["sha256"], 0, []
        with con:  # 一个事务：要么整份写进去，要么一行都不留
            fid = con.execute("INSERT INTO gene_file (file_sha, file_name, stored_as, format_code, vendor, build, rows, loaded_at, loader) "
                              "VALUES (?,?,?,?,?,?,?,?,?)", (sha, receipt.get("file_name"), receipt.get("stored_as"),
                                                             prof.get("format_code"), prof.get("vendor"), prof.get("build"),
                                                             0, now, LOADER)).lastrowid
            for row in _rows(file_path, prof):
                batch.append((fid,) + row)
                if len(batch) >= 20000:
                    con.executemany("INSERT INTO genotype VALUES (?,?,?,?,?,?,?,?,?)", batch)
                    count += len(batch)
                    batch = []
            if batch:
                con.executemany("INSERT INTO genotype VALUES (?,?,?,?,?,?,?,?,?)", batch)
                count += len(batch)
            con.execute("UPDATE gene_file SET rows = ? WHERE file_id = ?", (count, fid))
        return {"status": "LOADED", "rows": count}
    finally:
        con.close()


def lookup(db_path: Path, rsid: str = "", chrom: str = "", pos: int | None = None, limit: int = 50) -> list:
    if not db_path.exists():
        return []
    con = connect(db_path)
    try:
        sql = ("SELECT g.rsid, g.chrom, g.pos, g.genotype, g.ref, g.alt, g.raw, g.line, f.file_name, f.file_sha, f.build "
               "FROM genotype g JOIN gene_file f USING (file_id) WHERE ")
        if rsid:
            cur = con.execute(sql + "g.rsid = ? LIMIT ?", (rsid.strip().lower(), limit))
        else:
            cur = con.execute(sql + "g.chrom = ? AND g.pos = ? LIMIT ?", (gene_profile.chrom(chrom), pos, limit))
        keys = ("rsid", "chrom", "pos", "genotype", "ref", "alt", "raw_gt", "line", "file_name", "file_sha", "build")
        return [dict(zip(keys, r)) for r in cur.fetchall()]
    finally:
        con.close()


def stats(db_path: Path) -> dict:
    if not db_path.exists():
        return {"files": 0, "rows": 0, "path": str(db_path)}
    con = connect(db_path)
    try:
        files = [dict(zip(("file_sha", "file_name", "format_code", "rows", "loaded_at"), r)) for r in
                 con.execute("SELECT file_sha, file_name, format_code, rows, loaded_at FROM gene_file ORDER BY loaded_at")]
        return {"files": len(files), "rows": sum(f["rows"] for f in files), "by_file": files, "path": str(db_path)}
    finally:
        con.close()
