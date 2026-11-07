"""星轨 · 状态规则库（产品负责人 2026-10-14 批准 R05 第四节、R06）：一个算法 = 一条规则。

- 每条规则有 编号 + 版本 + 指纹。指纹 = 规则定义内容（条件、阈值、系数、参数）的 SHA-256 前 12 位，
  内容一变指纹就变；改规则只能发新版本，旧版本和旧结果都保留（与规则包、字典“只增不改”一致）。
- 引擎里的每张算法卡只引用“编号@版本”，计算记录里写着用的是哪条规则的哪一版（card_def.definition.rule）。
- 规则库页面只读；改规则 = 发新版本，由 产品负责人 或专家确认。
- 权威来源附原文链接（DOI 等）。link_checked = 本工程核对过链接能打开；没核对的界面上写“链接待核实”。
"""
from __future__ import annotations

import json
from pathlib import Path

from h1_common import canonical_bytes, sha256_hex

CORE = Path(__file__).resolve().parent / "core"

SETS = [
    {"id": "MAS", "zh": "sJIA·MAS 规则集"},
    {"id": "BIOAGE", "zh": "生物年龄规则集"},
    {"id": "SLEEP", "zh": "睡眠恢复"},
    {"id": "INFLAM", "zh": "炎症免疫"},
    {"id": "EXERCISE", "zh": "运动"},
    {"id": "METAB", "zh": "代谢"},
    {"id": "ORGAN", "zh": "器官功能"},
    {"id": "RHYTHM", "zh": "生理节律"},
    {"id": "BLOOD", "zh": "血液细胞"},
    {"id": "COAG", "zh": "凝血"},
    {"id": "LIVER", "zh": "肝脏"},
    {"id": "GENE", "zh": "基因研究位点覆盖"},
    {"id": "LIVE", "zh": "体验腕带（Somaloop）"},
    {"id": "CUSTOM", "zh": "我自定义的规则"},
]
SET_ZH = {s["id"]: s["zh"] for s in SETS}


def src(cite: str, url: str | None, checked: bool) -> dict:
    return {"cite": cite, "url": url, "link_checked": checked}


