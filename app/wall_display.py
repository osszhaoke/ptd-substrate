"""Card presentation preferences. Never modifies observations, rules or device bindings."""
import json


def catalogue(snap):
    out = {}
    for x in (snap.get('vitals') or {}).get('items', []):
        family = x.get('family')
        if family in ('DEVICE_GARMIN', 'DEVICE_OURA', 'DEVICE_SOMALOOP', 'DEVICE_QKEER', 'PHONE_HEALTH'):
            out.setdefault('card:VITALS:' + family, []).append(x['code'])
    for g in (snap.get('engines') or {}).get('groups', []):
        out['grp:' + g['id']] = (['summary'] if g['id'] == 'MAS' else []) + [c['rule'] for c in g['cards']]
    for c in snap.get('custom_cards') or []:
        out['cc:' + c['card_id']] = ['summary']
    band = snap.get('band_cards') or {}
    if band.get('spot') is not None:
        out['band:LIVE.SOMALOOP-SPOT'] = [x['label'] for x in band['spot']]
        out['band:LIVE.SPO2-LOW'] = ['summary']
        out['band:SLEEP.A03-HRV-DEV-SOMALOOP'] = [x['label'] for x in band.get('night', [])]
    if (snap.get('sleep') or {}).get('metrics'):
        out['sleep'] = [x['code'] for x in snap['sleep']['metrics']]
    for c in snap.get('instance', {}).get('cards', []):
        out.setdefault('card:' + c, ['summary'])
    return {k: list(dict.fromkeys(v)) for k, v in out.items()}


def load(conn):
    out = {}
    for card, value in conn.execute("SELECT card_id,value FROM card_setting WHERE key='wall_display' ORDER BY id"):
        value = json.loads(value)
        if value is None:
            out.pop(card, None)
        else:
            out[card] = value
    return out


def validate(card, value, snap):
    choices = catalogue(snap)
    if card not in choices:
        raise ValueError('这张卡片已不可用，请关闭后重新打开')
    if value is None:
        return None
    if not isinstance(value, dict) or set(value) != {'name', 'items'}:
        raise ValueError('卡片设置格式不正确')
    name, items = value['name'], value['items']
    if not isinstance(name, str) or not 1 <= len(name.strip()) <= 40:
        raise ValueError('请填写1至40字的卡片名称')
    if not isinstance(items, list) or not 1 <= len(items) <= 100 or not all(isinstance(x, str) for x in items) or len(set(items)) != len(items):
        raise ValueError('请至少选择一项，且不要重复选择')
    prior = ((snap.get('wall_prefs') or {}).get('display') or {}).get(card, {}).get('items', [])
    if any(x not in choices[card] and x not in prior for x in items):
        raise ValueError('展示项不属于这张卡，请重新打开编辑')
    return {'name': name.strip(), 'items': list(items)}
