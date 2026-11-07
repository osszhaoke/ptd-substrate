"""基因数据可用性与医学研究位点覆盖（G00；产品负责人 2026-10-14 08:08 “能测的就加”，R03 任务书）。

- 目标位点登记表在 core/gene-targets-<版本>.json：每个位点都写明出处、人群、效应方向和局限。分母就是这张表，
  不能拿“文件里正好有的位点”反过来定义分母。登记表只加版本，不改旧版本。
- 只核对“文件里有没有这个位点、分型成功没有、坐标对不对得上”。不算风险分，不推断 HLA 分型，
  不推断 CYP2C9 代谢表型，不给用药建议，不进任何预警。
- 缺失永远不等于阴性或参考型纯合；DI、II 原样保留，不改写成具体序列。
- 只在本机算；结果记一行“核对记录”（只有状态计数和登记表版本，不含基因型），登记表更新后可以按新版本重算，旧记录保留。
"""
from __future__ import annotations

import json
import re
import threading
from pathlib import Path

from h1_common import canonical_bytes, sha256_hex

import gene_db
import gene_profile

CORE = Path(__file__).resolve().parent / "core"
LOCK = threading.Lock()
STATUSES = ("PRESENT_CALLED", "PRESENT_NO_CALL", "NOT_IN_PROVIDED_FRAGMENT", "NOT_IN_FULL_EXPORT",
            "ASSAY_COVERAGE_UNKNOWN", "INFERRED_UNVALIDATED", "CLINICAL_CONFIRMATION_REQUIRED")
STATUS_ZH = {"PRESENT_CALLED": "直接观测到", "PRESENT_NO_CALL": "有这个位点，但没分型成功",
             "NOT_IN_PROVIDED_FRAGMENT": "不在这份片段里", "NOT_IN_FULL_EXPORT": "完整导出里没有",
             "ASSAY_COVERAGE_UNKNOWN": "无法确认是否检测", "INFERRED_UNVALIDATED": "只由未验证的方法推断",
             "CLINICAL_CONFIRMATION_REQUIRED": "临床使用前需要确认"}
ASSAY_ZH = {"SNP_ARRAY": "SNP 芯片原始数据（消费级）", "VCF_UNKNOWN_ASSAY": "VCF（文件没写是测序还是芯片）", "UNKNOWN": "无法判断"}
ARRAY_FORMATS = ("RAW_23ANDME", "RAW_ANCESTRY", "RAW_CSV")
AUTOSOMES = {str(i) for i in range(1, 23)}
FULL_MIN_ROWS = 100000
_BASES = re.compile(r"^[ACGT]{1,2}$")
_INDEL = re.compile(r"^[DI]{1,2}$")


def registry_path(version: str | None = None) -> Path:
    files = sorted(CORE.glob("gene-targets-*.json"), key=lambda p: [int(x) for x in p.stem.split("-")[-1].split(".")])
    if version:
        return CORE / f"gene-targets-{version}.json"
    return files[-1]


def load_registry(version: str | None = None) -> dict:
    return json.loads(registry_path(version).read_text("utf-8"))


def fingerprint(reg: dict) -> str:
    body = {k: reg[k] for k in ("version", "anchors", "cards", "targets")}
    return sha256_hex(canonical_bytes(json.loads(json.dumps(body), parse_float=str)))[:12]


def gt_class(gt) -> str:
    g = str(gt or "").strip().upper()
    if not g or g in gene_profile.NO_CALL:
        return "NO_CALL"
    if _INDEL.match(g):
        return "INDEL_CODE"  # 芯片的插入/缺失记号：原样保留，不改写成序列
    if _BASES.match(g):
        return "CALLED"
    return "UNPARSED"


def _q(con, sql, args=()):
    return con.execute(sql, args).fetchall()


def _file_facts(con, fid: int) -> dict:
    by = {c: (lo, hi, n) for c, lo, hi, n in _q(con, "SELECT chrom, MIN(pos), MAX(pos), COUNT(*) FROM genotype WHERE file_id=? GROUP BY chrom", (fid,))}
    rows = sum(v[2] for v in by.values())
    nocall = sum(n for g, n in _q(con, "SELECT UPPER(genotype), COUNT(*) FROM genotype WHERE file_id=? GROUP BY UPPER(genotype)", (fid,))
                 if gt_class(g) in ("NO_CALL", "UNPARSED"))
    nonstd = _q(con, "SELECT COUNT(*) FROM genotype WHERE file_id=? AND (rsid IS NULL OR rsid NOT LIKE 'rs%')", (fid,))[0][0]
    indel = _q(con, "SELECT COUNT(*) FROM genotype WHERE file_id=? AND UPPER(genotype) IN ('D','I','DD','II','DI','ID')", (fid,))[0][0]
    return {"chroms": by, "rows": rows, "valid": rows - nocall, "no_call": nocall, "nonstandard_ids": nonstd, "indel_codes": indel,
            "full": AUTOSOMES <= set(by) and rows >= FULL_MIN_ROWS}


