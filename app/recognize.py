"""星炬 · 化验单识别（本机 OCR + 本机千问），HR-35：

- 文字由 macOS Vision 在这台电脑上读出（app/tools/ocr_vision.swift）；
- 本机千问只负责"这一行是哪个指标"，数值与单位一律从这一行的原文截取，不换算、不四舍五入；
- 每个值带原文位置（页、行、框）；找不到原文的值不出现；所有结果都要本人逐项确认后才保存。
千问不可用时退到同义词表对照，并在引擎信息里如实写明。
"""
from __future__ import annotations

import vision_runtime
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

APP = Path(__file__).resolve().parent
SWIFT_SRC = APP / "tools" / "ocr_vision.swift"
BIN_DIR = Path(os.environ.get("PTDS_BIN", "~/.ptds/bin")).expanduser()
ENTRY_FAMILIES = ("LAB", "VITAL")

# 同义词（千问不可用时的退路，也作为给千问的提示）
ALIASES = {
    "FERRITIN": ["铁蛋白", "血清铁蛋白", "FER", "Ferritin", "SF"],
    "PLT": ["血小板计数", "血小板", "PLT"],
    "AST": ["天门冬氨酸氨基转移酶", "谷草转氨酶", "AST", "GOT"],
    "ALT": ["丙氨酸氨基转移酶", "谷丙转氨酶", "ALT", "GPT"],
    "TG": ["甘油三酯", "三酰甘油", "TG"],
    "FIB": ["纤维蛋白原", "FIB", "Fg"],
    "LDH": ["乳酸脱氢酶", "LDH", "LD"],
    "HB": ["血红蛋白", "HGB", "Hb"],
    "ANC": ["中性粒细胞绝对值", "中性粒细胞计数", "NEUT#", "ANC"],
    "SCD25": ["可溶性CD25", "sCD25", "sIL-2R", "可溶性白介素2受体"],
    "TEMP": ["体温", "T"],
    "WBC": ["白细胞计数", "白细胞", "WBC"],
    "LYMPH": ["淋巴细胞绝对值", "LYMPH#"],
    "MONO": ["单核细胞绝对值", "MONO#"],
    "NEUT_PCT": ["中性粒细胞百分比", "NEUT%"],
    "LYMPH_PCT": ["淋巴细胞百分比", "LYMPH%"],
    "RBC": ["红细胞计数", "红细胞", "RBC"],
    "HCT": ["红细胞压积", "红细胞比容", "HCT"],
    "MCV": ["平均红细胞体积", "MCV"],
    "CRP": ["C反应蛋白", "C-反应蛋白", "CRP"],
    "HSCRP": ["超敏C反应蛋白", "hs-CRP", "hsCRP"],
    "ESR": ["红细胞沉降率", "血沉", "ESR"],
    "PCT_PROCALCITONIN": ["降钙素原", "PCT"],
    "IL6": ["白介素6", "白细胞介素6", "IL-6"],
    "GGT": ["γ-谷氨酰转移酶", "谷氨酰转肽酶", "GGT"],
    "ALP": ["碱性磷酸酶", "ALP"],
    "CK": ["肌酸激酶", "CK"],
    "TBIL": ["总胆红素", "TBIL", "TB"],
    "ALB": ["白蛋白", "ALB"],
    "CREA": ["肌酐", "CREA", "Cr"],
    "UREA": ["尿素", "尿素氮", "UREA", "BUN"],
    "GLU": ["葡萄糖", "血糖", "GLU"],
    "TC": ["总胆固醇", "TC", "CHOL"],
    "SODIUM": ["钠", "Na"],
    "POTASSIUM": ["钾", "K"],
    "DDIMER": ["D-二聚体", "D二聚体", "D-D"],
    "PT": ["凝血酶原时间", "PT"],
    "APTT": ["活化部分凝血活酶时间", "APTT"],
    "INR": ["国际标准化比值", "INR"],
    # 字典 0.3 补的常见套餐
    "EO": ["嗜酸性粒细胞绝对值", "嗜酸性粒细胞计数", "EO#"], "BASO": ["嗜碱性粒细胞绝对值", "嗜碱性粒细胞计数", "BASO#"],
    "MONO_PCT": ["单核细胞百分比", "MONO%"], "EO_PCT": ["嗜酸性粒细胞百分比", "EO%"],
    "BASO_PCT": ["嗜碱性粒细胞百分比", "BASO%"], "MCH": ["平均红细胞血红蛋白量", "平均血红蛋白量", "MCH"],
    "MCHC": ["平均红细胞血红蛋白浓度", "平均血红蛋白浓度", "MCHC"],
    "RDW_CV": ["红细胞分布宽度-CV", "红细胞体积分布宽度CV", "RDW-CV"],
    "RDW_SD": ["红细胞分布宽度-SD", "红细胞体积分布宽度SD", "RDW-SD"], "MPV": ["平均血小板体积", "血小板平均体积", "MPV"],
    "PDW": ["血小板分布宽度", "PDW"], "TP": ["总蛋白", "TP"], "GLB": ["球蛋白", "GLB", "GLO"],
    "AG_RATIO": ["白球比", "白蛋白/球蛋白", "A/G"], "DBIL": ["直接胆红素", "结合胆红素", "DBIL", "DB"],
    "IBIL": ["间接胆红素", "非结合胆红素", "IBIL", "IB"], "TBA": ["总胆汁酸", "TBA"], "PA": ["前白蛋白", "PA", "PAB"],
    "CHE": ["胆碱酯酶", "CHE"], "UA": ["尿酸", "UA", "URIC"], "CYSC": ["胱抑素C", "Cys-C", "CysC"],
    "EGFR": ["估算肾小球滤过率", "eGFR"], "CO2CP": ["二氧化碳结合力", "二氧化碳", "CO2CP", "CO2"],
    "CHLORIDE": ["氯", "Cl"], "CALCIUM": ["钙", "Ca"], "MAGNESIUM": ["镁", "Mg"], "PHOSPHORUS": ["无机磷", "磷", "P"],
    "HDL_C": ["高密度脂蛋白胆固醇", "高密度脂蛋白", "HDL-C", "HDL"],
    "LDL_C": ["低密度脂蛋白胆固醇", "低密度脂蛋白", "LDL-C", "LDL"],
    "APOA1": ["载脂蛋白A1", "ApoA1", "APOA1"], "APOB": ["载脂蛋白B", "ApoB", "APOB"],
    "HBA1C": ["糖化血红蛋白", "HbA1c"], "HBDH": ["α-羟丁酸脱氢酶", "羟丁酸脱氢酶", "HBDH", "α-HBDH"],
    "TT": ["凝血酶时间", "TT"], "FDP": ["纤维蛋白(原)降解产物", "纤维蛋白降解产物", "FDP"],
    "IGG": ["免疫球蛋白G", "IgG"], "IGA": ["免疫球蛋白A", "IgA"], "IGM": ["免疫球蛋白M", "IgM"],
    "C3": ["补体C3", "C3"], "C4": ["补体C4", "C4"], "ASO": ["抗链球菌溶血素O", "抗O", "ASO"],
    "RF": ["类风湿因子", "RF"], "SAA": ["血清淀粉样蛋白A", "SAA"], "SI": ["血清铁", "铁", "Fe"],
    "TRF": ["转铁蛋白", "TRF"], "TSH": ["促甲状腺激素", "促甲状腺素", "TSH"],
    "FT3": ["游离三碘甲状腺原氨酸", "游离T3", "FT3"], "FT4": ["游离甲状腺素", "游离T4", "FT4"],
    # 字典 0.4（生物年龄引擎）
    "SBP": ["收缩压", "高压", "SBP"], "DBP": ["舒张压", "低压", "DBP"], "WAIST": ["腰围", "WC"],
    "CORTISOL": ["皮质醇", "血清皮质醇", "Cortisol", "COR"],
}
# 各家医院的叫法（"中性细胞计数""百分率""血红蛋白浓度"……）
for _code, _names in {"ANC": ["中性细胞计数", "中性细胞绝对值", "中性粒细胞数目"], "LYMPH": ["淋巴细胞计数", "淋巴细胞数目"],
                      "MONO": ["单核细胞计数", "单核细胞数目"],
                      "NEUT_PCT": ["中性细胞百分率", "中性粒细胞百分率", "中性细胞百分比"], "LYMPH_PCT": ["淋巴细胞百分率", "淋巴细胞比例"],
                      "MONO_PCT": ["单核细胞百分率"], "EO_PCT": ["嗜酸性粒细胞百分率", "嗜酸细胞百分率"],
                      "BASO_PCT": ["嗜碱性粒细胞百分率", "嗜碱细胞百分率"], "HB": ["血红蛋白浓度", "血红蛋白量"],
                      "HCT": ["血细胞比容", "红细胞比积"], "MCV": ["红细胞平均体积"], "RDW_CV": ["红细胞分布宽度", "红细胞分布宽度变异系数"],
                      "HSCRP": ["超敏CRP", "超敏C-反应蛋白"], "CRP": ["全血CRP", "全血C反应蛋白"],
                      # R19：调优时在真实化验单上见到的写法
                      "WBC": ["白细胞数目"], "EO": ["嗜酸性粒细胞数目"], "BASO": ["嗜碱性粒细胞数目"], "RBC": ["红细胞数目"], "PLT": ["血小板数目"],
                      "MCH": ["平均红细胞血红蛋白含量", "平均血红蛋白含量"],
                      "RDW_SD": ["红细胞分布宽度标准差"], "AG_RATIO": ["白球比例"], "GGT": ["γ-谷氨酰基转移酶", "谷氨酰基转移酶", "γ-GT"],
                      "DDIMER": ["血浆D-二聚体"], "INR": ["凝血酶原国际标准化比值", "国际标准化比率"],
                      "APTT": ["活化部分凝血酶原时间"], "TC": ["CHO"]}.items():
    ALIASES.setdefault(_code, []).extend(_names)
