"""Local extractive state summary: server-resolved selections, model-ranked facts.
No raw measurements or client prose goes to the model. No clinical advice generation.
"""
import json
import re
from decimal import Decimal, InvalidOperation
import hashlib
import compete_ai
import starling_page

TITLES = {'state': '当前状态', 'change': '主要变化', 'limit': '数据限制'}
SYSTEM = ('你是本地星灵。只对给出的结构化事实做摘要选取与排序，不诊断、不建议、不添加解释。'
          '每类选1至4条最能概括当前画面的事实；空类返回空数组。输出JSON：'
          '{"state":["F1"],"change":["F2"],"limit":["F3"]}。只能使用本类事实编号。')


def readable_state(text):
    return str(text).replace('缺数据算不了', '数据不足，暂无法计算').replace('算不了', '暂无法计算').replace(' · 建议补检', '')


def numeric_detail(ind, x, y, direction):
    if x.get('bool') or y.get('bool'):
        return ind['label'] + '由' + ('有' if x['value'] == 'true' else '未见') + '变为' + ('有' if y['value'] == 'true' else '未见')
    unit = y.get('unit') or x.get('unit') or ''
    detail = f"{ind['label']}由 {x.get('comparator') or ''}{x['value']} {x.get('unit') or unit} 变为 {y.get('comparator') or ''}{y['value']} {unit}"
    if x.get('unit') != y.get('unit'):
        return detail + '（单位不同，不计算增减）'
    if direction not in ('升高', '降低', '数值未变'):
        return detail + '（' + direction + '）'
    try:
        a, z = Decimal(str(x['value'])), Decimal(str(y['value']))
        if not a.is_finite() or not z.is_finite(): return detail + '（数值无法比较）'
        fmt = lambda n: format(n.quantize(Decimal('0.01')), 'f').rstrip('0').rstrip('.') if n else '0'
        delta = z-a
        detail += '，' + ('增加' if delta>0 else '减少' if delta<0 else '变化') + ' ' + fmt(abs(delta)) + (' '+unit if unit else '')
        detail += '（' + (fmt(abs(delta/a)*100)+'%' if a else '基线为0，不计算比例') + '）'
    except InvalidOperation:
        detail += '（数值无法比较）'
    return detail