# 首批规则（版本 0.1）。method = 参与指纹的规则定义；MAS 与生物年龄的定义取自规则包、参数文件本身（见 _method）。
RULES = [
    # ---------------- sJIA·MAS（来自规则包 sjia-mas 0.1；定义见 core/sjia-rulepack-0.1.json）
    {"id": "MAS.HLH-2004", "version": "0.1", "set": "MAS", "name": "HLH-2004 标准", "kind": "分类标准",
     "card": "R2", "inputs": ["TEMP", "FERRITIN", "TG", "FIB", "HB", "PLT", "ANC", "SCD25"],
     "output": "成立 / 不成立 / 缺数据", "summary": "八项满足五项",
     "source": src("Henter JI, et al. HLH-2004: Diagnostic and therapeutic guidelines for hemophagocytic lymphohistiocytosis. "
                   "Pediatr Blood Cancer. 2007;48(2):124–131", "https://doi.org/10.1002/pbc.21039", False),
     "param_source": "原文", "population": "已知或疑似 sJIA（演示病例）"},
    {"id": "MAS.EULAR-2016", "version": "0.1", "set": "MAS", "name": "2016 EULAR/ACR/PRINTO 分类标准", "kind": "分类标准",
     "card": "R1", "inputs": ["FERRITIN", "PLT", "AST", "TG", "FIB"],
     "output": "成立 / 不成立 / 缺数据", "summary": "发热 + 已知或疑似 sJIA；铁蛋白 > 684 ng/mL，另需两项",
     "source": src("Ravelli A, et al. 2016 Classification criteria for macrophage activation syndrome complicating systemic "
                   "juvenile idiopathic arthritis. Ann Rheum Dis. 2016;75(3):481–489",
                   "https://doi.org/10.1136/annrheumdis-2015-208982", True),
     "param_source": "原文", "population": "已知或疑似 sJIA（演示病例）"},
    {"id": "MAS.MS-2019", "version": "0.1", "set": "MAS", "name": "MS 评分", "kind": "线性评分",
     "card": "R3", "inputs": ["PLT", "LDH", "FIB", "FERRITIN"],
     "output": "分数；不低于 -2.1 为成立", "summary": "4 项化验 + 3 项体征标记加权求和，界值 -2.1",
     "source": src("Minoia F, et al. Development and initial validation of the MS score for diagnosis of macrophage activation "
                   "syndrome in systemic juvenile idiopathic arthritis. Ann Rheum Dis. 2019;78(10):1357–1362",
                   "https://doi.org/10.1136/annrheumdis-2019-215211", True),
     "param_source": "原文", "population": "已知或疑似 sJIA（演示病例）"},
    {"id": "MAS.DYN", "version": "0.2", "set": "MAS", "name": "指标变化", "kind": "变化检测",
     "card": "DYN", "inputs": ["FERRITIN", "PLT", "FIB", "AST", "TG", "LDH", "HB", "ANC", "DDIMER", "FEVER", "SPLENOMEGALY",
                               "CNS_INVOLVEMENT", "HEMORRHAGE"],
     "output": "关注 / 观察 / 无", "summary": "与上一个时点比，核心指标变化超过阈值",
     "source": src("演示默认值，不出自文献（dynamic-config 0.2）", None, False),
     "param_source": "本工程默认值", "population": "演示病例"},
    # ---------------- 生物年龄
    {"id": "BIOAGE.PHENOAGE", "version": "0.1", "set": "BIOAGE", "name": "PhenoAge 表型年龄", "kind": "回归模型",
     "card": "PHENOAGE", "inputs": ["ALB", "CREA", "GLU", "CRP", "LYMPH_PCT", "MCV", "RDW_CV", "ALP", "WBC"],
     "output": "岁", "summary": "9 项血检 + 实际年龄 → 等效年龄（Gompertz 模型）",
     "source": src("Levine ME, et al. An epigenetic biomarker of aging for lifespan and healthspan. Aging. 2018;10(4):573–591",
                   "https://doi.org/10.18632/aging.101414", True),
     "param_source": "原文系数", "population": "成人；参考人群为美国 NHANES，用于中国人群未经验证", "needs_profile": True},
    {"id": "BIOAGE.KDM", "version": "0.2", "set": "BIOAGE", "name": "KDM 生物年龄", "kind": "回归模型",
     "card": "KDM", "inputs": ["ALB", "CREA", "GLU", "CRP", "LYMPH_PCT", "MCV", "RDW_CV", "ALP", "WBC"],
     "output": "岁", "summary": "各指标对年龄回归，按误差加权合成；分性别，最多缺 2 项",
     "source": src("Klemera P, Doubal S. A new approach to the concept and computation of biological age. "
                   "Mech Ageing Dev. 2006;127(3):240–248", "https://doi.org/10.1016/j.mad.2005.10.004", True),
     "param_source": "本地拟合：NHANES III（BioAge，Kwon & Belsky 2021，https://doi.org/10.1007/s11357-021-00480-5），男 4805 人、女 5353 人",
     "population": "成人 30–75 岁；用于中国人群未经验证", "needs_profile": True},
    {"id": "BIOAGE.HD", "version": "0.2", "set": "BIOAGE", "name": "稳态失调 HD", "kind": "距离",
     "card": "HD", "inputs": ["ALB", "CREA", "GLU", "CRP", "LYMPH_PCT", "MCV", "RDW_CV", "ALP", "WBC"],
     "output": "分（数越大偏离越多）", "summary": "与 20–30 岁健康参考人群的马氏距离；分性别，9 项都要有",
     "source": src("Cohen AA, et al. A novel statistical approach shows evidence for multi-system physiological dysregulation "
                   "during aging. Mech Ageing Dev. 2013;134(3-4):110–117", "https://doi.org/10.1016/j.mad.2013.01.004", True),
     "param_source": "本地拟合：NHANES III（BioAge）。0.2 修正了 0.1 参考人群 CRP 无变化导致的结果失效",
     "population": "成人 30–75 岁；用于中国人群未经验证", "needs_profile": True},
    {"id": "BIOAGE.LEVINE-2013", "version": "0", "set": "BIOAGE", "name": "Levine 2013 生物年龄", "kind": "回归模型",
     "status": "PLANNED", "inputs": [], "output": "岁", "summary": "规划中",
     "source": src("Levine ME. Modeling the rate of senescence: can estimated biological age predict mortality more accurately "
                   "than chronological age? J Gerontol A Biol Sci Med Sci. 2013;68(6):667–674",
                   "https://doi.org/10.1093/gerona/gls233", False),
     "param_source": "—", "population": "—"},
    {"id": "BIOAGE.ALLOSTATIC", "version": "0", "set": "BIOAGE", "name": "稳态负荷 Allostatic Load", "kind": "计分",
     "status": "PLANNED", "inputs": [], "output": "分", "summary": "规划中",
     "source": src("Seeman TE, et al. Price of adaptation—allostatic load and its health consequences. "
                   "Arch Intern Med. 1997;157(19):2259–2268", "https://doi.org/10.1001/archinte.1997.00440400111013", False),
     "param_source": "—", "population": "—"},
    # ---------------- 健康状态观察卡组 R01 首批 12 张（产品负责人 2026-10-14 “全做”）
    {"id": "SLEEP.A01-DURATION", "version": "0.1", "set": "SLEEP", "name": "睡眠时长", "kind": "原始观测",
     "card": "A01", "inputs": ["OURA_TOTAL_SLEEP", "AH_SLEEP"], "output": "小时 / 每晚",
     "summary": "主睡眠总时长 ÷ 60；同一晚优先 Oura，其次苹果健康，不相加",
     "method": {"op": "total_sleep_min / 60", "prefer": ["OURA_TOTAL_SLEEP", "AH_SLEEP"]},
     "source": src("Berry RB, et al. AASM Scoring Manual（睡眠时长、睡眠效率的定义）", "https://aasm.org/clinical-resources/scoring-manual/", False),
     "param_source": "设备读数", "population": "成人"},
    {"id": "SLEEP.A02-EFFICIENCY", "version": "0.1", "set": "SLEEP", "name": "睡眠效率", "kind": "确定性衍生",
     "card": "A02", "inputs": ["OURA_TOTAL_SLEEP", "OURA_TIME_IN_BED"], "output": "% / 每晚",
     "summary": "100 × 总睡眠 ÷ 卧床时长（同一条睡眠记录）",
     "method": {"op": "100 * total_sleep_min / time_in_bed_min", "same_record": True},
     "source": src("Berry RB, et al. AASM Scoring Manual（睡眠效率 = 总睡眠 / 卧床）", "https://aasm.org/clinical-resources/scoring-manual/", False),
     "param_source": "设备读数", "population": "成人"},
    {"id": "SLEEP.A03-HRV-DEV", "version": "0.1", "set": "SLEEP", "name": "夜间 HRV 基线偏离", "kind": "个体纵向观察",
     "card": "A03", "inputs": ["OURA_HRV"], "output": "ms、% / 每晚",
     "summary": "当晚 − 前 28 天（不含当晚）中位数；至少 14 晚",
     "method": {"op": "current - median(baseline)", "baseline_days": 28, "baseline_lag_days": 1, "min_nights": 14},
     "source": src("Task Force of the ESC and NASPE. Heart rate variability: standards of measurement, physiological "
                   "interpretation and clinical use. Circulation. 1996;93(5):1043–1065", "https://doi.org/10.1161/01.CIR.93.5.1043", False),
     "param_source": "本工程默认值（28 天、14 晚），未经临床验证", "population": "同一设备的本人纵向比较"},
    {"id": "SLEEP.A04-LOWHR-DEV", "version": "0.1", "set": "SLEEP", "name": "夜间最低心率基线偏离", "kind": "个体纵向观察",
     "card": "A04", "inputs": ["OURA_LOWEST_HR", "OURA_RESTING_HR"], "output": "bpm / 每晚",
     "summary": "当晚 − 前 28 天（不含当晚）中位数；至少 14 晚。用夜间最低心率，不当作日间静息心率",
     "method": {"op": "current - median(baseline)", "baseline_days": 28, "baseline_lag_days": 1, "min_nights": 14,
                "codes": ["OURA_LOWEST_HR", "OURA_RESTING_HR"],
                "note": "OURA_RESTING_HR 是字典 0.5 之前存 lowest_heart_rate 的旧代码，同一原始字段"},
     "source": src("Task Force of the ESC and NASPE. Circulation. 1996;93(5):1043–1065", "https://doi.org/10.1161/01.CIR.93.5.1043", False),
     "param_source": "本工程默认值（28 天、14 晚），未经临床验证", "population": "同一设备的本人纵向比较"},
    {"id": "SLEEP.A05S-TIMING", "version": "0.1", "set": "SLEEP", "name": "睡眠时点规律性（简化版）", "kind": "研究性描述",
     "card": "A05S", "inputs": ["OURA_BEDTIME_START", "OURA_BEDTIME_END"], "output": "分钟 / 近 14 天",
     "summary": "入睡、醒来时刻的环形标准差取平均；至少 7 晚。不是原版 SRI",
     "method": {"op": "mean(circular_sd(start), circular_sd(end))", "window_days": 14, "min_nights": 7,
                "circular_sd": "sqrt(-2 ln R) × 1440 / 2π"},
     "source": src("对照：Phillips AJK, et al. Irregular sleep/wake patterns are associated with poorer academic performance "
                   "and delayed circadian and sleep/wake timing. Sci Rep. 2017;7:3216（原版 SRI，本卡不是 SRI）",
                   "https://doi.org/10.1038/s41598-017-03171-4", False),
     "param_source": "本工程定义，研究性", "population": "成人"},
    {"id": "INFLAM.B01-CRP", "version": "0.1", "set": "INFLAM", "name": "CRP / hs-CRP", "kind": "原始观测",
     "card": "B01", "inputs": ["HSCRP", "CRP"], "output": "mg/L / 检测日",
     "summary": "直接读数；同一天优先超敏，检测类型分开记；与上一次同类检测比变化",
     "method": {"op": "direct", "prefer": ["HSCRP", "CRP"], "change": "same assay"},
     "source": src("Pearson TA, et al. Markers of inflammation and cardiovascular disease: application to clinical and public "
                   "health practice. Circulation. 2003;107(3):499–511", "https://doi.org/10.1161/01.CIR.0000052939.46093.45", False),
     "param_source": "化验读数", "population": "成人"},
    {"id": "INFLAM.B02-NLR", "version": "0.1", "set": "INFLAM", "name": "NLR 中性粒/淋巴比", "kind": "确定性衍生",
     "card": "B02", "inputs": ["ANC", "LYMPH"], "output": "比值 / 同次血检",
     "summary": "中性粒细胞绝对值 ÷ 淋巴细胞绝对值；只用同一天同一份报告，不用百分比",
     "method": {"op": "ANC / LYMPH", "same_report": True},
     "source": src("Zahorec R. Ratio of neutrophil to lymphocyte counts—rapid and simple parameter of systemic inflammation "
                   "and stress in critically ill. Bratisl Lek Listy. 2001;102(1):5–14", "https://pubmed.ncbi.nlm.nih.gov/11723675/", False),
     "param_source": "化验读数", "population": "非特异；没有通用的健康人群判定界值"},
    {"id": "EXERCISE.C01-WEEKLY", "version": "0.1", "set": "EXERCISE", "name": "运动时长与次数", "kind": "确定性衍生",
     "card": "C01", "inputs": ["OURA_WORKOUT_MIN"], "output": "分钟、次 / 近 7 天",
     "summary": "近 7 天每次运动时长相加，并数次数；目前只用 Oura，同一次运动不重复计",
     "method": {"op": "sum(minutes), count(sessions)", "window_days": 7},
     "source": src("Bull FC, et al. World Health Organization 2020 guidelines on physical activity and sedentary behaviour. "
                   "Br J Sports Med. 2020;54(24):1451–1462", "https://doi.org/10.1136/bjsports-2020-102955", False),
     "param_source": "设备读数", "population": "成人"},
    {"id": "METAB.D01-HBA1C", "version": "0.1", "set": "METAB", "name": "糖化血红蛋白 HbA1c", "kind": "原始观测",
     "card": "D01", "inputs": ["HBA1C"], "output": "%（NGSP）/ 检测日",
     "summary": "直接读数；mmol/mol 按 IFCC–NGSP 主方程换算；与上一次比差值",
     "method": {"op": "direct", "ifcc_to_ngsp": "0.09148 × IFCC + 2.152"},
     "source": src("Hoelzel W, et al. IFCC reference system for measurement of hemoglobin A1c in human blood and the national "
                   "standardization schemes in the United States, Japan, and Sweden. Clin Chem. 2004;50(1):166–174",
                   "https://doi.org/10.1373/clinchem.2003.024802", False),
     "param_source": "化验读数", "population": "成人"},
    {"id": "METAB.D02-NONHDL", "version": "0.1", "set": "METAB", "name": "非 HDL 胆固醇", "kind": "确定性衍生",
     "card": "D02", "inputs": ["TC", "HDL_C"], "output": "mmol/L / 同次血检",
     "summary": "总胆固醇 − 高密度脂蛋白胆固醇；只用同一天同一份报告",
     "method": {"op": "TC - HDL_C", "same_report": True},
     "source": src("Grundy SM, et al. 2018 AHA/ACC/... Guideline on the Management of Blood Cholesterol. "
                   "Circulation. 2019;139(25):e1082–e1143", "https://doi.org/10.1161/CIR.0000000000000625", False),
     "param_source": "化验读数", "population": "成人"},
    {"id": "ORGAN.E01-EGFR", "version": "0.1", "set": "ORGAN", "name": "eGFR（CKD-EPI 2021）", "kind": "确定性衍生",
     "card": "E01", "inputs": ["CREA"], "output": "mL/min/1.73m²",
     "summary": "CKD-EPI 2021 肌酐方程（不含种族项）；肌酐 μmol/L ÷ 88.4；只用于 18 岁以上",
     "method": {"op": "142 × min(Scr/κ,1)^α × max(Scr/κ,1)^-1.200 × 0.9938^age × 1.012[女]",
                "kappa": {"女": 0.7, "男": 0.9}, "alpha": {"女": -0.241, "男": -0.302}, "umol_per_mgdl": 88.4, "min_age": 18},
     "source": src("Inker LA, et al. New creatinine- and cystatin C–based equations to estimate GFR without race. "
                   "N Engl J Med. 2021;385(19):1737–1749", "https://doi.org/10.1056/NEJMoa2102953", False),
     "param_source": "原文系数", "population": "成人；肌酐应为标准化检测", "needs_profile": True},
    {"id": "RHYTHM.F01-TEMPDEV", "version": "0.1", "set": "RHYTHM", "name": "夜间体温偏离", "kind": "设备衍生观测",
     "card": "F01", "inputs": ["OURA_TEMP_DEV"], "output": "°C / 每晚",
     "summary": "直接读 Oura 算好的基线偏离值，不是皮肤温度",
     "method": {"op": "vendor_derived"},
     "source": src("Oura API v2 文档（daily_readiness.temperature_deviation）", "https://cloud.ouraring.com/v2/docs", False),
     "param_source": "厂商算法", "population": "同一设备的本人纵向比较"},
]

