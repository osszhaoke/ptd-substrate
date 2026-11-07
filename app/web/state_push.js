/* State subscriptions: presentation only; schedules, reports and authority are server-owned. */
(function () {
  'use strict';
  var active = null;
  var FOCUS = ['grp:MAS', 'grp:BLOOD', 'grp:COAG', 'grp:LIVER'];
  function mount(panel, C, LIVE) {
    if (active) active.dispose();
    var key = C.st.key, disposed = false, controllers = new Set(), drawer = null, poll = null;
    var saved = null, catalog = [], reports = [], delivery = {}, phone = null, saving = false, initialDraft = null;
    var localAvailable = false, generation = null, timezone = '', initialReadReady = false;
    var draft = {card_ids: [], period_days: 7, time: '09:00', local_notification: false};
    var returnFocus = null, drawerMode = '', previewVersion = 0, phoneBusy = false, revokeConfirm = '';
    var esc = function (v) { return C.esc(v == null ? '' : String(v)); };
    var ic = function (name) { return C.ic(name); };
    var alive = function () { return !disposed && panel.isConnected && C.st.key === key; };
    var q = function (s) { return panel.querySelector(s); };
    var dq = function (s) { return drawer && drawer.querySelector(s); };
    var ids = function (v) { return Array.isArray(v) ? v.map(String) : []; };
    function date(v) {
      if (!v) return '尚未安排';
      return String(v).replace('T', ' ').replace(/:\d{2}(?:\.\d+)?(?:Z|[+-]\d\d:\d\d)$/, '').replace(/(?:Z|[+-]\d\d:\d\d)$/, '');
    }
    function available(c) { return c.available !== false && c.supported !== false; }
    function isFocus(c) { if (typeof c.pinned === 'boolean') return c.pinned; if (typeof c.focus === 'boolean') return c.focus; if (typeof c.selected === 'boolean') return c.selected; return FOCUS.indexOf(c.id) >= 0; }
    function names(v) { return ids(v).map(function (id) { var c = catalog.find(function (x) { return x.id === id; }); return c ? c.name : id; }).join('、'); }
    function valid() { return draft.card_ids.length > 0 && draft.card_ids.every(function (id) { return catalog.some(function (c) { return c.id === id && available(c); }); }) && /^(?:[01]\d|2[0-3]):[0-5]\d$/.test(draft.time); }
    function snapshot() { return {card_ids: draft.card_ids.slice(), period_days: draft.period_days, time: draft.time, local_notification: draft.local_notification}; }
    function same() {
      return !!saved && JSON.stringify(ids(saved.card_ids).slice().sort()) === JSON.stringify(draft.card_ids.slice().sort()) &&
        Number(saved.period_days) === draft.period_days && saved.time === draft.time && !!saved.local_notification === draft.local_notification;
    }
    function message(text, bad) {
      var el = q('[data-message]'); if (!el) return;
      el.textContent = text || ''; el.hidden = !text; el.setAttribute('role', bad ? 'alert' : 'status');
    }
    async function api(path, body, timeout) {
      var controller = new AbortController(); controllers.add(controller);
      var timer = setTimeout(function () { controller.abort(); }, timeout || 20000);
      try {
        var url = '/api/state-push/' + path, options = {cache: 'no-store', credentials: 'same-origin', headers: {'X-PTDS': '1'}, signal: controller.signal};
        if (body !== undefined) { options.method = 'POST'; options.headers = {'Content-Type': 'application/json', 'X-PTDS': '1'}; options.body = JSON.stringify(Object.assign({key: key}, body)); }
        else url += (url.indexOf('?') >= 0 ? '&' : '?') + 'key=' + encodeURIComponent(key);
        var res = await fetch(url, options), data;
        try { data = await res.json(); } catch (_) { throw new Error('服务暂时没有返回完整结果，请稍后重试。'); }
        if (!res.ok || data.error) throw new Error(data.detail || data.message || data.why || data.error || '操作未完成，请稍后重试。');
        return data;
      } catch (err) {
        if (err.name === 'AbortError') { var aborted = new Error('请求尚未完成。请检查本地服务后重试；页面不会把这次操作当作成功。'); aborted.name = 'AbortError'; throw aborted; }
        throw err;
      } finally { clearTimeout(timer); controllers.delete(controller); }
    }
    function adopt(data) {
      saved = data.subscription || null; catalog = data.catalog || catalog; reports = data.reports || [];
      delivery = data.delivery || {}; generation = data.generation || null;
      localAvailable = data.local_notification_available === true; timezone = data.tz || '';
      draft = saved ? {card_ids: ids(saved.card_ids), period_days: Number(saved.period_days), time: saved.time || '09:00', local_notification: !!saved.local_notification} :
        {card_ids: catalog.filter(function (c) { return c.selected === true && available(c) && FOCUS.indexOf(c.id) >= 0; }).map(function (c) { return c.id; }), period_days: 7, time: '09:00', local_notification: false};
      // Initial defaults are explicit approved focus groups, never all wearable cards.
      if (!saved && !draft.card_ids.length && catalog.every(function (c) { return typeof c.selected !== 'boolean'; })) draft.card_ids = catalog.filter(function (c) { return available(c) && FOCUS.indexOf(c.id) >= 0; }).map(function (c) { return c.id; });
      initialDraft = JSON.stringify(snapshot());
      render();
    }
    function choice(c) {
      var enabled = available(c), selected = draft.card_ids.indexOf(c.id) >= 0;
      return '<label class="spu-choice"><input type="checkbox" data-card="' + esc(c.id) + '" ' + (selected ? 'checked ' : '') + (enabled || selected ? '' : 'disabled ') + '><span><strong>' + esc(c.name) + '</strong>' +
        (c.reason || c.note ? '<small>' + esc(c.reason || c.note) + '</small>' : '') + '</span></label>';
    }
    function render() {
      if (!alive()) return;
      var focus = catalog.filter(isFocus), other = catalog.filter(function (c) { return !isFocus(c); });
      panel.classList.add('spu-panel');
      panel.innerHTML = '<div class="spu-intro"><div><h2 data-ptds-ui="s465af8ac11a4">给自己一份定期回顾</h2><p class="sub2" data-ptds-ui="sfb2a3af92505">星灵在本机整理所选卡片，报告留在 PTDS，准备好后提醒你。</p></div><span data-state class="spu-status"></span></div>' +
        '<div data-message class="spu-message" hidden></div><div class="spu-grid"><section aria-labelledby="spu-content-title"><div class="spu-heading"><h3 id="spu-content-title" data-ptds-inline><!--ptds-ui:scde63c6e590d-->报告内容 <!--/ptds-ui--><span data-count class="spu-count"></span></h3><button type="button" class="spu-text" data-focus data-ptds-ui="s44d6ea626c4b">仅选我的关注</button></div>' +
        '<p class="sub2 spu-helper" data-ptds-ui="sf5972c1fdf77">仅汇总你选中的卡片，新增关注不会自动加入。</p><div class="spu-category" data-ptds-ui="s9dccba0eafbb">我的关注</div><div class="spu-choices">' + focus.map(choice).join('') + '</div>' +
        (other.length ? '<details class="spu-other"><summary data-ptds-inline><!--ptds-ui:s82f491c1954c-->其他状态卡 <!--/ptds-ui--><span>' + other.length + '</span><span>' + ic('chevron-down') + '</span></summary><div class="spu-choices">' + other.map(choice).join('') + '</div></details>' : '') +
        '<p class="sub2 spu-selection" data-selection aria-live="polite"></p></section><section class="spu-schedule" aria-labelledby="spu-schedule-title"><h3 id="spu-schedule-title" data-ptds-ui="s177152c62404">推送节奏</h3>' +
        '<div class="seg spu-frequency" role="group" aria-label="推送频率" data-ptds-ui-aria-label="sf7eeb414a752">' + [[7, '每周一次'], [3, '每三天一次'], [1, '每天一次']].map(function (p) { return '<button type="button" data-days="' + p[0] + '">' + p[1] + '</button>'; }).join('') + '</div>' +
        '<div class="spu-time-row"><label for="spu-time" data-ptds-ui="s98b552661af4">提醒时间</label><input id="spu-time" data-time type="time" value="' + esc(draft.time) + '" required aria-describedby="spu-timezone"></div>' +
        '<div id="spu-timezone" class="sub2 spu-timezone">' + esc((saved || {}).tz || timezone || '按实例时区') + '</div><div class="spu-next"><span data-next-label></span><strong data-next></strong><span class="sub2" data-period></span></div>' +
        '<div class="spu-destination">' + ic('inbox') + '<div><strong data-ptds-ui="saaa572e202f4">应用内报告</strong><span class="sub2" data-ptds-ui="s43819bae07ce">在这里保留每一期，随时回来查看</span></div></div>' +
        '<label class="spu-notify"><input type="checkbox" data-notify ' + (draft.local_notification ? 'checked ' : '') + (!localAvailable ? 'disabled ' : '') + '><span data-ptds-inline><!--ptds-ui:sa97db8ca833f-->同时用 Mac 通知提醒我<!--/ptds-ui--><small>' + (localAvailable ? '通知不含健康读数；是否展示取决于 Mac 的通知设置' : '当前未连接 Mac 通知通道；应用内报告正常保留') + '</small></span></label>' +
        '<div class="spu-phone-destination" data-phone-destination></div></section></div><div class="spu-footer"><div><span class="spu-local">' + ic('cpu') + '本地 AI 生成</span><p class="sub2" data-ptds-ui="sb68cdbb981f6">Mac 休眠或 PTDS 关闭时，恢复后补发最近一期；手机查看时也需要 Mac 在线。</p></div>' +
        '<div class="spu-actions"><button type="button" class="spu-text" data-pause data-ptds-ui="sdde8b9de1ba7">暂停推送</button><button type="button" class="btn2" data-preview>' + ic('sparkles') + '预览报告</button><button type="button" class="btn" data-save data-ptds-ui="s7254715af7c9">开启订阅</button></div></div>' +
        '<section class="spu-history"><div class="spu-heading"><h3 data-ptds-ui="s32b6c4413680">最近报告</h3><span class="sub2">' + (reports.length ? reports.length + ' 期' : '尚无报告') + '</span></div><div data-history></div></section>';
      panel.querySelectorAll('[data-card]').forEach(function (el) { el.onchange = function () { draft.card_ids = Array.from(panel.querySelectorAll('[data-card]:checked')).map(function (e) { return e.dataset.card; }); if (!el.checked && !available(catalog.find(function (c) { return c.id === el.dataset.card; }))) el.disabled = true; changed(); }; });
      panel.querySelectorAll('[data-days]').forEach(function (el) { el.onclick = function () { draft.period_days = Number(el.dataset.days); changed(); }; });
      q('[data-focus]').onclick = function () { draft.card_ids = catalog.filter(function (c) { return isFocus(c) && available(c); }).map(function (c) { return c.id; }); panel.querySelectorAll('[data-card]').forEach(function (e) { e.checked = draft.card_ids.indexOf(e.dataset.card) >= 0; e.disabled = !available(catalog.find(function (c) { return c.id === e.dataset.card; })); }); changed(); };
      q('[data-time]').oninput = function (e) { draft.time = e.target.value; changed(); };
      q('[data-notify]').onchange = function (e) { draft.local_notification = e.target.checked; changed(); };
      q('[data-save]').onclick = save; q('[data-pause]').onclick = pause;
      q('[data-preview]').onclick = preview;
      q('[data-history]').innerHTML = reports.length ? reports.map(function (r) {
        return '<div class="spu-history-row">' + ic('file-text') + '<div><strong>' + esc((r.period || {}).label || '状态回顾') + '</strong><span>' + esc(date(r.created_at)) + '生成 · ' + ids(r.card_ids).length + ' 张状态卡</span></div><button type="button" class="spu-text" data-report="' + esc(r.id) + '">查看报告 ' + ic('chevron-right') + '</button></div>';
      }).join('') : '<p class="sub2" data-ptds-ui="s2f340d4f411a">第一期生成后会保存在这里，暂停推送也会保留已有报告。</p>';
      panel.querySelectorAll('[data-report]').forEach(function (b) { b.onclick = function () { readReport(b.dataset.report); }; });
      update(); renderPhoneDestination();
      var last = generation && generation.state !== 'ok' && generation.state !== 'generating' ? generation.why || '最近一期尚未生成，请检查本地星灵。' : delivery.last_error || (saved || {}).last_error;
      if (last) message(typeof last === 'string' ? last : last.detail || last.why || '最近一期尚未生成，请检查本地星灵。', true);
    }
    function changed() {
      previewVersion++; update();
      if (drawerMode === 'preview' && drawer && drawer.isConnected) {
        dq('.db').innerHTML = '<p role="status" data-ptds-ui="s76d88e7d669b">选择已变化。重新预览后，报告会按当前内容生成。</p><button type="button" class="btn2" data-refresh-preview data-ptds-ui="s088badb8c6f6">重新预览</button>';
        dq('[data-refresh-preview]').onclick = preview;
      }
    }
    function update() {
      if (!alive() || !q('[data-count]')) return;
      var dirty = saved && !same(), enabled = saved && saved.enabled;
      q('[data-count]').textContent = '已选 ' + draft.card_ids.length + ' 张';
      var missing = draft.card_ids.some(function (id) { return !catalog.some(function (c) { return c.id === id && available(c); }); });
      q('[data-selection]').textContent = missing ? '已选卡片中有已隐藏或停用的内容，请取消勾选后保存。' : draft.card_ids.length ? '报告仅包含已勾选的 ' + draft.card_ids.length + ' 张卡片' : '至少选择 1 张状态卡，才能预览或开启订阅。';
      panel.querySelectorAll('[data-days]').forEach(function (b) { b.setAttribute('aria-pressed', String(Number(b.dataset.days) === draft.period_days)); });
      q('[data-state]').textContent = saved ? enabled ? dirty ? '已开启 · 有未保存的修改' : '推送已开启' : '已暂停' : '尚未开启';
      q('[data-next-label]').textContent = !saved ? '首次推送' : !enabled ? '恢复后首次推送' : dirty ? '保存后下次推送' : '下次推送';
      q('[data-next]').textContent = saved && enabled && !dirty && (saved.next_due_at || saved.next_at) ? date(saved.next_due_at || saved.next_at) : '保存后安排推送时间';
      q('[data-period]').textContent = '回顾推送日前 ' + draft.period_days + ' 个完整自然日';
      q('[data-save]').textContent = saving ? '正在保存…' : saved ? enabled ? '保存修改' : '恢复推送' : '开启订阅';
      q('[data-save]').disabled = saving || !valid() || (enabled && same());
      q('[data-pause]').hidden = !enabled; q('[data-pause]').disabled = saving;
      q('[data-preview]').disabled = !valid() || saving;
      q('[data-time]').setAttribute('aria-invalid', String(!/^(?:[01]\d|2[0-3]):[0-5]\d$/.test(draft.time)));
    }
    async function save() {
      if (saving || !valid()) return;
      saving = true; update(); message('');
      try {
        var data = await api('save', Object.assign(snapshot(), {enabled: true}));
        if (!alive()) return;
        if (!data.catalog) data = await api('status');
        if (!alive()) return;
        adopt(data); message('订阅已保存。报告生成后会出现在这里。'); refreshPhone();
      } catch (e) { if (alive()) message(e.message, true); }
      finally { saving = false; if (alive()) update(); }
    }
    async function pause() {
      if (saving || !saved) return;
      saving = true; update(); message('');
      try {
        var data = await api('pause', {paused: true});
        if (!data.catalog) data = await api('status');
        if (alive()) { adopt(data); message('已暂停推送，已有报告仍可查看。'); }
      } catch (e) { if (alive()) message(e.message, true); }
      finally { saving = false; if (alive()) update(); }
    }
    function openDrawer(title, mode) {
      var focus = document.activeElement;
      closeDrawer(false);
      if (C.closeDrawer) C.closeDrawer();
      returnFocus = focus; drawerMode = mode;
      drawer = document.createElement('aside'); drawer.id = 'drawer'; drawer.className = 'drawer spu-drawer';
      drawer.setAttribute('role', 'dialog'); drawer.setAttribute('aria-modal', 'false'); drawer.setAttribute('aria-label', title);
      drawer.innerHTML = '<div class="dh">' + ic(mode === 'phone' ? 'smartphone' : 'sparkles') + '<span>' + esc(title) + '</span><button type="button" class="ibtn" data-close aria-label="关闭' + esc(title) + '">' + ic('x') + '</button></div><div class="db" aria-live="polite"></div>';
      C.st.drawer = 'live'; document.body.appendChild(drawer);
      dq('[data-close]').onclick = function () { closeDrawer(true); }; dq('[data-close]').focus();
      drawer.addEventListener('keydown', function (e) { if (e.key === 'Escape') { e.preventDefault(); closeDrawer(true); } });
    }
    function closeDrawer(focus) {
      clearTimeout(poll); poll = null; previewVersion++;
      if (drawer) { var owned = drawer.isConnected; if (owned) drawer.remove(); drawer = null; if (owned) C.st.drawer = null; }
      drawerMode = ''; if (focus && returnFocus && returnFocus.isConnected) returnFocus.focus();
    }
    function reportHTML(report, isPreview) {
      if (!report || report.state !== 'ok') return '<p role="status">' + esc((report || {}).why || (report || {}).detail || '本地星灵尚未完成报告，本次未生成内容。') + '</p>';
      var period = report.period || {}, list = report.cards || [];
      var number = function (text) { return esc(text).replace(/\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}(?::\d{2})?(?:Z|[-+]\d{2}:\d{2}))?|HLH-2004|2016|[-+]?\d+(?:\.\d+)?%?/g, function (n) { return /^\d{4}-\d{2}-\d{2}/.test(n) || n === 'HLH-2004' || n === '2016' ? n : '<strong>' + n + '</strong>'; }); };
      return '<div class="spu-kicker">' + (isPreview ? '预览 · 不保存、不发送通知' : '已保存报告') + '</div><h2 data-ptds-ui="sb3587d6366e7">我的状态回顾</h2><div class="spu-range">' + esc(period.label || (date(period.start) + ' — ' + date(period.end))) + '</div><div class="spu-report-scope">' + list.length + ' 张状态卡 · ' + esc(period.tz || '') + '<br>按观测日期回顾，不以导入时间替代观测时间</div>' +
        list.map(function (card) { return '<section class="spu-report-section"><h3>' + esc(card.name) + '</h3><p>' + number(card.text) + '</p>' + ((card.records || []).length ? '<details><summary data-ptds-inline><!--ptds-ui:sdb8db0530432-->查看 <!--/ptds-ui-->' + card.records.length + ' 条依据</summary>' + card.records.map(function (r) {
          return '<div class="spu-source">' + esc(r.label || r.code || '记录') + ' · ' + esc(r.at || r.date || '') + '<br>' + number((r.comparator || '') + (r.value == null ? '未记录' : r.value)) + ' ' + esc(r.unit || '') +
            (r.kind === 'state' ? '<br>计算记录 ' + esc(r.run_id == null ? '未标记' : r.run_id) : r.ref && C.openTorchDetail ? ' <button type="button" class="spu-text" data-source="' + esc(r.ref) + '">查看来源</button>' : '') + '</div>';
        }).join('') + '</details>' : '') + '</section>'; }).join('') + '<div class="spu-report-foot">' + esc(report.by || '本地星灵') + '<br>' + esc(report.method || '') + '<br>仅整理已有读数与状态，不作诊断或治疗建议。</div>';
    }
    function fillReport(report, preview) {
      dq('.db').innerHTML = reportHTML(report, preview);
      drawer.querySelectorAll('[data-source]').forEach(function (b) { b.onclick = function () { var ref = b.dataset.source; closeDrawer(false); if (alive()) C.openTorchDetail(ref, 'data'); }; });
    }
    async function preview() {
      if (!valid()) return;
      var input = snapshot(); openDrawer('星灵 · 状态报告', 'preview');
      var version = ++previewVersion, target = drawer;
      dq('.db').innerHTML = '<div class="spu-thinking">' + ic('sparkles') + '星灵正在整理所选卡片…</div><p class="sub2" data-ptds-ui="sfe82d9bdaeac">仅使用本期已有记录。预览不会保存或发送通知。</p>';
      try { var r = await api('preview', Object.assign(input, {enabled: true}), 180000); if (alive() && drawer === target && target.isConnected && previewVersion === version) fillReport(r.report || r, true); }
      catch (e) { if (alive() && drawer === target && target.isConnected && previewVersion === version) dq('.db').innerHTML = '<p role="alert">' + esc(e.message) + '</p>'; }
    }
    async function readReport(id) {
      openDrawer('星灵 · 状态报告', 'report'); var target = drawer;
      dq('.db').innerHTML = LIVE.readingHtml('compact');
      try { var r = await api('report?id=' + encodeURIComponent(id)); if (alive() && drawer === target && target.isConnected) fillReport(r.report || r, false); }
      catch (e) { if (alive() && drawer === target && target.isConnected) dq('.db').innerHTML = LIVE.readingHtml('compact',e.name==='AbortError'?'timeout':'error',e.message); }
    }
    function renderPhoneDestination() {
      var el = q('[data-phone-destination]'); if (!el) return;
      var count = phone && (phone.devices || []).filter(function (d) { return String(d.status || '').toUpperCase() === 'ACTIVE'; }).length;
      el.innerHTML = '<div class="spu-phone-line">' + ic('smartphone') + '<div><strong data-ptds-ui="s2fec4a1c5074">手机提醒</strong><small>' + (count ? count + ' 部手机已授权阅读' : '报告准备好，在手机上提醒你') + '</small></div><button type="button" class="spu-text" data-phone-open>' + (count ? '管理' : '连接手机') + '</button></div><p class="spu-caption">' + (phone && phone.setup_required ? '手机通道尚未配置；本机订阅可独立使用' : '无需下载 App；iPhone 需添加到主屏幕') + '</p>';
      q('[data-phone-open]').onclick = openPhone;
    }
    async function refreshPhone(polling) {
      if (!alive()) return;
      if (phoneBusy) { if (polling && drawerMode === 'phone') poll = setTimeout(function () { refreshPhone(true); }, 1000); return; }
      phoneBusy = true;
      try {
        var data = await api('phone/status');
        if (!alive()) return;
        var changed = JSON.stringify(phone) !== JSON.stringify(data); phone = data; renderPhoneDestination();
        if (drawerMode === 'phone' && drawer && drawer.isConnected) {
          if (changed) renderPhoneDrawer();
          else if (dq('[data-phone-error]')) dq('[data-phone-error]').hidden = true;
        }
      } catch (e) {
        if (alive() && drawerMode === 'phone' && drawer && drawer.isConnected) {
          var initial = dq('[data-phone-read]'), err = dq('[data-phone-error]');
          if (initial) { initial.innerHTML = LIVE.readingHtml('compact',e.name==='AbortError'?'timeout':'error',e.message); if (err) err.hidden = true; }
          else if (err) { err.textContent = e.message; err.hidden = false; }
        }
      } finally {
        phoneBusy = false;
        if (polling && alive() && drawerMode === 'phone' && drawer && drawer.isConnected) poll = setTimeout(function () { refreshPhone(true); }, 3000);
      }
    }
    function openPhone() {
      openDrawer('手机提醒', 'phone'); renderPhoneDrawer(); refreshPhone(true);
    }
    function safeQR(v) { return typeof v === 'string' && (/^data:image\/png;base64,[A-Za-z0-9+/=]+$/.test(v) || /^\/api\/state-push\/phone\/qr(?:\?|$)/.test(v)); }
    function safeURL(v) { try { var u = new URL(v); return u.protocol === 'https:' && !u.username && !u.password ? u.href : ''; } catch (_) { return ''; } }
    function renderPhoneDrawer() {
      if (!drawer || !drawer.isConnected || drawerMode !== 'phone') return;
      var body = '', ready = saved && same(), p = phone || {}, invite = p.invitation;
      if (p.setup_required) body += '<div class="spu-note"><b data-ptds-ui="scb2c2d4c0816">手机通道尚未配置</b><p>' + esc(p.detail || '需要稳定的 HTTPS 入口与手机通知配置，完成后才能连接手机。') + '</p><p data-ptds-ui="s88601658438d">本机订阅与应用内报告仍可使用。</p></div>';
      else if (!phone) body += '<div data-phone-read>' + LIVE.readingHtml('compact') + '</div>';
      var pending = p.pending || [], devices = p.devices || [];
      pending.forEach(function (d) {
        body += '<section class="spu-phone-request"><div class="spu-kicker" data-ptds-ui="s23c1d6b39929">手机正在申请配对</div><h2 data-ptds-ui="s3b5f9a78f722">是你的手机吗？</h2><p data-ptds-ui="s6e276ac20aa7">核对手机上显示的号码：</p><div class="spu-code">' + esc(d.confirmation) + '</div><dl class="spu-facts"><div><dt data-ptds-ui="se1506406a5bd">设备</dt><dd>' + esc(d.name || '手机浏览器') + '</dd></div><div><dt data-ptds-ui="s3af2b3bd4552">阅读范围</dt><dd>' + esc(names((saved || {}).card_ids)) + '<small data-ptds-ui="s165c25805439">仅本次授权后生成的报告</small></dd></div><div><dt data-ptds-ui="s9c2a28e8f98f">有效期</dt><dd data-ptds-ui="see3d4773aa1a">30 天 · 可随时撤回</dd></div><div><dt data-ptds-ui="s978cbca6265d">权限</dt><dd data-ptds-ui="s6e1c0d3604f4">只读，不可修改数据</dd></div></dl><button type="button" class="btn" data-approve="' + esc(d.device_id) + '">确认是我的手机</button><p class="spu-caption" data-ptds-ui="s7301a8c4d33e">确认后创建正式阅读授权。手机通知权限需在手机上单独开启。</p></section>';
      });
      devices.forEach(function (d) {
        var rawState = String(d.status || '').toUpperCase(), inactive = rawState !== 'ACTIVE';
        var state = inactive ? rawState === 'REVOKED' ? '已撤回' : /EXPIRE/.test(rawState) ? '授权已到期' : '授权不可用' : d.scope_changed ? '阅读范围待重新确认' : '报告阅读已授权';
        body += '<section class="spu-phone-device"><h3>' + esc(d.name || '手机浏览器') + '</h3><p>' + state + '</p><dl class="spu-facts"><div><dt data-ptds-ui="s2fec4a1c5074">手机提醒</dt><dd>' + (d.notification_enabled ? '已登记手机提醒' : '尚未登记手机提醒') + '<small data-ptds-ui="sc3fbc7eb04ba">实际展示仍取决于手机的通知权限与网络</small></dd></div><div><dt data-ptds-ui="s3af2b3bd4552">阅读范围</dt><dd>' + esc(names((d.scope || {}).card_ids)) + '<small data-ptds-ui="sf8d7a204fe21">仅授权后生成、且仍在当前订阅范围内的报告</small></dd></div><div><dt data-ptds-ui="s9c2a28e8f98f">有效期</dt><dd>' + esc(date(d.expires_at)) + '</dd></div></dl>' +
          (d.scope_changed ? '<div class="spu-note" data-ptds-ui="s27ce07384966">订阅内容已增加。此手机不会自动获得新增内容，请撤回后重新连接并确认范围。</div>' : '') +
          (!inactive ? '<div class="spu-phone-controls">' + (revokeConfirm === d.grant_id ? '<span data-ptds-ui="s4ee14a4ac5ae">撤回后此手机将无法继续读取。</span><button type="button" class="btn2" data-revoke="' + esc(d.grant_id) + '">确认撤回</button><button type="button" class="spu-text" data-revoke-cancel data-ptds-ui="s2cd0f3be8738">取消</button>' : '<button type="button" class="spu-text" data-revoke-ask="' + esc(d.grant_id) + '">撤回此手机</button>') + '</div>' : '') + '</section>';
      });
      if (!p.setup_required && phone) {
        if (!ready) body += '<div class="spu-note" data-ptds-ui="s6a1f4b12704e">先保存当前订阅内容，再连接手机。</div>';
        if (invite) {
          var url = safeURL(invite.pair_url);
          body += '<div class="spu-qr">' + (safeQR(invite.qr) ? '<img src="' + esc(invite.qr) + '" alt="手机连接入口二维码">' : '<p data-ptds-ui="s042b79c1640c">二维码暂不可用，请在手机打开下方入口。</p>') + '</div>' +
            (url ? '<a class="spu-phone-url" href="' + esc(url) + '" target="_blank" rel="noopener noreferrer">' + esc(url) + '</a>' : '') +
            (invite.pair_code ? '<p data-ptds-inline><!--ptds-ui:se1c88d9cf8e3-->配对码：<!--/ptds-ui--><strong class="spu-pair-code">' + esc(invite.pair_code) + '</strong></p>' : '') +
            '<p class="spu-caption" data-ptds-inline><!--ptds-ui:sdb494a5d3648-->入口有效至 <!--/ptds-ui-->' + esc(date(invite.expires_at)) + '。这不是阅读授权，仍需 Mac 确认。</p>';
        }
        body += '<ol class="spu-steps"><li><b data-ptds-ui="sd5c2b209712c">用手机打开入口</b><span data-ptds-ui="s5bbc46a80e50">iPhone：在浏览器分享菜单中添加到主屏幕。</span></li><li><b data-ptds-ui="saefa98f21988">从主屏幕打开 PTDS，再申请配对</b><span data-ptds-ui="s2221e5bd5895">手机显示确认号码后，在这台 Mac 核对。</span></li><li><b data-ptds-ui="sd6953d0017b7">Mac 确认后，在手机开启提醒</b><span data-ptds-ui="s66ab7903f261">通知只显示“你的状态报告已生成”，不含健康读数。</span></li></ol>' +
          '<button type="button" class="btn2" data-start ' + (ready ? '' : 'disabled') + '>' + (invite ? '重新生成连接入口' : '生成连接入口') + '</button>';
      }
      body += '<p class="spu-caption" data-ptds-ui="s2a2af94df362">撤回后停止提醒和后续读取；已阅读内容与截图无法收回。本机订阅不受影响。</p><p data-phone-error class="spu-message" role="alert" hidden></p>';
      dq('.db').innerHTML = body;
      drawer.querySelectorAll('[data-approve]').forEach(function (b) { b.onclick = function () { phoneAction('approve', {device_id: b.dataset.approve}); }; });
      drawer.querySelectorAll('[data-revoke-ask]').forEach(function (b) { b.onclick = function () { revokeConfirm = b.dataset.revokeAsk; renderPhoneDrawer(); }; });
      drawer.querySelectorAll('[data-revoke]').forEach(function (b) { b.onclick = function () { phoneAction('revoke', {grant_id: b.dataset.revoke}); }; });
      drawer.querySelectorAll('[data-revoke-cancel]').forEach(function (b) { b.onclick = function () { revokeConfirm = ''; renderPhoneDrawer(); }; });
      if (dq('[data-start]')) dq('[data-start]').onclick = function () { phoneAction('start', {}); };
    }
    async function phoneAction(action, body) {
      if (phoneBusy || !alive()) return;
      phoneBusy = true; clearTimeout(poll);
      if (drawer) drawer.querySelectorAll('button:not([data-close])').forEach(function (b) { b.disabled = true; });
      try {
        var r = await api('phone/' + action, body, 30000);
        if (!alive()) return; phone = r; revokeConfirm = ''; renderPhoneDestination(); renderPhoneDrawer();
      } catch (e) { if (alive() && drawerMode === 'phone' && drawer && drawer.isConnected) { renderPhoneDrawer(); dq('[data-phone-error]').textContent = e.message; dq('[data-phone-error]').hidden = false; } }
      finally { phoneBusy = false; if (alive() && drawerMode === 'phone' && drawer && drawer.isConnected) poll = setTimeout(function () { refreshPhone(true); }, 3000); }
    }
    function dispose() {
      disposed = true; clearTimeout(poll); closeDrawer(false);
      controllers.forEach(function (c) { c.abort(); }); controllers.clear(); observer.disconnect();
      if (active && active.dispose === dispose) active = null;
    }
    var observer = new MutationObserver(function () { if (!alive()) dispose(); });
    observer.observe(document.body, {childList: true, subtree: true});
    // Preserve the initial read/error surface across background snapshot paints.
    // Otherwise a remount aborts the read and resets its timeout on every refresh.
    // Navigation still disposes this panel; a failed read waits for explicit retry.
    active = {dispose: dispose, isEditing: function () { return alive() && (!initialReadReady || saving || !!(drawer && drawer.isConnected) || (initialDraft !== null && JSON.stringify(snapshot()) !== initialDraft)); }};
    panel.classList.add('spu-panel'); panel.innerHTML = LIVE.readingHtml('compact');
    api('status').then(function (data) { if (alive()) { adopt(data); initialReadReady = true; refreshPhone(); } }).catch(function (e) {
      if (alive()) { panel.innerHTML = LIVE.readingHtml('compact',e.name==='AbortError'?'timeout':'error',e.message)+'<button type="button" class="btn2" data-reload data-ptds-ui="sdf7392cc96be">重新读取</button>'; q('[data-reload]').onclick = function () { mount(panel, C, LIVE); }; }
    });
    return active;
  }
  window.PTDS_STATE_PUSH = {mount: mount, isEditing: function () { return !!(active && active.isEditing()); }, dispose: function () { if (active) active.dispose(); }};
}());