# 字典 0.8：测试数据集化验单里出现、之前没收的指标（产品负责人 2026-10-14 07:01Z“测试集中出现的指标要求都归集”）
ALIASES.update({
    "PLATELETCRIT": ["血小板压积", "血小板比容", "血小板比积"], "P_LCR": ["大型血小板比率", "大血小板比率", "P-LCR"],
    "P_LCC": ["大型血小板数目", "大血小板数目", "P-LCC"], "RET_PCT": ["网织红细胞计数百分数", "网织红细胞百分比", "网织红细胞百分数", "RET%"],
    "CKMB": ["肌酸激酶同工酶", "肌酸激酶同工酶MB", "肌酸激酶-MB", "肌酸激酶-M", "CK-MB"], "ADA": ["腺苷脱氨酶", "ADA"],
    "LIPASE": ["脂肪酶", "LIP", "LPS"], "AMY": ["淀粉酶", "AMY"], "MYO": ["肌红蛋白", "MYO", "Mb"],
    "RBP": ["视黄醇结合蛋白", "RBP"], "BHB": ["β-羟丁酸", "β羟丁酸", "β-HB"],
    "VITD_25OH": ["25-羟基维生素D", "25羟基维生素D", "羟基维生素D", "25-OH-VD", "25(OH)D"],
    "IGE_TOTAL": ["总免疫球蛋白E", "总IgE", "IgE"], "LIPEMIA_IDX": ["血清脂浊指数", "脂浊指数"],
    "ICTERUS_IDX": ["血清黄疸指数", "黄疸指数"], "HEMOLYSIS_IDX": ["血清溶血指数", "溶血指数"],
    "PTA": ["凝血酶原活动度", "PT%", "PTA"], "PTR": ["凝血酶原比率", "PTR"], "AT3": ["抗凝血酶III", "抗凝血酶Ⅲ", "AT-III", "AT3"],
    "BG_PH": ["酸碱度", "pH"], "PCO2": ["二氧化碳分压", "pCO2"], "PO2": ["氧分压", "pO2"], "SO2": ["氧饱和度", "血氧饱和度", "sO2"],
    "HCO3": ["碳酸氢根", "实际碳酸氢根", "HCO3-", "HCO3"], "SBC": ["标准碳酸氢根", "SBC"], "ABE": ["实际碱剩余", "ABE"],
    "SBE": ["标准碱剩余", "SBE"], "ANION_GAP": ["阴离子间隙", "AG"], "METHB": ["高铁血红蛋白", "MetHb"],
    "COHB": ["碳氧血红蛋白", "COHb"], "ICA": ["离子钙", "钙(离子)", "iCa"], "LACTATE": ["乳酸", "Lac"],
    "NSE": ["神经元特异性烯醇化酶", "神经元特异烯醇化酶", "NSE"], "CA125": ["糖类抗原125", "CA125"],
    "CA199": ["糖类抗原199", "糖类抗原19-9", "CA199", "CA19-9"], "CEA": ["癌胚抗原", "CEA"], "AFP": ["甲胎蛋白", "AFP"],
    "HCG": ["人绒毛膜促性腺激素", "β-HCG", "HCG"],
    "ANTI_CCP": ["抗环瓜氨酸肽抗体", "抗环瓜酸肽抗体", "抗CCP抗体", "抗CCP", "CCP"], "ANTI_DSDNA": ["抗双链DNA抗体", "抗dsDNA抗体", "抗dsDNA"],
    "ACL_IGG": ["抗心磷脂抗体IgG", "抗心磷脂IgG", "ACL-IgG"], "ACL_IGM": ["抗心磷脂抗体IgM", "抗心磷脂IgM", "ACL-IgM"],
    "HLA_B27": ["HLA-B27", "人类白细胞抗原B27"],
    "IL1B": ["白介素1β", "IL-1β", "IL-1B", "IL-1"], "IL2": ["白介素2", "IL-2"], "IL4": ["白介素4", "IL-4"], "IL5": ["白介素5", "IL-5"],
    "IL8": ["白介素8", "IL-8"], "IL10": ["白介素10", "IL-10"], "IL12": ["白介素12", "IL-12", "IL-12P70"], "IL17": ["白介素17", "IL-17", "IL-17A"],
    "TNFA": ["肿瘤坏死因子α", "TNF-α", "TNF-a"], "IFNG": ["干扰素γ", "IFN-γ", "IFN-Y", "IFN-r"], "IFNA": ["干扰素α", "IFN-α", "IFN-a"],
    "CD3_PCT": ["CD3+T细胞百分比", "CD3+", "CD3"], "CD4_PCT": ["CD4+T细胞百分比", "CD3+CD4+", "CD4+", "CD4"],
    "CD8_PCT": ["CD8+T细胞百分比", "CD3+CD8+", "CD8+", "CD8"], "CD19_PCT": ["CD19+B细胞百分比", "CD19+", "CD19"],
    "NK_PCT": ["NK细胞百分比", "CD3-CD16+CD56+", "CD16+CD56+", "CD3-CD16+"], "CD4_CD8": ["CD4/CD8比值", "CD4/CD8", "Th/Ts"],
    "CD3_ABS": ["CD3+T细胞绝对计数", "CD3绝对计数", "CD3绝对计"], "CD4_ABS": ["CD4+T细胞绝对计数", "CD4绝对计数", "CD4绝对计"],
    "CD8_ABS": ["CD8+T细胞绝对计数", "CD8绝对计数", "CD8绝对计"], "CD19_ABS": ["CD19+B细胞绝对计数", "CD19绝对计数", "CD19绝对计"],
    "NK_ABS": ["NK细胞绝对计数", "CD56+绝对计数", "CD16+CD56+绝对计数"],
    "TP_AB": ["梅毒螺旋体特异性抗体", "梅毒螺旋体抗体", "抗-TP", "TP-Ab"], "HCV_AB": ["丙型肝炎病毒抗体", "抗-HCV", "HCV-Ab"],
    "HIV_AGAB": ["人类免疫缺陷病毒抗原抗体", "HIV抗原抗体", "HIV Ag/Ab"],
    "HBSAG_Q": ["乙型肝炎病毒表面抗原", "乙肝表面抗原", "HBsAg"], "HBSAB_Q": ["乙型肝炎病毒表面抗体", "乙肝表面抗体", "抗-HBs", "HBsAb"],
    "HBEAG_Q": ["乙型肝炎病毒e抗原", "乙肝e抗原", "HBeAg"], "HBEAB_Q": ["乙型肝炎病毒e抗体", "乙肝e抗体", "抗-HBe", "HBeAb"],
    "TOXO_IGM": ["弓形体抗体IgM", "弓形虫抗体IgM", "TOX-IgM"], "TOXO_IGG": ["弓形体抗体IgG", "弓形虫抗体IgG", "TOX-IgG"],
    "RUV_IGM": ["风疹病毒抗体IgM", "RV-IgM"], "RUV_IGG": ["风疹病毒抗体IgG", "RV-IgG"],
    "CMV_IGM": ["巨细胞病毒抗体IgM", "CMV-IgM"], "CMV_IGG": ["巨细胞病毒抗体IgG", "CMV-IgG"],
    "HSV1_IGM": ["单纯疱疹病毒I型抗体IgM", "单纯疱疹病毒1型抗体IgM", "HSV-1-IgM"], "HSV2_IGM": ["单纯疱疹病毒II型抗体IgM", "单纯疱疹病毒2型抗体IgM", "HSV-2-IgM"],
    "HSV1_IGG": ["单纯疱疹病毒I型抗体IgG", "单纯疱疹病毒1型抗体IgG", "HSV-1-IgG"], "HSV2_IGG": ["单纯疱疹病毒II型抗体IgG", "单纯疱疹病毒2型抗体IgG", "HSV-2-IgG"],
    "EBV_EA_IGM": ["EB病毒早期抗原抗体IgM", "EA-IgM"], "EBV_NA_IGG": ["EB病毒核抗原抗体IgG", "EB病毒核心抗原抗体IgG", "EBNA-IgG"],
    "EBV_VCA_IGG": ["EB病毒衣壳抗原抗体IgG", "VCA-IgG"], "EBV_VCA_IGM": ["EB病毒衣壳抗原抗体IgM", "VCA-IgM"],
    "MP_IGM": ["肺炎支原体抗体IgM", "MP-IgM"], "CP_IGM": ["肺炎衣原体抗体IgM", "CP-IgM"], "LP_AB": ["嗜肺军团菌抗体", "肺炎军团菌抗体", "LP-Ab"],
})
# 细胞因子套餐里单写“IL-1”的是 IL-1β（β 常读丢）；“IL-1α”“IL-10”不会被这条配上（名称后面紧跟字母数字的不算）
ALIASES["GGT"] += ["V-谷氨酰基转移酶", "V-GT"]  # 拍照把 γ 读成 V
ALIASES["ESR"] += ["红细胞沉降"]
# 参考范围（30-400、3.5~9.5、<1.7）与报告自己的高低标记（↑↓、H/L）
RANGE_RE = re.compile(r"(?<![\d.])(\d+(?:\.\d+)?)\s*[-~～—–]{1,2}\s*(\d+(?:\.\d+)?)(?![\d.])|^[<>≤≥＜＞〈〉]=?\s*\d+(?:\.\d+)?$")
ABN_RE = re.compile(r"[↑↓]|(?<![A-Za-z/])[HL](?![A-Za-z/])|偏高|偏低")