# 分器官观察（产品负责人 2026-10-14 07:33 选定：A01 血液细胞、A02 凝血、A03 肝脏，甘油三酯并入肝脏）。
# 每条 = 一项化验的读数 + 与上一次同项读数比的变化。R03（Ravelli 2016 动态共识）没有给出变化阈值，所以这里不设阈值、不判好坏。
_EULAR = src("Fautrel B, et al. EULAR/PReS recommendations for the diagnosis and management of Still's disease, comprising "
             "systemic juvenile idiopathic arthritis and adult-onset Still's disease. Ann Rheum Dis. 2024;83(12):1614–1627"
             "（推荐 10）；指标先后参照 Ravelli A, et al. RMD Open. 2016;2(1):e000161",
             "https://doi.org/10.1136/ard-2024-225851", True)
BRANCH = {
    "BLOOD": [("PLT", "血小板"), ("ANC", "中性粒细胞"), ("WBC", "白细胞"), ("HB", "血红蛋白")],
    "COAG": [("FIB", "纤维蛋白原"), ("DDIMER", "D-二聚体"), ("PT", "凝血酶原时间"), ("INR", "INR"), ("APTT", "APTT")],
    "LIVER": [("AST", "AST"), ("LDH", "LDH"), ("ALT", "ALT"), ("TBIL", "总胆红素"), ("DBIL", "直接胆红素"), ("ALB", "白蛋白"),
              ("TG", "甘油三酯")],
}
for _set, _items in BRANCH.items():
    for _code, _zh in _items:
        RULES.append({"id": f"{_set}.{_code}", "version": "0.1", "set": _set, "name": _zh, "kind": "原始观测",
                      "card": _code, "inputs": [_code], "output": "读数 / 检测日",
                      "summary": "直接读数，并和上一次同项读数比变化；文献没有给出变化阈值，所以不设阈值、不判好坏",
                      "method": {"op": "direct", "change": "vs previous same code", "threshold": None},
                      "source": _EULAR, "param_source": "化验读数", "population": "研究演示；没有判定阈值"})