def _by_rsid(con, fid, ids):
    for rs in ids:
        r = _q(con, "SELECT rsid, chrom, pos, genotype, line FROM genotype WHERE file_id=? AND rsid=? LIMIT 1", (fid, rs.lower()))
        if r:
            return dict(zip(("rsid", "chrom", "pos", "genotype", "line"), r[0]))
    return None


def _build(con, fid, declared: str, anchors: list) -> dict:
    """参考基因组版本：文件头写的 + 锚定位点核对。两者对不上、或都没有，就是“未知”，不按坐标去查。"""
    v37 = v38 = other = 0
    for a in anchors:
        r = _by_rsid(con, fid, [a["rsid"]])
        if not r:
            continue
        if r["pos"] == a["pos37"]:
            v37 += 1
        elif r["pos"] == a["pos38"]:
            v38 += 1
        else:
            other += 1
    anch = "GRCh37" if v37 and not v38 else "GRCh38" if v38 and not v37 else "CONFLICT" if v37 and v38 else ""
    found = v37 + v38 + other
    if anch in ("GRCh37", "GRCh38") and declared in ("", anch):
        value, status = anch, "ANCHOR_CONFIRMED"
    elif anch in ("GRCh37", "GRCh38") or anch == "CONFLICT":
        value, status = None, "CONFLICT"
    elif declared in ("GRCh37", "GRCh38"):
        value, status = declared, "DECLARED_ONLY"
    else:
        value, status = None, "UNKNOWN"
    zh = {"ANCHOR_CONFIRMED": f"{value}（{found} 个锚定位点里 {max(v37, v38)} 个对得上" + ("，文件头也这么写" if declared else "，文件头没写") + "）",
          "CONFLICT": f"对不上（文件头：{declared or '没写'}；锚定位点：GRCh37 {v37} 个、GRCh38 {v38} 个）",
          "DECLARED_ONLY": f"{declared}（只有文件头这么写，锚定位点没找到）",
          "UNKNOWN": "未知（文件头没写，锚定位点也没找到）；不按坐标查"}[status]
    return {"value": value, "status": status, "declared": declared or None, "anchors_found": found, "anchors_37": v37,
            "anchors_38": v38, "zh": zh}


def _pos(t: dict, build) -> int | None:
    return t.get("pos37") if build == "GRCh37" else t.get("pos38") if build == "GRCh38" else None


def _row(t: dict, reg: dict, **kw) -> dict:
    ev = reg["refs"].get(t.get("evidence") or "", {})
    out = {"target_id": t["id"], "card": t["card"], "kind": t["kind"], "gene": t.get("gene"), "rsid": t.get("rsid"),
           "hla_allele": t.get("hla"), "star_allele": t.get("star"), "chromosome": t.get("chrom"), "position": None,
           "genome_build": None, "required_variant": t.get("required_variant"), "observed_genotype": None,
           "genotype_class": None, "detection_method": None, "source_record_id": None, "direct_observation_status": None,
           "chip_coverage_status": None, "evidence_doi": ev.get("doi"), "evidence_cite": ev.get("cite"), "evidence_url": ev.get("url"),
           "evidence_population": t.get("population"), "allele_effect_direction": t.get("effect"),
           "clinical_actionability": t.get("actionability") or "仅研究；不能用于诊断、用药或预警",
           "interpretation_limitations": t.get("limits"), "clinical_confirmation_status": "CLINICAL_CONFIRMATION_REQUIRED",
           "coord_check": None, "note": None}
    out.update(kw)
    out["status_zh"] = STATUS_ZH.get(out["direct_observation_status"], "")
    return out


