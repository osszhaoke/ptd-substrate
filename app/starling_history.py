"""Deterministic saved-record queries. No model calls or clinical values."""
from collections import Counter
from datetime import datetime, timedelta, time
import json
import re
from zoneinfo import ZoneInfo

DATE = re.compile(r'(?:(\d{4})[-/年.])?(\d{1,2})[-/月.](\d{1,2})日?')
RELATIVE = {'今天': 0, '昨天': 1, '昨日': 1, '前天': 2}


def intent(question):
    if not re.search(r'录入|导入|新增|保存|存入|收到了|接收了', question):
        return None
    if re.search(r'为什么|为何|怎么|如何|方式|流程|失败|来源|功能|设置', question):
        return None
    # Specific filters need their own interpretation; never silently ignore them.
    days = [word for word in RELATIVE if word in question]
    dates = list(DATE.finditer(question))
    week = bool(re.search(r'(最近|近|过去)\s*(7|七)\s*天', question))
    if len(days) + len(dates) + int(week) > 1:
        return {'kind': 'history', 'period': 'ambiguous'}
    if days:
        return {'kind': 'history', 'period': 'day', 'offset': RELATIVE[days[0]]}
    if dates:
        return {'kind': 'history', 'period': 'date', 'date': dates[0].groups()}
    if week:
        return {'kind': 'history', 'period': 'week'}
    return {'kind': 'history', 'period': 'missing'}


def window(plan, now, tz):
    zone = ZoneInfo(tz)
    current = datetime.fromisoformat(now) if isinstance(now, str) else now
    if current is None:
        current = datetime.now(zone)
    if current.tzinfo is None:
        raise ValueError('Current time must include timezone')
    today = current.astimezone(zone).date()
    if plan['period'] == 'day':
        first = today - timedelta(days=plan['offset'])
        last = first + timedelta(days=1)
    elif plan['period'] == 'week':
        first, last = today - timedelta(days=6), today + timedelta(days=1)
    elif plan['period'] == 'date':
        year, month, day = plan['date']
        first = today.replace(year=int(year or today.year), month=int(month), day=int(day))
        last = first + timedelta(days=1)
    else:
        raise ValueError('Date required')
    return datetime.combine(first, time.min, zone), datetime.combine(last, time.min, zone)


def selected(instant, start, end):
    parsed = datetime.fromisoformat(instant)
    if parsed.tzinfo is None:
        raise ValueError('Saved time has no timezone')
    return start <= parsed < end


def read(inst, start, end, labels):
    """Only formal-save metadata; the caller chooses exactly one instance."""
    from startorch_outbox import open_startorch
    from sqlite_util import assert_inside
    from muse_sessions import Store
    if not inst.ctx.startorch_db.is_file():
        raise ValueError('Formal store missing; do not create it for a read')
    conn = open_startorch(inst.ctx)
    groups = Counter()
    try:
        # UTC-aware comparison, not lexical ordering of offset-bearing strings.
        for revision, code, status, saved in conn.execute(
                "SELECT revision,json_extract(payload,'$.code'),json_extract(payload,'$.status'),saved_at "
                "FROM formal_observation WHERE julianday(saved_at)>=julianday(?) "
                "AND julianday(saved_at)<julianday(?)", (start.isoformat(), end.isoformat())):
            if not selected(saved, start, end):
                continue
            action = '撤回' if status == 'RETRACTED' else '新增' if revision == 1 else '更正'
            groups[(labels.get(code, code), action)] += 1
        if conn.execute('SELECT count(*) FROM formal_observation WHERE julianday(saved_at) IS NULL').fetchone()[0]:
            raise ValueError('Unusable formal save timestamps')
    finally:
        conn.close()
    genes, seen = 0, set()
    ledger = inst.ctx.root / 'startorch' / 'gene' / 'receipts.jsonl'
    assert_inside(inst.ctx.root, ledger)
    if ledger.exists():
        with ledger.open(encoding='utf-8') as handle:
            for line in handle:
                if not line.strip():
                    continue
                receipt = json.loads(line)
                if receipt['outcome'] != 'STORED' or receipt['sha256'] in seen:
                    continue
                seen.add(receipt['sha256'])
                genes += int(selected(receipt['received_at'], start, end))
    muse = 0
    if (inst.ctx.root / 'startorch' / 'muse' / 'requests').exists():
        muse = sum(selected(receipt['saved_at'], start, end) for receipt in Store(inst).list())
    return {'groups': groups, 'genes': genes, 'muse': muse}


def answer(plan, now, tz, query):
    if plan['period'] in ('missing', 'ambiguous'):
        return {'answer': '请明确一个时间范围，例如“昨天录入了哪些数据”或“最近7天导入了什么”。',
                'why': '需要明确查询日期', 'query_status': 'NEEDS_DATE'}
    try:
        start, end = window(plan, now, tz)
    except (ValueError, TypeError):
        return {'answer': '这个日期无法识别，请使用有效日期，例如“2026-10-14录入了什么”。',
                'why': '日期无效', 'query_status': 'INVALID_DATE'}
    try:
        if query is None:
            raise RuntimeError('Save-time query is unavailable')
        data = query(start, end)
        groups = data['groups']
        totals = Counter()
        for (_, action), count in groups.items():
            totals[action] += count
        period = start.date().isoformat()
        final_day = (end - timedelta(days=1)).date().isoformat()
        if final_day != period:
            period += ' 至 ' + final_day
        head = f'按实际保存时间查询 {period}（{tz}，含补录）：'
        if not sum(totals.values()) and not data['genes'] and not data['muse']:
            return {'answer': head + '当前库没有新增、更正或撤回的正式指标数据，也没有新保存的基因文件或Muse会话。',
                    'query_status': 'EMPTY', 'why': ''}
        counts = '、'.join(f'{action}{totals[action]}条' for action in ('新增', '更正', '撤回'))
        details = '；'.join(f'{label}：{action}{count}条' for (label, action), count in sorted(groups.items())[:10])
        text = head + '指标数据' + counts + f'；基因文件{data["genes"]}份；Muse会话{data["muse"]}段。'
        if details:
            text += details + ('；仅列前10项。' if len(groups) > 10 else '。')
        return {'answer': text, 'query_status': 'FOUND', 'why': ''}
    except Exception:
        return {'answer': '这次未能完成保存记录查询，不能判断有没有录入数据。请稍后重试。',
                'why': '保存记录查询失败', 'query_status': 'FAILED'}
