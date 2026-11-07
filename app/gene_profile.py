"""基因数据文件的资产属性（元属性）：格式、压缩、编码、行数、位点数、染色体、参考基因组版本……

只描述"这是一份什么样的文件"，不读基因型含义、不做任何解读。逐行流式读，几十 MB 到几 GB 都不整份进内存。
"""
from __future__ import annotations

import gzip
import io
import re
import zipfile
from collections import Counter
from pathlib import Path

VERSION = "gene-profile-0.1"
BUILD_RE = re.compile(r"GRCh3[78]|hg19|hg38|b37|build\s*3[678]|human_g1k_v37|NCBI\s*3[678]", re.I)
VENDORS = (("23andme", "23andMe"), ("wegene", "WeGene"), ("微基因", "WeGene"), ("ancestrydna", "AncestryDNA"),
           ("myheritage", "MyHeritage"), ("family tree dna", "FTDNA"), ("ftdna", "FTDNA"), ("livingdna", "LivingDNA"),
           ("genebox", "GeneBox"), ("23mofang", "23魔方"), ("各色", "各色基因"))
NO_CALL = {"--", "00", "0", "./.", ".|.", "."}
CHROM_ORDER = [str(i) for i in range(1, 23)] + ["X", "Y", "XY", "MT"]


def _build(text: str) -> str:
    m = BUILD_RE.search(text)
    if not m:
        return ""
    t = m.group(0).lower().replace(" ", "")
    if t in ("grch38", "hg38", "build38", "ncbi38"):
        return "GRCh38"
    if t in ("build36", "ncbi36"):
        return "NCBI36"
    return "GRCh37"


def chrom(c: str) -> str:
    c = c.strip()
    c = c[3:] if c.lower().startswith("chr") else c
    c = c.upper()
    return {"23": "X", "24": "Y", "25": "XY", "26": "MT", "M": "MT"}.get(c, c)


_chrom = chrom


def _open(path: Path):
    """返回 (二进制行流, 压缩方式, 包内文件名)。"""
    with open(path, "rb") as f:
        magic = f.read(4)
    if magic[:2] == b"\x1f\x8b":
        return gzip.open(path, "rb"), "gzip", ""
    if magic == b"PK\x03\x04":
        z = zipfile.ZipFile(path)
        members = [i for i in z.infolist() if not i.is_dir() and not i.filename.startswith("__MACOSX/")]
        if not members:
            return io.BytesIO(b""), "zip", ""
        pick = max(members, key=lambda i: i.file_size)
        return z.open(pick), "zip", pick.filename + (f"（包内共 {len(members)} 个文件，只看最大的）" if len(members) > 1 else "")
    return open(path, "rb"), "", ""


def profile(path: Path) -> dict:
    stream, compression, member = _open(path)
    with stream:
        head = stream.read(65536)
        if b"\x00" in head[:8192] or head[:4] in (b"BAM\x01", b"CRAM"):
            kind = "BAM" if head[:4] == b"BAM\x01" else "CRAM" if head[:4] == b"CRAM" else ""
            return {"version": VERSION, "format": (kind + " 比对文件（二进制）") if kind else "未识别的二进制文件",
                    "format_code": kind or "BINARY", "compression": compression, "member": member,
                    "encoding": "二进制", "text": False}
        return _profile_text(_chain(head, stream), compression, member)


def _chain(head: bytes, rest):
    tail = head
    while True:
        more = rest.read(1 << 20)
        if not more:
            if tail:
                yield from tail.split(b"\n")[:-1] if tail.endswith(b"\n") else tail.split(b"\n")
            return
        parts = (tail + more).split(b"\n")
        tail = parts.pop()
        yield from parts


