"""Immutable program statements for compete/retro; no storage, locks or inference."""
from dataclasses import dataclass, asdict
import json

VERSION = 'program-statements/1'


@dataclass(frozen=True)
class Claim:
    ref: str
    role: str
    text: str
    cols: tuple = ()
    selection: str = ''
    action_id: str = ''


def compile_catalog(c):
    out = []
    def add(role, text, cols=(), selection='', action_id=''):
        if isinstance(text, str) and text.strip():
            out.append(Claim('F' + str(len(out) + 1), role, text.strip(), tuple(cols), selection, action_id))
    for entry in c.get('explain') or []:
        add('sentences', entry['text'], entry.get('cols') or ())
    for text in (c.get('stability') or {}).get('text') or []:
        add('summary', text)
    nx = c.get('next') or {}
    for i, action in enumerate(nx.get('actions') or []):
        add('next', action['text'], action.get('cols') or (), 'A' + str(i + 1), action['id'])
    questions = list(nx.get('ask') or [])
    for action in nx.get('actions') or []:
        questions.extend(action.get('ask') or [])
    for text in dict.fromkeys(questions):
        add('ask', text)
    return tuple(out)


def material(catalog):
    return json.dumps([VERSION, [asdict(c) for c in catalog]], ensure_ascii=False,
                      sort_keys=True, separators=(',', ':'))


def select(catalog, doc):
    """Validate every item before rendering any output. Unknown data is never dropped."""
    if not isinstance(doc, dict) or set(doc) - {'sentences', 'summary', 'next', 'ask'}:
        raise ValueError('format')
    refs = {c.ref: c for c in catalog}
    actions = {c.selection: c for c in catalog if c.role == 'next'}
    questions = {c.text: c for c in catalog if c.role == 'ask'}
    selected = {}
    for role in ('sentences', 'summary', 'next', 'ask'):
        values = doc.get(role, [])
        if not isinstance(values, list):
            raise ValueError('format')
        if role == 'sentences' and len(values) < 3 or role == 'summary' and len(values) > 2 or role in ('next', 'ask') and len(values) > 3:
            raise ValueError('format')
        chosen = []
        for v in values:
            if role in ('sentences', 'summary'):
                if not isinstance(v, dict) or set(v) != {'text', 'facts'} or not isinstance(v['text'], str):
                    raise ValueError('format')
                rr = v['facts']
                if not isinstance(rr, list) or len(rr) != 1 or not isinstance(rr[0], str):
                    raise ValueError('format')
                c = refs.get(rr[0])
                if c is None or c.role != role or v['text'].strip() != c.text:
                    raise ValueError('format')
            elif role == 'next':
                if not isinstance(v, dict) or set(v) != {'id', 'why'} or not isinstance(v['id'], str) or not isinstance(v['why'], str):
                    raise ValueError('format')
                c = actions.get(v['id'])
                if c is None or v['why'].strip() != c.text:
                    raise ValueError('format')
            else:
                if not isinstance(v, str) or v.strip() not in questions:
                    raise ValueError('format')
                c = questions[v.strip()]
            if c in chosen:
                raise ValueError('format')
            chosen.append(c)
        selected[role] = tuple(chosen)
    return selected


def render(selected):
    return {'sentences': [{'text': c.text, 'cols': list(c.cols)} for c in selected['sentences']],
            'summary': [{'text': c.text} for c in selected['summary']],
            'next': [{'id': c.action_id, 'why': c.text} for c in selected['next']],
            'ask': [c.text for c in selected['ask']]}