# 基因研究位点覆盖（产品负责人 2026-10-14 08:08 “能测的就加”）：每组一条规则，定义 = 登记表里这一组的目标位点；
# 只核对有没有、分型成功没有，不判好坏、不出风险分。登记表换版本，指纹跟着变。
_GT = json.loads(sorted(CORE.glob("gene-targets-*.json"), key=lambda p: [int(x) for x in p.stem.split("-")[-1].split(".")])[-1].read_text("utf-8"))
for _c in _GT["cards"]:
    _ref = _GT["refs"].get(_c.get("evidence") or "", {})
    RULES.append({"id": f"GENE.{_c['id']}", "version": _GT["version"], "set": "GENE", "name": _c["zh"], "kind": "位点覆盖核对",
                  "card": _c["id"], "inputs": [], "output": "每个位点：直接观测 / 没分型成功 / 不在片段里 / 完整导出里没有 / 无法确认",
                  "summary": _c["rule_zh"],
                  "method": {"registry": _GT["version"], "targets": [t for t in _GT["targets"] if t["card"] == _c["id"]] if _c["id"] != "G00" else
                             {"anchors": _GT["anchors"], "cards": [c["id"] for c in _GT["cards"]]}, "threshold": None, "score": None},
                  "source": src(_ref.get("cite", "本工程登记表"), _ref.get("url"), bool(_ref.get("url"))),
                  "param_source": "目标位点登记表 v" + _GT["version"], "population": _c.get("population", "研究用途；不用于诊断、用药或预警")})