NUM_RE = re.compile(r"(?<![\d.])([<>≤≥＜＞〈〉]=?|<=|>=)?\s*(-?\d+(?:\.\d+)?)(?![\d.])")
CMP = {"<": "<", ">": ">", "≤": "<=", "≥": ">=", "＜": "<", "＞": ">", "〈": "<", "〉": ">", "<=": "<=", ">=": ">="}
DATE_RE = re.compile(r"(采样|[\u4e00-\u9fffA-Z]?集|留样|送检|接收|报告|检验|检测)?\s*(时间|日期)?\s*[:：]?\s*"
                     r"(\d{4})[-/.年](\d{1,2})[-/.月](\d{1,2})日?\s*(\d{1,2}:\d{2})?")


# ----------------------------------------------------------------------------- OCR

def vision_binary() -> Path:
    if sys.platform != "darwin":
        raise RuntimeError("OCR_UNSUPPORTED")  # 用的是 macOS 自带的 Vision，别的系统没有（先判断，免得用到别处编译好的旧程序）
    return vision_runtime.binary(SWIFT_SRC, BIN_DIR)


ORIGINAL_EXT = (".png", ".jpg", ".jpeg", ".heic", ".pdf", ".tif", ".tiff", ".webp")


def _run_vision(args, timeout):
    if vision_runtime.is_partner_request():
        return vision_runtime.verified_run(SWIFT_SRC, BIN_DIR, args, timeout)
    return subprocess.run([str(vision_binary()), *args], capture_output=True, timeout=timeout)


def preview_pdf(path: Path, page: int) -> bytes:
    """Render one original PDF page locally, without OCR or persistence."""
    if path.suffix.lower() != ".pdf" or not 1 <= page <= 100000:
        raise ValueError("ORIGINAL_PREVIEW_PAGE")
    try:
        result = _run_vision(["--preview", str(path), str(page)], 60)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("ORIGINAL_PREVIEW_UNAVAILABLE") from exc
    if result.returncode or not result.stdout.startswith(b"\x89PNG\r\n\x1a\n"):
        raise RuntimeError("ORIGINAL_PREVIEW_UNAVAILABLE")
    return result.stdout


def ocr(path: Path, page: int | None = None) -> dict:
    """page=None 读整份；page=N 只读 PDF 的第 N 页（大 PDF 一页一页读，不整份放进内存）。"""
    fake = None if vision_runtime.is_partner_request() else os.environ.get("PTDS_FAKE_OCR")  # 测试用：给一个 JSON 文件代替 Vision 输出（{"by_page": [...]} = 多页 PDF）
    if fake:
        doc = json.loads(Path(fake).read_text("utf-8"))
        return doc["by_page"][(page or 1) - 1] if "by_page" in doc else doc
    args = [str(path)] + (["--page", str(page)] if page else [])
    r = _run_vision(args, 180)
    if r.returncode != 0:
        raise RuntimeError("OCR_FAILED")
    return json.loads(r.stdout)


def pdf_pages(path: Path) -> int | None:
    """PDF 有几页。识别程序是旧版（不认 --count）时返回 None。"""
    fake = None if vision_runtime.is_partner_request() else os.environ.get("PTDS_FAKE_OCR")
    if fake:
        doc = json.loads(Path(fake).read_text("utf-8"))
        return len(doc["by_page"]) if "by_page" in doc else None
    try:
        r = _run_vision(["--count", str(path)], 120)
    except (OSError, subprocess.TimeoutExpired, RuntimeError):
        return None
    out = r.stdout.decode("utf-8", "replace").strip()
    return int(out) if r.returncode == 0 and out.isdigit() else None


HEADER_NAMES = {"项目名称", "项目", "检验项目", "检测项目", "中文名称", "名称", "检验名称", "项目中文名称", "检验项目名称", "序号指标", "指标", "指标名称"}
CJK_NAME = re.compile(r"^[\u4e00-\u9fff][\u4e00-\u9fff（(]")
NOT_NAME = {"偏高", "偏低", "结果", "单位", "参考区间", "参考范围", "参考值", "提示", "阳性", "阴性"}


