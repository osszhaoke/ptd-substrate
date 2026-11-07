/* One owner for the language preference, toolbar menu and bounded UI bindings. */
(function (root) {
  'use strict';
  var doc = root.document, resources = root.PTDS_LANGUAGE_RESOURCES, key = 'ptds-language';
  var language = 'zh', context = null, wrapper = null, menu = null, observer = null, roots = [];
  var remembered = new WeakMap(), attributes = new WeakMap(), listening = false;
  var startup = root.PTDS_FIRST_LANGUAGE, mode = null;
  try { mode = root.localStorage.getItem(key); } catch (_) { /* Optional local preference. */ }
  if (mode !== 'en' && mode !== 'zh' && !(startup && mode === 'system')) mode = null;
  function effective() { return startup && (!mode || mode === 'system') ? startup.systemLanguage() : (mode || 'zh'); }
  language = effective();
  var globe = '<svg class="ic" aria-hidden="true" focusable="false" width="1em" height="1em" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><ellipse cx="12" cy="12" rx="4" ry="9"/><path d="M3 12h18M5 6.5h14M5 17.5h14"/></svg>';
  var css = '#language-control{position:relative;display:inline-flex;flex:none}#language-menu{position:absolute;right:0;top:calc(100% + 8px);min-width:166px;padding:6px;border:1px solid var(--theme-line-control);border-radius:12px;background:var(--theme-surface-raised);color:var(--theme-text-primary);box-shadow:0 8px 24px #0002;z-index:2300}#language-menu[hidden]{display:none}#language-menu button{display:flex;align-items:center;justify-content:space-between;gap:24px;width:100%;padding:10px 12px;border:0;border-radius:8px;background:transparent;color:inherit;font:inherit;white-space:nowrap;cursor:pointer}#language-menu button:hover,#language-menu button:focus-visible{background:var(--component-sidebar-selBg)}#language-menu button[aria-checked="true"]{font-weight:600}#language-toggle:focus-visible{outline:2px solid var(--theme-text-primary);outline-offset:3px}html[lang="en"] #side .xmod .mn,html[lang="en"] #side .xmod .ms{overflow-wrap:anywhere}html[lang="en"] #side .xmod{grid-template-columns:auto minmax(0,1fr)}html[lang="en"] #side .xmod .ms{grid-column:2}html[lang="en"] #side .xtile{padding:6px;font-size:13px}html[lang="en"] #side .bname{font-size:13px}';
  function text(id, fallback) { var r = resources.messages[id]; return r ? (r[language] || r.zh) : fallback; }
  function translate(value, allowed) {
    if (language !== 'en') return value;
    var match = /^(\s*)([\s\S]*?)(\s*)$/.exec(value), id = allowed ? allowed.find(function(id){ return resources.matchesSource(id, match[2]); }) : resources.byChinese[match[2]];
    return id ? match[1] + text(id, match[2]) + match[3] : value;
  }
  function node(n, format, allowed) {
    if (n.nodeType !== 3) return;
    var old = remembered.get(n), current = n.nodeValue;
    if (!old || current !== old.last) old = {source:current, last:current};
    var formatted = language === 'en' && typeof format === 'function' ? format(old.source) : null;
    // Several fixed grammars can share a control; a nonmatching rule must leave its sibling's translation alone.
    if (language === 'en' && formatted === null && allowed && !allowed.some(id=>resources.matchesSource(id,old.source.trim()))) return;
    var next = formatted === null ? translate(old.source, allowed) : formatted; if (next !== current) n.nodeValue = next;
    old.last = next; remembered.set(n, old);
  }
  function label(el, format, allowed) {
    for(var p=el;p && p.nodeType===1;p=p.parentNode) if(p.hasAttribute('contenteditable') && p.getAttribute('contenteditable') !== 'false') return;
    if (el) Array.prototype.forEach.call(el.childNodes, function(n){ node(n, format, allowed); });
  }
  function attr(el, name, allowed, format) {
    if (!el || !el.hasAttribute(name)) return;
    var map = attributes.get(el) || {}, old = map[name], current = el.getAttribute(name);
    if (!old || current !== old.last) old = {source:current, last:current};
    var next = language === 'en' && format ? format(old.source) : null;
    if (next == null) next = translate(old.source, allowed);
    if (language === 'en' && el.id === 'inst' && name === 'aria-label') {
      const suffixes = [['，演示 · 合成数据。打开实例选择',', synthetic demo data. Back to home'],['，我的真实数据。打开实例选择',', personal data. Back to home'],['，回放合成读数。打开实例选择',', replayed synthetic readings. Back to home']];
      for (const [zh,en] of suffixes) if (old.source.endsWith(zh)) { next=old.source.slice(0,-zh.length)+en;break; }
    }
    if (language === 'en' && el.id === 'bell' && /^状态通知，\d+ 条未读$/.test(old.source)) next = 'Notifications, ' + old.source.match(/\d+/)[0] + ' unread';
    if (next !== current) el.setAttribute(name, next);
    old.last = next; map[name] = old; attributes.set(el, map);
  }
  function labels(rootNode, selector) { if (rootNode) rootNode.querySelectorAll(selector).forEach(function(el){ label(el); }); }
  let disclaimerSource;
  function setDisclaimer(source) {
    disclaimerSource = source;
    const footer = doc.getElementById('disc');
    if (!footer) return;
    const value = language === 'en' ? text('launch_disclaimer', source) : source;
    if (footer.textContent !== value) footer.textContent = value;
  }
  function apply(options) {
    options = options || {view:true, chromeText:true};
    doc.documentElement.lang = language === 'en' ? 'en' : 'zh-CN';
    var side = doc.getElementById('side'), bar = doc.getElementById('appbar');
    if(options.chromeText){
    // Explicit UI nodes only. Never scan data rows, inputs, card names or original text.
    attr(side,'aria-label',['a11y_modules']);
    labels(side, '.brand .bname, .xmod .mn, .xmod .ms, .xtile > span, .sfoot button > span');
    if (side) side.querySelectorAll('nav').forEach(function (el) { attr(el, 'aria-label'); });
    labels(bar, '.pdesc');
    var ret=bar && bar.querySelectorAll('#inst .ret')[0];
    attr(doc.getElementById('inst'),'aria-label',[]);
    label(ret,function(s){return s.trim()==='· 返回首页'?' · Back to home':null;},[]);
    if(bar && root.PTDS_LANGUAGE_PAGES)root.PTDS_LANGUAGE_PAGES.apply(bar,{label:label,attr:attr,node:node});
    var st = context && context.st;
    if(st && st.app==='torch' && st.tview==='detail' && bar){
      bar.querySelectorAll('.crumb .up').forEach(el=>label(el,null,['sde2ef7fa8890']));
      bar.querySelectorAll('.crumb .t').forEach(el=>label(el,null,['audit_detail']));
    }
    if (st && st.app==='torch' && st.tview==='entry' && bar) {
      bar.querySelectorAll('.crumb .t').forEach(el=>label(el,null,['partner_entry_heading']));
      bar.querySelectorAll('.crumb .up').forEach(el=>label(el,null,['s3d262416fecd']));
    }
    if (st && !st.foot && ({track:['wall','adv','rules'], torch:['guard','data','sources','graph','srcgroup'], cluster:['space','objects','rules']})[st.app] && ({track:['wall','adv','rules'], torch:['guard','data','sources','graph','srcgroup'], cluster:['space','objects','rules']})[st.app].indexOf(st.app === 'torch' ? st.tview : st.app === 'cluster' ? st.cview : st.view) >= 0) labels(bar, '.crumb .t, .crumb .up, .eyebrow .zh');
    ['bell','gear','theme-tog'].forEach(function (id) { var el = doc.getElementById(id); attr(el, 'title'); attr(el, 'aria-label'); });
    label(doc.getElementById('sub-back'),null,['back']);
    if(bar)bar.querySelectorAll('.eyebrow .zh').forEach(el=>label(el,null,['track_eyebrow','torch_eyebrow','cluster_eyebrow','trace_eyebrow']));
    }
    if (options.view && root.PTDS_LANGUAGE_PAGES) root.PTDS_LANGUAGE_PAGES.apply(doc, {label:label, attr:attr,node:node});
    if (startup && options.view) startup.home(language, label);
    if (disclaimerSource !== undefined) setDisclaimer(disclaimerSource);
    if (menu) menu.querySelectorAll('[data-language]').forEach(function (b) {
      if (startup && b.getAttribute('data-language') === 'system') {
        var systemLabel = text('language_menu_system');
        if (b.firstChild.nodeValue !== systemLabel) b.firstChild.nodeValue = systemLabel;
      }
      var selected = b.getAttribute('data-language') === (mode || (startup ? 'system' : language));
      b.setAttribute('aria-checked', String(selected)); var mark = selected ? '✓' : ''; if (b.lastChild.textContent !== mark) b.lastChild.textContent = mark;
    });
    var button = doc.getElementById('language-toggle');
    var title = language === 'en' ? 'Language · English' : '语言 · 中文';
    var accessibleName = language === 'en' ? 'Language' : '语言';
    if(button && button.getAttribute('aria-label')!==accessibleName)button.setAttribute('aria-label',accessibleName);
    if(menu && menu.getAttribute('aria-label')!==accessibleName)menu.setAttribute('aria-label',accessibleName);
    if (button && button.title !== title) button.title = title;
    if(observer)observer.takeRecords();
  }
  function close(focus) {
    if (menu) menu.hidden = true;
    var button = doc.getElementById('language-toggle');
    if (button) { button.setAttribute('aria-expanded', 'false'); if (focus) button.focus(); }
  }
  function choose(value) {
    if (value !== 'zh' && value !== 'en' && !(startup && value === 'system')) return;
    const changedPreference = mode !== value;
    mode = value;
    language = effective();
    try { if(changedPreference)root.localStorage.setItem(key, value); } catch (_) { /* Switching still works without storage. */ }
    syncRoots(); apply(); close(true);
  }
  function syncSystemLanguage() {
    var next = effective();
    if (next !== language) { language = next; apply(); }
  }
  function options() { return menu ? Array.from(menu.querySelectorAll('[data-language]')) : []; }
  function open(last) {
    menu.hidden = false; doc.getElementById('language-toggle').setAttribute('aria-expanded', 'true');
    var list = options(), selected = list.find(function (b) { return b.getAttribute('aria-checked') === 'true'; });
    (last ? list[list.length - 1] : selected || list[0]).focus();
  }
  function outside(event) { if (wrapper && !wrapper.contains(event.target)) close(false); }
  function keyboard(event) {
    if (!menu || menu.hidden) return;
    if (event.key === 'Escape') { event.preventDefault(); close(true); return; }
    if (!menu.contains(event.target)) return;
    var list = options(), at = list.indexOf(doc.activeElement), next;
    if (event.key === 'ArrowDown') next = (at + 1) % list.length;
    if (event.key === 'ArrowUp') next = (at + list.length - 1) % list.length;
    if (event.key === 'Home') next = 0;
    if (event.key === 'End') next = list.length - 1;
    if (next !== undefined) { event.preventDefault(); list[next].focus(); }
    if (event.key === 'Tab') close(true);
  }
  function mount(core, small) {
    if (core) context = core;
    var anchor = doc.getElementById('bell') || doc.getElementById('gear') || (startup && doc.getElementById('home-tgear'));
    if (!anchor) {
      if (wrapper && !wrapper.isConnected) { wrapper = null; menu = null; }
      // The loading header renders navigation before its toolbar buttons become available.
      syncRoots();
      apply({view:false,chromeText:language==='en'});
      return;
    }
    if (!doc.getElementById('language-css')) { var style = doc.createElement('style'); style.id = 'language-css'; style.textContent = css; doc.head.appendChild(style); }
    if (!doc.getElementById('language-control')) {
      wrapper = doc.createElement('span'); wrapper.id = 'language-control';
      var button = doc.createElement('button'); button.id = 'language-toggle'; button.className = 'ibtn'; button.type = 'button';
      button.setAttribute('aria-label', language==='en'?'Language':'语言'); button.setAttribute('aria-haspopup', 'menu'); button.setAttribute('aria-expanded', 'false'); button.setAttribute('aria-controls', 'language-menu'); button.innerHTML = globe;
      menu = doc.createElement('div'); menu.id = 'language-menu'; menu.hidden = true; menu.setAttribute('role', 'menu'); menu.setAttribute('aria-label', language==='en'?'Language':'语言');
      var choices = [['zh',startup ? resources.messages.first_language_zh.zh : '中文','zh-CN'],['en',startup ? resources.messages.first_language_en.en : 'English','en']];
      if (startup) choices.unshift(['system',text('language_menu_system'),'']);
      choices.forEach(function (row) {
        var option = doc.createElement('button'); option.type = 'button'; option.setAttribute('role', 'menuitemradio'); option.setAttribute('data-language', row[0]); if (row[2]) option.setAttribute('lang', row[2]); option.tabIndex = -1;
        option.appendChild(doc.createTextNode(row[1])); var check = doc.createElement('span'); check.setAttribute('aria-hidden', 'true'); option.appendChild(check);
        option.onclick = function () { choose(row[0]); }; menu.appendChild(option);
      });
      button.onclick = function () { if (menu.hidden) open(false); else close(false); };
      button.onkeydown = function (event) { if (event.key === 'ArrowDown' || event.key === 'ArrowUp') { event.preventDefault(); open(event.key === 'ArrowUp'); } };
      wrapper.appendChild(button); wrapper.appendChild(menu); anchor.parentNode.insertBefore(wrapper, anchor);
    }
    if (wrapper.nextSibling !== anchor) anchor.parentNode.insertBefore(wrapper, anchor);
    if (!listening) { if (startup) root.addEventListener('languagechange', syncSystemLanguage); doc.addEventListener('pointerdown', outside); doc.addEventListener('keydown', keyboard); root.addEventListener('pagehide', pagehide); root.addEventListener('pageshow', pageshow); listening = true; }
    syncRoots();
    apply({view:language === 'en' && !small, chromeText:language === 'en'});
  }
  function overlayRoot(){
    var el=doc.getElementById('fw');
    return el && el.parentNode===doc.body ? el : null;
  }
  function syncRoots(){
    var next=['appbar','side','view'].map(function(id){return doc.getElementById(id);}).filter(Boolean),fw=overlayRoot();
    if(fw)next.push(fw);
    const status=doc.getElementById('ptds-compute-status');if(status)next.push(status);
    if(doc.body)next.push(doc.body);
    if(root.MutationObserver && (next.length!==roots.length || next.some(function(el,i){return el!==roots[i];}))){
      if(observer){observer.takeRecords();observer.disconnect();}else observer=new root.MutationObserver(changed);
      roots=next;
      roots.forEach(function(el){
        var options={childList:true};
        if(el!==doc.body){options.subtree=true;options.characterData=el.id!=='view' && el.id!=='fw';}
        if(el.id==='appbar'){options.attributes=true;options.attributeFilter=['aria-label','title'];}
        observer.observe(el,options);
      });
    }
  }
  function changed(records){
    var added=[], chrome=false,overlayChanged=false;
    var bar=doc.getElementById('appbar'),side=doc.getElementById('side'),view=doc.getElementById('view'),fw=overlayRoot();
    records.forEach(function(record){
      var target=record.target;
      if(!target || !target.isConnected)return;
      if(target===doc.body){
        Array.prototype.forEach.call(record.addedNodes || [],function(el){if(el.nodeType!==1)return;if(el.id==='fw'||el.id==='ptds-compute-status')overlayChanged=true;if(language==='en' && (el===fw || ['sq-fab','tl-pillbox','sq','tl-pillbox-card','pb-settings','ptds-compute-status'].includes(el.id) || el.getAttribute('data-sem')==='csv-import-result'))added.push(el);});
        Array.prototype.forEach.call(record.removedNodes || [],function(el){if(el.nodeType===1 && (el.id==='fw'||el.id==='ptds-compute-status'))overlayChanged=true;});
        return;
      }
      const status=doc.getElementById('ptds-compute-status');
      if(status && (target===status || status.contains(target))){if(language==='en')added.push(status);return;}
      if(bar && (target===bar || bar.contains(target))){chrome=true;return;}
      if(side && (target===side || side.contains(target))){if(language==='en')chrome=true;return;}
      if(language!=='en' || !((view && (target===view || view.contains(target))) || (fw && (target===fw || fw.contains(target)))))return;
      Array.prototype.forEach.call(record.addedNodes || [],function(el){if(el.nodeType===1 && el.isConnected)added.push(el);});
    });
    if(overlayChanged)syncRoots();
    // Coalesce this delivery by ancestry, O(N * depth); no retained cache or timer.
    var members=new Set(added),unique=Array.from(members);
    unique=unique.filter(function(el){
      for(var parent=el.parentNode;parent && parent!==doc.body;parent=parent.parentNode){
        if(members.has(parent))return false;
        if(parent===view || parent===fw)break;
      }
      return true;
    });
    if(chrome)mount(null,true);
    if(language==='en' && root.PTDS_LANGUAGE_PAGES)unique.forEach(function(el){root.PTDS_LANGUAGE_PAGES.apply(el,{label:label,attr:attr,node:node});});
    if(observer)observer.takeRecords();
  }
  function pageshow(event){if(event.persisted){language=effective();mount(null,true);apply();}}
  function pagehide(event) { if (event.persisted) close(false); else destroy(); }
  function destroy() {
    if (startup) root.removeEventListener('languagechange', syncSystemLanguage);
    if (observer) {observer.takeRecords();observer.disconnect();} observer = null; roots = [];
    doc.removeEventListener('pointerdown', outside); doc.removeEventListener('keydown', keyboard); root.removeEventListener('pagehide', pagehide); root.removeEventListener('pageshow', pageshow); listening = false;
    if (wrapper) wrapper.remove(); wrapper = null; menu = null; context = null;
  }
  root.PTDS_LANGUAGE = Object.freeze({setDisclaimer:setDisclaimer, mount:mount, destroy:destroy, text:text, select:choose, current:function () { return language; }});
  if (startup && !mode) startup.show(choose);
})(window);