# 体验腕带（Somaloop，产品负责人 2026-10-14 10:51 确认）：只在 sJIA 演示里用。基线三条是 A03 / A04 / F01 的 0.2 版，
# 另立编号是为了不动 Oura 用的 0.1 版（编号@版本 → 指纹，旧版本和旧结果都保留）。算法见 band_cards.py。
_TASK_FORCE = src("Task Force of the ESC and NASPE. Heart rate variability: standards of measurement, physiological "
                  "interpretation and clinical use. Circulation. 1996;93(5):1043–1065", "https://doi.org/10.1161/01.CIR.93.5.1043", False)
_NIGHT = {"night": "本地 0:00–6:00", "min_readings_per_night": 3, "baseline_days": 28, "baseline_lag_days": 1, "min_nights": 14}
RULES += [
    {"id": "LIVE.SOMALOOP-SPOT", "version": "0.1", "set": "LIVE", "name": "现场体征", "kind": "原始观测",
     "card": "SPOT", "inputs": ["SOMALOOP_HR", "SOMALOOP_SPO2", "SOMALOOP_SKIN_TEMP", "SOMALOOP_HRV"], "output": "最近读数 / 是否刚测的",
     "summary": "四项的最近读数；1 分钟内算刚测的。只描述，不判断。皮温不是体温，不计入发热",
     "method": {"op": "latest", "fresh_seconds": 60},
     "source": src("Somaloop 体验腕带实时读数（腕带桥直连）", None, False), "param_source": "设备读数", "population": "现场体验者"},
    {"id": "LIVE.SPO2-LOW", "version": "0.1", "set": "LIVE", "name": "血氧低值提示", "kind": "研究性描述",
     "card": "SPO2LOW", "inputs": ["SOMALOOP_SPO2"], "output": "条数 / 本位体验者",
     "summary": "本位体验者的血氧读数里低于 94% 的条数。研究演示，未经临床验证；只提示，不发提醒、不进任何预警",
     "method": {"op": "count(value < threshold)", "threshold": "94", "unit": "%", "scope": "current visitor"},
     "source": src("O'Driscoll BR, et al. BTS guideline for oxygen use in adults in healthcare and emergency settings. "
                   "Thorax. 2017;72(Suppl 1):i1–i90（多数急症成人的目标血氧 94–98%）", "https://doi.org/10.1136/thoraxjnl-2016-209729", False),
     "param_source": "阈值借自成人给氧目标范围的下限，用在体验者身上是研究演示，未经临床验证", "population": "研究演示"},
    {"id": "SLEEP.A03-HRV-DEV-SOMALOOP", "version": "0.2", "set": "LIVE", "name": "夜间 HRV 基线偏离（Somaloop）", "kind": "个体纵向观察",
     "card": "A03", "inputs": ["SOMALOOP_HRV"], "output": "ms / 每晚",
     "summary": "A03 的 0.2 版：输入换成 Somaloop。当晚中位数 − 前 28 晚（不含当晚）中位数；至少 14 晚",
     "method": dict(_NIGHT, op="median(night) - median(baseline)", based_on="SLEEP.A03-HRV-DEV@0.1"),
     "source": _TASK_FORCE, "param_source": "本工程默认值（夜间时段、28 天、14 晚），未经临床验证", "population": "同一设备的本人纵向比较"},
    {"id": "SLEEP.A04-LOWHR-DEV-SOMALOOP", "version": "0.2", "set": "LIVE", "name": "夜间最低心率基线偏离（Somaloop）", "kind": "个体纵向观察",
     "card": "A04", "inputs": ["SOMALOOP_HR"], "output": "次/分 / 每晚",
     "summary": "A04 的 0.2 版：输入换成 Somaloop。当晚最低心率 − 前 28 晚（不含当晚）中位数；至少 14 晚",
     "method": dict(_NIGHT, op="min(night) - median(baseline)", based_on="SLEEP.A04-LOWHR-DEV@0.1"),
     "source": _TASK_FORCE, "param_source": "本工程默认值（夜间时段、28 天、14 晚），未经临床验证", "population": "同一设备的本人纵向比较"},
    {"id": "RHYTHM.F01-TEMPDEV-SOMALOOP", "version": "0.2", "set": "LIVE", "name": "夜间体温偏离（Somaloop 皮温）", "kind": "个体纵向观察",
     "card": "F01", "inputs": ["SOMALOOP_SKIN_TEMP"], "output": "°C / 每晚",
     "summary": "F01 的 0.2 版：用夜间皮肤温度中位数和自己前 28 晚比；至少 14 晚。皮温只作背景，不计入发热",
     "method": dict(_NIGHT, op="median(night) - median(baseline)", based_on="RHYTHM.F01-TEMPDEV@0.1"),
     "source": src("Maijala A, et al. Nocturnal finger skin temperature in menstrual cycle tracking: ambulatory pilot study "
                   "using a wearable Oura ring. BMC Womens Health. 2019;19(1):150（夜间皮温相对个人基线的用法）",
                   "https://doi.org/10.1186/s12905-019-0844-9", False),
     "param_source": "本工程默认值（夜间时段、28 天、14 晚），未经临床验证", "population": "同一设备的本人纵向比较"},
]
BY_ID = {r["id"]: r for r in RULES}