def _assess_target(con, fid, sha, facts, build, t, reg) -> dict:
    chrom = t.get("chrom")
    in_chrom = chrom in facts["chroms"]
    absent = "NOT_IN_FULL_EXPORT" if facts["full"] else "NOT_IN_PROVIDED_FRAGMENT"
    bv = build["value"]
    if t["kind"] == "HLA_ALLELE":
        if not in_chrom:
            return _row(t, reg, direct_observation_status="NOT_IN_PROVIDED_FRAGMENT" if not facts["full"] else "ASSAY_COVERAGE_UNKNOWN",
                        chip_coverage_status="ASSAY_COVERAGE_UNKNOWN", detection_method="需要临床 HLA 分型",
                        note=f"文件里没有 {chrom} 号染色体的数据")
        return _row(t, reg, direct_observation_status="ASSAY_COVERAGE_UNKNOWN", chip_coverage_status="ASSAY_COVERAGE_UNKNOWN",
                    detection_method="需要临床 HLA 分型；SNP 芯片不能直接分型，本系统也不做推断",
                    note="HLA 分型不能由单个 SNP 确认")
    if t["kind"] == "GENE_REGION":
        if not in_chrom:
            return _row(t, reg, direct_observation_status=absent if not facts["full"] else "ASSAY_COVERAGE_UNKNOWN",
                        chip_coverage_status="ASSAY_COVERAGE_UNKNOWN", detection_method="需要临床靶向测序",
                        note=f"文件里没有 {chrom} 号染色体的数据")
        lo, hi = (t.get("start37"), t.get("end37")) if bv == "GRCh37" else (t.get("start38"), t.get("end38")) if bv == "GRCh38" else (None, None)
        if lo is None:
            return _row(t, reg, direct_observation_status="ASSAY_COVERAGE_UNKNOWN", chip_coverage_status="ASSAY_COVERAGE_UNKNOWN",
                        detection_method="需要临床靶向测序", note="参考基因组版本未知，不按坐标数探针")
        flo, fhi, _ = facts["chroms"][chrom]
        if not facts["full"] and (hi < flo or lo > fhi):
            return _row(t, reg, direct_observation_status="NOT_IN_PROVIDED_FRAGMENT", chip_coverage_status="ASSAY_COVERAGE_UNKNOWN",
                        genome_build=bv, position=f"{lo}-{hi}", detection_method="需要临床靶向测序",
                        note=f"片段只到 {chrom} 号染色体 {flo}–{fhi}，这个基因不在里面")
        n = _q(con, "SELECT COUNT(*) FROM genotype WHERE file_id=? AND chrom=? AND pos BETWEEN ? AND ?", (fid, chrom, lo, hi))[0][0]
        return _row(t, reg, direct_observation_status="ASSAY_COVERAGE_UNKNOWN", chip_coverage_status="ASSAY_COVERAGE_UNKNOWN",
                    genome_build=bv, position=f"{lo}-{hi}", detection_method="需要临床靶向测序",
                    note=f"文件里有 {n} 个位点落在这个基因范围内；芯片位点不能说明罕见致病变异有没有被测到")
    # SNP（含 CYP2C9 星号等位的定义位点）
    hit = _by_rsid(con, fid, [t["rsid"]] + list(t.get("aliases") or []))
    if hit:
        cls = gt_class(hit["genotype"])
        reg_pos = _pos(t, bv)
        coord = ("REGISTRY_UNRESOLVED" if bv and not (t.get("pos37") or t.get("pos38")) else None) if reg_pos is None else \
            ("MATCH" if hit["pos"] == reg_pos and hit["chrom"] == chrom else "MISMATCH")
        note = []
        if hit["rsid"] != t["rsid"]:
            note.append(f"文件里用的是旧编号 {hit['rsid']}（已合并到 {t['rsid']}）")
        if coord == "REGISTRY_UNRESOLVED":
            note.append("登记表里这个位点的坐标还没核实，只按编号找到")
        if coord == "MISMATCH":
            note.append(f"坐标对不上：文件 {hit['chrom']}:{hit['pos']}，登记表（{bv}）{chrom}:{reg_pos}")
        if cls == "INDEL_CODE":
            note.append("基因型是芯片的插入/缺失记号，原样保留，没有改写成具体序列")
        if cls == "UNPARSED":
            note.append("基因型写法认不出，按没分型成功处理")
        return _row(t, reg, direct_observation_status="PRESENT_CALLED" if cls in ("CALLED", "INDEL_CODE") else "PRESENT_NO_CALL",
                    chip_coverage_status="DIRECT_IN_FILE", observed_genotype=hit["genotype"], genotype_class=cls,
                    position=hit["pos"], genome_build=bv, detection_method="SNP 芯片直接分型（文件原文）",
                    source_record_id=f"{sha[:12]}:{hit['line']}", coord_check=coord or "BUILD_UNKNOWN", note="；".join(note) or None)
    p = _pos(t, bv)
    if in_chrom and p is not None:
        other = _q(con, "SELECT rsid, line FROM genotype WHERE file_id=? AND chrom=? AND pos=? LIMIT 1", (fid, chrom, p))
        if other:
            return _row(t, reg, direct_observation_status="ASSAY_COVERAGE_UNKNOWN", chip_coverage_status="ASSAY_COVERAGE_UNKNOWN",
                        genome_build=bv, position=p, detection_method="同一坐标有别的探针编号",
                        source_record_id=f"{sha[:12]}:{other[0][1]}",
                        note=f"同一坐标是 {other[0][0]}，没有芯片说明书（manifest）映射，不当作这个位点")
    return _row(t, reg, direct_observation_status=absent, chip_coverage_status=absent if absent == "NOT_IN_FULL_EXPORT" else "ASSAY_COVERAGE_UNKNOWN",
                genome_build=bv, position=p, detection_method="—",
                note=(f"文件里没有 {chrom} 号染色体的数据" if not in_chrom else "文件里没找到这个编号") + "；没找到不等于阴性，也不等于参考型")


