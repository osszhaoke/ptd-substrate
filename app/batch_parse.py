"""批量入库 · 认文件、读文件（R20，产品负责人 2026-10-14 批准“四步全做”）。

只认、只读，不保存：每份文件读成“按类型分好的候选”，写进暂存区，等本人确认后由 batch.py 保存。
- 认文件类型靠扩展名和文件头，不靠猜；认不出的照实说。
- 苹果健康 export.xml、Withings 导出、连续血糖仪导出的表格：按类型给出条数、时间段、来源、抽样原文（产品负责人 05:55Z 选“按类型确认”）。
- 高频的（心率、步数、活动能量、血糖、睡眠分段）原始明细另存，正式库每天一条汇总（产品负责人 06:04Z 选“明细另存 + 日汇总”）。
- 账号、个人资料这类文件不读内容，直接标“不入库”。
- 数值一律按原文的十进制文本保留，不经过浮点。
"""
from __future__ import annotations

import csv
import io
import json
import re
import zipfile
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from xml.etree import ElementTree
from zoneinfo import ZoneInfo

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".heic", ".webp", ".tif", ".tiff"}
SAMPLES = 5
SAMPLE_AT = {1, 2, 3, 10, 100, 1000, 10000, 100000}  # 抽样原文：前几条 + 越往后越稀（不用随机数，同一份文件每次抽到的一样）

# ----------------------------------------------------------------------------- 苹果健康 export.xml

# HK 类型 → (界面名, 存法, 代码或代码前缀, 单位)。series = 明细另存 + 每天汇总；each = 每条进正式库
AH_TYPES = {
    "HKQuantityTypeIdentifierHeartRate": ("心率", "series:minmaxavg", "AH_HR", "bpm"),
    "HKQuantityTypeIdentifierStepCount": ("步数", "series:sum", "AH_STEPS_DAY", "steps"),
    "HKQuantityTypeIdentifierActiveEnergyBurned": ("活动能量", "series:sum", "AH_ACTIVE_ENERGY_DAY", "kcal"),
    "HKQuantityTypeIdentifierBloodGlucose": ("血糖", "series:minmaxavg", "AH_GLUCOSE", "mmol/L"),
    "HKCategoryTypeIdentifierSleepAnalysis": ("睡眠", "series:sleep", "AH_SLEEP_DAY", "min"),
    "HKQuantityTypeIdentifierRestingHeartRate": ("静息心率", "each", "AH_RESTING_HR", "bpm"),
    "HKQuantityTypeIdentifierHeartRateVariabilitySDNN": ("心率变异性", "each", "AH_HRV", "ms"),
    "HKQuantityTypeIdentifierOxygenSaturation": ("血氧", "each", "AH_SPO2", "%"),
    "HKQuantityTypeIdentifierRespiratoryRate": ("呼吸频率", "each", "AH_RESP_RATE", "次/分"),
    "HKQuantityTypeIdentifierBodyTemperature": ("体温", "each", "AH_BODY_TEMP", "°C"),
    "HKQuantityTypeIdentifierBodyMass": ("体重", "each", "AH_WEIGHT", "kg"),
}
AH_UNIT = {"count/min": "bpm", "count": "steps", "kcal": "kcal", "Cal": "kcal", "%": "%", "kg": "kg", "ms": "ms",
           "degC": "°C", "°C": "°C"}
AH_SKIP_ZH = {  # 字典里没有、这次不入库的常见类型，给个中文名方便看
    "BasalEnergyBurned": "静息能量", "WalkingSpeed": "步行速度", "WalkingStepLength": "步长",
    "HeadphoneAudioExposure": "耳机音量", "WalkingDoubleSupportPercentage": "双脚支撑时间",
    "DistanceWalkingRunning": "步行跑步距离", "WalkingAsymmetryPercentage": "步行不对称",
    "FlightsClimbed": "爬楼层数", "BodyMassIndex": "体重指数", "BodyFatPercentage": "体脂率",
    "LeanBodyMass": "去脂体重", "AppleWalkingSteadiness": "步行稳定性", "Height": "身高",
    "AppleStandTime": "站立时间", "EnvironmentalAudioExposure": "环境噪音", "AppleExerciseTime": "锻炼时间",
}
SLEEP_ASLEEP = ("HKCategoryValueSleepAnalysisAsleep",)  # Core / Deep / REM / Unspecified 都以它开头
REC_RE = re.compile(rb'<Record type="([^"]+)"([^>]*)>')
ATTR_RE = re.compile(rb'(\w+)="([^"]*)"')