REVIEW_ZH = {"PENDING": "待专家核实"}


def _method(r: dict) -> object:
    """参与指纹的规则定义。"""
    if r["set"] == "MAS":
        if r["card"] == "DYN":
            d = json.loads((CORE / "dynamic-config-0.2.json").read_text("utf-8"))
            return {"indicators": d["indicators"], "general_sum_threshold": d["general_sum_threshold"],
                    "sensitivity_multipliers": d["sensitivity_multipliers"]}
        return json.loads((CORE / "sjia-rulepack-0.1.json").read_text("utf-8"))["rules"][r["card"]]
    if r["set"] == "BIOAGE" and r.get("status") != "PLANNED":
        if r["card"] == "PHENOAGE":
            return {"xb": "-19.907 - 0.0336 ALB + 0.0095 CREA + 0.1953 GLU + 0.0954 ln(CRP mg/dL) - 0.0120 LYMPH% "
                          "+ 0.0268 MCV + 0.3306 RDW + 0.00188 ALP + 0.0554 WBC + 0.0804 age", "gamma": 0.0076927,
                    "pa": "141.50225 + ln(-0.00553 ln(1 - M)) / 0.090165"}
        p = json.loads((CORE / "bioage-params-0.2.json").read_text("utf-8"))
        key = r["card"].lower()
        return {sex: v[key] for sex, v in p["sex"].items()}
    return r.get("method") or {}