def context(b, rows):
    if not b.get('found') or not isinstance(rows, list) or not 1 <= len(rows) <= 32:
        raise ValueError('BASELINE_SELECTION_INVALID')
    facts = []
    def add(group, text, refs, **meta):
        if not any(f['text'] == text and f['group'] == group for f in facts):
            facts.append(dict(id='F'+str(len(facts)+1), group=group, text=text, refs=refs, **meta))
    dates = set()
    for row in rows:
        field = row['field']
        if row['kind'] == 'm':
            r = next(x for x in b['main'] if x['key'] == field)
            picks = []
            for side in ('base', 'dev'):
                p = row[side]
                o = next(x for x in r['options'] if x['tp'] == p['tp'] and x.get('run_id') == p.get('run_id'))
                picks.append(o); dates.add(o['tp'])
            a, z = picks
            refs = [dict(rule=r['rule'], tp=x['tp'], run_id=x.get('run_id')) for x in picks]
            # Scores are left in the table; model receives only labels and state changes.
            def label(o):
                return readable_state('已有评分结果' if o.get('num') is not None else o['text'])
            add('state', f"{r['label']}：基线 {a['tp']}「{label(a)}」；发展 {z['tp']}「{label(z)}」。", refs, label=r["label"], current=label(z), current_unknown=any(w in label(z) for w in ("缺", "算不了", "无法", "—")))
            if any(any(w in label(o) for w in ('缺', '算不了', '无法', '—')) for o in picks):
                add('limit', f"{r['label']}的所选结果含数据不足或无法判定，不能当作未出现。", refs)
        elif row['kind'] == 'c':
            group, _, code = field.partition(':')
            r = next(x for x in b['clues'] + b.get('catalogue', []) if x['id'] == group)
            sides = []
            for side in ('base', 'dev'):
                requests = row[side]
                if not isinstance(requests, list) or len(requests) > 2:
                    raise ValueError('BASELINE_SELECTION_INVALID')
                found = {}
                for req in requests:
                    if code and req['code'] != code:
                        raise ValueError('BASELINE_SELECTION_INVALID')
                    ind = next(i for i in r['indicators'] if i['code'] == req['code'])
                    rec = next(v for v in ind['records'] if v['ref'] == req['ref'])
                    found[ind['code']] = (ind, rec); dates.add(rec['tp'])
                sides.append(found)
            a, z = sides
            if not a or not z:
                add('limit', r['label']+'：所选侧没有记录。', [])
            if a.keys() != z.keys():
                add('limit', r['label']+'：两侧指标不同，只能对共同指标描述变化。', [])
            for c in a:
                if c not in z:
                    continue
                ind, x = a[c]; _, y = z[c]
                refs = [dict(code=c, ref=v['ref'], tp=v['tp']) for v in (x,y)]
                if x['ref'] == y['ref']:
                    direction = '两侧是同一条记录，不能判断变化'
                elif x.get('comparator') or y.get('comparator'):
                    direction = '含范围值，不计算精确偏移'
                elif x.get('bool'):
                    direction = '记录未变' if x['value'] == y['value'] else '记录发生变化'
                else:
                    try:
                        av, zv = Decimal(str(x['value'])), Decimal(str(y['value']))
                        if not av.is_finite() or not zv.is_finite(): raise InvalidOperation
                        direction = '升高' if zv > av else '降低' if zv < av else '数值未变'
                    except InvalidOperation:
                        direction = '数值无法比较'
                if y['tp'] < x['tp']:
                    direction += '；发展日期早于基线，不代表向后的时间趋势'
                add('change', f"{ind['label']}：{x['tp']} → {y['tp']}，{direction}。", refs, label=ind["label"], direction=direction, detail=numeric_detail(ind, x, y, direction))
        else:
            raise ValueError('BASELINE_SELECTION_INVALID')
    if len(dates) > 2:
        add('limit', '各行使用的日期不同，不是一组统一起止日期的比较。', [])
    add('limit', '仅总结当前选择；没有覆盖未显示的指标，不作诊断或治疗建议。', [])
    return facts



