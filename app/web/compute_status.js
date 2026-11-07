/* Saved-data computation status. Uses the existing refresh clock; no device polling. */
(function (root) {
  'use strict';
  var C, LIVE, request, states = Object.create(null), busy = Object.create(null), seen = Object.create(null);
  var receipts = new WeakMap();
  var pending = '数据已保存，状态更新中', failed = '数据已保存，状态更新失败，可重试';
  function enabled() { return !!(C && C.DATA.ptds_live && C.DATA.ptds_live.compute_queue_version >= 1); }
  function active(s) { return s && (s.state === 'PENDING' || s.state === 'RUNNING' || s.state === 'FAILED'); }
  function render() {
    if (!C || !root.document) return;
    var el = document.getElementById('ptds-compute-status'), s = states[C.st.key];
    if (!active(s)) { if (el) el.remove(); return; }
    if (!el) {
      el = document.createElement('div'); el.id = 'ptds-compute-status'; el.className = 'panel';
      el.setAttribute('role', 'status'); el.setAttribute('aria-live', 'polite');
      el.style.cssText = 'position:fixed;bottom:20px;left:280px;max-width:calc(100vw - 300px);padding:12px 18px;z-index:1100;background:var(--bg,#faf9f5);border:1px solid var(--line,#ccc);border-radius:12px;color:var(--ink,#202536);box-sizing:border-box';
      document.body.appendChild(el);
    }
    el.replaceChildren();
    var label = document.createElement('span'); label.textContent = s.state === 'FAILED' ? failed : pending; el.appendChild(label);
    if (s.state === 'FAILED') {
      var button = document.createElement('button'), key = C.st.key;
      button.textContent = '重试'; button.type = 'button'; button.style.marginLeft = '12px';
      button.onclick = async function () {
        button.disabled = true;
        try { accept(key, await request('POST', '/api/compute/retry', {key:key})); if(C.st.key===key&&C.render)C.render(); }
        catch (e) { if (C.st.key === key) C.toast(LIVE.saveErr(e)); }
        finally { render(); }
      };
      el.appendChild(button);
    }
  }
  function accept(key, value) {
    if (!value || !['IDLE','PENDING','RUNNING','DONE','FAILED'].includes(value.state)) throw Error('COMPUTE_STATE_INVALID');
    var old = states[key], identity = C.SNAPS[key] && C.SNAPS[key].instance.instance_id;
    if (value.instance_id && identity && value.instance_id !== identity) throw Error('COMPUTE_INSTANCE_MISMATCH');
    if (old && (value.generation || 0) < (old.generation || 0)) return; // late status cannot erase a newer receipt
    states[key] = Object.assign({}, value); seen[key] = true;
    if (value.state === 'DONE' && active(old)) LIVE.invalidateAfterWrite(key);
    render();
  }
  async function tick() {
    if (!enabled()) return;
    var key = C.st.key; render();
    if (!key || busy[key] || (seen[key] && !active(states[key]))) return;
    busy[key] = true;
    try { var previous=states[key]; accept(key, await request('GET', '/api/compute/status?key=' + encodeURIComponent(key))); if(C.st.key===key&&previous&&states[key].state!==previous.state&&C.render)C.render(); }
    catch (e) { /* Keep the last confirmed state; a lost response is not completion. */ }
    finally { busy[key] = false; }
  }
  function track(key, result) {
    if (enabled() && result && result.sync && result.sync.state) { receipts.set(result,key); accept(key, result.sync); }
  }
  function receipt(res, core) {
    var sy = (res || {}).sync || {}, names = [], current = receipts.has(res) && states[receipts.get(res)];
    if (sy.state && current && current.generation >= sy.generation) sy = current;
    if (sy.state === 'DONE') return '已保存到我的数据';
    if (sy.state === 'PENDING' || sy.state === 'RUNNING') return pending;
    if (sy.state === 'FAILED') return failed;
    if (!sy.ok) return '已保存到我的数据；交给星轨时没有成功，可在顶栏同步状态里重试。';
    if ((sy.new || []).length || (sy.updated || []).length) names.push('sJIA 关注卡');
    var cc = (core.S() || {}).custom_cards || [];
    (sy.custom || []).forEach(function (r) {
      if (!(r.evaluated || []).length) return;
      var c = cc.filter(function (x) { return x.card_id === r.card_id; })[0];
      names.push(c && c.definition ? '「' + c.definition.name + '」' : '自定义卡');
    });
    return names.length ? '已保存到我的数据，并已交给星轨：' + names.join('、') + ' 已按新数据自动算好，不用再点。'
      : '已保存到我的数据，并已交给星轨。目前没有状态卡用到这些指标。';
  }
  root.PTDS_COMPUTE = {enabled:enabled, tick:tick, track:track, receipt:receipt,
    install:function (core, live, call) {
      C = core; LIVE = live; request = call;
      if (!enabled()) return;
      var previous = C.render;
      if (previous) C.render = function () { var value = previous.apply(this, arguments); render(); return value; };
      tick();
    }};
})(window);