_FP = {}


def fingerprint(rule_id: str) -> str:
    if rule_id not in _FP:
        r = BY_ID[rule_id]
        _FP[rule_id] = sha256_hex(canonical_bytes(json.loads(json.dumps(
            {"id": r["id"], "version": r["version"], "method": _method(r)}), parse_float=str)))[:12]
    return _FP[rule_id]


def ref(rule_id: str) -> str:
    return f"{rule_id}@{BY_ID[rule_id]['version']}"


def private_rule(rule_id, *, rules, methods):
    """Project explicit bound release inputs, without lazy IO or _FP writes.

    The caller owns the release values during projection. The returned private
    value needs no registry/cache reference. Old public functions are unchanged.
    """
    from compute_input_versions import private_value
    r = rules[rule_id]
    if r['set'] == 'MAS':
        if r['card'] == 'DYN':
            d = methods['dynamic-config-0.2.json']
            method = {k: d[k] for k in ('indicators', 'general_sum_threshold',
                                       'sensitivity_multipliers')}
        else:
            method = methods['sjia-rulepack-0.1.json']['rules'][r['card']]
    elif r['set'] == 'BIOAGE' and r.get('status') != 'PLANNED':
        if r['card'] == 'PHENOAGE':
            method = _method(r)  # This branch is a literal formula, no file IO.
        else:
            method = {sex: v[r['card'].lower()] for sex, v in
                      methods['bioage-params-0.2.json']['sex'].items()}
    else:
        method = r.get('method') or {}
    definition = {'id': r['id'], 'version': r['version'], 'method': method}
    # Bound the successful projection before serialization. On an invalid type,
    # retain the old serialization/canonical exception, never accept the value.
    try:
        private = private_value(definition)
    except ValueError as exc:
        if str(exc) != 'INPUT_VERSION_TYPE':
            raise
        canonical_bytes(json.loads(json.dumps(definition), parse_float=str))
        raise
    bounded = private.copy()
    fingerprint = sha256_hex(canonical_bytes(json.loads(json.dumps(bounded), parse_float=str)))[:12]
    return private_value(dict(bounded, fingerprint=fingerprint,
                              ref=f"{r['id']}@{r['version']}"))