def compact_summary(facts, sections):
    """Three short, server-grounded points. Full facts remain available as evidence."""
    states = [f for f in facts if f['group'] == 'state']
    unknown = sum(bool(f.get('current_unknown')) for f in states)
    if not states:
        state = '本次未选择可概括的主状态。'
    elif unknown:
        state = f'当前选中 {len(states)} 项状态，{unknown} 项因数据不足暂无法判断。'
    else:
        named = [f.get('label', '状态') + '：' + f.get('current', '已有结果') for f in states[:2]]
        state = '；'.join(named) + (f'；其余 {len(states)-2} 项见表格。' if len(states)>2 else '。')
    # Model ordering prioritizes actual changes; unchanged facts never displace them.
    ranked = [f for sec in sections if sec['title'] == TITLES['change'] for f in sec['items']]
    changes = ranked + [f for f in facts if f['group'] == 'change' and f not in ranked]
    buckets = {'升高': [], '降低': [], '未变': [], '发生变化': [], '无法比较': []}
    for f in changes:
        d = f.get('direction', '')
        kind = ('无法比较' if any(x in d for x in ('不能判断', '范围值', '无法比较', '早于'))
                else '升高' if d == '升高' else '降低' if d == '降低'
                else '未变' if '未变' in d else '发生变化' if d == '记录发生变化' else '无法比较')
        label = f.get('label', '所选指标')
        if label not in buckets[kind]: buckets[kind].append(label)
    phrases = []
    for kind in ('升高', '降低', '未变', '发生变化', '无法比较'):
        labels = buckets[kind]
        if not labels: continue
        if kind in ('升高','降低'):
            names = '、'.join(labels[:2]) + (f'等 {len(labels)} 项' if len(labels)>2 else '')
            phrases.append(names + kind)
        else:
            phrases.append(f'{len(labels)} 项' + ('记录未变' if kind == '未变' else '记录发生变化' if kind == '发生变化' else '暂不能比较'))
    details = [f['detail'] for f in changes if f.get('detail') and f.get('direction') not in ('记录未变', '数值未变')]
    change = '；'.join(details) + '。' if details else ('；'.join(phrases) + '。' if phrases else '当前没有可比较的指标记录。')
    if details and buckets['未变']: change += f"另有 {len(buckets['未变'])} 项记录未变。"
    if states:
        state += '其中，' + '；'.join(f.get('label','状态') + '：' + f.get('current','未知') for f in states) + '。'
    texts = [f['text'] for f in facts]
    limits = []
    for needle, message in [('数据不足或无法判定',f'{unknown} 项当前状态数据不足或无法判定'), ('各行使用的日期不同','各指标比较日期不同'),
                            ('两侧指标不同','两侧指标未完全对应'), ('所选侧没有记录','部分记录缺失'),
                            ('两侧是同一条记录','同一记录不能判断变化'), ('含范围值','范围值不能精确比较'),
                            ('发展日期早于基线','部分日期顺序相反'), ('数值无法比较','部分数值无法比较')]:
        if any(needle in t for t in texts): limits.append(message)
    limit = '；'.join(limits[:2]) + ('等限制；' if len(limits)>2 else '；' if limits else '') + '仅概括当前选择，不作诊断。'
    return [dict(title=TITLES[g], text=t) for g,t in zip(TITLES,(state,change,limit))]

def summarize(llm, facts):
    fp = hashlib.sha256(json.dumps(facts, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    if llm is None or not llm.cfg.get('model'):
        return dict(state='no_llm', fp=fp)
    if not compete_ai.LOCK.acquire(blocking=False):
        return dict(state='error', why='本地星灵正忙，请稍后重试', fp=fp)
    try:
        if not llm.ensure(): return dict(state='no_llm', fp=fp)
        prompt = json.dumps([{k:f[k] for k in ('id','group','text')} for f in facts], ensure_ascii=False)
        for attempt in range(2):
            raw = llm.chat(SYSTEM, prompt)
            try:
                match = re.search(r'\{.*\}', raw, re.S)
                doc = json.loads(match.group())
                sections = []
                for group, title in TITLES.items():
                    ids = doc[group]
                    available = {f['id']: f for f in facts if f['group'] == group}
                    if not isinstance(ids,list) or len(ids)>4 or (available and not ids) or len(set(ids))!=len(ids): raise ValueError
                    items = [available[i] for i in ids]
                    # Scope and mixed-date caveats must survive model selection.
                    if group == 'limit':
                        for f in available.values():
                            if not f['refs'] and f not in items:
                                items.append(f)
                    sections.append(dict(title=title, items=items))
                return dict(state='ok', summary_contract='three-points/1', brief=compact_summary(facts, sections), sections=sections, by=starling_page.sign(llm), fp=fp,
                            method='本地模型选取与排序；表述及依据来自当前结构化事实')
            except (ValueError, KeyError, TypeError, AttributeError):
                if attempt == 0:
                    allowed = {g: [f['id'] for f in facts if f['group'] == g] for g in TITLES}
                    prompt += '\n上次输出未通过格式核对。请只返回三个数组，每类最多4个编号。各类允许编号：' + json.dumps(allowed)
                continue
        return dict(state='rejected', why='模型返回的事实编号或分类未通过核对', fp=fp)
    except Exception:
        return dict(state='error', why='本地模型调用失败', fp=fp)
    finally:
        compete_ai.LOCK.release()