def _xml_unescape(b: bytes) -> str:
    return b.decode("utf-8", "replace").replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"') \
        .replace("&apos;", "'").replace("&amp;", "&")


def ah_date(text: str) -> str:
    """'2025-12-09 08:38:44 +0700' → '2025-12-09T08:38:44+07:00'（保留手机给的偏移）。"""
    m = re.fullmatch(r"(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}:\d{2}) ([+-]\d{2})(\d{2})", text.strip())
    if not m:
        raise ValueError("date")
    return f"{m.group(1)}T{m.group(2)}{m.group(3)}:{m.group(4)}"


def ah_unit(code_unit: str, unit: str) -> str | None:
    if code_unit == "mmol/L" and re.fullmatch(r"mmol(<[\d.]+>)?/L", unit):  # 血糖：mmol<180.15…>/L 就是 mmol/L
        return "mmol/L"
    if code_unit == "mmol/L" and unit in ("mg/dL", "mg/dl"):
        return "mg/dL"
    if code_unit == "min":
        return "min"
    if code_unit == "次/分" and unit == "count/min":
        return "count/min"
    return AH_UNIT.get(unit) if AH_UNIT.get(unit) == code_unit else None


def parse_apple_health(path: Path, stage: Path, skip_sources: set) -> dict:
    """流式读 export.xml（几百 MB 也只占很少内存）。每类写一个暂存文件：每行 [开始, 结束, 数值, 单位, 来源, 行号]。"""
    stage.mkdir(parents=True, exist_ok=True)
    outs, types, other = {}, {}, {}
    with open(path, "rb") as f:
        for lineno, line in enumerate(f, 1):
            if b"<Record " not in line:
                continue
            m = REC_RE.search(line)
            if not m:
                continue
            hk = m.group(1).decode()
            spec = AH_TYPES.get(hk)
            if spec is None:
                short = re.sub(r"^HK(Quantity|Category|DataType)TypeIdentifier|^HKDataType", "", hk)
                other[short] = other.get(short, 0) + 1
                continue
            a = {k.decode(): _xml_unescape(v) for k, v in ATTR_RE.findall(m.group(2))}
            t = types.setdefault(hk, {"count": 0, "first": None, "last": None, "sources": {}, "skipped": {},
                                      "bad": 0, "samples": []})
            src = a.get("sourceName", "")
            try:
                start, end = ah_date(a["startDate"]), ah_date(a.get("endDate") or a["startDate"])
            except (KeyError, ValueError):
                t["bad"] += 1
                continue
            if src in skip_sources:
                t["skipped"][src] = t["skipped"].get(src, 0) + 1
                continue
            label, mode, code, unit = spec
            value = a.get("value", "")
            if mode == "series:sleep":
                if not value.startswith(SLEEP_ASLEEP):
                    continue
                secs = (datetime.fromisoformat(end) - datetime.fromisoformat(start)).total_seconds()
                if secs <= 0:
                    t["bad"] += 1
                    continue
                value, u = _plain((Decimal(int(secs)) / 60).quantize(Decimal("0.1"))), "min"  # 这一段睡了几分钟
            else:
                u = ah_unit(unit, a.get("unit", ""))
                if u is None or not _is_number(value):
                    t["bad"] += 1
                    continue
                if code == "AH_SPO2" and Decimal(value) <= 1:  # 健康里血氧存成小数 0.97 → 97 %
                    value = _plain(Decimal(value) * 100)
            t["count"] += 1
            t["sources"][src] = t["sources"].get(src, 0) + 1
            t["first"] = min(t["first"] or start, start)
            t["last"] = max(t["last"] or start, start)
            if len(t["samples"]) < SAMPLES and t["count"] in SAMPLE_AT:
                t["samples"].append(m.group(0).decode("utf-8", "replace")[:300])
            if hk not in outs:
                outs[hk] = open(stage / (_key(hk) + ".jsonl"), "w", encoding="utf-8")
            outs[hk].write(json.dumps([start, end, value, u, src, lineno], ensure_ascii=False) + "\n")
    for f in outs.values():
        f.close()
    out = []
    for hk, t in types.items():
        label, mode, code, unit = AH_TYPES[hk]
        out.append({"key": _key(hk), "label": label, "mode": mode, "code": code, "unit": unit, "count": t["count"],
                    "first": t["first"], "last": t["last"], "sources": t["sources"], "skipped_sources": t["skipped"],
                    "bad": t["bad"], "samples": t["samples"], "source_kind": "APPLE_HEALTH"})
    out.sort(key=lambda x: -x["count"])
    return {"kind": "device", "source_kind": "APPLE_HEALTH", "label": "苹果健康导出", "types": out,
            "not_imported": sorted(({"label": AH_SKIP_ZH.get(k, k), "count": n} for k, n in other.items()),
                                   key=lambda x: -x["count"])}