def _cards(reg: dict, rows: list) -> list:
    out = []
    for c in reg["cards"]:
        rs = [r for r in rows if r["card"] == c["id"]]
        counts = {s: sum(1 for r in rs if r["direct_observation_status"] == s) for s in STATUSES}
        snp = [r for r in rs if r["kind"] == "SNP"]
        called = sum(1 for r in snp if r["direct_observation_status"] == "PRESENT_CALLED")
        item = {"id": c["id"], "zh": c["zh"], "sub": c.get("sub"), "n_targets": len(rs), "counts": {k: v for k, v in counts.items() if v},
                "snp_targets": len(snp), "snp_called": called, "rule": "GENE." + c["id"]}
        if c["id"] == "G04":
            missing = [r["star_allele"] for r in snp if r["direct_observation_status"] != "PRESENT_CALLED"]
            item["phenotype"] = None  # 永远不在这里推断代谢表型
            item["g04_zh"] = (f"登记表里的 {len(snp)} 个定义位点都有结果；登记表以外的等位基因测不到，所以仍不推断代谢表型，要由药师或医生按临床检测判断"
                              if snp and not missing else
                              f"{len(missing)} 个定义位点没有结果（{'、'.join(m for m in missing if m)}）：信息不足，不推断 *1/*1，也不推断正常代谢")
        out.append(item)
    return out


def assess(db_path: Path, profiles: dict, reg: dict | None = None) -> dict:
    """profiles: file_sha → 纳管时记下的文件属性（含文件头写的 build）。返回每份已入库文件的覆盖核对结果。"""
    reg = reg or load_registry()
    files = []
    if db_path.exists():
        con = gene_db.connect(db_path)
        try:
            for fid, sha, name, code, loaded in _q(con, "SELECT file_id, file_sha, file_name, format_code, loaded_at FROM gene_file ORDER BY loaded_at"):
                prof = profiles.get(sha) or {}
                facts = _file_facts(con, fid)
                build = _build(con, fid, prof.get("build") or "", reg["anchors"])
                assay = "SNP_ARRAY" if code in ARRAY_FORMATS else "VCF_UNKNOWN_ASSAY" if code == "VCF" else "UNKNOWN"
                rows = [_assess_target(con, fid, sha, facts, build, t, reg) for t in reg["targets"]]
                files.append({"file_sha": sha, "file_name": name, "format_code": code, "vendor": prof.get("vendor") or None,
                              "loaded_at": loaded, "assay": assay, "assay_zh": ASSAY_ZH[assay], "build": build,
                              "rows_total": facts["rows"], "valid_genotypes": facts["valid"], "no_call": facts["no_call"],
                              "nonstandard_ids": facts["nonstandard_ids"], "indel_codes": facts["indel_codes"],
                              "chromosomes": sorted(facts["chroms"], key=lambda c: (gene_profile.CHROM_ORDER.index(c) if c in gene_profile.CHROM_ORDER else 99, c)),
                              "full_export": facts["full"], "cards": _cards(reg, rows), "matrix": rows})
        finally:
            con.close()
    return {"registry": {"version": reg["version"], "fingerprint": fingerprint(reg), "targets": len(reg["targets"]),
                         "refs": reg["refs"], "cards": reg["cards"]}, "files": files, "status_zh": STATUS_ZH}


def record_runs(ledger: Path, result: dict, now: str) -> list:
    """每份文件 × 每个登记表版本记一行核对记录（只有状态计数，没有基因型）；登记表换版本 = 重算，旧行保留。"""
    with LOCK:
        runs = [json.loads(x) for x in ledger.read_text("utf-8").splitlines() if x.strip()] if ledger.exists() else []
        seen = {(r["file_sha"], r["registry_fp"]) for r in runs}
        fp = result["registry"]["fingerprint"]
        new = []
        for f in result["files"]:
            if (f["file_sha"], fp) in seen:
                continue
            new.append({"at": now, "file_sha": f["file_sha"], "registry": result["registry"]["version"], "registry_fp": fp,
                        "build": f["build"]["value"], "cards": {c["id"]: c["counts"] for c in f["cards"]}})
        if new:
            ledger.parent.mkdir(parents=True, exist_ok=True)
            with open(ledger, "a", encoding="utf-8") as h:
                for r in new:
                    h.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
        return runs + new
