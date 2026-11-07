// Collect rendered text and accessible labels, including HTML outside the current view.
function scanEnglishScreen(doc) {
  const scope = doc.documentElement;
  const cjk = /\p{Script=Han}/u;
  const hits = [], elements = [scope, ...scope.querySelectorAll('*')];
  function collect(el, field, value) {
    if (!value || !cjk.test(value)) return;
    const parent = el.closest('[id]');
    hits.push({field, value:value.trim(), tag:el.localName, id:el.id, parent:parent?.id || '',
      classes:el.getAttribute('class') || '', selector: el.closest('[data-kg]')?.getAttribute('data-kg') || ''});
  }
  for (const el of elements) {
    if (el.closest('script,style,template,[hidden]') || el.getClientRects().length === 0) continue;
    const css = doc.defaultView.getComputedStyle(el);
    if (css.visibility !== 'visible' || css.display === 'none') continue;
    for (const name of ['aria-label','title','placeholder']) collect(el,name,el.getAttribute(name));
    for (const n of el.childNodes) if (n.nodeType === 3) collect(el,'text',n.nodeValue);
  }
  return hits;
}