def _key(hk: str) -> str:
    return re.sub(r"^HK(Quantity|Category)TypeIdentifier", "", hk)


def _is_number(text: str) -> bool:
    try:
        return Decimal(text).is_finite()
    except (InvalidOperation, ValueError):
        return False


def _plain(d: Decimal) -> str:
    s = format(d.normalize(), "f")
    return s if "." not in s else s.rstrip("0").rstrip(".") or "0"


# ----------------------------------------------------------------------------- 表格：CSV / Excel

def read_csv(path: Path, limit: int | None = None) -> list:
    raw = path.read_bytes()
    for enc in ("utf-8-sig", "gb18030"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ValueError("encoding")
    sample = text[:4096]
    delim = "\t" if sample.count("\t") > sample.count(",") else ","
    rows = []
    for i, r in enumerate(csv.reader(io.StringIO(text, newline=""), delimiter=delim)):
        if limit is not None and i >= limit:
            break
        rows.append([c.strip() for c in r])
    return rows


XL_NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def read_xlsx(path: Path, limit: int | None = None) -> list:
    """不装第三方库：xlsx 就是 zip + XML。只读第一个工作表；数字照原文文本保留。"""
    with zipfile.ZipFile(path) as z:
        names = set(z.namelist())
        strings = []
        if "xl/sharedStrings.xml" in names:
            root = ElementTree.fromstring(z.read("xl/sharedStrings.xml"))
            for si in root.findall("m:si", XL_NS):
                strings.append("".join(t.text or "" for t in si.iter("{%s}t" % XL_NS["m"])))
        sheet = "xl/worksheets/sheet1.xml" if "xl/worksheets/sheet1.xml" in names else \
            sorted(n for n in names if n.startswith("xl/worksheets/sheet"))[0]
        rows = []
        with z.open(sheet) as f:
            for _, el in ElementTree.iterparse(f):
                if el.tag != "{%s}row" % XL_NS["m"]:
                    continue
                row = {}
                for c in el.findall("m:c", XL_NS):
                    ref, t = c.get("r", ""), c.get("t")
                    col = _col_index(re.match(r"[A-Z]+", ref).group(0)) if ref else len(row)
                    v = c.find("m:v", XL_NS)
                    if t == "s" and v is not None:
                        val = strings[int(v.text)]
                    elif t == "inlineStr":
                        val = "".join(x.text or "" for x in c.iter("{%s}t" % XL_NS["m"]))
                    else:
                        val = v.text if v is not None and v.text is not None else ""
                    row[col] = val.strip()
                el.clear()
                if row:
                    rows.append([row.get(i, "") for i in range(max(row) + 1)])
                if limit is not None and len(rows) >= limit:
                    break
        return rows


def _col_index(letters: str) -> int:
    n = 0
    for ch in letters:
        n = n * 26 + ord(ch) - 64
    return n - 1


def read_table(path: Path, limit: int | None = None) -> list:
    return read_xlsx(path, limit) if path.suffix.lower() == ".xlsx" else read_csv(path, limit)


def excel_serial(text: str) -> datetime | None:
    """Excel 日期序号（1900 体系）→ 不带时区的时间。"""
    try:
        d = Decimal(text)
    except InvalidOperation:
        return None
    if not (20000 < d < 80000):
        return None
    return datetime(1899, 12, 30) + timedelta(days=float(d))


def parse_time(text: str, tz: str) -> str | None:
    """表格里常见的时间写法 → 带偏移的 ISO 时间；没写时区的按 tz 算。认不出返回 None。"""
    t = text.strip()
    m = re.fullmatch(r"(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})[ T](\d{1,2}):(\d{2})(?::(\d{2}))?(?:\.\d+)?\s*(Z|[+-]\d{2}:?\d{2})?", t)
    if m:
        y, mo, d, h, mi, s, off = m.groups()
        local = datetime(int(y), int(mo), int(d), int(h), int(mi), int(s or 0))
        if off:
            off = "+00:00" if off == "Z" else (off if ":" in off else off[:3] + ":" + off[3:])
            return local.isoformat() + off
        return local.replace(tzinfo=ZoneInfo(tz)).isoformat()
    x = excel_serial(t)
    if x is not None:
        return x.replace(microsecond=0, tzinfo=ZoneInfo(tz)).isoformat()
    return None


def parse_day(text: str) -> str | None:
    m = re.fullmatch(r"(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})", text.strip())
    return f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}" if m else None