def _profile_text(lines, compression: str, member: str) -> dict:
    total = blank = comment = data = header_line = 0
    encoding = "UTF-8"
    comments, header, ncols = [], None, Counter()
    chroms, rs, nocall, first_data = Counter(), 0, 0, []
    delim, plan = None, None
    for raw in lines:
        total += 1
        try:
            line = raw.decode("utf-8")
        except UnicodeDecodeError:
            encoding = "GB18030（不是 UTF-8）"
            line = raw.decode("gb18030", errors="replace")
        if total == 1 and line.startswith("\ufeff"):
            line, encoding = line[1:], "UTF-8（带 BOM）"
        line = line.rstrip("\r")
        if not line.strip():
            blank += 1
            continue
        if line[0] == "#":
            comment += 1
            if len(comments) < 400:
                comments.append(line)
            if line.startswith("#CHROM") or (header is None and re.match(r"#\s*rsid\b", line, re.I)):
                header = re.split(r"\t|,", line.lstrip("#").strip())
            continue
        if delim is None:
            delim = "\t" if "\t" in line else "," if "," in line else None
        cols = line.split(delim) if delim else line.split()
        if delim == ",":
            cols = [c.strip().strip('"') for c in cols]
        if plan is None:
            if header is None and not re.match(r"^(rs|i)\d+$", cols[0], re.I) and not cols[0].isdigit() \
                    and not cols[0].lower().startswith("chr") and len(cols) > 1:
                header = cols  # 无 # 的表头行（AncestryDNA、CSV 类）
                header_line = 1
                continue
            plan = _plan(header, cols)
        data += 1
        n = len(cols)
        ncols[n] += 1
        if len(first_data) < 3:
            first_data.append(cols)
        ci, gi, gj = plan
        if ci is not None and ci < n:
            chroms[cols[ci]] += 1
        if cols[0][:2] in ("rs", "RS") or (n > 2 and cols[2][:2] == "rs"):
            rs += 1
        if gi is not None and gi < n:
            gt = cols[gi].split(":", 1)[0] if plan_vcf(header) else cols[gi]
            if gj is not None and gj < n:
                gt += cols[gj]
            if gt in NO_CALL:
                nocall += 1
    merged = Counter()
    for c, k in chroms.items():
        merged[_chrom(c)] += k
    return _describe(total, blank, comment + header_line, data, encoding, comments, header, ncols, merged, rs, nocall,
                     first_data, delim, compression, member)


def plan_vcf(header) -> bool:
    return bool(header) and header[0].lower() == "chrom"


def _plan(header, cols):
    """按表头定好染色体列、基因型列（列号），逐行只做取值计数。"""
    h = [x.lower() for x in (header or [])]
    if h and h[0] == "chrom":  # VCF：第 10 列起是样本，取第一个样本的 GT
        return 0, (9 if len(h) > 9 else None), None
    ci = h.index("chromosome") if "chromosome" in h else (1 if len(cols) >= 4 and re.match(r"^(rs|i)\d+$", cols[0], re.I) else None)
    if "allele1" in h and "allele2" in h:
        return ci, h.index("allele1"), h.index("allele2")
    for name in ("genotype", "result"):
        if name in h:
            return ci, h.index(name), None
    return ci, (3 if len(cols) == 4 else None), None


def _describe(total, blank, comment, data, encoding, comments, header, ncols, chroms, rs, nocall, first_data, delim,
              compression, member) -> dict:
    ctext = "\n".join(comments)
    low = ctext.lower()
    vendor = next((name for key, name in VENDORS if key in low), "")
    build = _build(ctext)
    h = [x.lower() for x in (header or [])]
    first = (first_data[0][0] if first_data else "")
    out = {"version": VERSION, "compression": compression, "member": member, "encoding": encoding, "text": True,
           "lines_total": total, "lines_comment": comment, "lines_blank": blank, "rows_data": data,
           "columns": ncols.most_common(1)[0][0] if ncols else 0, "header": header or [],
           "delimiter": {"\t": "制表符", ",": "逗号", None: "空白"}[delim] if data else "",
           "chromosomes": sorted(chroms, key=lambda c: (CHROM_ORDER.index(c) if c in CHROM_ORDER else 99, c)),
           "build": build, "vendor": vendor}
    if comments and comments[0].startswith("##fileformat=VCF"):
        out.update(format_code="VCF", format="VCF " + comments[0].split("VCFv")[-1].strip() if "VCFv" in comments[0] else "VCF",
                   variants=data, samples=max(len(header or []) - 9, 0), no_calls=nocall)
    elif h[:4] in (["rsid", "chromosome", "position", "genotype"],) or (
            not h and out["columns"] == 4 and first[:2].lower() in ("rs", "i0", "i1", "i2", "i3", "i4", "i5", "i6", "i7", "i8", "i9")):
        name = vendor or "23andMe 式"
        out.update(format_code="RAW_23ANDME", format=f"{name} 原始数据（rsid/染色体/位置/基因型，4 列）",
                   snps=data, rsids=rs, no_calls=nocall)
    elif "allele1" in h and "allele2" in h:
        out.update(format_code="RAW_ANCESTRY", format=f"{vendor or 'AncestryDNA 式'} 原始数据（rsid/染色体/位置/两个等位基因，5 列）",
                   snps=data, rsids=rs, no_calls=nocall)
    elif h[:2] == ["rsid", "chromosome"] and "result" in h:
        out.update(format_code="RAW_CSV", format=f"{vendor or 'MyHeritage/FTDNA 式'} 原始数据（CSV）",
                   snps=data, rsids=rs, no_calls=nocall)
    elif first_data and first_data[0][0].startswith("@") and data >= 4:
        out.update(format_code="FASTQ", format="FASTQ 测序读段", reads=(total - blank) // 4)
    elif first_data and first_data[0][0].startswith(">"):
        out.update(format_code="FASTA", format="FASTA 序列")
    else:
        out.update(format_code="UNKNOWN_TEXT", format="未识别的文本文件（照样原样保存）")
    return out