def rows(registry=None, used_by: dict | None = None, custom: list | None = None) -> list:
    """规则库列表（界面只读）。used_by: rule_id → [“引擎 · 卡名”]。custom: 自定义卡（每张一条规则）。"""
    used_by = used_by or {}
    review = json.loads((CORE / "sjia-rulepack-0.1.json").read_text("utf-8"))["rules"]
    out = []
    for r in RULES:
        if r["id"] == "MAS.DYN":
            continue  # Retired demo rule; BY_ID retained only for historical references.
        planned = r.get("status") == "PLANNED"
        labels = []
        for c in r.get("inputs") or []:
            d = registry.current.codes.get(c) if registry else None
            labels.append(d.label_zh if d else c)
        rv = "待专家核实"
        if r["set"] == "MAS" and r["card"] in review:
            rv = REVIEW_ZH.get(review[r["card"]]["expert_review"], review[r["card"]]["expert_review"])
        fidelity = review[r["card"]].get("fidelity_zh") if r["set"] == "MAS" and r["card"] in review else None
        out.append({"id": r["id"], "version": r["version"], "ref": f"{r['id']}@{r['version']}", "set": r["set"],
                    "set_zh": SET_ZH[r["set"]], "name": r["name"], "kind": r["kind"], "inputs": r.get("inputs") or [],
                    "inputs_zh": labels, "output": r["output"], "summary": r["summary"], "source": r["source"],
                    "param_source": r["param_source"], "population": r["population"], "review": rv,
                    "status": "PLANNED" if planned else "ACTIVE", "maturity": "规划中" if planned else "早期测试",
                    "fingerprint": None if planned else fingerprint(r["id"]), "fidelity": fidelity,
                    "method": None if planned else _method(r) if r["set"] not in ("MAS",) else None,
                    "used_by": used_by.get(r["id"], [])})
    for c in custom or []:
        d = c["definition"]
        out.append({"id": "CUSTOM." + c["card_id"], "version": str(len(c["versions"])), "ref": c["card_def_id"][:12],
                    "set": "CUSTOM", "set_zh": SET_ZH["CUSTOM"], "name": d["name"], "kind": "阈值 / 变化",
                    "inputs": [d["code"]], "inputs_zh": [d["label_zh"]], "output": "观察 / 关注 / 无",
                    "summary": c["rule_zh"], "source": src("本人自设，不是医学规则", None, False),
                    "param_source": "本人自设", "population": "本人", "review": "不需要（本人自设）", "status": "ACTIVE",
                    "maturity": "早期测试", "fingerprint": c["card_def_id"][:12], "fidelity": None, "method": None,
                    "used_by": ["自定义卡 · " + d["name"]]})
    return out