# ----------------------------------------------------------------------------- 认识的表格格式

PTDS_HEADER = ["code", "value", "unit", "comparator", "observed_at", "observed_date", "tz"]
PERSONAL = {"account.csv", "user.csv", "user_survey.csv", "devices.csv", "signal.csv"}  # 个人资料：不读内容


def glucose_unit(values: list) -> str:
    """表里没写血糖单位时按数值大小推测：中位数 > 35 是 mg/dL，否则 mmol/L。界面上照实写“推测”。"""
    nums = sorted(Decimal(v) for v in values if _is_number(v))
    if not nums:
        return "mmol/L"
    return "mg/dL" if nums[len(nums) // 2] > 35 else "mmol/L"


# Withings 导出：文件名 → 怎么读。naive=表里的时间没写时区
WITHINGS = {
    "raw_hr_hr.csv": {"label": "心率", "mode": "series:minmaxavg", "code": "WITHINGS_HR", "unit": "bpm", "shape": "raw"},
    "raw_blood_glucose_Blood Glucose.csv": {"label": "血糖", "mode": "series:minmaxavg", "code": "WITHINGS_GLUCOSE",
                                            "unit": "glucose", "shape": "raw"},
    "aggregates_steps.csv": {"label": "每天步数", "mode": "each_day", "code": "WITHINGS_STEPS_DAY", "unit": "steps", "shape": "date_value"},
    "manual_spo2.csv": {"label": "血氧（手动测）", "mode": "each", "code": "WITHINGS_SPO2", "unit": "%", "shape": "date_value"},
    "raw_import_Respiratory rate.csv": {"label": "呼吸频率", "mode": "each", "code": "WITHINGS_RESP_RATE", "unit": "次/分", "shape": "raw"},
    "pwv.csv": {"label": "脉搏波速度", "mode": "each", "code": "WITHINGS_PWV", "unit": "m/s", "shape": "date_value"},
    "weight.csv": {"label": "体重", "mode": "each", "code": "WITHINGS_WEIGHT", "unit": "kg", "shape": "weight"},
    "bp.csv": {"label": "血压", "mode": "each", "code": "WITHINGS_SBP", "unit": "mmHg", "shape": "bp"},
    "sleep.csv": {"label": "睡眠", "mode": "each_day", "code": "WITHINGS_SLEEP", "unit": "min", "shape": "sleep"},
    "other.csv": {"label": "体脂率", "mode": "each", "code": "WITHINGS_FAT_PCT", "unit": "%", "shape": "other_fat"},
}
WITHINGS_HEAD = {"raw": "start", "date_value": "date", "weight": "date", "bp": "date", "sleep": "from", "other_fat": "type"}  # 表头第一列
CGM_FORMATS = [  # 连续血糖仪 App 导出的表（按表头认）
    {"cols": ["血糖时间", "血糖值"], "time": 0, "value": 1},
    {"cols": ["血糖自增ID", "时间", "血糖值"], "time": 1, "value": 2},
]


def _bracket(v: str) -> list:
    """Withings 原始表的 "[75]"、"[1620,690]" → ['75']、['1620','690']。"""
    v = v.strip()
    if v.startswith("["):
        return [x.strip() for x in v.strip("[]").split(",") if x.strip()]
    return [v] if v else []


def detect(path: Path, name: str, templates: dict) -> dict:
    """只看扩展名和文件头，判断这是什么文件、交给谁读。"""
    ext = path.suffix.lower()
    base = Path(name).name
    if ext in IMAGE_EXT:
        return {"kind": "lab_image", "label": "化验单（图片）"}
    if ext == ".pdf":
        return {"kind": "lab_pdf", "label": "化验单（PDF）"}
    if ext == ".gpx":
        return {"kind": "skip", "label": "运动轨迹", "why": "运动轨迹，不入库"}
    head = path.read_bytes()[:4096]
    if ext == ".xml":
        if b"<HealthData" in head or b"HealthData [" in head:
            return {"kind": "apple_health", "label": "苹果健康导出"}
        if b"ClinicalDocument" in head:
            return {"kind": "skip", "label": "苹果健康导出（另一种格式）", "why": "和 export.xml 是同一份数据的另一种格式，不重复导入"}
        return {"kind": "skip", "label": "XML 文件", "why": "认不出这种 XML，不入库"}
    if ext == ".vcf" or head.startswith(b"##fileformat=VCF") or re.search(rb"(?m)^rs\d+\t", head):
        return {"kind": "gene", "label": "基因文件", "why": "基因文件请从“基因”入口导入（只建索引，不解读）"}
    if base in PERSONAL:
        return {"kind": "skip", "label": "个人资料", "why": "账号、个人资料这类文件不读内容，不入库"}
    if ext in (".csv", ".xlsx", ".tsv", ".txt"):
        try:
            rows = read_table(path, limit=4)
        except Exception:  # noqa: BLE001
            return {"kind": "skip", "label": "表格", "why": "这个表格读不开"}
        if ext == ".txt" and (not rows or len(rows[0]) < 2):
            return {"kind": "skip", "label": "文本文件", "why": "说明文字，不入库"}
        if not rows:
            return {"kind": "skip", "label": "表格", "why": "空表"}
        header = rows[0]
        if header == PTDS_HEADER:
            return {"kind": "table_ptds", "label": "表格 · PTDS 标准格式"}
        if base in WITHINGS and header and header[0].strip().lower() == WITHINGS_HEAD[WITHINGS[base]["shape"]]:
            if len(rows) < 2:
                return {"kind": "skip", "label": "Withings · " + WITHINGS[base]["label"], "why": "空表"}
            return {"kind": "withings", "label": "Withings · " + WITHINGS[base]["label"], "spec": base}
        if base.startswith(("raw_", "aggregates_")) or base in ("activities.csv", "height.csv"):
            return {"kind": "skip", "label": "Withings 导出", "why": "空表" if len(rows) < 2 else "字典里没有这类数据，不入库"}
        for f in CGM_FORMATS:
            if [h.strip() for h in header] == f["cols"]:
                return {"kind": "cgm", "label": "表格 · 连续血糖", "format": f}
        sig = signature(header)
        if sig in templates:
            return {"kind": "table_template", "label": "表格 · 已认识的格式", "template": templates[sig]}
        if len(rows) < 2:
            return {"kind": "skip", "label": "表格", "why": "空表"}
        return {"kind": "table_unknown", "label": "表格 · 新格式", "header": header}
    return {"kind": "skip", "label": "其他文件", "why": "认不出这种文件，不入库"}


def signature(header: list) -> str:
    return "|".join(h.strip() for h in header)


# ----------------------------------------------------------------------------- 按类型读表

class Stager:
    """一类数据一个暂存文件，同时统计条数、时间段、来源、抽样原文。"""

    def __init__(self, stage: Path, key: str, label: str, mode: str, code: str, unit: str, source_kind: str,
                 note: str = ""):
        stage.mkdir(parents=True, exist_ok=True)
        self.f = open(stage / (key + ".jsonl"), "w", encoding="utf-8")
        self.t = {"key": key, "label": label, "mode": mode, "code": code, "unit": unit, "count": 0, "first": None,
                  "last": None, "sources": {}, "skipped_sources": {}, "bad": 0, "samples": [],
                  "source_kind": source_kind, "note": note}

    def add(self, start: str, end: str, value: str, unit: str, source: str, loc, raw: str):
        t = self.t
        t["count"] += 1
        t["sources"][source] = t["sources"].get(source, 0) + 1
        t["first"] = min(t["first"] or start, start)
        t["last"] = max(t["last"] or start, start)
        if len(t["samples"]) < SAMPLES and t["count"] in SAMPLE_AT:
            t["samples"].append(raw[:300])
        self.f.write(json.dumps([start, end, value, unit, source, loc], ensure_ascii=False) + "\n")

    def close(self) -> dict:
        self.f.close()
        return self.t


def parse_withings(path: Path, spec_name: str, stage: Path, tz: str) -> dict:
    spec = WITHINGS[spec_name]
    rows = read_csv(path)
    header, body = rows[0], rows[1:]
    src = "Withings"
    raw = lambda r: ",".join(r)  # noqa: E731
    types = []
    if spec["shape"] == "raw":  # start,duration,value；value 是 [75] 这样的数组
        unit = spec["unit"]
        if unit == "glucose":
            vals = [(_bracket(r[2]) or [""])[0] for r in body[:500] if len(r) >= 3]
            unit = glucose_unit(vals)
        s = Stager(stage, spec["code"], spec["label"], spec["mode"], spec["code"], unit, "DEVICE_WITHINGS",
                   "表里没写单位，按数值大小推测是 " + unit if spec["unit"] == "glucose" else "")
        for n, r in enumerate(body, 2):
            if len(r) < 3:
                s.t["bad"] += 1
                continue
            start, durs, vals = parse_time(r[0], tz), _bracket(r[1]), _bracket(r[2])
            if not start or not vals or len(durs) not in (0, len(vals)) or not all(_is_number(v) for v in vals + durs):
                s.t["bad"] += 1
                continue
            # 一行里可以有好几个读数："[60,60]"、"[75,76]"：第 k 个读数从前面几段时长加起来之后开始
            at = datetime.fromisoformat(start)
            for k, v in enumerate(vals):
                end = at + timedelta(seconds=float(durs[k])) if durs else at
                s.add(at.isoformat(), end.isoformat(), v, unit, src, f"{n}.{k + 1}" if len(vals) > 1 else n, raw(r))
                at = end
        types.append(s.close())
    elif spec["shape"] == "date_value":
        s = Stager(stage, spec["code"], spec["label"], spec["mode"], spec["code"], spec["unit"], "DEVICE_WITHINGS",
                   "表里的时间没写时区，按 " + tz + " 算" if spec["mode"] == "each" else "")
        for n, r in enumerate(body, 2):
            if len(r) < 2 or not _is_number(r[1]):
                s.t["bad"] += 1
                continue
            if spec["mode"] == "each_day":
                day = parse_day(r[0])
                if not day:
                    s.t["bad"] += 1
                    continue
                s.add(day, day, r[1], spec["unit"], src, n, raw(r))
            else:
                at = parse_time(r[0], tz)
                if not at:
                    s.t["bad"] += 1
                    continue
                s.add(at, at, r[1], spec["unit"], src, n, raw(r))
        types.append(s.close())
    elif spec["shape"] == "weight":
        i = header.index("Weight (kg)") if "Weight (kg)" in header else 1
        s = Stager(stage, "WITHINGS_WEIGHT", "体重", "each", "WITHINGS_WEIGHT", "kg", "DEVICE_WITHINGS",
                   "表里的时间没写时区，按 " + tz + " 算")
        for n, r in enumerate(body, 2):
            at = parse_time(r[0], tz) if r else None
            if not at or len(r) <= i or not _is_number(r[i]):
                s.t["bad"] += 1
                continue
            s.add(at, at, r[i], "kg", src, n, raw(r))
        types.append(s.close())
    elif spec["shape"] == "bp":
        cols = {"WITHINGS_SBP": ("收缩压", "Systolic", "mmHg"), "WITHINGS_DBP": ("舒张压", "Diastolic", "mmHg"),
                "WITHINGS_BP_HR": ("测血压时的心率", "Heart rate", "bpm")}
        for code, (label, col, unit) in cols.items():
            if col not in header:
                continue
            i = header.index(col)
            s = Stager(stage, code, label, "each", code, unit, "DEVICE_WITHINGS", "表里的时间没写时区，按 " + tz + " 算")
            for n, r in enumerate(body, 2):
                at = parse_time(r[0], tz) if r else None
                if at and len(r) > i and _is_number(r[i]):
                    s.add(at, at, r[i], unit, src, n, raw(r))
            t = s.close()
            if t["count"]:
                types.append(t)
    elif spec["shape"] == "sleep":  # 一行一晚：浅睡 + 深睡 + REM 的秒数 → 分钟，记在醒来那天
        idx = {h: i for i, h in enumerate(header)}
        s = Stager(stage, "WITHINGS_SLEEP", "睡眠时长", "each_day", "WITHINGS_SLEEP", "min", "DEVICE_WITHINGS",
                   "浅睡 + 深睡 + 快速眼动，记在醒来那天")
        h = Stager(stage, "WITHINGS_SLEEP_HR_AVG", "睡眠平均心率", "each_day", "WITHINGS_SLEEP_HR_AVG", "bpm",
                   "DEVICE_WITHINGS", "记在醒来那天")
        for n, r in enumerate(body, 2):
            try:
                end = datetime.fromisoformat(r[idx["to"]])
                secs = sum(Decimal(r[idx[k]] or "0") for k in ("light (s)", "deep (s)", "rem (s)"))
            except (KeyError, ValueError, InvalidOperation, IndexError):
                s.t["bad"] += 1
                continue
            day = end.astimezone(ZoneInfo(tz)).date().isoformat()
            s.add(day, day, _plain((secs / 60).quantize(Decimal("1"))), "min", src, n, raw(r))
            hr = r[idx["Average heart rate"]] if "Average heart rate" in idx and len(r) > idx["Average heart rate"] else ""
            if _is_number(hr):
                h.add(day, day, hr, "bpm", src, n, raw(r))
        types += [s.close(), h.close()]
    elif spec["shape"] == "other_fat":  # other.csv：type,date,value,unit；只取体脂率
        s = Stager(stage, "WITHINGS_FAT_PCT", "体脂率", "each", "WITHINGS_FAT_PCT", "%", "DEVICE_WITHINGS",
                   "表里的时间没写时区，按 " + tz + " 算；这个表里其他几十种体成分数据字典里没有，不入库")
        for n, r in enumerate(body, 2):
            if len(r) >= 3 and r[0] == "FAT_PERCENT":
                at = parse_time(r[1], tz)
                if at and _is_number(r[2]):
                    s.add(at, at, r[2], "%", src, n, raw(r))
        types.append(s.close())
    return {"kind": "device", "source_kind": "DEVICE_WITHINGS", "label": "Withings · " + spec["label"],
            "types": [t for t in types if t["count"] or t["bad"]], "not_imported": []}


def parse_cgm(path: Path, fmt: dict, stage: Path, tz: str, unit: str | None = None) -> dict:
    rows = read_table(path)
    body = rows[1:]
    vals = [r[fmt["value"]] for r in body[:500] if len(r) > fmt["value"]]
    guessed = unit is None
    unit = unit or glucose_unit(vals)
    s = Stager(stage, "CGM_GLUCOSE", "连续血糖", "series:minmaxavg", "CGM_GLUCOSE", unit, "DEVICE_CGM",
               ("表里没写单位，按数值大小推测是 " + unit + "；" if guessed else "") + "没写时区，按 " + tz + " 算")
    for n, r in enumerate(body, 2):
        if len(r) <= max(fmt["time"], fmt["value"]):
            s.t["bad"] += 1
            continue
        at = parse_time(r[fmt["time"]], tz)
        if not at or not _is_number(r[fmt["value"]]):
            s.t["bad"] += 1
            continue
        s.add(at, at, r[fmt["value"]], unit, "连续血糖仪导出", n, ",".join(r))
    return {"kind": "device", "source_kind": "DEVICE_CGM", "label": "连续血糖", "types": [s.close()], "not_imported": []}


def column_shapes(rows: list) -> list:
    """新格式表格交给本机千问之前，只给列名和“这一列像什么”（数字 / 时间 / 日期 / 文字），不给数值。"""
    header, body = rows[0], rows[1:51]
    out = []
    for i, h in enumerate(header):
        col = [r[i] for r in body if len(r) > i and r[i] != ""]
        if not col:
            shape = "空"
        elif all(_is_number(v) for v in col):
            shape = "数字"
        elif all(parse_time(v, "UTC") for v in col):
            shape = "时间"
        elif all(parse_day(v) for v in col):
            shape = "日期"
        else:
            shape = "文字"
        out.append({"col": h, "shape": shape})
    return out