def _rows(segs: list) -> list:
    segs = sorted(segs, key=lambda i: i["y"] + i["h"] / 2)
    rows, current = [], []
    for s in segs:
        cy = s["y"] + s["h"] / 2
        if current:
            ref = sum(c["y"] + c["h"] / 2 for c in current) / len(current)
            tol = max(min(c["h"] for c in current + [s]) * 0.6, 0.004)
            if abs(cy - ref) > tol:
                rows.append(sorted(current, key=lambda c: c["x"]))
                current = []
        current.append(s)
    if current:
        rows.append(sorted(current, key=lambda c: c["x"]))
    return rows


def panel_bounds(segs: list) -> list:
    """一页并排两栏（左右各一张表）时找出分栏位置：表头"项目名称"在同一行出现两次；
    没有表头时，看是否有多行在同一横向位置又起了一个新的指标名（前面已经有数值）。"""
    for row in _rows(segs):
        heads = [s["x"] for s in row if s["text"].replace(" ", "") in HEADER_NAMES]
        if len(heads) >= 2:
            # 表头有时居中，右栏的指标名比表头靠左：分栏线挪到表头下面、左边最近的一列指标名（至少 3 个对齐）前面
            top = min(s["y"] for s in row)
            cuts = []
            for h, prev in zip(sorted(heads)[1:], sorted(heads)):
                xs = sorted(s["x"] for s in segs if s["y"] > top and h - 0.12 < s["x"] <= h + 0.005 and s["x"] > prev + 0.1
                            and CJK_NAME.match(SEQ_RE.sub("", s["text"].strip())) and s["text"].strip() not in NOT_NAME)
                col = max(([x for x in xs if a <= x <= a + 0.02] for a in xs), key=len, default=[])
                cuts.append(min(min(col), h) - 0.005 if len(col) >= 3 else h)
            return cuts
    second = []
    for row in _rows(segs):
        seen_num = False
        for s in row[1:]:
            t = s["text"].strip()
            name = CJK_NAME.match(SEQ_RE.sub("", t)) and t not in NOT_NAME
            if seen_num and name:
                second.append(s["x"])
                break
            if NUM_RE.search(t) and not name:
                seen_num = True
    if len(second) >= 3:
        second.sort()
        mid = second[len(second) // 2]
        near = [x for x in second if abs(x - mid) <= 0.06]
        if len(near) >= 3:
            return [min(near) - 0.005]
    return []


def skew(segs: list) -> float:
    """手机斜拍时整张表是歪的：每段文字找它右边最近、纵向接近的一段，算两者中心连线的斜率，取中位数。"""
    out = []
    its = sorted(segs, key=lambda i: i["x"])
    for a in its:
        ca, ra, best = a["y"] + a["h"] / 2, a["x"] + a["w"], None
        for b in its:
            if b is a or b["x"] < ra - 0.002:
                continue
            cb = b["y"] + b["h"] / 2
            if abs(cb - ca) < max(a["h"], b["h"]) * 0.9:
                dx = (b["x"] + b["w"] / 2) - (a["x"] + a["w"] / 2)
                if dx > 0.05 and (best is None or dx < best[0]):
                    best = (dx, (cb - ca) / dx)
        if best:
            out.append(best[1])
    out.sort()
    return out[len(out) // 2] if len(out) >= 8 else 0.0


def deskew(segs: list) -> list:
    """斜率明显（>0.8%）就把每段的纵向位置按横向位置拉平，再分行；算两轮，第二轮补上第一轮漏配的。只改分行用的坐标，原文和原始框不动。"""
    total, cur = 0.0, segs
    for _ in range(2):
        s = skew(cur)
        if abs(s) < 0.008:
            break
        total += s
        cur = [dict(i, y=i["y"] - total * (i["x"] + i["w"] / 2 - 0.5), _raw=i.get("_raw", i)) for i in segs]
    return cur


SEQ_RE = re.compile(r"^\d{1,2}\s*(?=[\u4e00-\u9fffA-Za-zα-ωβγ])")


def strip_seq(segs: list) -> list:
    """表格最左边的序号（“7”“15 平均红细胞体积”）不是名称的一部分：去掉，名称才能对上字典。原文（text）不动。"""
    segs = list(segs)
    if len(segs) > 1 and re.fullmatch(r"\d{1,2}", segs[0].strip()):
        segs = segs[1:]
    if segs:
        segs[0] = SEQ_RE.sub("", segs[0].strip())
    return segs



def _column_layout(row, previous, known_names):
    """Use the named headers on this panel and page. A partial new header resets it."""
    from evidence_navigation import OCR_COLUMN_ROLES
    def role(segment):
        label = "".join(segment["text"].lower().split())
        return "name" if label in HEADER_NAMES else OCR_COLUMN_ROLES.get(label)
    roles = [role(segment) for segment in row]
    if not any(roles):
        # A heading need not contain any of our header words. Carry forward
        # a layout only across a positively identified metric in its name cell.
        name_cells = _column_cells(row, previous).get("name", [])
        name = norm_name(" ".join(name_cells))
        if not name or name not in known_names:
            return None
        return previous
    # A header-like word by itself can also be a section boundary. No old
    # column coordinates may leak into the following section.
    if any(roles.count(key) != 1 for key in ("name", "result", "unit")):
        return None
    centers = [seg["x"] + seg["w"] / 2 for seg in row]
    if any(a >= b for a, b in zip(centers, centers[1:])):
        return None
    edges = [0.0] + [(a + b) / 2 for a, b in zip(centers, centers[1:])] + [1.0]
    return [(key, left, right) for key, left, right in zip(roles, edges, edges[1:])]


def _column_cells(row, layout):
    cells = {}
    for key, left, right in layout or ():
        if not key:
            continue
        within = []
        for seg in row:
            x, end = seg["x"], seg["x"] + seg["w"]
            if end <= left or x >= right:
                continue
            if x < left or end > right or seg["conf"] < 0.3:
                within = []
                break
            within.append(seg["text"].strip())
        cells[key] = within
    return cells


def _partner_result(line, definition):
    """Only a single complete result in the result cell, with its own unit."""
    cells = line.get("cells", {})
    values, units = cells.get("result", []), cells.get("unit", [])
    if not cells.get("name") or len(units) != 1:
        return None
    if len(values) == 2 and values[0] in CMP:
        value_text = " ".join(values)
    elif len(values) == 1:
        value_text = values[0]
    else:
        return None
    from evidence_navigation import OCR_RESULT_LITERAL
    match = OCR_RESULT_LITERAL.fullmatch(value_text)
    if match is None:
        return None
    comparator = CMP.get(match.group(1), "")
    literals = [unit for unit, _ in definition.units]
    unit = units[0]  # Unit prefixes and case carry meaning; keep the literal from the unit cell.
    if unit not in literals or (comparator and not definition.comparators_allowed):
        return None
    flag = ABN_RE.fullmatch(" ".join(cells.get("flag", [])))
    abn = {"↑":"H", "↓":"L", "偏高":"H", "偏低":"L"}.get(flag[0], flag[0]) if flag else ""
    return {"value": match.group(2), "cmp": comparator, "unit": unit,
            "flag": None, "ref_range": " ".join(cells.get("reference", [])), "abn": abn}


def group_lines(items: list, known_names=frozenset()) -> list:
    """Vision 给的是一段段文字；按页、按栏、按行（框的纵向中心接近）拼成表格行，行内按横向排序。
    并排两栏的报告先分栏，左栏读完再读右栏，免得左右两项拼成一行。"""
    lines = []
    for page in sorted({i["page"] for i in items}):
        raw = [i for i in items if i["page"] == page]
        cuts = [0.0] + panel_bounds(deskew(raw)) + [9.0]
        for a, b in zip(cuts, cuts[1:]):
            part = deskew([s for s in raw if a <= s["x"] < b])  # 每栏单独拉平：照片有透视，左右两栏歪的程度不一样
            layout = None
            for row in _rows(part):
                if vision_runtime.is_partner_request():
                    layout = _column_layout(row, layout, known_names)
                lines.append((page, row, _column_cells(row, layout) if layout else {}))
    out = []
    for n, (page, segs, cells) in enumerate(lines, start=1):
        segs.sort(key=lambda s: s["x"])
        out.append({"n": n, "page": page, "segments": strip_seq([s["text"] for s in segs]),
                    "text": "\t".join(s["text"] for s in segs),
                    "conf": min(s["conf"] for s in segs),
                    "box": [min(s["x"] for s in segs), min(s.get("_raw", s)["y"] for s in segs),
                            max(s["x"] + s["w"] for s in segs), max(s.get("_raw", s)["y"] + s["h"] for s in segs)]})
        if vision_runtime.is_partner_request():
            out[-1]["cells"] = cells
    return out


# ----------------------------------------------------------------------------- 本机千问

class LocalLLM:
    def __init__(self, config: dict):
        self.cfg = config or {}
        self.port = int(self.cfg.get("port", 8786))
        self.base = f"http://127.0.0.1:{self.port}"
        self.proc = None
        self.model_name = Path(self.cfg.get("model", "")).name or "未配置"

    def healthy(self) -> bool:
        try:
            with urllib.request.urlopen(self.base + "/health", timeout=2) as r:
                return r.status == 200
        except OSError:
            return False

    def ensure(self) -> bool:
        if self.healthy():
            return True
        model = self.cfg.get("model")
        binary = shutil.which(self.cfg.get("server", "llama-server")) or self.cfg.get("server")
        if not model or not Path(model).exists() or not binary or not Path(binary).exists():
            return False
        if self.proc is None or self.proc.poll() is not None:
            log = open(Path(self.cfg.get("log", "~/.ptds/llama-server.log")).expanduser(), "ab")
            self.proc = subprocess.Popen([binary, "-m", model, "--host", "127.0.0.1", "--port", str(self.port),
                                          "-c", str(self.cfg.get("ctx", 8192)), "-ngl", "99", "--jinja"],
                                         stdout=log, stderr=log)
        for _ in range(int(self.cfg.get("start_timeout", 120))):
            if self.healthy():
                return True
            time.sleep(1)
        return False

    def chat(self, system: str, user: str) -> str:
        body = {"messages": [{"role": "system", "content": system}, {"role": "user", "content": user + " /no_think"}],
                "temperature": 0, "max_tokens": 1500, "response_format": {"type": "json_object"},
                "chat_template_kwargs": {"enable_thinking": False}}
        req = urllib.request.Request(self.base + "/v1/chat/completions", data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=180) as r:
            msg = json.loads(r.read())["choices"][0]["message"]["content"]
        return re.sub(r"<think>.*?</think>", "", msg, flags=re.S).strip()


UNITISH = re.compile(r"/|^%$|^[a-zA-Zμµ]{1,4}$|^\d+(\.\d+)?$|^[<>≤≥＜＞]")
CONT = re.compile(r"^[\w\u4e00-\u9fff\-－（(]{0,10}[）)]$|^[\u4e00-\u9fff]{1,8}[（(][\w\-]{0,6}$")
FRAG = re.compile(r"^[\u4e00-\u9fff（(][\u4e00-\u9fffA-Za-z0-9（）()\-]{0,9}$|^[A-Za-z]{1,2}$")
LABEL_ONLY = re.compile(r"^(被检者|患者)[：:]$")  # “被检者：”这一行有数值，指标名写在下面几行
ARROWS = re.compile(r"^[↑↓]+$")
UNIT_END = re.compile(r"^\d{0,2}/[Ll]$|^[Ll]$")  # 折到下一行的单位尾巴：“L”“2/L”
UNIT_CUT = re.compile(r"(/|10\^?\d?)$")         # 被折断的单位：“×10^9/”“x10^1”


def _attach_unit(prev: dict, tail: str) -> bool:
    """把折到下一行的单位尾巴接回上一行被折断的单位上。"""
    for k, seg in enumerate(prev["rest"]):
        toks = seg.split()
        for j, t in enumerate(toks):
            if not NUM_RE.fullmatch(t) and UNIT_CUT.search(t) and re.search(r"[A-Za-z×]|10", t):
                toks[j] = t + tail
                prev["rest"][k] = " ".join(toks)
                return True
    return False


def prep(lines: list, known: frozenset = frozenset()) -> list:
    """每行分出“名称”和“其余各栏”。手机长截图里名称常常折行（“铁蛋白(Ferr” 下一行 “i)”；“嗜酸性粒细” 下一行 “胞绝对值”），
    单位也会折行（“×10^9/” 下一行 “L”），高低箭头有时单独占一行：
    - 第一段按空白切开，名称后面像单位或数字的部分挪到“其余各栏”；
    - 紧跟在有数值的行后面、左边对齐的名称碎片，拼回上一行的名称；单独的箭头、单位尾巴，接回上一行；这些碎片行自己不再单独算一行。
    上一行名称以“：”或括号结尾的，说明名称是完整的，不拼；碎片本身就是一个完整指标名（如小标题“白细胞”）的，也不拼。"""
    prev = None
    for l in lines:
        segs = l["segments"]
        l["cont"] = False
        if prev is not None:
            whole = "".join(segs).replace(" ", "")
            first = segs[0].replace(" ", "") if segs else ""
            others = [x.replace(" ", "") for x in segs[1:]]
            near = l["box"][1] - prev["_y1"] < 2.5 * max(prev["_h"], 0.002)
            lined_up = -0.02 < l["box"][0] - prev["box"][0] < 0.10  # 左对齐或居中，都在名称栏里
            open_name = not re.search(r"[：:)）]$", prev["name"]) or LABEL_ONLY.match(prev["name"])
            if len(segs) == 1 and CONT.match(first):
                prev["name"] += first
            elif ARROWS.match(whole):
                prev["rest"].append(whole)
            elif len(segs) == 1 and UNIT_END.match(first) and _attach_unit(prev, first):
                pass
            elif (FRAG.match(first) and near and lined_up and open_name and norm_name(first) not in known
                  and all(ARROWS.match(x) or UNIT_END.match(x) or re.fullmatch(r"[A-Za-z]{1,4}", x) for x in others)):
                prev["name"] += first
                for x in others:
                    if ARROWS.match(x):
                        prev["rest"].append(x)
                    elif not _attach_unit(prev, x):
                        prev["rest"].append(x)
            else:
                prev = None
            if prev is not None:
                l["cont"] = True
                prev["_y1"] = l["box"][3]
                continue
        toks = segs[0].split() if segs else []
        name, extra = [], []
        for t in toks:
            if extra or (name and UNITISH.search(t) and not t.startswith(("（", "("))):
                extra.append(t)
            else:
                name.append(t)
        l["name"] = "".join(name)
        l["rest"] = ([" ".join(extra)] if extra else []) + segs[1:]
        if NUM_RE.search("\t".join(l["rest"])):
            prev = l
            l["_y1"], l["_h"] = l["box"][3], l["box"][3] - l["box"][1]
    for l in lines:
        l.pop("_y1", None)
        l.pop("_h", None)
    return lines


def llm_map(llm: LocalLLM, lines: list, codes: dict) -> dict:
    catalog = "\n".join(f"{c}: {d.label_zh}" + (f"（{'、'.join(ALIASES[c])}）" if c in ALIASES else "")
                        for c, d in codes.items())
    numbered = "\n".join(f"{l['n']}. {l['name']}\t" + "\t".join(l["rest"]) for l in lines if not l.get("cont"))
    system = ("你只做一件事：判断化验单的每一行是哪个检验指标。只能从给定的指标代码里选；"
              "拿不准就不选。不要输出数值，不要解释。输出 JSON：{\"map\":[{\"line\":行号,\"code\":\"代码\"}]}")
    user = f"指标代码表：\n{catalog}\n\n化验单文字（每行一个编号）：\n{numbered}"
    raw = llm.chat(system, user)
    m = re.search(r"\{.*\}", raw, re.S)
    doc = json.loads(m.group(0)) if m else {}
    out = {}
    for item in doc.get("map", []) if isinstance(doc, dict) else []:
        if isinstance(item, dict) and isinstance(item.get("line"), int) and item.get("code") in codes:
            out[item["line"]] = item["code"]
    return out


# 拍照、截图里常见的繁体或形近字，只用于“对名称”，不改原文
VARIANT = str.maketrans({"細": "细", "紅": "红", "飑": "胞", "檢": "检", "驗": "验", "測": "测", "鐵": "铁", "纖": "纤",
                         "維": "维", "時": "时", "間": "间", "總": "总", "膽": "胆", "單": "单", "數": "数", "計": "计",
                         "絕": "绝", "濃": "浓", "積": "积", "寬": "宽", "鹼": "碱", "氫": "氢", "轉": "转", "門": "门",
                         "國": "国", "際": "际", "標": "标", "準": "准", "値": "值",
                         "究": "宽", "自": "白", "氣": "氯", "減": "碱",
                         "（": "(", "）": ")", "－": "-", "—": "-"})
MARK_RE = re.compile(r"^[\s•·*＊※★☆▲△▼▽#]+|^(被检者|患者)[：:]|^[hn]uman(?=[A-Z])")
TAG_RE = re.compile(r"\((?:\d|[\u4e00-\u9fff])?-?HR\)")  # 互认标记“(9-HR)”“(陕HR)”
TAIL_WORDS = re.compile(r"(定量检测|定量测定|测定|检测|定量)(?=\(|$)")
ABBR_RE = re.compile(r"\(([A-Za-z][A-Za-z0-9\-#%]{1,8})\)")


def norm_name(s: str) -> str:
    """对名称用：去空格、去开头的“*”“•”这类互认标记、繁体和形近字换成简体、全角括号换成半角。"""
    s = TAG_RE.sub("", MARK_RE.sub("", s.replace(" ", "").translate(VARIANT)))
    s = re.sub(r"^[Yy]-", "γ-", s)  # Vision 常把 γ 读成 Y
    s = re.sub(r"[l1]g([GMAE])$", r"Ig\1", s)  # 抗体名末尾的 IgG / IgM 常被读成 lgG、1gM
    return TAIL_WORDS.sub("", s)


ELEMENT_TAIL = re.compile(r"\([A-Za-z]{1,2}\)|[A-Za-z]{1,2}[+\-]?")  # “钾(K)”“钠Na+”；“钙(离子)”是离子钙，不算总钙


def shares_zh(zh: str, code: str, codes: dict) -> bool:
    """缩写有歧义（“血小板压积(PCT)”不是降钙素原）：括号前的中文至少要和这个指标的某个中文名有一个字相同；括号前没有中文才只看缩写。"""
    got = set(re.findall(r"[\u4e00-\u9fff]", zh))
    if not got:
        return True
    return any(got & set(norm_name(n)) for n in [codes[code].label_zh] + ALIASES.get(code, []))


def own_tail(tail: str, code: str, codes: dict) -> bool:
    """名称后面紧跟的是这个指标自己的英文缩写（“氧分压pO2”“碳氧血红蛋白COHb”），或缩写的头几个字母连着单位
    （“钙(离子)Cmmol/L”“碳酸氢根HCmmol/L”，单位折进了名称栏）：仍算这个指标。"""
    abbrs = [a for a in ALIASES.get(code, []) if re.fullmatch(r"[A-Za-z][A-Za-z0-9+\-]{1,8}", a)]
    if any(tail.lower() == a.lower() for a in abbrs):
        return True
    for u, _ in codes[code].units:
        if len(u) >= 3 and tail.endswith(u):
            pre = tail[:-len(u)]
            return len(pre) <= 3 and pre.isascii() and (pre.isalpha() or not pre)
    return False


def alias_map(lines: list, codes: dict) -> dict:
    """名称对字典：去空格后以某个名称开头、且后面紧跟的不是字母数字或“-”（免得“肌酸激酶-MB”当成“肌酸激酶”）；取最长的那个名称。
    中文名读走样时（拍照常见），再看名称里括号中的英文缩写，例如“乳酸股気梅(LD)”里的 LD；缩写至少两个字母，整段相同才算。"""
    names = sorted(((norm_name(n), code) for code in codes
                    for n in [codes[code].label_zh] + ALIASES.get(code, []) if n), key=lambda x: -len(x[0]))
    abbr = {}
    for n, code in names:
        if re.fullmatch(r"[A-Za-z][A-Za-z0-9\-#%]{1,8}", n):
            abbr.setdefault(n.upper(), code)
    out = {}
    for l in lines:
        if l.get("cont"):
            continue
        head = norm_name(l["name"])
        for n, code in names:
            nxt = head[len(n):len(n) + 1]
            if head == n or (len(n) >= 2 and head.startswith(n) and not nxt.isalnum() and nxt not in "-") or \
                    (len(n) == 1 and head.startswith(n) and ELEMENT_TAIL.fullmatch(head[1:])) or \
                    (len(n) >= 2 and head.startswith(n) and own_tail(head[len(n):], code, codes)):
                out[l["n"]] = code
                break
        else:
            m = ABBR_RE.search(head)
            code = abbr.get(m.group(1).upper()) if m else None
            if code and shares_zh(head[:m.start()], code, codes):
                out[l["n"]] = code
    return out


def llm_check(lines: list, mapping: dict, codes: dict) -> tuple:
    """千问配的指标再按程序规则核一遍（R19 千问版评估，产品负责人 2026-10-14）：
    - 这一行的中文名和这个指标的任何一个中文名一个字都不沾（“血小板压积(PCT)”配成降钙素原）→ 不采用；
    - 单字的元素名（钾、钠、钙……）后面跟的不是元素符号（“钙(离子)”是离子钙）→ 不采用。
    不采用的行改看同义词对照，对不上就留在“没有对上”里。返回 (采用的, 不采用的行数)。"""
    syn = alias_map(lines, codes)
    by_n = {l["n"]: l for l in lines}
    out, dropped = {}, 0
    for n, code in mapping.items():
        l = by_n.get(n)
        if l is None:
            continue
        head = norm_name(l["name"])
        m = ABBR_RE.search(head)
        zh = head[:m.start()] if m else head
        single = min((len(norm_name(x)) for x in [codes[code].label_zh] + ALIASES.get(code, []) if x and re.search(r"[\u4e00-\u9fff]", x)), default=9) == 1
        if not shares_zh(zh, code, codes) or (single and syn.get(n) != code):
            dropped += 1
            if syn.get(n):
                out[n] = syn[n]
            continue
        out[n] = code
    return out, dropped


# ----------------------------------------------------------------------------- 取原文值

CARET_RE = re.compile(r"^[×xX]?10[\s7１1'’‘`ˆ^*]?(9|12)/[Ll]$")
UNIT_SEEN = {"秒": "s", "m/h": "mm/h", "mm/1h": "mm/h"}  # 报告上的写法 → 字典写法；只在字典里有右边这个写法时才生效（见 norm_unit）
UNIT_TAIL = re.compile(r"%|[A-Za-zμµ]{1,4}/[A-Za-z]{1,3}")
POWER_RE = re.compile(r"^([×xX*]?)\s*10\s*[\^ˆ'’`*~]?\s*(\d{1,2})\s*/\s*([Ll]|[uμµ][Ll])$")


def norm_unit(tok: str, literals: list) -> str:
    """把识别走样的单位写法对回字典里的写法：10'9/L、10ˆ9/L → 10^9/L；FL → fL。对不上就原样返回。"""
    t = tok.replace("（", "(").replace("）", ")").replace("％", "%").replace(" ", "").rstrip(".。,，、")
    t = re.sub(r"(?<=[A-Za-z])1(?=/|$)", "l", t)  # mmo1/L、f1：字母后面的 1 是 l
    t = UNIT_SEEN.get(t, t)
    if t in literals:
        return t
    m = CARET_RE.match(t)  # 拍照时 "^" 常被读成 7、1、' 或空白：10 9/L、1079/L、1019/L
    if m:
        t = "10^%s/L" % m.group(1)
    m = POWER_RE.match(t)
    if m:
        for cand in ("10^%s/%s" % (m.group(2), m.group(3)), "×10^%s/%s" % (m.group(2), m.group(3))):
            if cand in literals:
                return cand
    low = {}
    for u in literals:
        low.setdefault(u.lower(), u)
    if t.lower() in low:
        return low[t.lower()]
    # 希腊字母 μ 常被读成 M、W、u、µ：只有字典里没有同名的 mmol/L 这类写法时才换成 μ（例如胆红素只收 μmol/L）
    m = re.match(r"^[MWwuµμ](mol|g)/[Ll]$", t)
    if m:
        for cand in ("μ%s/L" % m.group(1), "µ%s/L" % m.group(1), "u%s/L" % m.group(1)):
            if cand in literals:
                return cand
    near = [u for u in literals if len(u) >= 3 and one_edit(t, u)]
    return near[0] if len(near) == 1 else tok


PREFIX = set("mμµunpkMWH")


def one_edit(a: str, b: str) -> bool:
    """a 和 b 只差一个字（换、多、少一个），而且差的那个字不是 m、μ、n 这类数量级前缀：
    “9/L”“B/L” → g/L、“UIL” → U/L 可以；“mol/L” 补成 mmol/L 还是 μmol/L 猜不了，不补。"""
    if a == b or abs(len(a) - len(b)) > 1:
        return False
    i = 0
    while i < min(len(a), len(b)) and a[i] == b[i]:
        i += 1
    if len(a) == len(b):
        ok = a[i + 1:] == b[i + 1:]
        diff = {a[i], b[i]}
    else:
        s_, l_ = (a, b) if len(a) < len(b) else (b, a)
        ok = s_[i:] == l_[i + 1:]
        diff = {l_[i]}
    return ok and not diff & PREFIX


def unit_like(tok: str, literals: list) -> bool:
    if NUM_RE.fullmatch(tok) or RANGE_RE.search(tok):
        return False
    if re.match(r"^[×xX*]?10\s*[\^ˆ'’‘`*~]?\s*\d", tok):
        return True
    return bool(re.search(r"[A-Za-zμµ%]", tok)) and ("/" in tok or norm_unit(tok, literals) in literals)


def extract(line: dict, cdef) -> dict:
    """从这一行原文里取数值、比较符、单位。数值是第一个出现在名称之后的数字；单位逐字比对字典。"""
    if "rest" in line:  # prep() 已经分好名称和其余各栏
        rest = list(line["rest"])
    else:
        segs = line["segments"]
        if len(segs) > 1:
            rest = segs[1:]
        else:  # 整行一段：名称到第一个空白为止（名称里可能有数字，如"白介素6"）
            parts = segs[0].split(None, 1) if segs else []
            rest = [parts[1]] if len(parts) > 1 else []
    # 参考范围单独拿出来，不能被当成结果值（结果栏空着时尤其要防）
    ref_range, kept = None, []
    for k, seg in enumerate(rest):
        piece = seg.strip()
        rm = RANGE_RE.search(piece)
        if rm and not rm.group(1):  # "<1.7" 只有在最后一栏、前面已有结果值时才算参考范围，否则是"<5"这样的结果
            earlier = [t for t in rest[:k] if NUM_RE.search(t) and not (RANGE_RE.search(t.strip()) or [None, None])[1]]
            if k != len(rest) - 1 or not earlier:
                rm = None
        if rm and (rm.group(0) == piece or len(rest) == 1 or UNIT_TAIL.fullmatch(piece[rm.end():].strip())):
            ref_range = ref_range or rm.group(0)
            piece = (piece[:rm.start()] + piece[rm.end():]).strip()
        if piece:
            kept.append(piece)
    rest = kept
    am = ABN_RE.search("\t".join(rest))
    abn = {"↑": "H", "偏高": "H", "H": "H", "↓": "L", "偏低": "L", "L": "L"}.get(am.group(0)) if am else None
    literals = sorted((u for u, _ in cdef.units), key=len, reverse=True)
    # 单位栏在结果栏前面时（手机截图常见），“×10^9/L”“9/L” 里的数字不能当成结果
    text = "\t".join(" ".join(t for t in seg.split() if not unit_like(t, literals)) for seg in rest)
    value, cmp_, flag = None, None, None
    m = NUM_RE.search(text)
    if m:
        value, cmp_ = m.group(2), CMP.get((m.group(1) or "").strip()) or None
    else:
        flag = "UNREADABLE"
    unit = None
    rest = [norm_unit(seg.strip(), literals) for seg in rest]
    for seg in rest:
        s = seg.strip()
        if s in literals:
            unit = s
            break
    tokens = [norm_unit(tok, literals) for s in rest for tok in s.split()]
    if unit is None:
        unit = next((tok for tok in tokens if tok in literals), None)
    if unit is None:
        cand = [tok for tok in tokens if not NUM_RE.fullmatch(tok) and not RANGE_RE.search(tok)
                and not ABN_RE.fullmatch(tok)]
        unit = cand[0] if cand else None
        if flag is None:
            flag = "UNIT_NOT_IN_DICT"
    if value is not None and line["conf"] < 0.3 and flag is None:
        flag = "UNREADABLE"
    if cmp_ and not cdef.comparators_allowed:
        flag = flag or "UNREADABLE"
    return {"value": value or "", "cmp": cmp_ or "", "unit": unit or "", "flag": flag, "ref_range": ref_range or "",
            "abn": abn or ""}


def find_datetime(lines: list):
    best = None
    for l in lines:
        m = DATE_RE.search(l["text"].replace("\t", " "))
        if not m:
            continue
        y, mo, d, hm = m.group(3), int(m.group(4)), int(m.group(5)), m.group(6)
        rank = 0 if (m.group(1) or "").endswith("集") else {"采样": 0, "留样": 0, "送检": 1, "接收": 2, "检验": 3, "检测": 3, "报告": 4}.get(m.group(1), 5)
        cand = (rank, f"{y}-{mo:02d}-{d:02d}", (hm.zfill(5) if hm else ""), l["n"])
        if best is None or cand < best:
            best = cand
    return best


# ----------------------------------------------------------------------------- 识别后的白话总结

BANNED = ("诊断", "确诊", "患有", "考虑为", "提示可能", "可能是", "建议", "治疗", "服用", "用药", "就医", "复查")


def rule_summary(rows: list, codes: dict, unmatched: list, when) -> str:
    hi = [codes[r["code"]].label_zh for r in rows if r.get("abn") == "H"]
    lo = [codes[r["code"]].label_zh for r in rows if r.get("abn") == "L"]
    parts = [f"这份化验单{('采样于 ' + when[1] + (' ' + when[2] if when[2] else '') + '，') if when else ''}"
             f"识别出 {len(rows)} 项指标"]
    if hi:
        parts.append("报告标注偏高的有" + "、".join(hi))
    if lo:
        parts.append("标注偏低的有" + "、".join(lo))
    if rows and not hi and not lo:
        parts.append("识别出的项目里报告没有标注偏高或偏低")
    if unmatched:
        parts.append(f"另有 {len(unmatched)} 行没对上字典，不会保存")
    return "，".join(parts) + "。"


def llm_summary(llm: LocalLLM, lines: list) -> str:
    text = "\n".join(l["text"].replace("\t", " ") for l in lines)
    system = ("你只复述化验单上已经写着的内容，给本人一个白话概览：这是什么检查、什么时候采样、报告自己用箭头或 H/L 标出的"
              "偏高偏低项目。不得做诊断，不得推测原因，不得给建议，不得出现原文里没有的数字。"
              "不超过 120 字。输出 JSON：{\"summary\":\"……\"}")
    raw = llm.chat(system, "化验单原文：\n" + text)
    m = re.search(r"\{.*\}", raw, re.S)
    doc = json.loads(m.group(0)) if m else {}
    return str(doc.get("summary", "")).strip() if isinstance(doc, dict) else ""


def check_summary(summary: str, lines: list) -> str | None:
    """不合格返回原因：出现原文没有的数字，或诊断、建议类说法。"""
    if not summary:
        return "EMPTY"
    source = " ".join(l["text"] for l in lines)
    norm = lambda n: repr(float(n))  # noqa: E731 — "01" 与 "1"、"2.30" 与 "2.3" 算同一个数
    nums = {norm(n) for n in re.findall(r"\d+(?:\.\d+)?", source)}
    if any(norm(n) not in nums for n in re.findall(r"\d+(?:\.\d+)?", summary)):
        return "NUMBER_NOT_IN_SOURCE"
    if any(w in summary for w in BANNED):
        return "INTERPRETATION"
    return None


def summarize(llm: LocalLLM | None, lines: list, rows: list, codes: dict, unmatched: list, when) -> dict:
    facts = rule_summary(rows, codes, unmatched, when)
    out = {"text": facts, "by": "规则（只按报告自己的标记）", "facts": facts, "rejected": None}
    if llm is not None and llm.healthy():
        try:
            text = llm_summary(llm, lines)
            why = check_summary(text, lines)
            if why is None:
                out.update(text=text, by=_sign(llm))
            else:
                out["rejected"] = why  # 千问写的不合格就不用，退回规则版，并如实标注
        except Exception:  # noqa: BLE001
            out["rejected"] = "LLM_ERROR"
    return out


def recognize_file(path: Path, file_sha: str, registry, llm: LocalLLM | None) -> dict:
    return parse(ocr(path), file_sha, registry, llm)


GENE_WORDS = re.compile(r"基因|外显子|测序|杂合|纯合|染色体|突变位点|转录本")
RECORD_WORDS = re.compile(r"出院记录|入院记录|出院小结|病程记录|现病史|既往史|主诉|入院情况|出院诊断|诊疗经过")
NOTICE = {
    "gene": "这像是一份基因检测报告，不是化验单。基因报告不在这里逐项识别，也不做解读。",
    "record": "这像是病历正文（出院记录、病程这类），不是化验单的表格。正文里的化验数值这一版不逐项识别，请对照原件手工录入。",
    "prose": "这张图不像单张化验单的表格（可能是成段的文字，或一张表里有好几个日期）。这一版不逐项识别，请对照原件手工录入。",
}


def kind_of(lines: list, matched: int) -> str:
    """程序按规则判断是不是化验单（不用模型）：有表头、或认出 3 项以上的，都按化验单处理。"""
    head = any(seg.replace(" ", "") in HEADER_NAMES for l in lines for seg in l["segments"])
    text = "\n".join(l["text"] for l in lines)
    genes = len(set(GENE_WORDS.findall(text)))
    if genes >= 3 or (genes >= 2 and matched <= 2):
        return "gene"
    if head or matched >= 3:
        return "lab"
    if RECORD_WORDS.search(text):
        return "record"
    if len(lines) >= 8 and sum(len(l["text"]) > 25 for l in lines) >= 0.6 * len(lines):
        return "prose"
    return "lab"


def parse(raw: dict, file_sha: str, registry, llm: LocalLLM | None, with_summary: bool = True) -> dict:
    """Vision 原始结果 → 待确认的识别结果。评估工具（tools/ocr_eval.py）也走这一条，保证评的就是线上的代码。"""
    codes = {c: d for c, d in registry.current.codes.items() if d.family in ENTRY_FAMILIES}
    names = frozenset(norm_name(n) for c in codes for n in [codes[c].label_zh] + ALIASES.get(c, []) if n)
    lines = prep(group_lines(raw.get("items", []), names | {norm_name(c) for c in codes}), names)
    if vision_runtime.is_partner_request():
        for line in lines:
            line["name"] = " ".join(strip_seq(line.get("cells", {}).get("name", [])))
    model, mapping, tried = "", {}, False
    kind = kind_of(lines, len(set(alias_map(lines, codes).values())))  # 先用同义词粗看一遍，不是化验单就不去问千问
    work = lines if kind == "lab" else []  # 不是化验单：不硬配指标，照实说
    if llm is not None and work and llm.ensure():
        tried = True
        try:
            mapping, dropped = llm_check(work, llm_map(llm, work, codes), codes)
            model = _sign(llm) + (f"（{dropped} 行千问配的指标没通过程序核对，没有采用）" if dropped else "")
        except Exception:  # noqa: BLE001 — 千问出错就退到同义词，并如实标注
            mapping = {}
    if not mapping:
        mapping = alias_map(work, codes)
        model = "同义词对照" + ("（千问未给结果）" if tried else "（千问不可用）")
    if kind != "lab":
        model = "程序按规则判断：不是化验单"
    rows, used, unmatched = [], set(), []
    # 同一个指标对上了好几行时（“白细胞”小标题和“白细胞计数”），用第一个有数值的那一行
    per_line = vision_runtime.is_partner_request()
    best = {}
    for l in (() if per_line else work):
        c = mapping.get(l["n"])
        if c and (c not in best or (not best[c][1] and NUM_RE.search("\t".join(l.get("rest") or [])))):
            best[c] = (l["n"], bool(NUM_RE.search("\t".join(l.get("rest") or []))))
    for l in work:
        code = mapping.get(l["n"])
        if code and not per_line and best[code][0] != l["n"]:
            code = None
        if code and (per_line or code not in used):
            used.add(code)
            got = _partner_result(l, codes[code]) if per_line else extract(l, codes[code])
            if per_line and (not got or not l.get("box")):
                unmatched.append(l["text"].replace("\t", "　"))
                continue
            rows.append({"code": code, "value": got["value"], "unit": got["unit"], "cmp": got["cmp"],
                         "flag": got["flag"], "ok": False, "text": l["segments"][0] if l["segments"] else l["text"],
                         "ref_range": got["ref_range"], "abn": got["abn"],
                         "line": l["n"], "page": l["page"], "box": l["box"],
                         "ref": f"OCR:{file_sha[:16]}#p{l['page']}l{l['n']}"})
        elif not l.get("cont") and NUM_RE.search(l["text"]) and not DATE_RE.search(l["text"]):
            unmatched.append(l["text"].replace("\t", "　"))
    when = find_datetime(lines)
    summary = summarize(llm, lines, rows, codes, unmatched, when) if with_summary and kind == "lab" else None
    return {"summary": summary, "source_lines": [l["text"] for l in lines], "engine": {"ocr": raw.get("engine", "macOS Vision"), "model": model, "version": "ptds-local-0.1",
                       "local": True},
            "date": when[1] if when else "", "time": when[2] if when else "", "timeOk": False,
            "time_line": when[3] if when else None, "rows": rows, "unmatched": unmatched,
            "kind": kind, "notice": NOTICE.get(kind, ""),
            "lines": len(lines), "pages": raw.get("pages", 1)}


def _sign(llm) -> str:
    """署名（产品负责人 2026-10-14）：星灵（Qwen 3.5 9B本地）发出。"""
    import starling_page  # noqa: PLC0415
    return starling_page.sign(llm)
