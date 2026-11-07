// PTDS_READ_UI_BUNDLE_BEGIN
/* Canonical read-only presentation. Bundled into existing desktop/mobile assets
 * by tools/build_read_transition.py; never starts a request or changes authority. */
(function (root) {
  'use strict';
  var escape = function (s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]; }); };
  var star = '<path class="ptds-read-star" d="M0-8C1-2 2-1 8 0 2 1 1 2 0 8-1 2-2 1-8 0-2-1-1-2 0-8Z"/>';
  var positions = [[26,112],[94,113],[166,104],[240,88],[314,66],[390,38]];
  var orbit = '<svg class="ptds-read-orbit" viewBox="0 0 420 140" aria-hidden="true" focusable="false">' +
    '<path class="ptds-read-trail-soft" d="M12 132C110 147 266 118 411 26"/>' +
    '<path class="ptds-read-trail" d="M26 112C116 130 281 92 390 38"/>' +
    positions.map(function (p) { return '<g class="ptds-read-point" transform="translate('+p[0]+' '+p[1]+')">' + star + '</g>'; }).join('') +
    '<g class="ptds-read-dust"><circle cx="92" cy="35" r="1"/><circle cx="269" cy="22" r="1"/><circle cx="345" cy="120" r="1"/></g></svg>';
  root.PTDS_READ_UI = {
    html: function (size, state, detail) {
      size = ['page','compact','inline'].indexOf(size) >= 0 ? size : 'compact';
      state = ['loading','timeout','error'].indexOf(state) >= 0 ? state : 'loading';
      var loading = state === 'loading';
      return '<div class="ptds-read ptds-read--'+size+'" data-star-read="1" data-state="'+state+'" role="'+(loading?'status':'alert')+'"'+(loading?' aria-label="内容加载中"':'')+' aria-live="polite" aria-atomic="true">' +
        orbit + '<div class="ptds-read-copy"><div class="ptds-read-kicker">星渐明，影随形</div>' +
        (loading?'':'<div class="ptds-read-title">'+(state==='timeout'?'这次读取超时了':'暂时无法读取')+'</div>') +
        (!loading && detail ? '<p class="ptds-read-detail">'+escape(detail)+'</p>' : '') +
        '</div></div>';
    }
  };
})(window);
// PTDS_READ_UI_BUNDLE_END
// PTDS_TAIL_COMPONENT_BEGIN
/* Shared wearable card. The OS host renders this exact HTML/CSS, never a second design. */
(function (root) {
  'use strict';
  var esc = function (s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]; }); };
  var UI = { css: ".tl-name{display:inline-flex;align-items:center;gap:5px;font:inherit;color:#cfd6e2;background:none;border:var(--primitive-border-hairline) solid transparent;border-radius:8px;padding:2px 6px;margin-left:-6px;cursor:pointer;flex:none}.tl-name:hover{border-color:rgba(190,200,215,.5)}.tl-name b{color:var(--theme-text-primary)}.tl-name svg{width:14px;height:14px}.tl-card{position:fixed;width:300px;max-width:calc(100vw - 96px);background:var(--theme-surface-raised);color:var(--theme-text-primary);border:var(--primitive-border-hairline) solid rgba(190,200,215,.5);border-radius:14px;box-shadow:0 14px 40px rgba(0,0,0,.45);z-index:61;padding:10px 12px 12px}.tl-h{display:flex;align-items:center;gap:6px;margin-bottom:8px;color:#cfd6e2}.tl-h b{color:var(--theme-text-primary)}.tl-h .sub2{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.tl-g{display:grid;grid-template-columns:1fr 1fr;gap:8px}.tl-t{display:flex;flex-direction:column;align-items:flex-start;gap:2px;text-align:left;font:inherit;color:inherit;background:rgba(128,140,160,.1);border:0;border-radius:10px;padding:8px 10px;cursor:pointer}.tl-t:hover{background:rgba(128,140,160,.18)}.tl-t.old .tl-v{color:var(--theme-text-secondary)}.tl-l{font-size:var(--scale-type-meta);color:var(--theme-text-secondary)}.tl-v{font-size:22px;font-weight:600;line-height:1.2}.tl-v.na{color:var(--theme-text-tertiary)}.tl-u{font-size:12px;color:var(--theme-text-tertiary);margin-left:3px}.tl-a{font-size:11px;color:var(--theme-text-tertiary)}.tl-f{font-size:11px;color:var(--theme-text-tertiary);margin-top:8px;line-height:1.5} .tl-card,.tl-card *{box-sizing:border-box}.tl-card button{line-height:inherit}.tl-card .tl-h .sub2{font-size:var(--scale-type-meta);line-height:1.6;color:var(--theme-text-secondary);min-width:0;flex:1}.tl-card .tl-h>.grow{display:none}.tl-card .tl-h .ibtn{display:inline-flex;align-items:center;justify-content:center;width:36px;height:36px;min-width:36px;flex:none;border:0;border-radius:10px;padding:1px 6px;background:none;color:var(--theme-text-secondary);font:inherit;cursor:pointer}.tl-card .tl-h .ibtn:hover{background:rgba(128,140,160,.16);color:var(--theme-text-primary)}.tl-card .tl-h .ibtn svg{width:18px;height:18px}.tl-card .tl-h .ibtn[aria-pressed=\"true\"]{color:#E8B65A;background:rgba(232,182,90,.1)}.tl-card .tl-h .ibtn:focus-visible,.tl-card .tl-t:focus-visible{outline:2px solid var(--theme-text-primary);outline-offset:1px}.tl-card .tl-ic{display:inline-flex}.tl-card .tl-ic.sm svg{width:16px;height:16px}.tl-card b{font-weight:700}.tl-card svg{display:block;flex:none}.tl-card .tl-h .ibtn:disabled{opacity:.55;cursor:wait}", pinIcon: "<svg width=\"14\" height=\"14\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\" aria-hidden=\"true\"><path d=\"M12 17v5\"/><path d=\"M9 10.76a2 2 0 0 1-1.11 1.79l-1.78.9A2 2 0 0 0 5 15.24V16a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-.76a2 2 0 0 0-1.11-1.79l-1.78-.9A2 2 0 0 1 15 10.76V7a1 1 0 0 1 1-1 2 2 0 0 0 0-4H8a2 2 0 0 0 0 4 1 1 0 0 1 1 1z\"/></svg>", bandIcon: "<svg viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.8\" aria-hidden=\"true\"><rect x=\"8\" y=\"2.5\" width=\"8\" height=\"19\" rx=\"4\"/><rect x=\"9.8\" y=\"9\" width=\"4.4\" height=\"6\" rx=\"1.2\"/></svg>" };
  UI.ouraIcon = "<svg viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.8\" aria-hidden=\"true\"><ellipse cx=\"12\" cy=\"13\" rx=\"7.5\" ry=\"7\"/><path d=\"M8.5 6.5c1-1.6 2.2-2.4 3.5-2.4s2.5.8 3.5 2.4\"/></svg>";
  UI.pin = function (pinned, busy) {
    var label = pinned ? '取消跨应用置顶' : '锁定在所有窗口前端';
    return '<button type="button" class="ibtn" data-desktop-pin="1" aria-pressed="' + !!pinned + '" aria-label="' + label + '" title="' + label + '"' + (busy ? ' disabled' : '') + '>' + UI.pinIcon + '</button>';
  };
  UI.share = function () { return '<button type="button" class="ibtn" data-tl-share="1" aria-label="分享 Somaloop 到手机" title="分享与授权管理" data-ptds-ui-aria-label="sab2beea85a69" data-ptds-ui-title="s8d00cb1277e6"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 16V3m-4 4 4-4 4 4M5 11v9h14v-9"/></svg></button>'; };
  UI.shareSummary = function (s) {
    if (!s) return '分享状态待更新';
    if (!s.running || !s.grant || s.grant.status !== 'ACTIVE') return '未分享';
    var n = Number.isInteger(s.approved_count) ? s.approved_count : 0;
    var pending = Number.isInteger(s.pending_count) ? s.pending_count : 0;
    return '分享中 · ' + n + ' 台' + (pending ? ' · 待批准 ' + pending + ' 台' : '');
  };
  UI.css += '.tl-card .tl-sharing{display:flex;align-items:center;gap:6px;margin:0 0 8px;padding:4px 6px;border:0;border-radius:8px;background:rgba(128,140,160,.1);color:var(--theme-text-secondary);font:inherit;font-size:12px;cursor:pointer;width:100%;text-align:left}.tl-sharing svg{width:16px;height:16px}.tl-sharing:focus-visible{outline:2px solid var(--theme-text-primary);outline-offset:2px}';
  UI.header = function (d) {
    var status = d.device === 'somaloop' ? (/^已连接/.test(d.status || '') ? '已连接' : '未连接') : d.status;
    var name = '<span class="tl-ic sm">' + (d.icon || UI.bandIcon) + '</span><b>' + esc(d.name) + '</b>';
    var close = d.readOnly ? '' : '<button type="button" class="ibtn" data-tl-x="1" aria-label="' + (d.native ? '关闭读数窗口' : '收起') + '" title="' + (d.native ? '关闭读数窗口' : '收起') + '"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" aria-hidden="true"><path d="m6 6 12 12M18 6 6 18"/></svg></button>';
    return '<div class="tl-h">' + ((d.configurable && !d.readOnly) ? '<button class="tl-name" data-tl-set="1" title="设置小尾巴显示哪四项" data-ptds-ui-title="s280d98c0170a">' + name + (d.settingsIcon || '') + '</button>' : '<span class="tl-name">' + name + '</span>') + '<span class="sub2" title="' + esc(status) + '">' + esc(status) + '</span>' + (d.readOnly ? '' : UI.pin(d.pinned, d.busy)) + close + '</div>' + (!d.readOnly && d.device === 'somaloop' ? UI.share().replace('class="ibtn"', 'class="tl-sharing"').replace('</button>', '<span>'+esc(UI.shareSummary(d.sharing))+'</span></button>') : '');
  };
  UI.bandValue = function (kind, value) { return value == null ? null : kind === "SKIN_TEMP" ? Number(value).toFixed(1) : String(Math.round(value)); };
  UI.body = function (d) {
    return '<div class="tl-g">' + d.tiles.map(function (z) {
      var value = z.kind ? UI.bandValue(z.kind, z.raw) : z.value;
      var empty = value == null || value === '—';
      return '<' + (d.readOnly ? 'div' : 'button type="button"') + ' class="tl-t' + (z.old ? ' old' : '') + '"' + (d.readOnly ? '' : ' data-tl-go="' + esc(z.code || '') + '"') + '><span class="tl-l">' + esc(z.label) + '</span><span>' + (empty ? '<span class="tl-v na">—</span>' : '<span class="tl-v">' + esc(value) + '</span><span class="tl-u">' + esc(z.unit) + '</span>') + '</span><span class="tl-a">' + esc(z.note) + '</span></' + (d.readOnly ? 'div' : 'button') + '>';
    }).join('') + '</div><div class="tl-f">' + esc(d.footer) + '</div>';
  };
  UI.html = function (d) { return d.device === "pillbox" ? UI.pillbox(d) : UI.header(d) + UI.body(d); };
  UI.visual = function (card) {
    var cs = getComputedStyle(card), visual = { width: card.getBoundingClientRect().width, height: card.getBoundingClientRect().height, pixelRatio: window.devicePixelRatio || 1, font: cs.fontFamily, size: cs.fontSize, line: String(parseFloat(cs.lineHeight) / parseFloat(cs.fontSize)), tokens: {} };
    ['--theme-surface-raised','--theme-text-primary','--theme-text-secondary','--theme-text-tertiary','--scale-type-meta','--primitive-border-hairline'].forEach(function (key) { visual.tokens[key] = cs.getPropertyValue(key).trim(); });
    var phone = card.querySelector('[data-phone-view]'); if (phone) visual.height = card.querySelector('.tl-f').getBoundingClientRect().bottom - card.getBoundingClientRect().top + parseFloat(cs.paddingBottom) + parseFloat(cs.borderBottomWidth);
    return visual;
  };
  UI.pillboxIcon = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true"><rect x="3" y="4" width="18" height="16" rx="4"/><path d="M3 12h18M12 4v16"/></svg>';
  UI.pillboxCss = '.pb-card .tl-name{margin-left:0;padding:0;gap:6px;border:0;cursor:default}.pb-card .tl-name b{font-size:15px}.pb-card .tl-h .sub2{font-size:12px}.pb-card .tl-h{gap:4px;margin-bottom:10px}.pb-card .tl-name svg{color:var(--theme-text-secondary)}.pb-card .pb-main{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:6px 0 4px}.pb-card .pb-battery{display:flex;align-items:center;gap:9px}.pb-card .pb-battery>svg{width:23px;height:23px;color:var(--theme-text-secondary)}.pb-card .pb-number{display:flex;align-items:baseline;font-variant-numeric:tabular-nums}.pb-card .pb-number .tl-v{font-size:26px}.pb-card .pb-label{font-size:12px;color:var(--theme-text-secondary)}.pb-card .pb-find{display:flex;align-items:center;gap:6px;font:inherit;font-size:13px;font-weight:600;color:var(--theme-text-primary);background:rgba(128,140,160,.1);border:1px solid rgba(128,140,160,.3);border-radius:10px;padding:10px;cursor:pointer;min-height:42px;white-space:nowrap}.pb-card .pb-find svg{width:16px;height:16px}.pb-card .pb-find:hover:enabled{background:rgba(128,140,160,.2)}.pb-card .pb-find:disabled{opacity:.52;cursor:default}.pb-card .pb-find:focus-visible{outline:2px solid var(--theme-text-primary);outline-offset:2px}.pb-card .tl-f{min-height:17px;margin-top:10px}';
  UI.css += UI.pillboxCss;
  UI.pillbox = function (d) {
    var connected=d.connected===true, value=connected&&typeof d.battery==='number'&&Number.isInteger(d.battery)&&d.battery>=0&&d.battery<=100?d.battery:null;
    var stamp=value!==null&&d.battery_at?new Date(d.battery_at*1000).toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'}):'';
    var note=d.message||(connected?(stamp?'最近更新：'+stamp:'尚未读取到电量'):'连接后可寻找药盒');
    var svg=function(s){return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'+s+'</svg>';};
    return UI.header(Object.assign({},d,{device:'pillbox',name:'我的药盒',icon:UI.pillboxIcon,status:connected?'已连接':'未连接'}))+
      '<div class="pb-main"><div class="pb-battery">'+svg('<rect x="2" y="7" width="17" height="10" rx="2"/><path d="M22 10v4"/>')+'<div><div class="pb-label" data-ptds-ui="s1c69b1aa723a">电量</div><div class="pb-number"><span class="tl-v'+(value===null?' na':'')+'">'+(value===null?'—':value)+'</span>'+(value===null?'':'<span class="tl-u">%</span>')+'</div></div></div><button type="button" class="pb-find" data-pillbox-find="1"'+(!connected||d.findBusy?' disabled':'')+'>'+svg('<path d="M8 8 4 11H2v2h2l4 3V8Zm4 1a5 5 0 0 1 0 6m4-9a9 9 0 0 1 0 12"/>')+'<span>'+(d.findBusy?'发送中…':'响铃寻找')+'</span></button></div><div class="tl-f" role="status" aria-live="polite">'+esc(note)+'</div>';
  };

  root.PTDSTail = UI;
})(typeof window !== 'undefined' ? window : globalThis);

// PTDS_TAIL_COMPONENT_END
/* PTDS 本机接入层：把原型的模拟方法换成本机进程的真实接口（异步请求，本机接口）。
   视图层不变；界面只渲染接口给的结果，不自己算。 */
(function () {
  'use strict';
  var readEpoch=0, pendingWrites=0;
  // PAGE_ASYNC_R06: asynchronous transport; no synchronous network fallback.
  var viewReads=new Map(), activeLegacyWrites=new Set();
  var VIEW_READ_CACHE_LIMIT=128;
  function pruneViewReads(){
    // Completed read cache only. In-flight requests and mounted read boundaries
    // keep their identity until completion; eviction never retries a mutation.
    readWaiters.forEach(function(w,path){
      if(!w.node.isConnected||!C||C.st.key!==w.key||viewRoute()!==w.route)readWaiters.delete(path);
    });
    var done=Array.from(viewReads.entries()).filter(function(pair){return !pair[1].promise&&!readWaiters.has(pair[0]);});
    done.sort(function(a,b){return (a[1].usedAt||a[1].at||0)-(b[1].usedAt||b[1].at||0);});
    done.slice(0,Math.max(0,done.length-VIEW_READ_CACHE_LIMIT)).forEach(function(pair){viewReads.delete(pair[0]);});
  }
  function viewRoute(){return C&&LIVE.refreshRoute?LIVE.refreshRoute():'';}
  function readFailure(path,entry){var e=entry&&entry.error||new Error('READ_PENDING');e.viewPending=true;e.path=path;e.loading=!!(entry&&entry.promise);return e;}
  function readCached(path) {
    pruneViewReads();
    var e=viewReads.get(path),key=C&&C.st.key,epoch=readEpoch,ttl=/^\/api\/batch\/list(?:\?|$)/.test(path)?1800:path==='/api/band'?2800:60000;
    if(e&&e.epoch===epoch&&e.value!==undefined&&Date.now()-e.at<ttl){e.usedAt=Date.now();return e.value;}
    if(e&&e.promise)throw readFailure(path,e);
    if(e&&e.error&&e.epoch===epoch)throw readFailure(path,e);
    e={epoch:epoch,key:key,usedAt:Date.now()};viewReads.set(path,e);
    e.promise=readView(path).then(function(value){
      if(viewReads.get(path)!==e)return;
      if(epoch!==readEpoch){viewReads.delete(path);return;}
      e.value=value;e.at=Date.now();
    }).catch(function(err){e.error=err;}).finally(function(){e.promise=null;flushReadBoundary(path);pruneViewReads();});
    throw readFailure(path,e);
  }
  var readWaiters=new Map();
  function flushReadBoundary(path){
    var w=readWaiters.get(path);if(!w)return;
    setTimeout(function(){
      if(readWaiters.get(path)!==w)return;
      readWaiters.delete(path);
      if(!C||C.st.key!==w.key||viewRoute()!==w.route||!w.node.isConnected)return;
      w.retry();
    },Math.max(0,(LIVE._interactionUntil||0)-Date.now())+20);
  }
  async function call(method,path,body,raw,headers) {
    var key=body&&body.key||C&&C.st.key,route=viewRoute(),writing=method!=='GET',token=key+'|'+path;
    var expectedInstance=C&&C.SNAPS[key]&&C.SNAPS[key].instance.instance_id;
    var entry=C&&C.st.entry,entryBound=/^\/api\/(?:torch|batch)\//.test(path),sp=LIVE.sp,subject=sp&&sp.subject,spToken=sp&&sp.token,memoryBound=/^\/api\/starling\/memory/.test(path);
    if(writing&&activeLegacyWrites.has(token)){var busy=new Error('WRITE_BUSY');busy.code='WRITE_BUSY';busy.detail='正在处理，请等待完成后再操作';throw busy;}
    if(writing){activeLegacyWrites.add(token);readEpoch++;if(LIVE._dataReadSession)LIVE._dataReadSession.invalidate();pendingWrites++;}
    var ctl=new AbortController(),timer=setTimeout(function(){ctl.abort();},writing?60000:20000);
    try {
      var h=Object.assign({'X-PTDS':'1'},raw?{}:{'Content-Type':'application/json'},headers||{});
      var response=await fetch(path,{method:method,headers:h,body:raw?body:body?JSON.stringify(body):null,cache:'no-store',signal:ctl.signal});
      var out=await response.json().catch(function(){throw Error('BAD_RESPONSE');});
      if(!response.ok){var err=new Error(out.error||'REQUEST_FAILED');err.code=out.error;err.detail=out.detail;throw err;}
      var confirmedReceipt=false;
      if(writing&&body&&body.response_view==='receipt-v1'){
        if(out.projection==='write-receipt/1'){
          LIVE.validateWriteReceipt(out,body,path,expectedInstance);LIVE.rememberWriteReceipt(key,out);confirmedReceipt=true;
        }else if(!out.snapshot){var missing=Error('WRITE_CONFIRMATION_INVALID');missing.code='WRITE_CONFIRMATION_INVALID';throw missing;}
      }
      // Responses remain bound to the original instance even if navigation changes.
      if(!confirmedReceipt&&out.snapshot&&key&&C.SNAPS[key]){
        if(!out.snapshot.instance||out.snapshot.instance.instance_id!==C.SNAPS[key].instance.instance_id)throw Error('SNAPSHOT_INSTANCE_MISMATCH');
        C.SNAPS[key]=out.snapshot;
      }
      if(!confirmedReceipt&&C&&(C.st.key!==key||viewRoute()!==route||(entryBound&&C.st.entry!==entry)||(memoryBound&&(LIVE.sp!==sp||(sp&&(sp.subject!==subject||sp.token!==spToken)))))){var stale=new Error('VIEW_CHANGED');stale.code='VIEW_CHANGED';stale.detail=writing?'操作已完成，请在原实例查看结果':'页面已切换';throw stale;}
      if(writing&&window.PTDS_COMPUTE)window.PTDS_COMPUTE.track(key,out);
      return out;
    } catch(err){
      if(!err.code)err.code=err.name==='AbortError'?'REQUEST_TIMEOUT':'SERVER_DOWN';
      if(writing&&!err.detail)err.detail='未收到操作确认，请刷新核对；不会自动重复提交';
      throw err;
    } finally {clearTimeout(timer);if(writing){activeLegacyWrites.delete(token);pendingWrites--;readEpoch++;if(LIVE._dataReadSession)LIVE._dataReadSession.invalidate();viewReads.clear();}}
  }
  /* 会等外部网络的请求（Oura）不能用同步请求：等待期间整页会卡住。这个版本不挡页面，结果回来再处理 */
  function callAsync(method, path, body) {
    var writing=method!=='GET',ctl=new AbortController(),timer=setTimeout(function(){ctl.abort();},writing?60000:20000);
    if(writing){readEpoch++;if(LIVE._dataReadSession)LIVE._dataReadSession.invalidate();pendingWrites++;}
    return fetch(path,{method:method,headers:{'X-PTDS':'1','Content-Type':'application/json'},body:body?JSON.stringify(body):null,signal:ctl.signal,cache:'no-store'})
      .then(function(r){return r.json().catch(function(){throw Error('BAD_RESPONSE');}).then(function(out){
        if(!r.ok){var err=new Error(out.error||'REQUEST_FAILED');err.code=out.error;err.detail=out.detail;throw err;}return out;
      });}).catch(function(err){
        if(!err.code)err.code=err.name==='AbortError'?'REQUEST_TIMEOUT':'SERVER_DOWN';
        if(writing&&!err.detail)err.detail='未收到操作确认，请刷新核对；不会自动重复提交';
        throw err;
      }).finally(function(){clearTimeout(timer);if(writing){pendingWrites--;readEpoch++;if(LIVE._dataReadSession)LIVE._dataReadSession.invalidate();viewReads.clear();}});
  }
  // Read-only view requests have a deadline; failures never imply empty data.
  function readView(path) {
    var controller=new AbortController(), timer=setTimeout(function(){controller.abort();},20000);
    var release=path.indexOf('/api/data/read?')===0&&LIVE._dataReadSession?LIVE._dataReadSession.track(controller,timer):function(){};
    var options={headers:{'X-PTDS':'1'},cache:'no-store',signal:controller.signal};
    if(path.indexOf('/api/data/read?')===0){
      var query=new URLSearchParams(path.slice(path.indexOf('?')+1)),id=query.get('preview_read');
      if(id){
        var preview=dataPreviewBodies.get(query.get('key'));
        if(!preview||String(preview.id)!==id){clearTimeout(timer);release();var changed=Error('DATA_VIEW_CHANGED');changed.code='DATA_VIEW_CHANGED';return Promise.reject(changed);}
        // Freeze the body before fetch; later navigation/sync cannot retarget it.
        options.method='POST';options.headers['Content-Type']='application/json';options.body=JSON.stringify({preview_receipts:preview.text});
        query.delete('preview_read');path='/api/data/read?'+query.toString();
      }
    }
    return fetch(path,options)
      .then(function(r){return r.json().then(function(value){
        if(!r.ok){var err=Error(value.error||'READ_UNAVAILABLE');err.code=value.error||'READ_UNAVAILABLE';err.detail=value.detail;throw err;}return value;
      });})
      .finally(function(){clearTimeout(timer);release();});
  }
  function rid() { return 'R-' + Date.now().toString(36) + '-' + Math.random().toString(36).slice(2, 8); }
  var C = null;
  var SRC_NAME = { DEVICE_GARMIN: 'Garmin', DEVICE_OURA: 'Oura', DEVICE_SOMALOOP: 'Somaloop 手环', DEVICE_QKEER: 'Qkeer', APPLE_HEALTH: '苹果健康', DEVICE_WITHINGS: 'Withings', DEVICE_CGM: '连续血糖', SYNTHETIC: '回放' };
  var DEVICE_FAMILIES = ['DEVICE_GARMIN', 'DEVICE_OURA', 'DEVICE_SOMALOOP', 'DEVICE_QKEER', 'PHONE_HEALTH'];
  var VITAL_ORDER = ['OURA_LOWEST_HR', 'OURA_RESTING_HR', 'OURA_HRV', 'OURA_TEMP_DEV', 'OURA_SPO2', 'OURA_SLEEP_SCORE', 'OURA_READINESS_SCORE', 'OURA_TOTAL_SLEEP', 'OURA_RESP_RATE', 'OURA_HR', 'OURA_STEPS', 'OURA_ACTIVITY_SCORE'];
  var UNIT_ZH = { score: '分', steps: '步', min: '分钟', bpm: '次/分' };
  /* 界面信息密度（产品负责人 2026-10-14 批准 R07）：只改显示，字典与存储不动 */
  var OPS = { LT: '<', LE: '≤', GT: '>', GE: '≥', '<': '<', '<=': '≤', '>': '>', '>=': '≥' };
  function hm(min) { min = Math.round(+min); var h = Math.floor(min / 60), m = min % 60; return h ? h + ' 小时' + (m ? ' ' + m + ' 分' : '') : m + ' 分钟'; }
  function clock(min) { min = ((Math.round(+min) % 1440) + 1440) % 1440; return ('0' + Math.floor(min / 60)).slice(-2) + ':' + ('0' + min % 60).slice(-2); }
  function human(code, v, unit, cmp) {
    if (v == null || v === '') return '无值';
    if (v === 'true' || v === true) return '有';  /* 是/否类指标显示成有/无（产品负责人 2026-10-14） */
    if (v === 'false' || v === false) return '无';
    var n = +v, u = unit || '';
    if (/_BEDTIME_(START|END)$/.test(code || '') && isFinite(n)) return clock(n);
    if (u === 'min' && /(SLEEP|IN_BED)/.test(code || '') && isFinite(n)) return hm(n);
    return (cmp ? (OPS[cmp] || cmp) : '') + v + (u ? ' ' + (UNIT_ZH[u] || u) : '');
  }
  function humanLabel(t) { return String(t || '').replace(/，距当天\s*0\s*点分钟/, ''); }
  function rank(code) { var i = VITAL_ORDER.indexOf(code); return i < 0 ? 99 : i; }
  function ms(item) { return item.observed_at ? Date.parse(item.observed_at) : item.observed_date ? Date.parse(item.observed_date + 'T12:00:00Z') : 0; }
  var LIVE = {
    readingHtml: function (size, state, detail) { return window.PTDS_READ_UI.html(size, state, detail); },
    call: call, readCached: readCached,
    human: human, humanLabel: humanLabel,
    /* 本实例自己录入、导入的数据默认性质（产品负责人 2026-10-14 09:18：演示病例放开收 REAL 给体验腕带，自己的数据仍是合成） */
    realNature: function () { var i = (C.S() || {}).instance || {}; return (i.default_nature || ((i.accept || []).indexOf('REAL') >= 0 ? 'REAL' : 'SYNTHETIC')) === 'REAL'; },
    /* 星轨"我的体征"读模型：来自星轨快照 vitals（最近读数、是否最新由星轨判断），界面只读 */
    liveState: function (snap, family) {
      var items = ((snap.vitals || {}).items || []).filter(function (i) { return DEVICE_FAMILIES.indexOf(i.family) >= 0 && (!family || i.family === family); });
      var sources = items.map(function (i) {
        var series = i.series.map(function (s, k) { return { v: s.v, t: Date.parse(s.t.length === 10 ? s.t + 'T12:00:00Z' : s.t), id: i.code + '#' + k }; }).slice(-12);
        return { id: i.code, name: SRC_NAME[i.source_kind] || i.source_kind, metric: i.label_zh.replace(/（.*）$/, ''), unit: UNIT_ZH[i.unit] || i.unit, connected: true,
          last: { v: i.value, t: ms(i), id: i.observation_id + '@' + i.revision, delivered: true }, series: series, fresh: !!i.fresh, item: i };
      });
      sources.sort(function (a, b) { return rank(a.id) - rank(b.id); });
      var latest = sources.reduce(function (m, s) { return Math.max(m, s.last.t); }, 0);
      return { updated_at: (snap.h1 && snap.h1.last_sync && Date.parse(snap.h1.last_sync.at)) || latest || null,
        fresh: sources.some(function (s) { return s.fresh; }), sources: sources, updates: [] };
    },
    /* 数据近况"近期数源"：按来源归并本机快照里的观测（设备按来源、录入按批次时点） */
    recentSources: function (snap) {
      var groups = {}, GRP = { DEVICE_GARMIN: 'wearable', DEVICE_OURA: 'wearable', DEVICE_SOMALOOP: 'wearable', DEVICE_QKEER: 'wearable', DEVICE_WITHINGS: 'wearable', DEVICE_CGM: 'wearable', APPLE_HEALTH: 'phone', MANUAL: 'manual' };
      var LAB = { MANUAL: '手工录入', TABLE: '表格导入', OCR_LLM: '化验单识别', TEXT_LLM: '文本抽取', SYNTHETIC: '合成' };
      (snap.timeline || []).forEach(function (o) {
        var dev = !!SRC_NAME[o.source_kind] && o.source_kind !== 'SYNTHETIC';
        var k = dev ? o.source_kind : o.source_kind + '|' + (o.tp || '时间未知'), g = groups[k];
        var t = o.temporal.observed_at ? Date.parse(o.temporal.observed_at) : o.tp ? Date.parse(o.tp + 'T12:00:00Z') : 0;
        if (!g) g = groups[k] = { dev: dev, kind: o.source_kind, tp: o.tp, n: 0, t: 0 };
        g.n += 1; g.t = Math.max(g.t, t);
      });
      return Object.keys(groups).map(function (k) { return groups[k]; }).sort(function (a, b) { return b.t - a.t; }).map(function (g) {
        return g.dev ? { name: SRC_NAME[g.kind], grp: GRP[g.kind] || 'wearable', ts: g.t || null, note: g.n + ' 条读数' }
          : { sourceKind: g.kind, name: (LAB[g.kind] || g.kind) + ' · ' + (g.tp || '时间未知'), grp: GRP[g.kind] || 'file', when: g.tp || '—', note: g.n + ' 项' };
      });
    },
    /* 星炬"接入设备"（真实实例）：状态读本机进程的来源登记，接入走 Oura 官方授权页 */
    /* 体验腕带（Somaloop，产品负责人 2026-10-14）：Mac 上的“PTDS 腕带桥”直连腕带，读数推到这里；只在 sJIA 演示环境，标“体验设备”，不记姓名。
       09:22：接入设备页只放一行连接状态 + 立即同步（和 Oura 那行同一形状），不放读数、不画图；读数在 Somaloop 小尾巴里（09:23 不画走势）。 */
    desktopPinHtml: function () {
      return window.PTDSTail.pin(false, LIVE._desktopOpening);
    },
    desktopPinBind: function (card, t, tiles) {
      var button = card.querySelector('[data-desktop-pin]'); if (!button) return;
      button.onclick = function () {
        if (LIVE._desktopOpening) return;
        LIVE._desktopOpening = true; button.disabled = true;
        C.toast('正在打开跨应用置顶小窗…');
        fetch('/api/desktop-tail/open', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-PTDS': '1' },
          body: JSON.stringify({ key: C.st.key, device: t.id, name: t.name, source: t.src,
            theme: document.documentElement.dataset.theme, tiles: tiles, footer: t.chain, visual: window.PTDSTail.visual(card) }) }).then(function (r) {
            return r.json().then(function (j) { if (!r.ok) throw new Error(r.status === 404 ? '请重启 PTDS 本机服务以加载置顶功能' : j.detail || '置顶窗口未打开'); return j; });
          }).then(function (j) { C.toast(j.existing ? '已请求将现有读数窗口重新置顶' : '已打开独立读数窗口，可用图钉取消置顶'); })
          .catch(function (e) { C.toast('无法打开置顶小窗：' + e.message); })
          .finally(function () { LIVE._desktopOpening = false; button.disabled = false; });
      };
    },
    phoneForm: function () {
      var p=C.PROD.cluster.phone_tail;
      return {object:p.object,channel:p.channel,card:p.resource,events:p.codes.slice(),method:'read',level:'data',view:'dynamic',duration:p.duration};
    },
    phoneSpec: function () {
      var t=LIVE.BAND_TAIL,card=document.getElementById('tl-somaloop-card');
      return {key:C.st.key,device:t.id,name:t.name,theme:document.documentElement.dataset.theme,footer:t.chain,
        tiles:['HR','SPO2','SKIN_TEMP','HRV'].map(function(k){return {code:'SOMALOOP_'+k,label:t.label[k],unit:t.unit[k],when:'instant'};}),
        visual:card?window.PTDSTail.visual(card):undefined};
    },
    phoneShare: async function (spec) {
      LIVE._phoneSpec=spec||LIVE.phoneSpec();
      try {
        var s=(await call('GET','/api/phone-tail/status')),P=window.__ptds;LIVE._phoneDeployment=s.deployment_mode||'lan';LIVE._phoneMaxViewers=s.max_viewers||1;
        if(s.owner_key && s.owner_key !== C.st.key) {
          if(!C.SNAPS[s.owner_key]) C.SNAPS[s.owner_key]=(await call('GET','/api/state?key='+encodeURIComponent(s.owner_key)));
          C.st.key=s.owner_key;LIVE._phoneSpec=Object.assign({},LIVE._phoneSpec,{key:s.owner_key});
        }
        C.closeDrawer();
        if(s.grant&&s.grant.status==='ACTIVE') { LIVE.phoneTailOpen(Object.assign({},LIVE._phoneSpec,{key:s.key,grant_id:s.grant.id})); }
        else if(s.running&&s.grant) { LIVE.phoneTailOpen(Object.assign({},LIVE._phoneSpec,{key:s.key,grant_id:s.grant.id})); }
        else if(!s.configured) { LIVE.phoneTailOpen(LIVE._phoneSpec); }
        else { P.st.gform=LIVE.phoneForm();P.goCluster('edit'); }
      } catch(e) { if(e&&(e.viewPending||e.code==='VIEW_CHANGED'))throw e; C.toast(e.message); }
    },
    renderPhoneGrantEdit: function () {
      var p=C.PROD.cluster.phone_tail,esc=C.esc,mode=LIVE._phoneDeployment||'lan';
      document.getElementById('view').innerHTML=C.pgh('新建授权')+'<div class="split"><section class="panel" data-sem="SEM-25">'+
        '<div class="fld"><span data-ptds-ui="s53f92c063963">对象</span><div data-ptds-ui="s9b272b49c377">经 Mac 本机批准的临时手机浏览器</div></div>'+
        '<div class="fld"><span data-ptds-ui="sae72b532f4b8">范围</span><div>'+esc(p.scope_zh)+'</div></div>'+
        '<div class="fld"><span data-ptds-ui="s05b36669c4ad">用途</span><div>'+esc(p.purpose)+'</div></div>'+
        '<div class="fld"><span data-ptds-ui="s978cbca6265d">权限</span><div data-ptds-ui="sde22f17114ee">只读 · 不允许修改数据或操作设备</div></div>'+
        '<div class="fld"><span data-ptds-ui="sb44553ef95da">手机数量</span><div data-ptds-inline><!--ptds-ui:seea3b2d2f03b-->最多 <!--/ptds-ui-->'+(LIVE._phoneMaxViewers||1)+' 台 · 每台分别在 Mac 确认</div></div>'+
        '<div class="fld"><span data-ptds-ui="scea526c6744c">时效</span><div data-ptds-ui="sbd61506de738">1 小时 · 可随时从授权详情撤回</div></div>'+
        '<div class="foot"><button class="btn" id="g-save">'+C.ic('shield-check')+'确认授权</button><button class="btn2" id="phone-grant-cancel" data-ptds-ui="s2cd0f3be8738">取消</button></div><p id="phone-grant-error" role="status"></p></section>'+
        '<div class="seeas"><div class="who">'+C.ic('eye')+'手机会看到什么</div><p data-ptds-ui="s4135cc6a5601">Somaloop 的四项近期读数及各自的实际观测时间。确认授权后生成二维码，手机申请后仍需在 Mac 核对号码。</p><p>'+ (mode!=='lan'?'本次访问通过 Cloudflare 等受控 HTTPS 服务转发，服务商会处理配对请求、会话及四项读数。':'') +'隐藏小尾巴或关闭配对抽屉不停止分享。'+((LIVE._phoneMaxViewers||1)>1?'手机“结束查看”只退出本机；Mac撤回授权会停止全部手机。':'手机“结束查看”会同时结束这项临时授权。')+'</p></div></div>';
      document.getElementById('phone-grant-cancel').onclick=function(){C.st.gform=null;window.__ptds.goCluster('rules');};
      document.getElementById('g-save').onclick=LIVE.action(async function(){
        this.disabled=true;
        var spec=LIVE._phoneSpec&&LIVE._phoneSpec.key===C.st.key?LIVE._phoneSpec:LIVE.phoneSpec();
        try {
          var status=(await call('GET','/api/phone-tail/status'));
          if(((status.deployment_mode||'lan')!==mode||(status.max_viewers||1)!==(LIVE._phoneMaxViewers||1))){LIVE._phoneDeployment=status.deployment_mode||'lan';LIVE._phoneMaxViewers=status.max_viewers||1;LIVE.renderPhoneGrantEdit();document.getElementById('phone-grant-error').textContent='连接方式已变化，请重新核对后确认授权。';return;}
          if(!status.configured){document.getElementById('phone-grant-error').textContent='请先完成手机连接设置，再确认授权。';this.disabled=false;LIVE.phoneTailOpen(spec);return;}
          var g=(await C.MockCluster.create(LIVE.phoneForm()));C.st.gform=null;C.st.gid=g.id;spec=Object.assign({},spec,{grant_id:g.id});
          window.__ptds.goCluster('grant');LIVE.phoneTailOpen(spec,true);
        } catch(e) { if(e&&(e.viewPending||e.code==='VIEW_CHANGED'))throw e;
          var error=document.getElementById('phone-grant-error');if(error)error.textContent=e.message.replace(/^PHONE_VIEW_UNAVAILABLE[：:]\s*/, '');this.disabled=false;
          if(e.message.indexOf('PHONE_VIEW_UNAVAILABLE')!==-1){
            try{var latest=(await call('GET','/api/phone-tail/status'));if(!latest.configured)LIVE.phoneTailOpen(spec);}catch(ignored){ if(ignored&&(ignored.viewPending||ignored.code==='VIEW_CHANGED'))throw ignored;}
          }
        }
      });
    },
    phoneGrantManage: function (g) { LIVE.phoneTailOpen(Object.assign({},LIVE.phoneSpec(),{grant_id:g.id})); },
    phoneNativeEntry: function () {
      var h=location.hash;if(h.indexOf('#phone-tail=')!==0)return;
      var key;try{key=decodeURIComponent(h.slice(12));}catch(e){ if(e&&(e.viewPending||e.code==='VIEW_CHANGED'))throw e;return;}
      if(!C.SNAPS[key])return;
      history.replaceState(null,'',location.pathname+location.search);C.st.key=key;LIVE.phoneShare(LIVE.phoneSpec());
    },
    phoneTailOpen: function (spec, autoStart) {
      C.closeDrawer(); C.st.drawer = 'live';
      var setupOnly=!spec.grant_id;
      var el = document.createElement('aside'); el.id = 'drawer'; el.className = 'drawer phone-tail-drawer';
      el.setAttribute('role','dialog'); el.setAttribute('aria-modal','false'); el.setAttribute('aria-label','手机查看小尾巴');
      el.innerHTML = '<style>#drawer.phone-tail-drawer [hidden]{display:none!important}</style><div class="dh"><span>'+(setupOnly?'手机分享 · 首次设置':'手机查看小尾巴')+'</span><button class="ibtn" id="phone-close" aria-label="关闭" data-ptds-ui-aria-label="s3fd47edce45b">'+C.ic('x')+'</button></div><div class="db" style="display:block">'+
        '<p id="phone-network-hint" data-ptds-ui="s668665929303">手机连接同一 Wi-Fi，扫码后在这里确认。手机仅查看四项读数；Mac 继续后台采集。</p><div id="phone-message" role="status" aria-live="polite"></div>'+
        '<div id="phone-connect" hidden><img id="phone-qr" alt="手机查看配对二维码" width="220" height="220" style="display:block;background:white;padding:16px;border-radius:10px;max-width:100%;height:auto"><p data-ptds-ui="s85fa1b87e0fc">也可在手机输入地址及配对码：</p><div id="phone-url" style="overflow-wrap:anywhere"></div><p data-ptds-inline><!--ptds-ui:se1c88d9cf8e3-->配对码：<!--/ptds-ui--><b id="phone-code" style="font-size:22px;letter-spacing:.12em;font-variant-numeric:tabular-nums"></b></p><p id="phone-ttl" class="sub2"></p></div>'+
        '<section id="phone-devices" hidden aria-label="手机连接情况" style="margin:16px 0"><p id="phone-device-count" role="status" aria-live="polite"></p><div id="phone-device-list"></div><p class="sub2" data-ptds-ui="s8fdea6a8168a">在线表示最近12秒内成功读取；已批准不代表在线。</p></section>'+
        '<div id="phone-pending" hidden><p data-ptds-ui="s2515cbcdaa8b">有手机申请查看。请核对手机显示的号码：</p><b id="phone-confirmation" style="font-size:26px;letter-spacing:.15em"></b><p><button class="btn" id="phone-approve" data-ptds-ui="s0c2223d7d4c9">确认这部手机</button></p></div>'+
        '<p id="phone-paired" hidden></p><div style="display:flex;gap:10px;flex-wrap:wrap"><button class="btn" id="phone-start" data-ptds-ui="sc85ef7328f09">生成配对码</button><button class="btn2" id="phone-invite" hidden data-ptds-ui="s1a96ee4864f5">添加手机</button><button class="btn2" id="phone-stop" hidden data-ptds-ui="sa4d1dcf81735">撤回授权并停止分享</button></div>'+
        '<div id="phone-setup-actions" hidden><button class="btn2" id="phone-recheck" data-ptds-ui="s80764ec981a7">重新检查设置</button> <button class="btn" id="phone-authorize" hidden data-ptds-ui="s024f6fb9fa95">继续授权</button></div>'+
        '<button class="btn2" id="phone-reenter" hidden data-ptds-ui="s6a84698a4758">重新授权</button>'+
        '<details id="phone-help" style="margin-top:20px"><summary data-ptds-ui="s22c6747abd74">首次连接设置</summary><div id="phone-help-lan"><ol>'+
        '<li data-ptds-inline><!--ptds-ui:s9be1ee80acd3-->Mac 与手机连接同一 Wi-Fi。在 Mac 的网络设置中确认内网 IPv4 地址。<!--/ptds-ui--></li>'+
        '<li data-ptds-inline><!--ptds-ui:s92a5c9293598-->准备包含该地址的 HTTPS 证书及对应私钥；使用专用本地证书时，由本人在手机安装并信任根证书。私钥留在 Mac。<!--/ptds-ui--></li>'+
        '<li data-ptds-inline><!--ptds-ui:s1e63926880be-->在 PTDS 实际使用的配置中填写内网地址、HTTPS 地址、证书文件和私钥文件，再按原方式重启 PTDS。<!--/ptds-ui--></li>'+
        '<li data-ptds-inline><!--ptds-ui:s689d52f16941-->返回这里重新检查，再确认授权、扫码和核对号码。配置字段齐备不代表手机已信任证书。<!--/ptds-ui--></li></ol>'+
        '<p class="sub2" data-ptds-ui="s5aed8117555c">“重新检查设置”只检查当前运行程序，不会改写配置或重启服务。未配置时不会创建授权或开放手机端口。</p>'+
        '<details><summary data-ptds-ui="s8e2907b53bf5">配置字段示例</summary><pre style="white-space:pre-wrap;overflow-wrap:anywhere">'+C.esc(JSON.stringify({phone_tail:{bind_host:'Mac内网IPv4',port:8791,public_origin:'https://Mac内网IPv4:8791',cert_file:'/绝对路径/server.crt',key_file:'/绝对路径/server.key'}},null,2))+'</pre><p class="sub2" data-ptds-ui="s2fd1ada5e1f6">替换示例中的地址和路径，只合并 phone_tail 段，保留其他配置。完整证书步骤见随附的《手机小尾巴首次配置与使用》。</p></details>'+
        '<p data-ptds-ui="sb3033738f4bd">访客网络隔离可能阻止访问。关闭本抽屉不会停止已批准的分享。</p></div>'+ 
        '<div id="phone-help-tunnel" hidden><p data-ptds-ui="s3a942ba0c7c3">手机通过公开 HTTPS 地址查看，不需要安装本地根证书或 App。请使用本次生成的准确地址，仍需在 Mac 核对号码并批准。</p>'+ 
        '<p data-ptds-ui="sd41940149097">本机证书只供转发程序核验网关身份，不安装到手机。连接经服务商处理，不是手机到 Mac 的端到端加密。</p>'+ 
        '<p data-ptds-ui="s89ecaaabd78f">由部署人员按 R03 指南配置专用回环网关；不要转发主产品端口。隧道地址变化后结束旧授权，重新建立分享。</p>'+ 
        '<p data-ptds-ui="s509198a88f15">关闭本抽屉不会停止分享；请从正式授权详情撤回。连接参数齐备不代表公网入口已通过验证。</p></div></details></div>';
      document.body.appendChild(el);
      var timer=null,busy=false,last=null,closed=false,queued=null,operationError='',find=function(id){return el.querySelector('#'+id);};
      function alive(){return !closed&&el.isConnected;}
      find('phone-start').disabled=true;
      if(setupOnly){find('phone-start').hidden=true;find('phone-setup-actions').hidden=false;find('phone-help').open=true;find('phone-message').innerHTML=LIVE.readingHtml('inline');}
      async function api(action,body){var ctl=new AbortController(),limit=setTimeout(function(){ctl.abort();},action==='start'?90000:10000);try{var r=await fetch('/api/phone-tail/'+action,{method:body?'POST':'GET',headers:{'Content-Type':'application/json','X-PTDS':'1'},body:body?JSON.stringify(body):undefined,cache:'no-store',signal:ctl.signal});var j=await r.json();if(!r.ok)throw new Error(j.detail||(r.status===404?'请重启 PTDS 本机服务加载手机查看':'操作未完成'));return j;}finally{clearTimeout(limit);}}
      function paint(s){
        var relayed=!!(s.deployment_mode&&s.deployment_mode!=='lan');find('phone-help-lan').hidden=relayed;find('phone-help-tunnel').hidden=!relayed;
        find('phone-network-hint').textContent=s.deployment_mode&&s.deployment_mode!=='lan'?'本次经受控 HTTPS 服务转发。扫码后仍需在 Mac 确认；最多 '+(s.max_viewers||1)+' 台手机分别确认后查看四项读数。':'手机连接同一 Wi-Fi，扫码后在这里确认。手机仅查看四项读数；Mac 继续后台采集。';
        if(setupOnly){
          last=s;['phone-start','phone-stop','phone-connect','phone-pending','phone-paired'].forEach(function(id){find(id).hidden=true;});
          find('phone-setup-actions').hidden=false;find('phone-help').open=true;
          var active=s.grant&&s.grant.status==='ACTIVE';find('phone-authorize').hidden=!s.configured&&!active;
          find('phone-authorize').textContent=active?'查看当前授权':'继续授权';
          find('phone-message').textContent=active?'已有手机授权，可返回详情管理或撤回。':s.configured?'加密参数已填写。继续确认授权后才能生成配对码；浏览器须能验证访问证书。':s.detail||'手机分享尚未完成首次设置。';
          return;
        }
        find('phone-invite').hidden=!(s.can_invite&&!s.pair_url);
        var matches=s.grant&&s.grant.id===spec.grant_id&&s.key===spec.key,active=s.grant&&s.grant.status==='ACTIVE',ending=s.running&&!active;
        if(!matches)s=Object.assign({},s,{pair_url:null,pair_code:null,pending:null,paired:false,qr:null,devices:[],can_invite:false});last=s;
        find('phone-start').hidden=!matches||!active||s.running;find('phone-stop').hidden=!matches||!active;find('phone-start').disabled=!s.configured||!matches||!active;
        find('phone-connect').hidden=!s.pair_url;find('phone-pending').hidden=!s.pending;find('phone-paired').hidden=!s.paired;
        find('phone-reenter').hidden=!!(matches&&active);find('phone-reenter').disabled=!!ending;
        find('phone-reenter').textContent=ending?'正在结束上一项分享…':active?'查看当前授权':'重新授权';
        find('phone-message').textContent=operationError|| (ending?'已撤回授权，正在结束上一项分享；完成后可重新授权。':!matches?(active?'当前授权已切换，请查看当前授权。':'数据分享已结束，可重新授权。'):!active?'数据分享已结束，可重新授权。':!s.configured?s.detail:(s.running?(s.pair_url?'配对等待中':s.pending?'请核对手机上的号码':s.paired?'手机已获准查看':'本次配对或查看已结束，请停止后重新开启'):'尚未开启手机查看'));
        if(s.pair_url){find('phone-qr').hidden=!s.qr;if(s.qr&&find('phone-qr').getAttribute('src')!==s.qr)find('phone-qr').src=s.qr;find('phone-url').textContent=s.entry_url;find('phone-code').textContent=s.pair_code;find('phone-ttl').textContent='配对码剩余 '+s.pair_seconds+' 秒';}else{find('phone-qr').removeAttribute('src');find('phone-code').textContent='';}
        find('phone-invite').hidden=!(matches&&active&&s.can_invite&&!s.pair_url);
        var devices=matches&&active&&Array.isArray(s.devices)?s.devices:null;
        find('phone-devices').hidden=!devices;
        if(devices){
          find('phone-pending').hidden=true;find('phone-paired').hidden=true;
          find('phone-device-count').textContent='已批准 '+(s.approved_count||0)+' / '+(s.max_viewers||1)+' 台 · 在线 '+(s.online_count||0)+' 台 · 待确认 '+(s.pending_count||0)+' 台';
          var deviceHtml=devices.map(function(d){
            var label={pending:'待确认',online:'在线',waiting:'已批准 · 等待首次读取',offline:'已断线'}[d.state]||'状态未知';
            var ago=d.last_read_seconds==null?'尚未读取':d.last_read_seconds<60?d.last_read_seconds+'秒前读取':Math.floor(d.last_read_seconds/60)+'分钟前读取';
            return '<div style="padding:10px 0;border-bottom:1px solid var(--theme-line-control);display:flex;align-items:center;gap:8px;flex-wrap:wrap"><span style="flex:1" data-ptds-inline><!--ptds-ui:s2e07333c8c74-->手机 <!--/ptds-ui-->'+C.esc(d.confirmation)+' · '+label+'<br><span class="sub2">'+ago+'</span></span>'+(!d.approved?'<button class="btn2" data-phone-confirm="'+C.esc(d.confirmation)+'">批准</button>':'')+'<button class="btn2" data-phone-remove="'+C.esc(d.id)+'">'+(d.approved?'移除':'拒绝')+'</button></div>';
          }).join('')||'<p class="sub2" data-ptds-ui="s9e5441a3e556">暂无手机连接，扫码后将在这里显示待确认号码。</p>';
          if(find('phone-device-list').innerHTML!==deviceHtml)find('phone-device-list').innerHTML=deviceHtml;
        }
        find('phone-confirmation').textContent=s.pending||'';if(s.paired)find('phone-paired').textContent=((s.max_viewers||1)>1?'已批准 '+s.approved_count+' / '+s.max_viewers+' 台 · 待确认 '+s.pending_count+' 台 · ':'只读查看中 · ')+'剩余约 '+Math.ceil(s.session_seconds/60)+' 分钟';if(!s.configured)find('phone-help').open=true;
      }
      // A just-confirmed grant is validated by /start, never replaced or blocked by an older aggregate status.
      async function refresh(){if(!alive()||busy)return;busy=true;try{var s=await api('status');if(!alive())return;paint(s);if(autoStart){autoStart=false;queued=['start',spec];}}catch(e){ if(e&&(e.viewPending||e.code==='VIEW_CHANGED'))throw e;if(alive())find('phone-message').textContent=operationError||e.message;}finally{busy=false;if(queued&&alive()){var next=queued;queued=null;act(next[0],next[1]);}else if(alive())timer=setTimeout(refresh,2000);}}
      async function act(action,body){if(!alive())return;if(busy){queued=[action,body];return;}clearTimeout(timer);busy=true;operationError='';find('phone-start').disabled=true;find('phone-approve').disabled=true;find('phone-stop').disabled=true;find('phone-message').textContent='正在处理…';try{var s=await api(action,body);if(alive())paint(s);}catch(e){ if(e&&(e.viewPending||e.code==='VIEW_CHANGED'))throw e;if(alive()){operationError=e.message;find('phone-message').textContent=operationError;try{var s=await api('status');if(alive())paint(s);}catch(ignored){ if(ignored&&(ignored.viewPending||ignored.code==='VIEW_CHANGED'))throw ignored;}}}finally{busy=false;if(alive()){if(last)paint(last);find('phone-approve').disabled=false;find('phone-stop').disabled=false;timer=setTimeout(refresh,2000);}}}
      find('phone-recheck').onclick=function(){clearTimeout(timer);refresh();};find('phone-authorize').onclick=function(){close();LIVE.phoneShare(spec);};
      find('phone-reenter').onclick=function(){if(!alive()||this.disabled)return;close();LIVE.phoneShare(LIVE.phoneSpec());};
      find('phone-device-list').onclick=function(e){
        if(busy)return;
        var button=e.target.closest('button');if(!button)return;
        if(button.dataset.phoneConfirm)act('approve',{confirmation:button.dataset.phoneConfirm,key:spec.key,grant_id:spec.grant_id});
        else if(button.dataset.phoneRemove)act('remove-device',{device_id:button.dataset.phoneRemove,key:spec.key,grant_id:spec.grant_id});
      };
      find('phone-invite').onclick=function(){act('invite',{key:spec.key,grant_id:spec.grant_id});};
      find('phone-start').onclick=function(){act('start',spec);};find('phone-approve').onclick=function(){if(last&&last.pending)act('approve',{confirmation:last.pending,key:spec.key,grant_id:spec.grant_id});};find('phone-stop').onclick=function(){act('stop',{key:spec.key,grant_id:spec.grant_id});};
      function close(){closed=true;clearTimeout(timer);el.remove();C.st.drawer=null;var entry=document.querySelector('[data-tl-share]');if(entry)entry.focus();}
      find('phone-close').onclick=LIVE.action(close);el.addEventListener('keydown',function(e){if(e.key==='Escape'){e.preventDefault();close();}});find('phone-close').focus();refresh();
    },
    bandGet: function () { var d; try { d = readCached('/api/band'); } catch (err) { if(err&&(err.viewPending||err.code==='VIEW_CHANGED'))throw err; d = null; } return d; },
    bandHhmm: function (x) { var d = new Date(x * 1000), z = function (n) { return (n < 10 ? '0' : '') + n; }; return z(d.getHours()) + ':' + z(d.getMinutes()); },
    bandState: function (d) {
      var state = (d && d.status) || {};
      return state.alive && state.connection === 'ready' ? '已连接' : '未连接';
    },
    bandBind: function () {
      var b = document.getElementById('band-sync');
      if (b) b.onclick = LIVE.action(async function () {
        try { (await call('POST', '/api/band/sync', {})); C.toast('已请腕带桥马上读一次（读数本来就实时推送，腕带桥每 5 秒来看一次）'); } catch (err) { if(err&&(err.viewPending||err.code==='VIEW_CHANGED'))throw err; C.toast('没请成：' + LIVE.saveErr(err)); }
        var s = document.getElementById('band-state'); if (s) s.textContent = LIVE.bandState(LIVE.bandGet());
      });
      clearTimeout(LIVE._bandT);
      LIVE._bandT = setTimeout(function tick() {
        if (C.st.tview !== 'connect' || C.S().instance.kind !== 'DEMO') return;
        var s = document.getElementById('band-state'); if (!s) return;
        try{s.textContent=LIVE.bandState(LIVE.bandGet());}catch(e){s.textContent=e.loading?'正在更新…':'连接状态暂不可用';} LIVE._bandT=setTimeout(tick,3000);
      }, 3000);
    },
    renderConnect: function () {
      // Legacy links now enter the same device catalogue instead of a mixed-device page.
      C.st.srcGroup = 'wearable'; C.st.tview = 'srcgroup';
      return LIVE.renderSourceGroup();
    },
    /* 证据图谱（真实）：从一条结论一路追到计算、数据版本、原件，以及之后谁经哪个授权用过；下方是各账本的事件轨迹 */
    GRAPH_CSS: '.xh-tabs{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}.xh-t{display:grid;grid-template-columns:auto auto 1fr;gap:2px 8px;align-items:center;text-align:left;padding:12px 14px;border-radius:12px;border:var(--primitive-border-hairline) solid var(--theme-line-hairline);background:transparent;color:var(--theme-text-secondary);font:inherit;cursor:pointer}' +
      '.xh-t .ic,.xh-t svg{justify-self:end;color:var(--theme-text-tertiary)}.xh-t .sub2{grid-column:1/-1}.xh-t .n{color:var(--theme-text-tertiary)}.xh-t b{color:var(--theme-text-primary)}.xh-t:hover{border-color:var(--theme-line-control)}.xh-t[aria-expanded="true"]{border-color:var(--theme-text-primary);background:var(--component-sidebar-selBg)}.xh-body{margin-top:14px}' +
      '.xh-r{display:grid;grid-template-columns:110px 110px 1.3fr 1.1fr 2.4fr 80px;gap:12px;padding:9px 0;align-items:start}.xh-rd{border-bottom:var(--primitive-border-hairline) solid var(--theme-line-hairline)}.xh-rd summary{list-style:none;cursor:pointer}.xh-rd summary::-webkit-details-marker{display:none}.xh-r.hd{color:var(--theme-text-tertiary);font-size:var(--scale-type-meta);border-bottom:var(--primitive-border-hairline) solid var(--theme-line-hairline)}.xh-more{padding:0 0 10px}' +
      '.eg-chain{display:grid;grid-template-columns:minmax(0,1fr) auto minmax(0,1fr);gap:var(--primitive-space-3);align-items:stretch}' +
      '.eg-arrow{align-self:center;color:var(--theme-text-tertiary)}' +
      '.eg-tbl{display:grid;grid-template-columns:minmax(0,1.2fr) minmax(0,1.3fr) minmax(0,1fr);gap:var(--primitive-space-2) var(--primitive-space-4);align-items:start}' +
      '.eg-tbl>.h{color:var(--theme-text-tertiary);font-size:var(--scale-type-meta)}' +
      '.eg-tbl>div{min-width:0;overflow-wrap:anywhere;padding-bottom:var(--primitive-space-2);border-bottom:var(--primitive-border-hairline) solid var(--theme-line-hairline)}' +
      '.eg-metric{font-size:var(--scale-type-title)}.eg-ok{color:var(--theme-text-primary)}' +
      '.eg-ev{display:grid;grid-template-columns:4em 6em minmax(0,1fr) auto;gap:var(--primitive-space-3);padding:var(--primitive-space-2) 0;border-bottom:var(--primitive-border-hairline) solid var(--theme-line-hairline);align-items:baseline}' +
      '.eg-ev>span{min-width:0;overflow-wrap:anywhere}' +
      '@media (max-width:720px){.eg-chain{grid-template-columns:1fr}.eg-arrow{display:none}.eg-tbl{grid-template-columns:1fr}.eg-ev{grid-template-columns:1fr}}',
    /* 知识图谱：把账本里的"东西"（来源、原件、指标、状态卡、结论、提醒、授权、对象）画成点，账本里写着的关系画成边。
       只读：点和边都来自 /api/graph/kg，前端只负责排布（按类别从左到右，力导向松开）、高亮和拖动。 */
    KG_KIND: { source: ['数据源', '#5b8def', 0], document: ['原件', '#8d7be0', 1], indicator: ['指标', '#3aa58f', 2], store: ['位点库', '#3aa58f', 2],
      card: ['状态卡', '#e0973b', 3], conclusion: ['结论', '#d9644a', 4], alert: ['提醒', '#d9644a', 5], channel: ['通道', '#9a9a9a', 6],
      grant: ['授权', '#b569b8', 5], party: ['对象', '#7f8c99', 6] },
    KG_CSS: '.kg-wrap{display:grid;grid-template-columns:minmax(0,1fr) 260px;gap:var(--primitive-space-3);align-items:start}' +
      '.kg-svg{display:block;width:100%;height:auto;touch-action:none;user-select:none;border:var(--primitive-border-hairline) solid var(--theme-line-hairline);border-radius:8px;background:var(--theme-surface-sunken)}' +
      '.kg-e{fill:none;stroke:var(--theme-text-tertiary);stroke-width:1.1;opacity:.55}.kg-e.on{stroke:var(--theme-text-primary);stroke-width:1.8;opacity:1}.kg-e.off{opacity:.08}' +
      '.kg-el{font-size:10.5px;fill:var(--theme-text-secondary);paint-order:stroke;stroke:var(--theme-surface-sunken);stroke-width:3px}' +
      '.kg-n{cursor:pointer}.kg-n circle{stroke:var(--theme-surface-raised);stroke-width:2}.kg-n.sel circle{stroke:var(--theme-text-primary);stroke-width:3}.kg-n.off{opacity:.15}' +
      '.kg-n text{font-size:11.5px;fill:var(--theme-text-primary);paint-order:stroke;stroke:var(--theme-surface-sunken);stroke-width:3px}' +
      '.kg-side{border:var(--primitive-border-hairline) solid var(--theme-line-hairline);border-radius:8px;padding:var(--primitive-space-3);min-width:0;overflow-wrap:anywhere}' +
      '.kg-side .rel{display:block;padding:3px 0;line-height:1.7}.kg-dot{display:inline-block;width:.7em;height:.7em;border-radius:50%;margin-right:.35em;vertical-align:middle}' +
      /* r70（产品负责人 2026-10-15）：图例筛选不用主按钮的深色实底：浅底、深字、细描边，保留彩色圆点；没选中的变淡、虚线框 */
      '.kg-leg button,.kg-leg button[aria-pressed=true]{background:var(--theme-surface-raised);color:var(--theme-text-primary);border:var(--primitive-border-hairline) solid var(--theme-line-control);box-shadow:none}' +
      '.kg-leg button[aria-pressed=true]{background:color-mix(in srgb,var(--theme-text-primary) 7%,var(--theme-surface-raised))}.kg-leg button:hover{border-color:var(--theme-text-secondary)}' +
      '.kg-leg button[aria-pressed=false]{opacity:.5;background:transparent;border-style:dashed}' +
      '#kg-canvas{position:relative}.kg-pop{position:absolute;z-index:3;min-width:200px;max-width:260px;padding:var(--primitive-space-3);border:var(--primitive-border-hairline) solid rgba(232,182,90,.6);border-radius:10px;background:var(--theme-surface-raised,#16213a);box-shadow:0 8px 24px rgba(0,0,0,.35)}' +
      '.kg-ph{display:flex;align-items:center;justify-content:space-between;color:#E8B65A;margin-bottom:var(--primitive-space-2)}.kg-px{background:none;border:0;color:var(--theme-text-tertiary);cursor:pointer;padding:0}' +
      '.kg-pt{display:flex;justify-content:space-between;gap:var(--primitive-space-4);width:100%;background:none;border:0;border-bottom:var(--primitive-border-hairline) solid var(--theme-line-hairline);color:var(--theme-text-primary);font:inherit;padding:6px 0;cursor:pointer;text-decoration:underline;text-underline-offset:4px;text-decoration-color:var(--theme-line-control)}.kg-pt.hot{color:#E8B65A}.kg-pt:hover{text-decoration-color:currentColor}' +
      '@media (max-width:860px){.kg-wrap{grid-template-columns:1fr}}',
    kgHtml: function () {
      var esc = C.esc, ic = C.ic, st = C.st, g;
      try { g = readCached('/api/graph/kg?key=' + encodeURIComponent(st.key)); } catch (err) { if(err&&(err.viewPending||err.code==='VIEW_CHANGED'))throw err; return '<section class="box"><div class="sub2" data-ptds-inline><!--ptds-ui:s7eb7abc67ed4-->图谱没取到（<!--/ptds-ui-->' + esc(err.code) + '）</div></section>'; }
      LIVE.kg = g;
      if (!g.nodes.length) return '<section class="box"><div class="sub2" data-ptds-ui="se5b69c643ba6">还没有数据。录入或接入数据后，来源、指标、状态卡和授权会出现在这里。</div></section>';
      var hide = st.kgHide || {}, K = LIVE.KG_KIND;
      var leg = Object.keys(K).filter(function (k) { return g.kinds[k]; }).map(function (k) { return '<button class="chip" data-kg-kind="' + k + '" aria-pressed="' + !hide[k] + '"><span class="kg-dot" style="background:' + K[k][1] + '"></span>' + K[k][0] + ' ' + g.kinds[k] + '</button>'; }).join('');
      return '<section class="box" id="kg-box"><h3 data-ptds-inline><!--ptds-ui:se6051b9b8965-->证据图谱<!--/ptds-ui--><span class="grow"></span><span class="sub2">' + g.nodes.length + ' 个点 · ' + g.edges.length + ' 条关系</span></h3>' +
        '<div class="chips kg-leg" role="group" aria-label="按类别显示" data-ptds-ui-aria-label="s3096c565c4c5">' + leg + (st.kgSel ? '<button class="chip" id="kg-clear">' + ic('x') + '取消选中</button>' : '') + '</div>' +
        '<div class="kg-wrap"><div id="kg-canvas"></div><div class="kg-side" id="kg-side"></div></div></section>';
    },
    kgLayout: function (nodes, edges, W, H) {
      /* 分层排布：类别决定列（来源在左、对象在右），列内按相邻点的平均高度排序并就近摆放，互不重叠；拖动过的点记住位置 */
      var K = LIVE.KG_KIND, pos = C.st.kgPos || {}, cols = {}, by = {}, adj = {}, GAP = 40, top = 34, bot = H - 34;
      nodes.forEach(function (n) { var c = K[n.kind] ? K[n.kind][2] : 3; (cols[c] = cols[c] || []).push(n); n.col = c; n.x = 70 + (W - 140) * c / 6; by[n.id] = n; adj[n.id] = []; });
      edges.forEach(function (e) { if (by[e.from] && by[e.to]) { adj[e.from].push(by[e.to]); adj[e.to].push(by[e.from]); } });
      var keys = Object.keys(cols).map(Number).sort(function (x, y) { return x - y; });
      keys.forEach(function (c) { cols[c].forEach(function (n, i) { n.y = top + (bot - top) * (i + 0.5) / cols[c].length; }); });
      var place = function (list) {
        list.sort(function (p, q) { return p.want - q.want; });
        var span = (list.length - 1) * GAP, start = Math.max(top, Math.min(bot - span, list.reduce(function (t, n) { return t + n.want; }, 0) / list.length - span / 2));
        list.forEach(function (n, i) { n.y = Math.max(n.want, i ? list[i - 1].y + GAP : top); });
        for (var i = list.length - 1; i >= 0; i--) n2(i);
        function n2(i) { var lim = i === list.length - 1 ? bot : list[i + 1].y - GAP; if (list[i].y > lim) list[i].y = lim; }
        if (list.length && list[0].y < top) { var d = top - list[0].y; list.forEach(function (n) { n.y += d; }); }
        return start;
      };
      for (var pass = 0; pass < 8; pass++) {
        (pass % 2 ? keys.slice().reverse() : keys).forEach(function (c) {
          cols[c].forEach(function (n) { var nb = adj[n.id].filter(function (m) { return m.col !== n.col; }); n.want = nb.length ? nb.reduce(function (t, m) { return t + m.y; }, 0) / nb.length : n.y; });
          place(cols[c]);
        });
      }
      nodes.forEach(function (n) { if (pos[n.id]) { n.x = Math.max(20, Math.min(W - 20, pos[n.id][0])); n.y = Math.max(24, Math.min(H - 30, pos[n.id][1])); } });
      return by;
    },
    kgDraw: function () {
      var g = LIVE.kg, st = C.st, esc = C.esc, K = LIVE.KG_KIND, box = document.getElementById('kg-canvas');
      if (!g || !box) return;
      var hide = st.kgHide || {}, nodes = g.nodes.filter(function (n) { return !hide[n.kind]; }).map(function (n) { return Object.assign({}, n); });
      var ids = {}; nodes.forEach(function (n) { ids[n.id] = 1; });
      var edges = g.edges.filter(function (e) { return ids[e.from] && ids[e.to]; });
      var per = {}; nodes.forEach(function (n) { var c = K[n.kind] ? K[n.kind][2] : 3; per[c] = (per[c] || 0) + 1; });
      var W = 1000, H = Math.max(360, 40 * Math.max.apply(null, Object.keys(per).map(function (k) { return per[k]; })) + 60);
      var by = LIVE.kgLayout(nodes, edges, W, H), sel = st.kgSel && by[st.kgSel] ? st.kgSel : null, nb = {};
      if (sel) { nb[sel] = 1; edges.forEach(function (e) { if (e.from === sel) nb[e.to] = 1; if (e.to === sel) nb[e.from] = 1; }); }
      var P = !sel && LIVE.kgPath ? LIVE.kgPath : null; /* R08：证据回执选中的结论，整条路径高亮、其余变暗 */
      var deg = {}; edges.forEach(function (e) { deg[e.from] = (deg[e.from] || 0) + 1; deg[e.to] = (deg[e.to] || 0) + 1; });
      var fit = function (s, px) { s = String(s || ''); var w = 0, out = ''; for (var i = 0; i < s.length; i++) { var cw = s.charCodeAt(i) > 0x2e80 ? 11.5 : 6.6; if (w + cw > px) return out + '…'; w += cw; out += s[i]; } return out; };
      var path = function (e) { var a = by[e.from], b = by[e.to], mx = (a.x + b.x) / 2; return 'M' + a.x.toFixed(1) + ',' + a.y.toFixed(1) + ' C' + mx.toFixed(1) + ',' + a.y.toFixed(1) + ' ' + mx.toFixed(1) + ',' + b.y.toFixed(1) + ' ' + b.x.toFixed(1) + ',' + b.y.toFixed(1); };
      var seenRel = {}, showLbl = function (e) { if (!(sel ? (e.from === sel || e.to === sel) : edges.length <= 18)) return false; var k = e.rel + (e.from === sel ? '>' : '<'); if (seenRel[k]) return false; seenRel[k] = 1; return true; };
      var lbl = function (e) { return e.rel + (e.n > 1 && /^(提供|原件)$/.test(e.rel) ? ' ' + e.n + ' 条' : ''); };
      var svg = '<svg class="kg-svg" id="kg-svg" viewBox="0 0 ' + W + ' ' + H + '" role="img" aria-label="知识图谱">' +
        edges.map(function (e, i) { var on = sel && (e.from === sel || e.to === sel), pp = P && P[e.from] && P[e.to]; return '<path class="kg-e' + (on ? ' on' : sel ? ' off' : pp ? ' path' : P ? ' off' : '') + '" data-i="' + i + '"' + (pp ? ' style="animation-delay:' + (by[e.from].col * 140) + 'ms"' : '') + ' d="' + path(e) + '"/>'; }).join('') +
        edges.map(function (e, i) { if (!showLbl(e)) return ''; var a = by[e.from], b = by[e.to]; return '<text class="kg-el" data-li="' + i + '" x="' + ((a.x + b.x) / 2).toFixed(1) + '" y="' + ((a.y + b.y) / 2 - 3).toFixed(1) + '" text-anchor="middle">' + esc(lbl(e)) + '</text>'; }).join('') +
        nodes.map(function (n) { var k = K[n.kind] || ['', '#999'], r = Math.min(15, 7 + Math.sqrt(deg[n.id] || 1) * 1.6);
          return '<g class="kg-n' + (n.id === sel ? ' sel' : sel && !nb[n.id] ? ' off' : P && !P[n.id] ? ' off' : P && n.kind === 'conclusion' ? ' sel' : '') + '" role="button" tabindex="0" data-kg-type="' + esc(n.kind) + '" data-kg-label="' + esc(n.label) + '" data-kg="' + esc(n.id) + '" transform="translate(' + n.x.toFixed(1) + ',' + n.y.toFixed(1) + ')"><title>' + esc(k[0] + '：' + n.label) + '</title><circle r="' + r.toFixed(1) + '" fill="' + k[1] + '"/><text y="' + (r + 12).toFixed(1) + '" text-anchor="middle">' + esc(fit(n.label, 138)) + '</text></g>'; }).join('') + '</svg>';
      box.innerHTML = svg;
      box.querySelectorAll('.kg-e.path').forEach(function (pe) { try { pe.style.setProperty('--len', Math.ceil(pe.getTotalLength())); } catch (err) { if(err&&(err.viewPending||err.code==='VIEW_CHANGED'))throw err; pe.style.setProperty('--len', 0); } });
      LIVE.kgSide(sel ? by[sel] : null, edges, by);
      LIVE.kgPop(sel ? by[sel] : null);
      LIVE.kgBindSvg(nodes, edges, by, path);
    },
    kgSide: function (n, edges, by) {
      var esc = C.esc, K = LIVE.KG_KIND, el = document.getElementById('kg-side'); if (!el) return;
      if (!n) { el.innerHTML = '<div class="sub2">点图里的任意一个点，这里列出它是什么、和谁有关系、依据是哪本账。</div><div class="sub2" style="margin-top:.6em">颜色：' + Object.keys(K).filter(function (k) { return (LIVE.kg.kinds || {})[k]; }).map(function (k) { return '<span class="kg-dot" style="background:' + K[k][1] + '"></span>' + K[k][0]; }).join('　') + '</div>'; return; }
      var k = K[n.kind] || [n.kind, '#999'], facts = [];
      if (n.kind === 'indicator' && n.last) facts.push('共 ' + n.count + ' 条' + (n.corrected ? '，更正过 ' + n.corrected + ' 条' : '') + '；最近 ' + (n.last.when || '').slice(0, 16).replace('T', ' ') + '：' + LIVE.yn(n.last.value) + (n.last.unit ? ' ' + n.last.unit : ''));
      if (n.kind === 'conclusion') facts.push('计算 #' + n.run_id + ' 得出；点下面的按钮看用了哪些数据、哪一版。');
      if (n.kind === 'alert') facts.push((n.title || '') + ' · ' + C.tzTime(n.at, true));
      if (n.kind === 'grant') facts.push('状态：' + ({ ACTIVE: '生效中', WAIT_CHANNEL: '等接入', REVOKED: '已撤销', EXPIRED: '已到期' }[n.status] || n.status));
      var groups = [], gi = {};
      edges.filter(function (e) { return e.from === n.id || e.to === n.id; }).forEach(function (e) {
        var out = e.from === n.id, k = (out ? '→ ' : '← ') + e.rel;
        if (!gi[k]) { gi[k] = { k: k, basis: e.basis, items: [] }; groups.push(gi[k]); }
        gi[k].items.push({ o: by[out ? e.to : e.from], n: e.n, rel: e.rel });
      });
      var rel = groups.map(function (gr) {
        return '<span class="rel">' + esc(gr.k) + '：' + gr.items.map(function (it) { return '<button class="link" data-kg-go="' + esc(it.o.id) + '"><span class="kg-dot" style="background:' + (K[it.o.kind] || ['', '#999'])[1] + '"></span>' + esc(it.o.label) + '</button>' + (it.n > 1 && /^(提供|原件)$/.test(it.rel) ? '<span class="sub2">（' + it.n + ' 条）</span>' : ''); }).join('、') +
          '<br><span class="sub2" data-ptds-inline><!--ptds-ui:s8124cd7ac28c-->依据：<!--/ptds-ui-->' + esc(gr.basis) + '</span></span>'; }).join('');
      el.innerHTML = '<div><span class="kg-dot" style="background:' + k[1] + '"></span><span class="sub2">' + esc(k[0]) + '</span></div><div data-kg-detail="' + esc(n.id) + '" style="font-size:var(--scale-type-date);margin:.2em 0 .4em">' + esc(n.label) + '</div>' +
        facts.map(function (f) { return '<div class="sub2">' + esc(f) + '</div>'; }).join('') + '<div style="margin-top:.6em">' + (rel || '<span class="sub2" data-ptds-ui="sf4335f2f8324">没有关系</span>') + '</div>' +
        (n.kind === 'conclusion' ? '<div style="margin-top:.6em"><button class="chip" id="kg-trace" data-ptds-ui="s4aada4928bd0">看这条结论的来龙去脉</button></div>' : '') +
        (n.kind === 'indicator' ? '<div style="margin-top:.6em"><button class="chip" id="kg-data" data-ptds-ui="sba33354c30da">去我的数据看</button></div>' : '');
      el.querySelectorAll('[data-kg-go]').forEach(function (b) { b.onclick = function () {
        var o = by[b.dataset.kgGo];
        if (o && o.kind === 'conclusion' && o.card && o.tp) { C.st.kgSel = null; LIVE.openTrace(o.card, o.tp, o.run_id); return; }  /* 侧栏里的结论（带下划线的时点）直接打开来龙去脉浮窗 */
        C.st.kgSel = b.dataset.kgGo; LIVE.kgDraw(); }; });
      var tb = document.getElementById('kg-trace'); if (tb) tb.onclick = function () { C.st.kgSel = null; LIVE.openTrace(n.card, n.tp, n.run_id); };
      var db = document.getElementById('kg-data'); if (db) db.onclick = function () { LIVE.graphNavigate(n.destination,C.st.key); };
    },
    /* 状态溯源小卡（产品负责人 2026-10-14）：点状态卡节点，在节点旁列出各时段的结论；点一个时段打开来龙去脉浮窗 */
    kgPop: function (n) {
      var old = document.getElementById('kg-pop'); if (old) old.remove();
      var cv = document.getElementById('kg-canvas'), svg = document.getElementById('kg-svg'); if (!n || n.kind !== 'card' || !cv || !svg) return;
      // Card history is needed only after selecting a card, never to open the map.
      var esc = C.esc, ic = C.ic, cid = n.id.replace(/^card:/, ''), co = LIVE.fwCards().filter(function (c) { return c.card_id === cid; })[0];
      var ts = co ? co.timepoints.slice().reverse() : [], all = C.st.kgPopAll;
      var row = function (t) { var lv = LIVE.rcValue({ value: t.value, text: t.level_zh, level_zh: t.level_zh, value_status: t.status, rule: cid.replace(/^engine-/, '') });
        return '<button class="kg-pt' + (t.level === 'ALERT' ? ' hot' : '') + '" data-kg-tp="' + esc(t.tp) + '"><span>' + esc(t.tp) + '</span><span>' + esc(lv) + '</span></button>'; };
      var el = document.createElement('div'); el.id = 'kg-pop'; el.className = 'kg-pop'; el.setAttribute('role', 'dialog'); el.setAttribute('aria-label', '状态溯源');
      el.innerHTML = '<div class="kg-ph"><span data-ptds-ui="sc8cd86785893">状态溯源</span><button class="kg-px" aria-label="关闭" data-ptds-ui-aria-label="s3fd47edce45b">' + ic('x') + '</button></div>' +
        (ts.length ? (all ? ts : ts.slice(0, 8)).map(row).join('') + (ts.length > 8 && !all ? '<button class="link sub2" id="kg-pmore" data-ptds-inline><!--ptds-ui:s268ec6902063-->另有 <!--/ptds-ui-->' + (ts.length - 8) + ' 个时段</button>' : '') + '<div class="sub2" data-ptds-ui="s816c03ce21c0">点一个时段，看它的来龙去脉</div>'
          : '<div class="sub2" data-ptds-ui="sc473958105bc">还没有算出来的结论</div>');
      cv.appendChild(el);
      var r = svg.getBoundingClientRect(), c = cv.getBoundingClientRect(), vb = svg.viewBox.baseVal;
      var x = (n.x * r.width / vb.width) + r.left - c.left, y = (n.y * r.height / vb.height) + r.top - c.top;
      var left = x + 22; if (left + el.offsetWidth > c.width) left = Math.max(0, x - 22 - el.offsetWidth);
      el.style.left = left + 'px'; el.style.top = Math.max(0, Math.min(c.height - el.offsetHeight, y - 24)) + 'px';
      var close = function () { C.st.kgSel = null; C.st.kgPopAll = false; LIVE.kgDraw(); };
      el.querySelector('.kg-px').onclick = LIVE.action(close);
      var mb = document.getElementById('kg-pmore'); if (mb) mb.onclick = function () { C.st.kgPopAll = true; LIVE.kgPop(n); };
      el.querySelectorAll('[data-kg-tp]').forEach(function (b) { b.onclick = function () { C.st.kgSel = null; C.st.kgPopAll = false; C.st.graphTp = b.dataset.kgTp; LIVE.openTrace(cid, b.dataset.kgTp); }; });
      if (!LIVE._kgEsc) { LIVE._kgEsc = true; document.addEventListener('keydown', function (ev) { if (ev.key === 'Escape' && document.getElementById('kg-pop')) { C.st.kgSel = null; LIVE.kgDraw(); } }); }
    },
    kgBindSvg: function (nodes, edges, by, path) {
      var svg = document.getElementById('kg-svg'), st = C.st; if (!svg) return;
      var drag = null, moved = false;
      var pt = function (ev) { var r = svg.getBoundingClientRect(), vb = svg.viewBox.baseVal; return [(ev.clientX - r.left) * vb.width / r.width, (ev.clientY - r.top) * vb.height / r.height]; };
      svg.addEventListener('click', function (ev) { if (ev.target === svg && st.kgSel) { st.kgSel = null; LIVE.kgDraw(); } });
      svg.querySelectorAll('.kg-n').forEach(function (g) {
        g.addEventListener('keydown',function(ev){if(ev.key==='Enter'||ev.key===' '){ev.preventDefault();var n=by[g.dataset.kg];if(n.destination)LIVE.graphNavigate(n.destination,st.key);}});
        g.addEventListener('pointerdown', function (ev) { drag = by[g.dataset.kg]; moved = false; LIVE.kgDragging = true; g.setPointerCapture(ev.pointerId); ev.preventDefault(); });
        g.addEventListener('pointermove', function (ev) {
          if (!drag || drag.id !== g.dataset.kg) return;
          var p = pt(ev); if (Math.abs(p[0] - drag.x) + Math.abs(p[1] - drag.y) > 2) moved = true;
          drag.x = Math.max(20, Math.min(svg.viewBox.baseVal.width - 20, p[0])); drag.y = Math.max(20, Math.min(svg.viewBox.baseVal.height - 20, p[1]));
          g.setAttribute('transform', 'translate(' + drag.x.toFixed(1) + ',' + drag.y.toFixed(1) + ')');
          edges.forEach(function (e, i) { if (e.from === drag.id || e.to === drag.id) { var pe = svg.querySelector('[data-i="' + i + '"]'); if (pe) pe.setAttribute('d', path(e)); var lt = svg.querySelector('[data-li="' + i + '"]'); if (lt) { var a = by[e.from], b = by[e.to]; lt.setAttribute('x', ((a.x + b.x) / 2).toFixed(1)); lt.setAttribute('y', ((a.y + b.y) / 2 - 3).toFixed(1)); } } });
        });
        g.addEventListener('pointerup', function () {
          var n = drag; drag = null; LIVE.kgDragging = false; if (!n) return;
          if (moved) { st.kgPos = st.kgPos || {}; st.kgPos[n.id] = [n.x, n.y]; return; }
          if (n.destination && n.destination.available) { st.kgSel=null; LIVE.graphNavigate(n.destination,st.key); return; } /* R10：点结论打开证据浮窗 */
          st.kgSel = st.kgSel === n.id ? null : n.id; LIVE.kgDraw(); var cl = document.getElementById('kg-clear'); if (!cl && st.kgSel) { /* 按钮在图例里，下次整页重画时出现 */ }
        });
      });
    },
    kgBind: function () {
      var st = C.st;
      document.querySelectorAll('[data-kg-kind]').forEach(function (b) { b.onclick = function () { st.kgHide = st.kgHide || {}; st.kgHide[b.dataset.kgKind] = !st.kgHide[b.dataset.kgKind]; b.setAttribute('aria-pressed', String(!st.kgHide[b.dataset.kgKind])); LIVE.kgDraw(); }; });
      var cl = document.getElementById('kg-clear'); if (cl) cl.onclick = function () { st.kgSel = null; LIVE.renderGraph(); };
      LIVE.kgDraw();
    },
    /* R08 证据图谱：页首一句话（多少结论能追到原始数据）→ 知识图谱 → “这个数是怎么来的”证据回执（和图谱联动高亮）→ 可信度体检 → 数据日记 */
    RC_CSS: '.eg-top{display:flex;flex-wrap:wrap;align-items:baseline;gap:var(--primitive-space-2) var(--primitive-space-4);margin-bottom:var(--primitive-space-4)}.eg-top b{font-size:var(--scale-type-title);font-weight:var(--primitive-font-weight-regular)}' +
      '.eg-q{display:inline-flex;align-items:center;justify-content:center;width:1.3em;height:1.3em;border-radius:50%;border:var(--primitive-border-hairline) solid var(--theme-line-control);font-size:11px;color:var(--theme-text-tertiary);cursor:help}' +
      '.eg-sc summary{cursor:pointer}.eg-sc .link{font:inherit;text-decoration:underline}.eg-ck{line-height:1.9;margin:4px 0 0 1em}.eg-ck .no{color:var(--theme-level-watch-text)}' +
      '.eg-pick{display:flex;flex-wrap:wrap;gap:var(--primitive-space-2);align-items:center;margin-bottom:var(--primitive-space-3)}.eg-pick select{max-width:100%;padding:4px 8px;border-radius:var(--primitive-radius-control);border:var(--primitive-border-hairline) solid var(--theme-line-control);background:var(--theme-surface-raised);color:var(--theme-text-primary);font:inherit}' +
      '.rc{border-left:2px solid var(--theme-line-control);margin-left:.4em;padding-left:var(--primitive-space-4)}.rc-head{font-size:var(--scale-type-title);margin-bottom:var(--primitive-space-2)}' +
      '.rc details{padding:6px 0}.rc summary{cursor:pointer;list-style:none;display:flex;gap:var(--primitive-space-2);align-items:baseline}.rc summary::-webkit-details-marker{display:none}' +
      '.rc .ar{color:var(--theme-text-tertiary);width:1.2em;flex:none;text-align:center}.rc .tech{margin:4px 0 2px 2em;font-size:var(--scale-type-meta);color:var(--theme-text-tertiary);overflow-wrap:anywhere;line-height:1.7}.rc .after{margin-top:var(--primitive-space-2);border-top:var(--primitive-border-hairline) dashed var(--theme-line-hairline);padding-top:var(--primitive-space-2)}' +
      '.ck{display:grid;grid-template-columns:1.6em minmax(0,1fr) auto;gap:var(--primitive-space-2);padding:6px 0;border-bottom:var(--primitive-border-hairline) solid var(--theme-line-hairline);align-items:baseline}.ck .ok{color:var(--theme-text-primary)}.ck .no{color:var(--theme-level-watch-text)}' +
      '.dy{border-bottom:var(--primitive-border-hairline) solid var(--theme-line-hairline);padding:8px 0}.dy summary{cursor:pointer;line-height:1.6}.dy summary b{font-weight:var(--primitive-font-weight-medium);margin-right:.4em}.dy .ev{display:grid;grid-template-columns:3.4em 3.4em minmax(0,1fr) auto;gap:var(--primitive-space-3);padding:4px 0 4px 1em;font-size:var(--scale-type-meta);align-items:baseline}.dy .ev>span{min-width:0;overflow-wrap:anywhere}' +
      '.kg-e.path{stroke:var(--theme-text-primary);stroke-width:2;opacity:1;stroke-dasharray:var(--len);stroke-dashoffset:var(--len);animation:kgdraw 420ms ease-out forwards}' +
      '@keyframes kgdraw{to{stroke-dashoffset:0}}@media (prefers-reduced-motion: reduce){.kg-e.path{animation:none;stroke-dashoffset:0}}' +
      '@media (max-width:720px){.dy .ev{grid-template-columns:3.4em minmax(0,1fr)}.dy .ev .ln{display:none}}',
    /* 结论的显示值：引擎卡用数值（睡眠时长换成小时分钟），sJIA 关注卡和自定义卡用等级 */
    rcValue: function (c) {
      if (c.value_status && c.value_status !== 'computed') return c.text || '这次算不了';
      if (/^SLEEP\.A01/.test(String(c.rule || '')) && c.value != null && isFinite(+c.value)) return hm(+c.value * 60);
      return c.text || c.level_zh || '—';
    },
    /* R10 证据浮窗（产品负责人 2026-10-14 定）：右侧浮窗，五个节点竖排：① 来源 → ② 落库·星炬 → ③ 计算·星轨 → ④ 结果 → ⑤ 授权·星簇。
       入口：卡片页“这个数怎么来的”、知识图谱结论点、数据日记“查看”、证据图谱页的选择器。只读：内容全部来自 /api/graph/trace。 */
    FW_CSS: '#fw{position:fixed;top:16px;right:16px;bottom:16px;width:440px;max-width:calc(100vw - 32px);z-index:60;display:flex;flex-direction:column;background:var(--theme-surface-raised);color:var(--theme-text-primary);border:var(--primitive-border-hairline) solid var(--theme-line-control);border-radius:14px;box-shadow:0 20px 60px rgba(0,0,0,.45);animation:fwin var(--ptds-fade-duration,180ms) ease-in-out both}' +
      '#fw.wide{width:min(1100px,calc(100vw - 32px))}@keyframes fwin{from{opacity:0}to{opacity:1}}@media (prefers-reduced-motion: reduce){#fw{animation:none}}' +
      '#fw .fh{padding:14px 18px 10px;border-bottom:var(--primitive-border-hairline) solid var(--theme-line-hairline);position:relative}#fw .fh .k{font-size:var(--scale-type-meta);color:var(--theme-text-tertiary);padding-right:2em}#fw .fh .v{font-size:var(--scale-type-title);margin-top:4px}' +
      '#fw .fx{position:absolute;right:10px;top:10px}#fw .fb{padding:14px 18px;overflow:auto;flex:1}#fw .ff{padding:10px 18px;border-top:var(--primitive-border-hairline) solid var(--theme-line-hairline);display:flex;gap:var(--primitive-space-2);align-items:center;flex-wrap:wrap}' +
      '#fw .nd{position:relative;padding-left:30px}#fw .nd:before{content:"";position:absolute;left:10px;top:22px;bottom:2px;width:2px;background:var(--theme-line-control)}#fw .nd:last-child:before{display:none}' +
      '#fw .no{position:absolute;left:2px;top:2px;width:18px;height:18px;border-radius:50%;border:2px solid var(--theme-text-secondary);font-size:11px;line-height:14px;text-align:center;color:var(--theme-text-secondary);background:var(--theme-surface-raised)}' +
      '#fw .nl{font-size:var(--scale-type-meta);color:var(--theme-text-tertiary)}#fw details.nb{border:var(--primitive-border-hairline) solid var(--theme-line-control);border-radius:10px;padding:9px 11px;margin:4px 0 14px}' +
      '#fw details.nb>summary{cursor:pointer;list-style:none}#fw details.nb>summary::-webkit-details-marker{display:none}#fw .tech{margin-top:8px;font-size:var(--scale-type-meta);color:var(--theme-text-tertiary);overflow-wrap:anywhere;line-height:1.7}' +
      '#fw .tg{display:inline-block;border:var(--primitive-border-hairline) solid var(--theme-line-control);border-radius:999px;padding:1px 8px;margin:4px 4px 0 0;font-size:var(--scale-type-meta)}#fw .tg.old{border-style:dashed;color:var(--theme-text-tertiary)}' +
      '#fw .ft{margin-top:6px}#fw .ft>summary{cursor:pointer;line-height:1.7}#fw .ft>div{line-height:1.8;margin:4px 0 0 1em}#fw .ft-ok{color:var(--theme-text-primary)}#fw .ft-no{color:var(--theme-level-watch-text)}' +
      '#fw .full{margin-top:var(--primitive-space-2)}#fw .full>summary{cursor:pointer;font-size:var(--scale-type-meta);color:var(--theme-text-secondary)}' +
      '@media (max-width:720px){#fw{top:8px;right:8px;bottom:8px;left:8px;width:auto}}',
    /* 这个数可信吗（产品负责人 2026-10-14 定）：④结果下面一行，点开看两句说明。重算是服务端现场按同一版定义在内存里再算（不写库） */
    fwTrust: function (t) {
      var esc = C.esc, ic = C.ic, v = (t.verify || {}).state, n = (t.inputs || []).length, rid = (t.run || {}).run_id;
      var ok = function (x) { return '<span class="ft-ok">' + ic('check') + ' ' + x + '</span>'; }, no = function (x) { return '<span class="ft-no">' + ic('circle-alert') + ' ' + x + '</span>'; };
      var head = [t.traceable ? ok('能追到原始数据') : no('追不全')];
      if (v === 'SAME') head.push(ok('重新算一遍，一字不差')); else if (v === 'DIFFER') head.push(no('重新算一遍和当时不一样')); else if (v === 'STALE') head.push('<span data-ptds-ui="sc80339cfb978">数据有更新，等下次计算再核对</span>');
      var body = [t.traceable ? '能追到原始数据：用到的 ' + n + ' 条数据都是星炬里的正式记录，来源、版本齐全。' : '追不全：缺 ' + esc((t.missing || []).join('、')) + '。'];
      if (v === 'SAME') body.push('重新算一遍：按计算 #' + esc(rid) + ' 用的同一版规则现场再算（只在内存里算，不写库），和当时存下的结果一字不差。');
      else if (v === 'DIFFER') body.push('重新算一遍：按同一版规则现场再算，结果和当时存下的不一样。这条结论先别用，看下面的完整明细。');
      else if (v === 'STALE') body.push('这条结论算完以后，用到的数据又有更正或新增；下次计算会按新数据重算，旧结果保留。');
      return '<details class="ft"><summary class="sub2" data-ptds-inline><!--ptds-ui:s5592c89f40d1-->这个数可信吗：<!--/ptds-ui-->' + head.join(' · ') + '</summary><div class="sub2">' + body.join('<br>') + '</div></details>';
    },
    graphReadV2: function () { return !!(C.DATA && C.DATA.ptds_live && C.DATA.ptds_live.graph_read_version >= 2); },
    fwCards: function () {
      // Use the instance/epoch-bound read cache; a previous instance's cards must
      // never be reused by a popup or trace opened directly from another page.
      return readCached((LIVE.graphReadV2() ? '/api/graph/read?view=cards&key=' : '/api/graph?key=') + encodeURIComponent(C.st.key)).cards || [];
    },
    openTrace: function (card, tp, runId) {
      var st = C.st; st.fw = { card: card, tp: tp, run_id: runId }; st.fwFull = false; LIVE.renderFw();
    },
    closeTrace: function () {
      var el = document.getElementById('fw'); if (el) el.remove(); C.st.fw = null;
      LIVE.noticeMount();
      if (LIVE.kgPath) { LIVE.kgPath = null; LIVE.kgDraw(); }
    },
    openEvidenceObservation: function (ref) {
      var key = C.st.key, text = String(ref || ''), match = /^([^@]+)@([1-9][0-9]*)$/.exec(text);
      if (!text || (text.indexOf('@') >= 0 && !match) || (match && !Number.isSafeInteger(Number(match[2])))) { C.toast('这条证据的版本引用无效'); return; }
      var target = { kind: 'observation', observation_id: match ? match[1] : text };
      if (match) target.revision = Number(match[2]);
      LIVE.closeTrace();
      return LIVE.graphNavigate(target, key);
    },
    renderFw: function () {
      if (!document.getElementById('fw-css')) { var s0 = document.createElement('style'); s0.id = 'fw-css'; s0.textContent = LIVE.FW_CSS + LIVE.GRAPH_CSS; document.head.appendChild(s0); }
      var esc = C.esc, ic = C.ic, st = C.st, f = st.fw; if (!f) return;
      var cards = LIVE.fwCards(), cobj = cards.filter(function (c) { return c.card_id === f.card; })[0], tps = cobj ? cobj.timepoints.map(function (t) { return t.tp; }) : [];
      if (!f.tp && tps.length) f.tp = tps[tps.length - 1];
      var t = null; if (f.tp) { try { t = readCached('/api/graph/trace?key=' + encodeURIComponent(st.key) + '&tp=' + encodeURIComponent(f.tp) + '&card=' + encodeURIComponent(f.card)+(f.run_id?'&run_id='+encodeURIComponent(f.run_id):'')); } catch (err) { if(err&&(err.viewPending||err.code==='VIEW_CHANGED'))throw err; t = null; } }
      var at = function (iso) { var s = C.tzTime(iso); return /^\d{4}-\d\d-\d\d \d\d:\d\d/.test(s) ? s.slice(5, 16) : String(iso || ''); };
      var KIND = { OCR: '化验单原件', TABLE: '表格导入', MANUAL: '手工录入', OURA: 'Oura 官方授权，自动拉取', AH: '苹果健康，手机同步', SYN: '合成数据（演示）', SOMALOOP: 'Somaloop 腕带，腕带桥直连' };
      var node = function (n, label, sum, tech) { return '<div class="nd"><span class="no">' + n + '</span><div class="nl">' + label + '</div><details class="nb"><summary>' + sum + '</summary>' + (tech ? '<div class="tech">' + tech + '</div>' : '') + '</details></div>'; };
      var head, body = '';
      if (!t || !t.found) {
        head = '<div class="k" data-ptds-ui="s6cbd0dfaba92">这个数是怎么来的</div><div class="v">' + esc(f.tp || '') + '</div>';
        body = '<div class="sub2" data-ptds-ui="s5026e365226b">这个时点还没有计算记录，或这张卡在这份数据里不显示。</div>';
      } else {
        var c = t.conclusion, r = t.run, ins = t.inputs.filter(function (i) { return i.role !== 'HISTORY'; }), hist = t.inputs.filter(function (i) { return i.role === 'HISTORY'; });
        head = '<div class="k" data-ptds-inline><!--ptds-ui:s6169160ac53d-->这个数是怎么来的 · <!--/ptds-ui-->' + esc(t.card_zh || (cobj || {}).name || '') + '</div><div class="v">' + esc(t.tp) + ' · ' + esc(t.card_id === 'VITALS' ? '取最近读数（只描述，不定级）' : LIVE.rcValue(c)) + '</div>';
        var srcs = {}, order = [];
        t.inputs.forEach(function (i) { if (!i.found) return; var o = i.origin || {}, k = (o.ref || '').split(':')[0], key = k === 'OCR' ? o.original || o.ref : k || o.zh;
          if (!srcs[key]) { srcs[key] = { k: k, o: o, n: 0 }; order.push(key); } srcs[key].n++; });
        body += node(1, '来源', order.map(function (key) { var s = srcs[key]; return '<div>' + esc(KIND[s.k] || s.o.zh || '来源未记录') + (s.k === 'OCR' && s.o.file_name ? ' · ' + esc(s.o.file_name) : '') + '<span class="sub2"> · ' + s.n + ' 条</span></div>'; }).join('') || '<div class="sub2" data-ptds-ui="s49f389a0484d">没有记录来源</div>',
          order.map(function (key) { var o = srcs[key].o; return (o.original ? '<a class="link" target="_blank" rel="noopener" href="/api/torch/original?key=' + encodeURIComponent(st.key) + '&name=' + encodeURIComponent(o.original) + '">' + ic('file-image') + ' 查看原图</a>' + (o.engine ? ' · 识别 ' + esc(o.engine) : '') + '<br>' : '') + (o.line ? '原文：' + esc(o.line) + '<br>' : '') + '来源引用 ' + esc(o.ref || '—'); }).join('<br>'));
        var changed = ins.filter(function (i) { return i.superseded || i.revision > 1; }).length;
        body += node(2, '落库 · 星炬', '<div>' + ins.length + ' 条数据' + '<span class="sub2"> · ' + (changed ? changed + ' 条更正过或之后有新版' : '全部第 1 版，没被改过') + '</span></div><div>' +
            ins.map(function (i) { return '<span class="tg">' + esc(i.found ? humanLabel(i.label).replace(/（[^（）]*）$/, '') + ' ' + human(i.code, i.value, i.unit, i.comparator) : '找不到这一版') + '</span>'; }).join('') +
            (hist.length ? '<span class="tg old" data-ptds-inline><!--ptds-ui:s268ec6902063-->另有 <!--/ptds-ui-->' + hist.length + ' 条更早的数据作对照</span>' : '') + '</div>',
          ins.map(function (i) { var hd = i.handoff || {}; return esc(humanLabel(i.label || i.observation_id)) + '：记录 ' + esc(i.observation_id) + ' · 第 ' + i.revision + ' 版 · 信度 ' + esc(i.trust_tier || '—') + (i.superseded ? ' · 之后有第 ' + i.latest.revision + ' 版' : '') +
            (hd.batch_id ? ' · 批次 ' + esc(hd.batch_id) + (hd.export ? ' · 交接文件 ' + esc(hd.export.file) + ' · 指纹 ' + esc(hd.export.sha256.slice(0, 12)) : '') : '') + ' <button class="link" data-eg-obs="' + esc(i.observation_id + '@' + i.revision) + '">打开</button>'; }).join('<br>'));
        var rule = c.rule_name ? esc(c.rule_name) + (c.rule ? ' v' + esc(String(c.rule).split('@')[1] || '') : '') : esc(t.card_zh || '') + (c.engine_version ? ' ' + esc(c.engine_version) : '');
        body += node(3, '计算 · 星轨', '<div>' + rule + '</div><div class="sub2">' + esc(at(r.started_at)) + ' · ' + esc(r.trigger_zh) + (r.history.length > 1 ? ' · 这个时点算过 ' + r.history.length + ' 次' : '') + '</div>',
          '计算 #' + r.run_id + (c.fingerprint ? ' · 规则指纹 ' + esc(String(c.fingerprint).slice(0, 16)) : '') + (c.engine_version ? ' · 引擎 ' + esc(c.engine_version) : '') +
          (r.history.length > 1 ? '<br>历次：' + r.history.map(function (x) { return '#' + x.run_id + ' ' + esc(x.trigger_zh) + ' ' + esc(at(x.at)); }).join('；') : '') +
          ((c.drivers || []).length ? '<br>驱动：' + esc(c.drivers.map(function (d) { return d.kind === 'DYNAMIC' ? d.code + ' ' + (d.change || '') : d.rule + ' ' + d.result; }).join('；')) : '') +
          (c.rule ? '<br><button class="link" id="fw-rule" data-ptds-ui="s47985087b1ae">看这条规则的出处和原文</button>' : ''));
        body += node(4, '结果', '<div style="font-size:var(--scale-type-title)">' + esc(LIVE.rcValue(c)) + '</div>' + LIVE.fwTrust(t),
          c.text && c.text !== LIVE.rcValue(c) ? esc(c.text) : '');
        body += LIVE.medsLineHtml(t.tp);
        var outs = (t.alerts || []).map(function (a) { var dl = (a.deliveries || []).map(function (d) { return d.zh + (d.outcome === 'SENT' ? '已送达' : '未送达'); }).join('、'); return '<div data-ptds-inline><!--ptds-ui:sefb4f2e83473-->推送给我自己<!--/ptds-ui-->' + (dl ? '（' + esc(dl) + '）' : '') + '</div>'; }).join('') +
          (t.used_by || []).filter(function (u) { return u.how !== '推送'; }).map(function (u) { return '<div data-ptds-inline><!--ptds-ui:s5c67a26ace4f-->经授权“<!--/ptds-ui-->' + esc(u.grant || '') + '”' + (u.obj === '我自己' ? '发给我自己' : '给了 ' + esc(u.obj)) + '<span class="sub2">（' + esc(u.result) + '）</span></div>'; }).join('');
        var gave = (t.used_by || []).some(function (u) { return u.obj !== '我自己'; });
        body += node(5, '授权 · 星簇', (outs || '<div data-ptds-ui="s9a57b807e306">没有推送</div>') + '<div class="sub2">' + (gave ? '' : '没有出域给别人') + '</div>',
          (t.alerts || []).map(function (a) { return esc(at(a.created_at)) + ' · “' + esc(a.title) + '”'; }).concat((t.used_by || []).map(function (u) { return esc(u.when) + ' · ' + esc(u.obj) + ' · ' + esc(u.how) + ' · ' + esc(u.result); })).join('<br>'));
        body += '<details class="full"' + (st.fwFull ? ' open' : '') + '><summary data-ptds-ui="s5871f960daba">完整连线图和逐条明细</summary>' + (st.fwFull ? LIVE.traceGraph(t) + LIVE.traceHtml(t) : '') + '</details>';
      }
      if (t && t.found && !C.isReplay()) body = LIVE.spFwHtml(t) + body;
      var i = tps.indexOf(f.tp);
      var html = '<div class="fh">' + head + '<button class="ibtn fx" id="fw-x" aria-label="关闭" data-ptds-ui-aria-label="s3fd47edce45b">' + ic('x') + '</button></div><div class="fb">' + body + '</div>' +
        '<div class="ff"><button class="chip" id="fw-prev"' + (i <= 0 ? ' disabled' : '') + '>‹ 前一个</button><button class="chip" id="fw-next"' + (i < 0 || i >= tps.length - 1 ? ' disabled' : '') + '>后一个 ›</button><span class="grow"></span>' +
        (C.st.tview === 'graph' && C.st.app === 'torch' ? '' : '<button class="link" id="fw-graph" data-ptds-ui="s9fc84d18975c">在证据图谱里看路径</button>') + '</div>';
      var el = document.getElementById('fw'); if (!el) { el = document.createElement('aside'); el.id = 'fw'; el.setAttribute('role', 'dialog'); el.setAttribute('aria-label', '这个数是怎么来的'); document.body.appendChild(el); }
      el.className = st.fwFull ? 'wide' : ''; el.innerHTML = html;
      var g = function (id, fn) { var b = document.getElementById(id); if (b) b.onclick = LIVE.action(fn); };
      g('fw-x', LIVE.closeTrace); LIVE.spBind();
      g('fw-prev', function () { f.tp = tps[i - 1]; LIVE.renderFw(); });
      g('fw-next', function () { f.tp = tps[i + 1]; LIVE.renderFw(); });
      g('fw-graph', function () { st.kgSel = null; C.goTorch('graph'); });
      g('fw-rule', function () { LIVE.openRule(String(t.conclusion.rule).split('@')[0]); });
      var full = el.querySelector('details.full'); if (full) full.ontoggle = function () { if (full.open !== !!st.fwFull) { st.fwFull = full.open; LIVE.renderFw(); } };
      el.querySelectorAll('[data-eg-obs]').forEach(function (b) { b.onclick = function () { LIVE.openEvidenceObservation(b.dataset.egObs); }; });
      el.querySelectorAll('[data-egv-href]').forEach(function (b) { b.onclick = function () { window.open(b.dataset.egvHref, '_blank', 'noopener'); }; });
      var hb = document.getElementById('eg-hist'); if (hb) hb.onclick = function () { st.graphHist = !st.graphHist; LIVE.renderFw(); };
      LIVE.kgPath = t && t.found ? LIVE.kgPathOf(t) : null; if (document.getElementById('kg-canvas')) LIVE.kgDraw();
      if (!LIVE.fwEsc) { LIVE.fwEsc = true; document.addEventListener('keydown', function (ev) { if (ev.key === 'Escape' && document.getElementById('fw') && !document.querySelector('.rule-pop, .modal')) LIVE.closeTrace(); }); }
    },
    /* 知识图谱联动：选中的结论从数据源到结论的整条路径（来源 → 原件 → 指标 → 状态卡 → 结论） */
    kgPathOf: function (t) {
      var g = LIVE.kg; if (!g || !t || !t.found) return null;
      var codes = {}; t.inputs.forEach(function (i) { if (i.code) codes['code:' + i.code] = 1; });
      var on = {}, card = 'card:' + t.card_id; on[card] = 1;
      g.edges.forEach(function (e) { if (e.from === card && e.to.indexOf('con:') === 0) on[e.to] = 1; if (e.to === card && codes[e.from]) on[e.from] = 1; });
      for (var k = 0; k < 2; k++) g.edges.forEach(function (e) { if (on[e.to] && e.to.indexOf('code:') === 0 || on[e.to] && e.to.indexOf('doc:') === 0) if (/^(src|doc):/.test(e.from)) on[e.from] = 1; });
      return Object.keys(on).length > 1 ? on : null;
    },
    trustLine: function (m) {
      var esc = C.esc, nt = m.not_traceable || [];
      if (!m.total) return '<div class="eg-top"><span data-ptds-ui="s0421b1c0e9e5">还没有算出来的结论。建好状态卡、数据一到，每条结论都会出现在这里，能一路追到原始数据。</span>' + LIVE.selfCheckHtml() + '</div>';
      return '<div class="eg-top"><span><b>' + (m.total || 0) + '</b> 条结论里，<b>' + (m.traceable || 0) + '</b> 条能一路追到原始数据。</span>' +
        '<span class="eg-q" tabindex="0" title="“追到原始数据”指：这条结论用到的每一条数据，都是星炬里的正式记录，来源、版本、信度三样齐全。只读各处已经留下的记录，不推断、不补边。" data-ptds-ui-title="scb8fa7b3b524">?</span>' +
        LIVE.selfCheckHtml() +
        (nt.length ? '<details class="more"><summary class="sub2" data-ptds-inline><!--ptds-ui:s3f3e286143b3-->哪 <!--/ptds-ui-->' + nt.length + ' 条追不全</summary><div class="sub2">' + nt.map(esc).join('、') + '</div></details>' : '') + '</div>';
    },
    diaryHtml: function (events, lane, paged) {
      var esc = C.esc, st = C.st, LANE = { source: '数据源', data: '数据', state: '计算', auth: '授权' }, days = {}, order = [];
      var loc = function (iso) { var s = C.tzTime(iso); return /^\d{4}-\d\d-\d\d \d\d:\d\d/.test(s) ? [s.slice(0, 10), s.slice(11, 16)] : [String(iso || '').slice(0, 10), '']; };
      events.forEach(function (e) { var l = loc(e.at); if (!days[l[0]]) { days[l[0]] = []; order.push(l[0]); } days[l[0]].push({ e: e, hm: l[1] }); });
      order.sort().reverse();
      var plain = function (e) { return String(e.text).replace(/^计算 #\d+ · /, '星轨计算 · ').replace(/交给星轨 · 批次 \S+ · /, '交给星轨 · ').replace(/ · 指纹 [0-9a-f]+/, '').replace(/ · 原件 \S+$/, ''); };
      var sum = function (list) {
        var by = {}, cards = {}, nAlert = 0, nOut = 0, nSrc = [];
        list.forEach(function (x) { var e = x.e;
          if (e.lane === 'data' && /^(保存|更正|撤回) /.test(e.text)) { var s = String(e.text).split(' · ').pop(); by[s] = (by[s] || 0) + 1; }
          else if (e.lane === 'state' && e.ref && e.ref.run) cards[e.ref.card] = 1;
          else if (e.lane === 'state') nAlert++;
          else if (e.lane === 'auth') nOut++;
          else if (e.lane === 'source') nSrc.push(plain(e).split(' · ')[0]); });
        var parts = Object.keys(by).map(function (s) { return (/Oura|苹果|手机/.test(s) ? s + ' 自动送来 ' : s + ' ') + by[s] + ' 条数据'; });
        if (nSrc.length) parts.push(nSrc.filter(function (x, i, a) { return a.indexOf(x) === i; }).slice(0, 2).join('、'));
        if (Object.keys(cards).length) parts.push('星轨算了 ' + Object.keys(cards).length + ' 张卡');
        if (nAlert) parts.push('给你发了 ' + nAlert + ' 条提醒');
        // A paged data/state view has no complete authorization ledger.
        if (nOut) parts.push(nOut + ' 次授权使用');
        else if (!paged) parts.push('没有数据出域');
        return parts.length ? parts.join('；') + '。' : list.length + ' 条记录。';
      };
      var lim = paged || st.graphMore ? order.length : 7;
      return order.slice(0, lim).map(function (d, k) {
        var list = days[d], shown = list.filter(function (x) { return lane === 'ALL' || x.e.lane === lane; });
        if (!shown.length) return '';
        return '<details class="dy"' + (st.diaryDay === d || paged && k === 0 && !st.diaryDay ? ' open' : '') + ' data-day="' + esc(d) + '"' + '><summary' + (list.some(x=>x.e.ref?.gene)&&list.every(x=>x.e.lane==='data'||x.e.lane==='source'&&x.e.ref?.gene)?' data-gene-day="'+esc(JSON.stringify(Array.from(new Set(list.filter(x=>x.e.lane==='source').map(x=>plain(x.e).split(' · ')[0]))).slice(0,2)))+'"':'') + '><b>' + esc(d.slice(5)) + '</b>' + (paged ? '<span class="sub2" data-ptds-ui="s1fab4347c895">本页记录 · </span>' : '') + esc(sum(list)) + '</summary>' +
          shown.slice(0, st.diaryAll === d ? 400 : 20).map(function (x) { var e = x.e, go = e.ref && e.ref.tps && e.ref.tps.length ? ' data-eg-go="' + esc(e.ref.card || '') + '|' + esc(e.ref.tps[e.ref.tps.length - 1]) + '"' : e.ref && e.ref.observation ? ' data-eg-obs="' + esc(e.ref.observation + '@' + e.ref.revision) + '"' : '';
            return '<div class="ev"' + (e.lane === 'auth' ? ' data-sem="SEM-30"' : '') + '><span class="sub2">' + esc(x.hm) + '</span><span class="sub2 ln">' + LANE[e.lane] + '</span><span data-event-template="' + esc(e.lane==='source' && e.ref?.gene && e.id==='gene:'+e.ref.gene?'gene-file':e.lane==='data' && e.ref?.observation && /^observation:\d+$/.test(e.id)?'observation':e.lane==='data' && e.ref?.commit && /^commit:\d+$/.test(e.id)?'commit':'') + '">' + esc(plain(e)) + '</span><span>' + (go ? '<button class="link"' + go + '>查看</button>' : '') + '</span></div>'; }).join('') +
          (shown.length > 20 && st.diaryAll !== d ? '<div style="padding-left:1em"><button class="link" data-dy-all="' + esc(d) + '">' + (paged ? '本页还有 ' : '这一天还有 ') + (shown.length - 20) + ' 条，展开</button></div>' : shown.length > 400 ? '<div class="sub2" style="padding-left:1em" data-ptds-ui="scad200e944b4">只列出前 400 条，用上面的筛选缩小范围。</div>' : '') + '</details>';
      }).join('') + (order.length > lim ? '<div><button class="chip" id="eg-more" data-ptds-inline><!--ptds-ui:sd53588ed7ccc-->看更早的 <!--/ptds-ui-->' + (order.length - lim) + ' 天</button></div>' : order.length ? '' : '<div class="sub2" data-ptds-ui="sebd0c2551068">还没有记录。</div>');
    },
    renderGraphRecords: function () {
      var st=C.st,esc=C.esc,key=st.key,tab=['data','state','auth'].indexOf(st.xhTab)>=0?st.xhTab:null;
      var page=st.graphPage;
      if(!page||page.key!==key||page.lane!==tab)page=st.graphPage={key:key,lane:tab,cursors:[''],index:0};
      var summaryPath='/api/graph/read?view=summary&key='+encodeURIComponent(key),summary;
      // This boundary is captured after page identity is established. Late reads
      // from a different tab/cursor must not redraw the current selection.
      try { summary=readCached(summaryPath); }
      catch(e){if(!LIVE.renderReadError(e,function(){LIVE.renderGraph();}))throw e;return;}
      var counts=summary.counts||{},tabs=[['data','数据记录','数据从哪来、哪天入库、哪个版本'],['state','状态记录','每次计算用了哪些数据、按哪版规则'],['auth','授权记录','给了谁、怎么给、给了什么、结果']];
      document.getElementById('view').innerHTML='<section class="box" id="eg-diary"><div class="xh-tabs" role="group" aria-label="三类记录" data-ptds-ui-aria-label="sbe1b7b96085c">'+tabs.map(function(t){
        return '<button class="xh-t" data-xh-tab="'+t[0]+'" aria-expanded="'+(tab===t[0])+'"'+(t[0]==='auth'?' data-sem="SEM-30"':'')+'><b>'+t[1]+'</b><span class="n">'+esc(counts[t[0]]==null?'—':counts[t[0]])+'</span><span style="justify-self:end;display:inline-flex;transform:rotate('+(tab===t[0]?180:0)+'deg)">'+C.ic('chevron-down')+'</span><span class="sub2">'+t[2]+'</span></button>';
      }).join('')+'</div><div style="display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin-top:16px"><button class="link" id="graph-history-refresh" data-ptds-ui="s0d5f2d169fae">读取最新记录</button>'+(tab?'<span class="sub2" data-ptds-ui="se0f55acaa269">每页最多 50 条 · 翻页期间保持本次记录范围</span>':'')+'</div>'+(tab?'<div class="xh-body" id="graph-history-body"></div><div style="display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin-top:16px"><button class="btn2" id="graph-page-prev"'+(page.index?'':' disabled')+'>上一页</button><span class="sub2" id="graph-page-count">第 '+(page.index+1)+' 页</span><button class="btn2" id="graph-page-next" disabled data-ptds-ui="s8a8542f69648">下一页</button></div>':'')+'</section>';
      document.querySelectorAll('[data-xh-tab]').forEach(function(b){b.onclick=function(){st.xhTab=st.xhTab===b.dataset.xhTab?null:b.dataset.xhTab;st.graphPage=null;st.diaryDay=null;st.diaryAll=null;LIVE.renderGraph();};});
      document.getElementById('graph-history-refresh').onclick=function(){
        // Discard only this instance's graph read cache. No mutation or sync is replayed.
        var suffix='&key='+encodeURIComponent(key);
        var paths=Array.from(viewReads.keys()).filter(function(path){return path.indexOf('/api/graph/read?')===0&&path.split('&').indexOf(suffix.slice(1))>=0;});
        if(paths.some(function(path){return !!viewReads.get(path).promise;}))return;
        paths.forEach(function(path){viewReads.delete(path);readWaiters.delete(path);});
        st.graphPage=null;st.diaryDay=null;st.diaryAll=null;LIVE.renderGraph();
      };
      if(st.graphJump){var jump=document.getElementById(st.graphJump);st.graphJump=null;if(jump)setTimeout(function(){if(jump.isConnected)jump.scrollIntoView({block:'start'});},0);}
      if(!tab)return;
      var previous=document.getElementById('graph-page-prev'),next=document.getElementById('graph-page-next');
      previous.onclick=function(){if(page!==st.graphPage||!page.index)return;page.index--;st.diaryDay=null;st.diaryAll=null;LIVE.renderGraph();};
      var path='/api/graph/read?view=events&key='+encodeURIComponent(key)+'&lane='+tab+'&limit=50'+(page.cursors[page.index]?'&cursor='+encodeURIComponent(page.cursors[page.index]):''),result;
      var host=document.getElementById('graph-history-body');
      try { result=readCached(path); }
      catch(e){
        document.getElementById('graph-history-refresh').disabled=!!e.loading;
        if(e&&/^GRAPH_CURSOR_/.test(e.code||'')){
          host.innerHTML='<p role="status" data-ptds-ui="sa6add0dcab3c">这次记录范围已结束，请点击“读取最新记录”重新开始。历史记录仍然保留。</p>';
          return;
        }
        if(!LIVE.renderReadError(e,function(){LIVE.renderGraph();},host))throw e;
        // This is an inline history region, not a drawer with a close action.
        var close=host.querySelector('.ptds-read-close');if(close)close.remove();
        return;
      }
      var items=result.items||[];
      if(page.index===0&&result.first_cursor&&!page.cursors[0]){
        page.cursors[0]=result.first_cursor;
        // Both paths describe the same immutable first page; don't fetch it
        // again just to expand a day or navigate back from page two.
        var firstEntry=viewReads.get(path);if(firstEntry)viewReads.set(path+'&cursor='+encodeURIComponent(result.first_cursor),firstEntry);
        pruneViewReads();
      }
      page.cursors[page.index+1]=result.next_cursor||null;
      next.disabled=!result.next_cursor;
      next.onclick=function(){if(page!==st.graphPage||!page.cursors[page.index+1])return;page.index++;st.diaryDay=null;st.diaryAll=null;LIVE.renderGraph();};
      document.getElementById('graph-page-count').textContent='第 '+(page.index+1)+' 页 · 本页 '+items.length+' 条 / 本次共 '+(result.total==null?'—':result.total)+' 条';
      if(tab==='auth'){
        host.innerHTML=(items.length?'<div class="xh-rec" data-sem="SEM-30"><div class="xh-r hd"><span data-ptds-ui="s8b6ff498515b">时间</span><span data-ptds-ui="s53f92c063963">对象</span><span data-ptds-ui="s184437f770fb">方式 · 通道</span><span data-ptds-ui="s714612c2d5ad">披露级别</span><span data-ptds-ui="s4b3a77b9804d">内容摘要</span><span data-ptds-ui="sbb7ef73495dd">结果</span></div>'+items.map(function(r){return '<details class="xh-rd" data-access-template="'+esc(r.action==='CREATE' && r.via==='SYSTEM' && ['G-001','G-002'].includes(r.grant)?r.grant:'')+'"><summary class="xh-r"><span class="sub2">'+esc(String(r.when||'').slice(5,16))+'</span><span>'+esc(r.obj)+'</span><span>'+esc(r.how)+'</span><span>'+esc(r.level)+'</span><span class="sub2">'+esc(r.summary)+'</span><span>'+esc(r.result)+'</span></summary><div class="sub2 xh-more" data-ptds-inline><!--ptds-ui:s91ead424189d-->记录号 <!--/ptds-ui-->'+esc(r.id||'')+(r.grant?'<!--ptds-ui:activity_24f8648ce192--> · 授权 <!--/ptds-ui-->'+esc(r.grant):'')+'<!--ptds-ui:activity_5a26eda5ae60--> · 时间 <!--/ptds-ui-->'+esc(r.when||'')+' · '+(r.egress?'<!--ptds-ui:activity_1630799936e0-->数据离开了本机<!--/ptds-ui-->':'<!--ptds-ui:activity_7184c4204876-->没有数据离开本机<!--/ptds-ui-->')+(r.reason?'<!--ptds-ui:activity_534fe66e3b71--> · 原因 <!--/ptds-ui-->'+esc(r.reason):'')+'</div></details>';}).join('')+'</div>':'<div class="sub2" data-ptds-ui="s290f0b0a6712">还没有授权或出域记录。</div>')+(result.hidden_count?'<p class="sub2" data-ptds-inline><!--ptds-ui:s268ec6902063-->另有 <!--/ptds-ui-->'+esc(result.hidden_count)+' 条测试时记的授权已从列表隐藏，原记录保留</p>':'');
      } else {
        host.innerHTML=items.length?LIVE.diaryHtml(items,'ALL',true):'<div class="sub2" data-ptds-inline><!--ptds-ui:sd2342efd86fa-->还没有<!--/ptds-ui-->'+(tab==='data'?'数据':'计算')+'记录。</div>';
        host.querySelectorAll('[data-eg-go]').forEach(function(b){b.onclick=function(){var p=b.dataset.egGo.split('|');LIVE.openTrace(p[0],p[1]);};});
        host.querySelectorAll('[data-eg-obs]').forEach(function(b){b.onclick=function(){LIVE.openEvidenceObservation(b.dataset.egObs);};});
        host.querySelectorAll('details.dy').forEach(function(d){d.ontoggle=function(){if(d.open)st.diaryDay=d.dataset.day;else if(st.diaryDay===d.dataset.day)st.diaryDay=null;};});
        host.querySelectorAll('[data-dy-all]').forEach(function(b){b.onclick=function(){st.diaryAll=b.dataset.dyAll;st.diaryDay=b.dataset.dyAll;LIVE.renderGraph();};});
      }
      if(st.fw)LIVE.renderFw();
      if(st.graphJump){var jt=document.getElementById(st.graphJump);st.graphJump=null;if(jt)setTimeout(function(){if(jt.isConnected)jt.scrollIntoView({block:'start'});},0);}
    },
    renderGraph: function () {
      if (!document.getElementById('eg-css')) { var stl = document.createElement('style'); stl.id = 'eg-css'; stl.textContent = LIVE.GRAPH_CSS + LIVE.KG_CSS + LIVE.RC_CSS; document.head.appendChild(stl); }
      var esc = C.esc, ic = C.ic, st = C.st, g = {};
      // EVIDENCE_GRAPH_READ_R01: the map has its own read model. Do not download
      // every historical event and authorization record and then discard them.
      if (st.graphJump === 'eg-diary') st.xhView = 'records';
      if (st.xhView !== 'records') {
        document.getElementById('view').innerHTML = LIVE.kgHtml();
        if (!st.fw) LIVE.kgPath = null;
        LIVE.kgBind();
        if (st.fw) LIVE.renderFw();
        return;
      }
      if(LIVE.graphReadV2()){LIVE.renderGraphRecords();return;}
      try { g = readCached('/api/graph?key=' + encodeURIComponent(st.key)); } catch (err) { if(err&&(err.viewPending||err.code==='VIEW_CHANGED'))throw err; g = { error: err.code, events: [], timepoints: [], metric: { traceable: 0, total: 0, not_traceable: [] } }; }
      var cards = g.cards || [];
      if (C.S().instance.kind === 'REAL') cards = cards.filter(function (c) { return c.card_id !== 'sjia-mas'; }).concat(cards.filter(function (c) { return c.card_id === 'sjia-mas'; })); /* 个人基座里 sJIA 关注卡是隐藏的，放最后 */
      LIVE.graphCards = cards;
      var ccard = st.graphCard && cards.some(function (c) { return c.card_id === st.graphCard; }) ? st.graphCard : (cards[0] || {}).card_id;
      var cobj = cards.filter(function (c) { return c.card_id === ccard; })[0];
      var tps = cobj ? cobj.timepoints : [], sel = st.graphTp && tps.some(function (t) { return t.tp === st.graphTp; }) ? st.graphTp : (tps.length ? tps[tps.length - 1].tp : null);
      var m = g.metric || {}, LANE = { source: '数据源', data: '数据', state: '计算', auth: '授权' }, lane = st.graphLane && st.graphLane !== 'ALL' ? st.graphLane : 'ALL';
      var cnt = { source: 0, data: 0, state: 0, auth: 0 }; (g.events || []).forEach(function (e) { cnt[e.lane] = (cnt[e.lane] || 0) + 1; });
      LIVE.graphM = m;
      var html = ''; /* 产品负责人 08:57：页首这行（结论数 / 系统自检）删 */
      /* 星痕（产品负责人 2026-10-15 r61/r62）：最上面三类记录卡（数据记录 / 状态记录 / 授权记录），平时折叠，点卡片展开明细，再点收起；下面是证据关系图。
         三类都只用已有的真实记录：数据记录 = 数据源和入库，状态记录 = 每次计算，授权记录 = 原来星簇“授权记录”那张出域流水表（测试时记、已隐藏的不列，只报条数）。 */
      var evs = g.events || [], dEv = evs.filter(function (e) { return e.lane === 'source' || e.lane === 'data'; }), sEv = evs.filter(function (e) { return e.lane === 'state'; });
      var recs = []; try { recs = readCached('/api/cluster/records?key=' + encodeURIComponent(st.key)) || []; } catch (err) { if(err&&(err.viewPending||err.code==='VIEW_CHANGED'))throw err; recs = []; }
      var aRec = recs.filter(function (r) { return !r.hidden; }), aHid = recs.length - aRec.length;
      var TABS = [['data', '数据记录', dEv.length, '数据从哪来、哪天入库、哪个版本'], ['state', '状态记录', sEv.length, '每次计算用了哪些数据、按哪版规则'], ['auth', '授权记录', aRec.length, '给了谁、怎么给、给了什么、结果']];
      var tab = st.xhTab || null, body = '';
      if (tab === 'data' || tab === 'state') { var list = tab === 'data' ? dEv : sEv; body = list.length ? LIVE.diaryHtml(list, 'ALL') : '<div class="sub2" data-ptds-inline><!--ptds-ui:sd2342efd86fa-->还没有<!--/ptds-ui-->' + (tab === 'data' ? '数据' : '计算') + '记录。</div>'; }
      if (tab === 'auth') body = (aRec.length ? '<div class="xh-rec" data-sem="SEM-30"><div class="xh-r hd"><span data-ptds-ui="s8b6ff498515b">时间</span><span data-ptds-ui="s53f92c063963">对象</span><span data-ptds-ui="s184437f770fb">方式 · 通道</span><span data-ptds-ui="s714612c2d5ad">披露级别</span><span data-ptds-ui="s4b3a77b9804d">内容摘要</span><span data-ptds-ui="sbb7ef73495dd">结果</span></div>' + aRec.map(function (r, k) {
          return '<details class="xh-rd"><summary class="xh-r"><span class="sub2">' + esc(String(r.when || '').slice(5, 16)) + '</span><span>' + esc(r.obj) + '</span><span>' + esc(r.how) + '</span><span>' + esc(r.level) + '</span><span class="sub2">' + esc(r.summary) + '</span><span>' + esc(r.result) + '</span></summary>' +
            '<div class="sub2 xh-more" data-ptds-inline><!--ptds-ui:s91ead424189d-->记录号 <!--/ptds-ui-->' + esc(r.id || '') + (r.grant ? '<!--ptds-ui:activity_24f8648ce192--> · 授权 <!--/ptds-ui-->' + esc(r.grant) : '') + '<!--ptds-ui:activity_5a26eda5ae60--> · 时间 <!--/ptds-ui-->' + esc(r.when || '') + ' · ' + (r.egress ? '<!--ptds-ui:activity_1630799936e0-->数据离开了本机<!--/ptds-ui-->' : '<!--ptds-ui:activity_7184c4204876-->没有数据离开本机<!--/ptds-ui-->') + (r.reason ? '<!--ptds-ui:activity_534fe66e3b71--> · 原因 <!--/ptds-ui-->' + esc(r.reason) : '') + '</div></details>'; }).join('') + '</div>'
        : '<div class="sub2" data-ptds-ui="s290f0b0a6712">还没有授权或出域记录。</div>') + (aHid ? '<div class="sub2" style="margin-top:8px" data-ptds-inline><!--ptds-ui:s268ec6902063-->另有 <!--/ptds-ui-->' + aHid + ' 条测试时记的授权已从列表隐藏，原记录保留</div>' : '');
      html += '<section class="box" id="eg-diary"><div class="xh-tabs" role="group" aria-label="三类记录" data-ptds-ui-aria-label="sbe1b7b96085c">' + TABS.map(function (t) {
        return '<button class="xh-t" data-xh-tab="' + t[0] + '" aria-expanded="' + (tab === t[0]) + '"' + (t[0] === 'auth' ? ' data-sem="SEM-30"' : '') + '><b>' + t[1] + '</b><span class="n">' + t[2] + '</span>' + '<span style="justify-self:end;display:inline-flex;transform:rotate(' + (tab === t[0] ? 180 : 0) + 'deg)">' + C.ic('chevron-down') + '</span>' + '<span class="sub2">' + t[3] + '</span></button>'; }).join('') + '</div>' +
        (tab ? '<div class="xh-body">' + body + '</div>' : '') + '</section>';
      document.getElementById('view').innerHTML = html;
      document.querySelectorAll('[data-eg-go]').forEach(function (b) { b.onclick = function () { var p = b.dataset.egGo.split('|'); LIVE.openTrace(p[0] || ccard, p[1]); }; });
      document.querySelectorAll('[data-xh-tab]').forEach(function (b) { b.onclick = function () { st.xhTab = st.xhTab === b.dataset.xhTab ? null : b.dataset.xhTab; st.graphMore = false; var y = window.scrollY; LIVE.renderGraph(); window.scrollTo(0, y); }; });
      document.querySelectorAll('[data-eg-obs]').forEach(function (b) { b.onclick = function () { LIVE.openEvidenceObservation(b.dataset.egObs); }; });
      document.querySelectorAll('[data-egv-href]').forEach(function (b) { b.onclick = function () { window.open(b.dataset.egvHref, '_blank', 'noopener'); }; });
      var more = document.getElementById('eg-more'); if (more) more.onclick = function () { st.graphMore = true; var y = window.scrollY; LIVE.renderGraph(); window.scrollTo(0, y); };
      var hb = document.getElementById('eg-hist'); if (hb) hb.onclick = function () { st.graphHist = !st.graphHist; LIVE.renderGraph(); };
      document.querySelectorAll('details.dy').forEach(function (d) { d.ontoggle = function () { if (d.open) st.diaryDay = d.dataset.day; else if (st.diaryDay === d.dataset.day) st.diaryDay = null; }; });
      document.querySelectorAll('[data-dy-all]').forEach(function (b) { b.onclick = function () { st.diaryAll = b.dataset.dyAll; st.diaryDay = b.dataset.dyAll; var y = window.scrollY; LIVE.renderGraph(); window.scrollTo(0, y); }; });
      LIVE.bindPack();
      LIVE.kgBind();
      if (st.fw) LIVE.renderFw(); else LIVE.kgPath = null;
      if (st.graphJump) { var jt = document.getElementById(st.graphJump); st.graphJump = null; if (jt) setTimeout(function () { jt.scrollIntoView({ block: 'start' }); }, 0); }
    },
    /* 系统自检（产品负责人 2026-10-14 定）：页首一行“上次全部通过 · 再查一次”，点开 3 行打勾。每个数自己的核对放在来龙去脉面板④里。
       结果只显示接口给的；证据包照旧在后台生成存档，界面不提供下载。 */
    selfCheckHtml: function () { if (globalThis.PTDS_TRIAL_UI && !PTDS_TRIAL_UI.can('pack')) return '';
      var esc = C.esc, ic = C.ic, st = C.st, last = null;
      if (st.packBusy) return '<span class="sub2 eg-sc" data-ptds-ui="s29fd7d8b8c83">正在自检：跑全部自动测试并核对，约 20 秒</span>';
      try { last = readCached('/api/evidence/last').last; } catch (err) { if(err&&(err.viewPending||err.code==='VIEW_CHANGED'))throw err; last = null; }
      if (!last) return '<span class="sub2 eg-sc" data-ptds-inline><!--ptds-ui:sc1e3fba43e8c-->系统自检：还没查过 · <!--/ptds-ui--><button class="link" id="ev-go" data-ptds-ui="s7048629b47fa">查一次</button></span>';
      var at = C.tzTime(last.at) || '', t = last.checks[0], lb = last.checks[1], sc = last.checks[2], bad = last.checks.filter(function (c) { return !c.ok; }).length;
      var row = function (ok, txt) { return '<div class="' + (ok ? '' : 'no') + '">' + (ok ? ic('check') : ic('circle-alert')) + ' ' + txt + '</div>'; };
      return '<details class="more eg-sc"><summary class="sub2" data-ptds-inline><!--ptds-ui:s3a551bd460e4-->系统自检：<!--/ptds-ui-->' + (bad ? '上次有 ' + bad + ' 项没通过' : '上次全部通过') + '（' + esc(String(at).slice(5, 16)) + '） · <button class="link" id="ev-go" data-ptds-ui="sa76642dd0ecf">再查一次</button></summary><div class="sub2 eg-ck">' +
        row(t.ok, t.ran ? '自动测试 ' + esc(t.passed + ' / ' + t.total) + ' 条通过' : '这次没跑自动测试') +
        row(lb.ok, lb.ok ? '功能标签没有夸大（标“可用”的都真能用）' : lb.n + ' 项功能标签高于实际证据（标签由你来定）') +
        row(sc.ok, sc.ok ? '导出的证据包里没有健康数值、没有密钥' : '证据包自检没通过，这次没有出包') + '</div></details>';
    },
    bindPack: function () {
      var st = C.st, go = document.getElementById('ev-go');
      if (!go) return;
      go.onclick = function (ev) {
        ev.preventDefault(); ev.stopPropagation();
        if (st.packBusy) return;
        st.packBusy = true;
        var y = window.scrollY; LIVE.renderGraph(); window.scrollTo(0, y);
        fetch('/api/evidence/pack', { method: 'POST', headers: { 'X-PTDS': '1', 'Content-Type': 'application/json' }, body: JSON.stringify({ tests: true }) })
          .then(function (resp) { return resp.json(); })
          .catch(function (err) { return { ok: false, error: 'NETWORK', detail: String(err) }; })
          .then(function (res) {
            st.packBusy = false;
            if (C.st.app === 'torch' && C.st.tview === 'graph') { var y2 = window.scrollY; LIVE.renderGraph(); window.scrollTo(0, y2); }
            C.toast(res.ok ? '自检完成' : '自检没有完成（' + (res.error || '') + '）');
          });
      };
    },
    /* 页面上有没填完的输入（更正、向导、查询框……）：这次不自动刷新，免得把正在填的内容冲掉 */
    editing: function () {
      if (window.PTDS_STATE_PUSH && window.PTDS_STATE_PUSH.isEditing()) return true;
      var a = document.activeElement, st = C.st;
      if (st.app === 'torch' && st.tview === 'srcgroup' && st.museOpen) return true;
      if (st.app === 'torch' && st.tview === 'srcgroup' && st.sourceDevice && document.querySelector('#view details[open]')) return true;
      if (a && /^(INPUT|TEXTAREA|SELECT)$/.test(a.tagName) && a.type !== 'checkbox' && a.type !== 'radio') return true;
      if (st.tdetail && st.tdetail.mode && st.tdetail.mode !== 'view') return true;
      if (st.view === 'eng' && st.eng && st.eng.step > 0) return true;
      if (LIVE.kgDragging) return true;
      return Array.prototype.some.call(document.querySelectorAll('#view input, #view textarea'), function (el) {
        return el.type !== 'checkbox' && el.type !== 'radio' && el.type !== 'file' && el.value !== el.defaultValue; });
    },
    ouraErr: function (code) {
      return ({ OURA_UNREACHABLE: '连不上 Oura（可能没联网），已保存的数据不受影响，联网后会自动补取',
        OURA_UNAVAILABLE: 'Oura 服务暂时不可用，稍后会自动再试', OURA_UNAUTHORIZED: '授权失效了，请断开后重新接入',
        OURA_NOT_CONNECTED: '还没有接入', OURA_REQUEST_FAILED: 'Oura 拒绝了这次请求，稍后会自动再试' })[code] || ('没有成功（' + code + '）');
    },
    saveErr: function (err) {
      var zh = { SERVER_DOWN: '本机服务没在运行，请双击「启动PTDS.command」后再点一次（填好的内容还在）', TIME_INVALID: '请填日期和时刻', TIME_FUTURE: '日期在今天之后，请核对', VALUE_INVALID: '数值格式不对（只写数字，不要以 0 开头）', UNIT_INVALID: '单位不认识',
        UNIT_UNKNOWN: '单位不认识', CODE_UNKNOWN: '指标不认识', TABLE_INVALID: '表格格式不对', TABLE_EMPTY: '表格是空的',
        REQUEST_CONFLICT: '这份内容之前用别的方式保存过' }[err.code];
      return zh ? zh + (err.detail && /[一-龥]/.test(err.detail) && zh.indexOf(err.detail) < 0 ? '（' + err.detail + '）' : '') : (err.detail && /[一-龥]/.test(err.detail) ? err.detail : '出错了（' + err.code + '）');
    },
    /* 提醒"知道了"：写进星轨（只追加）；回放实例不写 */
    ack: async function (key, instanceKey) {
      instanceKey=instanceKey||C.st.key;
      if (C.isReplay()) { C.st.acked[key]=true;return true; }
      try { (await call('POST', '/api/track/ack', { key: instanceKey, dedupe_key: key })); (await LIVE.refresh(instanceKey));C.st.acked[key]=true;return true; } catch (err) { throw err; }
    },
    /* 录入回执：星轨这次按新数据算了哪些卡 */
    receiptCards: function (res) { return window.PTDS_COMPUTE ? window.PTDS_COMPUTE.receipt(res,C) : '已保存到我的数据'; },
    /* 表格导入：读本机的 CSV → 预览（逐行检查）→ 核对后整份交给星炬（服务端再查一遍，有错整份不存） */
    parseCsv: function (text) {
      var rows = [], row = [], cell = '', q = false, i, ch;
      text = text.replace(/^﻿/, '');
      for (i = 0; i < text.length; i++) {
        ch = text[i];
        if (q) { if (ch === '"') { if (text[i + 1] === '"') { cell += '"'; i++; } else q = false; } else cell += ch; }
        else if (ch === '"') q = true;
        else if (ch === ',') { row.push(cell); cell = ''; }
        else if (ch === '\n' || ch === '\r') { if (ch === '\r' && text[i + 1] === '\n') i++; row.push(cell); cell = ''; if (row.some(function (x) { return x.trim(); })) rows.push(row); row = []; }
        else cell += ch;
      }
      row.push(cell); if (row.some(function (x) { return x.trim(); })) rows.push(row);
      return rows;
    },
    loadTable: function (file, e, rerender) {
      if (/\.(xlsx|xls|numbers|xml)$/i.test(file.name)) { C.toast('Excel、Numbers 表格请先"另存为 CSV（UTF-8）"再导入'); return; }
      var rd = new FileReader();
      rd.onload = function () {
        var text = String(rd.result || ''), grid = LIVE.parseCsv(text), head = (grid[0] || []).map(function (h) { return h.trim().toLowerCase(); });
        if (head.indexOf('code') < 0 || head.indexOf('value') < 0) { C.toast('表头要有 code、value 等列，可以先下载模板'); return; }
        if (grid.length < 2) { C.toast('表格里没有数据行'); return; }
        var objs = grid.slice(1).map(function (r) { var o = {}; head.forEach(function (h, k) { o[h] = (r[k] || '').trim(); });
          return { code: o.code, value: o.value, unit: o.unit || '', comparator: o.comparator || '', observed_at: o.observed_at || '', observed_date: o.observed_date || '', tz: o.tz || '' }; });
        var checked;
        try { checked = C.MockTorch.checkTable(objs); } catch (err) { if(err&&(err.viewPending||err.code==='VIEW_CHANGED'))throw err; checked = objs.map(function (r, k) { return { n: k + 1, row: r, err: null }; }); }
        e.table = { name: file.name, rows: checked, text: text }; rerender();
      };
      rd.onerror = function () { C.toast('这份文件读不出来'); };
      rd.readAsText(file, 'utf-8');
    },
    pickTable: function (e, rerender) {
      var f = document.getElementById('t-file'); if (!f) return;
      f.value = ''; f.onchange = function () { if (f.files[0]) LIVE.loadTable(f.files[0], e, rerender); }; f.click();
    },
    dropTable: function (e, rerender) {
      var dz = document.querySelector('.drop'); if (!dz) return;
      dz.ondragover = function (ev) { ev.preventDefault(); };
      dz.ondrop = function (ev) { ev.preventDefault(); var file = ev.dataTransfer.files[0]; if (file) LIVE.loadTable(file, e, rerender); };
    },
    tableTemplate: function () {
      var tz = ((C.S() || {}).instance || {}).tz || 'Asia/Shanghai';
      var text = 'code,value,unit,comparator,observed_at,observed_date,tz\nFERRITIN,450,ng/mL,,2026-10-01T08:00:00+08:00,,\nCRP,12,mg/L,,,2026-10-01,' + tz + '\n';
      var a = document.createElement('a'); a.href = URL.createObjectURL(new Blob(['﻿' + text], { type: 'text/csv' }));
      a.download = 'PTDS-表格模板.csv'; document.body.appendChild(a); a.click(); setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 1000);
      C.toast('已下载模板：第一行是表头，下面两行是例子，换成你的数据');
    },
    saveTableFile: async function (e, rerender) {
      var t = e.table, key=C.st.key, res;
      if (!t || !t.review || t.review.text !== t.text || t.review.key !== C.st.key) { C.toast('请先核对表格，再确认保存'); return; }
      // One identifier per reviewed submission; retries retain it, a newly selected file gets a new review.
      if (!t.requestId) t.requestId = 'CSV-' + crypto.randomUUID();
      try { res = (await C.MockTorch.saveTable(t.text, C.isLive() && LIVE.realNature() ? 'REAL' : null, t.requestId,key)); }
      catch (err) { if(err&&(err.viewPending||err.code==='VIEW_CHANGED'))throw err; C.toast('尚未确认保存：' + LIVE.saveErr(err)); return; }
      t.savedResult=res;
      if(C.st.key!==key||C.st.entry!==e||e.table!==t)return res;
      var n = { CREATED: 0, REVISED: 0, UNCHANGED: 0 }; (res.results || []).forEach(function (r) { n[r.outcome] = (n[r.outcome] || 0) + 1; });
      C.toast('已导入 ' + (res.results || []).length + ' 行：新增 ' + n.CREATED + '，更正 ' + n.REVISED + '，无变化 ' + n.UNCHANGED + '。' + LIVE.receiptCards(res), 'csv-import-result');
      e.table = null; C.st.entry = null; C.goTorch('data');
    },
    yn: function (v) { return v === 'true' || v === true ? '是' : v === 'false' || v === false ? '否' : v; },
    /* 数据详情里的版本：星炬只追加，旧版保留；每一版标出被哪几次计算用过 */
    versionsHtml: function (o, ver) {
      metricCss();
      var key=C.st.key, detail=C.st.tdetail, oid=o.ref.split('@')[0], epoch=readEpoch;
      var stamp=JSON.stringify([key,oid,epoch,LIVE.baselineVersion(C.S())]);
      var entry=detail && detail._versions;
      if(!entry || entry.stamp!==stamp){
        entry={stamp:stamp,id:'data-versions-'+rid(),status:'loading'};
        if(detail)detail._versions=entry;
        var current=function(){return C.st.key===key && C.st.tdetail===detail && detail && detail._versions===entry && readEpoch===epoch && C.st.app==='torch' && C.st.tview==='detail';};
        var content=function(){
          if(entry.status==='ready')return LIVE.versionRowsHtml(entry.versions,entry.currentRevision)+(entry.page&&entry.page.total>entry.page.limit?'<div class="opts"><button class="chip" data-version-prev'+(!entry.page.previous_cursor?' disabled':'')+'>较新版本</button><span class="sub2">'+(entry.page.offset+1)+'–'+Math.min(entry.page.offset+entry.page.limit,entry.page.total)+' / '+entry.page.total+'</span><button class="chip" data-version-next'+(!entry.page.has_more?' disabled':'')+'>较早版本</button></div>':'');
          if(entry.status==='error')return LIVE.readingHtml('inline','error','版本暂未读取，请重试。')+'<button class="link" data-version-retry="1" data-ptds-ui="sb8784c8dd563">重试</button>';
          return LIVE.readingHtml('inline');
        };
        var paint=function(){
          var host=document.getElementById(entry.id);if(!current()||!host)return;
          host.innerHTML=content();metricVersionLayout();
          var retry=host.querySelector('[data-version-retry]');if(retry)retry.onclick=LIVE.action(function(){entry.cursor=null;return load();});
          if(entry.page)['prev','next'].forEach(function(dir){var b=host.querySelector('[data-version-'+dir+']');if(b)b.onclick=LIVE.action(function(){entry.cursor=entry.page[dir==='prev'?'previous_cursor':'next_cursor'];return load();});});
        };
        var load=function(){
          if(entry.busy || !current())return;
          entry.busy=true;entry.status='loading';paint();
          readView((LIVE.dataReadEnabled&&LIVE.dataReadEnabled())?LIVE.dataPath('versions',{oid:oid,limit:50,cursor:entry.cursor}):'/api/torch/versions?key='+encodeURIComponent(key)+'&oid='+encodeURIComponent(oid))
            .then(function(r){if(!current())return;if(LIVE.dataReadEnabled&&LIVE.dataReadEnabled())LIVE.validateDataRead(r,LIVE.dataPath('versions',{oid:oid,limit:50,cursor:entry.cursor}));var vs=(LIVE.dataReadEnabled&&LIVE.dataReadEnabled())?r.items:r.versions;if(!Array.isArray(vs))throw Error('VERSIONS_INVALID');if(!current())return;entry.versions=vs;entry.page=(LIVE.dataReadEnabled&&LIVE.dataReadEnabled())?r:null;entry.currentRevision=r.current_revision;entry.status='ready';})
            .catch(function(){if(current())entry.status='error';})
            .finally(function(){entry.busy=false;paint();});
        };
        entry.content=content;entry.paint=paint;
        // Start after the loading shell is mounted. Never block the rendering call stack.
        setTimeout(load,0);
      }
      setTimeout(entry.paint,0); // Rebind retry after edit/cancel rerenders the same detail.
      return '<div id="'+entry.id+'" data-version-panel="1">'+entry.content()+'</div>';
    },
    versionRowsHtml: function (vs, currentRevision) {
      var esc=C.esc;
      if(!vs.length)return '<div class="sub2" role="status" data-ptds-ui="s2c2b10649a71">暂无可读取的版本记录。</div>';
      var last = currentRevision===undefined?vs[vs.length - 1].revision:currentRevision;
      setTimeout(metricVersionLayout, 0);
      return '<div class="rlist mx-versions" data-sem="SEM-03">' + vs.slice().reverse().map(function (v) {
        var tag = v.status !== 'ACTIVE' ? '已删除（历史保留）' : v.revision === last ? '当前' : '旧版，保留';
        return '<div data-mx-version="' + esc(JSON.stringify({ revision:v.revision, tag:tag, value:v.value, unit:v.unit, comparator:v.comparator, saved_at:v.saved_at, source:v.source_zh, runs:v.runs, cards:v.cards, status:v.status })) + '"><span>第 ' + v.revision + ' 版 · ' + tag + '<span class="sub2"> · ' + esc(C.tzTime(v.saved_at, true)) + ' · ' + esc(v.source_zh || '') + (v.runs.length ? ' · 被 ' + ((v.cards && v.cards.length) ? v.cards.join('、') : v.runs.map(function (r) { return '计算 #' + r; }).join('、')) + ' 用过' : ' · 现有状态卡暂未包含该数据') + '</span></span><span>' + (v.status !== 'ACTIVE' ? '—' : esc((v.comparator || '') + LIVE.yn(v.value) + (v.unit ? ' ' + v.unit : ''))) + '</span></div>';
      }).join('') + '</div>';
    },
    /* 证据图谱连线图：一条结论从原件 → 星炬正式记录（哪一版）→ 交给星轨 → 计算 → 结论 → 之后的提醒与授权读取。
       每个节点、每条边都来自 trace 接口里已有的字段，不推断、不补边。 */
    EGV_CSS: '.egv-wrap{overflow-x:auto;margin:var(--primitive-space-2) 0}.egv{display:block}.egv .n rect{fill:var(--component-currentCard-bg);stroke:var(--theme-line-control);stroke-width:1}' +
      '.egv .n.hist rect{stroke-dasharray:4 3}.egv .n.go{cursor:pointer}.egv .n.go:hover rect{stroke:var(--theme-text-secondary)}.egv .n .t{fill:var(--theme-text-primary);font-size:12.5px}.egv .n .s{fill:var(--theme-text-tertiary);font-size:11px}' +
      '.egv .n.lv-ALERT rect{stroke:var(--theme-level-alert-text);stroke-width:1.5}.egv .n.lv-WATCH rect{stroke:var(--theme-level-watch-text);stroke-width:1.5}.egv .n.warn rect{stroke:var(--theme-level-watch-text)}' +
      '.egv .e{fill:none;stroke:var(--theme-text-tertiary);stroke-width:1;opacity:.7}.egv .e.hist{stroke-dasharray:4 3;opacity:.45}.egv .h{fill:var(--theme-text-secondary);font-size:11.5px;letter-spacing:.04em}',
    traceGraph: function (t) {
      var esc = C.esc, st = C.st;
      if (!document.getElementById('egv-css')) { var s0 = document.createElement('style'); s0.id = 'egv-css'; s0.textContent = LIVE.EGV_CSS; document.head.appendChild(s0); }
      var KIND = { OCR: '化验单原件', TABLE: '表格导入', MANUAL: '手工录入', OURA: 'Oura 官方接口', AH: '苹果健康', SYN: '合成数据', SOMALOOP: 'Somaloop 腕带' };
      var cols = [[], [], [], [], [], []], edges = [], seen = {};
      var node = function (col, key, n) { if (seen[key]) return seen[key]; n.key = key; n.col = col; cols[col].push(n); seen[key] = n; return n; };
      var cut = function (s, n) { s = String(s == null ? '' : s); return s.length > n ? s.slice(0, n - 1) + '…' : s; };
      var fit = function (s, px, fs) { s = String(s == null ? '' : s); var w = 0, out = ''; for (var i = 0; i < s.length; i++) { var cw = s.charCodeAt(i) > 0x2e80 ? fs : fs * 0.6; if (w + cw > px - fs) { return out + '…'; } w += cw; out += s[i]; } return out; };
      var inputs = st.graphHist ? t.inputs : t.inputs.filter(function (i) { return i.role !== 'HISTORY'; });
      var run = node(3, 'run', { title: '计算 #' + t.run.run_id, sub: t.run.trigger_zh + (t.run.history.length > 1 ? ' · 共算过 ' + t.run.history.length + ' 次' : '') });
      var concl = node(4, 'concl', { title: t.tp + ' · ' + t.conclusion.level_zh, sub: (t.card_zh || '') + (t.traceable ? ' · 全部输入可追溯' : ' · 缺：' + (t.missing || []).join('、')), cls: 'lv-' + t.conclusion.level });
      edges.push([run, concl, false]);
      inputs.forEach(function (i) {
        var hist = i.role === 'HISTORY';
        if (!i.found) { var miss = node(1, 'o:' + i.observation_id, { title: '找不到这一版', sub: '第 ' + i.revision + ' 版', cls: 'warn' }); edges.push([miss, run, hist]); return; }
        var o = i.origin || {}, ref = o.ref || '', kind = ref.split(':')[0];
        var gk = kind === 'OURA' || kind === 'AH' ? ref.split(':').slice(0, 2).join(':') : kind === 'SYN' ? ref.split(':').slice(0, 3).join(':') : ref.split('#')[0];
        var src = node(0, 's:' + gk, { title: KIND[kind] || cut(o.zh || '来源未记录', 12), sub: o.file_name || o.original || (kind === 'OURA' ? ref.split(':')[1] : kind === 'TABLE' ? '批次 ' + ref.split(':')[1].split('#')[0].slice(0, 8) : cut(gk, 22)), n: 0,
          href: o.original ? '/api/torch/original?key=' + encodeURIComponent(st.key) + '&name=' + encodeURIComponent(o.original) : null, cls: o.found === false ? 'warn' : '' });
        src.n++;
        var obs = node(1, 'o:' + i.observation_id + '@' + i.revision, { title: (i.comparator || '') + LIVE.yn(i.value) + (i.unit ? ' ' + i.unit : '') + ' · ' + i.label,
          sub: '第 ' + i.revision + ' 版' + (hist ? ' · 历史基线' : '') + (i.superseded ? ' · 之后有新版' : ''), obs: i.observation_id + '@' + i.revision, cls: (hist ? 'hist' : '') + (i.superseded ? ' warn' : '') });
        var h = i.handoff, hand = node(2, 'h:' + (h ? h.commit_id : 'none'), h ? { title: '批次 ' + String(h.batch_id).replace(/^TABLE-/, '表格 ').replace(/^OURA-/, 'Oura '), sub: h.export ? '交接文件 ' + h.export.file.replace(/^h1-c0*/, '#').replace(/\.jsonl$/, '') + ' · ' + h.export.sha256.slice(0, 8) : '已提交，未见导出记录' } : { title: '没找到交接记录', sub: '', cls: 'warn' });
        if (!seen['e:' + src.key + obs.key]) { seen['e:' + src.key + obs.key] = 1; edges.push([src, obs, hist]); }
        edges.push([obs, hand, hist]);
        if (!seen['e:' + hand.key]) { seen['e:' + hand.key] = 1; edges.push([hand, run, false]); }
      });
      cols[0].forEach(function (n) { if (n.n > 1) n.sub = (n.sub ? n.sub + ' · ' : '') + n.n + ' 条'; });
      (t.alerts || []).forEach(function (a, k) {
        var dl = (a.deliveries || []).map(function (d) { return d.zh + (d.outcome === 'SENT' ? '已送达' : '未送达'); }).join('、');
        edges.push([concl, node(5, 'a' + k, { title: '提醒 · ' + a.level_zh, sub: dl || '还没有投递', cls: 'lv-' + a.level }), false]);
      });
      (t.used_by || []).forEach(function (u, k) { edges.push([concl, node(5, 'u' + k, { title: (u.grant || '') + ' · ' + cut(u.obj, 8), sub: cut(u.how + ' · ' + u.result, 20) }), false]); });
      if (!cols[5].length) node(5, 'none', { title: '之后还没有出域', sub: '没有被读取或推送过', cls: 'hist' });
      var NW = 160, NH = 46, GX = 28, GY = 12, TOP = 26, rows = Math.max.apply(null, cols.map(function (c) { return c.length; }));
      var H = TOP + rows * (NH + GY), W = cols.length * NW + (cols.length - 1) * GX;
      cols.forEach(function (c, ci) { var off = TOP + (rows - c.length) * (NH + GY) / 2; c.forEach(function (n, ri) { n.x = ci * (NW + GX); n.y = off + ri * (NH + GY); }); });
      var HEAD = ['来源与原件', '星炬正式记录', '交给星轨', '星轨计算', '结论', '之后（星簇）'];
      var svg = '<svg class="egv" width="100%" style="max-width:' + W + 'px;min-width:760px" viewBox="0 0 ' + W + ' ' + H + '" role="img" aria-label="' + esc(t.tp) + ' 这条结论的来龙去脉">' +
        HEAD.map(function (h, i) { return '<text class="h" x="' + (i * (NW + GX)) + '" y="14">' + esc(h) + '</text>'; }).join('') +
        edges.map(function (e) { var a = e[0], b = e[1], x1 = a.x + NW, y1 = a.y + NH / 2, x2 = b.x, y2 = b.y + NH / 2, mx = (x1 + x2) / 2;
          return '<path class="e' + (e[2] ? ' hist' : '') + '" d="M' + x1 + ',' + y1 + ' C' + mx + ',' + y1 + ' ' + mx + ',' + y2 + ' ' + x2 + ',' + y2 + '"/>'; }).join('') +
        cols.map(function (c) { return c.map(function (n) {
          var go = n.obs ? ' data-eg-obs="' + esc(n.obs) + '"' : n.href ? ' data-egv-href="' + esc(n.href) + '"' : '';
          return '<g class="n ' + (n.cls || '') + (go ? ' go' : '') + '"' + go + ' transform="translate(' + n.x + ',' + n.y + ')"><title>' + esc(n.title + (n.sub ? '\n' + n.sub : '')) + '</title><rect width="' + NW + '" height="' + NH + '" rx="8"/>' +
            '<text class="t" x="10" y="19">' + esc(fit(n.title, NW - 6, 12.5)) + '</text><text class="s" x="10" y="36">' + esc(fit(n.sub, NW - 6, 11)) + '</text></g>'; }).join(''); }).join('') + '</svg>';
      var hist = t.inputs.filter(function (i) { return i.role === 'HISTORY'; }).length;
      return '<div class="sub2" data-ptds-inline><!--ptds-ui:s4577d956135c-->连线图：每个方框和每条线都来自已有的记录，点数据方框可以在星炬中打开，点原件方框可以看原图。<!--/ptds-ui-->' + (hist && !st.graphHist ? '另有 ' + hist + ' 条作为历史基线的数据没画出来（在下面展开）。' : '') + '</div><div class="egv-wrap">' + svg + '</div><h4 class="sub2" style="margin-top:var(--primitive-space-3)" data-ptds-ui="s74b96254e95e">逐条明细</h4>';
    },
    traceHtml: function (t) {
      var esc = C.esc, ic = C.ic, c = t.conclusion, r = t.run;
      var drv = (c.drivers || []).map(function (d) { return d.kind === 'DYNAMIC' ? (d.code + ' ' + (d.change || '')) : (d.rule + ' ' + d.result); }).join('；');
      var html = '<div class="eg-chain"><div class="box"><div class="sub2" data-ptds-ui="s1f3fcdb04d4f">结论（星轨）</div><div class="big">' + esc(t.tp) + ' · ' + esc(c.level_zh) + '</div><div class="sub2">' + (drv ? '驱动：' + esc(drv) + ' · ' : '') + '引擎 ' + esc(c.engine_version || '') + '</div><div class="sub2">' + (t.traceable ? ic('check') + ' 全部输入可追溯' : '追不全：缺 ' + esc(t.missing.join('、'))) + '</div></div>' +
        '<span class="eg-arrow">' + ic('chevron-left') + '</span>' +
        '<div class="box"><div class="sub2" data-ptds-ui="s82aa3ce63885">计算（星轨）</div><div class="big">#' + r.run_id + ' · ' + esc(r.trigger_zh) + '</div><div class="sub2">' + esc(C.tzTime(r.started_at, true)) + ' · 用了 ' + t.inputs.length + ' 条数据</div>' +
        (r.history.length > 1 ? '<div class="sub2" data-ptds-inline><!--ptds-ui:sa776581d5b5b-->这个时点一共算过 <!--/ptds-ui-->' + r.history.length + ' 次：' + r.history.map(function (h) { return '#' + h.run_id + ' ' + esc(h.level_zh); }).join(' → ') + '</div>' : '') + '</div></div>';
      var hist = t.inputs.filter(function (i) { return i.role === 'HISTORY'; }), rows = C.st.graphHist ? t.inputs : t.inputs.filter(function (i) { return i.role !== 'HISTORY'; });
      html += '<div class="eg-tbl"><span class="h" data-ptds-ui="s091f2b63b181">用到的数据（星炬正式记录 · 版本）</span><span class="h" data-ptds-ui="sd7475abfcd42">来源与原件</span><span class="h" data-ptds-ui="s3881573eaa13">交给星轨</span>' + rows.map(function (i) {
        if (!i.found) return '<div>' + esc(i.observation_id) + ' 第 ' + i.revision + ' 版</div><div data-ptds-ui="s5b332a3fbd98">星炬里找不到这一版</div><div></div>';
        var o = i.origin || {}, h = i.handoff || {};
        var a = '<div><button class="link" data-eg-obs="' + esc(i.observation_id + '@' + i.revision) + '">' + esc(i.label) + '</button> ' + esc((i.comparator || '') + LIVE.yn(i.value) + (i.unit ? ' ' + i.unit : '')) + '<div class="sub2">第 ' + i.revision + ' 版' + (i.role === 'HISTORY' ? ' · 作为历史基线' : '') + ' · ' + esc(i.source_zh || '') + ' · 信度 ' + esc(i.trust_tier || '—') + '</div>' +
          (i.superseded ? '<div class="sub2">' + ic('circle-alert') + ' 之后有第 ' + i.latest.revision + ' 版（' + (i.latest.status === 'ACTIVE' ? esc(i.latest.value) : '已撤回') + '），这次计算用的是旧版</div>' : '') + '</div>';
        var b = '<div>' + esc(o.zh || '') + (o.line ? '<div class="sub2" data-ptds-inline><!--ptds-ui:s457f372b01cb-->原文：<!--/ptds-ui-->' + esc(o.line) + '</div>' : '') + (o.original ? '<div><a class="link" target="_blank" rel="noopener" href="/api/torch/original?key=' + encodeURIComponent(C.st.key) + '&name=' + encodeURIComponent(o.original) + '">' + ic('file-image') + ' 查看原图</a>' + (o.engine ? ' <span class="sub2">· ' + esc(o.engine) + '</span>' : '') + '</div>' : o.kind === 'OCR' ? '<div class="sub2" data-ptds-ui="s79dc149fa7f4">原件不在这台电脑上</div>' : '') + '<div class="sub2">' + esc(o.ref || '') + '</div></div>';
        var cc = '<div class="sub2">' + (h.batch_id ? '批次 ' + esc(h.batch_id) + (h.export ? '<br>交接文件 ' + esc(h.export.file) + ' · ' + esc(h.export.sha256.slice(0, 12)) : '') : '—') + '</div>';
        return a + b + cc; }).join('') + '</div>' + (hist.length ? '<div><button class="chip" id="eg-hist">' + (C.st.graphHist ? '收起作为历史基线的 ' + hist.length + ' 条' : '另有 ' + hist.length + ' 条作为历史基线（用于看变化），展开') + '</button></div>' : '');
      var after = t.alerts.map(function (a) { return '<div class="lrow"><span data-ptds-inline><!--ptds-ui:sce0cb066b70e-->提醒 · <!--/ptds-ui-->' + esc(a.level_zh) + '</span><span class="sub2">' + esc(a.title) + '</span><span class="sub2">' + a.deliveries.map(function (d) { return esc(d.zh) + (d.outcome === 'SENT' ? '已送达' : '未送达'); }).join('、') + '</span><span class="sub2">' + esc(C.tzTime(a.created_at, true)) + '</span></div>'; }).join('') +
        t.used_by.map(function (u) { return '<div class="lrow" data-sem="SEM-30"><span>' + esc(u.grant || '') + ' · ' + esc(u.obj) + '</span><span class="sub2">' + esc(u.how) + ' · ' + esc(u.level) + '</span><span class="sub2">' + esc(u.result) + '</span><span class="sub2">' + esc(u.when) + '</span></div>'; }).join('');
      html += '<div><div class="sub2" data-ptds-ui="s44156ba8145f">之后（星簇记录的出域与提醒推送）</div>' + (after || '<div class="sub2" data-ptds-ui="sc1a76b7e8061">这条结论算出之后，还没有被读取或推送过。</div>') + '</div>';
      return html;
    },
    /* 星轨 · 高阶计算：竞争性解释（真实，早期测试）——同一组数据按不同规则 / 假设各算一遍，只说各自成立与否 */
    renderAdvanced: function () {
      if (C.st.app === 'track' && C.st.view === 'wall' && C.st.stateSection === 'offset') return LIVE.renderWall();
      if (C.st.labTab === 'compete') return LIVE.renderDeviceTables();
      var esc = C.esc, ic = C.ic, st = C.st, PROD = C.DATA.product || {}, adv = PROD.advanced || [], d = {};

      var mt = function (m) { return { plan: '规划中', dev: '开发中' }[m] ? '<span class="tag">' + { plan: '规划中', dev: '开发中' }[m] + '</span>' : ''; };  /* r63（产品负责人 2026-10-15）：状态实验室不再挂“早期测试” */
      var OC = { '满足': 'ok', '成立': 'ok', '可用': 'use', '超过变化阈值': 'ok', '超过阈值': 'ok', '触发': 'ok' };
      var line = function (l, deep) { return '<div class="cp-l' + (deep ? ' deep' : '') + '"><span>' + esc(l.need) + '</span><span class="sub2">' + esc(l.got || '') + '</span><span class="cp-o ' + (OC[l.outcome] || (l.outcome.indexOf('缺') === 0 || l.outcome === '算不了' ? 'na' : 'no')) + '">' + esc(l.outcome) + '</span></div>' + (l.items || []).map(function (x) { return line(x, true); }).join(''); };
      var col = function (c) { return '<div class="box cp-col' + (st.cpCol === c.id ? ' hl' : '') + '" data-cp-colbox="' + esc(c.id) + '"><h3>' + esc(c.name) + '</h3><div class="big">' + esc(c.result_zh) + '</div><div class="sub2">' + esc(c.expert_review || '') + '</div>' +
        c.groups.map(function (g) { return '<div class="cp-g"><div class="sub2">' + esc(g.zh) + (g.outcome ? ' · ' + esc(g.outcome) : '') + '</div>' + g.lines.map(function (l) { return line(l, false); }).join('') + '</div>'; }).join('') +
        (c.missing.length ? '<div class="sub2" data-ptds-inline><!--ptds-ui:sd711e416d87f-->缺的数据：<!--/ptds-ui-->' + c.missing.map(esc).join('、') + '</div>' : '') + '</div>'; };
      var real = C.S().instance.kind === 'REAL';
      if (st.labFocus) st.labTab = 'compete';
      var defs = [
        ['compete', '多模型比对', '按指标比较不同设备的记录，保留来源与统计口径'],
        ['retro', '回溯式重计算', '功能开发中，暂未开放'],
        ['cf', '反事实推断', '功能开发中，暂未开放']
      ];
      var tab = null; // All laboratory modules are currently in development.
      st.labTab = tab;
      if (!document.getElementById('lab-sections-css')) {
        var labCss = document.createElement('style'); labCss.id = 'lab-sections-css';
        labCss.textContent = LIVE.GRAPH_CSS + '#lab-sections .lab-arrow{justify-self:end;display:inline-flex;transition:opacity var(--ptds-fade-duration,180ms) ease-in-out}#lab-sections .xh-t:disabled{cursor:not-allowed;opacity:1;border-color:var(--theme-line-hairline);background:transparent}#lab-sections .xh-t:disabled b{color:var(--theme-text-secondary)}#lab-sections .lab-dev{font-size:var(--scale-type-meta);font-weight:400;color:var(--theme-text-secondary)}#lab-sections .xh-t:focus-visible{outline:2px solid var(--theme-text-primary);outline-offset:3px}@media(max-width:700px){#lab-sections .xh-tabs{grid-template-columns:1fr}}@media(prefers-reduced-motion:reduce){#lab-sections .lab-arrow{transition:none}}';
        document.head.appendChild(labCss);
      }
      var html = '<section class="box" id="lab-sections"><div class="xh-tabs" role="group" aria-label="状态实验室分类" data-ptds-ui-aria-label="sb5cd6b70aa92">' + defs.map(function (def) {
        var disabled = def[0] !== 'compete';
        return '<button type="button" class="xh-t" id="lab-tab-' + def[0] + '" data-lab-tab="' + def[0] + '"' + (disabled ? ' disabled aria-disabled="true"' : ' aria-expanded="' + (tab === def[0]) + '" aria-controls="lab-section-panel"') + '><b>' + def[1] + '</b><span class="n">' + (disabled ? '<span class="tag lab-dev" data-ptds-ui="s78c33fbf0e2a">开发中</span>' : '') + '</span>' + (disabled ? '<span></span>' : '<span class="lab-arrow" style="transform:rotate(' + (tab === def[0] ? 180 : 0) + 'deg)">' + ic('chevron-down') + '</span>') + '<span class="sub2">' + esc(def[2]) + '</span></button>';
      }).join('') + '</div><div id="lab-section-panel" class="xh-body" role="region"' + (tab ? ' aria-labelledby="lab-tab-' + tab + '"' : ' hidden') + '>';
      adv.forEach(function (a) {
        if (a.id !== tab) return;
        if (a.id === 'compete') {
          html += '<section class="box" id="lab-compete" data-cmp="S20" data-sem="SEM-36"><h3>' + ic('flask-conical') + esc(defs[0][1]) + '<span class="grow"></span>' + mt(a.maturity) + '</h3><div>' + esc(a.what) + '</div>';
          if (!d.found && real) { html += (C.S().bioage ? '' : '<div class="sub2" data-ptds-ui="s9887c500a83f">这份数据还没有可以并排比较的规则。</div>') + LIVE.bioLabHtml() + '</section>'; return; }
          if (!d.found) { html += '<div class="sub2">' + (d.why === 'NO_SJIA_CARD' ? '这份数据没有绑定 sJIA 关注卡，没有可以并排比较的规则。' : '这份数据里还没有可以比较的时点。') + '</div></section>'; return; }
          html += '<div class="chips" role="group" aria-label="选择时点" data-ptds-ui-aria-label="s2aee49509aa6">' + d.tps.map(function (t) { return '<button class="chip" data-cmp-tp="' + esc(t) + '" aria-pressed="' + (t === d.tp) + '">' + esc(t) + '</button>'; }).join('') + '</div>' +
            '<div class="sub2">' + esc(d.tp) + ' · 用了 ' + d.data.length + ' 项数据（' + d.data.map(esc).join('、') + '）' + (d.status !== 'FRESH' ? ' · 数据在正式计算之后有更新，这里按现在的数据算' : '') + (d.formal ? ' · 星轨正式结果：计算 #' + d.formal.run_id + ' ' + esc(d.formal.level_zh) : '') + '</div>' +
            LIVE.cpExplainHtml(d) +
            '<div class="cp-tiles">' + d.columns.map(function (c) { return '<button class="cp-tile' + (st.cpOpen === c.id ? ' on' : '') + '" data-cp-open="' + esc(c.id) + '" aria-expanded="' + (st.cpOpen === c.id) + '"><span class="sub2">' + esc(c.name.replace(/（.*?）/g, '')) + '<span class="grow"></span>' + ic(st.cpOpen === c.id ? 'chevron-down' : 'chevron-right') + '</span><span class="v ' + (c.result === 'MET' || c.result === 'ALERT' || c.result === 'WATCH' ? 'ok' : c.result === 'INDETERMINATE' || c.result === 'NOT_EVALUABLE' ? 'na' : '') + '">' + esc(c.result_zh) + (c.score != null ? ' · ' + esc(c.score) : '') + '</span></button>'; }).join('') +
              '<button class="cp-tile cp-all' + (st.cpOpen === 'ALL' ? ' on' : '') + '" data-cp-open="ALL" aria-expanded="' + (st.cpOpen === 'ALL') + '"><span class="sub2">' + ic('scale') + ' 共同对比<span class="grow"></span>' + ic(st.cpOpen === 'ALL' ? 'chevron-down' : 'chevron-right') + '</span><span class="v">' + d.columns.length + ' 套并排</span></button></div>' +
            (st.cpOpen === 'ALL' ? '<div class="cp-cols cp-allv">' + d.columns.map(col).join('') + '</div>' : '') +
            (function () { var c = d.columns.filter(function (x) { return x.id === st.cpOpen; })[0]; if (!c) return '';
              return '<div class="cp-open"><div class="cp-oh"><b>' + esc(c.name) + '</b> · ' + esc(c.result_zh) + '<span class="sub2"> · ' + esc(c.expert_review || '') + '</span></div>' +
                c.groups.map(function (g) { return '<div class="cp-og"><div class="sub2">' + esc(g.zh) + (g.outcome ? ' · ' + esc(g.outcome) : '') + '</div>' + g.lines.map(function (l) { return line(l, false); }).join('') + '</div>'; }).join('') +
                (c.missing.length ? '<div class="sub2" data-ptds-inline><!--ptds-ui:sd711e416d87f-->缺的数据：<!--/ptds-ui-->' + c.missing.map(esc).join('、') + '</div>' : '') + '</div>'; })() +
            '<div class="sub2">' + esc(d.note) + '</div>' + (real ? LIVE.bioLabHtml() : '') + '</section>';
        } else if (a.id === 'retro') {
          html += '<section class="box" data-cmp="S20" data-sem="SEM-36"><h3>' + ic('history') + esc(a.zh) + '<span class="grow"></span>' + mt(a.maturity) + '</h3><div>' + esc(a.what) + '</div>' + LIVE.retroHtml() + '</section>';
        } else {
          html += '<section class="box" data-cmp="S20" data-sem="SEM-36"><h3>' + ic(a.maturity === 'plan' ? 'map' : 'flask-conical') + esc(a.zh) + '<span class="grow"></span>' + mt(a.maturity) + '</h3><div>' + esc(a.what) + '</div>' +
            (a.maturity === 'plan' ? '<div class="sub2" data-ptds-ui="s0d9e3a7dca50">规划中：只有这一句说明。</div>' : '<div class="sub2" data-ptds-inline><!--ptds-ui:s97c27cdca015-->需要：<!--/ptds-ui-->' + esc(a.needs) + '</div><div class="sub2" data-ptds-ui="s63e75947d726">还没接上，不显示任何结果。</div>') + '</section>';
        }
      });
      html += '</div></section>';
      if (!document.getElementById('cp-css')) { var stl = document.createElement('style'); stl.id = 'cp-css'; stl.textContent = LIVE.CP_CSS; document.head.appendChild(stl); }
      if (tab === 'baseline') html += LIVE.baselineHtml();
      document.getElementById('view').innerHTML = html;
      if (tab === 'baseline') LIVE.bindBaseline();
      document.querySelectorAll('#lab-sections [data-lab-tab]:not(:disabled)').forEach(function (b) { b.onclick = function () {
        var next = b.dataset.labTab, closing = st.labTab === next;
        var panel = document.getElementById('lab-section-panel'), reduce = document.documentElement.dataset.motion === 'reduced' || window.matchMedia('(prefers-reduced-motion: reduce)').matches;
        var finish = function () {
          if (!closing) st.cpOpen = null;
          st.labTab = closing ? null : next; LIVE.renderAdvanced();
          if (!closing && !reduce) {
            var body = document.getElementById('lab-section-panel'), arrow = document.querySelector('#lab-tab-' + next + ' .lab-arrow');
            if (body && body.animate) body.animate([{opacity:0},{opacity:1}],{duration:180,easing:'ease-in-out'});
          }
        };
        if (closing && !reduce && panel.animate) {
          panel.animate([{opacity:1},{opacity:0}],{duration:180,easing:'ease-in-out'}).finished.then(finish);
        } else finish();
      }; });
      document.querySelectorAll('[data-cmp-tp]').forEach(function (b) { b.onclick = function () { st.cmpTp = b.dataset.cmpTp; st.cpCol = null; LIVE.renderAdvanced(); }; });
      document.querySelectorAll('[data-cp-open]').forEach(function (b) { b.onclick = function () { st.cpOpen = st.cpOpen === b.dataset.cpOpen ? null : b.dataset.cpOpen; var y = window.scrollY; LIVE.renderAdvanced(); window.scrollTo(0, y); }; });
      LIVE.cpBind();
      LIVE._cpD = d;
      if (tab === 'compete' && d.found && document.getElementById('cp-ex')) LIVE.cpAiPoll(d);
      LIVE.bindRetro(); LIVE.bindBioLab();
    },
    /* 回溯式重计算（产品负责人 2026-10-14 批准 R13）：版式和竞争性解释一致——解释框（星灵逐句核对）→ 小结 → 下一步 → 4 格 + 分叉图格 → 逐次明细（折叠）。
       分叉都是内存里的试算，不写库；只有“确认重算”才追加正式计算。 */
    retroHtml: function () {
      var esc = C.esc, ic = C.ic, st = C.st, d;
      try { d = readCached('/api/track/retro_branches?key=' + encodeURIComponent(st.key)); } catch (err) { if(err&&(err.viewPending||err.code==='VIEW_CHANGED'))throw err; d = { found: false }; }
      LIVE._rtD = d;
      if (!d.found) return LIVE.retroRunsHtml();
      var open = st.cpOpen == null ? 'GRAPH' : st.cpOpen, cls = function (v) { return v.state === 'SAME' ? '' : v.state === 'NA' ? 'na' : 'ok'; };
      var tile = function (c) { return '<button class="cp-tile' + (open === c.id ? ' on' : '') + '" data-rt-open="' + esc(c.id) + '" aria-expanded="' + (open === c.id) + '"><span class="sub2">' + esc(c.name) + '<span class="grow"></span>' + ic(open === c.id ? 'chevron-down' : 'chevron-right') + '</span><span class="v ' + cls(c.verdict) + '">' + esc(c.verdict.zh) + '</span></button>'; };
      var col = d.columns.filter(function (c) { return c.id === open; })[0];
      var body = '';
      if (open === 'GRAPH') body = '<div class="cp-open rt-g">' + LIVE.rtGraphSvg(d) + '<div class="sub2 rt-lg"><span><span class="rt-dot a"></span>关注</span><span><span class="rt-dot"></span>无</span><span><span class="rt-dot n"></span>算不了</span>' +
        (d.graph.same.length ? '<span data-ptds-inline><!--ptds-ui:s55459fcd6ebd-->和现在一样、已收起：<!--/ptds-ui-->' + esc(d.graph.same.join('、')) + '</span>' : '') + (d.graph.more ? '<span data-ptds-inline><!--ptds-ui:s268ec6902063-->另有 <!--/ptds-ui-->' + d.graph.more + ' 条分叉没画</span>' : '') + '<span data-ptds-ui="s8b6da673ff29">点实线圆点看来龙去脉，点虚线圆点看那天的竞争性解释</span></div></div>';
      else if (col) body = '<div class="cp-open"><div class="cp-oh"><b data-ptds-inline><!--ptds-ui:s7b467eee3bb3-->只按 <!--/ptds-ui-->' + esc(col.name) + '</b> · ' + esc(col.verdict.zh) + '</div>' +
        '<div class="cp-l"><span class="sub2" data-ptds-ui="s9b6e85289091">时点</span><span class="sub2" data-ptds-ui="s84971b8795f2">现在的方法 → 只按这一套</span><span class="sub2" data-ptds-ui="sfb8791a7645e">比较</span></div>' +
        col.series.map(function (p, i) { var f = d.formal[i]; return '<div class="cp-l"><span>' + esc(p.tp) + '</span><span>' + esc(f.level_zh) + ' → ' + esc(p.level_zh) + '</span><span class="cp-o ' + (f.level === p.level ? 'same' : 'ok') + '">' + (f.level === p.level ? '一样' : '不一样') + '</span></div>'; }).join('') + '</div>';
      return '<div class="sub2" data-ptds-inline><!--ptds-ui:s38298c213802-->现在的方法：<!--/ptds-ui-->' + esc(d.method) + ' · ' + d.tps.length + ' 个时点 · 实线是星轨正式结果，其余是试算，不写库</div>' +
        LIVE.cpExplainHtml(d) +
        '<div class="cp-tiles">' + d.columns.map(tile).join('') + '<button class="cp-tile cp-all' + (open === 'GRAPH' ? ' on' : '') + '" data-rt-open="GRAPH" aria-expanded="' + (open === 'GRAPH') + '"><span class="sub2">' + ic('git-compare') + ' 分叉图<span class="grow"></span>' + ic(open === 'GRAPH' ? 'chevron-down' : 'chevron-right') + '</span><span class="v">' + d.tps.length + ' 个时点并排</span></button></div>' + body +
        '<details class="more rt-runs"' + (st.rtAsk ? ' open' : '') + '><summary class="sub2" data-ptds-ui="s52b282887242">逐次计算明细，也可以在这里按现在的方法重算全部时点</summary>' + LIVE.retroRunsHtml() + '</details>' +
        '<div class="sub2">' + esc(d.note) + '</div>';
    },
    /* 分叉图：横轴是时点；实线是现在的方法；分叉在和正式线结论相同的时点贴回正式线（汇合），不同的地方分开并标出差几天 */
    rtGraphSvg: function (d) {
      var esc = C.esc, g = d.graph, n = d.tps.length, W = 1040, L = 150, R = n > 1 ? 840 : 495, A = '#E8B65A', T = 'var(--theme-text-primary)', G = 'var(--theme-text-tertiary)';
      var xs = d.tps.map(function (t, i) { return n > 1 ? L + (R - L) * i / (n - 1) : R; }), y0 = 70, H = 120 + g.lanes.length * 80;
      var flag = function (lv) { return lv === 'ALERT' || lv === 'WATCH'; }, na = function (lv) { return lv === 'UNDETERMINED' || lv === 'NOT_EVALUABLE'; };
      var zh = function (p) { return na(p.level) ? '算不了' : p.level_zh; };
      var node = function (x, y, p, attr) { return '<g class="rt-n" ' + attr + '>' + (flag(p.level) ? '<circle cx="' + x + '" cy="' + y + '" r="9" fill="' + A + '"/>' : '<circle cx="' + x + '" cy="' + y + '" r="8" fill="var(--theme-surface-raised,#0d1428)" stroke="' + G + '" stroke-width="2"' + (na(p.level) ? ' stroke-dasharray="3 3"' : '') + '/>') +
        '<text x="' + x + '" y="' + (y - 16) + '" text-anchor="middle" font-size="13" fill="' + (flag(p.level) ? A : G) + '">' + esc(zh(p)) + '</text></g>'; };
      var curve = function (pts) { var s = 'M' + pts[0][0] + ' ' + pts[0][1]; for (var i = 1; i < pts.length; i++) { var a = pts[i - 1], b = pts[i], m = (a[0] + b[0]) / 2; s += ' C' + m + ' ' + a[1] + ' ' + m + ' ' + b[1] + ' ' + b[0] + ' ' + b[1]; } return s; };
      var step = n > 8 ? Math.ceil(n / 8) : 1, svg = '<svg class="rt-svg" width="100%" viewBox="0 0 ' + W + ' ' + H + '" role="img" aria-label="分叉图">';
      xs.forEach(function (x, i) { svg += '<line x1="' + x + '" y1="34" x2="' + x + '" y2="' + (H - 34) + '" stroke="' + G + '" stroke-opacity=".25"/>' + (i % step === 0 || i === n - 1 ? '<text x="' + x + '" y="' + (H - 12) + '" text-anchor="middle" font-size="13" fill="' + G + '">' + esc(d.tps[i]) + '</text>' : ''); });
      var nodes = '';
      g.lanes.forEach(function (ln, k) {
        var yl = 150 + k * 80, allNa = ln.verdict.state === 'NA';
        var pts = ln.series.map(function (p, i) { return [xs[i], !allNa && p.level === g.main[i].level ? y0 : yl]; });
        svg += n > 1 ? '<path d="' + curve(pts) + '" fill="none" stroke="' + (allNa ? G : A) + '" stroke-width="' + (allNa ? 2 : 2.5) + '" stroke-dasharray="' + (allNa ? '2 6' : '8 6') + '"/>' : '';
        ln.series.forEach(function (p, i) { if (pts[i][1] !== y0) nodes += node(xs[i], yl, p, 'data-rt-alt="' + esc(p.tp) + '"'); });
        var off = pts.map(function (q, i) { return q[1] !== y0 ? i : -1; }).filter(function (i) { return i >= 0; });
        if (!allNa && off.length && off[off.length - 1] < n - 1) {
          var mx = (xs[off[0]] + xs[off[off.length - 1]]) / 2;
          svg += '<text x="' + mx + '" y="' + (yl + 32) + '" text-anchor="middle" font-size="13" fill="' + A + '">分叉 · ' + esc(ln.zh) + '</text>' +
            '<text x="' + (xs[off[off.length - 1] + 1] - 8) + '" y="' + (y0 + 30) + '" text-anchor="end" font-size="12" fill="' + A + '">在这里汇合</text>';
        } else svg += '<text x="' + (xs[n - 1] + 30) + '" y="' + (yl + 5) + '" font-size="13" fill="' + (allNa ? G : A) + '">分叉 · ' + esc(ln.zh) + '</text>' + (allNa ? '<text x="' + (xs[n - 1] + 30) + '" y="' + (yl + 24) + '" font-size="12" fill="' + G + '">一直缺数据</text>' : '');
        var v = ln.verdict;
        if (k === 0 && v.days && (v.state === 'LATE' || v.state === 'EARLY')) {
          var at = v.state === 'LATE' ? d.first : v.first, i0 = d.tps.indexOf(at);
          if (i0 >= 0) { var bx = xs[i0] + 22; svg += '<path d="M' + bx + ' ' + (y0 + 4) + ' L' + (bx + 8) + ' ' + (y0 + 4) + ' L' + (bx + 8) + ' ' + (yl - 4) + ' L' + bx + ' ' + (yl - 4) + '" fill="none" stroke="' + A + '" stroke-width="1.5"/><text x="' + (bx + 18) + '" y="' + ((y0 + yl) / 2 + 5) + '" font-size="13" fill="' + A + '">' + (v.state === 'LATE' ? '早 ' : '这条早 ') + v.days + ' 天</text>'; }
        }
      });
      svg += n > 1 ? '<path d="M' + xs[0] + ' ' + y0 + ' L' + xs[n - 1] + ' ' + y0 + '" stroke="' + T + '" stroke-width="3"/>' : '';
      g.main.forEach(function (p, i) { nodes += node(xs[i], y0, p, 'data-rt-tp="' + esc(p.tp) + '"'); });
      svg += nodes + '<text x="' + (xs[n - 1] + 30) + '" y="' + (y0 + 5) + '" font-size="13" fill="' + T + '">现在的方法</text><text x="' + (xs[n - 1] + 30) + '" y="' + (y0 + 24) + '" font-size="12" fill="' + G + '">星轨正式结果</text>';
      return svg + '</svg>';
    },
    retroRunsHtml: function () {
      var esc = C.esc, ic = C.ic, st = C.st, h = {};
      try { h = readCached('/api/track/retro?key=' + encodeURIComponent(st.key)); } catch (err) { if(err&&(err.viewPending||err.code==='VIEW_CHANGED'))throw err; h = { tps: [] }; }
      if (!h.tps || !h.tps.length) return '<div class="sub2">' + (h.why === 'NO_SJIA_CARD' ? '这份数据没有绑定 sJIA 关注卡，没有可以重算的时点。' : '这份数据里还没有算过的时点。') + '</div>';
      var ask = st.rtAsk, run = function (r) { return r ? '#' + r.run_id + ' · ' + esc(r.level_zh) + '<div class="sub2">' + esc(r.trigger_zh) + ' · ' + esc(r.method) + '</div>' : '—'; };
      var other = h.sensitivities.filter(function (x) { return x.id !== h.sensitivity; });
      var conf = ask ? '<div class="confirm"><div>' + (ask === 'RUN' ? '按现在的方法，把 ' + h.tps.length + ' 个时点全部重算一遍。会新增一次计算，旧结果保留；同样的数据和方法，结果应该逐字一致。'
          : '把 sJIA 关注卡的变化灵敏度改成"' + esc(h.sensitivities.filter(function (x) { return x.id === ask; })[0].zh) + '"，再把全部时点重算一遍。这是卡的正式设置，之后的计算都按它；旧结果保留，随时可以改回来。') +
        '</div><div class="acts"><button class="btn" id="rt-ok">' + ic('check') + '确认重算</button><button class="ibtn" id="rt-no" aria-label="取消" title="取消" data-ptds-ui-aria-label="s2cd0f3be8738" data-ptds-ui-title="s2cd0f3be8738">' + ic('x') + '</button></div></div>' : '';
      return '<div class="sub2" data-ptds-inline><!--ptds-ui:s38298c213802-->现在的方法：<!--/ptds-ui-->' + esc(h.method.zh) + '</div>' +
        '<div class="opts"><button class="chip" id="rt-run">' + ic('refresh-cw') + '按现在的方法重算全部过去时点</button>' + other.map(function (x) { return '<button class="chip" data-rt-sens="' + x.id + '">换成灵敏度' + esc(x.zh) + '再算</button>'; }).join('') + '</div>' + conf +
        '<div class="cp-l"><span class="sub2" data-ptds-ui="s4a251052b90b">时点 · 之前</span><span class="sub2" data-ptds-ui="s43584f37c1f4">现在</span><span class="sub2" data-ptds-ui="sfb8791a7645e">比较</span></div>' +
        h.tps.map(function (t) { return '<div class="cp-l"><span>' + esc(t.tp) + ' · ' + run(t.prev) + '</span><span>' + run(t.latest) + '</span><span class="cp-o ' + (t.compare === '逐字一致' ? 'ok' : t.compare ? 'na' : 'no') + '">' + esc(t.compare || '只算过一次') + '</span></div>'; }).join('') +
        '<div class="sub2">' + esc(h.note) + '</div>';
    },
    bindRetro: function () {
      var st = C.st, g = function (k, fn) { var el = document.getElementById(k); if (el) el.onclick = LIVE.action(fn); };
      document.querySelectorAll('[data-rt-open]').forEach(function (b) { b.onclick = function () { var open = st.cpOpen == null ? 'GRAPH' : st.cpOpen; st.cpOpen = open === b.dataset.rtOpen ? 'NONE' : b.dataset.rtOpen; var y = window.scrollY; LIVE.renderAdvanced(); window.scrollTo(0, y); }; });
      document.querySelectorAll('[data-rt-tp]').forEach(function (b) { b.onclick = function () { LIVE.openTrace('sjia-mas', b.dataset.rtTp); }; });
      document.querySelectorAll('[data-rt-alt]').forEach(function (b) { b.onclick = function () { st.labTab = 'compete'; st.cmpTp = b.dataset.rtAlt; st.cpOpen = null; LIVE.renderAdvanced(); window.scrollTo(0, 0); }; });
      if (LIVE._rtD && LIVE._rtD.found && document.getElementById('cp-ex') && document.querySelector('[data-rt-open]')) LIVE.cpAiPoll(LIVE._rtD);
      g('rt-run', function () { st.rtAsk = 'RUN'; LIVE.renderAdvanced(); });
      document.querySelectorAll('[data-rt-sens]').forEach(function (b) { b.onclick = function () { st.rtAsk = b.dataset.rtSens; LIVE.renderAdvanced(); }; });
      g('rt-no', function () { st.rtAsk = null; LIVE.renderAdvanced(); });
      g('rt-ok', LIVE.action(async function () {
        var ask = st.rtAsk; st.rtAsk = null;
        try {
          var r = (await call('POST', '/api/track/retro', ask === 'RUN' ? { key: st.key } : { key: st.key, sensitivity: ask }));
          C.SNAPS[st.key] = r.snapshot;
          var n = (r.result.evaluated || r.result.new || []).length;
          C.toast(r.result.run_id ? '已重算 ' + n + ' 个时点（计算 #' + r.result.run_id + '），旧结果保留' : '没有可重算的时点');
        } catch (err) { if(err&&(err.viewPending||err.code==='VIEW_CHANGED'))throw err; C.toast('没能重算（' + (err.detail || err.code) + '）'); }
        LIVE.renderAdvanced();
      }));
    },
    /* 星灵（产品负责人 2026-10-14）：本机 Qwen 写的一律署名“星灵（Qwen 3.5 9B本地）发出”；只在我点了按钮后才写；不兜底、不替换，没写成就照实说。
       按钮的图标悬停时会动（sp-ic），以后全站图标动画沿用这个类。 */
    spBtn: function (attr, label) { var name = C.esc(label || '星灵解读'); return '<button type="button" class="sp-btn sp-icon-only" ' + attr + ' aria-label="' + name + '" title="' + name + '"><span class="sp-ic" aria-hidden="true">' + C.ic('sparkles') + '</span></button>'; },
    spStateHtml: function (res, what) {
      var esc = C.esc, sign = res.by || res.sign || '星灵', who = sign.replace(/发出$/, '');
      var bad = function (list) { return '<details class="cp-rej"><summary data-ptds-inline><!--ptds-ui:s29bc78f35a93-->看没通过核对的句子（<!--/ptds-ui-->' + list.length + '）</summary>' + list.map(function (x) { return '<div class="cp-l"><span>' + esc(x.text) + '</span><span class="sub2">' + esc((x.bad || []).join('；')) + '</span></div>'; }).join('') + '</details>'; };
      if (res.state === 'running') return { right: '<span class="cp-spin"></span>' + esc(who) + '正在写，约 1 分钟，写好后逐句核对', body: '' };
      if (res.state === 'ok') return { right: esc(sign) + ' · 逐句核对 ' + res.checked + '/' + res.checked + ' 通过', body: (res.rejected && res.rejected.length ? '<div class="sub2" data-ptds-ui="s06998ede1d95">第一次写的有句子没通过核对，已让它重写。</div>' + bad(res.rejected) : '') };
      if (res.state === 'rejected') return { right: '', body: '<div class="sub2">' + esc(who) + '这次写的' + (what || '') + '有句子没通过核对（写了 ' + res.attempts + ' 次），没有采用。</div>' + bad(res.rejected || []) };
      if (res.state === 'off') return { right: '', body: '<div class="sub2">' + esc(res.why || '本机未启用星灵') + '</div>' };  /* 分发测试版：没装千问 */
      if (res.state === 'no_llm') return { right: '', body: '<div class="sub2" data-ptds-ui="s8ba39db18dfc">本机模型没有在运行，星灵这次写不了。启动本机模型后再点一次。</div>' };
      if (res.state === 'blocked') return { right: '', body: '<div class="sub2">' + esc(res.why || '这次不交给星灵') + '</div>' };
      if (res.state === 'error') return { right: '', body: '<div class="sub2" data-ptds-inline><!--ptds-ui:sa7035157e6d9-->星灵这次没写成（<!--/ptds-ui-->' + esc(res.why || '出错') + '）。可以再点一次。</div>' };
      return { right: '', body: '' };
    },
    /* 三页（证据图谱、我的数据、我的数源）和来龙去脉浮窗的星灵框：只用记录，不含健康数值 */
    SP_PAGES: { graph: '证据图谱', data: '我的数据', sources: '我的数源' },
    spBoxHtml: function (sp) {
      var esc = C.esc, ic = C.ic, res = sp.res || { state: 'running' }, x = LIVE.spStateHtml(res);
      var facts = res.facts && res.facts.length ? '<details class="more"><summary data-ptds-inline><!--ptds-ui:s21cfce586a14-->星灵看到的记录（<!--/ptds-ui-->' + res.facts.length + ' 条，不含健康数值）</summary><div class="sub2 sp-facts">' + res.facts.map(esc).join('<br>') + '</div></details>' : '';
      return '<div class="cp-ex sp-box" id="' + sp.id + '"><div class="sub2"><span class="sp-ic on" role="img" aria-label="' + esc('星灵解读' + (sp.title ? ' · ' + sp.title : '')) + '" title="' + esc('星灵解读' + (sp.title ? ' · ' + sp.title : '')) + '">' + ic('sparkles') + '</span><span class="grow" style="flex:1"></span><span class="cp-right">' + x.right + '</span><button class="ibtn sp-x" data-sp-close="' + sp.id + '" aria-label="收起" title="收起">' + ic('x') + '</button></div>' +
        (res.state === 'ok' ? res.sentences.map(function (z) { return '<p>' + esc(z.text) + '</p>'; }).join('') : '') + x.body + facts + '</div>';
    },
    spAsk: function (sp, start) {
      var st = C.st, k = sp.k;
      clearTimeout(sp.timer);
      fetch(sp.url + (start ? '&start=1' : '&start=0')).then(function (r) { return r.json(); }).then(function (res) {
        if (!st.spMap || st.spMap[k] !== sp) return;
        if (!start && res.state === 'idle') res = sp.res || res;  // 轮询时后台已结束、结果在缓存里会直接回来
        sp.res = res; LIVE.spPaint(sp);
        if (res.state === 'running') sp.timer = setTimeout(function () { LIVE.spAsk(sp, false); }, 4000);
      }).catch(function () { sp.res = { state: 'error', why: '连不上本机服务' }; LIVE.spPaint(sp); });
    },
    spPaint: function (sp) {
      var el = document.getElementById(sp.id); if (!el) return;
      var tmp = document.createElement('div'); tmp.innerHTML = LIVE.spBoxHtml(sp); el.replaceWith(tmp.firstChild); LIVE.spBind();
    },
    spBind: function () {
      var st = C.st;
      document.querySelectorAll('[data-sp-close]').forEach(function (b) { b.onclick = function () { var id = b.dataset.spClose; Object.keys(st.spMap || {}).forEach(function (k) { if (st.spMap[k].id === id) { clearTimeout(st.spMap[k].timer); delete st.spMap[k]; } }); var el = document.getElementById(id); if (el) el.remove(); LIVE.spMount(); if (st.fw) LIVE.renderFw(); }; });
      document.querySelectorAll('[data-sp-page]').forEach(function (b) { b.onclick = function () { LIVE.spOpen(b.dataset.spPage); }; });
      document.querySelectorAll('[data-sp-trace]').forEach(function (b) { b.onclick = function () { var f = st.fw; if (f) LIVE.spOpen('trace', f.card, f.tp); }; });
    },
    spOpen: function (page, card, tp) {
      var st = C.st; st.spMap = st.spMap || {};
      var k = st.key + '|' + page + (page === 'trace' ? '|' + card + '|' + tp : '');
      var sp = { k: k, page: page, id: 'sp-' + page, title: page === 'trace' ? '' : LIVE.SP_PAGES[page], res: { state: 'running', by: '' },
        url: '/api/starling/page?key=' + encodeURIComponent(st.key) + '&page=' + page + (page === 'trace' ? '&card=' + encodeURIComponent(card) + '&tp=' + encodeURIComponent(tp) : '') };
      st.spMap[k] = sp;
      if (page === 'trace') LIVE.renderFw(); else LIVE.spMount();
      LIVE.spAsk(sp, true);
    },
    /* 每次画完星炬页面后调用：当前页如果点过星灵，就把星灵框放回页面最上面 */
    spMount: function () {
      var st = C.st, page = st.app === 'torch' && LIVE.SP_PAGES[st.tview] ? st.tview : null, view = document.getElementById('view');
      var old = document.querySelector('#view > .sp-box'); if (old) old.remove();
      if (!page || !view || C.isReplay()) return;
      var sp = (st.spMap || {})[st.key + '|' + page]; if (!sp) return;
      var tmp = document.createElement('div'); tmp.innerHTML = LIVE.spBoxHtml(sp); view.insertBefore(tmp.firstChild, view.firstChild); LIVE.spBind();
    },
    spFwHtml: function (t) {
      var st = C.st, sp = (st.spMap || {})[st.key + '|trace|' + t.card_id + '|' + t.tp];
      return sp ? LIVE.spBoxHtml(sp) : '<div class="sp-row">' + LIVE.spBtn('data-sp-trace="1"', '星灵讲讲这个数') + '</div>';
    },
    /* 竞争性解释最上面：一段人话。先显示程序拼的版本（每句只用已有事实）；我点了“星灵解读”后本机 Qwen 才写，逐句核对通过后可切换查看 */
    cpExplainHtml: function (d) {
      var esc = C.esc, ic = C.ic, st = C.st, NAME = {};
      d.columns.forEach(function (c) { NAME[c.id] = c.name.replace(/（.*?）/g, '').replace('变化与之前的时点比', '变化'); });
      var ai = st.cpAi && st.cpAi.key === st.key && st.cpAi.tp === d.tp ? st.cpAi.res : null;
      var useAi = ai && ai.state === 'ok' && !st.cpFixed, ex = useAi ? ai.sentences : (d.explain || []), right, more = '';
      var bad = function (list) { return '<details class="cp-rej"><summary data-ptds-inline><!--ptds-ui:s29bc78f35a93-->看没通过核对的句子（<!--/ptds-ui-->' + list.length + '）</summary>' + list.map(function (x) { return '<div class="cp-l"><span>' + esc(x.text) + '</span><span class="sub2">' + esc((x.bad || []).join('；')) + '</span></div>'; }).join('') + '</details>'; };
      var asked = (st.cpAsked || {})[st.key + '|' + d.tp];
      if (useAi) {
        right = esc(ai.by) + ' · 逐句核对 ' + ai.checked + '/' + ai.checked + ' 通过 <button class="cp-tag" data-cp-fixed="1" data-ptds-ui="s3b109a65fc4e">看程序版本</button>';
        if (ai.rejected && ai.rejected.length) more = '<div class="sub2" data-ptds-ui="s06998ede1d95">第一次写的有句子没通过核对，已让它重写。</div>' + bad(ai.rejected);
      } else if (ai && ai.state === 'ok') right = '程序按已有事实拼写 <button class="cp-tag" data-cp-fixed="0" data-ptds-ui="se76a74db5dd8">看星灵版本</button>';
      else if (ai && asked && ai.state !== 'idle') { var x = LIVE.spStateHtml(ai, '版本'); right = '程序按已有事实拼写' + (x.right ? ' · ' + x.right : ''); more = x.body; }
      else right = '程序按已有事实拼写 ' + LIVE.spBtn('data-cp-ask="1"');
      return '<div class="cp-ex" id="cp-ex"><div class="sub2">' + ic('sparkle') + (d.kind === 'retro' ? ' 换一种方法回头再算，结论哪天开始不一样' : ' 为什么这几种算法说法不一样') + '<span class="grow" style="flex:1"></span><span class="cp-right">' + right + '</span></div>' +
        ex.map(function (x) { return '<p>' + esc(x.text) + ' ' + (x.cols || []).map(function (id) { return '<button class="cp-tag" data-cp-col="' + esc(id) + '">' + esc(NAME[id] || id) + '</button>'; }).join('') + '</p>'; }).join('') + LIVE.cpSumHtml(d, useAi ? ai.summary : null, useAi ? ai.by : '') + LIVE.cpNextHtml(d, useAi ? ai : null) + more + '</div>';
    },
    /* 下一步（产品负责人 2026-10-14）：动作只从算法分歧里来（程序列候选）；千问核对通过时按它挑的先后和理由显示。一眼 3 行，点开看依据和问题 */
    cpNextHtml: function (d, ai) {
      var esc = C.esc, ic = C.ic, nx = d.next; if (!nx || !nx.actions.length) return '';
      var IC = { doctor: 'message-circle', lab: 'flask-conical', watch: 'activity', self: 'pencil', set: 'settings' }, by = {}, order = [], why = {};
      nx.actions.forEach(function (a) { by[a.id] = a; });
      if (ai && ai.next && ai.next.length) ai.next.forEach(function (x) { if (by[x.id]) { order.push(by[x.id]); why[x.id] = x.why; } });
      nx.actions.forEach(function (a) { if (order.indexOf(a) < 0) order.push(a); });
      var ask = ai && ai.ask && ai.ask.length ? ai.ask : nx.ask;
      var row = function (a) {
        var body = '<div class="sub2">' + esc(a.text) + '</div>' + (a.kind === 'doctor' ? '<ol class="cp-ask">' + ask.map(function (q) { return '<li>' + esc(q) + '</li>'; }).join('') + '</ol><button class="cp-tag" data-cp-copy="1">' + ic('copy') + ' 复制这些问题</button>' : '');
        return '<details class="cp-nx"><summary><span class="cp-ni">' + ic(IC[a.kind] || 'chevron-right') + '</span><span class="cp-nt">' + esc(a.kind === 'doctor' ? '带去问医生（' + ask.length + ' 个问题）' : a.title) + (why[a.id] ? '<span class="cp-nw">' + esc(why[a.id]) + '</span>' : '') + '</span></summary>' + body + '</details>';
      };
      LIVE._cpAsk = ask;
      return '<div class="cp-next"><div class="sub2">' + ic('list-checks') + ' 下一步' + (ai && ai.next && ai.next.length ? '<span class="cp-src">' + C.esc(ai.by) + ' · 排序已核对</span>' : '') + '</div>' +
        order.slice(0, 3).map(row).join('') + (order.length > 3 ? '<details class="more"><summary data-ptds-inline><!--ptds-ui:s268ec6902063-->另有 <!--/ptds-ui-->' + (order.length - 3) + ' 项</summary>' + order.slice(3).map(row).join('') + '</details>' : '') +
        '<div class="sub2 cp-nn">' + esc(nx.note) + '</div></div>';
    },
    /* 小结（产品负责人 2026-10-14）：客观部分是程序算的“换几种算法再算，等级变不变”，照实显示；千问的解读核对通过才显示，标明出处 */
    cpSumHtml: function (d, aiSum, by) {
      var esc = C.esc, ic = C.ic, sb = d.stability; if (!sb) return '';
      var rt = d.kind === 'retro', hl = function (h) { return '<div class="cp-l2"><span>' + esc(h.zh) + '</span><span class="cp-o ' + (!h.changed ? 'same' : h.level === 'UNDETERMINED' || h.level === 'NA' ? 'na' : 'ok') + '">' + esc(h.level_zh) + (h.changed && !rt ? '（变了）' : '') + '</span></div>'; };
      return '<div class="cp-sum"><div class="sub2">' + ic('scale') + ' 小结</div><p>' + sb.text.map(esc).join('') + '</p>' +
        (aiSum && aiSum.length ? '<p class="cp-ai">' + aiSum.map(function (x) { return esc(x.text); }).join('') + ' <span class="cp-src">' + esc(by || '星灵') + ' · 已核对</span></p>' : '') +
        '<details class="more"><summary data-ptds-inline><!--ptds-ui:sa91494b24267-->怎么看出来的：<!--/ptds-ui-->' + (rt ? '同一段数据换 ' + sb.alt + ' 种方法各算一遍' : '同一组数据换 ' + sb.alt + ' 种算法各算一遍') + '</summary><div class="sub2">' + esc(sb.how || '只用其中一套标准算，或者把“变化”的灵敏度调高、调低再算，看合起来的关注等级会不会跟着变。') + '</div><div class="cp-hyp">' + sb.rows.map(hl).join('') + '</div></details></div>';
    },
    /* 千问版本在后台写：页面先显示程序版本，每 4 秒问一次，写好就只换掉解释框，不重画整页 */
    cpAiPoll: function (d, start) {
      var st = C.st, key = st.key, tp = d.tp;
      if (!start && !(st.cpAsked || {})[key + '|' + tp]) return;  /* 没点过“星灵解读”就不问、不写（产品负责人 2026-10-14） */
      if (!start && st.cpAi && st.cpAi.key === key && st.cpAi.tp === tp && st.cpAi.res.state !== 'running') return;
      clearTimeout(LIVE._cpT);
      fetch((d.kind === 'retro' ? '/api/track/retro_ai?key=' : '/api/track/compete_ai?key=') + encodeURIComponent(key) + '&tp=' + encodeURIComponent(tp) + '&start=' + (start ? 1 : 0)).then(function (r) { return r.json(); }).then(function (res) {
        if (C.st.key !== key) return;
        st.cpAi = { key: key, tp: tp, res: res };
        var box = document.getElementById('cp-ex');
        if (!box || (d.kind !== 'retro' && C.st.cmpTp && C.st.cmpTp !== tp) || (d.kind === 'retro') !== !!document.querySelector('[data-rt-open]')) return;
        box.outerHTML = LIVE.cpExplainHtml(d);
        LIVE.cpBind();
        if (res.state === 'running') LIVE._cpT = setTimeout(function () { if (document.getElementById('cp-ex')) LIVE.cpAiPoll(d); }, 4000);
      }).catch(function () {});
    },
    cpBind: function () {
      var st = C.st;
      document.querySelectorAll('[data-cp-col]').forEach(function (b) { b.onclick = function () {
        st.cpOpen = b.dataset.cpCol; var y = window.scrollY; LIVE.renderAdvanced(); window.scrollTo(0, y);
        var box = document.querySelector('.cp-open'); if (box) box.scrollIntoView({ block: 'nearest', behavior: 'smooth' }); }; });
      document.querySelectorAll('[data-cp-copy]').forEach(function (b) { b.onclick = function () { var t = (LIVE._cpAsk || []).map(function (q, i) { return (i + 1) + '. ' + q; }).join('\n'); try { navigator.clipboard.writeText(t); C.toast('已复制 ' + (LIVE._cpAsk || []).length + ' 个问题'); } catch (e) { if(e&&(e.viewPending||e.code==='VIEW_CHANGED'))throw e;} }; });
      document.querySelectorAll('[data-cp-ask]').forEach(function (b) { b.onclick = function () {
        var d = document.querySelector('[data-rt-open]') ? LIVE._rtD : LIVE._cpD; if (!d) return;
        st.cpAsked = st.cpAsked || {}; st.cpAsked[st.key + '|' + d.tp] = 1; st.cpFixed = false;
        st.cpAi = { key: st.key, tp: d.tp, res: { state: 'running', by: '' } };
        var box = document.getElementById('cp-ex'); if (box) { box.outerHTML = LIVE.cpExplainHtml(d); LIVE.cpBind(); }
        LIVE.cpAiPoll(d, true); }; });
      document.querySelectorAll('[data-cp-fixed]').forEach(function (b) { b.onclick = function () { st.cpFixed = b.dataset.cpFixed === '1'; var y = window.scrollY; LIVE.renderAdvanced(); window.scrollTo(0, y); }; });
    },
    CP_CSS: '.cp-ex{margin:var(--primitive-space-4) 0;padding:var(--primitive-space-4);border-left:2px solid #E8B65A;background:rgba(232,182,90,.05);border-radius:0 8px 8px 0}.cp-ex p{margin:var(--primitive-space-2) 0;line-height:1.7}.cp-ex .sub2{display:flex;gap:6px;align-items:center}' +
      '.cp-tag{font:inherit;font-size:var(--scale-type-meta);color:var(--theme-text-secondary);background:none;border:var(--primitive-border-hairline) solid var(--theme-line-control);border-radius:10px;padding:0 8px;margin-left:4px;cursor:pointer}.cp-tag:hover{color:#E8B65A;border-color:#E8B65A}' +
      '.cp-tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:var(--primitive-space-3);margin:var(--primitive-space-3) 0}.cp-tile{display:flex;flex-direction:column;gap:4px;text-align:left;font:inherit;color:inherit;background:var(--theme-surface-raised,rgba(255,255,255,.03));border:var(--primitive-border-hairline) solid var(--theme-line-hairline);border-radius:10px;padding:var(--primitive-space-3) var(--primitive-space-4);cursor:pointer}.cp-tile .v{font-size:var(--scale-type-title)}.cp-tile .v.ok{color:#E8B65A}.cp-tile .v.na{color:var(--theme-text-tertiary)}' +
      '.cp-hyp{display:grid;grid-template-columns:1fr 1fr;column-gap:var(--primitive-space-6);font-size:var(--scale-type-meta)}.cp-o.same{color:var(--theme-text-tertiary)}.cp-stab{margin:var(--primitive-space-4) 0;padding-top:var(--primitive-space-3);border-top:var(--primitive-border-hairline) solid var(--theme-line-hairline)}.cp-stab p{margin:var(--primitive-space-2) 0;line-height:1.7}.cp-allv{margin-bottom:var(--primitive-space-3);font-size:var(--scale-type-meta)}.cp-allv .big{font-size:var(--scale-type-title)}.cp-allv .cp-l,.cp-allv .sub2{font-size:var(--scale-type-meta)}.cp-allv .cp-l{grid-template-columns:minmax(0,1.5fr) minmax(0,1fr) auto;padding:3px 0}.cp-allv h3{font-size:var(--scale-type-body)}.cp-l2{display:flex;justify-content:space-between;gap:var(--primitive-space-3);padding:var(--primitive-space-1) 0;border-bottom:var(--primitive-border-hairline) solid var(--theme-line-hairline)}@media (max-width:760px){.cp-hyp{grid-template-columns:1fr}}' +
      '.cp-tile .sub2{display:flex;align-items:center;gap:4px}.cp-tile.on{border-color:#E8B65A}' +
      '.cp-open{border:var(--primitive-border-hairline) solid rgba(232,182,90,.5);border-radius:10px;padding:var(--primitive-space-3) var(--primitive-space-4);margin-bottom:var(--primitive-space-3);font-size:var(--scale-type-meta)}' +
      '.cp-open .cp-og{margin-top:var(--primitive-space-2)}.cp-open .cp-l{grid-template-columns:minmax(0,2fr) minmax(0,1.4fr) 7em;padding:3px 0}.cp-open .cp-l.deep{padding-left:0}.cp-open .cp-l.deep>span:first-child{padding-left:var(--primitive-space-5)}.cp-oh{font-size:var(--scale-type-body)}' +
      '.cp-next{margin-top:var(--primitive-space-3);padding-top:var(--primitive-space-3);border-top:var(--primitive-border-hairline) solid rgba(232,182,90,.3)}.cp-nx{border-bottom:var(--primitive-border-hairline) solid var(--theme-line-hairline);padding:6px 0}.cp-nx summary{display:flex;gap:var(--primitive-space-2);align-items:baseline;cursor:pointer;list-style:none}.cp-nx summary::-webkit-details-marker{display:none}.cp-ni{color:#E8B65A;flex:none}.cp-nt{display:flex;flex-direction:column}.cp-nw{font-size:var(--scale-type-meta);color:var(--theme-text-secondary)}.cp-nx>.sub2,.cp-ask,.cp-nx>.cp-tag{margin-left:1.8em}.cp-ask{margin-top:4px;margin-bottom:6px;padding-left:1.2em;line-height:1.7}.cp-nn{margin-top:var(--primitive-space-2);font-size:var(--scale-type-meta)}.cp-sum{margin-top:var(--primitive-space-3);padding-top:var(--primitive-space-3);border-top:var(--primitive-border-hairline) solid rgba(232,182,90,.3)}.cp-sum p{margin:var(--primitive-space-2) 0;line-height:1.7}.cp-ai{color:var(--theme-text-secondary)}.cp-src{font-size:var(--scale-type-meta);color:#E8B65A;border:var(--primitive-border-hairline) solid rgba(232,182,90,.5);border-radius:10px;padding:0 8px;margin-left:4px;white-space:nowrap}.cp-right{display:inline-flex;align-items:center;gap:4px}.cp-rej{margin-top:var(--primitive-space-2);font-size:var(--scale-type-meta)}.cp-rej summary{cursor:pointer;color:var(--theme-text-secondary)}.cp-rej .cp-l{grid-template-columns:minmax(0,2fr) minmax(0,1fr)}' +
      '.sp-btn{display:inline-flex;align-items:center;gap:5px;font:inherit;font-size:var(--scale-type-meta);color:#E8B65A;background:rgba(232,182,90,.08);border:var(--primitive-border-hairline) solid rgba(232,182,90,.55);border-radius:999px;padding:2px 10px;margin-left:6px;cursor:pointer;vertical-align:middle}.sp-btn:hover{background:rgba(232,182,90,.16)}' +
      '.sp-btn.sp-icon-only,.nt-btns .sp-btn.sp-icon-only{width:32px;height:32px;padding:0;gap:0;justify-content:center;flex:none;border-radius:50%}.sp-icon-only .sp-ic svg{width:18px;height:18px}.sp-icon-only:focus-visible{outline:2px solid var(--theme-text-primary);outline-offset:3px}' +
      '.sp-ic{display:inline-flex;transform-origin:50% 50%}.sp-btn:hover .sp-ic,.sp-btn:focus-visible .sp-ic{animation:spw 900ms ease-in-out infinite}.sp-ic.on{color:#E8B65A}' +
      '@keyframes spw{0%{transform:rotate(0) scale(1)}25%{transform:rotate(-14deg) scale(1.15)}50%{transform:rotate(10deg) scale(.95)}75%{transform:rotate(-6deg) scale(1.1)}100%{transform:rotate(0) scale(1)}}@media (prefers-reduced-motion:reduce){.sp-btn:hover .sp-ic{animation:none}}' +
      '#sq-fab{position:fixed;right:28px;bottom:28px;width:52px;height:52px;margin:0;padding:0;justify-content:center;border-radius:50%;background:var(--theme-surface-raised);box-shadow:0 6px 20px rgba(0,0,0,.4);z-index:61}#sq-fab .sp-ic svg{width:24px;height:24px}#sq-fab{cursor:grab;touch-action:none;transition:left .2s ease,right .2s ease,top .2s ease}#sq-fab.drag{cursor:grabbing;transition:none}' +
      '.tl-fab{position:fixed;right:16px;bottom:92px;width:52px;height:52px;border-radius:50%;display:flex;align-items:center;justify-content:center;padding:0;background:var(--theme-surface-raised);color:#cfd6e2;border:var(--primitive-border-hairline) solid rgba(190,200,215,.7);box-shadow:0 6px 20px rgba(0,0,0,.4);z-index:61;cursor:grab;touch-action:none;transition:left .2s ease,right .2s ease,top .2s ease}.tl-fab.drag{cursor:grabbing;transition:none}' +
      '.tl-ic{display:inline-flex;transform-origin:50% 50%}.tl-ic svg{width:24px;height:24px}.tl-ic.sm svg{width:16px;height:16px}.tl-fab:hover .tl-ic{animation:spw 900ms ease-in-out infinite}@media (prefers-reduced-motion:reduce){.tl-fab:hover .tl-ic{animation:none}}' +
      '.tl-dot{position:absolute;right:3px;top:3px;width:10px;height:10px;border-radius:50%;border:2px solid var(--theme-surface-raised)}.tl-dot.ok{background:#5bd29a}.tl-dot.stale{background:#E8B65A}.tl-dot.off{background:#8a90a0}' +
      '.tl-name{display:inline-flex;align-items:center;gap:5px;font:inherit;color:#cfd6e2;background:none;border:var(--primitive-border-hairline) solid transparent;border-radius:8px;padding:2px 6px;margin-left:-6px;cursor:pointer;flex:none}.tl-name:hover{border-color:rgba(190,200,215,.5)}.tl-name b{color:var(--theme-text-primary)}.tl-name svg{width:14px;height:14px}' +
      '.tl-s{display:flex;flex-wrap:wrap;gap:6px;margin:8px 0}.tl-o{font:inherit;font-size:var(--scale-type-meta);color:var(--theme-text-secondary);background:rgba(128,140,160,.1);border:var(--primitive-border-hairline) solid transparent;border-radius:12px;padding:3px 10px;cursor:pointer;display:inline-flex;align-items:center;gap:4px}.tl-o.on{color:var(--theme-text-primary);border-color:rgba(190,200,215,.6)}.tl-n{font-size:11px;background:#cfd6e2;color:#141a2c;border-radius:50%;width:15px;height:15px;display:inline-flex;align-items:center;justify-content:center}.tl-acts{display:flex;gap:8px;align-items:center}' +
      window.PTDSTail.css +
      '#sq{position:fixed;right:28px;bottom:92px;width:420px;max-width:calc(100vw - 32px);max-height:calc(100vh - 120px);display:flex;flex-direction:column;background:var(--theme-surface-raised);color:var(--theme-text-primary);border:var(--primitive-border-hairline) solid rgba(232,182,90,.55);border-radius:14px;box-shadow:0 14px 40px rgba(0,0,0,.45);z-index:61}' +
      '.sq-h{display:flex;align-items:center;gap:8px;padding:12px 16px;border-bottom:var(--primitive-border-hairline) solid var(--theme-line-hairline)}.sq-h b,.sq-h .chip{white-space:nowrap;flex:none}.sq-h .sub2{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.sq-h .sp-ic svg{width:18px;height:18px}.sq-b{overflow:auto;padding:4px 16px 8px;flex:1}.sq-e{margin:12px 0;line-height:1.7}' +
      '.sq-q{margin:12px 0 6px;text-align:right}.sq-q span{display:inline-block;background:rgba(128,140,160,.14);border-radius:12px 12px 2px 12px;padding:6px 12px;text-align:left}' +
      '.sq-a{border-left:2px solid #E8B65A;background:rgba(232,182,90,.05);border-radius:0 8px 8px 0;padding:8px 12px;line-height:1.7}.sq-a.prog{border-left-color:#7fa7d9;background:rgba(127,167,217,.07)}.sq-a.fence{border-left-color:#8a90a0;background:rgba(138,144,160,.08)}' +
      '.sq-m{font-size:var(--scale-type-meta);color:var(--theme-text-tertiary);display:flex;gap:6px;align-items:center;flex-wrap:wrap;margin-bottom:2px}.sq-d{border:var(--primitive-border-hairline) solid var(--theme-line-control);border-radius:10px;padding:0 8px;color:var(--theme-text-secondary)}' +
      '.sq-go{font:inherit;font-size:var(--scale-type-meta);color:#E8B65A;border:var(--primitive-border-hairline) solid rgba(232,182,90,.5);border-radius:10px;padding:1px 9px;background:none;margin:6px 4px 0 0;cursor:pointer}.sq-f{font-size:var(--scale-type-meta);color:var(--theme-text-tertiary);margin-top:4px}.sq-f summary{cursor:pointer}' +
      '.sq-mem{margin:6px 0 2px;padding:6px 10px;border:var(--primitive-border-hairline) dashed rgba(127,167,217,.6);border-radius:8px;font-size:var(--scale-type-meta)}.sq-mh{display:flex;gap:8px;align-items:center;margin:10px 0 0}.sq-mh .inp{flex:1}.sq-mi{margin:10px 0;padding:8px 10px;border-radius:8px;background:rgba(128,140,160,.08)}' +
      '.sq-ft{padding:10px 16px 12px;border-top:var(--primitive-border-hairline) solid var(--theme-line-hairline)}.sq-row{display:flex;gap:8px}.sq-row .inp{flex:1}.sq-n{margin-top:6px}' +
      '@media (max-width:720px){#sq{right:8px;left:8px;width:auto;bottom:88px}#sq-fab{right:16px;bottom:16px}}' +
      '#nt-card{position:fixed;width:400px;max-width:calc(100vw - 32px);max-height:calc(100vh - 120px);overflow:auto;padding:14px 18px;background:var(--theme-surface-raised);color:var(--theme-text-primary);border:var(--primitive-border-hairline) solid rgba(232,182,90,.7);border-radius:14px;box-shadow:0 14px 40px rgba(0,0,0,.45);z-index:60}' +
      '.nt-h{display:flex;align-items:center;gap:8px;margin-bottom:6px}.nt-h .grow{flex:1}.nt-dot{width:8px;height:8px;border-radius:50%;background:#E8B65A;flex:none}.nt-dot.lv-WATCH{background:#7fa7d9}.nt-b{margin:4px 0;line-height:1.7}' +
      '.nt-btns{display:flex;flex-wrap:wrap;gap:8px;margin:10px 0 6px;align-items:center}.nt-btn{display:inline-flex;align-items:center;gap:5px;font:inherit;font-size:var(--scale-type-meta);color:var(--theme-text-primary);background:none;border:var(--primitive-border-hairline) solid var(--theme-line-control);border-radius:8px;padding:4px 10px;cursor:pointer}.nt-btn.pri{background:rgba(232,182,90,.14);border-color:rgba(232,182,90,.6)}.nt-btn:hover{border-color:#E8B65A}.nt-btn svg{width:14px;height:14px}.nt-btns .sp-btn{margin:0;padding:4px 10px}' +
      '.nt-cal{margin:2px 0 6px}.nt-f{margin-top:8px;line-height:1.6;display:block}.nt-link{font:inherit;color:#E8B65A;background:none;border:0;padding:0;cursor:pointer;text-decoration:underline}#nt-card .sp-box{margin:8px 0 0}#nt-card .sp-box>.sub2{flex-wrap:wrap}#nt-card .sp-box .cp-right{order:3;flex-basis:100%}' +
      '@media (max-width:720px){#nt-card{left:8px!important;right:8px!important;width:auto}}' +
      '.sp-t{white-space:nowrap}#fw .sp-box>.sub2{flex-wrap:wrap}#fw .sp-box .cp-right{order:3;flex-basis:100%}.sp-box{margin-top:0}.sp-box .sp-x{margin-left:6px}.sp-facts{line-height:1.8;margin:4px 0 0 1em}.sp-row{margin:0 0 10px}' +
      '.rt-g{padding:var(--primitive-space-2) var(--primitive-space-3)}.rt-svg{display:block;margin:4px 0}.rt-svg line,.rt-svg path,.rt-svg>text{pointer-events:none}.rt-svg .rt-n{cursor:pointer}.rt-svg .rt-n:hover circle{stroke:#E8B65A;stroke-width:3}.rt-lg{display:flex;flex-wrap:wrap;gap:6px 16px;align-items:center}.rt-dot{display:inline-block;width:9px;height:9px;border-radius:50%;border:1.5px solid var(--theme-text-tertiary);margin-right:4px;vertical-align:-1px}.rt-dot.a{background:#E8B65A;border-color:#E8B65A}.rt-dot.n{border-style:dashed}.rt-runs{margin:var(--primitive-space-3) 0}' +
      '.cp-spin{display:inline-block;width:8px;height:8px;border-radius:50%;background:#E8B65A;margin-right:6px;animation:cpb 1.2s ease-in-out infinite}@keyframes cpb{50%{opacity:.25}}@media (prefers-reduced-motion:reduce){.cp-spin{animation:none}}' +
      '.cp-col.hl{border-color:#E8B65A;box-shadow:0 0 0 1px rgba(232,182,90,.4)}' +
      '.cp-cols{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:var(--primitive-space-3);align-items:start}' +
      '.cp-col{min-width:0}.cp-g{display:grid;gap:var(--primitive-space-1);margin-top:var(--primitive-space-2)}' +
      '.cp-l{display:grid;grid-template-columns:minmax(0,1.4fr) minmax(0,1fr) auto;gap:var(--primitive-space-2);align-items:baseline;padding:var(--primitive-space-1) 0;border-bottom:var(--primitive-border-hairline) solid var(--theme-line-hairline)}' +
      '.cp-l>span{min-width:0;overflow-wrap:anywhere}.cp-l.deep{padding-left:var(--primitive-space-4)}' +
      '.cp-o{font-size:var(--scale-type-meta);white-space:nowrap}.cp-o.ok{color:#E8B65A}.cp-o.use{color:var(--theme-text-primary)}.cp-o.no{color:var(--theme-text-tertiary)}.cp-o.na{color:var(--theme-text-tertiary);font-style:italic}' +
      '.cp-h{display:grid;gap:var(--primitive-space-1);max-width:640px}',
    /* 星灵：在当前页面原位回答"这是什么、从哪来、去哪看"。只读；本机千问只看等级标签与对象引用，不看具体数值（HR-42） */
    spiritLive: function () { return !C.isReplay() && (C.S()._scope === 'home' || C.S().runs_by_tp !== undefined); },
    spiritPage: function () {
      var st = C.st;
      if (st.foot) return { page: 'general' };
      if (st.app === 'torch') {
        if (st.tview === 'detail' && st.tdetail) return { page: 'torch_detail', ref: st.tdetail.ref };
        if (st.tview === 'graph') return { page: 'graph', tp: st.graphTp || null };
        if (st.entry) return { page: 'entry' };
        return { page: { gene: 'gene', data: 'data', guard: 'guard', sources: 'sources', srcgroup: 'sources', apple: 'sources', connect: 'sources' }[st.tview] || 'data' };
      }
      if (st.app === 'cluster') return st.cview === 'grant' ? { page: 'grant', gid: st.gid } : { page: 'cluster' };
      if (st.view === 'detail') return { page: 'tp', tp: st.tp };
      if (st.view === 'status') return st.card === 'VITALS' ? { page: 'vitals' } : { page: 'card' };
      if (st.view === 'adv') return { page: 'compete', tp: st.cmpTp || null };
      return { page: { alerts: 'alerts', wall: 'wall' }[st.view] || 'track' };
    },
    /* 问星灵（产品负责人 2026-10-14）：左下角的标识撤掉，换成右下角的星灵图标浮窗。问 PTDS（星炬 / 星轨 / 星簇）里的记录；
       程序先分流（越界不答、要它做事就指路、问数值由程序查），进了门的才交给本机 Qwen。点了“问”才问，一次只问一个。不兜底。 */
    askFab: function (off) {
      LIVE.tailMount(off); LIVE.bandTailMount(off); LIVE.pillboxMount(off);
      var on = false; try { on = !off && (!window.PTDS_TRIAL_UI || window.PTDS_TRIAL_UI.can('starlingActions')) && LIVE.spiritLive(); } catch (err) { if(err&&(err.viewPending||err.code==='VIEW_CHANGED'))throw err; on = false; }
      var f = document.getElementById('sq-fab');
      if (!on) { if (f) f.remove(); var p0 = document.getElementById('sq'); if (p0) p0.remove(); return; }
      if (!f) {
        f = document.createElement('button'); f.id = 'sq-fab'; f.className = 'sp-btn'; f.setAttribute('aria-label', '问星灵'); f.title = '问星灵';
        f.innerHTML = '<span class="sp-ic">' + C.ic('sparkles') + '</span>'; document.body.appendChild(f); LIVE.sqDrag(f);
      }
      LIVE.noticeMount();
    },
    /* 规则触发，星灵转告（产品负责人 2026-10-14 00:37 / 00:42 / 00:43）：触发器是状态规则库里的规则，不是星灵。
       有没读过的“观察 / 关注”提醒，就在星灵图标旁弹一张小卡；话是程序按规则写的（提醒原文 + 建议复查），不调千问。
       “星灵讲讲”一直在：点了才让本机 Qwen 讲为什么触发（只给规则和结论，不给数值），逐句核对，不兜底。✕ = 知道了（和横幅同步）。 */
    noticeMount: function () {
      var S = null; try { S = C.S(); } catch (err) { if(err&&(err.viewPending||err.code==='VIEW_CHANGED'))throw err; S = null; }
      var n = S && S.notice, el = document.getElementById('nt-card'), fab = document.getElementById('sq-fab');
      if (!n || !fab || C.st.acked[n.dedupe_key] || document.getElementById('sq') || document.getElementById('fw') || C.isReplay()) { if (el) el.remove(); return; }
      var esc = C.esc, ic = C.ic, st = C.st;
      if (!el) { el = document.createElement('div'); el.id = 'nt-card'; el.setAttribute('role', 'alertdialog'); el.setAttribute('aria-label', '星灵转告 · 规则触发'); document.body.appendChild(el); }
      if (el.dataset.dk !== n.dedupe_key) { el.dataset.dk = n.dedupe_key; LIVE._ntSp = null; LIVE._ntCal = null; }
      var sp = LIVE._ntSp && LIVE._ntSp.dk === n.dedupe_key ? LIVE._ntSp : null;
      var when = C.tzTime(n.created_at, true), cal = LIVE._ntCal;
      el.innerHTML = '<div class="nt-h"><span class="nt-dot lv-' + esc(n.level) + '"></span><b data-ptds-ui="sb73b00992718">星灵转告 · 规则触发</b><span class="grow"></span><span class="sub2">' + esc((String(when).match(/^\d{4}-(\d\d-\d\d) (\d\d:\d\d)/) || ['', '', '']).slice(1).join(' ')) + '</span>' +
        '<button class="ibtn" data-nt-x="1" aria-label="知道了，关掉" title="知道了，关掉" data-ptds-ui-aria-label="s6b50b24af65f" data-ptds-ui-title="s6b50b24af65f">' + ic('x') + '</button></div>' +
        '<p class="nt-b">' + esc(String(n.body || '').replace(/这不是诊断，请联系主治医生。$/, '')) + '</p><p class="nt-b">' + esc(n.advice) + '</p>' +
        '<div class="nt-btns"><button class="nt-btn pri" data-nt-cal="1">' + ic('clock') + ' 加到日历：预约复查</button><button class="nt-btn" data-nt-trace="1" data-ptds-ui="sefee679233fb">看依据</button>' + LIVE.spBtn('data-nt-sp="1"', '星灵讲讲') + '</div>' +
        (cal ? '<div class="sub2 nt-cal">' + esc(cal) + '</div>' : '') +
        (sp ? LIVE.spBoxHtml(sp) : '') +
        '<div class="sub2 nt-f" data-ptds-inline><!--ptds-ui:s94144064149b-->触发来自状态规则库：<!--/ptds-ui--><button class="nt-link" data-nt-rule="1">' + esc(n.rule_set_zh) + '</button>。这段话由程序按规则写，不是千问；点“星灵讲讲”才调用' + esc((n.sign || '星灵').replace(/发出$/, '')) + '。</div>';
      var g = function (sel, fn) { var b = el.querySelector(sel); if (b) b.onclick = LIVE.action(fn); };
      g('[data-nt-x]', LIVE.action(async function () { (await LIVE.ack(n.dedupe_key)); LIVE._ntSp = null; el.remove(); C.renderMainOnly(); }));
      g('[data-nt-rule]', function () { LIVE.goRule(n.rule_set, n.rule_id); });
      g('[data-nt-trace]', function () {
        if (n.card_id === 'sjia-mas') { LIVE.openTrace(n.card_id, n.tp); return; }
        C.goTrack('wall'); st.ccard = n.card_id; st.ccAsk = null; st.view = 'custom'; C.render(); window.scrollTo(0, 0);
      });
      g('[data-nt-cal]', LIVE.action(async function () {
        try {
          var r = (await call('POST', '/api/alerts/calendar', { key: st.key, dedupe_key: n.dedupe_key }));
          var d = r.day.slice(5).replace('-', ' 月 ') + ' 日 ' + r.time;
          if (r.opened) LIVE._ntCal = '已在 Mac 日历里打开：' + d + '，点“添加”才会加入，时间可以在日历里改。日历里不写任何数值。';
          else {
            var a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([r.ics], { type: 'text/calendar' })); a.download = r.file; document.body.appendChild(a); a.click(); a.remove();
            LIVE._ntCal = '已下载日历文件（' + d + '），打开它再点“添加”。日历里不写任何数值。';
          }
        } catch (err) { if(err&&(err.viewPending||err.code==='VIEW_CHANGED'))throw err; LIVE._ntCal = '没能生成日历（' + LIVE.saveErr(err) + '）'; }
        LIVE.noticeMount();
      }));
      g('[data-nt-sp]', function () {
        var s2 = { k: 'nt', dk: n.dedupe_key, page: 'alert', id: 'sp-nt', title: '', res: { state: 'running', by: '' },
          url: '/api/starling/page?key=' + encodeURIComponent(st.key) + '&page=alert&dk=' + encodeURIComponent(n.dedupe_key) };
        LIVE._ntSp = s2; LIVE.noticeMount(); LIVE.ntAsk(s2, true);
      });
      var sx = el.querySelector('[data-sp-close]'); if (sx) sx.onclick = function () { LIVE._ntSp = null; LIVE.noticeMount(); };
      /* 放在星灵图标旁边：同一边，图标上方放得下就放上方 */
      var r0 = fab.getBoundingClientRect(), H = window.innerHeight, W = window.innerWidth, left = r0.left < W / 2;
      el.style.left = left ? '16px' : 'auto'; el.style.right = left ? 'auto' : '16px';
      var ph = el.offsetHeight;
      if (r0.top - 12 >= ph + 8) { el.style.top = 'auto'; el.style.bottom = (H - r0.top + 12) + 'px'; } else { el.style.bottom = 'auto'; el.style.top = Math.min(r0.bottom + 12, H - ph - 12) + 'px'; }
    },
    ntAsk: function (sp, start) {
      clearTimeout(sp.timer);
      fetch(sp.url + (start ? '&start=1' : '&start=0')).then(function (r) { return r.json(); }).then(function (res) {
        if (LIVE._ntSp !== sp) return;
        if (!start && res.state === 'idle') res = sp.res || res;
        if (res.state === 'none') res = { state: 'blocked', why: '这条提醒已经不在了，星灵没有可讲的记录' };
        sp.res = res; LIVE.noticeMount();
        if (res.state === 'running') sp.timer = setTimeout(function () { LIVE.ntAsk(sp, false); }, 4000);
      }).catch(function () { sp.res = { state: 'error', why: '连不上本机服务' }; LIVE.noticeMount(); });
    },
    /* 右下角的小图标（星灵、设备小尾巴）：都可拖动，松手贴到最近的左 / 右边；同一边上下排开不重叠（产品负责人 2026-10-14）。
       位置记在本机浏览器里（读不到就用默认位置）；弹出的框跟着各自的图标走。 */
    DOCK: { 'sq-fab': { def: 0, pop: 'sq' } },
    dockPos: function (id) {
      var p = null; try { p = JSON.parse(localStorage.getItem('ptds-dock-' + id) || (id === 'sq-fab' ? localStorage.getItem('ptds-sq-pos') : null) || 'null'); } catch (err) { if(err&&(err.viewPending||err.code==='VIEW_CHANGED'))throw err; p = null; }
      var d = LIVE.DOCK[id] || {}; return p && (p.side === 'left' || p.side === 'right') ? p : d.mem || { side: 'right', y: null };
    },
    dockPlace: function () {
      var H = window.innerHeight, used = { left: [], right: [] };
      Object.keys(LIVE.DOCK).sort(function (a, b) { return (LIVE.DOCK[a].def || 0) - (LIVE.DOCK[b].def || 0); }).forEach(function (id) {
        var f = document.getElementById(id); if (!f) return;
        var d = LIVE.DOCK[id], p = LIVE.dockPos(id), y = p.y == null ? H - 80 - 64 * (d.def || 0) : p.y;
        y = Math.min(Math.max(y, 12), H - 64);
        for (var k = 0; k < 20 && used[p.side].some(function (u) { return Math.abs(u - y) < 60; }); k++) y = y - 60 >= 12 ? y - 60 : y + 60;  // 同一边让开
        used[p.side].push(y);
        f.style.top = y + 'px'; f.style.bottom = 'auto'; f.style.left = p.side === 'left' ? '16px' : 'auto'; f.style.right = p.side === 'right' ? '16px' : 'auto';
        var el = d.pop && document.getElementById(d.pop); if (!el) return;
        var ph = Math.min(el.offsetHeight || 300, H - 32);
        if (d.beside) {  // 设备卡放在图标旁边
          el.style.left = p.side === 'left' ? '80px' : 'auto'; el.style.right = p.side === 'right' ? '80px' : 'auto';
          el.style.bottom = 'auto'; el.style.top = Math.min(Math.max(y + 52 - ph, 12), H - ph - 12) + 'px';
        } else {
          el.style.left = p.side === 'left' ? '16px' : 'auto'; el.style.right = p.side === 'right' ? '16px' : 'auto';
          if (y - 12 >= ph) { el.style.top = 'auto'; el.style.bottom = (H - y + 12) + 'px'; } else { el.style.bottom = 'auto'; el.style.top = Math.min(y + 64, H - ph - 16) + 'px'; }
        }
      });
    },
    sqPlace: function () { LIVE.dockPlace(); },
    dockDrag: function (f, id, onTap) {
      var sx, sy, oy, moved = false, down = false;
      f.addEventListener('pointerdown', function (e) { down = true; moved = false; sx = e.clientX; sy = e.clientY; oy = sy - f.getBoundingClientRect().top; f.setPointerCapture(e.pointerId); });
      f.addEventListener('pointermove', function (e) {
        if (!down) return;
        if (!moved && Math.abs(e.clientX - sx) + Math.abs(e.clientY - sy) < 6) return;
        moved = true; f.classList.add('drag');
        f.style.left = (e.clientX - 26) + 'px'; f.style.top = (e.clientY - oy) + 'px'; f.style.right = 'auto'; f.style.bottom = 'auto';
      });
      f.addEventListener('pointerup', function (e) {
        if (!down) return; down = false; f.classList.remove('drag');
        if (!moved) { onTap(); return; }
        var p = { side: e.clientX < window.innerWidth / 2 ? 'left' : 'right', y: e.clientY - oy };
        // 拖到的这一个优先占位：别的图标在同一高度就让它们让开
        Object.keys(LIVE.DOCK).forEach(function (k) { LIVE.DOCK[k].def = k === id ? -1 : Math.max(LIVE.DOCK[k].def || 0, 0); });
        LIVE.DOCK[id].mem = p;
        try { localStorage.setItem('ptds-dock-' + id, JSON.stringify(p)); } catch (err) { if(err&&(err.viewPending||err.code==='VIEW_CHANGED'))throw err; /* 存不了就只管这一次 */ }
        LIVE.dockPlace();
      });
      if (!LIVE._dockResize) { LIVE._dockResize = true; window.addEventListener('resize', LIVE.dockPlace); }
      LIVE.dockPlace();
    },
    sqDrag: function (f) { LIVE.dockDrag(f, 'sq-fab', LIVE.action(LIVE.openSpirit)); },
    /* 设备小尾巴（产品负责人 2026-10-14 06:59）：Oura 先做；四项都是最近的动态读数，不放评分。只显示星炬里已保存的正式数据，没有就照实写。
       以后加 Whoop / CGM 只要在 TAILS 里加一份配置。数值不交给星灵。 */
    TAILS: [{ id: 'garmin', name: 'Garmin', src: 'DEVICE_GARMIN', chain: 'Garmin Connect → 本机同步 → 个人基座 · 非实时蓝牙',
      syncHint: '每 5 分钟自动同步',
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><rect x="8" y="2" width="8" height="20" rx="4"/><path d="M9 8h6v8H9z"/></svg>',
      choices: [{code:'GARMIN_HR',label:'最近心率',unit:'次/分',when:'instant'}, {code:'GARMIN_STEPS',label:'今日步数',unit:'步',when:'today'}, {code:'GARMIN_SPO2_AVG',label:'平均血氧',unit:'%',when:'dayavg'}, {code:'GARMIN_HRV_NIGHT',label:'夜间平均 HRV',unit:'ms',when:'night'}, {code:'GARMIN_CAL_TOTAL',label:'今日消耗',unit:'千卡',when:'today'}],
      tiles: [{code:'GARMIN_HR',label:'最近心率',unit:'次/分',when:'instant'}, {code:'GARMIN_STEPS',label:'今日步数',unit:'步',when:'today'}, {code:'GARMIN_SPO2_AVG',label:'平均血氧',unit:'%',when:'dayavg'}, {code:'GARMIN_HRV_NIGHT',label:'夜间平均 HRV',unit:'ms',when:'night'}]
    }, { id: 'oura', name: 'Oura', src: 'DEVICE_OURA', chain: 'API 服务：戒指→手机→小尾巴',
      choices: [{ code: 'OURA_HR', label: '最近心率', unit: '次/分', when: 'instant' }, { code: 'OURA_STEPS', label: '今日步数', unit: '步', when: 'today' },
        { code: 'OURA_CAL_TOTAL', label: '今日消耗', unit: '千卡', when: 'today' }, { code: 'OURA_CAL_ACTIVE', label: '活动消耗', unit: '千卡', when: 'today' },
        { code: 'OURA_SPO2', label: '血氧', unit: '%', when: 'night' }, { code: 'OURA_HRV', label: '心率变异性', unit: 'ms', when: 'night' },
        { code: 'OURA_LOWEST_HR', label: '夜间最低心率', unit: '次/分', when: 'night' }, { code: 'OURA_RESP_RATE', label: '呼吸频率', unit: '次/分', when: 'night' },
        { code: 'OURA_TEMP_DEV', label: '体温偏差', unit: '°C', when: 'night' }, { code: 'OURA_TOTAL_SLEEP', label: '昨晚睡眠', unit: '分钟', when: 'night' },
        { code: 'OURA_WORKOUT_MIN', label: '最近运动', unit: '分钟', when: 'instant' }],
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><ellipse cx="12" cy="13" rx="7.5" ry="7"/><path d="M8.5 6.5c1-1.6 2.2-2.4 3.5-2.4s2.5.8 3.5 2.4"/></svg>',
      tiles: [{ code: 'OURA_HR', label: '最近心率', unit: '次/分', when: 'instant' }, { code: 'OURA_STEPS', label: '今日步数', unit: '步', when: 'today' },
        { code: 'OURA_CAL_TOTAL', label: '今日消耗', unit: '千卡', when: 'today' }, { code: 'OURA_SPO2', label: '血氧', unit: '%', when: 'night' }] }],
    /* 用药记录（产品负责人 2026-10-14 07:42 按渲染图做）：手动录入里的第四种方式 + MAS 卡组页的用药背景 + 来龙去脉里“当天在用”。
       只记事实，不判断剂量；记录不交给星灵，不进任何阈值。 */
    MED_UNITS: ['mg', 'mg/kg', 'g', 'μg', 'mL', 'IU', '片', '粒', '支'],
    MED_ROUTES: ['口服', '静脉', '皮下', '肌肉', '外用', '吸入', '其他'],
    MED_COLORS: ['#E8B65A', '#9DB4FF', '#7FD1B9', '#E89A9A', '#C9A6F2'],
    medsGet: function (force) {
      var k = C.st.key;
      if (force || !LIVE._meds || LIVE._meds.key !== k) { var v; try { v = readCached('/api/meds?key=' + encodeURIComponent(k)); } catch (err) { if(err&&(err.viewPending||err.code==='VIEW_CHANGED'))throw err; v = null; }
        if (!v || !v.courses) { LIVE._meds = null; return { courses: [], chain: { ok: true }, failed: true }; } /* 读失败不缓存，下次再读 */
        LIVE._meds = { key: k, v: v }; }
      return LIVE._meds.v;
    },
    medsOnDay: function (day) {
      var out = [];
      LIVE.medsGet().courses.forEach(function (c) { c.spans.forEach(function (s) { if (s.from <= day && (!s.to || day < s.to)) out.push({ drug: c.drug, dose: s.dose, unit: s.unit, route: s.route, freq: s.freq }); }); });
      return out;
    },
    medsLineHtml: function (day) {
      var M = LIVE.medsGet(); if (!M.courses.length || !day) return '';
      var on = LIVE.medsOnDay(day), esc = C.esc;
      return '<div class="sub2" style="margin:6px 0 10px">' + (on.length ? '当天在用：' + on.map(function (m) { return esc(m.drug + ' ' + m.dose + ' ' + m.unit + ' ' + m.route); }).join('；') : '当天没有在用的药') + '<span style="opacity:.7" data-ptds-ui="s37f43b584e99"> · 来自我录入的用药记录，只当背景</span></div>';
    },
    medsBandHtml: function (tps) {
      var esc = C.esc, M = LIVE.medsGet(), cs = M.courses.filter(function (c) { return c.spans.length; });
      var head = '<section class="box" id="med-band" style="margin-top:20px"><h3 data-ptds-inline><!--ptds-ui:s8809a5b61ced-->用药背景<!--/ptds-ui--><span class="grow"></span><span class="sub2" data-ptds-ui="s76b281dc78eb">来自我录入的用药记录 · 不参与计算</span></h3>';
      if (!cs.length) return head + '<div class="sub2" data-ptds-ui="s6fb1b25fd7ea">还没有用药记录。录入后，这里按日期画出每个药的用药区间、停药和重新用药。</div><div class="opts" style="margin-top:10px"><button class="btn2" id="med-go">' + C.ic('pencil') + '去录入用药</button></div></section>';
      var ds = (tps || []).slice(); cs.forEach(function (c) { c.spans.forEach(function (s) { ds.push(s.from); if (s.to) ds.push(s.to); }); });
      ds = ds.filter(Boolean).sort(); if (!ds.length) return ''; var d0 = ds[0], d1 = ds[ds.length - 1];
      var D = function (x) { return Date.UTC(+x.slice(0, 4), +x.slice(5, 7) - 1, +x.slice(8, 10)) / 864e5; }, n = Math.max(1, D(d1) - D(d0));
      var W = 1200, x0 = 170, x1 = W - 40, X = function (x) { return x0 + (D(x) - D(d0)) / n * (x1 - x0); }, rowH = 50, H = cs.length * rowH + 50;
      var every = Math.max(1, Math.ceil(n / 12)), svg = '<svg viewBox="0 0 ' + W + ' ' + H + '" style="width:100%;height:auto" role="img" aria-label="用药区间">';
      for (var i = 0; i <= n; i += every) { var dd = new Date((D(d0) + i) * 864e5).toISOString().slice(0, 10), xx = X(dd);
        svg += '<line x1="' + xx + '" y1="8" x2="' + xx + '" y2="' + (H - 30) + '" stroke="currentColor" stroke-opacity=".12"/><text x="' + xx + '" y="' + (H - 10) + '" text-anchor="middle" font-size="13" fill="currentColor" fill-opacity=".6">' + dd.slice(5) + '</text>'; }
      cs.forEach(function (c, ci) {
        var y = 20 + ci * rowH, col = LIVE.MED_COLORS[ci % LIVE.MED_COLORS.length];
        svg += '<text x="0" y="' + (y + 13) + '" font-size="14" fill="currentColor">' + esc(c.drug.length > 11 ? c.drug.slice(0, 10) + '…' : c.drug) + '</text>';
        c.spans.forEach(function (s, si) {
          var a = X(s.from), b = s.to ? X(s.to) : x1, w = Math.max(6, b - a);
          var tag = (s.kind === 'RESTART' ? '重新用药 · ' : '') + s.dose + ' ' + s.unit + (si === 0 ? ' · ' + s.route : '');
          svg += '<rect x="' + a + '" y="' + y + '" width="' + w + '" height="16" rx="8" fill="' + col + '" fill-opacity=".55"/>';
          if (w > 60) svg += '<text x="' + (a + 10) + '" y="' + (y + 13) + '" font-size="12" fill="#0b1226">' + esc(tag) + '</text>';
          if (s.end === 'STOP') svg += '<path d="M' + b + ' ' + (y - 4) + ' l0 24" stroke="' + col + '" stroke-width="2"/><text x="' + (b + 6) + '" y="' + (y - 6) + '" font-size="12" fill="' + col + '">停药</text>';
        });
      });
      return head + svg + '</svg><div class="sub2" style="margin-top:8px" data-ptds-ui="sc6f7a056a0c8">点某一天，来龙去脉浮窗里会写出当天在用的药。这里只当背景，不作原因判断。</div></section>';
    },
    /* ---------- 星炬 · 录入 · 批量（R20，产品负责人 2026-10-14：按渲染图 m1 m2 m3 做） ----------
       一次拖进很多文件：后台排队认、读、核对；保存永远要本人确认。化验单进现有的逐项确认页，其他按类型确认。 */
    BT_CSS: '.bt-list{display:grid;grid-template-columns:auto minmax(0,2.2fr) minmax(0,1.3fr) minmax(0,2fr) auto;gap:var(--primitive-space-2) var(--primitive-space-3);align-items:center}' +
      '.bt-list .h{color:var(--theme-text-tertiary);font-size:var(--scale-type-meta)}.bt-list .nm{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}' +
      '.bt-types{display:grid;grid-template-columns:minmax(0,2fr) auto minmax(0,1.6fr) minmax(0,1.4fr) auto;gap:var(--primitive-space-2) var(--primitive-space-4);align-items:center}' +
      '.bt-types .h{color:var(--theme-text-tertiary);font-size:var(--scale-type-meta)}.bt-num{font-variant-numeric:tabular-nums}' +
      '.bt-map{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.3fr) minmax(0,.8fr) minmax(0,1.6fr);gap:var(--primitive-space-2) var(--primitive-space-4);align-items:center}' +
      '.bt-map .h{color:var(--theme-text-tertiary);font-size:var(--scale-type-meta)}.bt-head{display:flex;gap:var(--primitive-space-2);align-items:center;flex-wrap:wrap}' +
      '.bt-head .grow{flex:1}.bt-samp{font-family:var(--font-mono,monospace);font-size:var(--scale-type-meta);white-space:pre-wrap;word-break:break-all}' +
      '@media (max-width:760px){.bt-list{grid-template-columns:auto minmax(0,1fr) auto}.bt-list .kd,.bt-list .h.kd{display:none}.bt-types{grid-template-columns:1fr auto}.bt-map{grid-template-columns:1fr 1fr}}',
    btCss: function () { if (!document.getElementById('bt-css')) { var s = document.createElement('style'); s.id = 'bt-css'; s.textContent = LIVE.BT_CSS; document.head.appendChild(s); } },
    btGet: function () { try { return readCached('/api/batch/list?key=' + encodeURIComponent(C.st.key)); } catch (err) { if(err&&(err.viewPending||err.code==='VIEW_CHANGED'))throw err; return { items: [], checks: [], paused: false, error: err.code }; } },
    BT_BUSY: { queued: 1, working: 1, saving: 1 },
    btStatus: function (it) {
      var esc = C.esc, ic = C.ic;
      var S = {
        queued: '排队中', working: it.progress || '识别中', saving: it.progress || '保存中', mapping: '要你确认一次各列是什么',
        ready: it.kind === 'lab_image' || it.kind === 'lab_pdf' ? '待确认 ' + (it.rows || 0) + ' 项' + (it.lab_pages > 1 ? '（' + it.lab_pages + ' 页）' : '') : '待确认 ' + (it.types || 0) + ' 类',
        saved: '已保存' + (it.saved_rows ? ' ' + it.saved_rows + ' 项' : ''), skipped: it.note || '不入库', notlab: '这类文件不做逐项识别',
        failed: it.note || '没读成', duplicate: '重复'
      }[it.status] || it.status;
      if (it.status === 'saved') return '<span class="badge">' + ic('check') + esc(S) + '</span>';
      if (it.status === 'duplicate') return '<span class="tag" data-ptds-ui="s609cf2fdf6ff">重复</span> <span class="sub2">' + esc(it.note) + '</span>';
      if (it.status === 'skipped' || it.status === 'notlab') return '<span class="sub2">' + esc(S) + '</span>';
      if (it.status === 'failed') return '<span class="tip">' + ic('circle-alert') + ' ' + esc(S) + '</span>';
      return '<span class="tag">' + esc(S) + '</span>' + (it.dup_of && it.status === 'ready' ? ' <span class="sub2" data-ptds-inline><!--ptds-ui:se16d62fe4d32-->可能和“<!--/ptds-ui-->' + esc(it.dup_name) + '”是同一份</span>' : '');
    },
    btIcon: function (kind) { return { lab_image: 'file-image', lab_pdf: 'file-text', apple_health: 'database', withings: 'file-spreadsheet', cgm: 'file-spreadsheet' }[kind] || (/^table/.test(kind) ? 'file-spreadsheet' : 'file-text'); },
    /* 一个文件夹里的 Withings 表格合成一行；不入库的同类文件（运动轨迹……）合成一行 */
    btRows: function (items) {
      var out = [], groups = {};
      items.forEach(function (it) {
        var gk = null;
        if (it.group && (it.kind === 'withings' || (it.kind === 'skip' && /^Withings/.test(it.label)))) gk = 'W|' + it.group;
        else if (it.status === 'skipped' && it.kind === 'skip') gk = 'S|' + it.label;
        if (!gk) { out.push({ one: it }); return; }
        if (!groups[gk]) { groups[gk] = { key: gk, items: [] }; out.push(groups[gk]); }
        groups[gk].items.push(it);
      });
      return out.map(function (r) { return r.one ? r : (r.items.length === 1 ? { one: r.items[0] } : r); });
    },
    renderBatch: function () {
      var esc = C.esc, ic = C.ic, st = C.st, e = st.entry, v = document.getElementById('view');
      LIVE.btCss();
      if (st.btOpen) return LIVE.renderBatchOpen();
      var B = st.btData = LIVE.btGet(), items = B.items || [];
      var head = '<section class="panel" data-cmp="T13" style="display:grid;gap:var(--primitive-space-4)">' + C.stepsHtml('fill') + C.modeSwitch(e);
      var drop = '<div class="drop" id="bt-drop">' + ic('inbox') + '<div data-ptds-ui="s733d74ba9e1a">把一批文件或整个文件夹拖进来：化验单图片、PDF，苹果健康导出，Withings、血糖仪导出的表格，CSV、Excel 都可以</div>' +
        '<div class="opts"><button class="btn" data-sem="SEM-14" id="bt-pick" data-ptds-ui="s822fb37dba29">选择文件</button><button class="btn2" id="bt-pickdir" data-ptds-ui="s0d6fad8138e7">选择文件夹</button></div></div>' +
        '<input type="file" id="bt-file" multiple hidden><input type="file" id="bt-dir" webkitdirectory multiple hidden>';
      var privacy = '<div class="sub2">' + ic('lock') + ' 在这台电脑上处理，不联网；关掉 PTDS 再打开，会从没做完的那份接着做。认出来的数据都要你确认后才保存。</div>';
      if (!items.length && !st.btUp) { v.innerHTML = head + drop + privacy + '</section>'; LIVE.bindBatch(); return; }
      var cnt = function (f) { return items.filter(f).length; };
      var chips = [['已保存', cnt(function (i) { return i.status === 'saved'; })], ['待确认', cnt(function (i) { return i.status === 'ready' || i.status === 'mapping'; })],
        ['识别中 · 排队', cnt(function (i) { return LIVE.BT_BUSY[i.status]; })], ['重复', cnt(function (i) { return i.status === 'duplicate'; })],
        ['不入库', cnt(function (i) { return i.status === 'skipped' || i.status === 'notlab'; })], ['没读成', cnt(function (i) { return i.status === 'failed'; })]]
        .filter(function (c) { return c[1]; }).map(function (c) { return '<span class="tag">' + c[0] + ' ' + c[1] + '</span>'; }).join('');
      var bar = '<div class="bt-head"><b data-ptds-inline><!--ptds-ui:s76e547a8fa54-->共 <!--/ptds-ui-->' + items.length + ' 份</b>' + chips + (st.btUp ? '<span class="tag">' + ic('clock') + ' 正在放进队列 ' + st.btUp.done + ' / ' + st.btUp.total + '</span>' : '') +
        '<span class="grow"></span><button class="chip" id="bt-pause">' + (B.paused ? ic('refresh-cw') + '接着做' : ic('clock') + '暂停') + '</button><button class="chip" id="bt-more">' + ic('plus') + '再加文件</button></div>' +
        (B.paused ? '<div class="tip">' + ic('info') + ' 已暂停：正在读的那一页读完就停，点“接着做”继续。</div>' : '');
      var rows = LIVE.btRows(items).map(function (r) {
        if (r.one) {
          var it = r.one, act = '';
          if (it.status === 'ready') act = '<button class="chip" data-bt-open="' + esc(it.id) + '">去确认</button>';
          else if (it.status === 'mapping') act = '<button class="chip" data-bt-open="' + esc(it.id) + '">去确认</button>';
          else if (it.status === 'saved') act = '<button class="chip" data-bt-open="' + esc(it.id) + '">回执</button>'; /* 存好了的：一律"回执"（存了什么、跳过了什么） */
          else if (it.status === 'notlab') act = '<button class="chip" data-bt-open="' + esc(it.id) + '">看看</button>'; /* 没存东西的图片：只能看原图 */
          else if (it.status === 'failed') act = '<button class="chip" data-bt-retry="' + esc(it.id) + '">再试一次</button>';
          var pages = it.kind === 'lab_pdf' && it.pages ? '（' + it.pages + ' 页）' : '';
          return '<span>' + ic(LIVE.btIcon(it.kind)) + '</span><span class="nm" title="' + esc(it.rel || it.name) + '">' + esc(it.name) + pages + '</span><span class="kd sub2">' + esc(it.label || '') + '</span><span>' + LIVE.btStatus(it) + '</span><span>' + act + '</span>';
        }
        var its = r.items, first = its[0], wi = its.filter(function (i) { return i.kind === 'withings'; });
        if (r.key.indexOf('W|') === 0) {
          var ready = wi.filter(function (i) { return i.status === 'ready'; }), busy = wi.filter(function (i) { return LIVE.BT_BUSY[i.status]; }), saved = wi.filter(function (i) { return i.status === 'saved'; });
          var types = wi.reduce(function (a, i) { return a + (i.types || 0); }, 0);
          var stx = busy.length ? '<span class="tag">' + (busy.some(function (i) { return i.status !== 'queued'; }) ? '读取中' : '排队中') + '</span>' : ready.length ? '<span class="tag" data-ptds-inline><!--ptds-ui:sa8b0bd9c65f7-->待确认 <!--/ptds-ui-->' + ready.reduce(function (a, i) { return a + (i.types || 0); }, 0) + ' 类</span>' : saved.length ? '<span class="badge">' + ic('check') + '已保存</span>' : '<span class="sub2" data-ptds-ui="sbd7e30b7662f">不入库</span>';
          return '<span>' + ic('file-spreadsheet') + '</span><span class="nm" data-ptds-inline><!--ptds-ui:s793448e03702-->Withings 导出（<!--/ptds-ui-->' + its.length + ' 个表格）</span><span class="kd sub2">Withings · ' + types + ' 类</span><span>' + stx + '</span><span>' + (ready.length ? '<button class="chip" data-bt-group="' + esc(r.key) + '">去确认</button>' : '') + '</span>';
        }
        return '<span>' + ic(first.kind === 'skip' && /轨迹/.test(first.label) ? 'map' : 'file-text') + '</span><span class="nm">' + esc(first.label) + ' ×' + its.length + '</span><span class="kd sub2">' + esc(first.label) + '</span><span class="sub2">' + esc(first.note || '不入库') + '</span><span></span>';
      }).join('');
      var ck = B.checks || [], same = ck.filter(function (c) { return c.state === 'same'; }), conf = ck.filter(function (c) { return c.state === 'conflict'; });
      var pick = st.btPick = st.btPick || {};
      var checks = ck.length ? '<details class="more"' + (st.btChecksOpen ? ' open' : '') + ' id="bt-checks"><summary data-ptds-inline><!--ptds-ui:sa670167d794a-->核对：<!--/ptds-ui-->' + (same.length ? same.length + ' 项和已有记录一样，不会再存' : '') + (same.length && conf.length ? '；' : '') + (conf.length ? conf.length + ' 项和已有记录不一样，要你选' : '') + '</summary>' +
        ck.map(function (c) {
          var lab = (C.FULL[c.code] || {}).zh || c.code, k = c.item + ':' + c.page + ':' + c.code;
          if (c.state === 'same') return '<div class="sub2">' + esc(lab) + ' · ' + esc(c.date) + ' 采样：“' + esc(c.name) + '”读出 ' + esc(c.new + ' ' + c.unit) + '，星炬里已有 ' + esc(c.old + ' ' + c.old_unit) + '（' + esc(c.old_src) + '）→ 只留一份</div>';
          return '<div class="bt-head sub2">' + esc(lab) + ' · ' + esc(c.date) + ' 采样：“' + esc(c.name) + '”读出 ' + esc(c.new + ' ' + c.unit) + '，星炬里已有 ' + esc(c.old + ' ' + c.old_unit) + '（' + esc(c.old_src) + '）→ ' +
            '<button class="chip" data-bt-pick="' + esc(k) + '" data-v="use" aria-pressed="' + (pick[k] === 'use') + '">也存这次的 ' + esc(c.new) + '</button><button class="chip" data-bt-pick="' + esc(k) + '" data-v="drop" aria-pressed="' + (pick[k] === 'drop') + '">只留原来的 ' + esc(c.old) + '</button>' +
            '<button class="chip" data-bt-open="' + esc(c.item) + '" data-page="' + c.page + '">看原图</button></div>';
        }).join('') + '</details>' : '';
      v.innerHTML = head + bar + '<div class="bt-list" role="table" aria-label="批量文件" data-ptds-ui-aria-label="s3d4d0350521b"><span></span><span class="h" data-ptds-ui="s39932f24fe11">文件</span><span class="h kd" data-ptds-ui="sef18f708398b">认成</span><span class="h" data-ptds-ui="sf81ff55de14e">进度</span><span></span>' + rows + '</div>' + checks + privacy +
        '<input type="file" id="bt-file" multiple hidden><input type="file" id="bt-dir" webkitdirectory multiple hidden></section>';
      LIVE.bindBatch();
      if (items.some(function (i) { return LIVE.BT_BUSY[i.status]; }) || st.btUp) LIVE.btPoll();
    },
    btPoll: function () {
      clearTimeout(LIVE._batchTimer);
      LIVE._batchTimer = setTimeout(function () { var e = C.st.entry; if (C.st.tview === 'entry' && e && e.method === 'batch' && !C.st.btOpen && e.step === 'fill') LIVE.renderBatch(); }, 2000);
    },
    btUpload: function (files) {
      var st = C.st, list = [];
      for (var i = 0; i < files.length; i++) if (!/^\./.test(files[i].name)) list.push(files[i]);
      if (!list.length) return;
      st.btUp = { done: 0, total: list.length };
      var one = function (k) {
        if (k >= list.length) { st.btUp = null; LIVE.renderBatch(); return; }
        var f = list[k];
        fetch('/api/batch/add?key=' + encodeURIComponent(st.key), { method: 'POST', body: f,
          headers: { 'X-PTDS': '1', 'Content-Type': 'application/octet-stream', 'X-File-Name': encodeURIComponent(f.name), 'X-File-Rel': encodeURIComponent(f.webkitRelativePath || f.name) } })
          .then(function (r) { return r.json(); }, function () { return { error: 'SERVER_DOWN' }; })
          .then(function (j) { if (j.error) C.toast('“' + f.name + '”没放进队列（' + j.error + '）'); st.btUp.done = k + 1; if (k % 5 === 0) LIVE.renderBatch(); one(k + 1); });
      };
      one(0);
    },
    bindBatch: function () {
      var st = C.st, e = st.entry, g = function (id, fn) { var el = document.getElementById(id); if (el) el.onclick = LIVE.action(fn); };
      document.querySelectorAll('[data-method]').forEach(function (b) { b.onclick = function () { e.method = b.dataset.method; C.render(); }; });
      var fi = document.getElementById('bt-file'), fd = document.getElementById('bt-dir');
      if (fi) fi.onchange = function () { LIVE.btUpload(fi.files); };
      if (fd) fd.onchange = function () { LIVE.btUpload(fd.files); };
      g('bt-pick', function () { fi.click(); }); g('bt-pickdir', function () { fd.click(); }); g('bt-more', function () { fi.click(); });
      var dz = document.getElementById('bt-drop') || document.getElementById('view');
      dz.ondragover = function (ev) { ev.preventDefault(); };
      dz.ondrop = function (ev) {
        ev.preventDefault(); var dt = ev.dataTransfer, out = [], pending = 0, done = function () { if (!pending) LIVE.btUpload(out); };
        var walk = function (entry, path) {  /* 拖进来的是文件夹：一层层展开，保留相对路径（同一个导出包合成一行） */
          if (entry.isFile) { pending++; entry.file(function (f) { try { Object.defineProperty(f, 'webkitRelativePath', { value: path + f.name }); } catch (x) { if(x&&(x.viewPending||x.code==='VIEW_CHANGED'))throw x; /* 只读就算了 */ } out.push(f); pending--; done(); }, function () { pending--; done(); }); }
          else if (entry.isDirectory) { var rd = entry.createReader(), more = function () { pending++; rd.readEntries(function (es) { pending--; es.forEach(function (x) { walk(x, path + entry.name + '/'); }); if (es.length) more(); else done(); }, function () { pending--; done(); }); }; more(); }
        };
        var its = dt.items && dt.items.length && dt.items[0].webkitGetAsEntry ? Array.prototype.map.call(dt.items, function (x) { return x.webkitGetAsEntry(); }) : null;
        if (its) { its.forEach(function (x) { if (x) walk(x, ''); }); done(); } else LIVE.btUpload(dt.files);
      };
      g('bt-pause', LIVE.action(async function () { try { (await call('POST', '/api/batch/pause', { key: st.key, on: !(st.btData || {}).paused })); } catch (err) { if(err&&(err.viewPending||err.code==='VIEW_CHANGED'))throw err; C.toast('没改成：' + (err.detail || err.code)); } LIVE.renderBatch(); }));
      var ckd = document.getElementById('bt-checks'); if (ckd) ckd.ontoggle = function () { st.btChecksOpen = ckd.open; };
      document.querySelectorAll('[data-bt-open]').forEach(function (b) { b.onclick = function () { st.btOpen = { id: b.dataset.btOpen, page: b.dataset.page ? +b.dataset.page : null }; LIVE.renderBatch(); window.scrollTo(0, 0); }; });
      document.querySelectorAll('[data-bt-group]').forEach(function (b) { b.onclick = function () { st.btOpen = { group: b.dataset.btGroup }; LIVE.renderBatch(); window.scrollTo(0, 0); }; });
      document.querySelectorAll('[data-bt-retry]').forEach(function (b) { b.onclick = LIVE.action(async function () { try { (await call('POST', '/api/batch/retry', { key: st.key, id: b.dataset.btRetry })); } catch (err) { if(err&&(err.viewPending||err.code==='VIEW_CHANGED'))throw err; C.toast(err.detail || err.code); } LIVE.renderBatch(); }); });
      document.querySelectorAll('[data-bt-pick]').forEach(function (b) { b.onclick = function () { st.btPick[b.dataset.btPick] = b.dataset.v; st.btChecksOpen = true; LIVE.renderBatch(); }; });
    },
    btBack: function () { C.st.btOpen = null; LIVE.renderBatch(); window.scrollTo(0, 0); },
    renderBatchOpen: async function () {
      var st = C.st, o = st.btOpen, d;
      if (o.group) return LIVE.renderBatchTypes(null, o.group);
      try { d = readCached('/api/batch/item?key=' + encodeURIComponent(st.key) + '&id=' + encodeURIComponent(o.id)); } catch (err) { if(err&&(err.viewPending||err.code==='VIEW_CHANGED'))throw err; st.btOpen = null; C.toast('找不到这份文件'); return LIVE.renderBatch(); }
      var it = d.item;
      if (it.kind === 'lab_image' || it.kind === 'lab_pdf') {
        var lab = (d.result.pages || []).filter(function (p) { return p.kind === 'lab' && p.rows; });
        var page = o.page || (lab.length === 1 ? lab[0].page : null);
        if (page && it.status === 'ready') return (await LIVE.btOpenPage(it, page));
        return LIVE.renderBatchPages(it, d.result);
      }
      if (it.status === 'mapping') return LIVE.renderBatchMap(it, d.result);
      return LIVE.renderBatchTypes(it, null, d.result);
    },
    /* 化验单：打开现有的逐项确认页；和星炬已有记录一样的不再列出来，不一样的标出来、要逐项点确认 */
    btOpenPage: async function (it, page) {
      var st = C.st, r, request=st._btPageRequest=(st._btPageRequest||0)+1;
      try { r = (await call('GET', '/api/batch/page?key=' + encodeURIComponent(st.key) + '&id=' + encodeURIComponent(it.id) + '&page=' + page)); } catch (err) { if(err&&(err.viewPending||err.code==='VIEW_CHANGED'))throw err; C.toast('打不开这一页：' + (err.detail || err.code)); st.btOpen = null; return LIVE.renderBatch(); }
      if(request!==st._btPageRequest)return;
      var pick = st.btPick || {}, keep = [], conflicts = [];
      r.rows.forEach(function (row, i) {
        var c = (r.checks || [])[i] || { state: 'new' }, k = it.id + ':' + page + ':' + row.code, lab = (C.FULL[row.code] || {}).zh || row.code;
        if (c.state === 'same') { r.unmatched.push('和星炬里已有的一样（' + c.old_src + '），不再存：' + lab + '　' + c.new + '　' + c.unit); return; }
        if (c.state === 'conflict') {
          if (pick[k] === 'drop') { r.unmatched.push('你选了只留原来的：' + lab + '　' + c.new + '　' + c.unit); return; }
          if (pick[k] !== 'use') row.flag = 'CONFLICT';
          conflicts.push(lab + '：这次读出 ' + c.new + ' ' + c.unit + '，星炬里同一天已有 ' + c.old + ' ' + c.old_unit + '（' + c.old_src + '）');
        }
        keep.push(row);
      });
      r.rows = keep; r.conflicts = conflicts;
      var e = C.newEntry(); e.method = 'ocr'; e.ocr = r; e.osel = 0; e.date = r.date; e.time = r.time; e.nature = r.nature; e.batch = { id: it.id, page: page };
      st.entry = e; st.btOpen = null; C.render(); window.scrollTo(0, 0);
    },
    renderBatchPages: function (it, res) {
      var esc = C.esc, ic = C.ic, v = document.getElementById('view'), pages = res.pages || [];
      var original = {name:it.name, original:it.sha.slice(0, 16) + (it.kind === 'lab_pdf' ? '.pdf' : (it.name.match(/\.[a-zA-Z]+$/) || [''])[0].toLowerCase())};
      var KZ = { lab: '化验单', gene: '基因报告', record: '病历正文', prose: '成段文字' };
      v.innerHTML = '<section class="panel" style="display:grid;gap:var(--primitive-space-4)">' + C.stepsHtml('fill') + C.modeSwitch(C.st.entry) +
        '<div class="bt-head"><span>' + ic(LIVE.btIcon(it.kind)) + ' <b>' + esc(it.name) + '</b>' + (res.total > 1 ? ' · ' + res.total + ' 页' : '') + '</span><span class="grow"></span><button class="ibtn" id="bt-back" aria-label="回到批量列表" title="回到批量列表" data-ptds-ui-aria-label="sfa4c3519715a" data-ptds-ui-title="sfa4c3519715a">' + ic('x') + '</button></div>' +
        (it.status === 'notlab' ? '<div class="box"><h3>' + ic('info') + ' 这份文件不做逐项识别</h3><div>' + esc(it.note) + '</div><div class="sub2" data-ptds-ui="s7fec42c1c4b5">程序按规则判断，没有用模型</div></div>' : '') +
        '<div class="original-compare">' + LIVE.originalHtml(original) + '<div class="original-fields"><h3 data-ptds-ui="s71fb8ae998dc">识别结果</h3><div class="bt-list"><span></span><span class="h" data-ptds-ui="sd24d3c99460c">页</span><span class="h kd" data-ptds-ui="s96d005802fb5">程序判断</span><span class="h" data-ptds-ui="sf81ff55de14e">进度</span><span></span>' + pages.map(function (p) {
          var ok = p.kind === 'lab' && p.rows;
          return '<span>' + ic('file-text') + '</span><span>第 ' + p.page + ' 页' + (p.date ? ' · ' + esc(p.date) : '') + '</span><span class="kd sub2">' + (KZ[p.kind] || p.kind) + '</span><span>' +
            (p.saved ? '<span class="badge">' + ic('check') + '已保存</span>' : ok ? '<span class="tag" data-ptds-inline><!--ptds-ui:sa8b0bd9c65f7-->待确认 <!--/ptds-ui-->' + p.rows + ' 项</span>' : '<span class="sub2" data-ptds-ui="s96cadb535c64">不做逐项识别</span>') + '</span><span>' +
            (ok && !p.saved && it.status === 'ready' ? '<button class="chip" data-bt-page="' + p.page + '">去确认</button>' : '') + '</span>';
        }).join('') + '</div></div></div>' +
        '<div><a class="chip" href="/api/torch/original?key=' + encodeURIComponent(C.st.key) + '&name=' + encodeURIComponent(it.sha.slice(0, 16) + (it.kind === 'lab_pdf' ? '.pdf' : (it.name.match(/\.[a-zA-Z]+$/) || [''])[0].toLowerCase())) + '" target="_blank" rel="noopener">' + ic('file-image') + ' 查看原件（保存在这台电脑上）</a></div></section>';
      LIVE.bindOriginal(v);
      document.getElementById('bt-back').onclick = LIVE.btBack;
      document.querySelectorAll('[data-method]').forEach(function (b) { b.onclick = function () { C.st.btOpen = null; C.st.entry.method = b.dataset.method; C.render(); }; });
      document.querySelectorAll('[data-bt-page]').forEach(function (b) { b.onclick = LIVE.action(async function () { (await LIVE.btOpenPage(it, +b.dataset.btPage)); }); });
    },
    /* 按类型确认（m2）：每类看条数、时间段、来源和抽样原文，确认后这一类全部保存 */
    renderBatchTypes: function (it, group, res) {
      var esc = C.esc, ic = C.ic, st = C.st, v = document.getElementById('view');
      var entries = [];  /* [{item, type}] */
      var notIn = [], overlap = [], title, items = [];
      if (group) {
        items = ((st.btData || LIVE.btGet()).items || []).filter(function (i) { return 'W|' + i.group === group && i.kind === 'withings' && (i.status === 'ready' || i.status === 'saved'); });
        items.forEach(function (i) { var d = readCached('/api/batch/item?key=' + encodeURIComponent(st.key) + '&id=' + encodeURIComponent(i.id)); (d.result.types || []).forEach(function (t) { entries.push({ item: d.item, type: t }); }); });
        title = 'Withings 导出（' + group.slice(2) + '）';
      } else {
        items = [it];
        (res.types || []).forEach(function (t) { entries.push({ item: it, type: t }); });
        notIn = res.not_imported || []; if (res.overlap) overlap.push(res.overlap);
        if (res.source_kind === 'APPLE_HEALTH') overlap.push('重新导出不会删除旧记录：在“健康”App 里删掉或改过的数，旧值仍留在星炬里'); /* 产品负责人 2026-10-14 08:11Z 选“维持现状” */
        title = it.name;
      }
      var dec = st.btDec = st.btDec && st.btDec._for === (group || it.id) ? st.btDec : { _for: group || it.id }, conf = st.btConf = st.btConf || {};
      var k = function (x) { return x.item.id + '|' + x.type.key; };
      var savedOf = function (x) { return (x.item.saved || {})[x.type.key]; };
      var pend = entries.filter(function (x) { return !savedOf(x) && dec[k(x)] === undefined; }).length;
      var anyYes = entries.some(function (x) { return !savedOf(x) && dec[k(x)] === true; });
      var busy = items.some(function (i) { return i.status === 'saving'; });
      var range = function (t) { return t.first ? esc(String(t.first).slice(0, 10)) + ' → ' + esc(String(t.last).slice(0, 10)) : '—'; };
      var srcs = function (t) { return esc(Object.keys(t.sources || {}).sort(function (a, b) { return t.sources[b] - t.sources[a]; }).slice(0, 3).join('、')); };
      var rel = function (t, x) {
        var c = t.check || {}, out = [];
        if (t.mode && t.mode.indexOf('series') === 0) out.push('原始明细存进本机明细库，正式库每天存一条汇总' + (c.series_have ? '；明细库里已有 ' + c.series_have + ' 条，同样的不会重复存' : ''));
        if (c.same) out.push(c.same + ' 条和星炬里已有的一样，不再存');
        if (c.internal) out.push(c.internal + ' 条在文件里同一时刻有两个不同的数，都不存');
        if (t.bad) out.push(t.bad + ' 行读不懂，不存');
        if (t.note) out.push(t.note);
        var h = out.length ? '<div class="sub2">' + out.map(esc).join('；') + '</div>' : '';
        if (c.conflict) {
          var ck = k(x), cv = conf[ck] || 'keep';
          h += '<details class="more"><summary>' + c.conflict + ' 条和星炬里已有的不一样，要你选</summary><div class="sub2">' + (c.conflicts || []).map(function (y) { return esc(String(y.when).slice(0, 16).replace('T', ' ') + '：这次 ' + y.new + ' ' + y.unit + '，原来 ' + y.old + ' ' + y.old_unit + '（' + y.old_src + '）'); }).join('<br>') + (c.conflict > 20 ? '<br>……' : '') + '</div>' +
            '<div class="opts"><button class="chip" data-bt-conf="' + esc(ck) + '" data-v="keep" aria-pressed="' + (cv === 'keep') + '">留原来的</button><button class="chip" data-bt-conf="' + esc(ck) + '" data-v="new" aria-pressed="' + (cv === 'new') + '">用这份文件的（原来的留作旧版本）</button></div></details>';
        }
        return h;
      };
      var rows = entries.map(function (x) {
        var t = x.type, s = savedOf(x), d = dec[k(x)], kk = esc(k(x));
        var act = s ? '<span class="badge">' + ic('check') + '已保存 ' + (s.saved || 0) + ' 条</span>' :
          d === true ? '<button class="chip" data-bt-dec="' + kk + '" data-v="">' + ic('check') + '已确认</button>' :
          d === false ? '<button class="chip" data-bt-dec="' + kk + '" data-v="">不存</button>' :
          '<span class="tag" data-ptds-ui="sa8b0bd9c65f7">待确认</span><button class="ibtn" data-bt-dec="' + kk + '" data-v="1" aria-label="确认' + esc(t.label) + '" title="确认">' + ic('check') + '</button><button class="ibtn" data-bt-dec="' + kk + '" data-v="0" aria-label="不存' + esc(t.label) + '" title="不存这一类">' + ic('x') + '</button>';
        return '<span><b>' + esc(t.label) + '</b> ' + (t.samples && t.samples.length ? '<details class="more inl"><summary data-ptds-inline><!--ptds-ui:sf4ddd25eec31-->抽样 <!--/ptds-ui-->' + t.samples.length + ' 条原文</summary><div class="bt-samp">' + t.samples.map(esc).join('\n') + '</div></details>' : '') + rel(t, x) + '</span>' +
          '<span class="bt-num">' + Number(t.count).toLocaleString('en-US') + '</span><span class="sub2">' + range(t) + '</span><span class="sub2">' + srcs(t) + '</span><span>' + act + '</span>';
      }).join('');
      v.innerHTML = '<section class="panel" style="display:grid;gap:var(--primitive-space-4)">' + C.stepsHtml('fill') + C.modeSwitch(st.entry) +
        '<div class="bt-head"><span>' + ic('database') + ' <b>' + esc(title) + '</b> · 认出 ' + entries.length + ' 类' + (notIn.length ? '，还有 ' + notIn.length + ' 类不入库' : '') + '</span><span class="grow"></span><button class="ibtn" id="bt-back" aria-label="回到批量列表" title="回到批量列表" data-ptds-ui-aria-label="sfa4c3519715a" data-ptds-ui-title="sfa4c3519715a">' + ic('x') + '</button></div>' +
        '<div class="sub2" data-ptds-ui="s32eb72b1fbe2">这类文件条数太多，按类型确认：每类看条数、时间段和抽样原文，确认后这一类全部保存，每条都记着它在原文件里的位置。</div>' +
        (busy ? '<div class="tip">' + ic('clock') + ' 正在保存……</div>' : '') +
        '<div class="bt-types" role="table"><span class="h" data-ptds-ui="sba40014ff496">类型</span><span class="h" data-ptds-ui="se18aa10c4faf">条数</span><span class="h" data-ptds-ui="s9af291a643f8">时间段</span><span class="h" data-ptds-ui="s9b6a4a82e39d">来自</span><span class="h" data-ptds-ui="s36f33adaf094">确认</span>' + rows + '</div>' +
        (notIn.length ? '<details class="more"><summary data-ptds-inline><!--ptds-ui:s83eec76b3911-->还有 <!--/ptds-ui-->' + notIn.length + ' 类不入库（字典里没有）</summary><div class="sub2">' + notIn.map(function (n) { return esc(n.label) + (n.count ? ' ' + Number(n.count).toLocaleString('en-US') + ' 条' : ''); }).join('、') + '</div></details>' : '') +
        (overlap.length ? '<div class="sub2">' + ic('info') + ' 和已有数据的关系：' + overlap.map(esc).join('；') + '</div>' : '') +
        '<div class="foot">' + (pend ? '<span class="tip" data-ptds-inline><!--ptds-ui:s83eec76b3911-->还有 <!--/ptds-ui-->' + pend + ' 类待确认</span><button class="chip" id="bt-all" data-ptds-ui="s55ad9574a7ff">全部确认</button>' : '') + '<button class="btn" data-sem="SEM-14" id="bt-save"' + (anyYes && !busy ? '' : ' disabled aria-disabled="true"') + '>保存</button></div></section>';
      document.getElementById('bt-back').onclick = LIVE.btBack;
      document.querySelectorAll('[data-method]').forEach(function (b) { b.onclick = function () { st.btOpen = null; st.entry.method = b.dataset.method; C.render(); }; });
      document.querySelectorAll('[data-bt-dec]').forEach(function (b) { b.onclick = function () { var vv = b.dataset.v; if (vv === '') delete dec[b.dataset.btDec]; else dec[b.dataset.btDec] = vv === '1'; LIVE.renderBatchOpen(); }; });
      document.querySelectorAll('[data-bt-conf]').forEach(function (b) { b.onclick = function () { conf[b.dataset.btConf] = b.dataset.v; LIVE.renderBatchOpen(); }; });
      var all = document.getElementById('bt-all'); if (all) all.onclick = function () { entries.forEach(function (x) { if (!savedOf(x) && dec[k(x)] === undefined) dec[k(x)] = true; }); LIVE.renderBatchOpen(); };
      document.getElementById('bt-save').onclick = LIVE.action(async function () {
        var by = {}, instanceKey=st.key;
        entries.forEach(function (x) { if (savedOf(x) || dec[k(x)] === undefined) return; var b = by[x.item.id] = by[x.item.id] || { decisions: {}, conflicts: {} }; b.decisions[x.type.key] = dec[k(x)]; b.conflicts[x.type.key] = conf[k(x)] || 'keep'; });
        var n = 0;
        for (const id of Object.keys(by)) { if (!Object.keys(by[id].decisions).some(function (t) { return by[id].decisions[t]; })) continue;
          try { (await call('POST', '/api/batch/confirm', { key: instanceKey, id: id, decisions: by[id].decisions, conflicts: by[id].conflicts })); n++; } catch (err) { if(err&&(err.viewPending||err.code==='VIEW_CHANGED'))throw err; C.toast('尚未确认全部保存，请回到列表核对：' + (err.detail || err.code));return; } };
        if (n) { C.toast('在后台保存，可以先去看别的文件'); st.btDec = null; LIVE.btBack(); }
      });
      if (busy) setTimeout(function () { if (C.st.btOpen && (C.st.btOpen.id === (it && it.id) || C.st.btOpen.group === group)) LIVE.renderBatchOpen(); }, 2000);
    },
    /* 新格式的表格（m3）：本机千问只看了列名和每列的样子，猜了每一列是什么；本人确认一次，存成模板 */
    renderBatchMap: function (it, res) {
      var esc = C.esc, ic = C.ic, st = C.st, v = document.getElementById('view');
      var targets = LIVE.btTargets = LIVE.btTargets || null, cols = st.btMap && st.btMap._for === it.id ? st.btMap.cols : (st.btMap = { _for: it.id, cols: res.columns.map(function (c) { return { target: c.target, unit: c.unit }; }) }).cols;
      var opts = [['time', '采样时间'], ['date', '日期（只有日期）'], ['skip', '不导入这一列'], ['series:CGM_GLUCOSE', '连续血糖（CGM）']].concat(Object.keys(C.FULL).filter(function (c) { return C.FULL[c].type === 'DECIMAL'; }).map(function (c) { return [c, C.FULL[c].zh]; }));
      var unitsOf = function (t) { return t === 'series:CGM_GLUCOSE' ? ['mmol/L', 'mg/dL'] : (C.FULL[t] ? C.FULL[t].units.map(function (u) { return u.lit; }) : []); };
      var rows = res.columns.map(function (c, i) {
        var cur = cols[i], us = unitsOf(cur.target);
        if (us.length && us.indexOf(cur.unit) < 0) cur.unit = us[0];
        return '<span>' + esc(c.name) + ' <span class="sub2">' + esc(c.shape) + '</span></span>' +
          '<select class="sel" data-bt-col="' + i + '" aria-label="' + esc(c.name) + '是什么">' + opts.map(function (o) { return '<option value="' + esc(o[0]) + '"' + (o[0] === cur.target ? ' selected' : '') + '>' + esc(o[1]) + '</option>'; }).join('') + '</select>' +
          (us.length ? '<select class="sel" data-bt-unit="' + i + '" aria-label="单位">' + us.map(function (u) { return '<option' + (u === cur.unit ? ' selected' : '') + '>' + esc(u) + '</option>'; }).join('') + '</select>' : '<span class="sub2">—</span>') +
          '<span class="sub2">' + (res.examples[i] || []).map(esc).join(' · ') + '</span>';
      }).join('');
      var guessed = res.columns.filter(function (c, i) { return c.unit_from === '字典默认' && cols[i].target !== 'skip' && cols[i].target !== 'time' && cols[i].target !== 'date'; });
      var hasT = cols.some(function (c) { return c.target === 'time' || c.target === 'date'; }), hasV = cols.some(function (c) { return ['time', 'date', 'skip'].indexOf(c.target) < 0; });
      v.innerHTML = '<section class="panel" style="display:grid;gap:var(--primitive-space-4)">' + C.stepsHtml('fill') + C.modeSwitch(st.entry) +
        '<div class="bt-head"><span>' + ic('file-spreadsheet') + ' <b>' + esc(it.name) + '</b>' + (res.rows != null ? ' · ' + Number(res.rows).toLocaleString('en-US') + ' 行' : '') + ' · 这个格式第一次见</span><span class="grow"></span><button class="ibtn" id="bt-back" aria-label="回到批量列表" title="回到批量列表" data-ptds-ui-aria-label="sfa4c3519715a" data-ptds-ui-title="sfa4c3519715a">' + ic('x') + '</button></div>' +
        '<div class="sub2">' + (/^星灵/.test(res.by) ? esc(res.by) + '：' : '') + '本机千问只看了列名、每列是数字还是时间，没看数值，猜了每一列是什么；你确认一次，以后同样的表直接用。' + (/^星灵/.test(res.by) ? '' : '<br>' + esc(res.by) + '：这次是程序按名称对的。') + '</div>' +
        '<div class="bt-map"><span class="h" data-ptds-ui="s112bb58c61a2">表里的列</span><span class="h" data-ptds-ui="sd7cbc446a659">是什么</span><span class="h" data-ptds-ui="s80b19d68b149">单位</span><span class="h" data-ptds-ui="s3cc5449ef467">前 3 行原文</span>' + rows + '</div>' +
        '<div class="sub2">' + ic('info') + ' 没写时区的时间按 ' + esc(res.tz) + ' 算' + (guessed.length ? '；' + guessed.map(function (c) { return esc(c.name); }).join('、') + ' 的单位表里没写，先按字典默认，请核对' : '') + '。</div>' +
        '<div class="foot">' + (!hasT ? '<span class="tip" data-ptds-ui="s2bb8a2118723">要有一列是时间或日期</span>' : !hasV ? '<span class="tip" data-ptds-ui="sfe44b67604dc">至少要有一列数据</span>' : '') + '<button class="chip" id="bt-skip" data-ptds-ui="sacad635e0ab4">不导入这个表</button><button class="btn" data-sem="SEM-14" id="bt-ok"' + (hasT && hasV ? '' : ' disabled aria-disabled="true"') + '>确认这个格式</button></div>' +
        '<div class="sub2" data-ptds-ui="s5e81e2b649dc">确认后：按类型确认（条数、时间段、抽样原文），再保存。</div></section>';
      document.getElementById('bt-back').onclick = LIVE.btBack;
      document.querySelectorAll('[data-method]').forEach(function (b) { b.onclick = function () { st.btOpen = null; st.entry.method = b.dataset.method; C.render(); }; });
      document.querySelectorAll('[data-bt-col]').forEach(function (s) { s.onchange = function () { cols[+s.dataset.btCol].target = s.value; cols[+s.dataset.btCol].unit = ''; LIVE.renderBatchOpen(); }; });
      document.querySelectorAll('[data-bt-unit]').forEach(function (s) { s.onchange = function () { cols[+s.dataset.btUnit].unit = s.value; }; });
      document.getElementById('bt-skip').onclick = LIVE.action(async function () { try { (await call('POST', '/api/batch/skip', { key: st.key, id: it.id })); } catch (err) { if(err&&(err.viewPending||err.code==='VIEW_CHANGED'))throw err; C.toast(err.detail || err.code); } LIVE.btBack(); });
      document.getElementById('bt-ok').onclick = LIVE.action(async function () {
        try { (await call('POST', '/api/batch/mapping', { key: st.key, id: it.id, columns: cols })); st.btMap = null; C.toast('记住这个格式了，正在按它读这份表'); LIVE.btBack(); }
        catch (err) { if(err&&(err.viewPending||err.code==='VIEW_CHANGED'))throw err; C.toast('没确认成：' + ({ MAPPING_NO_TIME: '要有一列是时间或日期', MAPPING_NO_VALUE: '至少要有一列数据' }[err.code] || err.detail || err.code)); }
      });
    },
    renderMeds: function () {
      var esc = C.esc, ic = C.ic, st = C.st, M = LIVE.medsGet(), cs = M.courses, today = String(C.tzTime(new Date().toISOString())).slice(0, 10);
      var f = st.medF = st.medF || { kind: 'START', med_id: '', drug: '', dose: '', unit: 'mg', route: '口服', freq: '', date: today, reason: '' };
      var KZ = { START: '开始用药', CHANGE: '改剂量', STOP: '停药', RESTART: '重新用药' };
      var pick = cs.filter(function (c) { return f.kind === 'RESTART' ? !c.active && c.live : c.active; });
      /* 选中哪个药，就把它最近一段的剂量、单位、途径、频次带进来（改剂量、重新用药时只改要改的） */
      var prefill = function (c) { var sp = c && c.spans[c.spans.length - 1]; if (sp) { f.dose = sp.dose; f.unit = sp.unit; f.route = sp.route; f.freq = sp.freq; } f._pre = c ? c.med_id : ''; };
      if (f.kind !== 'START' && !pick.some(function (c) { return c.med_id === f.med_id; })) f.med_id = pick.length ? pick[0].med_id : '';
      if (f.kind !== 'START' && f.med_id && f._pre !== f.med_id) prefill(pick.filter(function (c) { return c.med_id === f.med_id; })[0]);
      if (f.kind === 'START' && f._pre) { f.dose = ''; f.freq = ''; f._pre = ''; }
      var opt = function (list, cur) { return list.map(function (u) { return '<option' + (u === cur ? ' selected' : '') + '>' + esc(u) + '</option>'; }).join(''); };
      var lab = function (t, inner) { return '<label class="sub2">' + t + inner + '</label>'; }, W = ' style="width:100%;margin-top:6px"';
      var inp = function (k, ph) { return '<input class="inp" data-mf="' + k + '" value="' + esc(f[k] || '') + '"' + (ph ? ' placeholder="' + esc(ph) + '"' : '') + W + '>'; };
      var who = f.kind === 'START' ? lab('药名', inp('drug', '例如：写药品说明书上的名字')) :
        lab('哪个药', '<select class="sel" data-mf="med_id"' + W + '>' + (pick.length ? pick.map(function (c) { return '<option value="' + esc(c.med_id) + '"' + (c.med_id === f.med_id ? ' selected' : '') + '>' + esc(c.drug) + '</option>'; }).join('') : '<option value="">' + (f.kind === 'RESTART' ? '没有已停的药' : '没有在用的药') + '</option>') + '</select>');
      var form = '<section class="panel" data-cmp="T13" style="display:grid;gap:18px">' +
        C.modeSwitch(st.entry) +
        '<div style="display:flex;gap:12px;align-items:center;flex-wrap:wrap"><span class="sub2" style="width:84px" data-ptds-ui="s41456e3039a7">这次记的是</span><span class="seg2" role="group" aria-label="这次记的是" data-ptds-ui-aria-label="s41456e3039a7">' +
          ['START', 'CHANGE', 'STOP', 'RESTART'].map(function (k) { return '<button data-mk="' + k + '" aria-pressed="' + (f.kind === k) + '">' + KZ[k] + '</button>'; }).join('') + '</span></div>' +
        (f.kind === 'STOP' ? '<div class="mgrid2">' + who + lab('停药日期（这天起不再用）', '<input class="inp" type="date" data-mf="date" value="' + esc(f.date) + '" max="' + today + '"' + W + '>') + '</div>' :
          '<div class="mgrid">' + who + lab('剂量', '<input class="inp" data-mf="dose" inputmode="decimal" value="' + esc(f.dose) + '"' + W + '>') +
            lab('单位', '<select class="sel" data-mf="unit"' + W + '>' + opt(LIVE.MED_UNITS, f.unit) + '</select>') +
            lab('途径', '<select class="sel" data-mf="route"' + W + '>' + opt(LIVE.MED_ROUTES, f.route) + '</select>') + lab('频次', inp('freq', '例如：每天 1 次')) + '</div>' +
          '<div class="mgrid2">' + lab('日期', '<input class="inp" type="date" data-mf="date" value="' + esc(f.date) + '" max="' + today + '"' + W + '>') + lab('原因（选填）', inp('reason', '例如：按医生安排')) + '</div>') +
        (f.kind === 'STOP' ? '<div>' + lab('原因（选填）', inp('reason', '例如：按医生安排停药')) + '</div>' : '') +
        (st.medErr ? '<div class="sub2" style="color:var(--theme-level-alert-text)">' + esc(st.medErr) + '</div>' : '') +
        '<div style="display:flex;align-items:center;gap:12px"><span class="sub2" style="flex:1" data-ptds-ui="saefceacc1a70">只记事实，不判断剂量。用药记录不交给星灵，也不进任何阈值。</span><button class="btn" id="med-save"' + (f.kind !== 'START' && !f.med_id ? ' disabled' : '') + '>保存这一条</button></div></section>';
      var open = st.medOpen = st.medOpen || {}, ed = st.medEdit;
      var list = '<section class="box" style="margin-top:20px"><h3>已记录的用药<span class="grow"></span><span class="sub2">' + (M.chain.ok ? '记录完整 · 每条都能追到录入时间' : '记录核对没通过：第 ' + esc(M.chain.line) + ' 行被改过') + '</span></h3>' +
        (cs.length ? cs.map(function (c) {
          var sp = c.spans[c.spans.length - 1], last = c.events.filter(function (e) { return !e.retracted; }).slice(-1)[0] || c.events[c.events.length - 1];
          var sum = sp ? sp.dose + ' ' + sp.unit + ' · ' + sp.route + (sp.freq ? ' · ' + sp.freq : '') : '';
          var stt = c.active && sp ? '在用 · 自 ' + sp.from.slice(5) : sp ? '已停 · ' + c.spans[0].from.slice(5) + ' 起，' + (sp.to || '').slice(5) + ' 起不再用' : '已全部撤回';
          var row = '<button class="lrow c3" data-mo="' + esc(c.med_id) + '" style="width:100%;text-align:left;background:none;border:0;border-bottom:var(--primitive-border-hairline) solid var(--theme-line-hairline);color:inherit;font:inherit;cursor:pointer"><span>' + esc(c.drug) + ' <span class="sub2">' + esc(sum) + '</span><br><span class="sub2">' + esc(stt) + ' · ' + c.events.length + ' 条记录</span></span><span class="sub2">' + esc(last.date.slice(5) + ' ' + last.kind_zh) + '</span><span>' + ic(open[c.med_id] ? 'chevron-down' : 'chevron-right') + '</span></button>';
          if (!open[c.med_id]) return row;
          return row + '<div style="margin:4px 0 12px 16px;border-left:1px solid var(--theme-line-hairline);padding-left:14px;display:grid;gap:8px">' + c.events.map(function (e) {
            var txt = e.date.slice(5) + ' ' + e.kind_zh + (e.kind !== 'STOP' ? ' · ' + e.dose + ' ' + e.unit + ' · ' + e.route : '') + (e.reason ? ' · 原因：' + e.reason : '') + ((e.corrected_by || []).length ? '（更正过）' : '');
            var line = '<div class="sub2"' + (e.retracted ? ' style="opacity:.6"' : '') + '>' + (e.retracted ? '<s>' + esc(txt) + '</s> · 已撤回：' + esc(e.retract_reason || '') : esc(txt) + '　<button class="link" data-me="CORRECT|' + esc(e.event_id) + '">更正</button>　<button class="link" data-me="RETRACT|' + esc(e.event_id) + '">撤回</button>') + '</div>';
            if (ed && ed.event_id === e.event_id) {
              line += ed.mode === 'RETRACT' ? '<div style="display:flex;gap:8px;align-items:center"><input class="inp" data-mx="reason" placeholder="撤回原因（必填）" value="' + esc(ed.reason || '') + '" style="flex:1"><button class="btn2" id="me-ok" data-ptds-ui="s437aaf50094f">确认撤回</button><button class="link" id="me-no" data-ptds-ui="s2cd0f3be8738">取消</button></div>'
                : '<div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">' + (e.kind !== 'STOP' ? '<input class="inp" data-mx="dose" value="' + esc(ed.dose) + '" style="width:90px" aria-label="剂量"><select class="sel" data-mx="unit" aria-label="单位" data-ptds-ui-aria-label="s80b19d68b149">' + opt(LIVE.MED_UNITS, ed.unit) + '</select>' : '') +
                  '<input class="inp" type="date" data-mx="date" value="' + esc(ed.date) + '" max="' + today + '" aria-label="日期"><input class="inp" data-mx="reason" value="' + esc(ed.reason || '') + '" placeholder="原因（选填）" style="flex:1"><button class="btn2" id="me-ok" data-ptds-ui="s529ad45824a4">保存更正</button><button class="link" id="me-no" data-ptds-ui="s2cd0f3be8738">取消</button></div>';
            }
            return line;
          }).join('') + '</div>';
        }).join('') : '<div class="sub2" data-ptds-ui="se69db3dc9d76">还没有用药记录。</div>') + '</section>';
      document.getElementById('view').innerHTML = form + list;
      var v = document.getElementById('view');
      v.querySelectorAll('[data-method]').forEach(function (b) { b.onclick = function () { st.entry.method = b.dataset.method; st.medErr = null; C.render(); }; });
      v.querySelectorAll('[data-mk]').forEach(function (b) { b.onclick = function () { f.kind = b.dataset.mk; st.medErr = null; LIVE.renderMeds(); }; });
      v.querySelectorAll('[data-mf]').forEach(function (x) { x.oninput = x.onchange = function () { f[x.dataset.mf] = x.value;
        if (x.dataset.mf === 'med_id') LIVE.renderMeds(); }; });
      v.querySelectorAll('[data-mo]').forEach(function (b) { b.onclick = function () { open[b.dataset.mo] = !open[b.dataset.mo]; LIVE.renderMeds(); }; });
      v.querySelectorAll('[data-me]').forEach(function (b) { b.onclick = function () { var p = b.dataset.me.split('|'), e = null;
        cs.forEach(function (c) { c.events.forEach(function (z) { if (z.event_id === p[1]) e = z; }); });
        st.medEdit = { mode: p[0], event_id: p[1], dose: e.dose, unit: e.unit, date: e.date, reason: p[0] === 'RETRACT' ? '' : e.reason || '', kind: e.kind, o: e }; LIVE.renderMeds(); }; });
      v.querySelectorAll('[data-mx]').forEach(function (x) { x.oninput = x.onchange = function () { st.medEdit[x.dataset.mx] = x.value; }; });
      var g = function (id, fn) { var b = document.getElementById(id); if (b) b.onclick = LIVE.action(fn); };
      g('me-no', function () { st.medEdit = null; LIVE.renderMeds(); });
      g('me-ok', LIVE.action(async function () { var e = st.medEdit, body = { key: st.key, kind: e.mode, event_id: e.event_id };
        if (e.mode === 'RETRACT') body.reason = e.reason;
        else { body.fields = {}; (e.kind !== 'STOP' ? ['date', 'reason', 'dose', 'unit'] : ['date', 'reason']).forEach(function (k) { if (String(e[k] || '') !== String(e.o[k] || '')) body.fields[k] = e[k]; }); /* 只交改了的字段 */
          if (!Object.keys(body.fields).length) { C.toast('没有改动'); return; } }
        var r; try { r = (await call('POST', '/api/meds/amend', body)); } catch (err) { if(err&&(err.viewPending||err.code==='VIEW_CHANGED'))throw err; C.toast(err.detail || LIVE.saveErr(err)); return; }
        LIVE._meds = { key: st.key, v: r }; st.medEdit = null; C.toast(e.mode === 'RETRACT' ? '已撤回，原记录保留' : '已更正，原记录保留'); LIVE.renderMeds(); }));
      g('med-save', LIVE.action(async function () {
        var body = { key: st.key, kind: f.kind, med_id: f.med_id, date: f.date, reason: f.reason };
        if (f.kind === 'START') body.drug = f.drug;
        if (f.kind !== 'STOP') { body.dose = f.dose; body.unit = f.unit; body.route = f.route; body.freq = f.freq; }
        var r; try { r = (await call('POST', '/api/meds', body)); } catch (err) { if(err&&(err.viewPending||err.code==='VIEW_CHANGED'))throw err; st.medErr = err.detail || LIVE.saveErr(err); LIVE.renderMeds(); return; }
        LIVE._meds = { key: st.key, v: r }; st.medErr = null;
        C.toast('已保存：' + KZ[f.kind] + (f.kind === 'START' ? ' · ' + f.drug : ''));
        st.medF = { kind: 'START', med_id: '', drug: '', dose: '', unit: 'mg', route: '口服', freq: '', date: today, reason: '' };
        LIVE.renderMeds(); }));
    },
    /* 我的数源子页（产品负责人 2026-10-14 07:25）：纵向长方形卡片，四类来源同一尺寸；穿戴设备的图标只分类型，不用品牌 */
    KIND_IC: {
      scale: '<svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="4" y="3" width="16" height="18" rx="4"/><path d="M8 8a5 5 0 0 1 8 0M12 8l2-2M8 16h8"/></svg>',
      glucose: '<svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="5" y="4" width="14" height="16" rx="6"/><circle cx="12" cy="12" r="3"/><path d="M12 9v3l2 1"/></svg>',
      chest_strap: '<svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M8 8H5a3 3 0 0 0-3 3v2a3 3 0 0 0 3 3h3M16 8h3a3 3 0 0 1 3 3v2a3 3 0 0 1-3 3h-3"/><rect x="8" y="6" width="8" height="12" rx="3"/><path d="M10 12h1l1-2 1 4 1-2"/></svg>',
      pillbox: '<svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="4" width="18" height="16" rx="4"/><path d="M3 10h18M12 10v10M7 7h2M15 7h2"/></svg>',
      bed: '<svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 19V6a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v13M3 17h18M3 11h18"/><rect x="6" y="7" width="5" height="4" rx="1"/><rect x="13" y="7" width="5" height="4" rx="1"/></svg>',
      ring: '<svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" aria-hidden="true"><ellipse cx="12" cy="13" rx="7.5" ry="7"/><path d="M8.5 6.5c1-1.6 2.2-2.4 3.5-2.4s2.5.8 3.5 2.4"/></svg>',
      band: '<svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" aria-hidden="true"><rect x="8" y="2.5" width="8" height="19" rx="4"/><rect x="9.8" y="9" width="4.4" height="6" rx="1.2"/></svg>',
      bci: '<svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" aria-hidden="true"><path d="M4 16a8 8 0 0 1 16 0"/><circle cx="4" cy="17.5" r="1.6"/><circle cx="20" cy="17.5" r="1.6"/><path d="M7.6 9.6l1 1.2M16.4 9.6l-1 1.2M12 6.5v1.6"/></svg>',
      more: '<svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" aria-hidden="true"><rect x="3.5" y="3.5" width="7" height="7" rx="2"/><rect x="13.5" y="3.5" width="7" height="7" rx="2"/><rect x="3.5" y="13.5" width="7" height="7" rx="2"/><path d="M17 14v6M14 17h6"/></svg>'
    },
    // Catalog entries only. Adapter registration and acquisition remain separate.
    WEARABLE_ADDITIONS: [
      {id:'xiaomi_band',zh:'小米手环',sub:'手环 · 接入待适配',catalogOnly:true},
      {id:'withings_body_scan',zh:'Withings Body Scan',sub:'智能体重秤 · 接入待适配',catalogOnly:true},
      {id:'withings_body_segment',zh:'Withings Body Segment',sub:'智能体重秤 · 型号待核对 · 接入待适配',catalogOnly:true},
      {id:'dexcom_g7',zh:'Dexcom G7',sub:'连续血糖监测 · 接入待适配',catalogOnly:true},
      {id:'polar_h10',zh:'Polar H10',sub:'心率带 · 接入待适配',catalogOnly:true}
    ],
    renderSourceGroup: function () {
      var st = C.st, esc = C.esc, PROD = C.PROD, g = PROD.sources.filter(function (x) { return x.id === st.srcGroup; })[0] || PROD.sources[0];
      if (g.id === 'wearable' && !g.items.some(function(it){return it.id === 'pillbox';})) g.items.push({id:'pillbox',zh:'Hi-PB1',sub:'智能药盒 · 电量与响铃寻找',maturity:'adapted',go:'device:pillbox'});
      if (g.id === 'wearable') LIVE.WEARABLE_ADDITIONS.forEach(function (it) {
        if (!g.items.some(function (existing) { return existing.id === it.id; })) g.items.push(Object.assign({}, it));
      });
      g.items.forEach(function (it) { if (it.id === 'garmin' && it.zh === 'Garmin 手环') it.zh = 'Garmin'; });
      if (g.id === 'wearable' && st.museOpen) return LIVE.renderMuse();
      var icn = function (s) { return C.ic(String(s || '').replace(/^icon:/, '')); };
      var kind = function (it) { return it.id === 'more' ? 'more' : /脑机/.test(it.sub || '') ? 'bci' : /指环/.test(it.sub || '') ? 'ring' : 'band'; };
      var S = C.S(), real = S && (S.instance || {}).kind === 'REAL' && !C.isReplay(), src = real && g.id === 'wearable' ? LIVE.tailSrc() : null;
      var STAT = { CONNECTED: '已接入', NEEDS_REAUTH: '需要重新授权' };
      var items = g.items.filter(function (it) { return !it.hidden; });
      var groups = [{id:'band',zh:'手环'},{id:'ring',zh:'指环'},{id:'bci',zh:'脑机接口'},{id:'bed',zh:'智能床垫'},{id:'scale',zh:'智能体重秤'},{id:'glucose',zh:'连续血糖监测'},{id:'chest_strap',zh:'心率带'},{id:'pillbox',zh:'智能药盒'},{id:'more',zh:'其他'}];
      var deviceKinds = {pillbox:'pillbox',eight_sleep:'bed',garmin:'band',xiaomi_band:'band',withings_body_scan:'scale',withings_body_segment:'scale',dexcom_g7:'glucose',polar_h10:'chest_strap'};
      var deviceKind = function (it) { return deviceKinds[it.id] || kind(it); };
      if (g.id === 'wearable' && !st.deviceKind) {
        document.getElementById('view').innerHTML = '<section class="box"><h3>' + esc(g.zh) + '<span class="grow"></span><button class="btn2" id="src-back">返回</button></h3><div class="srcards">' + groups.map(function (gr) {
          var members = items.filter(function (it) { return deviceKind(it) === gr.id; });
          return '<button class="srcard" data-device-kind="' + gr.id + '"><span class="sc-top"><span class="sc-ic">' + (LIVE.KIND_IC[gr.id] || C.ic('layers')) + '</span><span class="grow"></span>' + C.ic('chevron-right') + '</span><span class="nm">' + gr.zh + '</span><span class="sub2">' + members.length + ' 款设备</span><span class="sub2">' + esc(members.map(function (it) { return it.zh; }).join(' · ')) + '</span></button>';
        }).join('') + '</div></section>';
        document.getElementById('src-back').onclick = function () { C.goTorch('sources'); };
        document.querySelectorAll('[data-device-kind]').forEach(function (b) { b.onclick = function () { st.deviceKind = b.dataset.deviceKind; C.render(); }; });
        return;
      }
      if (g.id === 'wearable') items = items.filter(function (it) { return deviceKind(it) === st.deviceKind; });
      if (g.id === 'wearable' && st.sourceDevice) {
        var selected = items.filter(function (it) { return it.id === st.sourceDevice; })[0];
        if (selected) {
          return LIVE.renderDeviceConnection(selected);
        }
        st.sourceDevice = null;
      }
      if (g.id === 'file') items = items.concat([{ id: 'batch', zh: '超融合批量识别', sub: '一次放进一批文件，自动分类识别，按类确认后入库', maturity: 'ready', go: 'entry:batch' }]); /* 产品负责人 2026-10-14 08:30 */
      var cards = items.map(function (it) {
        var muse = it.id === 'muse', click = g.id === 'wearable' || muse || (it.maturity !== 'dev' && !!it.go), note = muse ? '会话导入与读回 · 设备测试待进行' : '';
        var dv = (C.DATA.live && C.DATA.live.devices || []).filter(function (d) { return d.name === it.zh; })[0];
        if (dv && C.isReplay() && C.LV.dev[dv.id] && C.LV.dev[dv.id].connected) note = '已接入';
        if (src && src[it.id] && STAT[src[it.id].status]) note = STAT[src[it.id].status];
        if (it.catalogOnly) note = ''; // A catalog placeholder is never evidence of a connection.
        if (it.id === 'apple') { var ph = C.MockBridge.phones(C.instId())[0]; if (ph) note = '已配对 ' + ph.name + (ph.last_sync ? ' · 上次同步 ' + C.tzTime(ph.last_sync) : ''); }
        var icon = g.id === 'wearable' ? (LIVE.KIND_IC[deviceKind(it)] || C.ic('layers')) : icn(g.icon);
        return '<button class="srcard" data-go="' + esc(g.id === 'wearable' ? 'device:'+it.id : muse ? 'muse' : click ? it.go : '') + '"' + (click ? '' : ' aria-disabled="true"') + (g.id === 'wearable' ? ' data-sem="SEM-19"' : it.id === 'apple' ? ' data-sem="SEM-34"' : '') + '>' +
          '<span class="sc-top"><span class="sc-ic">' + icon + '</span><span class="grow"></span>' + (click ? C.ic('chevron-right') : '') + '</span>' +
          '<span class="nm">' + esc(it.zh) + C.mtag(it.maturity) + '</span><span class="sub2">' + esc(it.sub || '') + '</span>' +
          (note ? '<span class="sc-note">' + C.ic('check') + esc(note) + '</span>' : '') + '</button>';
      }).join('');
      document.getElementById('view').innerHTML = '<section class="box" data-cmp="T15"><h3>' + icn(g.icon) + esc(g.id === 'wearable' ? groups.filter(function (gr) { return gr.id === st.deviceKind; })[0].zh : g.zh) + '<span class="grow"></span><button class="btn2" id="src-back">' + C.ic('chevron-left') + '返回</button></h3>' +
        '<div class="sub2">' + esc(g.id === 'wearable' ? '选择设备，查看接入方式、连接状态与准备步骤。' : PROD.source_groups[g.id]) + '</div><div class="srcards">' + cards + '</div></section>';
      document.getElementById('src-back').onclick = function () { if (g.id === 'wearable') { st.deviceKind = null; st.sourceDevice = null; C.render(); } else C.goTorch('sources'); };
      document.querySelectorAll('.srcard[data-go]').forEach(function (b) { if (b.getAttribute('aria-disabled')) return; b.onclick = function () {
        var go = b.dataset.go; if (!go) return;
        if (go.indexOf('device:') === 0) { st.sourceDevice = go.slice(7); return C.render(); }
        if (go === 'muse') { st.museOpen = true; return C.render(); }
        if (go.indexOf('entry:') === 0) { st.entry = C.newEntry(); st.entry.method = go.slice(6); C.goTorch('entry'); }
        else { st.geneLast = null; st.ahPhase = null; st.ahMsg = null; C.goTorch(go); } }; });
    },
    tailSrc: function () {
      var now = Date.now(), k = C.st.key;
      if (LIVE._tlSrc && LIVE._tlSrc.key === k && now - LIVE._tlSrc.at < 60000) return LIVE._tlSrc.v;
      LIVE._tlSrc = { key: k, at: now, v: (LIVE._tlSrc && LIVE._tlSrc.key === k) ? LIVE._tlSrc.v : null };
      fetch('/api/sources?key=' + encodeURIComponent(k)).then(function (r) { return r.json(); }).then(function (j) { if (LIVE._tlSrc.key === k) { LIVE._tlSrc.v = j; if (!LIVE._tlSet && !LIVE._pointerDown) LIVE.tailMount(); } }).catch(function () {});
      return LIVE._tlSrc.v;
    },
    tailMount: function (off) { if(globalThis.PTDS_TRIAL_UI&&!PTDS_TRIAL_UI.can('tails')) off=true;
      var S = null; try { S = C.S(); } catch (err) { if(err&&(err.viewPending||err.code==='VIEW_CHANGED'))throw err; S = null; }
      var real = !off && S && (S.instance || {}).kind === 'REAL' && !C.isReplay(), src = real ? LIVE.tailSrc() : null;
      LIVE.TAILS.forEach(function (t) {
        var id = 'tl-' + t.id, f = document.getElementById(id), st = src && src[t.id] && src[t.id].status;
        var on = real && (st === 'CONNECTED' || st === 'NEEDS_REAUTH');
        if (!on) { if (f) f.remove(); var c0 = document.getElementById(id + '-card'); if (c0) c0.remove(); delete LIVE.DOCK[id]; return; }
        LIVE.DOCK[id] = LIVE.DOCK[id] || { def: 1, pop: id + '-card', beside: true };
        if (!f) {
          f = document.createElement('button'); f.id = id; f.className = 'tl-fab'; f.setAttribute('aria-label', t.name + ' 最近读数'); f.title = t.name + ' 最近读数';
          document.body.appendChild(f); LIVE.dockDrag(f, id, function () { LIVE._tlOpen = LIVE._tlOpen === t.id ? null : t.id; LIVE.tailMount(); });
        }
        var d = LIVE.tailData(t, S, src[t.id]);
        f.innerHTML = '<span class="tl-ic">' + t.icon + '</span><span class="tl-dot ' + d.dot + '"></span>';
        var card = document.getElementById(id + '-card');
        if (LIVE._tlOpen !== t.id) { if (card) card.remove(); }
        else {
          if (!card) { card = document.createElement('div'); card.id = id + '-card'; card.className = 'tl-card'; card.setAttribute('role', 'dialog'); document.body.appendChild(card); }
          card.innerHTML = LIVE.tailCardHtml(t, d);
          LIVE.desktopPinBind(card, t, d.tiles.map(function (z) { return z.x; }));
          card.querySelectorAll('[data-tl-go]').forEach(function (x) { x.onclick = function () { LIVE._tlOpen = null; LIVE.tailMount(); window.__ptds.goTorch('data'); }; });
          card.querySelector('[data-tl-x]').onclick = function () { LIVE._tlOpen = null; LIVE.tailMount(); };
          card.querySelectorAll('[data-tl-set]').forEach(function (x) { x.onclick = function () { LIVE._tlSet = LIVE._tlSet === t.id ? null : t.id; LIVE._tlPick = null; LIVE.tailMount(); }; });
          card.querySelectorAll('[data-tl-pick]').forEach(function (x) { x.onclick = function () {
            var cur = LIVE._tlPick || d.tiles.map(function (z) { return z.x.code; }), c = x.dataset.tlPick, i = cur.indexOf(c);
            cur = cur.slice(); if (i >= 0) cur.splice(i, 1); else if (cur.length < 4) cur.push(c); LIVE._tlPick = cur; LIVE.tailMount(); }; });
          var sv = card.querySelector('[data-tl-save]'); if (sv) sv.onclick = LIVE.action(async function () {
            try { (await call('POST', '/api/sources/tail', { key: C.st.key, device: t.id, codes: LIVE._tlPick || d.tiles.map(function (z) { return z.x.code; }) })); LIVE._tlSet = null; LIVE._tlPick = null; LIVE._tlSrc = null; C.toast('小尾巴改好了'); }
            catch (err) { if(err&&(err.viewPending||err.code==='VIEW_CHANGED'))throw err; C.toast('没存上（' + (err.detail || err.code) + '）'); }
            LIVE.tailMount(); });
        }
      });
      LIVE.dockPlace();
    },
    /* Somaloop 小尾巴（产品负责人 2026-10-14 09:21 / 09:23）：只在 sJIA 演示里出现；Oura 小尾巴只在个人基座。同一种圆形浮窗、同一种四格读数，
       不画走势。四项固定：心率、血氧、皮肤温度、心率变异性（都是腕带真实读数，没有就写“—”）。连续个人读数，不再切换体验者；图钉打开跨应用原生窗口。 */
    pillboxRequest: function (op, body) {
      return callAsync(op==='status'?'GET':'POST','/api/pillbox/'+op+(op==='status'?'?key='+encodeURIComponent(C.st.key):''),op==='status'?null:Object.assign({key:C.st.key},body||{}));
    },
    pillboxSettings: function () {
      var old=document.getElementById('pb-settings');if(old)old.remove();
      var el=document.createElement('aside');el.id='pb-settings';el.className='drawer';el.setAttribute('role','dialog');el.setAttribute('aria-label','我的药盒');
      el.innerHTML='<div class="daterow"><b>我的药盒</b><span class="grow"></span><button class="ibtn" id="pb-settings-x" aria-label="关闭药盒连接">'+C.ic('x')+'</button></div><p role="status">状态暂不可用</p>';
      document.body.appendChild(el);el.querySelector('#pb-settings-x').onclick=function(){el.remove();};
      el.querySelector('#pb-settings-x').focus();el.onkeydown=function(e){if(e.key==='Escape')el.remove();};
    },
    pillboxMount: function (off) {
      var S;try{S=C.S();}catch(e){ if(e&&(e.viewPending||e.code==='VIEW_CHANGED'))throw e;S=null;}var id='tl-pillbox',f=document.getElementById(id),card=document.getElementById(id+'-card');
      var active=!off&&S&&!C.isReplay(),key=C.st.key;
      if(!active||LIVE._pbKey!==key){clearInterval(LIVE._pbTimer);LIVE._pbTimer=null;LIVE._pbD=null;LIVE._pbOpen=false;LIVE._pbMessage='';LIVE._pbBusy=false;LIVE._pbKey=key;if(card)card.remove();var setup=document.getElementById('pb-settings');if(setup)setup.remove();}
      if(!active){if(f)f.remove();delete LIVE.DOCK[id];return;}
      if(!LIVE._pbTimer){var pull=function(){if(LIVE._pbPull)return;LIVE._pbPull=true;LIVE.pillboxRequest('status').then(function(d){if(C.st.key===key){if(!d.connected)LIVE._pbMessage="";LIVE._pbD=d;LIVE.pillboxMount();}}).catch(function(){if(C.st.key===key){LIVE._pbMessage="";LIVE._pbD=null;LIVE.pillboxMount();}}).finally(function(){LIVE._pbPull=false;});};LIVE._pbTimer=setInterval(pull,3000);pull();}
      LIVE.DOCK[id]=LIVE.DOCK[id]||{def:2,pop:id+'-card',beside:true};
      if(!f){f=document.createElement('button');f.id=id;f.className='tl-fab';f.setAttribute('aria-label','我的药盒');f.title='我的药盒';document.body.appendChild(f);LIVE.dockDrag(f,id,function(){LIVE._pbOpen=!LIVE._pbOpen;LIVE.pillboxMount();});}
      var d=LIVE._pbD||{connected:false};f.innerHTML='<span class="tl-ic">'+PTDSTail.pillboxIcon+'</span><span class="tl-dot '+(d.connected?'':'old')+'"></span>';
      if(!LIVE._pbOpen){if(card)card.remove();LIVE.dockPlace();return;}
      if(!card||!card.isConnected){card=document.createElement('div');card.id=id+'-card';card.className='tl-card pb-card';card.setAttribute('role','dialog');card.setAttribute('aria-label','我的药盒');document.body.appendChild(card);}
      var content=PTDSTail.pillbox(Object.assign({},d,{busy:LIVE._desktopOpening,findBusy:LIVE._pbBusy,message:LIVE._pbMessage}));
      if(card._pbContent===content){LIVE.dockPlace();return;}card._pbContent=content;var focused=card.contains(document.activeElement)&&document.activeElement.hasAttribute('data-pillbox-find');card.innerHTML=content;
      card.querySelector('[data-tl-x]').onclick=function(){LIVE._pbOpen=false;LIVE.pillboxMount();f.focus();};
      card.querySelector('.tl-name').style.cursor='pointer';card.querySelector('.tl-name').setAttribute('role','button');card.querySelector('.tl-name').tabIndex=0;card.querySelector('.tl-name').title='连接我的药盒';card.querySelector('.tl-name').onclick=LIVE.pillboxSettings;card.querySelector('.tl-name').onkeydown=function(e){if(e.key==='Enter'||e.key===' '){e.preventDefault();LIVE.pillboxSettings();}};
      card.querySelector('[data-pillbox-find]').onclick=function(){if(LIVE._pbBusy||!d.connected)return;LIVE._pbBusy=true;LIVE._pbMessage='正在发送寻找指令…';LIVE.pillboxMount();LIVE.pillboxRequest('find').then(function(r){if(C.st.key===key)LIVE._pbMessage=r.detail;}).catch(function(e){if(C.st.key===key)LIVE._pbMessage=e.detail||'未发送，请重新连接';}).finally(function(){if(C.st.key===key){LIVE._pbBusy=false;LIVE.pillboxMount();}});};
      LIVE.desktopPinBind(card,{id:'pillbox',name:'我的药盒',src:'LOCAL_PILLBOX',chain:''},[]);if(focused)card.querySelector('[data-pillbox-find]').focus();LIVE.dockPlace();
    },
    phoneSummaryPull: function () {
      if (LIVE._phoneSummaryBusy) return;
      LIVE._phoneSummaryBusy=true;
      var ctl=new AbortController(),timer=setTimeout(function(){ctl.abort();},5000);
      fetch('/api/phone-tail/status',{headers:{'X-PTDS':'1'},cache:'no-store',signal:ctl.signal})
        .then(function(r){if(!r.ok)throw new Error('status');return r.json();})
        .then(function(s){LIVE._phoneSummary=s;})
        .catch(function(){LIVE._phoneSummary=null;})
        .finally(function(){clearTimeout(timer);LIVE._phoneSummaryBusy=false;LIVE.bandTailMount();});
    },
    BAND_TAIL: { id: 'somaloop', name: 'Somaloop', chain: '腕带→这台 Mac（腕带桥）· 近期读数',
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><rect x="8" y="2.5" width="8" height="19" rx="4"/><rect x="9.8" y="9" width="4.4" height="6" rx="1.2"/></svg>',
      label: { HR: '最近心率', SPO2: '血氧', SKIN_TEMP: '皮肤温度', HRV: '心率变异性' }, unit: { HR: '次/分', SPO2: '%', SKIN_TEMP: '°C', HRV: 'ms' } },
    bandTailMount: function (off) { if(globalThis.PTDS_TRIAL_UI&&!PTDS_TRIAL_UI.can('band')) off=true;
      var S = null; try { S = C.S(); } catch (err) { if(err&&(err.viewPending||err.code==='VIEW_CHANGED'))throw err; S = null; }
      var t = LIVE.BAND_TAIL, id = 'tl-' + t.id, f = document.getElementById(id), on = !off && S && (S.instance || {}).kind === 'DEMO' && !C.isReplay();
      if (!on) { if (f) f.remove(); var c0 = document.getElementById(id + '-card'); if (c0) c0.remove(); delete LIVE.DOCK[id]; clearInterval(LIVE._bandTimer); LIVE._bandTimer = null; return; }
      if (!LIVE._bandTimer) {
        var pull = function () { LIVE.phoneSummaryPull(); if(LIVE._bandReadBusy)return;LIVE._bandReadBusy=true;readView('/api/band').then(function(j){LIVE._btD=j;LIVE.bandTailMount();}).catch(function(){}).finally(function(){LIVE._bandReadBusy=false;}); };
        LIVE._bandTimer = setInterval(pull, 3000); pull();
      }
      LIVE.DOCK[id] = LIVE.DOCK[id] || { def: 1, pop: id + '-card', beside: true };
      if (!f) {
        f = document.createElement('button'); f.id = id; f.className = 'tl-fab'; f.setAttribute('aria-label', t.name + ' 最近读数'); f.title = t.name + ' 最近读数';
        document.body.appendChild(f); LIVE.dockDrag(f, id, function () { LIVE._btOpen = !LIVE._btOpen; LIVE.bandTailMount(); });
      }
      var d = LIVE._btD, st = (d && d.status) || {}, now = Date.now() / 1000;
      var tiles = ((d && d.tiles) || ['HR', 'SPO2', 'SKIN_TEMP', 'HRV'].map(function (k) { return { kind: k }; })).map(function (z) {
        var L = z.latest, v = null;
        if (L) v = window.PTDSTail.bandValue(z.kind, L.value);
        return { k: z.kind, v: v, sub: L ? LIVE.bandHhmm(L.at) + ' 的读数' : (S.device_policy || {}).mode === 'daily' ? '等待最近读数' : '还没有数据', old: L && now - L.at > 600 };
      });
      var fresh = tiles.some(function (z) { return z.v != null && !z.old; });
      f.innerHTML = '<span class="tl-ic">' + t.icon + '</span><span class="tl-dot ' + (!st.alive ? 'off' : fresh ? 'ok' : 'stale') + '"></span>';
      var card = document.getElementById(id + '-card');
      if (!LIVE._btOpen) { if (card) card.remove(); LIVE.dockPlace(); return; }
      if (!card) { card = document.createElement('div'); card.id = id + '-card'; card.className = 'tl-card'; card.setAttribute('role', 'dialog'); document.body.appendChild(card); }
      var esc = C.esc;
      card.innerHTML = window.PTDSTail.html({ name: t.name, device: t.id, icon: t.icon, busy: LIVE._desktopOpening,
        status: LIVE.bandState(d), sharing: LIVE._phoneSummary,
        tiles: tiles.map(function (z) { return { code: z.k, label: t.label[z.k], value: z.v, unit: t.unit[z.k], note: z.sub, old: z.old }; }), footer: t.chain });
      card.querySelector('[data-tl-x]').onclick = function (e) { e.stopPropagation(); LIVE._btOpen = false; LIVE.bandTailMount(); f.focus(); };
      card.querySelector('[data-tl-share]').onclick = function (e) { e.stopPropagation(); LIVE.phoneShare(LIVE.phoneSpec()); };
      card.querySelectorAll('[data-tl-go]').forEach(function (x) { x.onclick = function () { LIVE._btOpen = false; LIVE.bandTailMount(); window.__ptds.goTorch('data'); }; });
      LIVE.desktopPinBind(card, t, ['HR', 'SPO2', 'SKIN_TEMP', 'HRV'].map(function (kind) {
        return { code: 'SOMALOOP_' + kind, label: t.label[kind], unit: t.unit[kind], when: 'instant' };
      }));
      LIVE.dockPlace();
    },
    /* 状态实验室 · 整体基线洞察（产品负责人 2026-10-15 批准 mock7；只在 sJIA 演示）。表头只有 基线状态 / 发展状态 / 偏移情况，不写日期：
       每一格单独选——换指标、换用哪一次的值，格子里写这个值的日期；偏移那列算两者差多少、相隔多久。
       可选的东西来自 /api/track/baseline（星轨账本的时点结果、星轨收件箱的正式观测）；选了什么只存在这个浏览器（ptds-baseline-sel），不进正式库。
       颜色沿用已发布的规则阈值，本人改过的用本人的并标「患」（紫色）；「规」通到规则库，「患」通到它定义的地方。 */
    BL_TONE: { big: '#E5675F', small: '#E8B65A', down: '#6FA8FF', none: '#8892a0', empty: '#8892a0' },
    BL_CSS: '.bl{display:grid;grid-template-columns:minmax(260px,1fr) 3fr;gap:var(--primitive-space-5);align-items:stretch;margin-top:var(--primitive-space-3)}' +
      '.bl .box{margin:0}.bl>div:last-child{display:flex;min-width:0}.bl>div:last-child>.box{flex:1;min-width:0}.bl-sum{text-align:right;margin-bottom:var(--primitive-space-2)}' +
      '.bl-t{display:grid;grid-template-columns:160px repeat(3,minmax(150px,1fr));align-items:center}' +
      '.bl-t>*{padding:7px 6px;border-bottom:var(--primitive-border-hairline) solid var(--theme-line-hairline);min-width:0}' +
      '.bl-t .hd{color:var(--theme-text-tertiary);font-size:var(--scale-type-meta);border-bottom:0}' +
      '.bl-t .sec{grid-column:1/-1;color:var(--theme-text-tertiary);font-size:var(--scale-type-meta);border-bottom:0;padding-top:14px}' +
      '.bl-t .lb{display:flex;align-items:center;gap:6px}.bl-t .lb>.sub2{white-space:nowrap}.bl-t .lb.hl{color:var(--theme-text-primary);font-weight:600}' +
      '.bl-p{display:inline-block;max-width:100%;padding:3px 9px;border-radius:8px;border:0;font:inherit;font-size:var(--scale-type-meta);cursor:pointer;text-align:left;' +
      'color:var(--theme-text-primary);background:color-mix(in srgb,var(--bl-c) 22%,transparent);overflow-wrap:anywhere}.bl-p.t-none,.bl-p.t-empty{color:var(--theme-text-secondary);background:color-mix(in srgb,var(--theme-text-tertiary) 14%,transparent)}' +
      '.bl-p .d{color:var(--theme-text-tertiary);margin-left:6px}.bl-p:focus-visible{outline:2px solid var(--theme-text-primary)}' +
      '.bl-mk{display:inline-block;font-size:11px;line-height:16px;padding:0 4px;border-radius:4px;border:1px solid var(--theme-line-control);color:var(--theme-text-tertiary);cursor:pointer;background:none}' +
      '.bl-mk.pt{border-color:#9d7cf0;color:#b9a0ff;background:color-mix(in srgb,#9d7cf0 16%,transparent)}' +
      '.bl-t .bl-group{display:flex;align-items:center;justify-content:space-between;gap:12px}.bl-group small{margin-left:8px;font-weight:normal}.bl-count-controls{display:inline-flex;gap:6px}.bl-count-controls button{width:28px;height:28px;border:1px solid var(--theme-line-control);border-radius:6px;background:transparent;color:var(--theme-text-primary);font:inherit;cursor:pointer}.bl-count-controls button:disabled{opacity:.35;cursor:default}' +
      '.bl-pk{position:absolute;z-index:95;width:340px;max-height:420px;overflow:auto;padding:12px;border-radius:12px;background:var(--theme-surface-raised);border:var(--primitive-border-hairline) solid var(--theme-line-control);box-shadow:0 12px 32px rgba(0,0,0,.35)}' +
      '.bl-pk .ch{display:flex;flex-wrap:wrap;gap:6px;margin:6px 0 10px}.bl-pk .rec{display:grid;grid-template-columns:18px 1fr auto;gap:6px;align-items:center;padding:5px 2px;border-bottom:var(--primitive-border-hairline) solid var(--theme-line-hairline);cursor:pointer}' +
      '.bl-lg{display:flex;flex-wrap:wrap;gap:4px 12px;font-size:var(--scale-type-meta);color:var(--theme-text-secondary)}.bl-lg i{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:5px;vertical-align:middle}' +
      '.bl-svg text{font-size:20px;fill:var(--theme-text-secondary)}.bl-svg .spot{cursor:pointer}.bl-svg [role=button]:focus-visible rect{stroke:var(--theme-text-primary);stroke-width:1;rx:3}.bl-svg .spot.hl text{fill:var(--theme-text-primary);font-weight:600}' +
      '.bl-systemic{display:grid;gap:6px;margin:8px 0 14px}.bl-region{border:1px solid var(--theme-line-hairline);border-radius:8px;padding:7px;text-align:left;background:transparent;color:var(--theme-text-secondary);font:inherit;font-size:var(--scale-type-meta);cursor:pointer;line-height:1.6}.bl-region.hl{border-color:var(--theme-text-primary)}.bl-region small{display:block;color:var(--theme-text-tertiary)}.bl-region i{display:inline-block;width:7px;height:7px;border-radius:50%;margin-right:4px}.bl-t .hl{background:color-mix(in srgb,var(--theme-text-primary) 7%,transparent)}' +
      '#bl-summary-go{width:36px;height:36px;padding:0;justify-content:center;border-radius:50%}#bl-summary-go svg{width:20px;height:20px}.bl-summary-drawer{width:480px;z-index:90;animation:bl-slide var(--ptds-fade-duration,180ms) ease-in-out}.bl-summary-drawer{box-shadow:-8px 0 24px rgba(0,0,0,.15)}.bl-brief{padding-left:24px;display:grid;gap:14px}.bl-brief li{padding-left:4px}.bl-summary-evidence{margin-top:20px}.bl-thinking{display:flex;gap:10px;align-items:center;padding:16px 0}.bl-thinking .sp-ic{animation:spw 1.3s ease-in-out infinite}.bl-summary-drawer li{margin:8px 0;overflow-wrap:anywhere}.bl-summary-drawer details{margin-top:4px}.bl-summary-drawer .db{display:block;line-height:1.7}#bl-summary{outline:none}' +
      '@keyframes bl-slide{from{opacity:0}to{opacity:1}}@media(prefers-reduced-motion:reduce){.bl-summary-drawer,.bl-thinking .sp-ic{animation:none}}' +
      '@media (max-width:900px){.bl{grid-template-columns:1fr}}',
    /* BASELINE_ASYNC_R02_BEGIN: rendering never waits for network IO. */
    blGet: function () {
      var key=C.st.key, entry=LIVE._bl;
      if(entry&&entry.key===key&&entry.epoch===readEpoch&&(!entry.retryAt||Date.now()<entry.retryAt))return entry.v;
      if(LIVE._blRequest&&LIVE._blRequest.key===key&&LIVE._blRequest.epoch===readEpoch)return {found:false,why:'LOADING',main:[],clues:[]};
      entry=LIVE._bl={key:key,epoch:readEpoch,v:{found:false,why:'LOADING',main:[],clues:[]}};
      LIVE._blRequest=entry;
      var epoch=readEpoch;
      Promise.all([readView('/api/track/baseline?key='+encodeURIComponent(key)),loadRulesAsync()])
        .then(function(parts){
          if(LIVE._bl!==entry||C.st.key!==key)return;
          if(epoch!==readEpoch){LIVE._bl=null;return;}
          entry.v=parts[0];
          if(C.st.app==='track'&&C.st.view==='wall'){
            LIVE._baselinePaint=key;LIVE.paintCardSaved(key);
          }
        }).catch(function(err){
          if(LIVE._bl!==entry||C.st.key!==key)return;
          // A superseded read is not a service failure; the current view will read again.
          if(epoch!==readEpoch||(err&&err.message==='READ_STALE')){LIVE._bl=null;return;}
          entry.v={found:false,why:'READ_UNAVAILABLE',main:[],clues:[]};entry.retryAt=Date.now()+5000;
          if(C.st.app==='track'&&C.st.view==='wall'){
            LIVE._baselinePaint=key;LIVE.paintCardSaved(key);
          }
        }).finally(function(){
          if(LIVE._blRequest===entry)LIVE._blRequest=null;
          if((!LIVE._bl||LIVE._bl.key!==C.st.key)&&C.st.app==='track'&&C.st.view==='wall'){
            LIVE._baselinePaint=C.st.key;LIVE.paintCardSaved(C.st.key);
          }
        });
      return entry.v;
    },
    /* BASELINE_ASYNC_R02_END */
    /* 选择：{行: {base: {...}, dev: {...}}}；主状态行记时点，线索行记指标和每个指标用哪条记录（按 观测编号@版本） */
    blSel: function (save) {
      var k = 'ptds-baseline-sel', id = C.S().instance.instance_id, all = {};
      try { all = JSON.parse(localStorage.getItem(k) || '{}') || {}; } catch (e) { if(e&&(e.viewPending||e.code==='VIEW_CHANGED'))throw e; all = {}; }
      if (save !== undefined) { all[id] = save; try { localStorage.setItem(k, JSON.stringify(all)); } catch (e) { if(e&&(e.viewPending||e.code==='VIEW_CHANGED'))throw e; /* 只是偏好 */ } }
      return all[id] || {};
    },
    // Field catalog is the intersection of published rules and available engine results.
    blFields: function (kind) {
      var b = LIVE.blGet(), rules = loadRules().rules || [], out = [];
      if (!b.found) return out;
      if (kind === 'm') out = b.main.filter(function (r) { return r.key !== 'level' && r.key !== 'dyn' && rules.some(function (q) { return q.id === r.rule; }); }).map(function (r) { return { value: r.key, label: r.label, row: r }; });
      if (kind === 'c') b.clues.forEach(function (r) {
        out.push({ value: r.id, label: r.label + (r.metric ? '' : '（组合）'), row: r });
        r.indicators.forEach(function (ind) {
          if (!rules.some(function (q) { return (q.inputs || []).indexOf(ind.code) >= 0; })) return;
          out.push({ value: r.id + ':' + ind.code, label: ind.label, row: Object.assign({}, r, { label: ind.label, indicators: [ind], default: [ind.code] }) });
        });
      });
      (b.catalogue || []).forEach(function(r){if(!out.some(function(f){return f.value===r.id;}))out.push({value:r.id,label:r.label,row:r});});
      return out;
    },
    BL_ROW_LIMITS: { m: 5, c: 15 },
    blSlots: function (kind) {
      var b = LIVE.blGet(), sel = LIVE.blSel(), defaults = (kind === 'm' ? b.main : b.clues).map(function (r) { return r.id || r.key; });
      if (!defaults.length) defaults = LIVE.blFields(kind).slice(0, 2).map(function(f){return 'main-' + f.value;});
      var saved = (sel._rows || {})[kind];
      var slots = Array.isArray(saved) ? saved.filter(function (id, i) { return typeof id === 'string' && id.length > 0 && saved.indexOf(id) === i; }) : defaults;
      if (kind === 'm') slots = slots.filter(function (id) { return (id !== 'level' && id !== 'dyn') || LIVE.blFields('m').some(function (f) { return f.value === (sel._fields || {})['m|' + id]; }); });
      return (slots.length ? slots : defaults.slice(0, 1)).slice(0, LIVE.BL_ROW_LIMITS[kind]);
    },
    blRows: function (kind) {
      var b = LIVE.blGet(), sel = LIVE.blSel(), fields = LIVE.blFields(kind), defaults = kind === 'm' ? b.main : b.clues;
      return LIVE.blSlots(kind).map(function (id) {
        var r = defaults.filter(function (x) { return (x.id || x.key) === id; })[0];
        var chosen = (sel._fields || {})[kind + '|' + id];
        var f = fields.filter(function (x) { return x.value === chosen; })[0];
        if (!f && !r) f = fields.filter(function(x){return x.value===id || (kind==='m' && 'main-'+x.value===id);})[0] || fields[0];
        return f ? Object.assign({}, f.row, { id: id, fieldValue: f.value, originId: f.row.id }) : r;
      }).filter(Boolean);
    },
    blResize: function (kind, delta) {
      if (!LIVE.BL_ROW_LIMITS[kind] || (delta !== 1 && delta !== -1)) return;
      var slots = LIVE.blSlots(kind), sel = LIVE.blSel(), fields = LIVE.blFields(kind);
      if ((delta > 0 && (slots.length >= LIVE.BL_ROW_LIMITS[kind] || !fields.length)) || (delta < 0 && slots.length <= 1)) return;
      sel._fields = sel._fields || {};
      if (delta > 0) {
        var used = LIVE.blRows(kind).map(function (r) { return r.fieldValue || r.id || r.key; });
        var f = fields.filter(function (x) { return used.indexOf(x.value) < 0; })[0] || fields[0];
        var n = 1, id;
        do { id = 'extra-' + kind + '-' + n++; } while (slots.indexOf(id) >= 0);
        slots.push(id); sel._fields[kind + '|' + id] = f.value;
      } else {
        var removed = slots.pop(); delete sel[removed]; delete sel._fields[kind + '|' + removed];
      }
      sel._rows = sel._rows || {}; sel._rows[kind] = slots;
      LIVE.blSel(sel); C.st.blRegion = null; LIVE.renderAdvanced();
    },
    blDay: function (tp) { var y = String(new Date().getFullYear()); return String(tp).slice(0, 4) === y ? String(tp).slice(5) : String(tp); },
    blGap: function (a, z) { var d = Math.round(Math.abs(Date.parse(z) - Date.parse(a)) / 86400000); return d >= 365 ? '隔 ' + (d / 365).toFixed(1) + ' 年' : d === 0 ? '同一天' : '隔 ' + d + ' 天'; },
    blVal: function (r) { return r.bool ? (r.value === 'true' ? '有' : '未见') : (r.comparator || '') + r.value; },
    /* 一行一侧选中的东西：主状态 → 时点结果；线索 → [{指标, 记录}] */
    blPick: function (kind, row, side) {
      var s = (LIVE.blSel()[row.id || row.key] || {})[side] || {};
      if (kind === 'm' && !row.metric) { var n = row.options.length, i = s.i != null && s.i < n ? s.i : (side === 'base' ? 0 : n - 1); return { i: i, o: row.options[i] }; }
      var codes = (s.codes || row.default).filter(function (c) { return row.indicators.some(function (x) { return x.code === c; }); });
      if (!codes.length) codes = row.default;
      return codes.map(function (c) {
        var ind = row.indicators.filter(function (x) { return x.code === c; })[0], rs = ind.records, ref = (s.refs || {})[c];
        var r = rs.filter(function (x) { return x.ref === ref; })[0] || (side === 'base' ? rs[0] : rs[rs.length - 1]);
        return { ind: ind, r: r };
      });
    },
    blOffset: function (kind, row) {
      var b = LIVE.blPick(kind, row, 'base'), d = LIVE.blPick(kind, row, 'dev');
      if (kind === 'm' && !row.metric) {
        var gap = LIVE.blGap(b.o.tp, d.o.tp), A = b.o.state || b.o.text, B = d.o.state || d.o.text;
        if (b.o.num != null && d.o.num != null) { var df = (+d.o.num) - (+b.o.num); return { text: (df > 0 ? '↑ ' : df < 0 ? '↓ ' : '→ ') + Math.abs(df).toFixed(2).replace(/\.?0+$/, ''), gap: gap, tone: d.o.tone }; }
        return { text: A === B ? '没变' : A + ' → ' + B, gap: gap, tone: A === B ? 'none' : d.o.tone };
      }
      return LIVE.blComparePicks(row, b, d);
    },
    blComparePicks: function (row, b, d) {
      var parts = [], tones = [], gaps = {};
      d.forEach(function (x) {
        var y = b.filter(function (z) { return z.ind.code === x.ind.code; })[0]; if (!y) return;
        if (y.r.ref === x.r.ref) { parts.push(x.ind.label + ' 两侧为同一条记录'); tones.push('none'); return; }
        gaps[LIVE.blGap(y.r.tp, x.r.tp)] = 1;
        if (x.r.bool) { parts.push(y.r.value === x.r.value ? x.ind.label + ' 没变' : x.ind.label + ' ' + LIVE.blVal(y.r) + ' → ' + LIVE.blVal(x.r)); tones.push(x.r.value === 'true' ? 'small' : 'none'); return; }
        if (x.r.unit !== y.r.unit || x.r.source_kind !== y.r.source_kind) { parts.push(x.ind.label + ' 来源或单位不同，不计算偏移'); tones.push('none'); return; }
        var a = +y.r.value, z = +x.r.value;
        if (!Number.isFinite(a) || !Number.isFinite(z)) { parts.push(x.ind.label + ' 数值无法比较'); tones.push('none'); return; }
        if (!a || y.r.comparator || x.r.comparator) { parts.push(x.ind.label + ' ' + LIVE.blVal(y.r) + ' → ' + LIVE.blVal(x.r)); tones.push('small'); return; }
        var pc = Math.round((z - a) / Math.abs(a) * 100), th = row.thresholds[x.ind.code];
        parts.push(x.ind.label + ' ' + (pc > 0 ? '↑' : pc < 0 ? '↓' : '→') + Math.abs(pc) + '%');
        tones.push(th != null && Math.abs(pc) / 100 >= +th ? 'big' : pc < 0 ? 'down' : pc > 0 ? 'small' : 'none');
      });
      if (!parts.length) return { text: '无记录', gap: '', tone: 'empty' };
      return { text: parts.join(' · '), gap: Object.keys(gaps).join(' / '), tone: ['big', 'down', 'small', 'none'].filter(function (t) { return tones.indexOf(t) >= 0; })[0] };
    },
    blCellText: function (kind, pick) {
      if (kind === 'm') return { text: pick.o.text, day: LIVE.blDay(pick.o.tp), tone: pick.o.tone };
      if (!pick.length) return { text: '无记录', day: '', tone: 'empty' };
      var days = {}; pick.forEach(function (x) { days[LIVE.blDay(x.r.tp)] = 1; });
      var one = Object.keys(days).length === 1;
      return { text: pick.map(function (x) { return x.ind.label + ' ' + LIVE.blVal(x.r) + (one ? '' : ' ' + LIVE.blDay(x.r.tp)); }).join(' · '), day: one ? Object.keys(days)[0] : '',
        tone: pick.some(function (x) { return x.r.bool ? x.r.value === 'true' : true; }) ? 'small' : 'none' };
    },
    // Resolve the actual selected codes, never the row slot, label or group default.
    blBodyRegions: function () {
      var b = LIVE.blGet(), map = b.body_map || {}, B = window.PTDS_BODY || {}, groups = {};
      var compatible = map.asset_id === B.asset_id && map.asset_version === B.asset_version;
      LIVE.blRows('c').forEach(function (row) {
        var base = LIVE.blPick('c', row, 'base'), dev = LIVE.blPick('c', row, 'dev'), selected = {};
        base.concat(dev).forEach(function (p) { selected[p.ind.code] = p.ind; });
        Object.keys(selected).forEach(function (code) {
          var ind = selected[code], binding = ind.body_binding || {}, ids = binding.version === map.version && binding.code === code ? binding.region_ids || [] : [];
          var a = base.filter(function (p) { return p.ind.code === code; }), d = dev.filter(function (p) { return p.ind.code === code; });
          var off = a.length && d.length ? LIVE.blComparePicks(row, a, d) : {tone:'empty',text:'缺少一侧记录'};
          if (!ids.length) ids = ['unlocated'];
          ids.forEach(function (id) {
            var region = (map.regions || {})[id], valid = region && (region.scope === 'systemic' || (compatible && region.scope === 'anatomical' && (region.anchor_ids || []).length && region.anchor_ids.every(function (x) { return B.anchors && B.anchors[x]; }) && B.labelAnchors && B.labelAnchors[region.label_anchor]));
            if (!valid) { id = 'unlocated'; region = {label:'未定位',scope:'unmapped',anchor_ids:[]}; }
            if (!groups[id]) groups[id] = {id:id,region:region,members:[],rows:[]};
            var g = groups[id], signature = JSON.stringify([code,a.map(function(p){return p.r.ref;}),d.map(function(p){return p.r.ref;})]);
            var member = g.members.filter(function (m) { return m.signature === signature; })[0];
            if (!member) { member = {signature:signature,code:code,label:ind.label,tone:off.tone,text:off.text,rows:[]}; g.members.push(member); }
            if (member.rows.indexOf(row.id) < 0) member.rows.push(row.id);
            if (g.rows.indexOf(row.id) < 0) g.rows.push(row.id);
          });
        });
      });
      return Object.keys(groups).map(function (id) {
        var g = groups[id], tones = g.members.map(function (m) { return m.tone; });
        g.tone = ['big','down','small','none','empty'].filter(function (t) { return tones.indexOf(t) >= 0; })[0] || 'empty';
        g.incomplete = tones.indexOf('empty') >= 0;
        return g;
      });
    },
    blBodyHtml: function (groups) {
      var esc = C.esc, B = window.PTDS_BODY, T = LIVE.BL_TONE, st = C.st;
      if (!B) return '<div class="sub2" data-ptds-ui="s0a2d874211fe">人体图没有装上</div>';
      var grad = '<linearGradient id="bs-fill" x1="0" y1="15" x2="0" y2="547" gradientUnits="userSpaceOnUse">' + B.stops.map(function (s) { return '<stop offset="' + s[0] + '" stop-color="' + s[1] + '"/>'; }).join('') + '</linearGradient>' +
        Object.keys(T).map(function (k) { return '<radialGradient id="bs-g-' + k + '"><stop offset="0" stop-color="' + T[k] + '" stop-opacity=".75"/><stop offset="1" stop-color="' + T[k] + '" stop-opacity="0"/></radialGradient>'; }).join('');
      var description = function (g) { return g.members.map(function (m) { return m.text; }).join('；'); };
      var spots = groups.filter(function (g) { return g.region.scope === 'anatomical'; }).map(function (g) {
        var t = g.tone, pts = g.region.anchor_ids.map(function (a) { return B.anchors[a]; }), p0 = pts[0], label = B.labelAnchors[g.region.label_anchor], left = label[0] < 130;
        return '<g class="spot' + (st.blRegion === g.id ? ' hl' : '') + '"><title>' + esc(description(g)) + '</title><g data-bl-region="' + esc(g.id) + '">' +
          pts.map(function (p) { return '<circle cx="' + p[0] + '" cy="' + p[1] + '" r="' + (pts.length > 1 ? 14 : 24) + '" fill="url(#bs-g-' + t + ')"/><circle cx="' + p[0] + '" cy="' + p[1] + '" r="2.6" fill="' + T[t] + '"/>'; }).join('') + '</g>' +
          '<line x1="' + p0[0] + '" y1="' + p0[1] + '" x2="' + (left ? 45 : label[0] - 4) + '" y2="' + label[1] + '" stroke="' + T[t] + '" stroke-opacity=".6" stroke-width="1"/>' +
          '<g data-bl-region="' + esc(g.id) + '" role="button" tabindex="0" aria-label="' + esc(g.region.label + '：' + g.members.map(function (m) { return m.label; }).join('、')) + '"><rect x="' + (label[0] - 2) + '" y="' + (label[1] - 15) + '" width="' + (g.region.label.length * 18 + (g.incomplete ? 18 : 0) + 4) + '" height="30" fill="transparent"/><text x="' + label[0] + '" y="' + (label[1] + 7) + '" style="font-size:18px">' + esc(g.region.label) + (g.incomplete ? '＊' : '') + '</text></g></g>';
      }).join('');
      var systemic = groups.filter(function (g) { return g.region.scope !== 'anatomical'; }).map(function (g) {
        return '<button class="bl-region' + (st.blRegion === g.id ? ' hl' : '') + '" data-bl-region="' + esc(g.id) + '" title="' + esc(description(g)) + '"><b>' + esc(g.region.label) + '</b> · ' + g.members.map(function (m) { return '<span><i style="background:' + T[m.tone] + '"></i>' + esc(m.label) + (m.tone === 'empty' ? '（待比较）' : '') + '</span>'; }).join('、') + '<small>' + (g.region.scope === 'systemic' ? '全身指标，不定位到单一器官' : '暂无匹配位置') + '</small></button>';
      }).join('');
      return '<svg class="bl-svg" viewBox="' + B.viewBox + '" style="width:100%;max-height:460px" role="img" aria-label="人体正面轮廓，按所选指标自动绑定"><defs>' + grad + '</defs>' +
        '<path id="bs-body" d="' + B.d + '" fill="url(#bs-fill)" stroke="rgba(140,196,255,0.25)" stroke-width="1" stroke-linejoin="round"/>' + spots + '</svg><div class="bl-systemic">' + systemic + '</div>';
    },
    blSummarySelection: function () {
      var rows = [];
      ['m', 'c'].forEach(function (kind) { LIVE.blRows(kind).forEach(function (r) {
        var row = {kind: r.metric ? 'c' : kind, field: r.fieldValue || r.key || r.id};
        ['base', 'dev'].forEach(function (side) {
          var p = LIVE.blPick(kind, r, side);
          row[side] = row.kind === 'm' ? {tp:p.o.tp, run_id:p.o.run_id} : p.map(function (x) { return {code:x.ind.code, ref:x.r.ref}; });
        }); rows.push(row);
      }); });
      return {key:C.st.key, rows:rows};
    },
    blSummarySignature: function () {
      return JSON.stringify([LIVE.blSummarySelection(), LIVE.blGet()]);
    },
    blSummaryOpen: function () {
      C.closeDrawer(); C.st.drawer = 'live';
      var drawer = document.createElement('aside');
      drawer.id = 'drawer'; drawer.className = 'drawer bl-summary-drawer';
      drawer.setAttribute('role', 'dialog'); drawer.setAttribute('aria-modal', 'false'); drawer.setAttribute('aria-label', '星灵 · 当前状态');
      drawer.innerHTML = '<div class="dh"><span><span class="sp-ic on">' + C.ic('sparkles') + '</span> 星灵 · 当前状态</span><button class="ibtn" id="bl-summary-retry" aria-label="重新总结" title="重新总结" data-ptds-ui-aria-label="sb83496f5e2f8" data-ptds-ui-title="sb83496f5e2f8">' + C.ic('refresh-cw') + '</button><button class="ibtn" id="dclose" aria-label="关闭星灵" data-ptds-ui-aria-label="s6de3fe3488e4">' + C.ic('x') + '</button></div><div class="db"><div id="bl-summary" tabindex="0" aria-live="polite"></div></div>';
      var close = function () {
        drawer.remove(); C.st.drawer = null; clearTimeout(LIVE._blSummaryTimer); LIVE._blSummaryTimer = null;
        if (C.st.blSummary && !C.st.blSummary.sent) C.st.blSummary = null;
        var trigger = document.getElementById('bl-summary-go'); if (trigger) trigger.focus();
      };
      document.body.append(drawer);
      drawer.querySelector('#dclose').onclick = LIVE.action(close);
      drawer.querySelector('#bl-summary-retry').onclick = LIVE.blSummaryAsk;
      drawer.addEventListener('keydown', function (ev) {
        if (ev.key === 'Escape') { ev.preventDefault(); close(); }

      });
      drawer.querySelector('#dclose').focus(); LIVE.blSummaryAsk(); LIVE.blSummaryPaint();
    },
    blSummaryPaint: function () {
      var el = document.getElementById('bl-summary'), job = C.st.blSummary;
      if (!el || !job) return;
      var retry = document.getElementById('bl-summary-retry');
      if (job.signature !== LIVE.blSummarySignature()) {
        if (retry) retry.disabled = false; el.setAttribute('aria-busy', 'false');
        el.innerHTML = '<div role="status" class="bl-thinking" data-ptds-ui="s6eea36528068">选择已更新，星灵正在思考…</div>'; return;
      }
      var r = job.result, esc = C.esc;
      if (retry) retry.disabled = r.state === 'running';
      el.setAttribute('aria-busy', String(r.state === 'running'));
      if (r.state === 'running') { el.innerHTML = '<div role="status" class="bl-thinking"><span class="sp-ic on">' + C.ic('sparkles') + '</span><div data-ptds-inline><!--ptds-ui:s2e16fd13c7c0-->星灵正在思考…<!--/ptds-ui--><div class="sub2" data-ptds-ui="sfad6c83ede52">正在总结当前选中的状态和指标</div></div></div>'; return; }
      if (r.state !== 'ok') { el.innerHTML = '<div role="status" class="sub2">' + esc(r.why || (r.state === 'no_llm' ? '本地星灵未运行，本次未生成总结。' : '本次总结未通过核对，请重试。')) + '</div>'; return; }
      if (!Array.isArray(r.brief) || r.brief.length !== 3) { el.innerHTML = '<div class="sub2" data-ptds-ui="sfee1737fba1c">摘要格式需要更新，请重新总结。</div>'; return; }
      var emphasize = function (text) { return esc(text).replace(/([-+]?\d+(?:\.\d+)?%?)/g, '<strong>$1</strong>'); };
      el.innerHTML = '<div class="sub2">' + esc(r.by) + '</div><ol class="bl-brief">' + r.brief.map(function (point) {
        return '<li><b>' + esc(point.title) + '：</b>' + '<p style="display:inline">' + emphasize(point.text) + '</p></li>';
      }).join('') + '</ol><details class="bl-summary-evidence"><summary class="sub2" data-ptds-ui="s81308942a4fb">查看依据与完整记录</summary><div class="sub2">' + esc(r.method) + '</div>' + r.sections.map(function (section) {
        return '<div style="margin-top:10px"><b>' + esc(section.title) + '</b>' + section.items.map(function (item) {
          return '<p>' + emphasize(item.detail || item.text) + (item.refs.length ? '<br><span class="sub2">' + item.refs.map(function (ref) { return esc((ref.tp ? '记录日期：' + ref.tp : '') + (ref.run_id != null ? ' · 计算批次：' + ref.run_id : '') + (ref.ref ? ' · 记录版本：' + String(ref.ref).split('@').pop() : '')); }).join('<br>') + '</span>' : '') + '</p>';
        }).join('') + '</div>';
      }).join('') + '</details>';
    },
    // One request at a time; rapid selection changes replace the pending snapshot.
    blSummarySync: function (force) {
      if (!document.getElementById('bl-summary')) return;
      var signature = LIVE.blSummarySignature(), old = C.st.blSummary;
      if (old && old.signature === signature && (!force || old.result.state === 'running')) { LIVE.blSummaryPaint(); return; }
      var selection = JSON.stringify(LIVE.blSummarySelection());
      C.st.blSummary = {selection:selection,signature:signature,result:{state:'running'},sent:false};
      LIVE.blSummaryPaint(); clearTimeout(LIVE._blSummaryTimer);
      LIVE._blSummaryTimer = setTimeout(function () { LIVE._blSummaryTimer = null; LIVE.blSummaryRun(); }, 350);
    },
    blSummaryAsk: function () { LIVE.blSummarySync(true); },
    blSummaryRun: function () {
      if (LIVE._blSummaryInFlight || !document.getElementById('bl-summary')) return;
      var job = C.st.blSummary; if (!job || job.sent) return;
      job.sent = true; LIVE._blSummaryInFlight = job;
      fetch('/api/starling/baseline', {method:'POST',headers:{'Content-Type':'application/json','X-PTDS':'1'},body:job.selection})
        .then(function (r) { return r.json(); }).then(function (res) {
          if (C.st.blSummary === job && job.signature === LIVE.blSummarySignature()) job.result = res;
        }).catch(function () { if (C.st.blSummary === job) job.result = {state:'error',why:'连不上本机服务，本次未生成总结。'}; })
        .finally(function () {
          LIVE._blSummaryInFlight = null;
          if (!document.getElementById('bl-summary')) return;
          LIVE.blSummarySync();
          if (C.st.blSummary !== job && !C.st.blSummary.sent && !LIVE._blSummaryTimer) LIVE.blSummaryRun();
        });
    },
    baselineHtml: function () {
      var esc = C.esc, st = C.st, b = LIVE.blGet(), T = LIVE.BL_TONE;
      if (!document.getElementById('bl-css')) { var s0 = document.createElement('style'); s0.id = 'bl-css'; s0.textContent = LIVE.BL_CSS; document.head.appendChild(s0); }
      if(b&&b.why==='LOADING')return '<section class="box">'+LIVE.readingHtml('compact')+'</section>';
      if(b&&b.found&&!(b.catalogue||[]).length&&!(b.main||[]).length)return '<section class="box"><div class="sub2" data-ptds-ui="sc9d33ad3bc5a">当前场景还没有可比较的记录。接入设备或导入数据后，可在主状态与状态线索中添加指标。</div></section>';
      if(b&&b.why==='READ_UNAVAILABLE')return '<section class="box">'+LIVE.readingHtml('compact','error','暂时无法读取状态偏移，请稍后重新打开。')+'</section>';
      if (!b || !b.found) return '<section class="box"><div class="sub2">' + (b && b.why === 'NO_TIMEPOINTS' ? '这份数据里还没有算过的时点。' : '当前场景尚无可比较的记录。') + '</div></section>';
      var mark = function (r) {
        if (!r.rule && r.mark !== '患') return '<span class="sub2" title="原始观测比较，没有医学阈值判定" data-ptds-ui-title="s35a1a11473aa" data-ptds-ui="sb47316c00878">观测</span>';
        return r.mark === '患' ? '<button class="bl-mk pt" data-bl-pt="' + esc(r.originId || r.id || '') + '" title="' + esc(r.id ? '你在本页自己定的偏离阈值，点开修改或恢复规则' : '按你在本页定的阈值重算（只给这一页看）：' + (r.patient_codes || []).join('、')) + '">患</button>'
          : '<button class="bl-mk" data-bl-rule="' + esc(r.rule) + '" title="有文献出处的规则，仍待专家核实">规</button>';
      };
      var bodyRegions = LIVE.blBodyRegions(), activeRegion = bodyRegions.filter(function (g) { return g.id === st.blRegion; })[0];
      var highlighted = activeRegion ? activeRegion.rows : [];
      var row = function (kind, r) {
        var id = r.id || r.key, off = LIVE.blOffset(kind, r);
        var fields = LIVE.blFields(kind), value = r.fieldValue || id;
        var selector = '<select data-bl-field="' + kind + '|' + esc(id) + '" aria-label="选择' + esc(r.label) + '字段" style="max-width:145px;width:100%;background:var(--theme-surface-raised);color:inherit;border:1px solid var(--theme-line-control);border-radius:6px;padding:4px;font:inherit">' + fields.map(function (f) { return '<option value="' + esc(f.value) + '"' + (f.value === value ? ' selected' : '') + '>' + esc(f.label) + '</option>'; }).join('') + '</select>';
        var cell = function (side) { var c = LIVE.blCellText(r.metric ? 'c' : kind, LIVE.blPick(kind, r, side)); return '<span><button class="bl-p t-' + c.tone + '" style="--bl-c:' + T[c.tone] + '" data-bl-pick="' + kind + '|' + esc(id) + '|' + side + '">' + esc(c.text) + (c.day ? '<span class="d">' + esc(c.day) + '</span>' : '') + ' ▾</button></span>'; };
        return '<span class="lb' + (kind === 'c' && highlighted.indexOf(id) >= 0 ? ' hl' : '') + '">' + selector + mark(r) + '</span>' + cell('base') + cell('dev') +
          '<span><button class="bl-p t-' + off.tone + '" style="--bl-c:' + T[off.tone] + '" data-bl-off="' + kind + '|' + esc(id) + '">' + esc(off.text) + (off.gap ? '<span class="d">' + esc(off.gap) + '</span>' : '') + '</button></span>';
      };
      var group = function (kind, label) {
        var rs = LIVE.blRows(kind), max = LIVE.BL_ROW_LIMITS[kind];
        return '<span class="sec bl-group"><span>' + label + ' <small>' + rs.length + ' / ' + max + '</small></span><span class="bl-count-controls"><button type="button" data-bl-resize="' + kind + '|-1" aria-label="减少' + label + '" title="移除最后一项"' + (rs.length <= 1 ? ' disabled' : '') + '>−</button><button type="button" data-bl-resize="' + kind + '|1" aria-label="增加' + label + '" title="增加一项"' + (rs.length >= max ? ' disabled' : '') + '>＋</button></span></span>' + rs.map(function (r) { return row(kind, r); }).join('');
      };
      var rows = group('m', '主状态') + group('c', '状态线索');
      var table = '<div class="bl-t"><span class="hd"></span><span class="hd" data-ptds-ui="s199b09248000">基线状态</span><span class="hd" data-ptds-ui="s7ef0c0a73aec">发展状态</span><span class="hd" data-ptds-ui="s56011581c078">偏移情况</span>' + rows + '</div>';
      return '<div class="bl"><section class="box"><div class="sub2" data-ptds-ui="s169cbcb3bdda">发展状态 · 对比基线</div>' + LIVE.blBodyHtml(bodyRegions) +
        '<div class="bl-lg"><span><i style="background:' + T.big + '"></i>偏离大</span><span><i style="background:' + T.small + '"></i>有记录 / 小偏离</span><span><i style="background:' + T.down + '"></i>降低</span><span><i style="background:' + T.none + '"></i>无变化 / 待比较</span></div>' +
        '<div class="sub2" style="margin-top:6px" data-ptds-ui="sef4dfa7545c3">位置随右侧所选指标自动更新。点标记可高亮对应行；＊表示缺少比较记录。颜色表示偏移，不代表病灶。</div></section>' +
        '<div><section class="box" style="position:relative" id="bl-box"><div style="display:flex;justify-content:flex-end;margin-bottom:8px"><button class="sp-btn" id="bl-summary-go" aria-label="星灵总结当前状态" title="星灵总结当前状态" data-ptds-ui-aria-label="s5a753dd376ba" data-ptds-ui-title="s5a753dd376ba"><span class="sp-ic">' + C.ic('sparkles') + '</span></button></div>' + '<div class="sub2">'+esc(b.summary || '')+' 自选项目仅作为当前浏览器的场景偏好保存。</div>' + table +
        '<div class="sub2" style="margin-top:10px" data-ptds-inline><!--ptds-ui:s2efacb919cbe-->每一格单独选：点开换指标、换用哪一次的值，格子里标出这个值的日期；偏移那列写两者相隔多久。点任意一格看来源和「这个数是怎么来的」。<!--/ptds-ui--><span class="bl-mk" data-ptds-ui="s07986adb7982">规</span> 为有出处、待专家核实的规则；观测仅比较记录，<span class="bl-mk pt" data-ptds-ui="s25f612e055c9">患</span> 用的是你在本页自己定的规则（点「患」修改）。</div></section></div></div>';
    },
    bindBaseline: function () {
      var st = C.st, b = LIVE.blGet(); if (!b || !b.found) return;
      var rowOf = function (kind, id) { return LIVE.blRows(kind).filter(function (x) { return (x.id || x.key) === id; })[0]; };
      var g = function (id, fn) { var e = document.getElementById(id); if (e) e.onclick = LIVE.action(fn); };
      document.querySelectorAll('[data-bl-field]').forEach(function (e) { e.onchange = function () {
        var p = e.dataset.blField.split('|'), sel = LIVE.blSel();
        if (!LIVE.blFields(p[0]).some(function (f) { return f.value === e.value; })) return;
        sel._fields = sel._fields || {}; sel._fields[e.dataset.blField] = e.value;
        delete sel[p[1]]; st.blRegion = null; LIVE.blSel(sel); LIVE.renderAdvanced();
      }; });
      document.querySelectorAll('[data-bl-resize]').forEach(function (e) { e.onclick = function () { var p = e.dataset.blResize.split('|'); LIVE.blResize(p[0], +p[1]); }; });
      g('bl-summary-go', LIVE.blSummaryOpen); LIVE.blSummarySync();
      g('bl-reset', function () { LIVE.blSel({}); LIVE.renderAdvanced(); });
      document.querySelectorAll('[data-bl-rule]').forEach(function (e) { e.onclick = function (ev) { ev.stopPropagation(); LIVE.goRule('MAS', e.dataset.blRule); }; });
      document.querySelectorAll('[data-bl-pt]').forEach(function (e) { e.onclick = function (ev) {
        ev.stopPropagation(); var id = e.dataset.blPt || ((b.clues.filter(function (c) { return c.mark === '患'; })[0] || {}).id); if (id) LIVE.blRuleEdit(id); }; });
      var hl = function (id) { st.blRegion = st.blRegion === id ? null : id; LIVE.renderAdvanced(); };
      document.querySelectorAll('[data-bl-region]').forEach(function (e) { e.onclick = function () { hl(e.dataset.blRegion); }; if (e.tagName.toLowerCase() !== 'button') e.onkeydown = function (ev) { if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); hl(e.dataset.blRegion); } }; });
      document.querySelectorAll('[data-bl-pick]').forEach(function (e) { e.onclick = function () { var p = e.dataset.blPick.split('|'); LIVE.blPicker(e, p[0], rowOf(p[0], p[1]), p[2]); }; });
      document.querySelectorAll('[data-bl-off]').forEach(function (e) { e.onclick = function () { var p = e.dataset.blOff.split('|'); LIVE.blCellOpen(p[0], rowOf(p[0], p[1])); }; });
    },
    /* 选择器：(a) 指标（可多选，格子里最多放 2 个）(b) 用哪一次的值（日期 + 值 + 来源） */
    blPicker: function (anchor, kind, row, side) {
      var esc = C.esc, old = document.getElementById('bl-pk'); if (old) old.remove();
      var id = row.id || row.key, sel = LIVE.blSel(), cur = (sel[id] || {})[side] || {};
      var el = document.createElement('div'); el.id = 'bl-pk'; el.className = 'bl-pk'; el.setAttribute('role', 'dialog');
      var draw = function () {
        var h = '<div style="display:flex;align-items:center;gap:8px"><b>' + esc(row.label) + ' · ' + (side === 'base' ? '基线状态' : '发展状态') + '</b><span class="grow" style="flex:1"></span><button class="ibtn" data-pk-x="1" aria-label="关闭" data-ptds-ui-aria-label="s3fd47edce45b">' + C.ic('x') + '</button></div>';
        if (kind === 'm' && !row.metric) {
          var pk = LIVE.blPick(kind, row, side);
          h += '<div class="sub2" style="margin:6px 0" data-ptds-ui="s70fc02817eb2">用哪一次的结果</div>' + row.options.map(function (o, i) { return '<div class="rec" data-pk-i="' + i + '"><span>' + (i === pk.i ? '●' : '○') + '</span><span>' + esc(o.tp) + '</span><span>' + esc(o.text) + '</span></div>'; }).join('');
        } else {
          var picks = LIVE.blPick(kind, row, side), codes = picks.map(function (x) { return x.ind.code; });
          h += '<div class="sub2" style="margin-top:6px" data-ptds-ui="sa3c71c67f693">指标（最多选 2 个）</div><div class="ch">' + row.indicators.map(function (x) { return '<button class="chip" data-pk-code="' + esc(x.code) + '" aria-pressed="' + (codes.indexOf(x.code) >= 0) + '">' + esc(x.label) + '</button>'; }).join('') + '</div>' +
            picks.map(function (p) { return '<div class="sub2" style="margin:8px 0 2px">' + esc(p.ind.label) + ' · 用哪一次的值</div>' + p.ind.records.map(function (r) {
              return '<div class="rec" data-pk-ref="' + esc(p.ind.code + '|' + r.ref) + '"><span>' + (r.ref === p.r.ref ? '●' : '○') + '</span><span>' + esc(r.tp) + ' · ' + esc(LIVE.blVal(r)) + (r.unit && !r.bool ? ' ' + esc(r.unit) : '') + '</span><span class="sub2">' + esc(r.source) + '</span></div>'; }).join(''); }).join('');
        }
        h += '<div style="display:flex;gap:10px;margin-top:10px"><button class="link" data-pk-src="1" data-ptds-ui="s8c5922d0ae91">看来源和「这个数是怎么来的」</button><span class="grow" style="flex:1"></span><button class="link" data-pk-reset="1" data-ptds-ui="sb174fd0081ca">这一格恢复默认</button></div>';
        el.innerHTML = h;
        el.querySelector('[data-pk-x]').onclick = function () { el.remove(); };
        el.querySelector('[data-pk-reset]').onclick = function () { var s = LIVE.blSel(); if (s[id]) delete s[id][side]; LIVE.blSel(s); el.remove(); LIVE.renderAdvanced(); };
        el.querySelector('[data-pk-src]').onclick = function () { el.remove(); LIVE.blCellOpen(kind, row, side); };
        var save = function (patch) { var s = LIVE.blSel(); s[id] = s[id] || {}; s[id][side] = Object.assign({}, s[id][side] || {}, patch); LIVE.blSel(s); LIVE.renderAdvanced(); var a = document.querySelector('[data-bl-pick="' + kind + '|' + id + '|' + side + '"]'); if (a) LIVE.blPicker(a, kind, row, side); };
        el.querySelectorAll('[data-pk-i]').forEach(function (x) { x.onclick = function () { save({ i: +x.dataset.pkI }); }; });
        el.querySelectorAll('[data-pk-code]').forEach(function (x) { x.onclick = function () {
          var cs = LIVE.blPick(kind, row, side).map(function (p) { return p.ind.code; }), c = x.dataset.pkCode, i = cs.indexOf(c);
          if (i >= 0) { if (cs.length > 1) cs.splice(i, 1); } else { cs.push(c); if (cs.length > 2) cs.shift(); }
          save({ codes: cs }); }; });
        el.querySelectorAll('[data-pk-ref]').forEach(function (x) { x.onclick = function () { var p = x.dataset.pkRef.split('|'), refs = Object.assign({}, cur.refs || {}, ((LIVE.blSel()[id] || {})[side] || {}).refs || {}); refs[p[0]] = p[1]; save({ refs: refs }); }; });
      };
      draw();
      document.body.appendChild(el);  /* 挂在页面上，不被卡片裁掉 */
      var ra = anchor.getBoundingClientRect(), left = Math.min(ra.left + window.scrollX, window.scrollX + document.documentElement.clientWidth - 356);
      el.style.left = Math.max(8, left) + 'px'; el.style.top = (ra.bottom + window.scrollY + 6) + 'px';
    },
    /* 本人规则编辑（只在这一页）：点身体部位或「患」打开；每个数值指标填“变化超过多少算偏离大”，起始值是已发布的阈值。
       保存 = 追加一个版本（startorch/patient_rules.jsonl）；恢复规则 = 追加撤回。别处的发布结果不变。 */
    blRuleEdit: function (cid) {
      var esc = C.esc, ic = C.ic, b = LIVE.blGet(), r = b.clues.filter(function (x) { return x.id === cid; })[0]; if (!r) return;
      if (!document.getElementById('fw-css')) { var s0 = document.createElement('style'); s0.id = 'fw-css'; s0.textContent = LIVE.FW_CSS + LIVE.GRAPH_CSS; document.head.appendChild(s0); }
      var old = document.getElementById('fw'); if (old) old.remove();
      var nums = r.indicators.filter(function (x) { return x.records.some(function (q) { return !q.bool; }); });
      var pct = function (t) { return t == null ? '' : String(Math.round(+t * 1000) / 10); };
      var hist = (r.history || []).slice().reverse().slice(0, 8);
      var html = '<div class="fh"><div class="k">' + esc(r.label) + ' · 本页的偏离阈值</div><div class="v">' + (r.mark === '患' ? '<span class="bl-mk pt" data-ptds-ui="s25f612e055c9">患</span> 用的是你自己定的' : '<span class="bl-mk" data-ptds-ui="s07986adb7982">规</span> 用的是已发布的规则') + '</div>' +
        '<button class="ibtn fx" id="fw-x" aria-label="关闭" data-ptds-ui-aria-label="s3fd47edce45b">' + ic('x') + '</button></div><div class="fb">' +
        (nums.length ? '<div class="sub2" style="margin-bottom:8px" data-ptds-ui="s3748d30b27bd">和基线比，变化超过这个幅度记为“偏离大”（红色）。只影响这一页，别处的结果不变。</div>' +
          nums.map(function (x) { var pub = r.published[x.code], cur = r.thresholds[x.code];
            return '<div style="display:grid;grid-template-columns:1fr 90px;gap:8px;align-items:center;margin:6px 0"><span>' + esc(x.label) + '<br><span class="sub2" data-ptds-inline><!--ptds-ui:s944a2852baaf-->发布的规则：<!--/ptds-ui-->' + (pub != null ? pct(pub) + '%' : '没有，按升 / 降上色') + '</span></span>' +
              '<label><input type="number" min="1" max="1000" step="1" data-bl-thr="' + esc(x.code) + '" value="' + esc(pct(cur != null ? cur : pub)) + '" style="width:64px"> %</label></div>'; }).join('')
          : '<div class="sub2" data-ptds-ui="s633c42b29458">这一类线索是“有 / 没有”，没有可以设的变化幅度。</div>') +
        (hist.length ? '<div class="nl" style="margin-top:14px" data-ptds-ui="s67fef6fe217c">修改记录</div>' + hist.map(function (h) { return '<div class="sub2">第 ' + h.version + ' 版 · ' + esc(C.tzTime(h.at).slice(5, 16)) + ' · ' + esc((r.indicators.filter(function (x) { return x.code === h.code; })[0] || {}).label || h.code) + ' ' + (h.threshold == null ? '恢复规则' : pct(h.threshold) + '%') + '</div>'; }).join('') : '') +
        '<div class="sub2" style="margin-top:12px" data-ptds-ui="s25e15c0034e7">研究演示，未经临床验证。</div></div>' +
        '<div class="ff">' + (nums.length ? '<button class="btn" id="bl-thr-save" data-ptds-ui="sa3030bf8f16d">保存</button>' : '') + (r.mark === '患' ? '<button class="btn2" id="bl-thr-reset" data-ptds-ui="s5832a6313ace">恢复规则</button>' : '') + '</div>';
      var el = document.createElement('aside'); el.id = 'fw'; el.setAttribute('role', 'dialog'); el.setAttribute('aria-label', r.label + ' 偏离阈值'); el.innerHTML = html; document.body.appendChild(el);
      var done = function (res) { LIVE._bl = { key: C.st.key, v: res.view }; LIVE.renderAdvanced(); LIVE.blRuleEdit(cid); };
      document.getElementById('fw-x').onclick = function () { el.remove(); };
      var sv = document.getElementById('bl-thr-save'); if (sv) sv.onclick = LIVE.action(async function () {
        var t = {}; el.querySelectorAll('[data-bl-thr]').forEach(function (x) { var v = x.value.trim(), c = x.dataset.blThr, pub = r.published[c];
          if (v === '') return; if (pub != null && Math.abs(+v - (+pub * 100)) < 1e-9 && r.thresholds[c] === pub) return; t[c] = +v; });
        if (!Object.keys(t).length) { C.toast('和发布的规则一样，没有要存的'); return; }
        try { done((await call('POST', '/api/track/baseline/rule', { key: C.st.key, clue: cid, thresholds: t }))); C.toast('已存为你自己的规则（只在这一页）'); } catch (err) { if(err&&(err.viewPending||err.code==='VIEW_CHANGED'))throw err; C.toast('没存上：' + LIVE.saveErr(err)); } });
      var rs = document.getElementById('bl-thr-reset'); if (rs) rs.onclick = LIVE.action(async function () {
        try { done((await call('POST', '/api/track/baseline/rule', { key: C.st.key, clue: cid, reset: true }))); C.toast('已恢复为发布的规则'); } catch (err) { if(err&&(err.viewPending||err.code==='VIEW_CHANGED'))throw err; C.toast('没恢复成：' + LIVE.saveErr(err)); } });
    },
    /* 证据小窗：选中的值从哪来、两边差多少、当天记录的症状和用药；再进原有的证据浮窗 / 星炬记录 */
    blCellOpen: function (kind, row, only) {
      var esc = C.esc, ic = C.ic, b = LIVE.blGet(), id = row.id || row.key;
      if (!document.getElementById('fw-css')) { var s0 = document.createElement('style'); s0.id = 'fw-css'; s0.textContent = LIVE.FW_CSS + LIVE.GRAPH_CSS; document.head.appendChild(s0); }
      var old = document.getElementById('fw'); if (old) old.remove();
      var sides = only ? [only] : ['base', 'dev'], ZH = { base: '基线状态', dev: '发展状态' }, tps = {}, refs = [];
      var dayHtml = function (tp) { var d = (b.days || {})[tp] || {}; return '<div class="sub2" style="line-height:1.8" data-ptds-inline><!--ptds-ui:s5b805ce3ad9d-->当天记录的症状：<!--/ptds-ui-->' + (d.symptoms && d.symptoms.length ? d.symptoms.map(esc).join('、') : '未记录') + '<br>当天的用药：' + (d.meds && d.meds.length ? d.meds.map(function (m) { return esc(m.drug + ' ' + m.dose + ' ' + m.unit + ' ' + m.route); }).join('；') : '未记录') + '</div>'; };
      var body = sides.map(function (side) {
        var p = LIVE.blPick(kind, row, side), h = '<div style="margin:8px 0 4px" class="nl">' + ZH[side] + '</div>';
        if (kind === 'm' && !row.metric) { tps[p.o.tp] = 1; return h + '<div><b>' + esc(p.o.text) + '</b> <span class="sub2">' + esc(p.o.tp) + ' · 星轨第 ' + esc(p.o.run_id) + ' 次计算</span></div>' + dayHtml(p.o.tp); }
        return h + p.map(function (x) { tps[x.r.tp] = 1; refs.push(x.r.ref); return '<div><b>' + esc(x.ind.label) + '</b> ' + esc(LIVE.blVal(x.r)) + (x.r.unit && !x.r.bool ? ' ' + esc(x.r.unit) : '') + ' <span class="sub2">' + esc(x.r.tp) + ' · ' + esc(x.r.source) +
          (x.r.raw_unit && x.r.raw_unit !== x.r.unit ? ' · 原值 ' + esc(x.r.raw + ' ' + x.r.raw_unit) : '') + '</span></div>'; }).join('') + dayHtml(p[0] ? p[0].r.tp : '');
      }).join('');
      var off = only ? null : LIVE.blOffset(kind, row);
      var masTps = ((b.main[0] || {}).options || []).map(function (o) { return o.tp; }), traceTp = Object.keys(tps).filter(function (t) { return masTps.indexOf(t) >= 0; }).pop();
      var html = '<div class="fh"><div class="k">' + esc(row.label) + (off ? ' · 偏移情况' : ' · ' + ZH[only]) + '</div><div class="v">' + esc(off ? off.text + (off.gap ? ' · ' + off.gap : '') : '') + '</div>' +
        '<button class="ibtn fx" id="fw-x" aria-label="关闭" data-ptds-ui-aria-label="s3fd47edce45b">' + ic('x') + '</button></div><div class="fb">' + body + '<div class="sub2" style="margin-top:12px">' + esc(b.note) + '</div></div>' +
        '<div class="ff">' + (kind === 'c' && !row.metric ? '<button class="btn2" id="bl-adjust" data-ptds-ui="s6d9cd9bab56c">调整偏移阈值</button>' : '') + (refs.length ? '<button class="btn2" id="bl-rec">' + ic('database') + ' 在星炬里看这条记录</button>' : '') + (traceTp ? '<button class="btn" id="bl-trace">' + ic('route') + ' 这个数是怎么来的</button>' : '') + '</div>';
      var el = document.createElement('aside'); el.id = 'fw'; el.setAttribute('role', 'dialog'); el.setAttribute('aria-label', row.label); el.innerHTML = html; document.body.appendChild(el);
      document.getElementById('fw-x').onclick = function () { el.remove(); };
      var adj = document.getElementById('bl-adjust'); if (adj) adj.onclick = function () { el.remove(); LIVE.blRuleEdit(row.originId || row.id); };
      var tr = document.getElementById('bl-trace'); if (tr) tr.onclick = function () { el.remove(); LIVE.openTrace('sjia-mas', traceTp); };
      var rc = document.getElementById('bl-rec'); if (rc) rc.onclick = function () { el.remove(); var st = C.st; st.tdetail = { ref: refs[refs.length - 1], mode: 'view', from: 'data' }; st.tview = 'detail'; window.__ptds.setSeg('data-app', 'torch'); C.render(); };
    },
    /* 铃铛 = 状态通知的入口（产品负责人 2026-10-15 批准 r52 示意稿）：左侧不再有“状态通知”；有未读时铃铛上红点 + 数字；
       点开从右侧滑出，放在页头下面不挡铃铛，未读在前，列最近 5 条；每条 知道了 / 加到日历 / 看依据 / 星灵讲讲；
       底部“查看全部”进完整历史页（带去问医生、各通道送达情况都在那里）。只显示本实例的提醒。 */
    BELL_CSS: '#bell{position:relative}#bell .bell-n{position:absolute;top:-3px;right:-5px;min-width:16px;height:16px;padding:0 4px;border-radius:8px;background:#E5675F;color:#fff;font-size:11px;line-height:16px;text-align:center;font-weight:600;pointer-events:none}' +
      '#bell-dr{position:fixed;top:84px;right:16px;bottom:16px;width:440px;max-width:calc(100vw - 32px);z-index:2000;display:flex;flex-direction:column;background:var(--theme-surface-raised);color:var(--theme-text-primary);' +
      'border:var(--primitive-border-hairline) solid var(--theme-line-control);border-radius:16px;box-shadow:0 18px 48px rgba(0,0,0,.28);animation:bdin var(--ptds-fade-duration,180ms) ease-in-out}' +
      '@keyframes bdin{from{opacity:0}to{opacity:1}}@media (prefers-reduced-motion: reduce){#bell-dr{animation:none}}' +
      '#bell-dr .bh{padding:14px 18px 10px;border-bottom:var(--primitive-border-hairline) solid var(--theme-line-hairline);display:flex;align-items:center;gap:10px}' +
      '#bell-dr .bb{padding:2px 18px;overflow:auto;flex:1}#bell-dr .bf{padding:12px 18px;border-top:var(--primitive-border-hairline) solid var(--theme-line-hairline);display:flex;align-items:center;gap:10px}' +
      '#bell-dr .bi{padding:12px 0;border-bottom:var(--primitive-border-hairline) solid var(--theme-line-hairline)}#bell-dr .bi:last-child{border-bottom:0}' +
      '#bell-dr .bt{display:flex;align-items:center;gap:8px}#bell-dr .ud{width:8px;height:8px;border-radius:50%;flex:none}#bell-dr .ud.on{background:#4f9dff}' +
      '#bell-dr .lv{padding:1px 8px;border-radius:6px;font-size:var(--scale-type-meta)}#bell-dr .lv.lv-ALERT{background:color-mix(in srgb,#E5675F 22%,transparent)}#bell-dr .lv.lv-WATCH{background:color-mix(in srgb,#E8B65A 22%,transparent)}' +
      '#bell-dr .bx{margin:6px 0 0 16px;line-height:1.6}#bell-dr .ba{display:flex;flex-wrap:wrap;gap:6px;margin:8px 0 0 16px}@media (max-width:720px){#bell-dr{top:72px;left:8px;right:8px;width:auto}}',
    bellAlerts: function () {
      var S = null; try { S = C.S(); } catch (err) { if(err&&(err.viewPending||err.code==='VIEW_CHANGED'))throw err; return []; }
      var A = ((S && S.alerts) || []).map(function (a) { return Object.assign({}, a, { acked: a.acked || !!C.st.acked[a.dedupe_key] }); });
      return A.sort(function (a, b) { return (a.acked - b.acked) || ((b.created_at || '') > (a.created_at || '') ? 1 : -1); });
    },
    bellMount: function () {
      if (!document.getElementById('bell-css')) { var s0 = document.createElement('style'); s0.id = 'bell-css'; s0.textContent = LIVE.BELL_CSS + '[data-nav2="alerts"]{display:none!important}[data-nav2="adv"] .mt,[data-nav2="rules"] .mt{display:none}'; document.head.appendChild(s0); }
      var bell = document.getElementById('bell'); if (!bell) return;
      if (C.isReplay()) return;
      var n = LIVE.bellAlerts().filter(function (a) { return !a.acked; }).length, old = bell.querySelector('.bell-n');
      if (old) old.remove();
      if (n) { var b = document.createElement('span'); b.className = 'bell-n'; b.textContent = n > 99 ? '99+' : n; bell.appendChild(b); }
      bell.setAttribute('aria-label', n ? '状态通知，' + n + ' 条未读' : '状态通知'); bell.title = bell.getAttribute('aria-label');
      bell.onclick = function (e) { e.preventDefault(); if (document.getElementById('bell-dr')) LIVE.bellClose(); else LIVE.bellOpen(); };
      if (document.getElementById('bell-dr')) LIVE.bellOpen(true);
    },
    bellClose: function () { var d = document.getElementById('bell-dr'); if (d) d.remove(); LIVE._bellSp = null; },
    bellOpen: function (keep) {
      var esc = C.esc, ic = C.ic, st = C.st, A = LIVE.bellAlerts(), unread = A.filter(function (a) { return !a.acked; }).length;
      if(LIVE._bellFocus){var focus=A.find(function(a){return a.dedupe_key===LIVE._bellFocus;});if(focus)A=[focus].concat(A.filter(function(a){return a!==focus;}));else C.toast('该通知在当前列表不可见，可在操作记录中查看历史');LIVE._bellFocus=null;}
      var NAME = function (a) {
        if (a.card_id === 'sjia-mas') return 'sJIA·MAS 规则集 · MAS 预警';
        var c = (C.S().custom_cards || []).filter(function (x) { return x.card_id === a.card_id; })[0];
        return c ? c.name + ' · 我自定义的规则' : a.title.replace(/^PTDS [^·]*· /, '');
      };
      var LVZ = { ALERT: '关注', WATCH: '观察' }, sp = LIVE._bellSp;
      var item = function (a) {
        return '<div class="bi"><div class="bt"><span class="ud' + (a.acked ? '' : ' on') + '"></span><span class="lv lv-' + esc(a.level) + '">' + esc(LVZ[a.level] || a.level) + '</span><b>' + esc(NAME(a)) + '</b></div>' +
          '<div class="sub2" style="margin:4px 0 0 16px" data-ptds-inline><!--ptds-ui:s9b6e85289091-->时点 <!--/ptds-ui-->' + esc(a.tp) + ' · ' + esc(String(C.tzTime(a.created_at)).slice(5, 16)) + ' · ' + (a.acked ? '已知道' : '未读') + '</div>' +
          '<div class="bx">' + esc(a.body) + '</div>' +
          '<div class="ba">' + (a.acked ? '' : '<button class="btn2" data-bd-ack="' + esc(a.dedupe_key) + '">' + ic('check') + ' 知道了</button>') +
          '<button class="chip" data-bd-cal="' + esc(a.dedupe_key) + '">加到日历</button><button class="chip" data-bd-why="' + esc(a.dedupe_key) + '">看依据</button>' +
          '<button class="chip" data-bd-sp="' + esc(a.dedupe_key) + '">星灵讲讲</button></div>' +
          (sp && sp.dk === a.dedupe_key ? '<div style="margin:8px 0 0 16px">' + LIVE.spBoxHtml(sp) + '</div>' : '') +
          (LIVE._bellCal && LIVE._bellCal.dk === a.dedupe_key ? '<div class="sub2" style="margin:6px 0 0 16px">' + esc(LIVE._bellCal.msg) + '</div>' : '') + '</div>';
      };
      var html = '<div class="bh"><b style="font-size:var(--scale-type-title)" data-ptds-ui="s9b6175f5899b">状态通知</b><span class="sub2">' + (A.length ? unread + ' 条未读 · 共 ' + A.length + ' 条' : '还没有提醒') + '</span><span class="grow" style="flex:1"></span>' +
        '<button class="ibtn" data-bd-x="1" aria-label="关闭" title="关闭" data-ptds-ui-aria-label="s3fd47edce45b" data-ptds-ui-title="s3fd47edce45b">' + ic('x') + '</button></div>' +
        '<div class="bb">' + (A.length ? A.slice(0, 5).map(item).join('') : '<div class="sub2" style="padding:16px 0" data-ptds-ui="se738b31fdee8">状态有变化或有新结果时，会出现在这里。提醒在「增加我的状态」里配。</div>') + '</div>' +
        '<div class="bf"><span class="sub2" data-ptds-ui="sd3ffc125b075">通知在「增加我的状态」里配；完整历史保留「带去问医生」和各通道送达情况</span><span class="grow" style="flex:1"></span><button class="btn2" data-bd-threshold="1" data-ptds-ui="scee6d37a5589">阈值通知</button><button class="btn" data-bd-all="1" data-ptds-ui="sb92c0ea98b9a">查看全部 ›</button></div>';
      var el = document.getElementById('bell-dr');
      if (!el) { el = document.createElement('aside'); el.id = 'bell-dr'; el.setAttribute('role', 'dialog'); el.setAttribute('aria-label', '状态通知'); document.body.appendChild(el); }
      el.innerHTML = html;
      var by = {}; A.forEach(function (a) { by[a.dedupe_key] = a; });
      var on = function (sel, fn) { el.querySelectorAll(sel).forEach(function (b) { b.onclick = function () { fn(by[b.getAttribute(sel.slice(1, -1))] || b.getAttribute(sel.slice(1, -1)), b); }; }); };
      on('[data-bd-threshold]', function () { LIVE.thresholdOpen(); });
      on('[data-bd-x]', function () { LIVE.bellClose(); });
      on('[data-bd-all]', function () { LIVE.bellClose(); C.goTrack('alerts'); });
      on('[data-bd-ack]', LIVE.action(async function (a) { (await LIVE.ack(a.dedupe_key)); C.renderMainOnly && C.renderMainOnly(); LIVE.bellMount(); LIVE.bellOpen(); LIVE.noticeMount(); }));
      on('[data-bd-why]', function (a) {
        LIVE.bellClose();
        if (/^threshold-/.test(a.card_id || '')) { LIVE.graphCards = null; LIVE.openTrace(a.card_id, a.tp); return; }
        if (a.card_id === 'sjia-mas') { LIVE.openTrace(a.card_id, a.tp); return; }
        C.goTrack('wall'); st.ccard = a.card_id; st.ccAsk = null; st.view = 'custom'; C.render(); window.scrollTo(0, 0);
      });
      on('[data-bd-cal]', LIVE.action(async function (a) {
        try {
          var r = (await call('POST', '/api/alerts/calendar', { key: st.key, dedupe_key: a.dedupe_key })), d = r.day.slice(5).replace('-', ' 月 ') + ' 日 ' + r.time;
          if (r.opened) LIVE._bellCal = { dk: a.dedupe_key, msg: '已在 Mac 日历里打开：' + d + '，点“添加”才会加入。日历里不写任何数值。' };
          else { var x = document.createElement('a'); x.href = URL.createObjectURL(new Blob([r.ics], { type: 'text/calendar' })); x.download = r.file; document.body.appendChild(x); x.click(); x.remove();
            LIVE._bellCal = { dk: a.dedupe_key, msg: '已下载日历文件（' + d + '），打开它再点“添加”。日历里不写任何数值。' }; }
        } catch (err) { if(err&&(err.viewPending||err.code==='VIEW_CHANGED'))throw err; LIVE._bellCal = { dk: a.dedupe_key, msg: '没能生成日历（' + LIVE.saveErr(err) + '）' }; }
        LIVE.bellOpen();
      }));
      on('[data-bd-sp]', function (a) {
        var s2 = { k: 'bell', dk: a.dedupe_key, page: 'alert', id: 'sp-bell', title: '', res: { state: 'running', by: '' },
          url: '/api/starling/page?key=' + encodeURIComponent(st.key) + '&page=alert&dk=' + encodeURIComponent(a.dedupe_key) };
        LIVE._bellSp = s2; LIVE.bellOpen(); LIVE.bellAsk(s2, true);
      });
      var sx = el.querySelector('[data-sp-close]'); if (sx) sx.onclick = function () { LIVE._bellSp = null; LIVE.bellOpen(); };
    },
    bellAsk: function (sp, start) {
      clearTimeout(sp.timer);
      fetch(sp.url + (start ? '&start=1' : '&start=0')).then(function (r) { return r.json(); }).then(function (res) {
        if (LIVE._bellSp !== sp) return;
        if (!start && res.state === 'idle') res = sp.res || res;
        if (res.state === 'none') res = { state: 'blocked', why: '这条提醒已经不在了，星灵没有可讲的记录' };
        sp.res = res; if (document.getElementById('bell-dr')) LIVE.bellOpen();
        if (res.state === 'running') sp.timer = setTimeout(function () { LIVE.bellAsk(sp, false); }, 4000);
      }).catch(function () { sp.res = { state: 'error', why: '连不上本机服务' }; if (document.getElementById('bell-dr')) LIVE.bellOpen(); });
    },
    tailData: function (t, S, src) {
      var items = ((S.vitals || {}).items || []), today = C.tzTime(new Date().toISOString()).slice(0, 10), hhmm = function (iso) { return C.tzTime(iso).slice(11, 16); };
      var daily = (S.device_policy || {}).mode === 'daily', cache = (S.device_latest || {})[t.src] || {};
      var pick = (src && src.tail && src.tail.length === 4 ? src.tail : t.tiles.map(function (x) { return x.code; }));
      var tiles = pick.map(function (c) { return t.choices.filter(function (x) { return x.code === c; })[0]; }).filter(Boolean).map(function (x) {
        var cached = cache[x.code];
        if (!cached || cached.code !== x.code || cached.value_raw == null || !cached.observed_at) cached = null;
        var o = cached || items.filter(function (i) { return i.code === x.code && (i.family || i.source_kind) === t.src && (!daily || (!i.observed_at && i.observed_date)); })[0];
        if (!o) return { x: x, v: null, sub: daily ? '等待最近读数' : '还没有数据' };
        var day = o.observed_date || C.tzTime(o.observed_at).slice(0, 10), v = String(o.value_raw);
        if (!cached && (x.unit === '千卡' || x.unit === '步')) v = String(Math.round(Number(o.value_raw)));
        var sub = cached || (x.when === 'instant' && o.observed_at) ? (day === today ? hhmm(o.observed_at) + ' 的读数' : day.slice(5) + ' ' + hhmm(o.observed_at) + ' 的读数')
          : x.when === 'today' ? (day === today ? '今天累计' : day.slice(5) + ' 的数') : day.slice(5) + (x.code === 'OURA_SPO2' ? ' 夜间平均' : ' 夜间');
        if (!cached && x.when === 'dayavg') sub = day.slice(5) + ' 日平均';
        if (!cached && x.when === 'instant' && !o.observed_at) sub = day.slice(5) + ' 日汇总';
        return { x: cached ? Object.assign({},x,{unit:cached.unit_raw || ''}) : x, v: v, sub: sub, old: x.when !== 'night' && day !== today };
      });
      var st = src.status, anyToday = tiles.some(function (z) { return z.v != null && !z.old; });
      return { tiles: tiles, dot: st !== 'CONNECTED' ? 'off' : anyToday ? 'ok' : 'stale', pulled: src.last_pull_at ? (t.id === 'garmin' ? C.tzTime(src.last_pull_at).slice(5,16) : hhmm(src.last_pull_at)) : '', syncStatus: src.sync_status, syncError: src.sync_error, status: st };
    },
    tailCardHtml: function (t, d) {
      var esc = C.esc, set = LIVE._tlSet === t.id;
      var garminStatus = d.status !== 'CONNECTED' ? '需重新授权' : d.syncError ? '同步待重试' : d.syncStatus === 'SYNCING' ? '正在同步' : '每 5 分钟同步';
      var head = window.PTDSTail.header({ name: t.name, icon: t.icon, configurable: true, busy: LIVE._desktopOpening, settingsIcon: C.ic(set ? 'chevron-left' : 'settings'),
        status: t.id === 'garmin' ? garminStatus : d.status === 'CONNECTED' ? (d.pulled ? '同步：' + d.pulled + ' · ' + (t.syncHint || '每 5 分钟一次') : '还没有同步') : '需要重新授权，读数停在上次' });
      if (set) {
        head = head.replace('title="设置小尾巴显示哪四项"', 'title="回到读数"');
        var cur = LIVE._tlPick || d.tiles.map(function (z) { return z.x.code; });
        return head + '<div class="sub2" data-ptds-inline><!--ptds-ui:seeaf07de2b7b-->按照点选的先后排（已选 <!--/ptds-ui-->' + cur.length + '/4）</div><div class="tl-s">' +
          t.choices.map(function (x) { var i = cur.indexOf(x.code); return '<button class="tl-o' + (i >= 0 ? ' on' : '') + '" data-tl-pick="' + esc(x.code) + '">' + (i >= 0 ? '<span class="tl-n">' + (i + 1) + '</span>' : '') + esc(x.label) + '</button>'; }).join('') +
          '</div><div class="tl-acts"><button class="btn" data-tl-save="1"' + (cur.length === 4 ? '' : ' disabled') + '>保存</button><button class="chip" data-tl-set="1" data-ptds-ui="s2cd0f3be8738">取消</button></div>';
      }
      return head + window.PTDSTail.body({ tiles: d.tiles.map(function (z) { return { code: z.x.code, label: z.old ? z.x.label.replace('今日', '') : z.x.label, value: z.v, unit: z.x.unit, note: z.sub, old: z.old }; }), footer: (t.id === 'garmin' ? (d.pulled ? '最近成功同步：' + d.pulled : '尚未成功同步') + ' · ' : '') + t.chain });
    },

    openSpirit: async function () { if(globalThis.PTDS_TRIAL_UI&&!PTDS_TRIAL_UI.can('starlingActions')){C.toast(document.documentElement.lang==='en'?'Starling is off on this device.':'本机未启用星灵');return;}
      var sp = LIVE.sp = LIVE.sp || { turns: [], token: 0 };
      sp.open = !sp.open;
      if (sp.open) { try { sp.memDoc = (await call('GET', '/api/starling/memory?key=' + encodeURIComponent(C.st.key) + '&subject=' + encodeURIComponent(LIVE.memSubject()))); sp.memOn = !!sp.memDoc.enabled; } catch (err) { if(err&&(err.viewPending||err.code==='VIEW_CHANGED'))throw err; sp.memOn = false; sp.memDoc = null; } if (!sp.memOn) sp.mem = false; }
      LIVE.renderSpirit(); LIVE.noticeMount();
      if (sp.open) { var q = document.getElementById('sq-q'); if (q) q.focus(); }
    },
    sqTurnHtml: function (t) {
      var esc = C.esc, ic = C.ic, r = t.r || {}, q = '<div class="sq-q"><span>' + esc(t.q) + '</span></div>';
      var meta = function (tag, right) { return '<div class="sq-m">' + (tag ? '<span class="sq-d">' + esc(tag) + '</span>' : '') + right + '</div>'; };
      var go = function () { return r.go && r.go.length ? '<div>' + r.go.map(function (g) { return '<button class="sq-go" data-sqgo="' + esc(g) + '">' + esc((r.nav || {})[g] || g) + '</button>'; }).join('') + '</div>' : ''; };
      var sent = function () { return r.sent && r.sent.length ? '<details class="sq-f"><summary data-ptds-inline><!--ptds-ui:s21cfce586a14-->星灵看到的记录（<!--/ptds-ui-->' + r.sent.length + ' 条，不含健康数值）</summary><div>' + r.sent.map(esc).join('<br>') + '</div></details>' : ''; };
      var bad = function (list) { return '<details class="sq-f"><summary data-ptds-inline><!--ptds-ui:s29bc78f35a93-->看没通过核对的句子（<!--/ptds-ui-->' + list.length + '）</summary>' + list.map(function (x) { return '<div>' + esc(x.text) + ' <span class="sub2">（' + esc((x.bad || []).join('；')) + '）</span></div>'; }).join('') + '</details>'; };
      var mems = function () { return r.memories && r.memories.length ? '<div class="sq-mem"><div class="sq-m" data-ptds-ui="sa5a38e32de53">用到的记忆 · 你确认过的偏好，不是事实证据</div>' + r.memories.map(function (m) { return '<div>· ' + esc(m.text) + ' <span class="sub2">（' + esc(m.created_at.slice(5, 10)) + ' 记下）</span></div>'; }).join('') + '</div>' : (r.memory_state === 'failed' ? '<div class="sq-f" data-ptds-ui="s5efbbae7e4d2">记忆这次没取到，这个回答没有用记忆。</div>' : ''); };
      if (r.state === 'remember_ask') return q + '<div class="sq-a prog">' + meta('我的记忆', esc(r.by)) + '<div>' + esc(r.answer) + '</div><div class="sq-mem"><div>' + esc(r.proposal) + '</div></div>' +
        (t.saved ? '<div class="sub2" data-ptds-ui="sd87cf79b4a5b">已记住。可以在“我的记忆”里改或删。</div>' : t.skip ? '<div class="sub2" data-ptds-ui="saa318e7664f9">没有记。</div>' :
          '<div><button class="sq-go" data-sqmem-ok="' + t.n + '">确认记住</button><button class="sq-go" data-sqmem-no="' + t.n + '">不用记</button></div>') + '</div>';
      if (t.pending) return q + '<div class="sq-a">' + meta('', '<span class="cp-spin"></span>正在问。交给星灵的问题要写约 1 分钟，写好后逐句核对') + '</div>';
      if (r.state === 'ok') return q + '<div class="sq-a">' + meta(r.area_zh, esc(r.by) + ' · 逐句核对通过') + '<div>' + esc(r.answer) + '</div>' +
        (r.rejected && r.rejected.length ? '<div class="sub2" data-ptds-ui="s8295e53db924">第一次写的没通过核对，已让它重写。</div>' + bad(r.rejected) : '') + mems() + sent() + go() + '</div>';
      if (r.state === 'value') return q + '<div class="sq-a prog">' + meta(r.area_zh, esc(r.by)) + '<div>' + esc(r.answer) + '</div>' + go() + '</div>';
      if (r.state === 'guide') return q + '<div class="sq-a prog">' + meta(r.area_zh, esc(r.by)) + '<div>' + esc(r.answer) + '</div>' + go() + '</div>';
      if (r.state === 'out') return q + '<div class="sq-a fence">' + meta(r.area_zh || '不在范围内', esc(r.by)) + '<div>' + esc(r.answer) + '</div>' + (r.why ? '<div class="sq-f" data-ptds-inline><!--ptds-ui:sf1c63861fe9f-->挡下的原因：<!--/ptds-ui-->' + esc(r.why) + '</div>' : '') + '</div>';
      if (r.state === 'rejected') return q + '<div class="sq-a">' + meta(r.area_zh, '') + '<div>' + esc((r.by || '星灵').replace(/发出$/, '')) + '这次写的回答没通过核对（写了 ' + (r.attempts || 2) + ' 次），没有采用。</div>' + bad(r.rejected || []) + sent() + '</div>';
      if (r.state === 'off') return q + '<div class="sq-a fence"><div>' + esc(r.why || '本机未启用星灵') + '。这个版本只能看记录，不能问星灵。</div></div>';
      if (r.state === 'no_llm') return q + '<div class="sq-a fence">' + meta(r.area_zh, '') + '<div data-ptds-ui="saaf556fad122">本机模型没有在运行，星灵这次答不了。启动本机模型后再问一次。</div></div>';
      if (r.state === 'busy') return q + '<div class="sq-a fence">' + meta(r.area_zh, '') + '<div data-ptds-ui="sc540f51baa33">星灵还在答上一个问题，等它答完再问。</div></div>';
      return q + '<div class="sq-a fence"><div data-ptds-inline><!--ptds-ui:s8e9dfe94d54f-->这次没问成（<!--/ptds-ui-->' + esc(r.error || r.detail || '出错') + '）。可以再问一次。</div></div>';
    },
    renderSpirit: function () {
      var sp = LIVE.sp || { turns: [] }, el = document.getElementById('sq'), esc = C.esc, ic = C.ic;
      if (!sp.open) { if (el) el.remove(); return; }
      if (!el) { el = document.createElement('aside'); el.id = 'sq'; el.setAttribute('role', 'dialog'); el.setAttribute('aria-label', '问星灵'); document.body.appendChild(el); }
      var busy = sp.turns.some(function (t) { return t.pending; }), draft = (document.getElementById('sq-q') || {}).value || sp.draft || '';
      el.innerHTML = '<div class="sq-h"><span class="sp-ic on">' + ic('sparkles') + '</span><b data-ptds-ui="s67f4bfd60c66">问星灵</b><span class="sub2" data-ptds-ui="sc1ee8701acb5">只答 PTDS 里的记录：星炬 · 星轨 · 星簇</span><span class="grow" style="flex:1"></span>' +
        (sp.memOn ? '<button class="chip" id="sq-mem" aria-pressed="' + !!sp.mem + '" title="星灵记住的偏好，可以改、可以删">' + (sp.mem ? '回到问答' : '我的记忆') + '</button>' : '') +
        (sp.turns.length && !sp.mem ? '<button class="chip" id="sq-clear" title="清空这次的问答，还没回来的回答也不再显示" data-ptds-ui-title="s19b5461b974a" data-ptds-ui="s1ef3de06b32e">清空</button>' : '') + '<button class="ibtn" id="sq-x" aria-label="收起" title="收起" data-ptds-ui-aria-label="safd4b783536b" data-ptds-ui-title="safd4b783536b">' + ic('x') + '</button></div>' +
        (sp.mem ? '<div class="sq-b" id="sq-b">' + LIVE.memHtml() + '</div>' : '<div class="sq-b" id="sq-b">' + (sp.turns.length ? sp.turns.map(LIVE.sqTurnHtml).join('') : '<div class="sub2 sq-e" data-ptds-inline><!--ptds-ui:s779fd5509f0b-->可以问：我的数据从哪来、提醒发过几次、有没有数据离开过本机、某项数据最近一次是多少。看病、用药和好坏判断不在范围内。<!--/ptds-ui-->' + (sp.memOn ? '想让星灵记住一个偏好，就说“请记住……”，确认后才会存。' : '') + '</div>') + '</div>') +
        '<div class="sq-ft"><div class="sq-row"><input class="inp" id="sq-q" placeholder="问 PTDS 里的任何记录" aria-label="问星灵"' + (busy ? ' disabled' : '') + ' value="' + esc(busy ? '' : draft) + '"><button class="btn" id="sq-send" aria-label="发送" title="发送"' + (busy ? ' disabled' : '') + '>' + ic('send') + '</button></div>' +
        '<div class="sub2 sq-n" data-ptds-ui="s0fdb5732874f">一次一个问题｜完全本地｜数据不出域｜不构成医学建议</div></div>';
      var b = document.getElementById('sq-b'); if (!sp.mem) b.scrollTop = b.scrollHeight; LIVE.sqPlace();
      var mb = document.getElementById('sq-mem'); if (mb) mb.onclick = LIVE.action(async function () { sp.mem = !sp.mem; sp.memEdit = null; sp.memDel = null; sp.memProof = null; if (sp.mem) (await LIVE.memLoad()); LIVE.renderSpirit(); });
      if (sp.mem) LIVE.memBind(el);
      el.querySelectorAll('[data-sqmem-ok]').forEach(function (x) { x.onclick = LIVE.action(async function () {
        var t = sp.turns.filter(function (u) { return u.n === +x.dataset.sqmemOk; })[0];
        try { (await call('POST', '/api/starling/memory', { key: C.st.key, op: 'remember', subject: LIVE.memSubject(), text: t.r.proposal, confirmed: true, source: '星灵浮窗 · 用户确认' })); t.saved = true; }
        catch (err) { if(err&&(err.viewPending||err.code==='VIEW_CHANGED'))throw err; C.toast('没记上（' + (err.detail || err.code) + '）'); }
        LIVE.renderSpirit(); }); });
      el.querySelectorAll('[data-sqmem-no]').forEach(function (x) { x.onclick = function () { sp.turns.filter(function (u) { return u.n === +x.dataset.sqmemNo; })[0].skip = true; LIVE.renderSpirit(); }; });
      document.getElementById('sq-x').onclick = function () { sp.open = false; LIVE.renderSpirit(); LIVE.noticeMount(); };
      var clr = document.getElementById('sq-clear'); if (clr) clr.onclick = function () { sp.turns = []; sp.token++; LIVE.renderSpirit(); };  /* 清空后，迟到的回答直接丢掉 */
      var q = document.getElementById('sq-q'), send = function () { var t = q.value.trim(); if (t && !busy) { sp.draft = ''; sp.mem = false; LIVE.askSpirit(t); } };
      q.oninput = function () { sp.draft = q.value; };
      document.getElementById('sq-send').onclick = LIVE.action(send); q.onkeydown = function (ev) { if (ev.key === 'Enter' && !ev.isComposing) send(); };
      el.querySelectorAll('[data-sqgo]').forEach(function (x) { x.onclick = function () { var t = sp.turns.filter(function (u) { return u.r; }).pop(); sp.open = false; LIVE.renderSpirit(); LIVE.spiritGo(x.dataset.sqgo, t && t.r && t.r.tp); }; });
    },
    /* 星灵记忆：独立的本机记忆库；只存我确认过的话，按主体分开，可改可删，删了能核对 */
    memSubject: function () { var sp = LIVE.sp || {}; return sp.subject || 'default'; },
    memLoad: async function () {
      var sp = LIVE.sp;
      try { sp.memDoc = (await call('GET', '/api/starling/memory?key=' + encodeURIComponent(C.st.key) + '&subject=' + encodeURIComponent(LIVE.memSubject()))); sp.memErr = null; }
      catch (err) { if(err&&(err.viewPending||err.code==='VIEW_CHANGED'))throw err; sp.memDoc = null; sp.memErr = err.detail || err.code; }
    },
    memHtml: function () {
      var sp = LIVE.sp, esc = C.esc, d = sp.memDoc || { items: [], deleted: [] };
      var h = '<div class="sq-mh"><span class="sub2" data-ptds-ui="sead6d98b1710">记忆主体</span><input class="inp" id="sq-subj" value="' + esc(LIVE.memSubject()) + '" aria-label="记忆主体" maxlength="32"><button class="chip" id="sq-subj-go" data-ptds-ui="seff514b8b83f">切换</button></div>' +
        '<div class="sub2 sq-e" data-ptds-inline><!--ptds-ui:s8b8f88b99903-->这里只有你点过“确认记住”的话。它们是偏好，不是事实证据；换一个主体，彼此看不到。检索方式：<!--/ptds-ui-->' + (d.embed_ready ? '本机向量模型（' + esc(d.embed_model) + '）' : '本机字词匹配（没找到向量模型）') + '。</div>' +
        (sp.memErr ? '<div class="sq-a fence" data-ptds-inline><!--ptds-ui:s39a38806bc11-->记忆没读到（<!--/ptds-ui-->' + esc(sp.memErr) + '）。</div>' : '');
      if (!d.items.length) h += '<div class="sub2 sq-e" data-ptds-ui="se26047396039">这个主体下还没有记忆。在问答里说“请记住……”，确认后就会出现在这里。</div>';
      h += d.items.map(function (m) {
        var ed = sp.memEdit === m.chain_id, del = sp.memDel === m.chain_id;
        return '<div class="sq-mi"><div class="sq-m"><span class="sq-d">第 ' + m.version + ' 版</span>' + esc(m.created_at.slice(5, 16).replace('T', ' ')) + ' · ' + esc(m.source) + '</div>' +
          (ed ? '<div class="sq-row"><input class="inp" id="sq-mem-txt" value="' + esc(m.text) + '" maxlength="200" aria-label="更正记忆"></div><div><button class="sq-go" data-memfix="' + esc(m.chain_id) + '">确认更正</button><button class="sq-go" data-memcancel="1" data-ptds-ui="s2cd0f3be8738">取消</button></div>'
            : '<div>' + esc(m.text) + '</div>' + (del ? '<div class="sub2" data-ptds-ui="s59fcffb9e833">删掉后星灵再也想不起它，所有旧版本一起删，只留删除凭证。</div><div><button class="sq-go" data-memdelok="' + esc(m.chain_id) + '">确认删除</button><button class="sq-go" data-memcancel="1" data-ptds-ui="s2cd0f3be8738">取消</button></div>'
              : '<div><button class="sq-go" data-memedit="' + esc(m.chain_id) + '">改</button><button class="sq-go" data-memdel="' + esc(m.chain_id) + '">删</button></div>')) + '</div>';
      }).join('');
      if (sp.memProof) { var p = sp.memProof; h += '<div class="sq-a ' + (p.deleted ? 'prog' : 'fence') + '"><div class="sq-m" data-ptds-ui="s5da9db927b31">删除凭证</div><div>' + (p.deleted ? '已删干净：库里按编号和内容指纹都查不到（剩 ' + p.rows_left + ' 行），数据库文件里也找不到原文。共删 ' + p.versions + ' 个版本。' : '没有删干净，请把这条截图给我。') + '</div><div class="sub2" data-ptds-inline><!--ptds-ui:s8846cd7c325e-->内容指纹 <!--/ptds-ui-->' + esc((p.content_shas || []).join('、')) + ' · ' + esc((p.deleted_at || '').slice(5, 16).replace('T', ' ')) + '</div></div>'; }
      if (d.deleted.length) h += '<details class="sq-f"><summary data-ptds-inline><!--ptds-ui:sfed5a188b937-->删除记录（<!--/ptds-ui-->' + d.deleted.length + ' 条，只有删除时间，没有原文）</summary>' + d.deleted.map(function (x) { return '<div>' + esc(x.deleted_at.slice(5, 16).replace('T', ' ')) + ' 删除 · ' + x.versions + ' 个版本 <button class="nt-link" data-memverify="' + esc(x.chain_id) + '">再核对一次</button></div>'; }).join('') + '</details>';
      return h;
    },
    memBind: function (el) {
      var sp = LIVE.sp, post = async function (body) { return (await call('POST', '/api/starling/memory', Object.assign({ key: C.st.key, subject: LIVE.memSubject() }, body))); };
      var go = document.getElementById('sq-subj-go'); if (go) go.onclick = LIVE.action(async function () {
        var v = document.getElementById('sq-subj').value.trim();
        if (!/^[A-Za-z0-9_-]{1,32}$/.test(v)) return C.toast('主体编号只能用字母、数字、- 和 _');
        sp.subject = v; sp.memProof = null; sp.turns = []; sp.token++; (await LIVE.memLoad()); LIVE.renderSpirit(); C.toast('已切换到主体 ' + v + '，问答也换成这个主体'); });
      var w = function (sel, fn) { el.querySelectorAll(sel).forEach(function (x) { x.onclick = LIVE.action(async function () { await fn(x); LIVE.renderSpirit(); }); }); };
      w('[data-memedit]', function (x) { sp.memEdit = x.dataset.memedit; sp.memDel = null; });
      w('[data-memdel]', function (x) { sp.memDel = x.dataset.memdel; sp.memEdit = null; });
      w('[data-memcancel]', function () { sp.memEdit = null; sp.memDel = null; });
      w('[data-memfix]', LIVE.action(async function (x) {
        try { sp.memDoc = Object.assign(sp.memDoc, (await post({ op: 'correct', chain_id: x.dataset.memfix, text: document.getElementById('sq-mem-txt').value, confirmed: true, source: '我的记忆 · 用户更正' }))); sp.memEdit = null; C.toast('已更正，旧版本不再用'); }
        catch (err) { if(err&&(err.viewPending||err.code==='VIEW_CHANGED'))throw err; C.toast('没改上（' + (err.detail || err.code) + '）'); } }));
      w('[data-memdelok]', LIVE.action(async function (x) {
        try { var r = (await post({ op: 'forget', chain_id: x.dataset.memdelok })); sp.memDoc = Object.assign(sp.memDoc, r); sp.memProof = r.result; sp.memDel = null; }
        catch (err) { if(err&&(err.viewPending||err.code==='VIEW_CHANGED'))throw err; C.toast('没删掉（' + (err.detail || err.code) + '）'); } }));
      w('[data-memverify]', LIVE.action(async function (x) {
        try { var r = (await post({ op: 'verify', chain_id: x.dataset.memverify })); sp.memProof = Object.assign({ versions: '' }, r.result); }
        catch (err) { if(err&&(err.viewPending||err.code==='VIEW_CHANGED'))throw err; C.toast('没核对成（' + (err.detail || err.code) + '）'); } }));
    },
    askSpirit: function (label) {
      var sp = LIVE.sp, mine = sp.token, t = { pending: true, q: label, n: (sp.seq = (sp.seq || 0) + 1) };
      sp.turns.push(t); LIVE.renderSpirit();
      fetch('/api/starling/ask', { method: 'POST', headers: { 'X-PTDS': '1', 'Content-Type': 'application/json' }, body: JSON.stringify({ key: C.st.key, page: LIVE.spiritPage(), question: label, subject: LIVE.memSubject() }) })
        .then(function (r) { return r.json(); })
        .then(function (j) { if (mine !== sp.token) return; t.pending = false; t.r = j.error ? { state: 'error', error: j.detail || j.error } : j; LIVE.renderSpirit(); })
        .catch(function (err) { if (mine !== sp.token) return; t.pending = false; t.r = { state: 'error', error: '连不上本机服务' }; LIVE.renderSpirit(); });
    },
    spiritGo: function (g, tp) {
      var P = window.__ptds, st = P.st; C.closeDrawer();
      if (g === 'graph') { if (tp) st.graphTp = tp; st.graphLane = 'ALL'; return P.goTorch('graph'); }
      if (g === 'tp' && tp) { st.foot = null; st.card = 'SJIA_FOCUS'; P.setSeg('data-app', 'track'); return P.openDetail(tp); }
      if (g === 'vitals') { st.card = 'VITALS'; return P.goTrack('status'); }
      if (g === 'records') { st.xhTab = 'auth'; st.xhView = 'records'; return P.goTorch('graph'); }  /* r62：授权记录在星痕 */
      if (g === 'grants') return P.goCluster('rules');
      if (g === 'wall' || g === 'alerts' || g === 'eng' || g === 'adv') return P.goTrack(g);
      return P.goTorch(g === 'tp' ? 'graph' : g);
    },
    /* 新的"设备断开 / 恢复"事件在页面上也提示一次（Mac 通知由本机进程发） */
    announceDevice: function () {
      var evs = C.S().device_events || [], last = evs[evs.length - 1];
      if (!last) return;
      if (LIVE.seenDevice === undefined) { LIVE.seenDevice = last.id; return; }
      if (last.id !== LIVE.seenDevice) { LIVE.seenDevice = last.id; C.toast(last.title + '：' + (last.reason || last.body)); }
    },
    /* 「增加我的状态」与绑定（路径 C）：哪些来源进"我的体征"，由本机进程记下（card_setup），解绑后读数块消失、记录保留 */
    SOURCE_ZH: { DEVICE_GARMIN: 'Garmin', DEVICE_OURA: 'Oura', PHONE_HEALTH: '苹果健康', DEVICE_SOMALOOP: 'Somaloop 手环', DEVICE_QKEER: 'Qkeer' },
    engSources: function () {
      var snap = C.S(), fams = {}, out = [];
      try { var src = readCached('/api/sources?key=' + encodeURIComponent(C.st.key)); if ((src.oura || {}).status === 'CONNECTED') fams.DEVICE_OURA = 1; } catch (err) { if(err&&(err.viewPending||err.code==='VIEW_CHANGED'))throw err; /* 无 */ }
      ((snap.vitals_all || snap.vitals || {}).items || []).forEach(function (i) { if (LIVE.SOURCE_ZH[i.family]) fams[i.family] = 1; });
      (snap.known_sources || []).forEach(function (f) { fams[f] = 1; });
      var META = { DEVICE_OURA: '静息心率、心率变异性、睡眠、体温、血氧等', PHONE_HEALTH: '步数、心率等（苹果健康同步）', DEVICE_SOMALOOP: '心率', DEVICE_QKEER: '体温' };
      Object.keys(LIVE.SOURCE_ZH).forEach(function (f) { if (fams[f]) out.push({ id: f, name: LIVE.SOURCE_ZH[f], metric: META[f], unit: '' }); });
      return out;
    },
    engCreate: async function (e, key) {
      key=key||C.st.key;
      var sel = {}, who = Object.keys(e.notify || {}).filter(function (k) { return e.notify[k]; });
      LIVE.engSources().forEach(function (d) { sel[d.id] = !!e.sel[d.id]; });
      var res = (await call('POST', '/api/track/card', { key: key, card: 'VITALS', sources: sel, notify: { DEVICE_OFFLINE: who } }));
      C.SNAPS[key] = res.snapshot; C.st.cards[C.S().instance.instance_id] = res.setup.cards;
      return (await LIVE.restoreCreatedCard('card:VITALS',key));
    },
    bindingHtml: function () {
      var snap = C.S(), setup = snap.card_setup || {}, esc = C.esc, ic = C.ic, srcs = LIVE.engSources();
      if ((setup.cards || []).indexOf('VITALS') < 0) return srcs.length ? '<section class="confirm" data-sem="SEM-18"><div data-ptds-inline><!--ptds-ui:sfa1876770899-->已接入 <!--/ptds-ui-->' + srcs.length + ' 个来源。要让哪张卡用这些数据，在星轨"「增加我的状态」"里新建"我的体征"时选择。</div><div class="acts"><button class="' + (C.st.engReturn ? 'btn' : 'btn2') + '" id="live-back-eng">' + ic('wand-sparkles') + (C.st.engReturn ? '回到「增加我的状态」' : '去「增加我的状态」') + '</button></div></section>' : '';
      var vs = setup.vitals_sources, ask = C.st.liveUnbind;
      var rows = srcs.map(function (d) { var bound = !vs || !!vs[d.id];
        return '<div class="lrow"><span>' + esc(d.name) + '</span><span class="sub2">' + esc(d.metric) + '</span><span>' + (bound ? '<span class="tag" data-ptds-ui="sb78b33932ee7">已绑定 · 我的体征</span>' : '<span class="sub2" data-ptds-ui="sb9aae73f4007">没有绑定</span>') + '</span><span>' +
          (bound ? '<button class="ibtn" data-live-unbind="' + d.id + '" aria-label="解绑 ' + esc(d.name) + '" title="解绑">' + ic('x') + '</button>' : '<button class="chip" data-live-bind="' + d.id + '">绑定到我的体征</button>') + '</span></div>'; }).join('');
      var conf = ask ? '<section class="confirm" data-cmp="T10" data-sem="SEM-18"><div data-ptds-inline><!--ptds-ui:s571630fea0b4-->解绑后，"我的体征"不再使用 <!--/ptds-ui-->' + esc(LIVE.SOURCE_ZH[ask]) + ' 的数据，已有记录保留。</div><div class="acts"><button class="btn" id="live-unbind-ok" data-ptds-ui="sb26b245416e8">确认解绑</button><button class="ibtn" id="live-unbind-no" aria-label="取消" title="取消" data-ptds-ui-aria-label="s2cd0f3be8738" data-ptds-ui-title="s2cd0f3be8738">' + ic('x') + '</button></div></section>' : '';
      return '<section class="box"><h3>' + ic('link-2-off') + ' 绑定到"我的体征"的数据</h3>' + (rows || '<div class="sub2" data-ptds-ui="se24357011ce2">还没有接入的来源</div>') + '</section>' + conf +
        LIVE.deviceEventsHtml();
    },
    /* 设备断开 / 恢复（最近 5 条）：接入设备页和状态通知页共用 */
    deviceEventsHtml: function () {
      var esc = C.esc, ic = C.ic, evs = ((C.S() || {}).device_events || []).slice().reverse().slice(0, 5);
      return evs.length ? '<section class="box"><h3>' + ic('bell') + ' 设备断开 / 恢复</h3>' + evs.map(function (x) { return '<div class="lrow"><span>' + esc(x.title) + '</span><span class="sub2">' + esc(x.reason || x.body) + '</span><span class="sub2">' + esc(C.tzTime(x.at, true)) + '</span><span class="sub2">' + ((x.deliveries || []).filter(function (d) { return d.channel !== 'BANNER'; }).map(function (d) { return (d.channel === 'MACOS' ? 'Mac 通知' : d.channel) + (d.outcome === 'SENT' ? '已送达' : '未送达'); }).join('、') || (x.kind === 'DEVICE_OFFLINE' ? '没有配通知' : '')) + '</span></div>'; }).join('') + '</section>' : '';
    },
    /* 状态通知页没有提醒时：说清楚每张卡现在在什么等级、什么时候才会提醒，而不是一句"还没有" */
    alertsEmpty: function () {
      var esc = C.esc, s = C.S() || {}, lines = [], zh = { ALERT: '关注', WATCH: '观察', UNDETERMINED: '无法判定 · 建议补检', NONE: '无' };
      var tps = s.timepoints || [], last = tps[tps.length - 1];
      if (s.card) lines.push('sJIA 关注卡：' + (last && last.level ? '最新时点 ' + last.tp + ' 是"' + zh[last.level] + '"' : '还没有算过的时点'));
      (s.custom_cards || []).filter(function (c) { return c.active; }).forEach(function (c) {
        lines.push('「' + c.name + '」：' + (c.current ? '最新时点 ' + c.current.tp + ' 是"' + c.current.level_zh + '"' : '还没有算过的时点'));
      });
      if (((s.card_setup || {}).cards || []).indexOf('VITALS') >= 0) lines.push('我的体征：只显示读数，不提醒');
      var inst = s.instance || {};
      return '<div class="empty" data-cmp="G10">现在没有提醒。</div>'; /* 产品负责人 08:47：说明话多，删 */
    },
    bindBinding: function () {
      var post = async function (src, bound) { var r = (await call('POST', '/api/track/bind', { key: C.st.key, source: src, bound: bound })); C.SNAPS[C.st.key] = r.snapshot; };
      document.querySelectorAll('[data-live-unbind]').forEach(function (b) { b.onclick = function () { C.st.liveUnbind = b.dataset.liveUnbind; C.render(); }; });
      document.querySelectorAll('[data-live-bind]').forEach(function (b) { b.onclick = LIVE.action(async function () { (await post(b.dataset.liveBind, true)); C.toast('已绑定。"我的体征"会自动更新'); C.render(); }); });
      var g = function (k, fn) { var el = document.getElementById(k); if (el) el.onclick = LIVE.action(fn); };
      g('live-unbind-ok', LIVE.action(async function () { var f = C.st.liveUnbind; (await post(f, false)); C.st.liveUnbind = null; C.toast('"我的体征"不再使用 ' + LIVE.SOURCE_ZH[f] + ' 的数据，已有记录保留'); C.render(); }));
      g('live-unbind-no', function () { C.st.liveUnbind = null; C.render(); });
      g('live-back-eng', function () { C.st.eng = C.st.eng || { step: 1, tpl: 'VITALS', sel: {} }; if (C.st.eng.step < 1) { C.st.eng.tpl = 'VITALS'; C.st.eng.step = 1; } window.__ptds.goTrack('eng'); });
    },
    /* 苹果健康"iPhone 端"：真实操作在手机快捷指令里，这里给地址和配对码，接收端状态来自本机进程 */
    applePhonePanel: function (b) {
      var esc = C.esc, ic = C.ic, c = b.code, on = b.on;
      return '<section class="mock agent" id="ah-live-phone" aria-label="iPhone 端"><div class="mk">' + ic('smartphone') + '<span data-ptds-ui="sbaa254d2163c">在 iPhone 上</span></div>' +
        '<div class="b" data-ptds-inline><!--ptds-ui:s2aca40789468-->接收端<!--/ptds-ui-->' + (on ? '已打开' : '未打开') + '。iPhone 和这台电脑在同一个 Wi‑Fi 时，在快捷指令里填下面任一地址：</div>' +
        (on ? '<div class="sub2">' + b.addresses.map(esc).join('<br>') + '</div>' : '') +
        (c && !c.used ? '<div class="resp"><div class="sub2" data-ptds-inline><!--ptds-ui:s0908383b7c87-->配对码（<!--/ptds-ui-->' + esc(String(b.code_minutes)) + ' 分钟内有效，只能用一次）</div><div style="font-size: var(--scale-type-title)">' + esc(c.code) + '</div></div>' : '') +
        '<div class="sub2" data-ptds-ui="safe4271658c1">快捷指令"配对星炬"和"同步到星炬"的做法见 app/docs/apple_health_shortcut.md。手机发来的每一批都会在左边出现回执。</div>' +
        '<div class="opts">' + (on ? '<button class="chip" id="ah-off">' + ic('unplug') + '停止接收</button>' : '<button class="chip" id="ah-on">' + ic('smartphone') + '打开接收</button>') + '</div></section>';
    },
    bindApplePhone: function () {
      var g = function (k, fn) { var el = document.getElementById(k); if (el) el.onclick = LIVE.action(fn); };
      g('ah-on', LIVE.action(async function () { (await call('POST', '/api/bridge/enable', { key: C.st.key })); C.renderApple(); }));
      g('ah-off', LIVE.action(async function () { (await call('POST', '/api/bridge/disable', { key: C.st.key })); C.toast('已停止接收，已收到的数据保留'); C.renderApple(); }));
    },
    /* 基因纳管写入器：原文件原样保存进本机实例目录，记 SHA-256 与回执；不解析、不进星轨 */
    /* 星炬"我的数据"、近期数源、证据里的基因文件取自本机回执（原型放在 st.geneFiles） */
    loadGene: function (key) {
      if (window.PTDS_TRIAL_UI && !window.PTDS_TRIAL_UI.can('genes')) return Promise.resolve(); var id=C.SNAPS[key].instance.instance_id;
      return readView('/api/gene?key='+encodeURIComponent(key)).then(function(files){
        if(!C.SNAPS[key]||C.SNAPS[key].instance.instance_id!==id)return;
        C.st.geneFiles[id]=files.slice().reverse().map(function(f){
          return {name:f.file_name,when:C.tzTime(f.received_at),batch:f.receipt_id,nature:f.nature};
        });
      }).catch(function(){ /* Keep last receipts on a failed read. */ });
    },
    /* 基因文件的资产属性（只描述文件本身：格式、行数、位点数……，不解读） */
    geneAttrs: function (f) {
      var esc = C.esc, p = f.profile || {}, kv = [], n = function (x) { return x == null ? null : Number(x).toLocaleString('zh-CN'); };
      var add = function (k, v) { if (v !== null && v !== undefined && v !== '') kv.push([k, v]); };
      var size = f.bytes >= 1048576 ? (f.bytes / 1048576).toFixed(1) + ' MB' : f.bytes >= 1024 ? (f.bytes / 1024).toFixed(1) + ' KB' : f.bytes + ' 字节';
      add('格式', p.format || '（这份回执生成时还没有记录属性）');
      add('来源厂商', p.vendor || (p.format ? '文件里没写' : ''));
      add('参考基因组', p.build || (p.text ? '文件里没写' : ''));
      add('压缩', p.compression ? p.compression + (p.member ? ' · 包内 ' + p.member : '') : p.format ? '无' : '');
      add('文字编码', p.encoding);
      add('大小', size + '（' + n(f.bytes) + ' 字节）');
      add('总行数', n(p.lines_total));
      add('注释/表头行', n(p.lines_comment));
      add('数据行', n(p.rows_data));
      add('位点数', n(p.snps));
      add('变异记录数', n(p.variants));
      add('样本数', n(p.samples));
      add('读段数', n(p.reads));
      add('带 rs 编号的位点', n(p.rsids));
      add('未检出（no-call）', n(p.no_calls));
      add('染色体', p.chromosomes && p.chromosomes.length ? p.chromosomes.join(' ') + '（' + p.chromosomes.length + ' 条）' : '');
      add('列数', p.columns ? p.columns + (p.delimiter ? ' · ' + p.delimiter + '分隔' : '') : '');
      add('表头', p.header && p.header.length ? p.header.join(' · ') : '');
      var db = f.db_now || f.db || null, DBW = { NOT_LOADABLE: '这种格式不进位点库（原件照样保存）', LOAD_FAILED: '写入位点库失败（' + ((f.db || {}).why || '') + '），原件已保存' };
      add('位点库', db ? (db.status === 'LOADED' || db.status === 'ALREADY_LOADED' ? '已写入 ' + n(db.rows) + ' 行（本机 genotypes.db，可按 rs 号或位置调取）' : DBW[db.status] || db.status) : p.format ? '还没写入' : '');
      if (f.profile_added_later) add('属性来源', '纳管后补算（回执原文未改）');
      add('指纹（SHA-256）', f.sha256);
      add('回执编号', f.receipt_id);
      add('纳管时间', C.tzTime(f.received_at, true));
      add('保存为', f.stored_as);
      return '<div class="kv2">' + kv.map(function (x) { return '<span>' + esc(x[0]) + '</span><span>' + esc(String(x[1])) + '</span>'; }).join('') + '</div>';
    },
    /* 位点库调取：按 rs 号或"染色体:位置"查，只显示文件里写着的内容和出处 */
    geneLookupBox: function () {
      var st = {}; try { st = readCached('/api/gene/db?key=' + encodeURIComponent(C.st.key)); } catch (err) { if(err&&(err.viewPending||err.code==='VIEW_CHANGED'))throw err; /* 显示为空 */ }
      LIVE.geneDbFiles = st.files || 0;
      if (!st.files) return '';
      return '<section class="box"><h3>' + C.ic('search') + ' 位点库 · ' + st.files + ' 份文件 · ' + Number(st.rows).toLocaleString('zh-CN') + ' 行</h3>' +
        '<div class="daterow"><input class="inp" id="gene-q" placeholder="rs 号（如 rs4988235）或 染色体:位置（如 2:136608646）" style="flex: 1" value="' + C.esc((C.st.geneQ || {}).q || '') + '"><button class="btn" id="gene-go" data-ptds-ui="sb97d6107342e">调取</button></div>' +
        '<div id="gene-qout">' + LIVE.geneLookupOut() + '</div><div class="sub2" data-ptds-ui="s64aac23e2ad7">只显示文件里写着的基因型和出处（文件、行号），不做解读。</div></section>';
    },
    geneLookupOut: function () {
      var q = C.st.geneQ, esc = C.esc; if (!q) return '';
      if (q.error) return '<div class="tip">' + esc(q.error) + '</div>';
      if (!q.rows.length) return '<div class="sub2" data-ptds-inline><!--ptds-ui:se45f2b43992f-->位点库里没有 <!--/ptds-ui-->' + esc(q.q) + '</div>';
      return '<div class="kv2">' + q.rows.map(function (r) { return '<span>' + esc(r.rsid || '—') + ' · ' + esc(r.chrom) + ':' + esc(String(r.pos)) + (r.build ? '（' + esc(r.build) + '）' : '') + '</span><span><b>' + esc(r.genotype || '—') + '</b>' + (r.raw_gt ? '（GT ' + esc(r.raw_gt) + '，REF ' + esc(r.ref) + ' ALT ' + esc(r.alt) + '）' : '') + ' · ' + esc(r.file_name) + ' 第 ' + r.line + ' 行</span>'; }).join('') + '</div>';
    },
    /* 基因位点经星簇授权供给：只给本人的本机智能体（MCP）、只读、可限定 rs 号；撤销后读不到，每次读取都留痕 */
    geneScope: function (g) {
      var l = g.loci || g.events;
      return '基因位点（原始基因型，未解读） · ' + (l === '*' ? '全部位点（每次读取要说明读哪些 rs 号）' : l.length + ' 个位点：' + l.slice(0, 6).join('、') + (l.length > 6 ? ' 等' : ''));
    },
    restateGene: function (p) {
      var rows = p.loci || [];
      return (rows.length ? '我读到了 ' + rows.length + ' 条原始基因型：' + rows.map(function (x) { return x.rsid + ' ' + (x.genotype || '—') + '（' + x.chrom + ':' + x.pos + '，' + x.build + '）'; }).join('，') + '。' : '这次没有读到任何位点。') +
        (p.not_found ? '文件里没有 ' + p.not_found + '。' : '') + '这些只是文件里写着的基因型，我不做解读；即使解释，也只是遗传倾向，非诊断。';
    },
    geneGrantBox: function (dbFiles) {
      var esc = C.esc, ic = C.ic, gs = [];
      if (!dbFiles) return '';
      try { gs = readCached('/api/cluster/list?key=' + encodeURIComponent(C.st.key)).filter(function (g) { return g.card === 'GENE_LOCI'; }); } catch (err) { if(err&&(err.viewPending||err.code==='VIEW_CHANGED'))throw err; gs = []; }
      var ST = { ACTIVE: '生效中', WAIT_CHANNEL: '等接入', REVOKED: '已撤销', EXPIRED: '已到期' }, dur = C.st.geneDur || '7d';
      return '<section class="box" data-sem="SEM-25"><h3>' + ic('key-round') + ' 让我的本机智能体按位点读取</h3>' +
        '<div class="sub2" data-ptds-ui="s9817b12b64b6">经星簇授权：只给你自己的本机智能体（本机 MCP，只读），只能读你列出的 rs 号；读别的位点会被拒绝，每次读取（含被拒绝）都记进授权记录。随时可在星簇撤销。</div>' +
        '<div class="daterow"><input class="inp" id="gg-loci" placeholder="要开放的 rs 号，用逗号或空格隔开（如 rs4149056, rs1045642）" style="flex: 1" value="' + esc(C.st.geneLoci || '') + '"></div>' +
        '<div class="opts" role="group" aria-label="时效" data-ptds-ui-aria-label="scea526c6744c">' + [['24h', '24 小时'], ['7d', '7 天'], ['30d', '30 天']].map(function (d) { return '<button class="chip" data-ggdur="' + d[0] + '" aria-pressed="' + (d[0] === dur) + '">' + d[1] + '</button>'; }).join('') + '<button class="btn" id="gg-make">' + ic('key-round') + '新建授权</button></div>' +
        (gs.length ? '<div>' + gs.map(function (g) { return '<div class="lrow"><span>' + esc(g.id) + ' · ' + esc(LIVE.geneScope(g)) + '</span><span class="sub2">' + esc(ST[g.status] || g.status) + (g.expires_at ? ' · 到 ' + esc(C.tzTime(g.expires_at, true)) : '') + '</span><span><button class="link" data-gggo="' + esc(g.id) + '">在星簇查看</button></span></div>'; }).join('') + '</div>' : '') +
        '<div class="sub2" data-ptds-ui="s7b096a86b23f">智能体那一端：用本机 MCP 工具 read_my_gene_loci，带上授权编号和 rs 号（配置见 app/mcp_cluster.py 开头）。</div></section>';
    },
    bindGeneGrant: function () {
      var g = function (k, fn) { var el = document.getElementById(k); if (el) el.onclick = LIVE.action(fn); };
      document.querySelectorAll('[data-ggdur]').forEach(function (b) { b.onclick = function () { C.st.geneLoci = (document.getElementById('gg-loci') || {}).value || ''; C.st.geneDur = b.dataset.ggdur; LIVE.renderGene(); }; });
      document.querySelectorAll('[data-gggo]').forEach(function (b) { b.onclick = function () { window.__ptds.st.gid = b.dataset.gggo; window.__ptds.goCluster('grant'); }; });
      g('gg-make', LIVE.action(async function () {
        var raw = (document.getElementById('gg-loci').value || '').trim(), loci = raw.split(/[\s,，、;；]+/).filter(Boolean);
        C.st.geneLoci = raw;
        if (!loci.length) { C.toast('先写上要开放的 rs 号'); return; }
        var bad = loci.filter(function (x) { return !/^rs\d{1,12}$/i.test(x); });
        if (bad.length) { C.toast('这些不是 rs 号：' + bad.slice(0, 5).join('、')); return; }
        try {
          var gg = (await call('POST', '/api/cluster/create', { key: C.st.key, form: { object: 'my_agent', channel: 'mcp', method: 'read', level: 'data', card: 'GENE_LOCI', loci: loci, duration: C.st.geneDur || '7d' } }));
          C.st.geneLoci = ''; C.toast('已授权 ' + gg.id + '：本机智能体可以读这 ' + gg.loci.length + ' 个位点'); LIVE.renderGene();
        } catch (err) { if(err&&(err.viewPending||err.code==='VIEW_CHANGED'))throw err; C.toast('没能新建授权（' + (err.detail || err.code) + '）'); }
      }));
    },
    /* 基因数据覆盖（G00，产品负责人 2026-10-14 08:08）：目标位点登记表里的每个位点，文件里有没有、分型成功没有、坐标对不对得上。
       第一层一行概况 + 四组；第二层抽屉列位点；第三层单个位点的五步：原始基因型 → 编号和坐标核对 → 文献 → 统计关联 → 局限。
       只在本机算；不解读、不出风险分、不推断 HLA 分型和代谢表型、不给用药建议。 */
    geneCover: function () {
      try { LIVE._gcov = readCached('/api/gene/coverage?key=' + encodeURIComponent(C.st.key)); } catch (err) { if(err&&(err.viewPending||err.code==='VIEW_CHANGED'))throw err; LIVE._gcov = null; }
      return LIVE._gcov;
    },
    geneCoverBox: function () {
      var esc = C.esc, ic = C.ic, R = LIVE.geneCover(); if (!R || !R.files.length) return '';
      var f = R.files[R.files.length - 1], n = function (x) { return Number(x).toLocaleString('zh-CN'); };
      var head = [['检测类型', f.assay_zh + (f.vendor ? ' · ' + f.vendor : '')], ['参考基因组', f.build.zh], ['有效基因型', n(f.valid_genotypes) + ' 个（没分型成功 ' + n(f.no_call) + ' 个）'],
        ['范围', (f.full_export ? '完整导出' : '片段') + ' · ' + f.chromosomes.length + ' 条染色体' + (f.nonstandard_ids ? ' · 非标准探针编号 ' + n(f.nonstandard_ids) + ' 个（保留原文，未映射）' : '')]];
      return '<section class="box" id="gcov"><h3>' + ic('dna') + ' 基因数据覆盖 · 医学研究位点<span class="grow"></span><span class="sub2" data-ptds-inline><!--ptds-ui:sa9e2b6908ddb-->登记表 v<!--/ptds-ui-->' + esc(R.registry.version) + ' · ' + R.registry.targets + ' 个目标</span><span class="rl-ic" id="gcov-rule" title="看这组状态规则" style="cursor:pointer" data-ptds-ui-title="s3aadf6850a8f">' + ic('scroll-text') + '</span></h3>' +
        '<div class="kv2">' + head.map(function (x) { return '<span>' + esc(x[0]) + '</span><span>' + esc(x[1]) + '</span>'; }).join('') + '</div>' +
        f.cards.filter(function (c) { return c.id !== 'G00'; }).map(function (c) {
          var k = c.counts, bits = [];
          (c.snp_targets ? [] : ['PRESENT_CALLED']).concat(['PRESENT_NO_CALL', 'NOT_IN_PROVIDED_FRAGMENT', 'NOT_IN_FULL_EXPORT', 'ASSAY_COVERAGE_UNKNOWN']).forEach(function (s) { if (k[s]) bits.push(R.status_zh[s] + ' ' + k[s]); });
          return '<button class="lrow c3" data-gcard="' + esc(c.id) + '" style="width:100%;text-align:left;background:none;border:0;border-bottom:var(--primitive-border-hairline) solid var(--theme-line-hairline);color:inherit;font:inherit;cursor:pointer"><span>' + esc(c.zh) + '<br><span class="sub2">' + esc(c.sub || '') + '</span>' + (c.g04_zh ? '<br><span class="sub2">' + esc(c.g04_zh) + '</span>' : '') + '</span><span class="sub2">' + (c.snp_targets ? '直接观测 ' + c.snp_called + '/' + c.snp_targets + ' 个位点 · ' : '') + esc(bits.join(' · ')) + '</span><span>' + ic('chevron-right') + '</span></button>';
        }).join('') +
        '<div class="sub2" style="margin-top:10px" data-ptds-inline><!--ptds-ui:s51c0754c3aea-->只核对文件里有没有这个位点、分型成功没有；没找到不等于阴性。不算风险分，不推断 HLA 分型和代谢表型，不给用药建议。只在这台电脑上算 · 核对记录 <!--/ptds-ui-->' + (R.runs || []).filter(function (r) { return r.file_sha === f.file_sha; }).length + ' 次</div></section>';
    },
    geneCardPop: function (cid, tid) {
      var esc = C.esc, ic = C.ic, R = LIVE._gcov; if (!R) return;
      var f = R.files[R.files.length - 1], c = f.cards.filter(function (x) { return x.id === cid; })[0], rows = f.matrix.filter(function (r) { return r.card === cid; });
      var old = document.getElementById('rule-pop'); if (old) old.remove();
      var label = function (r) { return r.rsid ? r.rsid + (r.star_allele ? '（CYP2C9' + r.star_allele + '）' : r.gene ? ' · ' + r.gene : '') : r.hla_allele || r.gene; };
      var body;
      var t = tid && rows.filter(function (r) { return r.target_id === tid; })[0];
      if (t) {
        var steps = [['原始基因型', t.observed_genotype ? t.observed_genotype + (t.genotype_class === 'INDEL_CODE' ? '（芯片的插入/缺失记号，原样保留）' : '') + ' · 文件第 ' + String(t.source_record_id || '').split(':')[1] + ' 行' : R.status_zh[t.direct_observation_status] + (t.note ? '：' + t.note : '')],
          ['编号和坐标核对', t.kind === 'HLA_ALLELE' ? t.hla_allele + ' · ' + t.chromosome + ' 号染色体 HLA 区域；HLA 分型不是单个坐标，不按坐标核对' : (t.rsid || t.gene) + ' · ' + (t.chromosome || '') + (t.position ? ':' + t.position : '') + (t.genome_build ? '（' + t.genome_build + '）' : '（参考基因组版本未知）') + (t.coord_check === 'MATCH' ? ' · 与登记表一致' : t.coord_check === 'MISMATCH' ? ' · 与登记表不一致' : '') + (t.observed_genotype && t.note ? ' · ' + t.note : '')],
          ['文献来源', null], ['统计关联', (t.allele_effect_direction || '—') + (t.evidence_population ? ' · 人群：' + t.evidence_population : '') + (t.required_variant ? ' · 关注的变异：' + t.required_variant : '')],
          ['证据局限', (t.interpretation_limitations || '') + ' · ' + t.clinical_actionability + ' · ' + R.status_zh[t.clinical_confirmation_status]]];
        body = '<button class="link" id="gc-back">' + ic('chevron-left') + '返回这一组</button><div class="sub2" style="margin:8px 0">' + esc(R.status_zh[t.direct_observation_status]) + ' · ' + esc(t.detection_method || '') + '</div>' +
          steps.map(function (s, i) { return '<h3>' + (i + 1) + ' · ' + esc(s[0]) + '</h3><div class="sub2">' + (s[1] === null ? (t.evidence_url ? '<a href="' + esc(t.evidence_url) + '" target="_blank" rel="noopener" style="color:#E8B65A">' + esc(t.evidence_cite || t.evidence_doi) + '</a>' : esc(t.evidence_cite || '—')) : esc(s[1])) + '</div>'; }).join('');
      } else {
        body = '<div class="sub2">' + esc(c.sub || '') + '</div>' + (c.g04_zh ? '<div class="tip" style="margin-top:8px">' + esc(c.g04_zh) + '</div>' : '') +
          '<div style="margin-top:10px">' + rows.map(function (r) {
            return '<button class="lrow c3" data-gt="' + esc(r.target_id) + '" style="width:100%;text-align:left;background:none;border:0;border-bottom:var(--primitive-border-hairline) solid var(--theme-line-hairline);color:inherit;font:inherit;cursor:pointer"><span>' + esc(label(r)) + '</span><span class="sub2">' + esc(R.status_zh[r.direct_observation_status]) + (r.observed_genotype ? ' · ' + esc(r.observed_genotype) : '') + '</span><span>' + ic('chevron-right') + '</span></button>';
          }).join('') + '</div><div class="sub2" style="margin-top:10px" data-ptds-ui="sbaba65ea0ef1">分母是登记表里预先定下的位点，不是文件里碰巧有的位点。点一个位点看五步：原始基因型、核对、文献、关联、局限。</div>';
      }
      var box = document.createElement('div'); box.id = 'rule-pop'; box.className = 'rule-pop';
      box.innerHTML = '<div class="scrim" data-close="1"></div><aside class="drawer" role="dialog" aria-label="' + esc(c.zh) + '"><div class="dh"><span>' + esc(t ? label(t) : c.zh) + '</span><button class="ibtn" data-close="1" aria-label="关闭" data-ptds-ui-aria-label="s3fd47edce45b">' + ic('x') + '</button></div><div class="db">' + body + '</div></aside>';
      document.body.appendChild(box);
      box.querySelectorAll('[data-close]').forEach(function (b) { b.onclick = function () { box.remove(); }; });
      box.querySelectorAll('[data-gt]').forEach(function (b) { b.onclick = function () { LIVE.geneCardPop(cid, b.dataset.gt); }; });
      var bk = document.getElementById('gc-back'); if (bk) bk.onclick = function () { LIVE.geneCardPop(cid); };
      document.addEventListener('keydown', function esc1(ev) { if (ev.key === 'Escape') { box.remove(); document.removeEventListener('keydown', esc1); } });
    },
    renderGene: function () { if (window.PTDS_TRIAL_UI) return window.PTDS_TRIAL_UI.renderGene(C, call, function(key){LIVE.invalidateAfterWrite(key);});
      var esc = C.esc, ic = C.ic, real = LIVE.realNature(), list = [], last = C.st.geneLast, busy = C.st.geneBusy;
      try { list = C.MockTorch.geneList().slice().reverse(); } catch (err) { if(err&&(err.viewPending||err.code==='VIEW_CHANGED'))throw err; /* 显示为空 */ }
      var v = document.getElementById('view'), p = (last && last.profile) || {};
      var headline = function (f) { var q = f.profile || {}; return [q.format_code === 'VCF' ? q.format : (q.vendor || q.format || ''), q.snps != null ? Number(q.snps).toLocaleString('zh-CN') + ' 个位点' : q.variants != null ? Number(q.variants).toLocaleString('zh-CN') + ' 条变异' : '', q.lines_total != null ? Number(q.lines_total).toLocaleString('zh-CN') + ' 行' : ''].filter(Boolean).join(' · '); };
      v.innerHTML = '<section class="panel" data-cmp="T18">' +
        (busy ? '<div class="big" data-ptds-inline><!--ptds-ui:sc885a736fb89-->正在保存 · <!--/ptds-ui-->' + esc(busy) + '</div><div class="progress" role="status"><div>' + ic('clock') + '原样保存并记下指纹，再读一遍文件的格式和行数（不解读内容）</div></div>'
        : last ? '<div class="big">' + (last.outcome === 'DUPLICATE' ? '这份文件之前已经纳管过 · ' : '已纳管 · ') + esc(last.file_name) + '</div><div class="chan">' + ic('check') + '<span class="grow" data-ptds-inline><!--ptds-ui:sc6ee19908a6a-->原始文件已原样保存在这台电脑上，记下了指纹（SHA-256）。<!--/ptds-ui-->' + esc(headline(last)) + '。下面的“基因数据覆盖”只核对研究位点有没有，不解读。</span></div>' +
          '<section class="box"><h3>' + ic('database') + ' 数据资产属性</h3>' + LIVE.geneAttrs(last) + '<div class="sub2" data-ptds-inline><!--ptds-ui:se1795c84adc6-->性质：<!--/ptds-ui-->' + (real ? '真实' : '合成（示例文件）') + ' · 属性只描述文件本身，不读基因型含义，不做解读</div></section><div class="foot"><button class="btn" data-sem="SEM-14" id="gene-again" data-ptds-ui="sfbda5584519f">再纳管一份</button></div>'
          : '<div class="drop" id="gene-drop">' + ic('dna') + '<div data-ptds-ui="s886074cddfc0">拖入一份基因原始数据文件，一次一份（WeGene、23andMe、AncestryDNA 的 .txt/.csv/.zip，或 VCF/.vcf.gz）</div>' + (real ? '' : '<div class="opts"><button class="chip" id="gene-sample">' + ic('file-up') + '示例：基因测序数据（合成）</button></div>') + '<div class="sub2" data-ptds-ui="s2737d30c52da">星炬只纳管：原样保存、留痕、可寻源，并记下文件的格式、行数、位点数等属性；不做解读。</div></div><div class="foot"><button class="btn" data-sem="SEM-14" id="gene-pick" data-ptds-ui="s822fb37dba29">选择文件</button><input type="file" id="gene-file" hidden></div>') + '</section>' +
        LIVE.geneLookupBox() + (LIVE.geneDbFiles ? LIVE.geneCoverBox() : '') + LIVE.geneGrantBox(LIVE.geneDbFiles) +
        (list.length ? '<section class="box"><h3 data-ptds-inline><!--ptds-ui:s83dbf11c12ae-->已纳管的文件 · <!--/ptds-ui-->' + list.length + ' 份</h3>' + list.map(function (f, i) { return '<details class="more"><summary>' + esc(f.file_name) + ' <span class="sub2">· ' + esc(headline(f) || '旧回执，未记属性') + ' · ' + esc(C.tzTime(f.received_at, true)) + ' · ' + (f.outcome === 'DUPLICATE' ? '重复' : '已保存') + ' · ' + esc(f.sha256.slice(0, 12)) + '</span></summary>' + LIVE.geneAttrs(f) + '</details>'; }).join('') + '</section>' : '');
      var send = function (name, body) {
        var key=C.st.key,route=viewRoute(),job={key:C.st.key};
        C.st._geneJob=job;
        var current=function(){return C.st._geneJob===job&&C.st.key===key&&viewRoute()===route;};
        C.st.geneBusy = name; LIVE.renderGene();
        fetch('/api/gene?key=' + encodeURIComponent(key) + '&nature=' + encodeURIComponent(C.S().instance.default_nature), { method: 'POST', body: body, headers: { 'X-PTDS': '1', 'Content-Type': 'application/octet-stream', 'X-File-Name': encodeURIComponent(name) } })
          .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
          .then(function (res) { if(!current())return;C.st.geneBusy = null; if (res.ok) C.st.geneLast = res.j; else C.toast('没能纳管这份文件（' + res.j.error + '）'); })
          .catch(function (err) { if(!current())return;C.st.geneBusy = null; C.toast('没能纳管这份文件：' + err); })
          .finally(function(){if(C.st._geneJob===job)C.st.geneBusy=null;})
          .then(function () { return LIVE.loadGene(key); }).then(function(){ if (current()&&C.st.app === 'torch' && C.st.tview === 'gene') LIVE.renderGene(); });
      };
      var takeFile = function (f) { if (f) send(f.name, f); };  /* 直接交文件本身，浏览器边读边发，不整份进内存 */
      var g = function (k, fn) { var el = document.getElementById(k); if (el) el.onclick = LIVE.action(fn); };
      g('gene-again', function () { C.st.geneLast = null; LIVE.renderGene(); });
      g('gene-pick', function () { document.getElementById('gene-file').click(); });
      g('gene-sample', function () { send('示例_基因测序数据_合成.vcf', '##fileformat=VCFv4.2\n##source=PTDS-synthetic-sample\n##reference=GRCh38\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tSAMPLE\nchr1\t1000\trs0000001\tA\tG\t50\tPASS\t.\tGT\t0/1\n'); });
      var fi = document.getElementById('gene-file'); if (fi) fi.onchange = function () { takeFile(fi.files[0]); };
      var lq = document.getElementById('gene-q'), go = async function () {
        var out = document.getElementById('gene-qout'), q = lq.value.trim(); if (!q) return;
        try { var r = (await call('GET', '/api/gene/lookup?key=' + encodeURIComponent(C.st.key) + '&q=' + encodeURIComponent(q))); C.st.geneQ = { q: q, rows: r.rows }; }
        catch (err) { if(err&&(err.viewPending||err.code==='VIEW_CHANGED'))throw err; C.st.geneQ = { q: q, error: err.detail || err.code }; }
        out.innerHTML = LIVE.geneLookupOut();
      };
      if (lq) { lq.onkeydown = LIVE.action(async function (ev) { if (ev.key === 'Enter') (await go()); }); g('gene-go', go); }
      LIVE.bindGeneGrant();
      document.querySelectorAll('[data-gcard]').forEach(function (b) { b.onclick = function () { LIVE.geneCardPop(b.dataset.gcard); }; });
      g('gcov-rule', function () { LIVE.goRule('GENE'); });
      var dz = document.getElementById('gene-drop');
      if (dz) { dz.ondragover = function (e) { e.preventDefault(); }; dz.ondrop = function (e) { e.preventDefault(); takeFile(e.dataTransfer.files[0]); }; }
    },
    /* 更正/撤回后的说明行：更新了哪个时点、等级变没变、有没有新提醒（都取星轨的历次计算与同步结果） */
    updateNote: function (sy, snap) {
      var LZ = { ALERT: '关注', WATCH: '观察', UNDETERMINED: '无法判定', NONE: '无' }, parts = [];
      (sy.updated || []).concat(sy.new || []).forEach(function (tp) {
        var rr = ((snap.runs_by_tp || {})[tp]) || [], cur = rr[rr.length - 1], pv = rr[rr.length - 2];
        if (!cur) parts.push(tp); else if (!pv) parts.push(tp + ' 等级' + LZ[cur.level]);
        else parts.push(tp + (pv.level === cur.level ? ' 等级未变（' + LZ[cur.level] + '）' : ' 等级 ' + LZ[pv.level] + ' → ' + LZ[cur.level]));
      });
      if (!parts.length) return '已交给星轨，没有时点需要重新计算';
      return '刚刚按新数据自动更新 ' + parts.join('；') + (sy.alert ? '；有一条新提醒' : '；没有新提醒');
    },
    /* Original bytes/text stay separate from editable recognition fields. */
    originalHtml: function (o) {
      var esc = C.esc, name = o.name || '文件原文', src = o.original ? '/api/torch/original?key=' + encodeURIComponent(C.st.key) + '&name=' + encodeURIComponent(o.original) : o.previewUrl;
      if (!o.original && src && !/^blob:/.test(src)) src = null;
      var pdf = /\.pdf$/i.test(o.original || name), renderedPdf = pdf && !!o.original, body;
      var page = Math.max(1, Number((o.batch || {}).page) || 1), previewSrc = renderedPdf ? src + '&preview_page=' + page : src;
      if (!document.getElementById('original-preview-css')) {
        var style = document.createElement('style'); style.id = 'original-preview-css';
        style.textContent = '.original-preview{min-width:0;border:1px solid var(--theme-line-hairline);border-radius:12px;overflow:hidden;align-self:start}.original-toolbar{display:flex;gap:8px;align-items:center;flex-wrap:wrap;padding:12px;border-bottom:1px solid var(--theme-line-hairline)}.original-toolbar strong{margin-right:auto;overflow-wrap:anywhere}.original-stage{height:62vh;min-height:300px;overflow:auto;background:var(--theme-surface-raised)}.original-stage img{display:block;width:100%;max-width:none;height:auto;transform-origin:top left}.original-stage pre{margin:0;padding:16px;font:inherit;font-size:14px;line-height:1.7;white-space:pre;min-width:max-content}.original-stage iframe{width:100%;height:100%;border:0;background:white}.original-preview .original-missing{padding:24px}.original-preview .original-error{padding:12px;color:var(--theme-text-secondary)}.original-compare{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:var(--primitive-space-5);align-items:start}.original-fields{min-width:0;overflow-x:auto}.original-dialog{width:94vw;max-width:1400px;max-height:94vh;padding:16px;background:var(--theme-surface-raised);color:var(--theme-text-primary);border:1px solid var(--theme-line-control);border-radius:14px}.original-dialog::backdrop{background:rgba(0,0,0,.35)}.original-dialog>.original-toolbar{padding:0 0 12px}.original-dialog .original-stage{height:72vh}.original-dialog .original-preview{border:0}@media(max-width:900px){.original-compare{grid-template-columns:1fr}.original-stage{height:48vh}}';
        document.head.appendChild(style);
      }
      if (src && (o.original || /^blob:/.test(src))) {
        body = pdf && !renderedPdf ? '<iframe title="' + esc(name) + ' · PDF原文" src="' + esc(src) + '#page=' + Math.max(1, Number((o.batch || {}).page) || 1) + '&view=FitH"></iframe>' : '<img alt="' + esc(name) + ' · 文件原文" src="' + esc(previewSrc) + '">';
      } else if (o.text != null) body = '<pre>' + esc(o.text) + '</pre>';
      else body = '<div class="original-missing" data-ptds-ui="s17be46ce6f5b">原件暂不可用，请重新选择文件。右侧为识别字段。</div>';
      return '<section class="original-preview" data-original-panel><div class="original-toolbar"><strong data-ptds-ui="se6851bb078ec">文件原文</strong>' + (!pdf || renderedPdf ? '<button type="button" class="chip" data-original-scale="-" aria-label="缩小原文" data-ptds-ui-aria-label="s0e555ea3f78b">−</button><button type="button" class="chip" data-original-scale="1" aria-label="重置原文缩放" data-ptds-ui-aria-label="sf2e243562c02">100%</button><button type="button" class="chip" data-original-scale="+" aria-label="放大原文" data-ptds-ui-aria-label="sc3b22f595728">＋</button>' : '') + '<button type="button" class="chip" data-original-expand data-ptds-ui="s92630d631453">放大查看</button>' + (src ? '<a class="link" href="' + esc(src) + '" target="_blank" rel="noopener">打开原件</a>' : '') + '</div><div class="original-stage">' + body + '</div><div class="original-error" hidden data-ptds-ui="scec3bd7a8c2a">浏览器无法预览此格式，请用“打开原件”查看。</div></section>';
    },
    bindOriginal: function (root) {
      root = root || document.getElementById('view');
      if (!root) return;
      root.querySelectorAll('[data-original-panel]').forEach(function (panel) {
        var reset = panel.querySelector('[data-original-scale="1"]'), scale = reset ? parseFloat(reset.textContent) / 100 || 1 : 1, img = panel.querySelector('img'), pre = panel.querySelector('pre');
        if (img) img.onerror = function () { panel.querySelector('.original-error').hidden = false; };
        panel.querySelectorAll('[data-original-scale]').forEach(function (button) { button.onclick = function () {
          var value = button.dataset.originalScale; scale = value === '1' ? 1 : Math.max(.5, Math.min(4, scale + (value === '+' ? .25 : -.25)));
          if (img) img.style.width = (scale * 100) + '%'; if (pre) pre.style.fontSize = (14 * scale) + 'px';
          panel.querySelector('[data-original-scale="1"]').textContent = Math.round(scale * 100) + '%';
        }; });
        var expand = panel.querySelector('[data-original-expand]');
        if (expand) expand.onclick = function () {
          var dialog = document.createElement('dialog'); dialog.className = 'original-dialog'; dialog.setAttribute('aria-label', '放大查看文件原文');
          dialog.innerHTML = '<div class="original-toolbar"><strong data-ptds-ui="se6851bb078ec">文件原文</strong><button type="button" class="chip" data-original-close aria-label="关闭放大原文" data-ptds-ui-aria-label="sf2bcbc27d674" data-ptds-ui="sfec81f2d7742">关闭 ×</button></div>' + panel.outerHTML;
          dialog.querySelector('[data-original-expand]').remove(); document.body.appendChild(dialog); LIVE.bindOriginal(dialog);
          dialog.querySelector('[data-original-close]').onclick = function () { dialog.close(); };
          dialog.onclose = function () { dialog.remove(); if (expand.isConnected) expand.focus(); }; dialog.showModal();
        };
      });
    },
    releaseOriginal: function (o) { if (o && o.previewUrl) { URL.revokeObjectURL(o.previewUrl); delete o.previewUrl; } },
    /* 识别结果页：识别后的总结（只复述原文，不是诊断）+ 原件 */
    ocrExtras: function (o) {
      var esc = C.esc, ic = C.ic, sm = o.summary, out = '';
      if (o.conflicts && o.conflicts.length) out += '<div class="box"><h3>' + ic('circle-alert') + ' 和星炬里已有的不一样</h3><div class="sub2">' + o.conflicts.map(esc).join('<br>') + '</div><div class="sub2" data-ptds-ui="s35c94418eca6">确认这一项就会再存一条，原来的照旧保留；不想存就点 ×。</div></div>';
      if (o.notice) out += '<div class="box" data-sem="SEM-24"><h3>' + ic('info') + ' 这份文件不做逐项识别</h3><div>' + esc(o.notice) + '</div><div class="sub2" data-ptds-ui="s7fec42c1c4b5">程序按规则判断，没有用模型</div></div>';
      if (sm && sm.text) out += '<div class="box" data-sem="SEM-24"><h3>' + ic('file-text') + ' 这份化验单说了什么</h3><div>' + esc(sm.text) + '</div><div class="sub2">' +
        (sm.by.indexOf('星灵') === 0 ? esc(sm.by) + '，只复述原文，未经核对，不是诊断' : '按报告自己标的偏高偏低整理' + (sm.rejected ? '（千问写的总结没通过核对，没有采用）' : '（本机千问没有在运行）')) + '</div></div>';
      if (o.original) out += '<div><a class="chip" href="/api/torch/original?key=' + encodeURIComponent(C.st.key) + '&name=' + encodeURIComponent(o.original) + '" target="_blank" rel="noopener">' + ic('file-image') + ' 查看原图（保存在这台电脑上）</a></div>';
      return out;
    },
    ouraErasureModule: function(done){if(window.PTDS_OURA_ERASURE)return done(window.PTDS_OURA_ERASURE);var s=document.createElement('script');s.src='/assets/oura_erasure.js';s.onload=function(){done(window.PTDS_OURA_ERASURE);};s.onerror=function(){s.remove();};document.head.appendChild(s);},
    openVitalSource: function (code) {
      var i = ((C.S().vitals || {}).items || []).filter(function (x) { return x.code === code; })[0]; if (!i) return;
      C.closeDrawer(); C.st.drawer = 'live';
      var sc = document.createElement('div'); sc.className = 'scrim'; sc.id = 'scrim'; sc.onclick = C.closeDrawer;
      var el = document.createElement('aside'); el.className = 'drawer'; el.id = 'drawer'; el.setAttribute('role', 'dialog'); el.setAttribute('aria-modal', 'true'); el.setAttribute('aria-label', '数据寻源');
      var esc = C.esc, when = i.observed_at ? C.tzTime(i.observed_at, true) : (i.observed_date || '时间未知') + '（只有日期）';
      el.innerHTML = '<div class="dh"><span>' + esc(i.label_zh) + ' · 数据寻源</span><button class="ibtn" id="dclose" aria-label="关闭" title="关闭" data-ptds-ui-aria-label="s3fd47edce45b" data-ptds-ui-title="s3fd47edce45b">' + C.ic('x') + '</button></div><div class="db">' +
        '<div class="sub2" data-ptds-inline><!--ptds-ui:s1554964a6a14-->最近一次读数从哪来、什么时候、第几版，都留了痕。共 <!--/ptds-ui-->' + i.count + ' 条。</div>' +
        '<div class="item"><div class="big">' + esc(i.value) + ' <span class="u">' + esc(i.unit || '') + '</span></div><div class="kv2"><span data-ptds-ui="s8b6ff498515b">时间</span><span>' + esc(when) + '</span><span data-ptds-ui="sa488e93d69cc">来源</span><span>' + esc(SRC_NAME[i.source_kind] || i.source_kind) + ' · ' + (i.nature === 'SYNTHETIC' ? '合成' : '真实') + '</span><span data-ptds-ui="sf0b3e9f4c14b">原始记录</span><span>' + esc(i.source_ref) + '</span><span data-ptds-ui="s5f76b2bf82dd">版本</span><span>' + esc(i.observation_id) + ' · 第 ' + i.revision + ' 版</span><span data-ptds-ui="s0ab85a5324c7">是否最新</span><span>' + (i.fresh ? '最新' : '不是最新') + '</span></div></div>' +
        '<div><button class="btn" data-sem="SEM-14" id="open-torch-live">' + C.ic('external-link') + '在星炬中打开</button></div></div>';
      document.body.appendChild(sc); document.body.appendChild(el); if(i.source_kind==='DEVICE_OURA'){var ek=C.st.key;LIVE.ouraErasureModule(function(m){m.markSource({host:el,key:ek,source_ref:i.source_ref,current:function(){return el.isConnected&&C.st.key===ek;}});});}
      document.getElementById('dclose').onclick = C.closeDrawer;
      document.getElementById('open-torch-live').onclick = function () { C.closeDrawer(); C.st.tview = 'data'; C.setSeg('data-app', 'torch'); C.render(); };
    },
    /* 化验单识别：原件交给本机进程（本机 OCR + 本机千问），返回待逐项确认的候选；不保存 */
    recognizeFile: async function (file, e, again) {
      var key=C.st.key,route=viewRoute(),pending={name:file.name,phase:'ocr',rows:[],unmatched:[]};
      var current=function(){return C.st.key===key&&viewRoute()===route&&C.st.entry===e&&e.ocr===pending;};
      LIVE.releaseOriginal(e.ocr);pending.previewUrl=URL.createObjectURL(file);e.ocr=pending;again();
      try {
        var engine=await call('GET','/api/torch/engine?key='+encodeURIComponent(key));
        if(!current()){LIVE.releaseOriginal(pending);return;}
        pending.engine=engine;
        var buf=await file.arrayBuffer();
        if(!current()){LIVE.releaseOriginal(pending);return;}
        var r=await call('POST','/api/torch/recognize?key='+encodeURIComponent(key)+'&name='+encodeURIComponent(file.name),buf,true,{'Content-Type':'application/octet-stream'});
        if(!current()){LIVE.releaseOriginal(pending);return;}
        r.phase='done';if(!r.original)r.previewUrl=pending.previewUrl;else LIVE.releaseOriginal(pending);
        e.ocr=r;e.osel=0;e.date=r.date;e.time=r.time;e.nature=r.nature;again();
      } catch(err){
        LIVE.releaseOriginal(pending);
        if(e.ocr===pending)e.ocr=null;
        if(C.st.key!==key||viewRoute()!==route||C.st.entry!==e)return;
        again();var why={OCR_UNSUPPORTED:'本机不支持化验单识别，可以改用表格导入或手工录入',OCR_ENGINE_UNAVAILABLE:'本机识别程序暂不可用，可以改用表格导入或手工录入'}[err.code];
        C.toast(why||'识别没有完成：'+(err.detail||err.code||err.message));
      }
    },
    key: function () { return C.st.key; },
    /* ---------- 星轨 · 自定义状态卡（早期测试）：卡墙、卡片详情、「增加我的状态」"自定义规则"向导 ---------- */
    CC_CSS: '.cc-row{display:grid;grid-template-columns:minmax(7em,1fr) minmax(6em,1fr) minmax(0,3fr) auto;gap:var(--primitive-space-3);align-items:center;padding:var(--primitive-space-2) 0;border-top:var(--primitive-border-hairline) solid var(--theme-line-hairline)}' +
      '.cc-row .lvx{display:inline-flex;gap:var(--primitive-space-1);align-items:center}.cc-row .lvx svg{width:1.2em;height:1.2em;overflow:visible}.cc-row .lvname{font-size:inherit}' +
      '.cc-trend{width:100%;height:auto;max-height:160px;display:block}.cc-trend .ln{fill:none;stroke:var(--theme-text-secondary);stroke-width:1.5}.cc-trend .th{stroke:var(--theme-level-watch-text);stroke-dasharray:4 4;stroke-width:1}' +
      '.cc-trend circle{fill:var(--theme-text-primary)}.cc-trend text{fill:var(--theme-text-tertiary);font-size:11px}' +
      '.cc-pick{display:grid;grid-template-columns:auto minmax(0,1fr) auto;gap:var(--primitive-space-2) var(--primitive-space-3);align-items:center}' +
      '.cc-field{display:grid;gap:var(--primitive-space-2)}.cc-field input[type=text]{max-width:22em}' +
      '@media (max-width:640px){.cc-row{grid-template-columns:1fr 1fr}.cc-row>span:nth-child(3){grid-column:1/-1}}',
    ccCss: function () { if (!document.getElementById('cc-css')) { var s = document.createElement('style'); s.id = 'cc-css'; s.textContent = LIVE.CC_CSS; document.head.appendChild(s); } },
    customOk: function (t) { return !C.isReplay() && (t.maturity === 'ready' || t.maturity === 'beta'); },
    customOf: function (id) { return (C.S().custom_cards || []).filter(function (c) { return c.card_id === id; })[0]; },
    customWall: function () {
      var esc = C.esc, ic = C.ic;
      return (C.S().custom_cards || []).map(function (c) {
        var cur = c.current;
        return '<button class="wcard lv-' + (cur ? cur.level : 'NONE') + '" data-ccard="' + esc(c.card_id) + '" data-cmp="S18" data-sem="SEM-32"><span class="wn">' + esc(c.name) + '<span class="grow"></span>' +
          (c.new_alert ? '<span class="tag">' + ic('bell') + ' 有新提醒</span>' : '') + '<span class="tag" data-ptds-ui="s4eafa9e925b3">自定义</span></span><span class="sub2">' + esc(c.rule_zh) + '</span>' +
          (cur ? '<span class="wl">' + C.levelSvg(cur.level, '') + '<span class="lvname">' + esc(cur.level_zh) + '</span></span><span class="daterow" style="font-size: var(--scale-type-meta)"><span>' + esc(cur.tp) + '</span>' + (cur.stale ? '<span class="badge">' + ic('clock') + '数据有更新，等计算</span>' : '') + '</span>'
            : '<span class="sub2" data-ptds-ui="sda7c6f3f7674">还没有可以计算的时点</span>') + '</button>';
      }).join('');
    },
    bindCustomWall: function () {
      document.querySelectorAll('[data-ccard]').forEach(function (b) { b.onclick = function () { C.st.ccard = b.dataset.ccard; C.st.ccAsk = null; C.st.view = 'custom'; C.render(); window.scrollTo(0, 0); }; });
      document.querySelectorAll('[data-sleep]').forEach(function (b) { b.onclick = function () { C.st.view = 'sleep'; C.render(); window.scrollTo(0, 0); }; });
    },
    customCrumb: function () {
      if (C.st.view === 'sleep') return [{ t: '我的状态', go: function () { C.goTrack('wall'); } }, { t: '睡眠' }];
      var c = LIVE.customOf(C.st.ccard);
      return [{ t: '我的状态', go: function () { C.st.ccard = null; C.goTrack('wall'); } }, { t: c ? c.name : '自定义状态卡' }];
    },
    ccValue: function (r, unit) {
      if (!r || !r.value) return '';
      var v = function (x) { return (x.comparator || '') + x.value + (unit ? ' ' + unit : ''); };
      if (r.method === 'ABOVE' || r.method === 'BELOW') return (r.readings > 1 ? '当天' + (r.method === 'ABOVE' ? '最高' : '最低') + ' ' : '') + v(r.value) + (r.readings > 1 ? '（共 ' + r.readings + ' 条读数）' : '');
      return v(r.value) + (r.base ? '，上一个时点 ' + r.base.tp + '：' + v(r.base) : '') + (r.change_pct != null ? '，变化 ' + (+r.change_pct > 0 ? '+' : '') + r.change_pct + '%' : '');
    },
    ccTrend: function (c) {
      var pts = (c.series || []).map(function (p) { return { tp: p.tp, v: +p.v }; }).filter(function (p) { return isFinite(p.v); });
      if (pts.length < 2) return '';
      var d = c.definition, thr = (d.method === 'ABOVE' || d.method === 'BELOW') ? +d.threshold : null, vs = pts.map(function (p) { return p.v; });
      if (thr != null) vs.push(thr);
      var lo = Math.min.apply(null, vs), hi = Math.max.apply(null, vs), W = 900, H = 150, pad = 16, span = hi - lo || 1;
      var X = function (i) { return pad + i * (W - 2 * pad) / (pts.length - 1); }, Y = function (v) { return H - pad - (v - lo) / span * (H - 2 * pad); };
      return '<svg class="cc-trend" viewBox="0 0 ' + W + ' ' + H + '" role="img" aria-label="' + C.esc(d.label_zh) + '的读数轨迹">' +
        (thr != null ? '<line class="th" x1="0" x2="' + W + '" y1="' + Y(thr) + '" y2="' + Y(thr) + '"/><text x="4" y="' + (Y(thr) - 4) + '">阈值 ' + C.esc(d.threshold) + '</text>' : '') +
        '<polyline class="ln" points="' + pts.map(function (p, i) { return X(i) + ',' + Y(p.v); }).join(' ') + '"/>' +
        pts.map(function (p, i) { return '<circle cx="' + X(i) + '" cy="' + Y(p.v) + '" r="2.5"><title>' + C.esc(p.tp + '：' + p.v) + '</title></circle>'; }).join('') +
        '<text x="' + pad + '" y="' + (H - 1) + '">' + C.esc(pts[0].tp) + '</text><text x="' + (W - pad) + '" y="' + (H - 1) + '" text-anchor="end">' + C.esc(pts[pts.length - 1].tp) + '</text></svg>';
    },
    renderCustom: function () {
      var esc = C.esc, ic = C.ic, st = C.st, c = LIVE.customOf(st.ccard), v = document.getElementById('view');
      LIVE.ccCss();
      if (!c) { v.innerHTML = '<div class="empty" data-cmp="G10"><div data-ptds-ui="s4eb97546b1e8">这张卡已经停用，或者不在这份数据里。</div><button class="btn2" id="cc-wall">' + ic('layout-grid') + '回到我的状态</button></div>'; document.getElementById('cc-wall').onclick = function () { C.goTrack('wall'); }; return; }
      var d = c.definition, cur = c.current, unit = c.unit_zh, TRZ = { SYNC: '数据到达后计算', AUTO_UPDATE: '来源更新后自动更新', RECOMPUTE: '改规则后重算' };
      var tpl = ((C.DATA.product || {}).templates || []).filter(function (t) { return t.id === 'CUSTOM'; })[0] || {};
      var mt = { beta: '早期测试', dev: '开发中', plan: '规划中' }[tpl.maturity];
      var ask = st.ccAsk === 'stop' ? '<div class="confirm"><div data-ptds-ui="s399a8e4cf6ff">停用后这张卡不再计算、不再提醒；已有的计算和提醒记录都保留。</div><div class="acts"><button class="btn" id="cc-stop-ok">' + ic('check') + '确认停用</button><button class="ibtn" id="cc-stop-no" aria-label="取消" title="取消" data-ptds-ui-aria-label="s2cd0f3be8738" data-ptds-ui-title="s2cd0f3be8738">' + ic('x') + '</button></div></div>' : '';
      var html = '<section class="box" data-cmp="S18" data-sem="SEM-32"><h3>' + esc(c.name) + '<span class="grow"></span>' + (mt ? '<span class="tag">' + mt + '</span>' : '') + '<span class="tag" data-ptds-ui="s4eafa9e925b3">自定义</span></h3>' +
        '<div>' + esc(c.rule_zh) + '</div>' + (c.note ? '<div class="sub2">' + esc(c.note) + '</div>' : '') +
        (cur ? '<div class="wl lv-' + cur.level + '" style="display:flex;gap:var(--primitive-space-3);align-items:center">' + C.levelSvg(cur.level, '').replace('<svg', '<svg width="2.2em" height="2.2em"') + '<span class="lvname big">' + esc(cur.level_zh) + '</span><span class="sub2" data-ptds-inline><!--ptds-ui:s768ac1d2b215-->最新时点 <!--/ptds-ui-->' + esc(cur.tp) + (cur.stale ? ' · 数据有更新，等计算' : '') + '</span></div>' : '<div class="sub2" data-ptds-ui="s9d6e4d52dece">星轨里还没有这一项带日期的读数，读数一到就会计算。</div>') +
        LIVE.ccTrend(c) +
        '<div class="opts"><button class="chip" id="cc-edit">' + ic('settings') + '改规则</button><button class="chip" id="cc-stop">' + ic('x') + '停用这张卡</button></div>' + ask +
        '<div class="sub2">' + esc(c.note_zh) + ' 数据来自星轨收到的' + esc(d.label_zh) + '读数（' + (c.series || []).length + ' 个时点）。</div></section>';
      html += '<section class="box"><h3>' + ic('history') + ' 每个时点</h3>' + (c.timepoints.length ? c.timepoints.map(function (t) {
        var r = t.result, ref = r && r.value && r.value.ref;
        return '<div class="cc-row"><span>' + esc(t.tp) + '</span><span class="lvx lv-' + (t.level || 'NONE') + '">' + (t.level ? C.levelSvg(t.level, '') + '<span class="lvname">' + esc(t.level_zh) + '</span>' : '<span class="sub2" data-ptds-ui="seffc02a3ac34">没算</span>') + '</span>' +
          '<span>' + esc(LIVE.ccValue(r, unit)) + (t.outcome_zh ? '<span class="sub2"> · ' + esc(t.outcome_zh) + (t.reason_zh ? '：' + esc(t.reason_zh) : '') + '</span>' : '') + (t.status === 'STALE' ? '<span class="sub2" data-ptds-ui="sabb5a4d2ced4"> · 数据有更新，等计算</span>' : '') + (t.run_id ? '<span class="sub2" data-ptds-inline><!--ptds-ui:s69297c6c18d9--> · 计算 #<!--/ptds-ui-->' + t.run_id + '</span>' : '') + '</span>' +
          '<span>' + (ref ? '<button class="ibtn" data-cc-obs="' + esc(ref) + '" aria-label="在星炬中打开这条数据" title="在星炬中打开这条数据">' + ic('file-text') + '</button>' : '') + (t.run_id ? '<button class="ibtn" data-cc-trace="' + esc(t.tp) + '" aria-label="在证据图谱里追溯" title="在证据图谱里追溯">' + ic('waypoints') + '</button>' : '') + '</span></div>';
      }).join('') : '<div class="sub2" data-ptds-ui="scc91367ef114">还没有时点。</div>') + '</section>';
      html += '<section class="box"><h3>' + ic('bell') + ' 这张卡的提醒</h3>' + (c.alerts.length ? c.alerts.slice().reverse().map(function (a) {
        return '<div class="lrow"><span class="lvx lv-' + a.level + '">' + esc(a.level_zh) + ' · ' + esc(a.tp) + '</span><span class="sub2">' + esc(a.body) + '<br>' + esc(C.tzTime(a.created_at)) + ' · ' + (a.deliveries.map(function (x) { return ({ BANNER: '站内', MACOS: 'Mac 通知', SOMALOOP: '手环' }[x.channel] || x.channel) + (x.outcome === 'SENT' ? '已送达' : '未送达'); }).join('、') || '没有通道') + '</span><span>' +
          (a.acked ? '<span class="sub2">' + ic('check') + ' 已知道</span>' : '<button class="ibtn" data-cc-ack="' + esc(a.dedupe_key) + '" aria-label="知道了" title="知道了">' + ic('check') + '</button>') + '</span></div>';
      }).join('') : '<div class="sub2" data-ptds-ui="s07a9033efef6">还没有提醒。等级比上一次记下的高时提醒，同一时点同一等级只提醒一次。</div>') + '</section>';
      html += '<section class="box"><h3>' + ic('file-text') + ' 规则版本与计算记录</h3>' + c.versions.slice().reverse().map(function (x, i) { return '<div class="lrow"><span>' + (i === 0 ? '现在的规则' : '之前的规则') + '</span><span class="sub2">' + esc(x.rule_zh) + '</span><span class="sub2">' + esc(C.tzTime(x.set_at)) + '</span></div>'; }).join('') +
        '<div class="sub2" data-ptds-inline><!--ptds-ui:sac3754f80851-->改规则会生成新的定义并重算全部时点；之前规则下的结果都保留。最近的计算：<!--/ptds-ui-->' + c.runs.slice(-5).reverse().map(function (r) { return '#' + r.run_id + ' ' + (TRZ[r.trigger] || r.trigger); }).join('、') + '</div></section>';
      v.innerHTML = html;
      var g = function (k, fn) { var el = document.getElementById(k); if (el) el.onclick = LIVE.action(fn); };
      g('cc-edit', function () { st.eng = { step: 2, tpl: 'CUSTOM', sel: {}, cc: { card_id: c.card_id, code: d.code, name: d.name, note: d.note, method: d.method, threshold: d.threshold, level: d.level, notify_self: d.notify_self } }; C.goTrack('eng'); });
      g('cc-stop', function () { st.ccAsk = 'stop'; LIVE.renderCustom(); });
      g('cc-stop-no', function () { st.ccAsk = null; LIVE.renderCustom(); });
      g('cc-stop-ok', LIVE.action(async function () {
        st.ccAsk = null;
        try { var r = (await call('POST', '/api/track/custom', { key: st.key, action: 'stop', card_id: c.card_id })); C.SNAPS[st.key] = r.snapshot; C.toast('已停用"' + c.name + '"，记录都保留'); C.goTrack('wall'); }
        catch (err) { if(err&&(err.viewPending||err.code==='VIEW_CHANGED'))throw err; C.toast('没有停用成功：' + err.message); }
      }));
      document.querySelectorAll('[data-cc-obs]').forEach(function (b) { b.onclick = function () { C.openTorchDetail(b.dataset.ccObs, 'track'); }; });
      document.querySelectorAll('[data-cc-trace]').forEach(function (b) { b.onclick = function () { LIVE.graphCards = null; LIVE.openTrace(c.card_id, b.dataset.ccTrace); }; });
      document.querySelectorAll('[data-cc-ack]').forEach(function (b) { b.onclick = LIVE.action(async function () { (await call('POST', '/api/track/ack', { key: st.key, dedupe_key: b.dataset.ccAck })); (await LIVE.refresh()); LIVE.renderCustom(); }); });
    },
    renderEngCustom: function (e) {
      var esc = C.esc, ic = C.ic, v = document.getElementById('view'), STEPS = ['选模板', '绑数据', '定规则', '配通知', '审方案'];
      LIVE.ccCss();
      var cc = e.cc = e.cc || { code: null, name: '', note: '', method: 'ABOVE', threshold: '', level: 'WATCH', notify_self: true };
      if (!e.avail) { try { var r0 = readCached('/api/track/custom?key=' + encodeURIComponent(C.st.key)); e.avail = r0.available; e.methods = r0.methods; } catch (err) { if(err&&(err.viewPending||err.code==='VIEW_CHANGED'))throw err; e.avail = []; e.methods = {}; } }
      var item = e.avail.filter(function (a) { return a.code === cc.code; })[0], pct = cc.method === 'RISE' || cc.method === 'FALL';
      var unitOf = function () { return pct ? '%' : (item ? item.unit_zh : ''); };
      var valid = function () { var t = String(cc.threshold).trim(); return !!cc.name.trim() && /^-?\d+(\.\d+)?$/.test(t) && (!pct || (+t > 0 && +t <= 1000)); };
      var ruleText = function () { return (item ? item.label_zh : '') + (e.methods[cc.method] || '') + ' ' + (cc.threshold || '？') + (pct ? '%' : (item && item.unit_zh ? ' ' + item.unit_zh : '')) + '，等级为' + (cc.level === 'ALERT' ? '关注' : '观察'); };
      var body = '', can = true;
      if (e.step === 1) {
        if (!e.avail.length) { body = '<div class="empty" data-cmp="G10"><div data-ptds-ui="s2ecb7b7c2c11">星轨里还没有带数值的读数。</div><div class="tip" data-ptds-ui="s929c821748dc">先在星炬录入化验单或接入设备，读数交给星轨后回到这一步。</div><button class="btn2" id="cc-go-torch">' + ic('inbox') + '去星炬</button></div>'; can = false; }
        else {
          var fam = null;
          body = '<div class="sub2" data-ptds-ui="se0e5b759131f">这张卡看哪一项数据？只能选一项，只用星轨已经收到的读数。</div><section class="confirm cc-pick" data-cmp="T10" data-sem="SEM-18">' + e.avail.map(function (a) {
            var h = (a.family_zh !== fam ? '<div class="sub2" style="grid-column:1/-1">' + esc(a.family_zh) + '</div>' : ''); fam = a.family_zh;
            return h + '<input type="radio" name="cc-code" id="cc-c-' + esc(a.code) + '" data-cc-code="' + esc(a.code) + '"' + (cc.code === a.code ? ' checked' : '') + '><label for="cc-c-' + esc(a.code) + '">' + esc(a.label_zh) + '</label><span class="sub2">' + a.days + ' 天 · 最近 ' + esc(a.last_tp) + '：' + esc(a.last) + (a.unit_zh ? ' ' + esc(a.unit_zh) : '') + '</span>';
          }).join('') + '</section>';
          can = !!item;
        }
      } else if (e.step === 2) {
        if (!cc.name && item) cc.name = '我的' + item.label_zh.replace(/（.*）$/, '');
        body = '<section class="confirm" data-sem="SEM-31"><div class="cc-field"><label for="cc-name" data-ptds-ui="s213c8c22556a">卡片名</label><input type="text" id="cc-name" maxlength="24" value="' + esc(cc.name) + '"></div>' +
          '<div class="cc-field"><span data-ptds-ui="s1123245d1bed">规则</span><div class="chips" role="group" aria-label="规则" data-ptds-ui-aria-label="s1123245d1bed">' + Object.keys(e.methods).map(function (m) { return '<button class="chip" data-cc-m="' + m + '" aria-pressed="' + (cc.method === m) + '">' + esc(e.methods[m]) + '</button>'; }).join('') + '</div></div>' +
          '<div class="cc-field"><label for="cc-thr">' + (pct ? '变化超过（百分比）' : '阈值') + '</label><span><input type="text" inputmode="decimal" id="cc-thr" style="max-width:9em" value="' + esc(cc.threshold) + '"> ' + esc(unitOf()) + '</span>' + (item ? '<span class="sub2" data-ptds-inline><!--ptds-ui:s31c27a0029ba-->最近一次：<!--/ptds-ui-->' + esc(item.last) + (item.unit_zh ? ' ' + esc(item.unit_zh) : '') + '（' + esc(item.last_tp) + '）</span>' : '') + '</div>' +
          '<div class="cc-field"><span data-ptds-ui="s4e4e32c17d47">达到时，这张卡显示</span><div class="chips" role="group" aria-label="等级" data-ptds-ui-aria-label="s337717173807"><button class="chip" data-cc-l="WATCH" aria-pressed="' + (cc.level === 'WATCH') + '">观察</button><button class="chip" data-cc-l="ALERT" aria-pressed="' + (cc.level === 'ALERT') + '">关注</button></div></div>' +
          '<div id="cc-rule">' + esc(ruleText()) + '</div>' +
          '<div class="sub2">' + (pct ? '每个时点取当天最后一条读数，和上一个有读数的时点比；第一个时点没有可比的，显示无法判定。' : '当天任一条读数' + (cc.method === 'ABOVE' ? '高于' : '低于') + '阈值就算达到。') + '规则是你自己定的，不是医学规则；卡片名里不能有诊断字样。</div>' +
          (item ? '' : '<div class="tip">' + ic('info') + ' 先在上一步选一项数据。</div>') + '</section>';
        can = valid() && !!item;
      } else if (e.step === 3) {
        body = '<section class="confirm" data-sem="SEM-31"><div data-ptds-ui="s14f2281bfe91">这张卡会产生的状态通知：等级比上一次记下的高时提醒一次，同一时点同一等级只提醒一次。</div>' +
          '<label class="chk"><input type="checkbox" id="cc-notify"' + (cc.notify_self ? ' checked' : '') + '>通知我自己 <span class="soon" data-ptds-ui="sb60771ab59d4">本机通道：Mac 通知</span></label>' +
          '<div class="sub2" data-ptds-ui="sb6f9e9ccbb36">不勾的话，提醒只记在状态通知和这张卡里，不发到 Mac。</div><div class="sub2" data-sem="SEM-25" data-ptds-ui="s7703599ae512">发给我自己走星簇预置授权 G-001（我自己 · 本机通道 · 摘要级），不出域。</div></section>';
      } else {
        body = '<section class="confirm"><div class="kv2"><span data-ptds-ui="s62b95daecb7f">模板</span><span data-ptds-ui="s51c22886b573">自定义规则</span><span data-ptds-ui="s213c8c22556a">卡片名</span><span>' + esc(cc.name) + '</span><span data-ptds-ui="s33fa3162ff09">绑数据</span><span>' + esc(item ? item.label_zh + ' · ' + item.family_zh : '—') + '</span><span data-ptds-ui="s935514d4b5e9">定规则</span><span>' + esc(ruleText()) + '</span><span data-ptds-ui="s713f764c8dae">配通知</span><span>' + (cc.notify_self ? '通知我自己（Mac 通知）' : '只记录，不发到 Mac') + '</span><span data-ptds-ui="sbd2539694f18">出域</span><span data-sem="SEM-25" data-ptds-ui="s37e160e5d4e1">默认不出域，由星簇授权决定</span></div>' +
          '<div class="sub2">' + (cc.card_id ? '保存后按新规则把全部时点重算一遍；之前规则下的结果都保留，可以在卡片里对照。' : '创建后马上按星轨里已有的 ' + (item ? item.days : 0) + ' 个时点算一遍；最新时点已经达到的话，会提醒一次。') + '</div>' +
          (e.err ? '<div class="tip">' + ic('info') + ' ' + esc(e.err) + '</div>' : '') + '</section>';
        can = valid() && !!item;
      }
      var last = e.step === STEPS.length - 1;
      v.innerHTML = '<div class="wiz" data-cmp="S19" data-sem="SEM-31"><ol class="wsteps">' + STEPS.map(function (x, i) { return '<li' + (i === e.step ? ' aria-current="step"' : i < e.step ? ' class="done"' : '') + '>' + esc(x) + '</li>'; }).join('') + '</ol>' +
        '<section class="panel">' + body + '<div class="foot"><button class="ibtn" id="cc-back" aria-label="上一步" title="上一步" data-ptds-ui-aria-label="sda336fdc0dbd" data-ptds-ui-title="sda336fdc0dbd">' + ic('chevron-left') + '</button><button class="btn" data-sem="SEM-14" id="' + (last ? 'cc-create' : 'cc-next') + '"' + (can ? '' : ' disabled') + '>' + (last ? (cc.card_id ? '保存新规则' : '创建') : '下一步') + '</button></div></section></div>';
      var g = function (k, fn) { var el = document.getElementById(k); if (el) el.onclick = LIVE.action(fn); };
      var redo = function () { e.err = null; LIVE.renderEngCustom(e); };
      g('cc-back', function () { if (e.step === 1) { if (cc.card_id) { C.st.eng = null; C.st.view = 'custom'; C.render(); return; } e.step = 0; C.render(); return; } e.step--; redo(); });
      g('cc-next', function () { e.step++; redo(); });
      g('cc-go-torch', function () { C.goTorch('sources'); });
      document.querySelectorAll('[data-cc-code]').forEach(function (b) { b.onchange = function () { if (cc.code !== b.dataset.ccCode) { cc.code = b.dataset.ccCode; if (!cc.card_id) cc.name = ''; } redo(); }; });
      document.querySelectorAll('[data-cc-m]').forEach(function (b) { b.onclick = function () { cc.method = b.dataset.ccM; redo(); }; });
      document.querySelectorAll('[data-cc-l]').forEach(function (b) { b.onclick = function () { cc.level = b.dataset.ccL; redo(); }; });
      var live = function () { var btn = document.getElementById('cc-next'), rl = document.getElementById('cc-rule'); if (btn) btn.disabled = !(valid() && !!item); if (rl) rl.textContent = ruleText(); };
      var nm = document.getElementById('cc-name'); if (nm) nm.oninput = function () { cc.name = nm.value; live(); };
      var th = document.getElementById('cc-thr'); if (th) th.oninput = function () { cc.threshold = th.value.trim(); live(); };
      var nt = document.getElementById('cc-notify'); if (nt) nt.onchange = function () { cc.notify_self = nt.checked; };
      g('cc-create', LIVE.action(async function () {
        try {
          var res = (await call('POST', '/api/track/custom', { key: C.st.key, card_id: cc.card_id || null, name: cc.name.trim(), note: cc.note || '', code: cc.code, method: cc.method, threshold: String(cc.threshold).trim(), level: cc.level, notify_self: !!cc.notify_self }));
          C.SNAPS[C.st.key] = res.snapshot; C.st.eng = null; C.st.ccard = res.card_id; C.st.view = 'custom';
          if ((await LIVE.restoreCreatedCard('cc:' + res.card_id))) C.toast(cc.card_id ? '已保存新规则，全部时点已重算' : '已创建"' + cc.name.trim() + '"，已按现有数据算好'); C.render(); window.scrollTo(0, 0);
        } catch (err) { if(err&&(err.viewPending||err.code==='VIEW_CHANGED'))throw err; e.err = err.detail || err.message; LIVE.renderEngCustom(e); }
      }));
    },
    /* ---------- 星轨 · 睡眠卡（早期测试）：设备睡眠读数的长期观察，只显示读数和变化，不打分 ---------- */
    trendSvg: function (pts, aria, thr, thrText, fmt) {
      fmt = fmt || String;
      pts = pts.filter(function (p) { return isFinite(p.v); });
      if (pts.length < 2) return '';
      var vs = pts.map(function (p) { return p.v; }); if (thr != null) vs.push(thr);
      var lo = Math.min.apply(null, vs), hi = Math.max.apply(null, vs), W = 900, H = 150, pad = 16, span = hi - lo || 1, esc = C.esc;
      var X = function (i) { return pad + i * (W - 2 * pad) / (pts.length - 1); }, Y = function (v) { return H - pad - (v - lo) / span * (H - 2 * pad); };
      return '<svg class="cc-trend" viewBox="0 0 ' + W + ' ' + H + '" role="img" aria-label="' + esc(aria) + '">' +
        (thr != null ? '<line class="th" x1="0" x2="' + W + '" y1="' + Y(thr) + '" y2="' + Y(thr) + '"/><text x="4" y="' + (Y(thr) - 4) + '">' + esc(thrText || '') + '</text>' : '') +
        '<polyline class="ln" points="' + pts.map(function (p, i) { return X(i) + ',' + Y(p.v); }).join(' ') + '"/>' +
        pts.map(function (p, i) { return '<circle cx="' + X(i) + '" cy="' + Y(p.v) + '" r="2.5"><title>' + esc(p.tp + '：' + (p.label || p.v)) + '</title></circle>'; }).join('') +
        '<text x="' + pad + '" y="' + (H - 1) + '">' + esc(pts[0].tp) + '</text><text x="' + (W - pad) + '" y="' + (H - 1) + '" text-anchor="end">' + esc(pts[pts.length - 1].tp) + '</text>' +
        '<text x="' + (W - pad) + '" y="12" text-anchor="end">' + esc(fmt(hi)) + '</text><text x="' + (W - pad) + '" y="' + (H - pad - 4) + '" text-anchor="end">' + esc(fmt(lo)) + '</text></svg>';
    },
    sleepLive: function (p) { return !C.isReplay() && (p.maturity === 'ready' || p.maturity === 'beta') && !!C.S().sleep; },
    slVal: function (m, v) {
      if (v == null) return '—';
      if (m.unit === 'min') { var n = Math.round(+v), h = Math.floor(Math.abs(n) / 60), r = Math.abs(n) % 60; return (n < 0 ? '-' : '') + (h ? h + ' 小时 ' : '') + r + ' 分'; }
      return v + (m.unit_zh ? ' ' + m.unit_zh : '');
    },
    sleepWall: function (p) {
      var esc = C.esc, sl = C.S().sleep || {}, ms = sl.metrics || [], pick = ['OURA_TOTAL_SLEEP', 'AH_SLEEP', 'OURA_HRV', 'OURA_SLEEP_SCORE'];
      var ordered=pick.map(function(c){return ms.find(function(m){return m.code===c;});}).filter(Boolean).concat(ms.filter(function(m){return pick.indexOf(m.code)<0;}));
      var top=LIVE.wallPick('sleep',((C.S().wall_prefs||{}).display||{}).sleep?ordered:ordered.filter(function(m){return pick.indexOf(m.code)>=0;}),function(x){return x.code;}).slice(0,3);
      var mt = { beta: '早期测试', dev: '开发中' }[p.maturity];
      return '<button class="wcard" data-sleep="1" data-cmp="S18" data-sem="SEM-32"><span class="wn">' + esc(p.zh) + '<span class="grow"></span>' + (mt ? '<span class="tag">' + mt + '</span>' : '') + '</span>' +
        '<span class="sub2">' + (sl.last_day ? '最近一晚 ' + esc(sl.last_day) + ' · ' + esc(sl.sources.join('、')) + ' · 共 ' + sl.night_count + ' 晚' : esc(p.sub)) + '</span>' +
        (top.length ? '<span class="big">' + top.map(function (m) { return esc(m.label_zh.replace(/（.*）$/, '')) + ' ' + esc(LIVE.slVal(m, m.last)); }).join('　') + '</span><span class="sub2" data-ptds-ui="sc87846341bf9">只显示读数和变化，不打分</span>' : '<span class="sub2" data-ptds-ui="sd85b04c1afc0">星轨里还没有睡眠读数。接入 Oura 后会自动出现。</span>') + '</button>';
    },
    renderSleep: function () {
      var esc = C.esc, ic = C.ic, st = C.st, sl = C.S().sleep, v = document.getElementById('view');
      LIVE.ccCss();
      if (!document.getElementById('sl-css')) { var s0 = document.createElement('style'); s0.id = 'sl-css'; s0.textContent = '.sl-tiles{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:var(--primitive-space-3)}.sl-tile{text-align:left;cursor:pointer;display:grid;gap:var(--primitive-space-1)}.sl-tbl{display:grid;gap:0;overflow-x:auto}.sl-tbl .r{display:grid;grid-template-columns:7em repeat(var(--n),minmax(5.5em,1fr));gap:var(--primitive-space-2);padding:var(--primitive-space-1) 0;border-top:var(--primitive-border-hairline) solid var(--theme-line-hairline);font-size:var(--scale-type-meta)}.sl-tbl .r.h{color:var(--theme-text-tertiary)}.sl-tbl button.link{font-size:inherit}'; document.head.appendChild(s0); }
      if (!sl || !sl.metrics.length) { v.innerHTML = '<div class="empty" data-cmp="G10"><div data-ptds-ui="s31cedc6f3803">星轨里还没有睡眠读数。</div><div class="tip" data-ptds-ui="s89cd15c6e532">在星炬接入 Oura（或用苹果健康同步睡眠），读数交给星轨后，这里按晚列出。</div><button class="btn2" id="sl-go">' + ic('inbox') + '去星炬接入设备</button></div>'; document.getElementById('sl-go').onclick = function () { C.goTorch('connect'); }; return; }
      var sign = function (x) { return x == null ? '' : (+x > 0 ? '+' : '') + x; };
      var chg = function (m) {
        var out = [];
        if (m.vs_prev != null) out.push('比上一晚 ' + (m.unit === 'min' ? sign(Math.round(+m.vs_prev)) + ' 分钟' : sign(m.vs_prev) + (m.unit_zh ? ' ' + m.unit_zh : '')) + (m.vs_prev_pct != null ? '（' + sign(m.vs_prev_pct) + '%）' : ''));
        if (m.avg7_n >= 3 && m.vs_avg7 != null) out.push('比之前 ' + m.avg7_n + ' 晚平均 ' + (m.vs_avg7_pct != null ? sign(m.vs_avg7_pct) + '%' : sign(m.vs_avg7) + (m.unit_zh ? ' ' + m.unit_zh : '')));
        return out.join(' · ') || '只有一晚，还看不出变化';
      };
      var html = '<div class="lede">每晚的睡眠读数和变化。' + esc(sl.note) + '</div>';
      html += '<section class="box" data-cmp="S18" data-sem="SEM-32"><h3>' + ic('activity') + ' 最近一晚 · ' + esc(sl.last_day) + '<span class="grow"></span><span class="tag">早期测试</span></h3><div class="sl-tiles">' + sl.metrics.map(function (m) {
        return '<button class="box sl-tile" data-sl-obs="' + esc(m.ref) + '" title="在星炬中打开这条数据"><span class="sub2">' + esc(m.label_zh) + ' · ' + esc(m.source_zh) + (m.vendor_score ? ' 给的分' : '') + '</span><span class="big">' + esc(LIVE.slVal(m, m.last)) + '</span>' +
          '<span class="sub2">' + (m.last_day !== sl.last_day ? esc(m.last_day) + ' · ' : '') + esc(chg(m)) + '</span></button>';
      }).join('') + '</div></section>';
      var trendOf = function (code) { var m = sl.metrics.filter(function (x) { return x.code === code; })[0], pts = (sl.series[code] || []).map(function (p) { return { tp: p.tp, v: +p.v, label: m ? LIVE.slVal(m, p.v) : p.v }; }); return m && pts.length > 1 ? '<div><div class="sub2">' + esc(m.label_zh) + ' · ' + pts.length + ' 晚</div>' + LIVE.trendSvg(pts, m.label_zh + '的轨迹', null, null, function (x) { return LIVE.slVal(m, x); }) + '</div>' : ''; };
      var trends = ['OURA_TOTAL_SLEEP', 'AH_SLEEP', 'OURA_HRV', 'OURA_LOWEST_HR', 'OURA_RESTING_HR'].map(trendOf).filter(Boolean).slice(0, 3).join('');
      if (trends) html += '<section class="box"><h3>' + ic('history') + ' 长期轨迹</h3>' + trends + '</section>';
      var cols = sl.metrics.slice(0, 6), rows = st.sleepAll ? sl.nights : sl.nights.slice(0, 14);
      html += '<section class="box"><h3>' + ic('file-text') + ' 每一晚<span class="grow"></span><span class="sub2">' + sl.night_count + ' 晚 · 点数值可以在星炬中打开</span></h3><div class="sl-tbl" style="--n:' + cols.length + '"><div class="r h"><span>日期</span>' + cols.map(function (m) { return '<span>' + esc(m.label_zh) + '</span>'; }).join('') + '</div>' +
        rows.map(function (n) { return '<div class="r"><span>' + esc(n.day) + '</span>' + cols.map(function (m) { var x = n.values[m.code]; return '<span>' + (x ? '<button class="link" data-sl-obs="' + esc(x.ref) + '" title="' + esc(x.source_ref || '') + '">' + esc(LIVE.slVal(m, x.value)) + '</button>' : '<span class="sub2">—</span>') + '</span>'; }).join('') + '</div>'; }).join('') + '</div>' +
        (sl.nights.length > 14 ? '<div><button class="chip" id="sl-all">' + (st.sleepAll ? '只看最近 14 晚' : '显示全部 ' + sl.nights.length + ' 晚') + '</button></div>' : '') +
        '<div class="sub2" data-ptds-ui="sd1e0f19dba72">每个数都是星轨收到的一条数据，写着来自哪台设备、哪一晚（鼠标停在数值上可以看到来源编号）。和"我的体征"共用绑定：在星炬解绑的设备不进这张卡。</div></section>';
      v.innerHTML = html;
      document.querySelectorAll('[data-sl-obs]').forEach(function (b) { b.onclick = function () { C.openTorchDetail(b.dataset.slObs, 'track'); }; });
      var all = document.getElementById('sl-all'); if (all) all.onclick = function () { st.sleepAll = !st.sleepAll; LIVE.renderSleep(); };
    },
    refresh: async function (key) {
      key = key || C.st.key;readEpoch++;if(LIVE._dataReadSession)LIVE._dataReadSession.invalidate();
      LIVE._bl = null; C.st.cpAi = null;  /* 新数据到了，MAS 页的看板和路径、整体基线洞察、千问解释都要重新取 */
      // Home has its own authoritative projection. Keep the full-history cache
      // separate; detail routes will hydrate it against the new read version.
      if (key === C.st.key && LIVE.homeReadEnabled() && (LIVE.homeRoute() || (LIVE.dataRoute&&LIVE.dataRoute())) && !C.isReplay()) {
        if(LIVE.dataRoute&&LIVE.dataRoute())LIVE.invalidateData();
        var base = C.SNAPS[key], epoch = readEpoch, route = viewRoute();
        var next = await call('GET', '/api/state/refresh?key=' + encodeURIComponent(key));
        if (C.st.key !== key || viewRoute() !== route) {
          var stale = new Error('VIEW_CHANGED'); stale.code = 'VIEW_CHANGED'; throw stale;
        }
        if (epoch !== readEpoch || pendingWrites || C.SNAPS[key] !== base) {
          // A newer read or write only supersedes this projection, not the
          // confirmed action. Navigation remains checked after the await.
          return;
        }
        return LIVE.acceptHome(key, base, next);
      }
      C.SNAPS[key] = (await call('GET', '/api/state?key=' + encodeURIComponent(key)));
      return C.SNAPS[key];
    },
    refreshAll: async function () { readEpoch++;if(LIVE._dataReadSession)LIVE._dataReadSession.invalidate();C.st.cpAi = null; var all = (await call('GET', '/api/state')); Object.keys(all).forEach(function (k) { C.SNAPS[k] = all[k]; }); return all; },
    install: function (core) {
      C = core;
      try { var th = localStorage.getItem('ptds-theme'); if (th === 'light' || th === 'dark') (core.setSeg ? core.setSeg('data-theme', th) : document.documentElement.setAttribute('data-theme', th)); } catch (e) { if(e&&(e.viewPending||e.code==='VIEW_CHANGED'))throw e; /* 默认深色 */ }
      var mtag0 = core.mtag; if (mtag0) core.mtag = function (m) {
        if (m === 'adapted') return '';  /* 产品负责人 08:30：已适配不再特殊标注 */
        if (core.st.app === 'track' && (core.st.view === 'eng' || core.st.view === 'adv')) return '';  /* r63：状态实验室也不挂（产品负责人 2026-10-15 11:02） */  /* 产品负责人 2026-10-15：「增加我的状态」里不再标“早期测试”（显得不专业） */
        return mtag0(m); };
      (function () { var s0 = document.createElement('style'); s0.textContent = '[data-nav2="eng"] .mt{display:none}'; document.head.appendChild(s0); })();  /* 左侧「增加我的状态」也不带标签 */
      var live = core.DATA.ptds_live; if (!live) return;
      if(window.PTDS_COMPUTE)window.PTDS_COMPUTE.install(core,LIVE,call);
      if (live.home) LIVE._home = live.home;
      /* 原型使用空的示意快照，这里还原成本机实时快照 */
      Object.keys(live.snapshots || {}).forEach(function (k) { core.SNAPS[k] = live.snapshots[k]; });
      document.addEventListener('click', function (ev) {  /* 批量里打开的化验单存好后：回到批量列表 */
        var b = ev.target && ev.target.closest && ev.target.closest('#go-batch'); if (!b) return;
        core.st.entry = core.newEntry(); core.st.entry.method = 'batch'; core.st.btOpen = null; core.render();
      });
      var T = core.MockTorch;
      T.save = async function (items, key) {
        key=key||core.st.key;
        var e = core.st.entry || {}, rows = [];
        items.forEach(function (it) {
          if (typeof it === 'string') rows.push({ code: it, value: (e.flags || {})[it] });
          else if (it && it.code) rows.push({ code: it.code, value: it.value, unit: it.unit, cmp: it.cmp, source_ref: it.source_ref });
        });
        e.request_id = e.request_id || rid();  /* 同一次保存重试用同一个请求号（HR-13） */
        var res;
        try {
          res = (await call('POST', '/api/torch/save', LIVE.writeBody({ key: key, method: e.method || 'manual', tpMode: e.tpMode,
            date: e.date, time: e.time, rows: rows, request_id: e.request_id, nature: e.nature })));
        } catch (err) { if(err&&(err.viewPending||err.code==='VIEW_CHANGED'))throw err; C.toast('尚未确认保存：' + LIVE.saveErr(err)); throw err; }
        if((!res.snapshot&&!LIVE.isConfirmedWrite(key,res))||!Array.isArray(res.results)){var invalid=new Error('SAVE_CONFIRMATION_MISSING');invalid.detail='未收到完整保存回执，请刷新核对；不会自动重复提交';throw invalid;}
        if(res.snapshot){core.SNAPS[key] = res.snapshot;delete res.snapshot;}
        res.counts = { CREATED: 0, REVISED: 0, UNCHANGED: 0 };
        res.results.forEach(function (r) { res.counts[r.outcome] = (res.counts[r.outcome] || 0) + 1; });
        if (e.batch) { try { (await call('POST', '/api/batch/page_saved', { key: key, id: e.batch.id, page: e.batch.page, counts: res.counts })); } catch (err) { /* 保存已确认；批量列表状态下次刷新再核对，不重发保存。 */ } }
        return res;
      };
      T.saveTable = async function (text, nature, requestId, key) {
        key=key||core.st.key;
        var res = (await call('POST', '/api/torch/table?key=' + encodeURIComponent(key) + (nature ? '&nature=' + nature : '') + (requestId ? '&request_id=' + encodeURIComponent(requestId) : '') + (window.PTDS_COMPUTE&&window.PTDS_COMPUTE.enabled()?'&compute_mode=background-v1':''), text, true, { 'Content-Type': 'text/csv' }));
        if (res.rejected && res.rejected.length) {  /* 日期在今天之后的行没导入，其余照常（产品负责人 2026-10-15） */
          var rows = res.rejected.map(function (r) { return r.row ? '第 ' + r.row + ' 行' : r.code; }).filter(function (x, i, a) { return a.indexOf(x) === i; });
          C.toast('有 ' + res.rejected.length + ' 项日期在今天之后，没有导入（' + rows.join('、') + '），请核对；其余已导入');
        }
        if(!Array.isArray(res.results)||!res.sync||res.export!=='WRITTEN'||(requestId&&res.request_id!==requestId))throw Error('SAVE_CONFIRMATION_MISSING');
        LIVE.invalidateAfterWrite(key);return res;
      };
      T.gene = async function (file, bytes, key) {
        key=key||core.st.key;
        return (await call('POST', '/api/gene?key=' + encodeURIComponent(key) + '&nature=' + encodeURIComponent(core.S().instance.default_nature), bytes, true,
          { 'Content-Type': 'application/octet-stream', 'X-File-Name': encodeURIComponent(file.name) }));
      };
      T.geneList = function () { if (window.PTDS_TRIAL_UI && !window.PTDS_TRIAL_UI.can('genes')) return []; return readCached('/api/gene?key=' + encodeURIComponent(core.st.key)); };
      /* 化验单识别：真实引擎接入前，不给任何示例结果（不冒充） */
      var ENGINE = null;
      T.recognize = function () { ENGINE = ENGINE || readCached('/api/torch/engine'); return { name: '', engine: ENGINE, date: '', time: '', timeOk: false, rows: [], unmatched: [], nature: 'REAL' }; };
      document.addEventListener('pointerdown',function(){LIVE._pointerDown=true;},true);
      var endPointer=function(){LIVE._pointerDown=false;LIVE._interactionUntil=Date.now()+250;};
      document.addEventListener('pointerup',endPointer,true);document.addEventListener('pointercancel',endPointer,true);
      window.addEventListener('blur',endPointer);
      document.addEventListener('keydown',function(){LIVE._interactionUntil=Date.now()+250;},true);
      /* UI reads are asynchronous; backend device sync continues independently of the page. */
      readTimer(function(){if(window.PTDS_COMPUTE)window.PTDS_COMPUTE.tick();LIVE.refreshInBackground();},10000);
      /* 星簇：授权、撤销、读取、出域记录都在本机进程（cluster.db 只追加）；按当前实例分开 */
      var K = function () { return encodeURIComponent(core.st.key); }, CLU = core.MockCluster;
      ['disclosure:披露级别', 'message:信号', 'alert:提醒', 'values:数值', 'fresh:是否最新', 'scope:范围', 'loci:位点', 'rsid:rs 号', 'chrom:染色体', 'pos:位置', 'genotype:基因型', 'build:参考基因组', 'file:来源文件', 'file_sha:文件指纹', 'not_found:文件里没有'].forEach(function (kv) { var p = kv.split(':'); core.PKEY[p[0]] = p[1]; });
      CLU.list = function () { return readCached('/api/cluster/list?key=' + K()).filter(function (g) { return !(g.example && g.id === 'G-002' && g.object === 'doctor' && g.channel === 'wa'); }); };
      CLU.find = function (id) { try { return readCached('/api/cluster/find?key=' + K() + '&id=' + encodeURIComponent(id)); } catch (err) { if(err&&(err.viewPending||err.code==='VIEW_CHANGED'))throw err; return null; } };
      CLU.create = async function (f, key) { key=key||core.st.key; return (await call('POST', '/api/cluster/create', { key: key, form: f })); };
      CLU.revoke = async function (id, key) { key=key||core.st.key; return (await call('POST', '/api/cluster/revoke', { key: key, id: id })); };
      CLU.records = function (all) { return readCached('/api/cluster/records?' + (all ? 'lifecycle=1' : 'egress=1') + '&key=' + K()); };
      window.addEventListener('hashchange',LIVE.phoneNativeEntry);setTimeout(LIVE.phoneNativeEntry,0);
      CLU.read = async function (id, key) { key=key||core.st.key;
        var r = (await call('POST', '/api/cluster/read', { key: key, grant_id: id, via: 'UI' }));
        if (r.payload && r.payload.items) r.payload.items.forEach(function (x) { if (x.source) x.source = SRC_NAME[x.source] || x.source; });
        return r;
      };
      /* 苹果健康：接收端在本机进程（局域网端口，按需打开）；配对、同步在 iPhone 快捷指令里完成 */
      var BR = core.MockBridge, BCACHE = null, BCACHE_RAW=null;
      var brState = function () { if (window.PTDS_TRIAL_UI && !window.PTDS_TRIAL_UI.can('bridge')) return {phones:[],receipts:[],code:null};
        var b = JSON.parse(JSON.stringify(readCached('/api/bridge/state?key=' + K())));
        BCACHE_RAW=JSON.stringify([b.phones,b.receipts,b.code]);
        if(bridgeReads)bridgeReads[core.st.key]={at:Date.now(),value:JSON.parse(JSON.stringify(b))};
        if (b.code) b.code.code = b.code.code.slice(0, 3) + ' ' + b.code.code.slice(3);
        b.receipts = b.receipts.map(function (r) { return Object.assign({}, r, { when: core.tzTime(r.when), window: r.since ? '自 ' + core.tzTime(r.since) + ' 以来' : '首次同步', errors: r.errors_by_code || [] }); });
        BCACHE = b; return b;
      };
      var bridgeReads={};
      var cachedBridge=function(){ if (window.PTDS_TRIAL_UI && !window.PTDS_TRIAL_UI.can('bridge')) return {phones:[],receipts:[]};
        var key=core.st.key,e=bridgeReads[key]||(bridgeReads[key]={at:0,value:{phones:[],receipts:[]}});
        if(!e.busy&&Date.now()-e.at>10000){e.busy=true;var epoch=readEpoch;
          callAsync('GET','/api/bridge/state?key='+encodeURIComponent(key)).then(function(b){
            if(epoch!==readEpoch||bridgeReads[key]!==e)return;
            var prior=JSON.stringify([e.value.phones,e.value.receipts]);e.value=b;e.at=Date.now();
            if(prior!==JSON.stringify([b.phones,b.receipts]))e.dirty=true;
            LIVE.flushBridgeView();
          }).catch(function(){e.at=Date.now();}).finally(function(){e.busy=false;});
        }return e.value;
      };
      LIVE.flushBridgeView=function(){
        if(core.st.app==='torch'&&['data','sources','guard'].indexOf(core.st.tview)>=0)cachedBridge();
        var e=bridgeReads[core.st.key];
        if(e&&e.dirty&&LIVE.canAutoPaint()&&core.st.app==='torch'&&['data','sources','guard'].indexOf(core.st.tview)>=0){e.dirty=false;var y=window.scrollY;core.renderMainOnly();window.scrollTo(0,y);}
      };
      var MOCK = Object.assign({}, BR), REALB = {
        state: function () { return brState(); },
        phones: function () { return cachedBridge().phones||[]; },
        receipts: function () { return (cachedBridge().receipts||[]).map(function(r){return Object.assign({},r,{when:core.tzTime(r.when),window:r.since?'自 '+core.tzTime(r.since)+' 以来':'首次同步',errors:r.errors_by_code||[]});}); },
        code: async function (id,key) { key=key||core.st.key; await call('POST','/api/bridge/code',{key:key}); return (await call('GET','/api/bridge/state?key='+encodeURIComponent(key))).code; },
        unpair: async function (id,key) { key=key||core.st.key; var state=await call('GET','/api/bridge/state?key='+encodeURIComponent(key)),ph=state.phones[0]; if(ph)await call('POST','/api/bridge/unpair',{key:key,phone_id:ph.id}); },
        pair: function () { return { outcome: 'CODE_INVALID' }; },
        sync: function () { return { outcome: 'UNPAIRED' }; }
      };
      /* 只有收真实数据的实例用真接收端；演示病例、回放仍用原型的模拟手机 */
      LIVE.realBridge = function () { var i = core.S().instance; return !i.replay && LIVE.realNature(); };
      Object.keys(REALB).forEach(function (m) { BR[m] = function () { return (LIVE.realBridge() ? REALB : MOCK)[m].apply(null, arguments); }; });
      var applePollBusy=false;
      setInterval(async function(){
        if((window.PTDS_TRIAL_UI && !window.PTDS_TRIAL_UI.can('bridge'))||applePollBusy||core.st.tview!=='apple'||!document.getElementById('ah-live-phone'))return;
        applePollBusy=true;var key=core.st.key,route=viewRoute();
        try{var b=await readView('/api/bridge/state?key='+encodeURIComponent(key));
          if(key!==core.st.key||route!==viewRoute())return;
          var next=JSON.stringify([b.phones,b.receipts,b.code]),changed=BCACHE_RAW!==next;
          if(changed){
            if(b.phones.length&&core.st.ahPhase==='pairing')core.st.ahPhase='paired';
            if(LIVE.homeReadEnabled())await LIVE.refreshInBackground();else await LIVE.refresh(key);if(key!==core.st.key||route!==viewRoute())return;
          }
          viewReads.set('/api/bridge/state?key='+encodeURIComponent(key),{value:b,at:Date.now(),epoch:readEpoch});
          if(changed&&LIVE.canAutoPaint())core.renderApple();
        }catch(err){/* Keep the prior receipt; no write or replay. */}finally{applePollBusy=false;}
      },3000);
      // Per-instance gene receipts load on entry; launch never reads every instance.

      if (/[?&]dev=1/.test(location.search)) { var dv = document.querySelector('.dev'); if (dv) { dv.style.display = ''; setTimeout(function () { window.dispatchEvent(new Event('resize')); }, 0); } }
      if (/[?&]oura=connected/.test(location.search)) {  /* 从 Oura 授权页回来 */
        try { history.replaceState(null, '', '/'); } catch (err) { if(err&&(err.viewPending||err.code==='VIEW_CHANGED'))throw err; /* 忽略 */ }
        setTimeout(function () { core.toast('Oura 已接入，读数已保存到"我的真实数据"'); }, 900);
      }
      readView('/api/health').then(function(h){if(h.code_changed !== false)setTimeout(function(){C.toast('程序文件已更新，但正在运行的还是旧版本：请重新启动后台服务');},1500);}).catch(function(){});
      window.PTDS_LIVE_READY = true;
      setTimeout(function(){LIVE.openDeviceLink();},0);
    }
  };
  /* Muse 原始会话：只调用专用本机接口；保存意图只保留定位符，刷新不恢复保存许可。 */
  LIVE.museState = function () {
    var key = C.st.key;
    if (!LIVE._muse || LIVE._muse.key !== key) LIVE._muse = { key: key, sessions: [], loaded: false };
    return LIVE._muse;
  };
  LIVE.museRemember = function (m, value) {
    try { if (value) sessionStorage.setItem('ptds-muse-intent:' + m.key, JSON.stringify(value)); else sessionStorage.removeItem('ptds-muse-intent:' + m.key); }
    catch (err) { if(err&&(err.viewPending||err.code==='VIEW_CHANGED'))throw err; /* Memory still preserves the current request; server remains the authority. */ }
  };
  LIVE.musePaint = function (m) {
    if (LIVE._muse === m && C.st.key === m.key && C.st.tview === 'srcgroup' && C.st.museOpen) LIVE.renderMuse();
  };
  LIVE.museError = function (err) {
    return ({ SERVER_DOWN: '连不上本机服务', UPLOAD_TOO_LARGE: '会话总量最多32 MiB，单文件最多16 MiB',
      REVIEW_CANCELLED: '这份核对已取消，请重新选择完整会话', REQUEST_CONFLICT: '请求与原保存内容不一致，请查询原结果',
      READ_ONLY: '回放实例只能查看', NATURE_NOT_ACCEPTED: '当前实例不接收这份会话的数据性质',
      COMPONENT_CHANGED: '组件文件与固定版本不一致，请修复组件后重试', COMPONENT_UNAVAILABLE: '缺少固定版本组件文件',
      BUNDLE_FILES_INVALID: '会话文件不完整或含有额外文件，请选择单个完整会话', SESSION_INCOMPLETE: '采集会话未完整结束，不能正式保存',
      SUPERVISOR_INCOMPLETE: '缺少成功结束的采集监督记录，不能正式保存', REVIEW_CHANGED: '已核对的会话文件发生变化，不能保存',
      SESSION_CONFLICT: '相同会话编号已保存了不同文件，请核对来源',
      REPLAY_INSTANCE: '回放实例只能查看', NON_SYNTHETIC_IN_DEMO: '当前实例只接收合成数据',
      SYNTHETIC_IN_REAL: '当前实例只接收真实数据' })[err.code] || err.detail || ('操作未完成（' + (err.code || '本机服务错误') + '）');
  };
  LIVE.museLoad = function (m) {
    if (m.busy) return;
    m.busy = true; m.error = '';
    callAsync('GET', '/api/muse/status?key=' + encodeURIComponent(m.key)).then(function (r) {
      m.status = r.status; m.sessions = r.sessions || []; m.loaded = true;
    }).catch(function (err) { m.error = LIVE.museError(err); }).then(function () {
      m.busy = false; LIVE.musePaint(m);
      if (!m.recovered && m.loaded) {
        m.recovered = true; var p = null;
        try { p = JSON.parse(sessionStorage.getItem('ptds-muse-intent:' + m.key) || 'null'); } catch (err) { if(err&&(err.viewPending||err.code==='VIEW_CHANGED'))throw err; /* no intent */ }
        if (p && p.review_id && p.request_id && p.review_sha256) { m.intent = p; LIVE.museRecover(m); }
      }
    });
  };
  // Refresh committed sessions only; never recover or submit a save intention here.
  readTimer(function () {
    var m=LIVE._muse;
    if(!m||m.busy||m.intent||m.review||m.polling||!C.st.museOpen||C.st.tview!=='srcgroup'||C.st.key!==m.key)return;
    m.polling=true;
    LIVE.managedRead('/api/muse/status?key='+encodeURIComponent(m.key)).then(function(r){
      if(LIVE._muse!==m||!C.st.museOpen||m.busy||m.intent||m.review)return;
      var rows=r.sessions||[];if(JSON.stringify(rows)!==JSON.stringify(m.sessions)){m.sessions=rows;LIVE.musePaint(m);}
    }).catch(function(){}).finally(function(){m.polling=false;});
  },5000);
  LIVE.museRecover = function (m) {
    if (!m.intent || m.busy) return;
    m.busy = true; m.error = '';
    callAsync('GET', '/api/muse/request?key=' + encodeURIComponent(m.key) + '&request_id=' + encodeURIComponent(m.intent.request_id)).then(function (r) {
      if (r.result.status === 'SAVED') {
        m.receipt = r.result.receipt; m.review = null; m.uncertain = false; m.intent = null; LIVE.museRemember(m, null);
        return callAsync('GET', '/api/muse/status?key=' + encodeURIComponent(m.key)).then(function (s) { m.sessions = s.sessions || []; });
      }
      return callAsync('GET', '/api/muse/review?key=' + encodeURIComponent(m.key) + '&review_id=' + encodeURIComponent(m.intent.review_id)).then(function (s) {
        m.review = s.review; m.uncertain = false;
        m.note = '已查询原请求，尚无正式回执。请重新核对后决定保存或取消；不会自动保存。';
      });
    }).catch(function (err) {
      if (m.receipt && !m.intent) { m.uncertain = false; m.error = '已查到正式回执，列表暂未刷新。请刷新列表。'; }
      else { m.uncertain = true; m.error = '保存结果尚未确认：' + LIVE.museError(err); }
    })
      .then(function () { m.busy = false; LIVE.musePaint(m); });
    LIVE.musePaint(m);
  };
  LIVE.museSelect = function (files, m) {
    if (m.busy || m.intent) return;
    var chosen = Array.from(files || []), total = chosen.reduce(function (n, f) { return n + f.size; }, 0);
    if (!chosen.length) return;
    if (total > 32 * 1024 * 1024 || chosen.length > 32) { m.error = '请选择一个完整会话，最多32个文件、总量32 MiB。'; LIVE.musePaint(m); return; }
    var names = {}, roots = {};
    if (chosen.some(function (f) {
      var rel = f.webkitRelativePath, parts = rel ? rel.split('/') : [f.name];
      if (rel) roots[parts[0]] = true;
      if (parts.length > 2 || names[f.name]) return true;
      names[f.name] = true; return false;
    }) || Object.keys(roots).length > 1) { m.error = '请选择单个会话文件夹，不要包含其他目录或同名文件。'; LIVE.musePaint(m); return; }
    m.busy = true; m.error = ''; m.note = '正在复制并校验所选会话，尚未正式保存。'; m.receipt = null; m.detail = null;
    Promise.all(chosen.map(function (f) {
      return new Promise(function (resolve, reject) {
        var reader = new FileReader();
        reader.onerror = function () { reject(new Error('文件读取失败')); };
        reader.onload = function () { resolve({ name: f.name, base64: String(reader.result).split(',')[1] }); };
        reader.readAsDataURL(f);
      });
    })).then(function (parts) { return callAsync('POST', '/api/muse/prepare', { key: m.key, files: parts }); })
      .then(function (r) {
        m.review = r.review; m.intent = { review_id: r.review.review_id, review_sha256: r.review.review_sha256, request_id: rid() };
        LIVE.museRemember(m, m.intent); m.note = '校验通过，请核对下方会话后决定是否保存。';
      }).catch(function (err) { m.error = LIVE.museError(err); m.note = ''; })
      .then(function () { m.busy = false; LIVE.musePaint(m); });
    LIVE.musePaint(m);
  };
  LIVE.museSave = function (m) {
    if (!m.intent || m.busy || m.uncertain || !m.review || m.review.status !== 'READY') return;
    m.busy = true; m.error = ''; m.note = '正在正式保存…'; LIVE.museRemember(m, m.intent);
    callAsync('POST', '/api/muse/save', Object.assign({ key: m.key }, m.intent)).then(function (r) {
      m.receipt = r.receipt; m.review = null; m.intent = null; m.note = '已正式保存，下面的会话列表从星炬读取。'; LIVE.museRemember(m, null);
      return callAsync('GET', '/api/muse/status?key=' + encodeURIComponent(m.key)).then(function (s) { m.sessions = s.sessions || []; });
    }).catch(function (err) {
      if (m.receipt) m.error = '已收到正式回执，列表暂未刷新。请刷新列表。';
      else { m.uncertain = true; m.note = ''; m.error = '保存结果尚未确认，请查询这次保存结果。' + LIVE.museError(err); }
    }).then(function () { m.busy = false; LIVE.musePaint(m); });
    LIVE.musePaint(m);
  };
  LIVE.museCancel = function (m) {
    if (!m.review || m.busy || m.uncertain) return;
    m.busy = true;
    callAsync('POST', '/api/muse/cancel', { key: m.key, review_id: m.review.review_id }).then(function () {
      m.review = null; m.intent = null; m.error = ''; m.note = '已取消，候选保留为未保存，不会出现在正式会话列表。'; LIVE.museRemember(m, null);
    }).catch(function (err) { m.error = LIVE.museError(err); }).then(function () { m.busy = false; LIVE.musePaint(m); });
    LIVE.musePaint(m);
  };
  LIVE.museDetail = function (m, id) {
    m.busy = true; m.error = ''; m.rows = null;
    callAsync('GET', '/api/muse/session?key=' + encodeURIComponent(m.key) + '&asset_id=' + encodeURIComponent(id))
      .then(function (r) { m.detail = r.session; m.asset = id; })
      .catch(function (err) { m.error = LIVE.museError(err); }).then(function () { m.busy = false; LIVE.musePaint(m); });
    LIVE.musePaint(m);
  };
  LIVE.museReplay = function (m, stream, offset) {
    if (m.busy) return;
    m.busy = true; m.error = '';
    callAsync('GET', '/api/muse/replay?key=' + encodeURIComponent(m.key) + '&asset_id=' + encodeURIComponent(m.asset) +
      '&stream=' + encodeURIComponent(stream) + '&offset=' + offset + '&limit=20')
      .then(function (r) { m.rows = r.replay; m.stream = stream; m.offset = offset; })
      .catch(function (err) { m.error = LIVE.museError(err); }).then(function () { m.busy = false; LIVE.musePaint(m); });
    LIVE.musePaint(m);
  };
  LIVE.renderMuse = function () {
    var m = LIVE.museState(), esc = C.esc, v = document.getElementById('view'), labels = { eeg: '脑电 EEG', imu: '运动 IMU', optical: '光学 Optical' };
    if (!document.getElementById('muse-css')) {
      var style = document.createElement('style'); style.id = 'muse-css';
      style.textContent = '.muse-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px}.muse-meta{display:grid;gap:6px}.muse-table{max-width:100%;overflow:auto}.muse-table table{border-collapse:collapse;font-size:var(--scale-type-meta)}.muse-table td,.muse-table th{padding:6px 10px;border-bottom:1px solid var(--theme-line-hairline);white-space:nowrap;text-align:right}.muse-json{max-height:320px;overflow:auto;white-space:pre-wrap;overflow-wrap:anywhere;font-size:var(--scale-type-meta)}.muse-session{display:flex;align-items:center;justify-content:space-between;gap:16px;padding:12px 0;border-bottom:1px solid var(--theme-line-hairline)}@media(max-width:900px){.muse-grid{grid-template-columns:1fr}}';
      document.head.appendChild(style);
    }
    var blocked = m.busy || !!m.intent || C.isReplay() || (m.status && !m.status.available);
    var summary = function (doc) {
      var man = doc.manifest || {}, req = man.request || {}, streams = doc.streams || man.streams || {}, nature = doc.data_nature || req.data_nature;
      var shortSpan = nature === 'REAL' && req.duration_seconds > 0 && Object.keys(streams).some(function (name) {
        var span = streams[name].timestamp_span_seconds;
        return typeof span === 'number' && span < req.duration_seconds * 0.9;
      });
      return '<div class="chips"><span class="tag">' + esc(nature === 'SYNTHETIC' ? '合成数据' : nature === 'REAL' ? '真实数据' : '性质未知') + '</span><span data-ptds-ui="sc450eb3cc7b7">三路原始会话</span></div>' +
        '<p class="sub2">' + (nature === 'SYNTHETIC' ? '这是虚构样例，未连接设备。请求时长不代表真实采集时长。' : '保留设备会话原始数据；完整性校验不代表医学质量或来源身份认证。') + '</p>' +
        (req.device_name ? '<p data-ptds-inline><!--ptds-ui:s6ab8f8474b49-->来源设备：<!--/ptds-ui-->' + esc(req.device_name) + ' · ' + (man.runtime && man.runtime.segment_sealed ? '分段目标 ' : '请求采集 ') + esc(req.duration_seconds) + ' 秒</p>' : '') +
        (man.runtime && man.runtime.segment_sealed ? '<p data-ptds-ui="sd975ea8b792f">持续采集的已封存片段；不代表设备会话已结束。断连或暂停时可能不足目标时长，保留实际收到的数据。</p>' : '') +
        (shortSpan ? '<p role="alert" data-ptds-ui="s7d677b0ed065">部分数据的时间戳跨度明显短于请求时长；仅展示实际收到的数据，覆盖情况待核对。</p>' : '') +
        '<div class="muse-grid">' + Object.keys(labels).map(function (name) {
          var s = streams[name] || {};
          return '<div class="box muse-meta"><b>' + labels[name] + '</b><span>' + esc(s.samples == null ? '未知' : s.samples) + ' 个样本</span>' +
            '<span class="sub2" data-ptds-inline><!--ptds-ui:s8d1ae3f7d752-->时间戳跨度 <!--/ptds-ui-->' + esc(s.timestamp_span_seconds == null ? '未知' : s.timestamp_span_seconds + ' 秒') + '</span>' +
            '<span class="sub2" data-ptds-inline><!--ptds-ui:s3df0913c0a32-->非有限值 <!--/ptds-ui-->' + esc(s.nonfinite_values == null ? '未知' : s.nonfinite_values) + '</span></div>';
        }).join('') + '</div><details><summary data-ptds-ui="s25c80a4ec871">来源、通道与完整性依据</summary><pre class="muse-json">' + esc(JSON.stringify(man, null, 2)) + '</pre></details>';
    };
    var html = '<section class="box"><h3>' + LIVE.KIND_IC.bci + ' Muse S Athena<span class="grow"></span><button class="btn2" id="muse-back" data-ptds-ui="s572cf45ba436">返回</button></h3>' +
      '<p data-ptds-ui="sbd6d4cb321e7">保存并查看脑电、运动和光学三路会话。当前入口用于导入已采集的完整会话文件夹。</p>' +
      '<p class="sub2" data-ptds-ui="s9c994a40aa9f">此入口导入已有会话，不会扫描或连接设备；采集结果以各会话来源为准，原始波形暂不参与状态计算。</p>' +
      '<div class="opts"><button class="btn" id="muse-folder"' + (blocked ? ' disabled' : '') + '>选择会话文件夹</button>' +
      '<button class="btn2" id="muse-files"' + (blocked ? ' disabled' : '') + '>选择会话内全部文件</button>' +
      '<button class="btn2" id="muse-refresh"' + (m.busy ? ' disabled' : '') + '>刷新列表</button></div>' +
      '<input id="muse-dir-input" type="file" webkitdirectory multiple hidden><input id="muse-file-input" type="file" multiple hidden>' +
      '<p class="sub2" data-ptds-ui="s75eb39b6ea0a">选择 MuseAtom 生成的单个会话，不要选择整个组件目录。文件总量上限32 MiB。</p>' +
      (m.status && !m.status.available ? '<p role="alert" data-ptds-ui="sa2b2090b6047">组件文件校验未通过，暂不能导入新会话。已保存的数据保留。</p>' : '') +
      (m.busy ? '<p role="status" data-ptds-ui="sba3e42c4e618">正在处理，请稍候…</p>' : '') + (m.note ? '<p role="status">' + esc(m.note) + '</p>' : '') +
      (m.error ? '<p role="alert">' + esc(m.error) + '</p>' : '') +
      (m.uncertain ? '<button class="btn2" id="muse-recover"' + (m.busy ? ' disabled' : '') + '>查询这次保存结果</button>' : '') + '</section>';
    if (m.review) html += '<section class="box"><h3 data-ptds-ui="s3db41d13f385">核对会话 · 尚未正式保存</h3>' + summary(m.review) +
      '<div class="opts"><button class="btn" id="muse-save"' + (m.busy || m.uncertain || m.review.status !== 'READY' ? ' disabled' : '') + '>核对无误，正式保存</button>' +
      '<button class="btn2" id="muse-cancel"' + (m.busy || m.uncertain ? ' disabled' : '') + '>取消此次导入</button></div></section>';
    if (m.receipt) html += '<section class="box"><h3 data-ptds-ui="s85b1b5b510c5">正式保存回执</h3><p data-ptds-ui="s234d9135c934">三路原始数据已保存到当前实例。</p><div class="sub2">' + esc(C.tzTime(m.receipt.saved_at, true)) +
      '</div><button class="btn2" data-muse-asset="' + esc(m.receipt.asset_id) + '">查看已保存会话</button></section>';
    html += '<section class="box"><h3 data-ptds-inline><!--ptds-ui:s89a82f0768c9-->已保存的会话 · <!--/ptds-ui-->' + m.sessions.length + '</h3>' + (m.sessions.length ? m.sessions.map(function (s) {
      return '<div class="muse-session"><div><div>Muse S Athena · ' + esc(s.data_nature === 'SYNTHETIC' ? '合成数据' : '真实数据') + '</div><div class="sub2">' +
        esc(C.tzTime(s.saved_at, true)) + '</div></div><button class="btn2" data-muse-asset="' + esc(s.asset_id) + '">查看三路数据</button></div>';
    }).join('') : '<p class="sub2" data-ptds-ui="s427c9d4aa426">还没有正式保存的会话。核对后保存，记录才会出现在这里。</p>') + '</section>';
    if (m.detail) {
      html += '<section class="box"><h3 data-ptds-ui="s5561e261a56f">已保存会话详情</h3>' + summary(m.detail) +
        '<div class="chips">' + Object.keys(labels).map(function (name) { return '<button class="chip" data-muse-stream="' + name + '"' + (m.busy ? ' disabled' : '') + '>' + labels[name] + '</button>'; }).join('') + '</div>';
      if (m.rows) {
        var rows = m.rows.rows || [], ncols = rows.length ? rows[0].length : 0;
        html += '<p class="sub2" data-ptds-inline><!--ptds-ui:s3cec3a1b3194-->原始字面值 · <!--/ptds-ui-->' + esc(labels[m.stream]) + ' · 从第 ' + (m.offset + 1) + ' 个样本起。通道含义见上方来源依据。</p>' +
          '<div class="muse-table"><table><thead><tr><th data-ptds-ui="s6661c42b523f">样本</th>' + Array.from({ length: ncols }, function (_, i) { return '<th data-ptds-inline><!--ptds-ui:s0c04098e48ab-->通道 <!--/ptds-ui-->' + i + '</th>'; }).join('') + '</tr></thead><tbody>' +
          rows.map(function (row, i) { return '<tr><th>' + (m.offset + i + 1) + '</th>' + row.map(function (x) { return '<td>' + esc(x) + '</td>'; }).join('') + '</tr>'; }).join('') +
          '</tbody></table></div><div class="opts"><button class="btn2" id="muse-prev"' + (m.busy || !m.offset ? ' disabled' : '') + '>上一页</button><button class="btn2" id="muse-next"' +
          (m.busy || rows.length < 20 ? ' disabled' : '') + '>下一页</button></div>';
      }
      html += '</section>';
    }
    v.innerHTML = html;
    var on = function (id, fn) { var b = document.getElementById(id); if (b) b.onclick = LIVE.action(fn); };
    on('muse-back', function () { C.st.museOpen = false; C.render(); });
    on('muse-folder', function () { document.getElementById('muse-dir-input').click(); });
    on('muse-files', function () { document.getElementById('muse-file-input').click(); });
    ['muse-dir-input', 'muse-file-input'].forEach(function (id) { document.getElementById(id).onchange = function () { LIVE.museSelect(this.files, m); }; });
    on('muse-refresh', function () { LIVE.museLoad(m); });
    on('muse-save', function () { LIVE.museSave(m); });
    on('muse-cancel', function () { LIVE.museCancel(m); });
    on('muse-recover', function () { LIVE.museRecover(m); });
    v.querySelectorAll('[data-muse-asset]').forEach(function (b) { b.onclick = function () { LIVE.museDetail(m, b.dataset.museAsset); }; });
    v.querySelectorAll('[data-muse-stream]').forEach(function (b) { b.onclick = function () { LIVE.museReplay(m, b.dataset.museStream, 0); }; });
    on('muse-prev', function () { LIVE.museReplay(m, m.stream, Math.max(0, m.offset - 20)); });
    on('muse-next', function () { LIVE.museReplay(m, m.stream, m.offset + 20); });
    if (!m.loaded && !m.busy && !m.error) LIVE.museLoad(m);
  };
  /* ---------- 星轨 · 我的状态（卡片引擎化，产品负责人 2026-10-14）：卡片放大、单卡带缩略趋势；同类算法叠成卡片组（引擎） ---------- */
  var WALL_CSS = '.wall2{display:grid;grid-template-columns:repeat(auto-fill,minmax(400px,1fr));gap:var(--primitive-space-5)}' +
    '.wall2 .wcard{min-height:200px;gap:var(--primitive-space-2);align-content:start;grid-auto-rows:min-content}' +
    '.wall2 .wcard.add{align-content:center}' +
    '.wcard .spk{width:100%;height:56px;display:block;margin-top:var(--primitive-space-1)}' +
    '.spk .ln{fill:none;stroke:var(--theme-text-secondary);stroke-width:1.5}.spk .th{stroke:var(--theme-line-control);stroke-dasharray:3 3}' +
    '.spk .end{fill:var(--theme-text-primary)}.spk text{fill:var(--theme-text-tertiary);font-size:10px}' +
    '.metric-card{min-width:0}.metric-card .wn{align-items:center}.metric-time{display:grid;gap:var(--primitive-space-1);text-align:right;white-space:nowrap;flex:none}' +
    '.metric-value{display:flex;align-items:baseline;flex-wrap:wrap;column-gap:var(--primitive-space-3);row-gap:var(--primitive-space-1)}.metric-change{font-size:var(--scale-type-meta);color:var(--theme-text-secondary)}' +
    '.metric-trend{display:block;min-width:0;max-width:100%;overflow-x:auto}.metric-trend:focus-visible{outline:var(--primitive-border-hairline) solid var(--theme-line-control)}' +
    '.metric-spark{display:block;width:100%;height:104px}.metric-spark .ln{fill:none;stroke:var(--theme-text-secondary);stroke-width:1.5}.metric-spark .end{fill:var(--theme-text-primary)}' +
    '.metric-spark text{fill:var(--theme-text-secondary);font-family:inherit;font-size:var(--scale-type-meta,12px)}.metric-range{display:grid;grid-template-columns:1fr auto 1fr;gap:var(--primitive-space-2);width:100%}.metric-range>:last-child{text-align:right}' +
    '.mrow{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:var(--primitive-space-4) var(--primitive-space-5);align-content:start}' +
    '.mrow .m.more{place-content:center;justify-items:center;text-align:center;border:var(--primitive-border-hairline) dashed var(--theme-line-control);border-radius:var(--primitive-radius-card);color:var(--theme-text-secondary);font-size:var(--scale-type-meta);gap:var(--primitive-space-1)}' +
    '.mrow .m.more svg{width:20px;height:20px}' +
    '.mrow .m{display:grid;gap:2px;min-width:0}.mrow .m .v{font-size:var(--scale-type-driver)}.mrow .m .k{font-size:var(--scale-type-meta);color:var(--theme-text-tertiary)}' +
    '.wcard.grp{position:relative;margin:0 10px 10px 0;box-shadow:5px 5px 0 -1px var(--theme-canvas-edge),5px 5px 0 0 var(--component-currentCard-line),10px 10px 0 -1px var(--theme-canvas-edge),10px 10px 0 0 var(--component-currentCard-line)}' +
    '.grp-list{display:grid;gap:var(--primitive-space-2);margin:var(--primitive-space-1) 0 0;padding:0;list-style:none}' +
    '.grp-list li{display:grid;grid-template-columns:auto minmax(0,1fr);gap:var(--primitive-space-3);font-size:var(--scale-type-meta)}' +
    '.grp-list li b{font-weight:var(--primitive-font-weight-medium);color:var(--theme-text-primary);white-space:nowrap}.grp-list li span{color:var(--theme-text-secondary)}' +
    '.strip{display:flex;gap:6px;align-items:center;flex-wrap:wrap;margin-top:var(--primitive-space-1)}' +
    '.strip i{width:12px;height:12px;border-radius:6px;display:inline-block;border:1px solid var(--theme-line-control)}' +
    '.strip i.MET,.strip i.ALERT{background:var(--theme-text-primary)}.strip i.WATCH{background:var(--theme-text-secondary)}' +
    '.strip i.INDETERMINATE,.strip i.UNDETERMINED,.strip i.NOT_APPLICABLE{background:repeating-linear-gradient(45deg,transparent 0 2px,var(--theme-line-control) 2px 4px)}' +
    '.strip span{font-size:var(--scale-type-meta);color:var(--theme-text-tertiary)}' +
    '.bio-in{display:grid;grid-template-columns:minmax(0,1.2fr) auto auto;gap:2px var(--primitive-space-3);font-size:var(--scale-type-meta)}' +
    '.bio-in span{min-width:0}.bio-form{display:flex;gap:var(--primitive-space-3);flex-wrap:wrap;align-items:end}' +
    '.bio-form label{display:grid;gap:4px;font-size:var(--scale-type-meta)}' +
    '@media (max-width:700px){.wall2{grid-template-columns:1fr}}';
  function wallCss() { engCss(); if (!document.getElementById('wall2-css')) { var s = document.createElement('style'); s.id = 'wall2-css'; s.textContent = WALL_CSS; document.head.appendChild(s); } }
  /* 缩略趋势：只画线、阈值和最后一个点，两端日期 */
  function spark(pts, thr) {
    pts = (pts || []).map(function (p) { return { tp: p.tp, v: +p.v }; }).filter(function (p) { return isFinite(p.v); });
    if (pts.length < 2) return '';
    var W = 320, H = 56, pad = 4, vs = pts.map(function (p) { return p.v; }).concat(thr != null ? [thr] : []);
    var lo = Math.min.apply(null, vs), hi = Math.max.apply(null, vs), span = hi - lo || 1;
    var X = function (i) { return pad + i * (W - 2 * pad) / (pts.length - 1); }, Y = function (v) { return H - 14 - (v - lo) / span * (H - 22); };
    var last = pts[pts.length - 1];
    return '<svg class="spk" viewBox="0 0 ' + W + ' ' + H + '" preserveAspectRatio="none" aria-hidden="true">' +
      (thr != null ? '<line class="th" x1="0" x2="' + W + '" y1="' + Y(thr) + '" y2="' + Y(thr) + '"/>' : '') +
      '<polyline class="ln" vector-effect="non-scaling-stroke" points="' + pts.map(function (p, i) { return X(i).toFixed(1) + ',' + Y(p.v).toFixed(1); }).join(' ') + '"/>' +
      '<circle class="end" cx="' + X(pts.length - 1) + '" cy="' + Y(last.v) + '" r="3"/>' +
      '<text x="' + pad + '" y="' + (H - 1) + '">' + C.esc(pts[0].tp.slice(5)) + '</text><text x="' + (W - pad) + '" y="' + (H - 1) + '" text-anchor="end">' + C.esc(last.tp.slice(5)) + '</text></svg>';
  }
  var RES_ZH = { MET: '成立', NOT_MET: '不成立', INDETERMINATE: '缺数据', NOT_APPLICABLE: '不适用', ALERT: '关注', WATCH: '观察', UNDETERMINED: '无法判定', NONE: '无' };
  function strip(items) {
    return '<span class="strip" aria-hidden="true">' + items.map(function (x) { return '<i class="' + x.r + '" title="' + C.esc(x.tp + '：' + (RES_ZH[x.r] || x.r)) + '"></i>'; }).join('') + '</span>';
  }
  function bioCard(c) {
    var esc = C.esc, L = c.latest, ok = !!L;
    return '<button class="wcard" data-bio="' + c.id + '"><span class="wn">' + esc(c.zh) + '<span class="grow"></span><span class="tag">' + esc(c.year) + '</span></span>' +
      '<span class="sub2">' + esc(c.how) + '</span>' +
      (ok ? '<span class="wl"><span class="lvname">' + esc(L.value) + ' ' + esc(c.unit) + '</span>' + (L.delta != null ? '<span class="sub2" data-ptds-inline><!--ptds-ui:s4f2ca164245c-->比实际年龄 <!--/ptds-ui-->' + (L.delta > 0 ? '大 ' : '小 ') + esc(Math.abs(L.delta)) + ' 岁</span>' : (L.extra && L.extra.band ? '<span class="sub2">' + esc(L.extra.band) + '</span>' : '')) + '</span>' + spark(c.series) +
        '<span class="sub2">' + esc(L.day) + ' · 实际年龄 ' + esc(L.age) + ' 岁 · 共 ' + c.series.length + ' 次化验</span>'
        : '<span class="sub2">' + esc(c.why || '还没有可用的血检') + '</span>') + '</button>';
  }
  /* EVIDENCE_NAV_R02: a node carries a typed target, never an arbitrary URL/path. */
  LIVE.graphDialog=function(title){var old=document.getElementById('graph-target');if(old)old.remove();var el=document.createElement('aside');el.id='graph-target';el.className='drawer';el.setAttribute('role','dialog');el.setAttribute('aria-label',title);el.style.cssText='position:fixed;right:0;top:0;bottom:0;width:min(560px,100vw);z-index:2400;background:var(--theme-surface-raised);color:var(--theme-text-primary);border-left:1px solid var(--theme-line-control);overflow:auto';el.innerHTML='<div class="dh"><strong>'+C.esc(title)+'</strong><button class="ibtn" aria-label="关闭" data-ptds-ui-aria-label="s3fd47edce45b">'+C.ic('x')+'</button></div><div class="db" role="status" data-ptds-ui="s821ffb8cd6a2">正在打开…</div>';document.body.appendChild(el);el.querySelector('button').onclick=function(){el.remove();};return el;};
  LIVE.openDeviceDestination=function(device){C.st.srcGroup='wearable';C.st.deviceKind=/^(oura|qkeer)$/.test(device)?'ring':device==='eight_sleep'?'bed':device==='pillbox'?'pillbox':'band';C.st.sourceDevice=device;C.goTorch('srcgroup');};
  LIVE.graphNavigate=async function(target,key){
    key=key||C.st.key;if(key!==C.st.key)return;var d=target||{},esc=C.esc,el,body;
    if(d.available===false){C.toast(d.reason||'此节点暂无可定位的内容');return;}
    try{
      if(d.kind==='data_metric'){C.st.assetF='ALL';C.st.dataSources=(d.sources||[]).slice();C.st.dataView='code';C.st.dataCode=d.code;C.st.dataPage=0;C.st.dataAll=false;C.st._dataPages=null;C.st.dataFrom='';C.st.dataTo='';C.goTorch('data');return;}
      if(d.kind==='trace'){return LIVE.openTrace(d.card_id,d.tp,d.run_id);}
      if(d.kind==='card'){
        if(LIVE.vitalsDefinition(d.card_id))return LIVE.vitalsDetail(d.card_id);
        var id=d.card_id,snap=C.S();if(id==='sjia-mas'){C.st.card='SJIA_FOCUS';return C.goTrack('status');}
        if((snap.custom_cards||[]).some(function(c){return c.card_id===id;})){C.st.ccard=id;return C.goTrack('custom');}
        var group=((snap.engines||{}).groups||[]).find(function(g){return g.cards.some(function(c){return 'engine-'+c.rule===id||c.rule===id;});});
        if(group){C.st.group=group.id;C.st.ecard={g:group.id,r:String(id).replace(/^engine-/,'')};return C.goTrack('ecard');}
        if(id==='VITALS'||String(id).indexOf('VITALS:')===0){C.st.card='VITALS';C.st.vitalsFamily=id.indexOf(':')>=0?id.slice(7):null;return C.goTrack('status');}
        C.toast('这张卡片暂无可打开的页面，历史证据仍保留');return;
      }
      if(d.kind==='source'){if(d.device)return LIVE.openDeviceDestination(d.device);C.st.srcGroup='file';return C.goTorch(/GENE/.test(d.source_kind)?'gene':'srcgroup');}
      if(d.kind==='grant'){C.st.gid=d.grant_id;return window.__ptds.goCluster('grant');}
      if(d.kind==='store'){C.st.srcGroup='file';return C.goTorch('gene');}
      if(d.kind==='alert'){
        var home=await callAsync('GET','/api/state/refresh?key='+encodeURIComponent(key));if(C.st.key!==key)return;LIVE.acceptHome(key,C.SNAPS[key],home);LIVE._bellFocus=d.dedupe_key;LIVE.bellOpen();return;
      }
      el=LIVE.graphDialog(d.kind==='document'?'证据原件':d.kind==='observation'?(d.revision?'数据资产 · 指定版本':'数据资产 · 最新版本'):d.kind==='party'?'对象的关联授权':d.kind==='channel'?'通道送达记录':'关联内容');body=el.querySelector('.db');
      var current=function(){return C.st.key===key&&el.isConnected;};
      if(d.kind==='document'){
        var doc=await callAsync('GET','/api/graph/document?key='+encodeURIComponent(key)+'&doc='+encodeURIComponent(d.document_id));if(!current())return;
        if(!doc.found){body.textContent=doc.reason||'未找到已保存的原件';return;}
        body.innerHTML='<h3>'+esc(doc.name)+'</h3><p class="sub2" data-ptds-inline><!--ptds-ui:saff535dacad4-->PTDS 保存副本 · <!--/ptds-ui-->'+esc(doc.bytes)+' 字节</p><p data-reveal-status data-ptds-ui="s45b66caae284">正在访达中定位保存副本…</p><button class="btn2" data-reveal data-ptds-ui="s3131d651cc22">再次在访达中显示</button>';
        if(globalThis.PTDS_TRIAL_UI&&!PTDS_TRIAL_UI.can('finder'))return; var reveal=async function(){if(!current())return;var btn=body.querySelector('[data-reveal]');if(btn.disabled)return;btn.disabled=true;try{await callAsync('POST','/api/graph/reveal',{key:key,doc:d.document_id});if(current())body.querySelector('[data-reveal-status]').textContent='已在这台 Mac 的访达中选中保存副本';}catch(err){if(current())body.querySelector('[data-reveal-status]').textContent=err.detail||'暂时无法定位原件，请重试';}finally{if(current())btn.disabled=false;}};body.querySelector('[data-reveal]').onclick=reveal;await reveal();return;
      }
      if(d.kind==='observation'){
        var out=await callAsync('GET','/api/graph/observation?key='+encodeURIComponent(key)+'&oid='+encodeURIComponent(d.observation_id)+(d.revision?'&revision='+encodeURIComponent(d.revision):''));if(!current())return;if(!out.found){body.textContent=out.reason||'当前实例没有该版本';return;}
        var p=out.payload,t=p.temporal||{},label=(C.DICT[p.code]&&C.DICT[p.code].zh)||p.code,origin=out.origin||{};
        body.innerHTML='<h3>'+esc(label)+'</h3><p style="font-size:1.4em">'+esc((p.comparator||'')+p.value_raw+' '+(p.unit_raw||''))+'</p><dl class="kv2"><dt data-ptds-ui="sc8f71fa6ca5b">观测时间</dt><dd>'+esc(t.observed_at||t.observed_date||'时间未提供')+'</dd><dt data-ptds-ui="sa488e93d69cc">来源</dt><dd>'+esc(p.source_kind)+'</dd><dt data-ptds-ui="s5f76b2bf82dd">版本</dt><dd>第 '+esc(out.revision)+' 版'+(out.superseded?' · 历史版本，当前为第 '+esc(out.latest_revision)+' 版':'')+'</dd><dt data-ptds-ui="s6320b4a8722a">状态</dt><dd>'+esc(out.latest_status==='RETRACTED'?'当前记录已撤回，保留此历史版本':p.status==='ACTIVE'?'有效':'已撤回')+'</dd></dl><p class="sub2" data-ptds-ui="s1ff696a58461">原始字面值与来源保留，旧版本不会被最新值替代。</p>'+(origin.destination?'<button class="btn2" data-original data-ptds-ui="sc1e1a64b96ff">查看证据原件</button>':'<p class="sub2" data-ptds-ui="s80bd10d5d3e8">这条记录没有可定位的文件原件。</p>');
        var btn=body.querySelector('[data-original]');if(btn)btn.onclick=function(){if(current()){el.remove();LIVE.graphNavigate(origin.destination,key);}};if(p.source_kind==='DEVICE_OURA'&&(!globalThis.PTDS_TRIAL_UI||PTDS_TRIAL_UI.can('erasure')))LIVE.ouraErasureModule(function(m){m.markSource({host:body,key:key,source_ref:p.source_ref,current:current});});return;
      }
      if(d.kind==='party'||d.kind==='channel'){
        var list=await callAsync('GET','/api/graph/related?key='+encodeURIComponent(key)+'&kind='+d.kind+'&id='+encodeURIComponent(d.object_id||d.channel));if(!current())return;
        body.innerHTML='<p class="sub2">'+esc(list.total)+' 条关联记录'+(list.total>list.items.length?' · 当前显示最近 '+list.items.length+' 条':'')+'</p>'+list.items.map(function(x){return '<section class="box"><strong>'+esc(x.title||x.id||'送达记录')+'</strong><p>'+esc(x.status||x.result||'')+'</p><p class="sub2">'+esc(x.at||'')+'</p>'+(x.grant_id?'<button class="link" data-related-grant="'+esc(x.grant_id)+'">查看授权</button>':'')+'</section>';}).join('');body.querySelectorAll('[data-related-grant]').forEach(function(b){b.onclick=function(){if(current()){el.remove();LIVE.graphNavigate({kind:'grant',grant_id:b.dataset.relatedGrant},key);}};});return;
      }
      body.textContent=d.reason||'此节点暂时没有可定位的内容';
    }catch(err){if(key===C.st.key){if(el&&el.isConnected)el.querySelector('.db').textContent=err.detail||'暂时无法打开，请返回后重试';else C.toast(err.detail||'暂时无法打开，请重试');}}
  };
  /* EVIDENCE_NAV_R02_END */
  /* VITALS_VIEW_R02: independent definitions; exact source/metric identity. */
  LIVE.vitalsItemKey=function(x){return x.family+'\u001f'+x.code;};
  LIVE.vitalsDefinitions=function(){return C.S().vitals_cards||[];};
  LIVE.vitalsDefinition=function(id){return LIVE.vitalsDefinitions().find(function(x){return x.card_id===id||x.wall_id===id;});};
  LIVE.vitalsRows=function(card){var latest=((C.S().vitals_all||C.S().vitals||{}).items||[]),index=Object.create(null);latest.forEach(function(x){index[LIVE.vitalsItemKey(x)]=x;});return card.items.map(function(x){return Object.assign({},x,index[LIVE.vitalsItemKey(x)]||{missing:true});});};
  LIVE.vitalsSourceName=function(f){return LIVE.SOURCE_ZH[f]||f;};
  LIVE.vitalsReading=function(x){return (x.comparator||'')+String(x.value_raw!=null?x.value_raw:x.value)+' '+String(x.unit_raw!=null?x.unit_raw:x.unit||'');};
  LIVE.vitalsCardHtml=function(card){
    var esc=C.esc,rows=LIVE.vitalsRows(card);
    return '<button class="wcard vitals-summary" data-vitals-card="'+esc(card.card_id)+'" data-vitals-wall="'+esc(card.wall_id)+'"><span class="wn">'+esc(card.name)+'</span><div class="mrow">'+rows.slice(0,2).map(function(x){return '<span class="m"><span class="k">'+esc(x.label_zh||x.code)+'</span><span class="v">'+(x.missing?'—':esc(LIVE.vitalsReading(x)))+'</span><span class="sub2">'+esc(LIVE.vitalsSourceName(x.family))+' · '+esc(x.missing?'等待读数':String(x.observed_at||x.observed_date||'时间未提供').replace('T',' ').slice(0,19))+'</span>'+(!x.missing&&x.series?spark(x.series.slice(-10).map(function(p){return {tp:p.t,v:p.v};})).replace(/<text[^>]*>[^<]*<\/text>/g,''):'')+'</span>';}).join('')+'</div>'+(rows.length?'<span class="vc-more">'+C.ic('chevron-right')+'<span>'+(rows.length>2?'另有 '+(rows.length-2)+' 项':'查看详情')+'</span></span>':'<span class="sub2" data-ptds-ui="sb197b2f6ffb4">暂无读数。卡片保留，设备恢复后自动更新。</span>')+'</button>';
  };
  // Collection expansion uses the bounded home projection, never a full-history read.
  LIVE.vitalsDetail=function(id){
    var card=LIVE.vitalsDefinition(id);if(!card){C.toast('这张卡片暂不可用，请刷新后重试');return;}
    var old=document.getElementById('vitals-detail');if(old)old.remove();
    C.st.vitalsCardId=card.card_id;C.st.vitalsCardKey=C.st.key;
    C.goTrack('vitals-card');
  };
  LIVE.vitalsTrend=function(x){
    var esc=C.esc,points=(x.series||[]).slice(-60);
    if(x.missing||!points.length)return '<p class="sub2" data-ptds-ui="s12c9e4143aeb">暂无趋势记录</p>';
    if(points.length===1)return '<p class="sub2" data-ptds-ui="s4a3c7c5c09b1">仅有一条观测，积累后显示趋势</p>';
    if(x.comparator||points.some(function(p){return p.v==null||String(p.v).trim()===''||!isFinite(Number(p.v));}))return '<p class="sub2" data-ptds-ui="s708a8034fce5">当前记录不适合绘制数值趋势，请查看数据来源</p>';
    return '<div class="vc-trend" aria-label="最近观测趋势" data-ptds-ui-aria-label="s595d1994ebd2">'+spark(points.map(function(p){return {tp:p.t,v:p.v};})).replace(/<text[^>]*>[^<]*<\/text>/g,'')+'</div><div class="vc-range sub2"><span>'+esc(String(points[0].t||'').slice(0,10))+'</span><span>'+esc(String(points[points.length-1].t||'').slice(0,10))+'</span></div><p class="sub2" data-ptds-inline><!--ptds-ui:s997a5e6e513f-->最近 <!--/ptds-ui-->'+points.length+' 条观测 · '+esc(x.unit||'')+'</p>';
  };
  LIVE.renderVitalsCollection=function(){
    wall3Css();
    var key=C.st.key,esc=C.esc,card=C.st.vitalsCardKey===key&&LIVE.vitalsDefinition(C.st.vitalsCardId),view=document.getElementById('view');
    if(!card){view.innerHTML='<section class="box"><p data-ptds-ui="s797b2157fad3">这张体征卡集在当前数据基座中不可用。</p><button class="btn2" data-vc-back data-ptds-ui="s59a3a7ba38ad">返回状态卡片</button></section>';view.querySelector('[data-vc-back]').onclick=function(){C.goTrack('wall');};return;}
    var rows=LIVE.vitalsRows(card);
    view.innerHTML='<section class="vitals-collection" aria-label="'+esc(card.name)+'"><h2 class="vc-title">'+esc(card.name)+'</h2><div class="vc-toolbar"><button class="btn2" data-vc-back data-ptds-ui="s59a3a7ba38ad">返回状态卡片</button><span class="sub2">'+rows.length+' 项体征 · 按卡集设置顺序展示</span><button class="btn2" data-vc-edit data-ptds-ui="s014326c7d0ad">编辑卡集</button></div><div class="vc-grid">'+rows.map(function(x,i){return '<section class="box vc-metric" data-vc-metric="'+esc(LIVE.vitalsItemKey(x))+'"><h3>'+esc(x.label_zh||x.code)+'</h3><div class="vc-value">'+(x.missing?'—':esc(LIVE.vitalsReading(x)))+'</div><p class="sub2">'+esc(LIVE.vitalsSourceName(x.family))+' · '+esc(x.missing?'等待该来源的读数':(x.observed_at&&C.tzTime?C.tzTime(x.observed_at,true):String(x.observed_at||x.observed_date||'时间未提供').replace('T',' ').slice(0,19)))+'</p>'+LIVE.vitalsTrend(x)+(x.observation_id?'<button class="link" data-vc-data="'+i+'">查看这条数据</button>':'')+'</section>';}).join('')+'</div>'+(rows.length?'':'<div class="box" data-ptds-ui="s774b533a27ce">尚未选择体征项目，请编辑卡集添加。</div>')+'<p class="sub2" data-ptds-ui="s21d0209b5f62">连线表示本设备观测顺序，不代表连续监测；各来源独立保留。</p></section>';
    view.querySelector('[data-vc-back]').onclick=function(){C.goTrack('wall');};
    view.querySelector('[data-vc-edit]').onclick=function(){if(C.st.key===key)LIVE.renderVitalsEditor({card:card});};
    view.querySelectorAll('[data-vc-data]').forEach(function(b){b.onclick=LIVE.action(async function(){if(C.st.key!==key)return;var x=rows[Number(b.dataset.vcData)];if(LIVE.graphNavigate)return LIVE.graphNavigate({kind:'observation',available:true,observation_id:x.observation_id,revision:x.revision},key);C.st.assetsCode=x.code;C.goTorch('data');});});
  };
  LIVE.renderVitalsEditor=function(e){
    var key=C.st.key,card=e.card,esc=C.esc,old=document.getElementById('vitals-editor');if(old)old.remove();
    var choices=(C.S().vitals_catalogue||[]).slice(),known=new Set(choices.map(LIVE.vitalsItemKey));(card?card.items:[]).forEach(function(x){if(!known.has(LIVE.vitalsItemKey(x)))choices.push(x);});
    var selected=(card?card.items:[]).map(LIVE.vitalsItemKey),order=selected.concat(choices.map(LIVE.vitalsItemKey).filter(function(k){return selected.indexOf(k)<0;})),name=card?card.name:'我的体征',requestId='vitals-'+crypto.randomUUID(),pendingBody=null,busy=false,review=false;
    var el=document.createElement('aside');el.id='vitals-editor';el.setAttribute('role','dialog');el.setAttribute('aria-label',card?'编辑状态卡片':'新建我的体征');el.className='drawer';el.style.cssText='position:fixed;right:0;top:0;bottom:0;width:min(620px,100vw);z-index:2400;background:var(--theme-surface-raised);color:var(--theme-text-primary);border-left:1px solid var(--theme-line-control);box-shadow:-8px 0 24px #0002;overflow:auto';document.body.appendChild(el);
    function close(){if(busy)return;el.remove();if(!card&&C.st.key===key){C.st.eng=null;C.goTrack('wall');}}
    function item(k){return choices.find(function(x){return LIVE.vitalsItemKey(x)===k;});}
    function draw(){
      el.innerHTML='<div class="dh"><strong>'+(card?'编辑状态卡片':'新建我的体征')+'</strong><button class="ibtn" data-ve-close aria-label="关闭" data-ptds-ui-aria-label="s3fd47edce45b">'+C.ic('x')+'</button></div><div class="db"><p class="sub2">'+(review?'确认这张卡的名称和展示项。保存后会保留各设备来源。':'选择设备和指标，组成一张独立卡片。已有卡片不受影响。')+'</p><label style="display:grid;gap:8px" data-ptds-inline><!--ptds-ui:sa41ec76ecac2-->卡片名称<!--/ptds-ui--><input id="ve-name" maxlength="40" value="'+esc(name)+'"'+(review?' readonly':'')+' style="padding:10px;background:var(--theme-surface-raised);color:inherit;border:1px solid var(--theme-line-control);border-radius:8px;font:inherit"></label><h4 data-ptds-ui="s596bf9b85d5a">展示项与顺序</h4><p class="sub2" data-ptds-ui="sdf907e2a5f4a">前两项显示在卡面，其余通过详情查看。来源相同的指标不会替代其他设备的读数。</p><div id="ve-items"></div><p id="ve-error" role="alert"></p><div class="row" style="gap:8px;flex-wrap:wrap"><button class="btn" id="ve-next">'+(review?'确认保存':'预览卡片')+'</button><button class="btn2" id="ve-back">'+(review?'返回编辑':'取消')+'</button></div><p class="sub2" data-ptds-ui="s614f384424e2">只配置展示内容。设备同步、历史记录和已有授权继续保留。</p></div>';
      var list=review?order.filter(function(k){return selected.includes(k);}):order;
      el.querySelector('#ve-items').innerHTML=list.map(function(k,i){var x=item(k);return '<div style="display:flex;align-items:center;gap:8px;padding:10px 0;border-bottom:1px solid var(--theme-line-hairline)"><label style="display:flex;gap:10px;flex:1;align-items:center">'+(review?'':'<input type="checkbox" data-ve-item="'+esc(k)+'"'+(selected.includes(k)?' checked':'')+'>')+'<span>'+esc(x.label_zh||x.code)+'<br><small class="sub2">'+esc(LIVE.vitalsSourceName(x.family))+'</small></span></label>'+(!review?'<button class="ibtn" data-ve-up="'+esc(k)+'" aria-label="上移"'+(i===0?' disabled':'')+'>↑</button><button class="ibtn" data-ve-down="'+esc(k)+'" aria-label="下移"'+(i===list.length-1?' disabled':'')+'>↓</button>':'')+'</div>';}).join('')||'<p class="sub2" data-ptds-ui="seeeb8a63325e">还没有可选指标。设备首次同步后即可选择。</p>';
      el.querySelector('#ve-name').oninput=function(x){name=x.target.value;pendingBody=null;};
      el.querySelectorAll('[data-ve-item]').forEach(function(x){x.onchange=function(){selected=order.filter(function(k){return k===x.dataset.veItem?x.checked:selected.includes(k);});pendingBody=null;};});
      ['up','down'].forEach(function(d){el.querySelectorAll('[data-ve-'+d+']').forEach(function(b){b.onclick=function(){var k=b.getAttribute('data-ve-'+d),i=order.indexOf(k),j=i+(d==='up'?-1:1);if(j<0||j>=order.length)return;order.splice(i,1);order.splice(j,0,k);pendingBody=null;draw();};});});
      el.querySelector('[data-ve-close]').onclick=close;el.querySelector('#ve-back').onclick=function(){if(review){review=false;draw();}else close();};
      el.querySelector('#ve-next').onclick=async function(){
        if(busy)return;if(C.st.key!==key){el.remove();C.toast('数据基座已切换，请重新打开编辑');return;}
        var error=el.querySelector('#ve-error');if(!name.trim()||!selected.length){error.textContent='请填写名称并至少选择一个指标';return;}
        if(!review){review=true;draw();return;}
        if(!pendingBody){requestId='vitals-'+crypto.randomUUID();pendingBody={key:key,request_id:requestId,expected_revision:card?card.revision:0,name:name.trim(),items:order.filter(function(k){return selected.includes(k);}).map(function(k){var x=item(k);return {family:x.family,code:x.code};})};if(card)pendingBody.card_id=card.card_id;}
        busy=true;el.querySelectorAll('button,input').forEach(function(b){b.disabled=true;});error.textContent='正在保存…';
        try{await LIVE.cardMutation('/api/track/vitals-card',pendingBody);el.remove();if(C.st.key===key){C.st.eng=null;C.goTrack('wall');C.toast(card?'卡片已更新':'已添加独立卡片');}}
        catch(err){error.textContent=err.detail||'未收到保存确认。再次确认只核对本次请求，不重复创建。';}
        finally{busy=false;if(el.isConnected)el.querySelectorAll('button,input').forEach(function(b){b.disabled=false;});}
      };
    }
    draw();el.addEventListener('keydown',function(ev){if(ev.key==='Escape')close();});
  };
  LIVE.vitalsDelete = async function(id) {
    var card=LIVE.vitalsDefinition(id), key=C.st.key;
    if(!card){C.toast('这张卡片已不可用，请刷新');return;}
    if(!window.confirm('删除“'+card.name+'”？\n只移除这张体征卡片，保留设备数据、历史记录、已有规则与后台同步。以后可重新添加。'))return;
    LIVE._vitalsDeletes=LIVE._vitalsDeletes||{};
    var token=key+'|'+card.card_id, pending=LIVE._vitalsDeletes[token];
    if(pending&&pending.busy)return;
    if(!pending)pending=LIVE._vitalsDeletes[token]={body:{key:key,action:'delete',card_id:card.card_id,expected_revision:card.revision,request_id:'delete-'+Date.now()+'-'+Math.random().toString(16).slice(2)}};
    pending.busy=true;
    try {
      await LIVE.cardMutation('/api/track/vitals-card',pending.body);
      delete LIVE._vitalsDeletes[token];
      if(C.st.key===key){C.st.vitalsCardId=null;C.goTrack('wall');C.toast('卡片已删除，设备数据保留');}
    } catch(err) {
      if(err&&['VITALS_CARD_CONFLICT','VITALS_REQUEST_CONFLICT','VITALS_CARD_UNKNOWN'].indexOf(err.code)>=0)delete LIVE._vitalsDeletes[token];
      C.toast('删除尚未确认：'+LIVE.saveErr(err));
    } finally {pending.busy=false;}
  };
  /* VITALS_VIEW_R02_END */
  function deviceCards() {
    if (Array.isArray(C.S().vitals_cards)) return LIVE.vitalsDefinitions().map(LIVE.vitalsCardHtml);
    var esc = C.esc, S = C.S(), items = (S.vitals && S.vitals.items) || [], series = S.series || {}, fams = {};
    items.forEach(function (i) { if (DEVICE_FAMILIES.indexOf(i.family) >= 0) (fams[i.family] = fams[i.family] || []).push(i); });
    return Object.keys(fams).map(function (f) {
      var name = SRC_NAME[f === 'PHONE_HEALTH' ? 'APPLE_HEALTH' : f] || f;
      var chosen = LIVE.wallPick('card:VITALS:'+f,fams[f].slice().sort(function(a,b){return rank(a.code)-rank(b.code);}),function(x){return x.code;});
      var top = chosen.slice(0,2);  /* 卡一样大：墙上放 2 项，其余收进“另有 N 项” */
      var more = '<span class="m more">' + C.ic('chevron-right') + '<span>' + (chosen.length > 2 ? '另有 ' + (chosen.length - 2) + ' 项' : '查看更多') + '</span></span>';
      var fresh = fams[f].some(function (i) { return i.fresh; });
      return '<button class="wcard" data-card="VITALS" data-vitals-family="' + esc(f) + '"><span class="wn" data-ptds-inline><!--ptds-ui:s67a73bfaf0e7-->我的体征（<!--/ptds-ui-->' + esc(name) + '）<span class="grow"></span>' + (fresh ? '' : '<span class="badge">' + C.ic('clock') + '等待新读数</span>') + '</span>' +
        '<div class="mrow">' + top.map(function (i) {
          return '<span class="m"><span class="k">' + esc(i.label_zh.replace(/（.*）$/, '')) + '</span><span class="v">' + esc(human(i.code, i.value, i.unit)) + '</span>' + spark((series[i.code] || []).slice(-10)).replace(/<text[^>]*>[^<]*<\/text>/g, '') + '</span>';
        }).join('') + more + '</div></button>';
    });
  }
  LIVE.groupDefs = function () {  /* 卡片组 = 「增加我的状态」里建好的引擎模板（产品负责人 2026-10-14：不建模板，卡墙上就没有这个引擎） */
    var S = C.S(), out = [];
    ((S.engines && S.engines.groups) || []).forEach(function (g) {
      var items = g.cards.map(function (c) { var L = c.latest; return { zh: c.name, how: L ? (L.status === 'computed' ? (L.text || '') : (ENG_STATUS[L.status] || '')) : '还没有结果' }; });
      out.push({ id: g.id, zh: g.zh, sub: g.sub, items: items, eng: g, new: g.new });
    });
    return out;
  };
  var DAILY = { SLEEP: 1, RHYTHM: 1, EXERCISE: 1 };
  var SHORT_RULE = { 'SLEEP.A01-DURATION': '睡眠时长', 'SLEEP.A02-EFFICIENCY': '睡眠效率', 'SLEEP.A03-HRV-DEV': 'HRV 偏离', 'SLEEP.A04-LOWHR-DEV': '最低心率偏离', 'SLEEP.A05S-TIMING': '作息规律',
    'INFLAM.B01-CRP': 'CRP', 'INFLAM.B02-NLR': 'NLR', 'EXERCISE.C01-WEEKLY': '近 7 天运动', 'METAB.D01-HBA1C': 'HbA1c', 'METAB.D02-NONHDL': '非 HDL-C', 'ORGAN.E01-EGFR': 'eGFR',
    'RHYTHM.F01-TEMPDEV': '夜间体温偏离', 'BIOAGE.PHENOAGE': '表型年龄', 'BIOAGE.KDM': 'KDM 生物年龄', 'BIOAGE.HD': '稳态失调', 'MAS.HLH-2004': 'HLH-2004', 'MAS.EULAR-2016': '2016 分类标准', 'MAS.MS-2019': 'MS 评分', 'MAS.DYN': '指标变化' };
  var SHORT_GRP = { BIOAGE: '生物年龄' };
  function grpShort(g) { return SHORT_GRP[g.id] || String(g.zh).replace(/观察$/, ''); }
  function ndot(on) { return on ? '<span class="ndot" title="有新结果" aria-label="有新结果" data-ptds-ui-title="s0653c4db5be7" data-ptds-ui-aria-label="s0653c4db5be7"></span>' : ''; }
  /* 一个结果的显示文字：睡眠时长按“7 小时 50 分”显示（存的是小时） */
  function engVal(c, L) {
    if (!L) return '';
    if (L.status !== 'computed') return ENG_STATUS[L.status] || L.status_zh || '';
    if (c.rule === 'SLEEP.A01-DURATION' && L.value != null && isFinite(+L.value)) return hm(+L.value * 60);
    return prettyU(L.text, L.unit);
  }
  function prettyU(t, unit) { t = String(t || '').replace(/×10\^9\/L/g, '×10⁹/L').replace(/×10\^12\/L/g, '×10¹²/L'); return unit === '1' ? t.replace(/ 1$/, '') : t; }
  /* 分支观察卡：和上一次同项读数比（只列数，不判好坏、不设阈值） */
  function chgLine(L) {
    var x = (L && L.status === 'computed' && L.extra) || {}; if (!x.prev_day) return '';
    var sg = function (v) { return (+v > 0 ? '+' : '') + v; };
    return '上次 ' + String(x.prev_day).slice(5) + '：' + prettyU(x.prev_text, L.unit) + (x.change != null ? ' · 变化 ' + sg(x.change) + (x.change_pct != null ? '（' + sg(x.change_pct) + '%）' : '') : '');
  }
  function nolabels(svg) { return svg.replace(/<text[^>]*>[^<]*<\/text>/g, ''); }
  /* 指标卡批注：变化靠近主数值；点值和起止时间保留，长序列横向查看。 */
  function cardChange(L) {
    var x = (L && L.extra) || {};
    if (x.change == null) return '';
    var value = String(x.change), plus = !/^-|^0(?:\.0+)?$/.test(value) ? '+' : '';
    return '<span class="metric-change" title="' + C.esc(x.prev_day ? '与 ' + x.prev_day + ' 的记录相比' : '与上次记录相比') + '">较上次 ' +
      C.esc(plus + value + (L.unit && L.unit !== '1' ? ' ' + prettyU(L.unit, '') : '')) + '</span>';
  }
  function cardTrend(c) {
    var pts = (c.series || []).filter(function (p) { return p.v != null && isFinite(+p.v); }), esc = C.esc;
    if (!pts.length) return '<span class="sub2" data-ptds-ui="sbbb6a62f24ed">暂无有效趋势记录</span>';
    var labels = pts.map(function (p) { return prettyU(p.value_text != null ? p.value_text : String(p.v), ''); });
    var labelWidth = Math.max.apply(null, labels.map(function (s) {
      return Array.from(s).reduce(function (w, ch) { return w + (ch.charCodeAt(0) > 255 ? 14 : 8); }, 0);
    }));
    var spacing = Math.max(54, labelWidth + 24), pad = Math.max(24, labelWidth / 2 + 12);
    var W = Math.max(280, (pts.length - 1) * spacing + 2 * pad), H = 104;
    var vs = pts.map(function (p) { return +p.v; }), lo = Math.min.apply(null, vs), hi = Math.max.apply(null, vs);
    var X = function (i) { return pts.length === 1 ? W / 2 : pad + i * (W - 2 * pad) / (pts.length - 1); };
    var Y = function (v) { return hi === lo ? 64 : 84 - (v - lo) / (hi - lo) * 40; };
    var total = c.series_count == null ? pts.length : c.series_count, first = pts[0].tp, last = pts[pts.length - 1].tp;
    var shortDate = function (tp) { return String(first).slice(0, 4) === String(last).slice(0, 4) ? String(tp).slice(5) : tp; };
    var svg = '<svg class="metric-spark" viewBox="0 0 ' + W + ' ' + H + '" style="min-width:' + W + 'px" role="img" aria-label="' + esc(c.name + '，' + pts.length + ' 个时点的趋势') + '">' +
      '<polyline class="ln" vector-effect="non-scaling-stroke" points="' + pts.map(function (p, i) { return X(i).toFixed(1) + ',' + Y(+p.v).toFixed(1); }).join(' ') + '"/>' +
      pts.map(function (p, i) {
        return '<circle class="end" cx="' + X(i) + '" cy="' + Y(+p.v) + '" r="' + (i === pts.length - 1 ? 3 : 2) + '"><title>' + esc(p.tp + '：' + labels[i]) + '</title></circle>' +
          '<text x="' + X(i) + '" y="' + (Y(+p.v) - 12) + '" text-anchor="middle">' + esc(labels[i]) + '</text>';
      }).join('') + '</svg>';
    return '<span class="metric-trend" tabindex="0" role="group" aria-label="趋势图，可横向查看全部点值" data-ptds-ui-aria-label="s84e337243dbd">' + svg + '</span>' +
      '<span class="metric-range sub2"><span title="起始采样时间：' + esc(first) + '">' + esc(shortDate(first)) + '</span>' +
      '<span title="按有效采样时点计数，同一时点更正不重复计数" data-ptds-ui-title="s779832409d88">' + (total > pts.length ? '近 ' + pts.length + ' 次 / ' : '') + '共 ' + total + ' 次</span>' +
      '<span title="最近采样时间：' + esc(last) + '">' + esc(shortDate(last)) + '</span></span>';
  }
  var SRC_CSS = '.cap[hidden]{display:none!important}' +
    '.rl-ic{display:inline-grid;place-items:center;width:26px;height:26px;margin-left:8px;border-radius:8px;border:var(--primitive-border-hairline) solid var(--theme-line-hairline);color:var(--theme-text-secondary);cursor:pointer;flex:none}.rl-ic:hover{color:#E8B65A;border-color:#E8B65A}.rl-ic .ic{width:15px;height:15px}' +
    '.mgrid{display:grid;grid-template-columns:2fr 1fr 1fr 1fr 1.4fr;gap:12px}.mgrid2{display:grid;grid-template-columns:1fr 3fr;gap:12px}@media (max-width:900px){.mgrid,.mgrid2{grid-template-columns:minmax(0,1fr)}}' +
    '.srcards{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:var(--primitive-space-4);margin-top:var(--primitive-space-4)}' +
    '.srcard{display:flex;flex-direction:column;gap:var(--primitive-space-2);text-align:left;min-height:200px;padding:var(--primitive-space-5);background:var(--theme-surface-raised);border:var(--primitive-border-hairline) solid var(--theme-line-hairline);border-radius:var(--primitive-radius-card);color:inherit;font:inherit;cursor:pointer}' +
    '.srcard:hover{border-color:var(--theme-line-control)}.srcard[aria-disabled="true"]{cursor:default;border-style:dashed;color:var(--theme-text-secondary)}' +
    '.srcard .sc-top{display:flex;align-items:center;margin-bottom:var(--primitive-space-2)}.srcard .sc-top>.ic{margin-left:auto;color:var(--theme-text-tertiary)}' +
    '.srcard .sc-ic{display:inline-grid;place-items:center;width:44px;height:44px;border-radius:12px;border:var(--primitive-border-hairline) solid var(--theme-line-hairline)}.srcard .sc-ic .ic{width:24px;height:24px;font-size:24px}' +
    '.srcard .nm{font-size:var(--scale-type-driver);display:flex;gap:var(--primitive-space-2);align-items:center;flex-wrap:wrap}' +
    '.srcard .sc-note{margin-top:auto;display:flex;gap:4px;align-items:center;font-size:var(--scale-type-meta);color:var(--theme-text-secondary)}' +
    '#view .box h3 #src-back{margin-left:auto;font-size:var(--scale-type-meta)}' +
    '@media (max-width:1100px){.srcards{grid-template-columns:repeat(2,minmax(0,1fr))}}@media (max-width:560px){.srcards{grid-template-columns:minmax(0,1fr)}.srcard{min-height:0}}';
  var WALL3_CSS = '.vc-title{font-size:var(--scale-type-title);margin:0 0 20px;font-weight:500}.vitals-collection .vc-toolbar{display:flex;align-items:center;gap:16px;flex-wrap:wrap;margin-bottom:20px}.vc-toolbar [data-vc-edit]{margin-left:auto}.vc-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,300px),1fr));gap:20px}.vc-metric{min-width:0;margin:0;display:flex;flex-direction:column;gap:10px}.vc-metric h3,.vc-metric p{margin:0}.vc-value{font-size:var(--scale-type-title);overflow-wrap:anywhere}.vc-trend .spk{display:block;width:100%;height:100px;margin-top:14px}.vc-range{display:flex;justify-content:space-between;gap:12px}.vc-metric .link{align-self:flex-start;margin-top:auto}.wallu .wcard.vitals-summary{grid-template-rows:auto minmax(0,1fr);padding-bottom:52px}.vitals-summary .vc-more{position:absolute;left:var(--primitive-space-5);bottom:12px;right:48px;min-height:26px;justify-content:flex-start;background:none}.vitals-summary .mrow{align-content:start}.vitals-summary .mrow{min-height:0;overflow:hidden;gap:16px}.vitals-summary .mrow .k{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.vitals-summary .mrow .sub2{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.vitals-summary .spk{height:32px}.vc-more{display:flex;align-items:center;gap:6px;font-size:var(--scale-type-meta);color:var(--theme-text-secondary)}.vc-more svg{width:18px;height:18px}' +
    '.wall2{grid-template-columns:repeat(auto-fill,minmax(340px,1fr))}.wall2 .wcard{min-height:0}' +
    /* 产品负责人 2026-10-14 10:51：我的状态墙上的卡一样大（两个实例都是）；放不下的收进“另有 N 项”或卡片详情，不撑高 */
    '.wallu{grid-auto-rows:260px}.wallu .wcard{height:100%;overflow:hidden}' +
    '.fdot{display:inline-block;width:7px;height:7px;border-radius:50%;margin-left:6px;vertical-align:middle;background:var(--theme-text-tertiary)}.fdot.on{background:#3aa58f}' +
    '.ndot{width:8px;height:8px;border-radius:4px;background:var(--theme-text-primary);display:inline-block;margin-left:var(--primitive-space-2);flex:none}' +
    '.wcard .hk{font-size:var(--scale-type-meta);color:var(--theme-text-tertiary)}.hv{font-size:var(--scale-type-title);color:var(--theme-text-primary);line-height:1.25}' +
    '.wcard .also{display:flex;flex-wrap:wrap;gap:4px var(--primitive-space-4);font-size:var(--scale-type-meta);color:var(--theme-text-secondary)}.wcard .also b{font-weight:var(--primitive-font-weight-regular);color:var(--theme-text-tertiary)}' +
    '.wsec{font-size:var(--scale-type-meta);color:var(--theme-text-tertiary);margin:var(--primitive-space-6) 0 var(--primitive-space-3)}.wsec:first-of-type{margin-top:var(--primitive-space-2)}' +
    '.ebox .spk{width:100%;height:120px;margin:var(--primitive-space-2) 0 0}.ebox .spk .end{display:none}.ebox .ends{display:flex;justify-content:space-between}.ebox .used summary,.ebox .how summary{cursor:pointer;font-size:var(--scale-type-meta);color:var(--theme-text-secondary)}' +
    '.gsum{display:flex;flex-wrap:wrap;gap:var(--primitive-space-2) var(--primitive-space-6);margin-bottom:var(--primitive-space-4);color:var(--theme-text-secondary)}.gsum b{font-size:var(--scale-type-title);font-weight:var(--primitive-font-weight-regular);color:var(--theme-text-primary);margin-right:4px}' +
    '.tabs{display:flex;gap:var(--primitive-space-2);flex-wrap:wrap;margin-bottom:var(--primitive-space-4)}' +
    '.dcode{display:grid;grid-template-columns:minmax(0,1.1fr) minmax(0,1fr) minmax(140px,1fr) minmax(0,.9fr) 20px;gap:var(--primitive-space-3);align-items:center;width:100%;padding:var(--primitive-space-3) 0;border:0;border-bottom:var(--primitive-border-hairline) solid var(--theme-line-hairline);background:none;color:inherit;font:inherit;text-align:left;cursor:pointer}' +
    '.dcode .spk{width:100%;max-width:260px;height:28px;margin:0}.dcode.hd{cursor:default;color:var(--theme-text-tertiary);font-size:var(--scale-type-meta)}' +
    '.l1{display:grid;grid-template-columns:minmax(0,1fr) auto auto;gap:var(--primitive-space-3);align-items:center;padding:7px 0;border-bottom:var(--primitive-border-hairline) solid var(--theme-line-hairline);font-size:var(--scale-type-meta)}.l1>span:first-child{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;color:var(--theme-text-primary)}.l1 .sub2{white-space:nowrap}.gall{display:block;width:100%;text-align:center;margin-top:var(--primitive-space-3)}' +
    '@media (max-width:700px){.dcode{grid-template-columns:minmax(0,1fr) auto 20px}.dcode .hs{display:none}}';
  /* 墙上的卡片组：1 个主数字 + 最多 2 项 + “另有 N 项”；公式、编号、版本都不上墙 */
  function grpCard(g) {
    var esc = C.esc, S = C.S(), items;
    items = g.eng.cards.map(function (c) { var L = c.latest; return { id:c.rule, k: SHORT_RULE[c.rule] || c.name, v: L ? engVal(c, L) : '还没有结果', ok: !!(L && L.status === 'computed'), ser: c.series, tp: L && L.tp }; });
    items=LIVE.wallPick('grp:'+g.id,items,function(x){return x.id;});
    var custom=((S.wall_prefs||{}).display||{})['grp:'+g.id];
    var hi = (custom?items[0]:items.filter(function (x) { return x.ok; })[0]) || items[0] || { k: '', v: '还没有结果' }, rest = items.filter(function (x) { return x !== hi; }), two = rest.slice(0, 2);
    return '<button class="wcard grp" data-group="' + g.id + '"><span class="wn">' + esc(grpShort(g)) + ndot(g.new) + '<span class="grow"></span>' + (hi.tp ? '<span class="sub2">' + esc(String(hi.tp).slice(5)) + '</span>' : '') + '</span>' +
      '<span class="hk">' + esc(hi.k) + '</span><span class="hv">' + esc(hi.v) + '</span>' + (hi.ser ? nolabels(spark(hi.ser)) : '') +
      (two.length ? '<span class="also">' + two.map(function (x) { return '<span><b>' + esc(x.k) + '</b> ' + esc(x.v) + '</span>'; }).join('') + '</span>' : '') +
      (rest.length > 2 ? '<span class="sub2" data-ptds-inline><!--ptds-ui:s268ec6902063-->另有 <!--/ptds-ui-->' + (rest.length - 2) + ' 项</span>' : '') + '</button>';
  }
  function wall3Css() { wallCss(); if (!document.getElementById('wall3-css')) { var s = document.createElement('style'); s.id = 'wall3-css'; s.textContent = WALL3_CSS; document.head.appendChild(s); } }
  LIVE.renderWall = function () {
    wall3Css();
    var esc = C.esc, ic = C.ic, st = C.st, S = C.S(), PROD = C.DATA.product || {}, daily = [], lab = [], later = [];
    LIVE.groupDefs().forEach(function (g) { (DAILY[g.id] ? daily : lab).push(grpCard(g)); });
    if ((S.instance.cards || []).indexOf('VITALS') >= 0 || (S.vitals_cards||[]).length) {
      var dv = deviceCards();
      daily.unshift(dv.length ? dv.join('') : '<button class="wcard" data-card="VITALS"><span class="wn" data-ptds-ui="sd1cf5de0c8e7">我的体征</span><span class="sub2" data-ptds-ui="s9941dc22308a">还没有绑定设备读数</span></button>');
    }
    (S.custom_cards || []).forEach(function (c) {
      var cur = c.current, code = ((c.definition || {}).code || '');
      (/^(OURA_|AH_)/.test(code) ? daily : lab).push('<button class="wcard lv-' + (cur ? cur.level : 'NONE') + '" data-ccard="' + esc(c.card_id) + '"><span class="wn">' + esc(c.name) + (c.new_alert ? '<span class="ndot" title="有新提醒" aria-label="有新提醒" data-ptds-ui-title="s02bf15d12048" data-ptds-ui-aria-label="s02bf15d12048"></span>' : '') + '<span class="grow"></span>' + (cur ? '<span class="sub2">' + esc(String(cur.tp).slice(5)) + '</span>' : '') + '</span>' +
        (cur ? '<span class="wl">' + C.levelSvg(cur.level, '') + '<span class="lvname">' + esc(cur.level_zh) + '</span></span>' : '<span class="sub2" data-ptds-ui="sda7c6f3f7674">还没有可以计算的时点</span>') +
        nolabels(spark(c.series, c.definition && (c.definition.method === 'ABOVE' || c.definition.method === 'BELOW') ? +c.definition.threshold : null)) + '</button>');
    });
    LIVE.bandWallCards().forEach(function (h) { daily.push(h); });
    (PROD.wall_placeholders || []).forEach(function (p) {  /* 规划中的占位卡收进“新建状态卡”（产品负责人 2026-10-14） */
      if (p.id === 'LONGEVITY') return;
      if (p.id === 'SLEEP' && LIVE.sleepLive(p)) {
        var sl = S.sleep, tot = (sl.series.OURA_TOTAL_SLEEP || sl.series.AH_SLEEP || []).map(function (x) { return { tp: x.tp, v: +x.v / 60 }; });
        daily.push(LIVE.sleepWall(p).replace(/<\/button>$/, nolabels(spark(tot)) + '</button>')); return;
      }
      later.push(p.zh);
    });
    var add = '<button class="wcard add" id="w-new"><span>' + ic('plus') + '</span><span>新建状态卡</span></button>';  /* 产品负责人 09:26：去掉“规划中：…”那一行 */
    (lab.length ? lab : daily).push(add);
    var two = daily.length && lab.length;
    var sec = function (t, arr) { return arr.length ? (two ? '<div class="wsec">' + t + '</div>' : '') + '<div class="wall2 wallu">' + arr.join('') + '</div>' : ''; };
    document.getElementById('view').innerHTML = C.pgh('我的状态') + sec('每天变化（设备）', daily) + sec('化验与报告', lab);
    document.querySelectorAll('[data-vitals-card]').forEach(function(b){b.onclick=function(){LIVE.vitalsDetail(b.dataset.vitalsCard);};});
    document.querySelectorAll('[data-card]').forEach(function (b) { b.onclick = function () { st.card = b.dataset.card; st.vitalsFamily = b.dataset.vitalsFamily || null; st.deviceMetric = 'all'; st.view = 'status'; st.pulse = true; C.render(); }; });
    document.querySelectorAll('[data-group]').forEach(function (b) { b.onclick = function () { st.group = b.dataset.group; st.view = 'group'; C.render(); window.scrollTo(0, 0); }; });
    LIVE.bindCustomWall();
    document.querySelectorAll('[data-band-go]').forEach(function (b) { b.onclick = function () { C.goTorch('data'); }; });
    document.getElementById('w-new').onclick = function () { st.eng = null; C.goTrack('eng'); };
  };
  /* 体验腕带三张卡（产品负责人 2026-10-14 10:51 确认示意稿 v2）：卡面只放数值和一个小标签，说明都在规则图标点开的规则库里。
     只有存了 Somaloop 读数的实例（sJIA 演示）才有；新鲜度用小圆点（绿 = 1 分钟内）。 */
  LIVE.bandWallCards = function () {
    var esc = C.esc, B = C.S().band_cards;
    if (!B || !B.spot) return [];
    var daily = (C.S().device_policy || {}).mode === 'daily';
    var stopped = daily ? '<span class="sub2" data-ptds-ui="sd0e3ac1bd75e">逐点分析已停止 · 仅显示历史结果</span>' : '';
    var dot = function (f) { f = f && !daily; return '<span class="fdot' + (f ? ' on' : '') + '" title="' + (daily ? '历史读数' : f ? '刚测的（1 分钟内）' : '不是刚测的') + '"></span>'; };
    var spot = '<button class="wcard" data-band-go="1" data-brule="LIVE.SOMALOOP-SPOT"><span class="wn" data-ptds-inline><!--ptds-ui:s15cad7068703-->现场体征 · Somaloop<!--/ptds-ui--><span class="grow"></span></span><div class="mrow">' +
      LIVE.wallPick('band:LIVE.SOMALOOP-SPOT',B.spot,function(x){return x.label;}).map(function (x) { return '<span class="m"><span class="k">' + esc(x.label) + '</span><span class="v">' + (x.value == null ? '—' : esc(x.value + ' ' + x.unit) + dot(x.fresh)) + '</span></span>'; }).join('') + '</div>' + stopped + '</button>';
    var s = B.spo2_low;
    var low = '<button class="wcard" data-band-go="1" data-brule="LIVE.SPO2-LOW"><span class="wn" data-ptds-inline><!--ptds-ui:sacd13457dada-->血氧低值提示<!--/ptds-ui--><span class="grow"></span></span>' +
      '<span class="hv">' + (s.n ? s.low + ' / ' + s.n : '—') + '</span><span class="sub2">' + (s.n ? '研究演示' : '这位体验者还没有血氧读数') + '</span>' + stopped + '</button>';
    var night = '<button class="wcard" data-band-go="1" data-brule="SLEEP.A03-HRV-DEV-SOMALOOP"><span class="wn" data-ptds-inline><!--ptds-ui:s09151cb6695c-->夜间基线偏离 · Somaloop<!--/ptds-ui--><span class="grow"></span></span>' +
      LIVE.wallPick('band:SLEEP.A03-HRV-DEV-SOMALOOP',B.night,function(x){return x.label;}).map(function (r) { return '<span class="sub2">' + esc(r.label) + '　' + (r.status === 'computed' ? esc(r.text) : '数据还不够 · ' + r.have + '/' + r.need + ' 晚') + '</span>'; }).join('') + stopped + '</button>';
    return [spot, low, night];
  };
  LIVE.groupCrumb = function () {
    var g = LIVE.groupDefs().filter(function (x) { return x.id === C.st.group; })[0];
    return [{ t: '我的状态', go: function () { C.st.group = null; C.goTrack('wall'); } }, { t: g ? g.zh : '卡片组' }];
  };
  function toLab(tp, focus) { var st = C.st; st.cmpTp = tp || null; st.labFocus = focus || null; st.labTab = 'compete'; st.view = 'adv'; C.render(); window.scrollTo(0, 0); }
  LIVE.renderGroup = function () {
    wall3Css();
    var esc = C.esc, ic = C.ic, st = C.st, S = C.S(), v = document.getElementById('view'), html = '';
    var g = LIVE.groupDefs().filter(function (x) { return x.id === st.group; })[0];
    if (!g) { st.view = 'wall'; return LIVE.renderWall(); }
    html += LIVE.engGroupHtml(g.eng);
    v.innerHTML = C.pgh(g.zh) + html;
    document.querySelectorAll('[data-card]').forEach(function (b) { b.onclick = function () { st.card = b.dataset.card; st.vitalsFamily = b.dataset.vitalsFamily || null; st.deviceMetric = 'all'; st.view = 'status'; st.pulse = true; C.render(); }; });
    LIVE.bindEngGroup(g.eng);
    var mg = document.getElementById('med-go'); if (mg) mg.onclick = function () { st.entry = C.newEntry(); st.entry.method = 'meds'; C.goTorch('entry'); };
  };
  /* 状态实验室：生物年龄三种算法并排（同一次化验） */
  LIVE.bioLabHtml = function () {
    var esc = C.esc, ic = C.ic, st = C.st, B = C.S().bioage;
    if (!B || C.S().instance.kind !== 'REAL') return '';
    var days = {}; B.cards.forEach(function (c) { c.series.forEach(function (p) { days[p.tp] = 1; }); });
    var ds = Object.keys(days).sort(), day = st.bioDay && days[st.bioDay] ? st.bioDay : ds[ds.length - 1];
    var h = '<section class="box sub-card" id="lab-bio"><h3>' + ic('flask-conical') + '生物年龄：三种算法并排<span class="grow"></span></h3>' +
      '<div data-ptds-inline><!--ptds-ui:s42e7dd3f3111-->同一次化验，按 PhenoAge、KDM、稳态失调各算一遍，看它们是否一致。<!--/ptds-ui-->' + esc(B.note) + '</div>';
    if (B.need_profile) return h + '<div class="sub2" data-ptds-ui="s58063347555f">先在“生物年龄计算引擎”卡片组里填出生日期和性别。</div></section>';
    if (!day) return h + '<div class="sub2" data-ptds-ui="s39699c932296">还没有算得出的化验日期。</div></section>';
    h += '<div class="chips" role="group" aria-label="选择化验日期" data-ptds-ui-aria-label="s60c0da856602">' + ds.map(function (d) { return '<button class="chip" data-bio-day="' + esc(d) + '" aria-pressed="' + (d === day) + '">' + esc(d) + '</button>'; }).join('') + '</div><div class="cp-cols">';
    B.cards.forEach(function (c) {
      var pt = c.series.filter(function (p) { return p.tp === day; })[0], L = c.latest && c.latest.day === day ? c.latest : null;
      h += '<div class="box cp-col"><h3>' + esc(c.zh) + '</h3><div class="big">' + (pt ? esc(pt.v) + ' ' + esc(c.unit) : '这天算不了') + '</div><div class="sub2">' + esc(c.how) + '</div><div class="sub2" data-ptds-inline><!--ptds-ui:s362a75d274c6-->出处：<!--/ptds-ui-->' + esc(c.source) + '</div>' + spark(c.series) + '</div>';
    });
    h += '</div>';
    var L = (B.cards.filter(function (c) { return c.latest && c.latest.day === day && c.latest.inputs; })[0] || {}).latest;
    if (L) h += '<details class="more"><summary>' + esc(day) + ' 用到的数据（实际年龄 ' + esc(L.age) + ' 岁）</summary><div class="bio-in">' + L.inputs.map(function (x) {
      return '<span>' + esc(x.label_zh) + '</span><span>' + (x.missing ? '没有' : esc(x.value_text) + ' ' + esc(x.unit)) + '</span><span class="sub2">' + (x.missing ? '' : esc(x.day) + (x.borrowed ? '（借用）' : '') + (x.note ? ' · ' + esc(x.note) : '')) + '</span>';
    }).join('') + '</div></details>';
    return h + '</section>';
  };
  LIVE.bindBioLab = function () {
    document.querySelectorAll('[data-bio-day]').forEach(function (b) { b.onclick = function () { C.st.bioDay = b.dataset.bioDay; LIVE.renderAdvanced(); }; });
    if (C.st.labFocus) { var el = document.getElementById(C.st.labFocus === 'bio' ? 'lab-bio' : 'lab-compete'); C.st.labFocus = null; if (el) el.scrollIntoView(); }
  };
  /* ---------- 星轨 · 计算引擎模板（产品负责人 2026-10-14，R05/R06）：「增加我的状态」五步 + 卡片组 + 算法卡页（历次结果）+ 状态规则库 ---------- */
  var ENG_CSS = '.ech{display:grid;gap:var(--primitive-space-2)}.ech .row{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:var(--primitive-space-1) var(--primitive-space-3);padding:var(--primitive-space-3) 0;border-bottom:var(--primitive-border-hairline) solid var(--theme-line-hairline)}' +
    '.ech .row:last-child{border-bottom:0}.ech .nm{font-weight:var(--primitive-font-weight-medium)}.ech .sub2{grid-column:1/-1}' +
    '.st-ok{color:var(--theme-text-primary)}.st-no{color:var(--theme-text-tertiary)}' +
    '.newtag{font-size:var(--scale-type-meta);padding:1px 8px;border-radius:999px;border:var(--primitive-border-hairline) solid var(--theme-text-primary);color:var(--theme-text-primary);white-space:nowrap}' +
    '.runs details{border-top:var(--primitive-border-hairline) solid var(--theme-line-hairline);padding:var(--primitive-space-2) 0}.runs summary{cursor:pointer;font-size:var(--scale-type-meta);color:var(--theme-text-secondary)}' +
    '.runs .it{display:grid;grid-template-columns:7em minmax(0,1fr);gap:2px var(--primitive-space-3);font-size:var(--scale-type-meta);margin-top:var(--primitive-space-1)}' +
    '.rtab{width:100%;border-collapse:collapse;font-size:var(--scale-type-meta)}.rtab th{text-align:left;font-weight:var(--primitive-font-weight-regular);color:var(--theme-text-tertiary);padding:var(--primitive-space-2) var(--primitive-space-3);border-bottom:var(--primitive-border-hairline) solid var(--theme-line-control)}' +
    '.rtab td{padding:var(--primitive-space-3);border-bottom:var(--primitive-border-hairline) solid var(--theme-line-hairline);vertical-align:top}.rtab tr.r{cursor:pointer}.rtab tr.r:hover td{background:var(--component-currentCard-bg,transparent)}' +
    '.rtab .nm{color:var(--theme-text-primary)}.rtab .dim{color:var(--theme-text-tertiary)}' +
    '.rkv{display:grid;grid-template-columns:7em minmax(0,1fr);gap:var(--primitive-space-2) var(--primitive-space-3);font-size:var(--scale-type-meta)}.rkv>span:nth-child(odd){color:var(--theme-text-tertiary)}' +
    '@media (max-width:700px){.rtab .hide-s{display:none}}';
  function engCss() { if (!document.getElementById('eng-css')) { var s = document.createElement('style'); s.id = 'eng-css'; s.textContent = ENG_CSS; document.head.appendChild(s); } }
  function E() { return C.S().engines || { templates: [], groups: [] }; }
  function tplOf(id) { return E().templates.filter(function (t) { return t.id === id; })[0]; }
  function grpOf(id) { return E().groups.filter(function (g) { return g.id === id; })[0]; }
  var ENG_STATUS = { computed: '已算出', insufficient_data: '数据不足', invalid_input: '输入无效', not_applicable: '不适用' };
  function srcLink(s, short) {
    var esc = C.esc;
    if (!s) return '';
    if (!s.url) return '<span class="sub2">' + esc(short ? '无原文（' + s.cite.replace(/（.*$/, '') + '）' : s.cite) + '</span>';
    return '<a class="link" href="' + esc(s.url) + '" target="_blank" rel="noopener noreferrer">' + (short ? '原文' : esc(s.cite)) + '</a>' + (s.link_checked ? '' : '<span class="sub2" data-ptds-ui="s2997fd10ce7f"> · 链接待核实</span>');
  }
  /* 「增加我的状态」第 0 步：状态计算卡（引擎模板 + “我的体征” + “自定义规则”一组列出，产品负责人 2026-10-14） */
  LIVE.engTplOk = function (id) { return !!(id && id.indexOf('ENG:') === 0 && tplOf(id.slice(4))); };
  LIVE.engTplGrid = function (e, base) {
    var esc = C.esc, ts = E().templates;
    var more = (base || []).filter(function (t) { return t.id === 'VITALS' || t.id === 'CUSTOM'; }).map(function (t) {
      var ok = t.maturity === 'ready' || (t.id === 'CUSTOM' && LIVE.customOk(t));
      return '<button class="tpl" data-tpl="' + t.id + '" aria-pressed="' + (e.tpl === t.id) + '"' + (ok ? '' : ' aria-disabled="true"') + '><span class="nm">' + esc(t.zh) + C.mtag(t.maturity) + '</span><span class="sub2">' + esc(t.sub) + '</span></button>'; });
    return '<div class="sub2" style="display:flex;gap:var(--primitive-space-2);align-items:center" data-ptds-ui="sb4e11bad6b87">选一张状态计算卡。每张卡决定用什么数据、怎么算。</div><div class="grid3">' + ts.map(function (t) {
      var id = 'ENG:' + t.id;
      return '<button class="tpl" data-tpl="' + id + '" aria-pressed="' + (e.tpl === id) + '"><span class="nm">' + esc(SHORT_GRP[t.id] || t.zh) + C.mtag('beta') + (t.active ? ' <span class="tag" data-ptds-ui="sdfb802238b38">已启用</span>' : '') + '</span><span class="sub2">' + esc(t.sub) + '</span></button>';
    }).concat(more).join('') + '</div>';
  };
  LIVE.renderEngTpl = function (e) {
    engCss();
    var esc = C.esc, ic = C.ic, v = document.getElementById('view'), STEPS = ['选模板', '绑数据', '定规则', '配通知', '审方案'];
    var t = tplOf(e.tpl.slice(4)), must = t.notify === 'required', body = '', can = true;
    var x = e.x = e.x || { check: null, rules: null, notify: must };
    if (must) x.notify = true;
    var rules = (x.check && x.check.rules) || [];
    if (e.step === 1) {
      if (!x.check) {
        body = '<section class="confirm"><div>“' + esc(t.zh) + '”有 ' + t.rules.length + ' 条规则。先检查这份数据里有没有它们要用的指标。</div>' +
          '<div class="opts"><button class="btn" id="et-check">' + ic('list-checks') + '一键检查匹配数据</button></div></section>';
        can = false;
      } else {
        var c = x.check;
        body = '<section class="confirm"><div><b>' + c.computable + ' / ' + rules.length + '</b> 条规则现在能算。</div><div class="ech">' + rules.map(function (r) {
          var ok = r.status === 'computed', ins = r.inputs.filter(function (i) { return i.days; });
          return '<div class="row"><span class="nm">' + esc(r.name) + '</span><span class="' + (ok ? 'st-ok' : 'st-no') + '">' + esc(r.status_zh || '') + '</span>' +
            '<span class="sub2">' + (ins.length ? '用到 ' + ins.map(function (i) { return esc(i.label.replace(/（.*）$/, '')) + ' ' + i.days + ' 天'; }).join('、') : '还没有要用的数据') + (r.reason ? ' · ' + esc(r.reason) : '') + '</span></div>';
        }).join('') + '</div>' +
          (c.need_profile ? '<form class="bio-form" id="et-prof"><label data-ptds-inline><!--ptds-ui:s1c54caca8ead-->出生日期<!--/ptds-ui--><input class="inp" type="date" id="et-bd" required></label><label data-ptds-inline><!--ptds-ui:sa752a7d8c127-->性别<!--/ptds-ui--><select class="inp" id="et-sex"><option value="">请选择</option><option>男</option><option>女</option></select></label><button class="btn2" type="submit">' + ic('check') + '保存，再检查一次</button><span class="sub2" data-ptds-ui="scfe088221c8f">有几条规则要用实际年龄和性别。只存在本机这份数据里，填一次就够。</span></form>' : '') +
          '<div class="opts"><button class="link" id="et-check">' + ic('list-checks') + '重新检查</button></div></section>';
        can = c.computable > 0;
      }
    } else if (e.step === 2) {
      if (!x.rules) { x.rules = {}; rules.forEach(function (r) { x.rules[r.rule] = r.status === 'computed'; }); }
      body = '<section class="confirm"><div data-ptds-ui="s31b5fbbe6f24">选这组卡里要哪几条规则。规则内容来自状态规则库，这里只选不改。</div><div class="ech">' + rules.map(function (r) {
        return '<label class="row chk"><span><input type="checkbox" data-et-r="' + esc(r.rule) + '"' + (x.rules[r.rule] ? ' checked' : '')  + '> <span class="nm">' + esc(r.name) + '</span></span><span class="sub2">' + esc(r.ref) + '</span></label>';
      }).join('') + '</div>' + '<div class="sub2" data-ptds-ui="se2e67de728f8">没勾的规则不出卡，以后可以在这里加回来。</div>' + '</section>';
      can = Object.keys(x.rules).some(function (k) { return x.rules[k]; });
    } else if (e.step === 3) {
      body = '<section class="confirm" data-sem="SEM-31">' + (must
        ? '<div data-ptds-ui="se8060af1f0c7">预警引擎必须配通知。综合关注等级比上一次记下的高时提醒一次，同一时点同一等级只提醒一次。</div>' +
          '<label class="chk"><input type="checkbox" checked disabled>状态通知（页面横幅） <span class="soon" data-ptds-ui="sce115ad5b7e3">不可关闭</span></label>' +
          '<label class="chk"><input type="checkbox" checked disabled>通知我自己 <span class="soon" data-ptds-ui="s678352e5cf6b">本机通道：Mac 通知 · 不可关闭</span></label>'
        : '<div data-ptds-ui="s2e7cbeef6a55">这组卡只算数值，不定等级。可以在有新结果时通知你。</div>' +
          '<label class="chk"><input type="checkbox" id="et-notify"' + (x.notify ? ' checked' : '') + '>有新结果时通知我 <span class="soon" data-ptds-ui="sb60771ab59d4">本机通道：Mac 通知</span></label>' +
          '<div class="sub2" data-ptds-ui="se4de7cd2a77b">不勾的话，新结果只在卡面上标“有新结果”。</div>') +
        '<div class="sub2" data-sem="SEM-25" data-ptds-ui="s7703599ae512">发给我自己走星簇预置授权 G-001（我自己 · 本机通道 · 摘要级），不出域。</div></section>';
    } else {
      var picked = rules.filter(function (r) { return x.rules && x.rules[r.rule]; });
      body = '<section class="confirm"><div class="kv2"><span data-ptds-ui="s62b95daecb7f">模板</span><span>' + esc(t.zh) + '</span><span data-ptds-ui="s33fa3162ff09">绑数据</span><span>' + (x.check ? x.check.computable + ' / ' + rules.length + ' 条规则现在能算' : '—') + '</span>' +
        '<span data-ptds-ui="s935514d4b5e9">定规则</span><span>' + picked.map(function (r) { return esc(r.name); }).join('、') + '</span><span data-ptds-ui="s713f764c8dae">配通知</span><span>' + (x.notify ? '状态通知 + Mac 通知' : '只在卡面标“有新结果”') + '</span><span data-ptds-ui="sbd2539694f18">出域</span><span data-sem="SEM-25" data-ptds-ui="s37e160e5d4e1">默认不出域，由星簇授权决定</span></div>' +
        '<div class="sub2" data-ptds-ui="s1c5dc48d6266">创建后马上按现有数据算一遍；以后数据一到自动重算，旧结果都保留。结果是计算，不是诊断。</div>' + (e.err ? '<div class="tip">' + ic('info') + ' ' + esc(e.err) + '</div>' : '') + '</section>';
      can = picked.length > 0;
    }
    var last = e.step === STEPS.length - 1;
    v.innerHTML = C.pgh('「增加我的状态」') + '<div class="wiz" data-cmp="S19" data-sem="SEM-31"><ol class="wsteps">' + STEPS.map(function (s, i) { return '<li' + (i === e.step ? ' aria-current="step"' : i < e.step ? ' class="done"' : '') + '>' + esc(s) + '</li>'; }).join('') + '</ol>' +
      '<section class="panel">' + body + '<div class="foot"><button class="ibtn" id="et-back" aria-label="上一步" title="上一步" data-ptds-ui-aria-label="sda336fdc0dbd" data-ptds-ui-title="sda336fdc0dbd">' + ic('chevron-left') + '</button><button class="btn" data-sem="SEM-14" id="' + (last ? 'et-create' : 'et-next') + '"' + (can ? '' : ' disabled') + '>' + (last ? '创建并计算' : '下一步') + '</button></div></section></div>';
    var g = function (k, fn) { var el = document.getElementById(k); if (el) el.onclick = LIVE.action(fn); };
    var redo = function () { e.err = null; LIVE.renderEngTpl(e); };
    var doCheck = async function () { try { x.check = (await call('GET', '/api/track/engines/check?key=' + encodeURIComponent(C.st.key) + '&tpl=' + t.id)); x.rules = null; } catch (err) { if(err&&(err.viewPending||err.code==='VIEW_CHANGED'))throw err; C.toast('没能检查：' + (err.detail || err.message)); } redo(); };
    g('et-check', doCheck);
    g('et-back', function () { if (e.step === 1) { e.step = 0; e.x = null; C.render(); return; } e.step--; redo(); });
    g('et-next', function () { e.step++; redo(); });
    document.querySelectorAll('[data-et-r]').forEach(function (b) { b.onchange = function () { x.rules[b.dataset.etR] = b.checked; redo(); }; });
    var nt = document.getElementById('et-notify'); if (nt) nt.onchange = function () { x.notify = nt.checked; };
    var pf = document.getElementById('et-prof');
    if (pf) pf.onsubmit = LIVE.action(async function (ev) {
      ev.preventDefault();
      try { var r = (await call('POST', '/api/profile', { key: C.st.key, birth_date: document.getElementById('et-bd').value, sex: document.getElementById('et-sex').value })); C.SNAPS[C.st.key] = r.snapshot; (await doCheck()); }
      catch (err) { if(err&&(err.viewPending||err.code==='VIEW_CHANGED'))throw err; C.toast({ BIRTH_DATE_INVALID: '出生日期不对', SEX_INVALID: '请选择性别' }[err.code] || '没能保存（' + (err.detail || err.code) + '）'); }
    });
    g('et-create', LIVE.action(async function () {
      try {
        var res = (await call('POST', '/api/track/engines', { key: C.st.key, tpl: t.id, rules: rules.filter(function (r) { return x.rules[r.rule]; }).map(function (r) { return r.rule; }), notify_self: !!x.notify }));
        C.SNAPS[C.st.key] = res.snapshot; C.st.eng = null; C.st.group = t.id; C.st.view = 'group';
        if ((await LIVE.restoreCreatedCard('grp:' + t.id))) C.toast('已创建“' + t.zh + '”，已按现有数据算好'); C.render(); window.scrollTo(0, 0);
      } catch (err) { if(err&&(err.viewPending||err.code==='VIEW_CHANGED'))throw err; e.err = err.detail || err.message; LIVE.renderEngTpl(e); }
    }));
  };
  /* 卡片组里的一张算法卡（非 MAS） */
  function ecardHtml(g, c) {
    var esc = C.esc, L = c.latest, ok = L && L.status === 'computed';
    var saved = L && L.saved_at ? C.tzTime(L.saved_at, true) : '未知';
    var savedDay = /^\d{4}-\d{2}-\d{2}/.test(saved) ? saved.slice(5, 10) : saved;
    return '<button class="wcard metric-card" data-ecard="' + esc(g.id + '|' + c.rule) + '"><span class="wn">' + esc(c.name) + ndot(c.new) + '<span class="grow"></span>' +
      (L ? '<span class="metric-time sub2" title="本次结果所用当期数据最近一次正式入库时间：' + esc(saved) + '"><span data-ptds-ui="s10d8d95351a8">录入时间</span><span>' + esc(savedDay) + '</span></span>' : '') + '</span>' +
      (L ? '<span class="metric-value"><span class="hv' + (ok ? '' : ' st-no') + '">' + esc(engVal(c, L)) + '</span>' + (ok ? cardChange(L) : '') + '</span>' +
        (ok ? '' : '<span class="sub2">' + esc(L.reason || '') + '</span>') + cardTrend(c)
        : '<span class="sub2" data-ptds-ui="s0be4940b2e6e">还没有可以算的时点</span>') + '</button>';
  }
  LIVE.engGroupHtml = function (g) {
    var esc = C.esc, ic = C.ic, P = E().profile || {}, needP = g.cards.some(function (c) { return /^(BIOAGE|ORGAN)\./.test(c.rule); });
    var acts = (g.id === 'BIOAGE' ? '<button class="btn2" id="g-lab">' + ic('flask-conical') + '推到状态实验室，并排对比</button>' : '') +
      (needP ? '<span class="sub2" data-ptds-inline><!--ptds-ui:s554edfa06951-->个人信息：<!--/ptds-ui-->' + (P.birth_date ? esc(P.birth_date) + ' · ' + esc(P.sex || '') : '还没填') + ' <button class="link" id="g-prof" data-ptds-ui="s37090f456516">修改</button></span>' : '');
    return '<div class="lede">' + esc(g.sub) + '</div>' + (acts ? '<div class="opts">' + acts + '</div>' : '') +
      '<div class="wall2">' + g.cards.map(function (c) { return ecardHtml(g, c); }).join('') + '</div>';
  };
  function markSeen(g) {
    if (!g || !g.new) return;
    try { callAsync('POST', '/api/track/engines', { key: C.st.key, tpl: g.id, action: 'seen' }).then(function () { g.new = false; g.cards.forEach(function (c) { c.new = false; }); }, function () { }); } catch (err) { if(err&&(err.viewPending||err.code==='VIEW_CHANGED'))throw err; /* 下次再记 */ }
  }
  LIVE.bindEngGroup = function (g) {
    var st = C.st;
    document.querySelectorAll('[data-ecard]').forEach(function (b) { b.onclick = function () { var p = b.dataset.ecard.split('|'); st.ecard = { g: p[0], r: p[1] }; st.view = 'ecard'; C.render(); window.scrollTo(0, 0); }; });
    var pr = document.getElementById('g-prof');
    if (pr) pr.onclick = function () { st.eng = { step: 1, tpl: 'ENG:' + g.id, sel: {} }; C.goTrack('eng'); };
    markSeen(g);
  };
  /* 算法卡页：最新结果、用到的数据、历次结果（全部保留，新的在前，旧的折叠） */
  LIVE.ecardCrumb = function () {
    var e = C.st.ecard || {}, g = grpOf(e.g), c = g && g.cards.filter(function (x) { return x.rule === e.r; })[0];
    return [{ t: '我的状态', go: function () { C.goTrack('wall'); } }, { t: g ? g.zh : '卡片组', go: function () { C.st.group = e.g; C.goTrack('group'); } }, { t: c ? c.name : '算法卡' }];
  };
  LIVE.renderECard = function () {
    engCss(); wall3Css();
    var esc = C.esc, ic = C.ic, st = C.st, e = st.ecard || {}, g = grpOf(e.g), v = document.getElementById('view');
    var c = g && g.cards.filter(function (x) { return x.rule === e.r; })[0];
    if (!c) { st.view = 'wall'; return LIVE.renderWall(); }
    var L = c.latest, label = {};
    (C.S().timeline || []).forEach(function (o) { label[o.ref] = humanLabel(o.label_zh); });
    /* 第一层：大数字 + 一句话 + 趋势；第二层（展开）：用到的数据、怎么算的；第三层：规则库弹层 */
    var h = '<section class="box ebox">' + (c.new ? '<div class="sub2">' + ndot(true) + ' 有新结果</div>' : '');
    if (!L) h += '<div class="sub2" data-ptds-ui="seca21ed66376">还没有可以算的时点。</div>';
    else {
      h += '<div class="hv" style="font-size:var(--scale-type-display, 2rem)">' + esc(engVal(c, L)) + '</div><div class="sub2">' + esc(L.tp) + (L.reason ? ' · ' + esc(L.reason) : '') + '</div>' + (chgLine(L) ? '<div class="sub2">' + esc(chgLine(L)) + '</div>' : '') + nolabels(spark(c.series)) +
        (c.series.length > 1 ? '<div class="sub2 ends"><span>' + esc(c.series[0].tp) + '</span><span>' + esc(c.series[c.series.length - 1].tp) + '</span></div>' : '');
      var U = L.used || [];
      if (U.length) {
        var tpU = U.filter(function (u) { return u.role === 'TP'; }), base = U.filter(function (u) { return u.role !== 'TP'; });
        var names = []; U.forEach(function (u) { var n = label[u.ref] || u.code; if (names.indexOf(n) < 0) names.push(n); });
        var days = U.map(function (u) { return u.day; }).filter(Boolean).sort(), n = L.used_count || U.length;
        var sum = '用了' + names.slice(0, 2).join('、') + (names.length > 2 ? ' 等' : '') + ' ' + n + ' 条' + (days.length ? '（' + (days[0] === days[days.length - 1] ? days[0] : days[0].slice(5) + ' 至 ' + days[days.length - 1].slice(5)) + '）' : '');
        h += '<details class="used"><summary>' + esc(sum) + '</summary><div class="bio-in">' + tpU.concat(base.slice(0, 6)).map(function (u) {
          return '<span><button class="link" data-ec-obs="' + esc(u.ref) + '">' + esc(label[u.ref] || u.code) + '</button></span><span>' + esc(human(u.code, u.value, u.unit)) + '</span><span class="sub2">' + esc(u.day || '') + (u.role === 'TP' ? '' : ' · 基线 / 之前') + '</span>';
        }).join('') + '</div>' + (n > tpU.length + Math.min(6, base.length) ? '<div class="sub2" data-ptds-inline><!--ptds-ui:sc2dca481cf38-->只列出前 <!--/ptds-ui-->' + (tpU.length + Math.min(6, base.length)) + ' 条，全部在证据图谱里</div>' : '') + '</details>';
      }
    }
    h += '<details class="how"><summary data-ptds-ui="sa2f7e1d4281b">怎么算的</summary><div class="sub2">' + esc(c.summary) + '</div></details>' +
      '<div class="sub2" data-ptds-inline><!--ptds-ui:s8124cd7ac28c-->依据：<!--/ptds-ui--><button class="link" id="ec-rule">' + esc(c.name) + ' · v' + esc(String(c.ref).split('@')[1] || '') + '</button>，点开看原文和完整定义' + (L && L.tp ? ' · <button class="link" id="ec-how">' + ic('waypoints') + '这个数怎么来的</button>' : '') + '</div>';
    if (g.id === 'BIOAGE') h += '<div class="opts"><button class="btn2" id="ec-lab">' + ic('flask-conical') + '推到状态实验室，并排对比</button>'  + '</div>';
    h += '</section><section class="box runs"><h3>' + ic('history') + '历次结果<span class="grow"></span><span class="sub2">' + c.runs.length + ' 次计算，全部保留</span></h3>' + c.runs.map(function (r) {
      var items = r.items.slice().reverse();
      return '<details><summary>' + esc(C.tzTime ? C.tzTime(r.at, true) : r.at) + ' · ' + esc(r.trigger_zh) + ' · ' + items.length + ' 个时点</summary>' +
        items.slice(0, 7).map(function (it) { return '<div class="it"><span>' + esc(it.tp) + '</span><span>' + esc(it.status === 'computed' ? engVal(c, it) : (it.status_zh || '') + (it.reason ? ' · ' + it.reason : '')) + '</span></div>'; }).join('') +
        (items.length > 7 ? '<div class="sub2" data-ptds-inline><!--ptds-ui:s268ec6902063-->另有 <!--/ptds-ui-->' + (items.length - 7) + ' 个更早的时点</div>' : '') + '<div class="sub2" data-ptds-inline><!--ptds-ui:s507e8d2a7131-->计算 #<!--/ptds-ui-->' + r.run_id + '</div></details>';
    }).join('') + '</section>';
    v.innerHTML = C.pgh(c.name) + h;
    var gg = function (k, fn) { var el = document.getElementById(k); if (el) el.onclick = LIVE.action(fn); };
    gg('ec-rule', function () { LIVE.openRule(c.rule); });
    gg('ec-how', function () { LIVE.graphCards = null; LIVE.openTrace('engine-' + c.rule, L.tp); }); /* R10：就地打开证据浮窗 */
    gg('ec-lab', function () { toLab(null, 'bio'); });
    gg('ec-sjia', function () { st.card = 'SJIA_FOCUS'; st.view = 'status'; C.render(); });
    document.querySelectorAll('[data-ec-obs]').forEach(function (b) { b.onclick = function () { C.openTorchDetail(b.dataset.ecObs, 'track'); }; });
    markSeen(g);
  };
  /* 状态规则库：一行一条规则（列表克制：名称、版本、规则集、原文、状态）；点开一行 = 二级弹出卡，看全部字段 */
  var RULES = null, RULES_KEY = null, RULES_REQUEST = null;
  function loadRulesAsync() {
    var key=C.st.key;
    if(RULES&&RULES_KEY===key)return Promise.resolve(RULES);
    if(RULES_REQUEST&&RULES_REQUEST.key===key&&RULES_REQUEST.epoch===readEpoch)return RULES_REQUEST.promise;
    var epoch=readEpoch,request={key:key,epoch:epoch};RULES_REQUEST=request;
    request.promise=readView('/api/rules?key='+encodeURIComponent(key)).then(function(data){
      if(C.st.key!==key||epoch!==readEpoch||RULES_REQUEST!==request)throw Error('READ_STALE');
      RULES=data;RULES_KEY=key;return data;
    }).finally(function(){if(RULES_REQUEST===request)RULES_REQUEST=null;});
    return request.promise;
  }
  function loadRules(force) { if (!RULES || RULES_KEY!==C.st.key || force) { try { RULES = readCached('/api/rules?key=' + encodeURIComponent(C.st.key)); RULES_KEY=C.st.key; } catch (err) { if(err&&(err.viewPending||err.code==='VIEW_CHANGED'))throw err; RULES = { sets: [], rules: [] }; } } return RULES; }
  /* 产品负责人 2026-10-14 07:42：凡是规则出自医学研究的状态卡，卡上加一个图标，一键跳到状态规则库里的这条规则（卡片组跳到这一组）。
     演示默认值、设备厂商文档、仅作对照的、本人自设的规则不算。 */
  function researchRule(r) { return !!(r && r.set !== 'CUSTOM' && r.status !== 'PLANNED' && r.source && r.source.url && !/^对照/.test(r.source.cite || '') && !/ouraring\.com/.test(r.source.url)); }
  LIVE.goRule = function (set, id) {
    var st = C.st; st.ruleSet = set || ''; C.goTrack('rules');
    if (id) setTimeout(function () { LIVE.openRule(id); }, 0);
  };
  LIVE.ruleIcons = function () { if(globalThis.PTDS_TRIAL_UI&&!PTDS_TRIAL_UI.can('rules'))return;
    if(!RULES||RULES_KEY!==C.st.key){
      loadRulesAsync().then(function(){if(C.st.app==='track'&&(C.st.view==='wall'||C.st.view==='group'))LIVE.ruleIcons();}).catch(function(){});return;
    }
    var R = RULES, by = {}, sets = {};
    R.rules.forEach(function (r) { by[r.id] = r; if (researchRule(r)) sets[r.set] = true; });
    var add = function (el, set, id, name) {
      var host = el.querySelector('.wn') || el; if (host.querySelector('.rl-ic')) return;
      /* 卡片本身是按钮，里面不再放可聚焦的控件：图标只给鼠标；键盘用户从卡片页的“依据”链接到同一条规则 */
      var a = document.createElement('span'); a.className = 'rl-ic'; a.setAttribute('aria-hidden', 'true');
      a.title = id ? '看这条状态规则：' + name : '看这组状态规则'; a.innerHTML = C.ic('scroll-text');
      a.onclick = function (ev) { ev.stopPropagation(); ev.preventDefault(); LIVE.goRule(set, id); };
      host.appendChild(a);
    };
    document.querySelectorAll('#view [data-ecard]').forEach(function (el) { var p = el.dataset.ecard.split('|'), r = by[p[1]]; if (researchRule(r)) add(el, r.set, r.id, r.name); });
    document.querySelectorAll('#view [data-group]').forEach(function (el) { if (sets[el.dataset.group]) add(el, el.dataset.group, null); });
    document.querySelectorAll('#view [data-brule]').forEach(function (el) { var r = by[el.dataset.brule]; if (r) add(el, r.set, null); });  /* 体验腕带卡：打开这一组规则 */
  };
  ['renderWall', 'renderGroup'].forEach(function (n) { var f0 = LIVE[n]; LIVE[n] = function () { var out = f0.apply(this, arguments); try { LIVE.ruleIcons(); } catch (err) { if(err&&(err.viewPending||err.code==='VIEW_CHANGED'))throw err; /* 图标只是捷径，失败不影响卡片 */ } return out; }; });
  /* 我的状态墙：图钉 / 齿轮 / 我的关注（产品负责人 2026-10-15 批准 r55）。钉了哪些、隐藏了哪些存在本实例（card_setting 只追加，/api/track/wall）。
     自己在「增加我的状态」建的分组卡、自建阈值卡可以删除（= 停用，结果和提醒都保留）；我的体征可删除其独立定义，数据保留；其他内置卡只能隐藏。
     隐藏的卡在「增加我的状态」页下面“已隐藏的卡”里，点一下恢复。「我的关注」不设上限，按钉的先后排。 */
  var PIN_IC = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 17v5"/><path d="M9 10.76a2 2 0 0 1-1.11 1.79l-1.78.9A2 2 0 0 0 5 15.24V16a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-.76a2 2 0 0 0-1.11-1.79l-1.78-.9A2 2 0 0 1 15 10.76V7a1 1 0 0 1 1-1 2 2 0 0 0 0-4H8a2 2 0 0 0 0 4 1 1 0 0 1 1 1z"/></svg>';
  var PIN_CSS = '.wcard{position:relative}.wcard .wpin,.wcard .wgear{position:absolute;width:26px;height:26px;border-radius:7px;display:flex;align-items:center;justify-content:center;color:var(--theme-text-tertiary);cursor:pointer;z-index:2}' +
    '.wcard.haspin{padding-bottom:42px}.wcard .wpin{top:10px;left:10px}.wcard .wgear{bottom:10px;right:10px}.wcard .wpin:hover,.wcard .wgear:hover{color:var(--theme-text-primary);background:color-mix(in srgb,var(--theme-text-primary) 8%,transparent)}' +
    '.wcard .wpin.on{color:var(--theme-text-primary);background:color-mix(in srgb,var(--theme-text-primary) 10%,transparent)}.wcard.haspin .wn{padding-left:22px}' +
    '.wmenu{position:absolute;z-index:2100;width:230px;padding:6px;border-radius:10px;background:var(--theme-surface-raised);color:var(--theme-text-primary);border:var(--primitive-border-hairline) solid var(--theme-line-control);box-shadow:0 10px 28px rgba(0,0,0,.25);font-size:var(--scale-type-meta)}' +
    '.wmenu button{display:block;width:100%;text-align:left;padding:8px 10px;border:0;background:none;color:inherit;font:inherit;border-radius:6px;cursor:pointer}.wmenu button:hover{background:color-mix(in srgb,var(--theme-text-primary) 8%,transparent)}' +
    '.wmenu .dg{color:#E5675F}.wmenu .sub2{padding:4px 10px 6px}.wall2 .wcard.grp{margin:0}';
  function wallId(el) {
    if (el.dataset.vitalsWall) return el.dataset.vitalsWall;
    if (el.dataset.group) return 'grp:' + el.dataset.group;
    if (el.dataset.ccard) return 'cc:' + el.dataset.ccard;
    if (el.dataset.brule) return 'band:' + el.dataset.brule;
    if (el.dataset.card === 'VITALS' && el.dataset.vitalsFamily) return 'card:VITALS:' + el.dataset.vitalsFamily;
    if (el.dataset.card) return 'card:' + el.dataset.card;
    if (el.dataset.sleep != null || /^睡眠/.test((el.querySelector('.wn') || el).innerText || '')) return 'sleep';
    return null;
  }
  function wallKind(id) { return /^grp:/.test(id) && ['grp:MAS', 'grp:BIOAGE'].indexOf(id) < 0 || /^cc:/.test(id) ? 'own' : 'builtin'; }
  /* CARD_ASYNC_R05: one explicit card write at a time; never retry an uncertain write. */
  LIVE.cardMutation = async function (path, body) {
    if (LIVE._cardWriting) { var busy=new Error('CARD_BUSY');busy.detail='正在保存卡片，请等待完成后再操作';throw busy; }
    var key=body.key,instance=(C.SNAPS[key]||{}).instance,job={key:key};
    LIVE._cardWriting=job;
    try {
      var r=await callAsync('POST',path,body);
      if(!r.snapshot||!r.snapshot.instance||!instance||r.snapshot.instance.instance_id!==instance.instance_id)throw Error('CARD_CONFIRMATION_MISSING');
      if(r.snapshot._scope==='home') LIVE.acceptHome(key,C.SNAPS[key],r.snapshot);
      else C.SNAPS[key]=r.snapshot; // Keep complete history when accepting a lightweight card update.
      return r;
    } catch(err) { if(err&&(err.viewPending||err.code==='VIEW_CHANGED'))throw err;
      if(!err.detail)err.detail='未收到保存确认，请刷新核对后再操作；不会自动重复提交';
      throw err;
    } finally { if(LIVE._cardWriting===job)LIVE._cardWriting=null; }
  };
  LIVE.paintCardSaved = function (key) {
    // A fast save may finish inside the click-protection window. Paint once
    // after it, still respecting any new dialog, input, pointer or base change.
    setTimeout(function(){if(C.st.key===key)LIVE.paintFreshState();},
      Math.max(0,(LIVE._interactionUntil||0)-Date.now())+16);
  };
  LIVE.wallSet = async function (card, patch, name) {
    var key=C.st.key,route=LIVE.refreshRoute();
    if(LIVE._cardWriting){C.toast('正在保存卡片，请等待完成后再操作');return false;}
    C.toast('正在保存卡片…');
    try { await LIVE.cardMutation('/api/track/wall',Object.assign({key:key,card:card,name:name||''},patch)); }
    catch(err){ if(err&&(err.viewPending||err.code==='VIEW_CHANGED'))throw err;if(C.st.key===key)C.toast(err.detail||LIVE.saveErr(err));return false;}
    if(C.st.key!==key)return true;
    if(route===LIVE.refreshRoute()&&!document.querySelector('[role="dialog"]')&&!LIVE.editing()){
      if(patch.hide===false){C.st.eng=null;C.st.view='wall';C.st.stateSection='cards';C.render();}
      else C.renderMainOnly();
    }
    C.toast(patch.hide===false?'已恢复到我的状态':patch.hide?'卡片已隐藏':patch.pin?'已加入我的关注':'已移出我的关注');
    return true;
  };
  // Creating an existing card must also restore its independent wall preference.
  LIVE.restoreCreatedCard = async function (card,key) {
    key=key||C.st.key;
    var route=LIVE.refreshRoute();
    var visible=LIVE.snapshotFor(key,C.SNAPS[key]);
    if (!((visible.wall_prefs || {}).hidden || []).some(function (h) { return h.card === card; })) return true;
    try {
      await LIVE.cardMutation('/api/track/wall', {key:key,card:card,hide:false});
      if(C.st.key!==key||route!==LIVE.refreshRoute()){
        var stale=new Error('VIEW_CHANGED');stale.code='VIEW_CHANGED';throw stale;
      }
      return true;
    } catch (err) { if(err&&(err.viewPending||err.code==='VIEW_CHANGED'))throw err;
      C.toast('卡片已保存，但恢复显示失败。请在“增加我的状态”的“已隐藏的卡”中重试：' + LIVE.saveErr(err));
      return false;
    }
  };
  // Weekly focus uses only the approved pinned groups; wearable sections are excluded.
  LIVE.weeklySignature = function () {
    var s=C.S(),p=s.wall_prefs||{},allowed=['grp:MAS','grp:BLOOD','grp:COAG','grp:LIVER'];
    return C.st.key+'|'+JSON.stringify((p.pins||[]).filter(function(id){return allowed.indexOf(id)>=0 && !(p.hidden||[]).some(function(h){return h.card===id;});}));
  };
  LIVE.weeklyHtml = function (r) {
    var esc=C.esc,number=function(t){return esc(t).replace(/\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[-+]\d{2}:\d{2}))?|HLH-2004|2016|[-+]?\d+(?:\.\d+)?%?/g,function(n){if(/^\d{4}-\d{2}-\d{2}/.test(n))return n.replace('T',' ').replace(/(?:Z|[-+]\d{2}:\d{2})$/,'');return n==='HLH-2004'||n==='2016'?n:'<strong>'+n+'</strong>';});};
    if(r.state!=='ok') return '<p role="status">'+esc(r.why||(r.state==='no_llm'?'本地星灵尚未就绪，本次未生成解读。':r.state==='empty'?'我的关注中暂无可汇总的卡片。':'本次解读未通过核对，请重试。'))+'</p>';
    return '<p class="sub2">'+esc(r.period.label.replace('T',' ').replace(/(?:Z|[-+]\d{2}:\d{2})$/,''))+' · '+esc(r.period.tz)+'</p><p class="sub2">'+esc(r.by)+' · '+esc(r.method)+'</p>'+r.cards.map(function(card){
      return '<section class="weekly-card"><h3>'+esc(card.name)+'</h3><p>'+number(card.text)+'</p>'+(card.records.length?'<details><summary data-ptds-inline><!--ptds-ui:sdb8db0530432-->查看 <!--/ptds-ui-->'+card.records.length+' 条依据</summary>'+card.records.map(function(o){
        return '<p class="weekly-record">'+esc(o.label)+' · '+esc(o.at)+'<br>'+number((o.comparator||'')+(o.value==null?'未记录':o.value))+' '+esc(o.unit||'')+(o.kind==='state'?' <span class="sub2" data-ptds-inline><!--ptds-ui:s779337b160ff-->计算记录 <!--/ptds-ui-->'+esc(o.run_id==null?'未标记':o.run_id)+'</span> <button class="link" data-weekly-state="'+esc(o.rule||'')+'" data-weekly-date="'+esc(o.at)+'" data-weekly-run="'+esc(o.run_id==null?'':o.run_id)+'">查看该日计算依据</button>':o.ref?' <button class="link" data-weekly-ref="'+esc(o.ref)+'">查看来源</button>':'')+'</p>';
      }).join('')+'</details>':'')+'</section>';
    }).join('');
  };
  LIVE.weeklyOpen = function () {
    C.closeDrawer();C.st.drawer='live';
    if(!document.getElementById('weekly-css')){var style=document.createElement('style');style.id='weekly-css';style.textContent=LIVE.BL_CSS+'.weekly-card{padding:10px 0;border-bottom:1px solid var(--theme-line-hairline)}.weekly-drawer .weekly-card h3{margin:4px 0;color:var(--theme-text-primary);font-size:16px;font-weight:600}.weekly-card p{overflow-wrap:anywhere}.weekly-record{font-size:var(--scale-type-meta)}.weekly-drawer{max-width:100vw}';document.head.appendChild(style);}
    var el=document.createElement('aside');el.id='drawer';el.className='drawer bl-summary-drawer weekly-drawer';el.setAttribute('role','dialog');el.setAttribute('aria-modal','false');el.setAttribute('aria-label','星灵 · 近一周关注');
    el.innerHTML='<div class="dh"><span>'+C.ic('sparkles')+' 星灵 · 近一周关注</span><button class="ibtn" data-weekly-refresh aria-label="重新解读" data-ptds-ui-aria-label="s98b10d652f4e">'+C.ic('refresh-cw')+'</button><button class="ibtn" data-weekly-close aria-label="关闭星灵" data-ptds-ui-aria-label="s6de3fe3488e4">'+C.ic('x')+'</button></div><div class="db" data-weekly-body aria-live="polite"></div>';
    document.body.appendChild(el);
    var body=el.querySelector('[data-weekly-body]'),button=el.querySelector('[data-weekly-refresh]'),controller=null,busy=false,closed=false;
    function current(){return !closed&&el.isConnected;}
    function close(){closed=true;if(controller)controller.abort();el.remove();C.st.drawer=null;var b=document.getElementById('weekly-focus-go');if(b)b.focus();}
    async function ask(){
      if(!current()||busy)return;
      if(LIVE._weeklyBusy){body.innerHTML='<p role="status" data-ptds-ui="s41f43cd2db04">星灵正在完成上一项请求，请稍后重新解读。</p>';return;}
      var key=C.st.key,signature=LIVE.weeklySignature();busy=true;LIVE._weeklyBusy=true;button.disabled=true;body.setAttribute('aria-busy','true');
      body.innerHTML='<div class="bl-thinking"><span class="sp-ic on">'+C.ic('sparkles')+'</span>星灵正在整理近一周关注…</div><p class="sub2" data-ptds-ui="secb4dcb5604b">仅包含我的关注中的 MAS 预警、血液细胞、凝血、肝脏。</p>';
      controller=new AbortController();var timeout=setTimeout(function(){controller.abort();},180000);
      try{
        var response=await fetch('/api/starling/weekly-focus',{method:'POST',headers:{'Content-Type':'application/json','X-PTDS':'1'},body:JSON.stringify({key:key}),signal:controller.signal,cache:'no-store'}),r=await response.json();
        if(!current())return;
        if(signature!==LIVE.weeklySignature()){body.innerHTML='<p role="status" data-ptds-ui="s8bf312647a8a">当前实例或关注已变化，请重新解读。</p>';return;}
        body.innerHTML=LIVE.weeklyHtml(r);
        body.querySelectorAll('[data-weekly-ref]').forEach(function(b){b.onclick=function(){if(signature!==LIVE.weeklySignature()){body.innerHTML='<p role="status" data-ptds-ui="s8bf312647a8a">当前实例或关注已变化，请重新解读。</p>';return;}close();C.openTorchDetail(b.dataset.weeklyRef,'data');};});
        body.querySelectorAll('[data-weekly-state]').forEach(function(b){b.onclick=LIVE.action(async function(){if(signature!==LIVE.weeklySignature()){body.innerHTML='<p role="status">当前实例或关注已变化，请重新解读。</p>';return;}try{var trace=(await call('GET','/api/graph/trace?key='+encodeURIComponent(key)+'&card=sjia-mas&tp='+encodeURIComponent(b.dataset.weeklyDate)));if(!trace.found||String((trace.run||{}).run_id)!==b.dataset.weeklyRun){C.toast('该日期的计算记录已变化，请重新解读后查看依据。');return;}close();LIVE.graphCards=null;LIVE.openTrace('sjia-mas',b.dataset.weeklyDate);}catch(e){ if(e&&(e.viewPending||e.code==='VIEW_CHANGED'))throw e;C.toast('暂时无法读取该日期的计算依据，请稍后重试。');}});});
      }catch(e){ if(e&&(e.viewPending||e.code==='VIEW_CHANGED'))throw e;if(current())body.innerHTML='<p role="status" data-ptds-ui="s1b7dbd71c46c">本次解读未完成，请检查本地星灵后重试。</p>';}
      finally{clearTimeout(timeout);busy=false;LIVE._weeklyBusy=false;if(current()){button.disabled=false;body.setAttribute('aria-busy','false');}}
    }
    button.onclick=LIVE.action(ask);el.querySelector('[data-weekly-close]').onclick=LIVE.action(close);
    el.addEventListener('keydown',function(e){if(e.key==='Escape'){e.preventDefault();close();}});
    el.querySelector('[data-weekly-close]').focus();ask();
  };
  LIVE.wallPrefs = function () {
    if (C.isReplay()) return;
    if (!document.getElementById('pin-css')) { var s0 = document.createElement('style'); s0.id = 'pin-css'; s0.textContent = PIN_CSS; document.head.appendChild(s0); }
    var esc = C.esc, ic = C.ic, P = C.S().wall_prefs || { pins: [], hidden: [] }, hid = {}, v = document.getElementById('view');
    P.hidden.forEach(function (h) { hid[h.card] = 1; });
    var cards = [].slice.call(v.querySelectorAll('.wcard')).filter(function (c) { return c.id !== 'w-new' && wallId(c); });
    cards.forEach(function(c){if(c.dataset.vitalsCard)return;var d=(P.display||{})[wallId(c)],title=c.querySelector('.wn');if(d&&title){var node=Array.prototype.find.call(title.childNodes,function(n){return n.nodeType===3;});if(node)node.nodeValue=d.name;else title.insertBefore(document.createTextNode(d.name),title.firstChild);}});
    cards.forEach(function (c) { if (hid[wallId(c)]) c.remove(); });
    cards = cards.filter(function (c) { return !hid[wallId(c)]; });
    LIVE.thresholdCards = cards.map(function (c) { return {card:wallId(c),name:((c.querySelector('.wn') || c).innerText || '').split('\n')[0].trim()}; });
    var byId = {}; cards.forEach(function (c) { byId[wallId(c)] = c; });
    var first = v.querySelector('.wsec') || v.querySelector('.wall2'); if (!first) return;
    var sec = document.createElement('div'); sec.id = 'w-pins';
    var pinned = P.pins.filter(function (id) { return byId[id]; });
    sec.innerHTML = '<div style="margin-bottom:4px"><button type="button" class="ibtn" id="weekly-focus-go" aria-label="星灵解读近一周关注" title="星灵 · 近一周关注" data-ptds-ui-aria-label="s7f4f403264e7" data-ptds-ui-title="se8be54d027aa">'+ic('sparkles')+'</button></div><div class="wsec" style="display:flex;align-items:center;gap:6px">' + PIN_IC + ' 我的关注</div>' +
      (pinned.length ? '<div class="wall2 wallu"></div>' : '<div class="sub2" style="margin:0 0 8px" data-ptds-ui="sb22ebb44a0d4">还没有钉住的卡片。点任意一张卡左上角的图钉，它就会放到这里；再点一次放回原来那一栏。</div>');
    first.parentNode.insertBefore(sec, first);
    sec.querySelector('#weekly-focus-go').onclick=LIVE.weeklyOpen;
    if (!v.querySelector('.wsec:not(#w-pins .wsec)')) { var lab = document.createElement('div'); lab.className = 'wsec'; lab.textContent = '全部'; first.parentNode.insertBefore(lab, first); }
    pinned.forEach(function (id) { sec.querySelector('.wall2').appendChild(byId[id]); });
    [].slice.call(v.querySelectorAll('.wall2')).forEach(function (w) { if (!w.closest('#w-pins') && !w.querySelector('.wcard')) { var h = w.previousElementSibling; if (h && h.classList.contains('wsec')) h.remove(); w.remove(); } });
    cards.forEach(function (c) {
      var id = wallId(c), on = pinned.indexOf(id) >= 0, name = ((c.querySelector('.wn') || c).innerText || '').split('\n')[0].trim();
      c.classList.add('haspin');
      var pn = document.createElement('span'); pn.className = 'wpin' + (on ? ' on' : ''); pn.setAttribute('role', 'button'); pn.title = on ? '从我的关注移出' : '钉到我的关注'; pn.setAttribute('aria-label', pn.title); pn.innerHTML = PIN_IC;
      pn.onclick = function (e) { e.stopPropagation(); e.preventDefault(); LIVE.wallSet(id, { pin: !on }, name); };
      var gr = document.createElement('span'); gr.className = 'wgear'; gr.setAttribute('role', 'button'); gr.title = '这张卡的设置'; gr.setAttribute('aria-label', '这张卡的设置'); gr.innerHTML = ic('settings');
      gr.onclick = function (e) { e.stopPropagation(); e.preventDefault(); LIVE.wallMenu(gr, id, name, on); };
      c.appendChild(pn); c.appendChild(gr);
    });
  };
  LIVE.thresholdOpen = async function (card, name, code, cached) {
    LIVE.bellClose();
    var old = document.getElementById('threshold-dr'); if (old) old.remove();
    var instanceKey = C.st.key;
    var loading=document.createElement('aside');loading.id='threshold-dr';loading.setAttribute('role','dialog');loading.setAttribute('aria-modal','false');loading.setAttribute('aria-label','阈值与通知');
    loading.style.cssText='position:fixed;right:0;top:0;bottom:0;width:min(480px,100vw);box-sizing:border-box;z-index:2400;overflow:auto;background:var(--theme-surface-raised);color:var(--theme-text-primary);border-left:1px solid var(--theme-line-control);padding:24px;box-shadow:-8px 0 24px #0002';
    loading.innerHTML='<div style="display:flex;justify-content:space-between;align-items:center"><h3 data-ptds-ui="s67f1b373520b">阈值与通知</h3><button class="ibtn" data-th-loading-close aria-label="关闭阈值设置" data-ptds-ui-aria-label="s6ba4eaae86a4">'+C.ic('x')+'</button></div><div data-th-read>'+LIVE.readingHtml('compact')+'</div>';
    document.body.appendChild(loading);loading.querySelector('[data-th-loading-close]').onclick=function(){loading.remove();};
    loading.addEventListener('keydown',function(e){if(e.key==='Escape')loading.remove();});
    if(cached&&cached.key!==instanceKey){loading.remove();C.toast('数据基座已切换，请重新打开阈值设置');return;}
    var data=cached&&cached.data;
    try { if(!data)data=await readView('/api/track/thresholds?key='+encodeURIComponent(instanceKey)); }
    catch(err){ if(err&&(err.viewPending||err.code==='VIEW_CHANGED'))throw err;
      if(loading.isConnected&&C.st.key===instanceKey){loading.querySelector('[data-th-read]').innerHTML=LIVE.readingHtml('compact',err.name==='AbortError'?'timeout':'error','暂未读到阈值设置。')+'<button class="link" data-th-retry data-ptds-ui="sb8784c8dd563">重试</button>';loading.querySelector('[data-th-retry]').onclick=function(){LIVE.thresholdOpen(card,name,code);};}
      else loading.remove();
      return;
    }
    if(C.st.key!==instanceKey||!loading.isConnected){loading.remove();return;}
    loading.remove();
    var esc = C.esc, all = Object.values(data.configs || {}), choices = (LIVE.thresholdCards || []).slice();
    all.forEach(function (d) { if (!choices.some(function (x) { return x.card === d.card; })) choices.push({card:d.card,name:d.name}); });
    card = card || (choices[0] || {}).card;
    if (!card) { C.toast('请先在状态卡片中选择一张卡设置阈值'); return; }
    name = name || ((choices.filter(function (x) { return x.card === card; })[0] || {}).name) || card;
    var avail = (data.available || []).slice(), prior = all.filter(function (d) { return d.card === card; });
    prior.forEach(function (d) { if (!avail.some(function (x) { return x.code === d.code; })) avail.push({code:d.code,label_zh:d.label,unit:d.unit}); });
    code = code || (prior[0] || {}).code || (avail[0] || {}).code;
    var item = avail.filter(function (x) { return x.code === code; })[0] || {}, d = prior.filter(function (x) { return x.code === code; })[0] || {};
    var el = document.createElement('aside'); el.id = 'threshold-dr'; el.setAttribute('role','dialog'); el.setAttribute('aria-modal','false'); el.setAttribute('aria-label','阈值与通知');
    el.style.cssText = 'position:fixed;right:0;top:0;bottom:0;width:min(480px,100vw);box-sizing:border-box;z-index:2400;overflow:auto;background:var(--theme-surface-raised);color:var(--theme-text-primary);border-left:1px solid var(--theme-line-control);padding:24px;box-shadow:-8px 0 24px #0002';
    el.innerHTML = '<div style="display:flex;justify-content:space-between;align-items:center"><h3 data-ptds-ui="s67f1b373520b">阈值与通知</h3><button class="ibtn" id="th-close" aria-label="关闭阈值设置" data-ptds-ui-aria-label="s6ba4eaae86a4">' + C.ic('x') + '</button></div>' +
      '<label class="cc-field" data-ptds-inline><!--ptds-ui:sf809c22a7f16-->状态卡片<!--/ptds-ui--><select id="th-card">' + choices.map(function (x) { return '<option value="' + esc(x.card) + '"' + (x.card === card ? ' selected' : '') + '>' + esc(x.name) + '</option>'; }).join('') + '</select></label>' +
      '<label class="cc-field" data-ptds-inline><!--ptds-ui:s802545e49773-->关注指标<!--/ptds-ui--><select id="th-code">' + avail.map(function (x) { return '<option value="' + esc(x.code) + '"' + (x.code === code ? ' selected' : '') + '>' + esc(x.label_zh) + ' · ' + esc(x.unit_zh || x.unit || '') + '</option>'; }).join('') + '</select></label>' +
      '<p class="sub2" data-ptds-ui="s2368d38b980b">为这张卡选择要关注的数值指标。上下限可只填一侧；两侧留空即关闭该指标阈值。</p>' +
      '<label class="cc-field" data-ptds-inline><!--ptds-ui:sbfdf58a087cc-->下限（<!--/ptds-ui-->' + esc(item.unit_zh || item.unit || '') + '）<input id="th-lower" type="text" inputmode="decimal" value="' + esc(d.lower == null ? '' : d.lower) + '" placeholder="不设下限"></label>' +
      '<label class="cc-field" data-ptds-inline><!--ptds-ui:s18fe382e5951-->上限（<!--/ptds-ui-->' + esc(item.unit_zh || item.unit || '') + '）<input id="th-upper" type="text" inputmode="decimal" value="' + esc(d.upper == null ? '' : d.upper) + '" placeholder="不设上限"></label>' +
      '<h4 data-ptds-ui="sfcb1a0f2ac08">通知条件</h4><label class="chk"><input id="th-nlower" type="checkbox"' + (d.notify_lower ? ' checked' : '') + '>低于下限时通知</label>' +
      '<label class="chk"><input id="th-nupper" type="checkbox"' + (d.notify_upper ? ' checked' : '') + '>高于上限时通知</label>' +
      '<label class="chk"><input id="th-mac" type="checkbox"' + (d.mac ? ' checked' : '') + (!data.mac_available ? ' disabled' : '') + '>同时发送 Mac 通知' + (!data.mac_available ? '（本机通道未启用）' : '') + '</label>' +
      '<p class="sub2" data-ptds-ui="s74473493f41e">通知默认记在铃铛内。保存后从新读数开始判断；等于阈值不触发，持续越界不重复提醒，回到范围内后再越界会重新提醒。只比较最新记录，补录更早的数据不触发。</p>' +
      '<p class="sub2" data-ptds-ui="s946a29f153e3">这是你自己的关注阈值，不改变原规则库的判定。</p><p id="th-error" role="alert"></p><button class="btn" id="th-save"' + (!code ? ' disabled' : '') + '>保存阈值与通知</button>';
    document.body.appendChild(el);
    el.querySelectorAll('.cc-field').forEach(function (x) { x.style.cssText='display:grid;gap:8px;margin:16px 0'; });
    el.querySelectorAll('select,input[type=text]').forEach(function (x) { x.style.cssText='width:100%;box-sizing:border-box;min-height:42px;padding:9px 12px;border:1px solid var(--theme-line-control);border-radius:8px;background:var(--theme-surface-raised);color:var(--theme-text-primary);font:inherit'; });
    document.getElementById('th-close').onclick = function () { el.remove(); };
    document.getElementById('th-card').onchange = function () { LIVE.thresholdOpen(this.value,undefined,undefined,{key:instanceKey,data:data}); };
    document.getElementById('th-code').onchange = function () { LIVE.thresholdOpen(card,name,this.value,{key:instanceKey,data:data}); };
    var saving=false;
    el.addEventListener('keydown',function(e){if(e.key==='Escape'&&!saving)el.remove();});
    document.getElementById('th-save').onclick = LIVE.action(async function () {
      if(saving)return;
      if (C.st.key !== instanceKey) { el.remove(); C.toast('数据基座已切换，请重新打开阈值设置'); return; }
      var payload = {key:instanceKey,card:card,name:name,code:code,lower:document.getElementById('th-lower').value.trim(),upper:document.getElementById('th-upper').value.trim(),notify_lower:document.getElementById('th-nlower').checked,notify_upper:document.getElementById('th-nupper').checked,mac:document.getElementById('th-mac').checked};
      saving=true;el.querySelector('#th-error').textContent='正在保存…';el.querySelectorAll('button,input,select').forEach(function(x){x.disabled=true;});
      try { await LIVE.cardMutation('/api/track/thresholds',payload);el.remove();if(C.st.key===instanceKey){LIVE.paintCardSaved(instanceKey);C.toast('阈值与通知已保存，从新读数开始判断');} }
      catch(err) { if(err&&(err.viewPending||err.code==='VIEW_CHANGED'))throw err; if(el.isConnected)el.querySelector('#th-error').textContent=err.detail||LIVE.saveErr(err); }
      finally {saving=false;if(el.isConnected)el.querySelectorAll('button,input,select').forEach(function(x){x.disabled=false;});if(el.isConnected&&!data.mac_available)el.querySelector('#th-mac').disabled=true;}
    });
  };
  /* CARD_EDITOR_R01: persisted presentation, separate from rules and observations. */
  LIVE.wallPick = function(id,items,key){
    var pref=((C.S().wall_prefs||{}).display||{})[id];
    if(!pref||!Array.isArray(pref.items))return items;
    return pref.items.map(function(k){return items.find(function(x){return key(x)===k;});}).filter(Boolean);
  };
  LIVE.wallOptions = function(id){
    var s=C.S(),b=s.band_cards||{},opts=[],g;
    if(id.indexOf('card:VITALS:')===0)opts=((s.vitals||{}).items||[]).filter(function(x){return x.family===id.slice(12);}).sort(function(a,b){return rank(a.code)-rank(b.code);}).map(function(x){return {id:x.code,label:x.label_zh||x.code};});
    else if(id.indexOf('grp:')===0){g=((s.engines||{}).groups||[]).find(function(x){return x.id===id.slice(4);});if(g)opts=g.cards.map(function(x){return {id:x.rule,label:SHORT_RULE[x.rule]||x.name};});}
    else if(id==='band:LIVE.SOMALOOP-SPOT')opts=(b.spot||[]).map(function(x){return {id:x.label,label:x.label};});
    else if(id==='band:SLEEP.A03-HRV-DEV-SOMALOOP')opts=(b.night||[]).map(function(x){return {id:x.label,label:x.label};});
    else if(id==='sleep')opts=((s.sleep||{}).metrics||[]).map(function(x){return {id:x.code,label:x.label_zh||x.code};});
    else opts=[{id:'summary',label:id==='band:LIVE.SPO2-LOW'?'低血氧记录次数 / 总记录次数':'状态结果'}];
    return opts.filter(function(x,i,a){return a.findIndex(function(y){return y.id===x.id;})===i;});
  };
  LIVE.wallEdit = function(id,name){
    var vc=LIVE.vitalsDefinition(id);if(vc)return LIVE.renderVitalsEditor({card:vc});
    var old=document.getElementById('card-edit-dr');if(old)old.remove();
    var key=C.st.key,esc=C.esc,pref=((C.S().wall_prefs||{}).display||{})[id],options=LIVE.wallOptions(id);
    var selected=pref?pref.items.slice():options.map(function(x){return x.id;});
    selected.forEach(function(k){if(!options.some(function(x){return x.id===k;}))options.push({id:k,label:k+'（暂不可用）'});});
    var order=selected.concat(options.map(function(x){return x.id;}).filter(function(k){return selected.indexOf(k)<0;}));
    var el=document.createElement('aside');el.id='card-edit-dr';el.className='drawer';el.setAttribute('role','dialog');el.setAttribute('aria-modal','false');el.setAttribute('aria-label','编辑状态卡片');
    el.style.cssText='position:fixed;right:0;top:0;bottom:0;width:min(480px,100vw);max-width:100vw;z-index:2400;background:var(--theme-surface-raised);color:var(--theme-text-primary);border-left:1px solid var(--theme-line-control);box-shadow:-8px 0 24px #0002;overflow:auto';
    el.innerHTML='<div class="dh"><strong data-ptds-ui="s03fb8903dd5a">编辑状态卡片</strong><button class="ibtn" data-ce-close aria-label="关闭卡片编辑" data-ptds-ui-aria-label="sef475c90fb10">'+C.ic('x')+'</button></div><div class="db"><label style="display:grid;gap:8px" data-ptds-inline><!--ptds-ui:sa41ec76ecac2-->卡片名称<!--/ptds-ui--><input id="ce-name" maxlength="40" value="'+esc(pref?pref.name:name)+'" style="width:100%;box-sizing:border-box;padding:10px;color:inherit;background:var(--theme-surface-raised);border:1px solid var(--theme-line-control);border-radius:8px;font:inherit"></label><h4 data-ptds-ui="s596bf9b85d5a">展示项与顺序</h4><p class="sub2" data-ptds-inline><!--ptds-ui:s43e50fcb5ee0-->勾选要显示的项目，使用上下移调整顺序。至少保留一项。<!--/ptds-ui-->'+(id.indexOf('card:VITALS:')===0?'前两项显示在卡面，其余通过详情查看。':id.indexOf('grp:')===0?'第一项作为卡面主要结果，其余依次显示。':'')+'</p><div id="ce-items"></div><p class="sub2" data-ptds-ui="s4512375c4fcc">仅调整这张卡的展示，不修改原始数据、设备来源或计算规则。阈值与通知仍单独设置。</p><p id="ce-error" role="alert"></p><div style="display:flex;gap:8px;flex-wrap:wrap"><button class="btn" id="ce-save" data-ptds-ui="s991bb7cfe5a8">保存修改</button><button class="btn2" data-ce-close data-ptds-ui="s2cd0f3be8738">取消</button><button class="btn2" id="ce-reset" data-ptds-ui="s58d0a6b11c9b">恢复默认展示</button></div></div>';
    document.body.appendChild(el);var busy=false;
    function close(){if(busy)return;el.remove();}
    function rows(focus){
      el.querySelector('#ce-items').innerHTML=order.map(function(k,i){var o=options.find(function(x){return x.id===k;});return '<div style="display:flex;align-items:center;gap:8px;padding:8px 0;border-bottom:1px solid var(--theme-line-hairline)"><label style="display:flex;align-items:center;gap:8px;flex:1;min-width:0"><input type="checkbox" data-ce-item="'+esc(k)+'"'+(selected.indexOf(k)>=0?' checked':'')+'><span>'+esc(o.label)+'</span></label><button class="ibtn" data-ce-up="'+esc(k)+'" aria-label="上移'+esc(o.label)+'"'+(i===0?' disabled':'')+'>↑</button><button class="ibtn" data-ce-down="'+esc(k)+'" aria-label="下移'+esc(o.label)+'"'+(i===order.length-1?' disabled':'')+'>↓</button></div>';}).join('');
      el.querySelectorAll('[data-ce-item]').forEach(function(x){x.onchange=function(){selected=order.filter(function(k){return k===x.dataset.ceItem?x.checked:selected.indexOf(k)>=0;});};});
      ['up','down'].forEach(function(d){el.querySelectorAll('[data-ce-'+d+']').forEach(function(x){x.onclick=function(){var k=x.getAttribute('data-ce-'+d),i=order.indexOf(k),j=i+(d==='up'?-1:1);if(j<0||j>=order.length)return;order.splice(i,1);order.splice(j,0,k);rows({d:d,k:k});};});});
      if(focus){var target=Array.prototype.find.call(el.querySelectorAll('[data-ce-'+focus.d+']'),function(x){return x.getAttribute('data-ce-'+focus.d)===focus.k;});if(target&&!target.disabled)target.focus();}
    }
    async function save(reset){
      if(busy)return;if(C.st.key!==key){close();C.toast('数据基座已切换，请重新打开卡片编辑');return;}
      var value={name:el.querySelector('#ce-name').value.trim(),items:order.filter(function(k){return selected.indexOf(k)>=0;})},error=el.querySelector('#ce-error');
      if(!reset&&(!value.name||!value.items.length)){error.textContent='请填写卡片名称，并至少选择一个展示项';return;}
      busy=true;error.textContent='正在保存…';el.querySelectorAll('button,input').forEach(function(x){x.disabled=true;});
      try{await LIVE.cardMutation('/api/track/wall',{key:key,card:id,display:reset?null:value});el.remove();if(C.st.key===key){LIVE.paintCardSaved(key);C.toast(reset?'已恢复默认展示':'卡片已更新');}}
      catch(e){ if(e&&(e.viewPending||e.code==='VIEW_CHANGED'))throw e;error.textContent=e.detail||'保存未完成，请重试；本次输入已保留';}
      finally{busy=false;if(el.isConnected){el.querySelectorAll('button,input').forEach(function(x){x.disabled=false;});rows();}}
    }
    rows();el.querySelectorAll('[data-ce-close]').forEach(function(x){x.onclick=LIVE.action(close);});el.querySelector('#ce-save').onclick=function(){save(false);};el.querySelector('#ce-reset').onclick=function(){save(true);};el.addEventListener('keydown',function(e){if(e.key==='Escape'){e.preventDefault();close();}});el.querySelector('#ce-name').focus();
  };
  /* CARD_EDITOR_R01_END */

  LIVE.wallMenu = function (anchor, id, name, pinned) {
    var esc = C.esc, st = C.st, old = document.getElementById('wmenu'); if (old) { old.remove(); if (old.dataset.id === id) return; }
    var el = document.createElement('div'); el.id = 'wmenu'; el.className = 'wmenu'; el.dataset.id = id; el.setAttribute('role', 'menu');
    var draw = function () {
      el.innerHTML = '<button role="menuitem" data-wm="edit" data-ptds-ui="s051836569928">编辑</button><button role="menuitem" data-wm="threshold" data-ptds-ui="s67f1b373520b">阈值与通知</button><button role="menuitem" data-wm="hide" data-ptds-ui="s145219e726b8">隐藏</button>' + (LIVE.vitalsDefinition(id) ? '<button role="menuitem" class="dg" data-wm="delete-vitals" data-ptds-ui="s7ca7b60a347c">删除卡片</button>' : '');
      el.querySelectorAll('[data-wm]').forEach(function (b) { b.onclick = function (e) { e.stopPropagation(); act(b.dataset.wm); }; });
    };
    var act = function (k) {
      el.remove();
      if (k === 'delete-vitals') return LIVE.vitalsDelete(id);
      if (k === 'threshold') return LIVE.thresholdOpen(id, name);
      if (k === 'hide') return LIVE.wallSet(id, { hide: true }, name);
      return LIVE.wallEdit(id, name);
    };
    draw(false);
    document.body.appendChild(el);
    var r = anchor.getBoundingClientRect();
    el.style.left = Math.min(r.left + window.scrollX, window.scrollX + document.documentElement.clientWidth - 246) + 'px';
    el.style.top = Math.max(window.scrollY + 8, r.top + window.scrollY - el.offsetHeight - 6) + 'px';
    setTimeout(function () { document.addEventListener('click', function off(e) { if (!el.contains(e.target)) { el.remove(); document.removeEventListener('click', off); } }); }, 0);
  };
  /* r60（产品负责人 2026-10-15 10:39）：状态工程不再占左侧导航；「我的状态」页内容区右上角放「增加我的状态」，点开就是原来的状态工程（模板、向导、已隐藏的卡） */
  LIVE.addStateMount = function () {
    var v = document.getElementById('state-cards-panel');
    if (C.st.app !== 'track' || C.st.view !== 'wall' || !v || document.getElementById('add-state')) return;
    var bar = document.createElement('div'); bar.id = 'add-state';
    bar.style.cssText = 'display:flex;justify-content:flex-end;position:relative;gap:8px;margin:8px 0';
    v.insertBefore(bar, v.firstChild);
  };
  /* 「增加我的状态」页下面：已隐藏的卡，点一下恢复 */
  LIVE.engHiddenMount = function () {
    if (C.st.app !== 'track' || C.st.view !== 'eng' || (C.st.eng && C.st.eng.step)) return;
    var v = document.getElementById('view'), H = (C.S().wall_prefs || {}).hidden || [], esc = C.esc;
    if (!v || document.getElementById('eng-hidden')) return;
    var sec = document.createElement('section'); sec.className = 'box'; sec.id = 'eng-hidden'; sec.style.marginTop = 'var(--primitive-space-5)';
    sec.innerHTML = '<h3 data-ptds-ui="se8371e681cb4">已隐藏的卡</h3>' + (H.length ? H.map(function (h) { return '<div class="lrow"><span>' + esc(h.name || h.card) + '</span><span class="sub2">' + esc(String(C.tzTime(h.at)).slice(5, 16)) + ' 隐藏</span><button class="chip" data-unhide="' + esc(h.card) + '">恢复到我的状态</button></div>'; }).join('')
      : '<div class="sub2" data-ptds-ui="saa26f9f09c83">没有隐藏的卡。在我的状态里点卡片右下角的齿轮，可以把卡片从我的状态里隐藏。</div>');
    v.appendChild(sec);
    sec.querySelectorAll('[data-unhide]').forEach(function (b) { b.onclick = function () { LIVE.wallSet(b.dataset.unhide, { hide: false }); }; });
  };
  (function () { var f0 = LIVE.renderWall; LIVE.renderWall = function () { var out = f0.apply(this, arguments); try { LIVE.wallPrefs(); } catch (err) { if(err&&(err.viewPending||err.code==='VIEW_CHANGED'))throw err; /* 图钉、齿轮只是快捷操作，失败不影响卡片 */ } return out; }; })();

  // STATE_SECTIONS_HELPERS_BEGIN: only formal references, never clinical values.
  function stateSectionRefs(b) {
    if (b && b.why === 'NO_TIMEPOINTS') return [];
    if (!b || !b.found) return null;
    var refs = [];
    (b.clues || []).forEach(function (c) { (c.indicators || []).forEach(function (i) {
      (i.records || []).forEach(function (r) { if (r.ref) refs.push('obs:' + r.ref); });
    }); });
    (b.main || []).forEach(function (m) { (m.options || []).forEach(function (o) {
      if (o.run_id != null) refs.push('run:' + o.tp + ':' + o.run_id);
    }); });
    return Array.from(new Set(refs)).sort();
  }
  function stateSectionUnread(current, seen) {
    return current !== null && current.some(function (r) { return !seen || seen.indexOf(r) < 0; });
  }
  // STATE_SECTIONS_HELPERS_END
  LIVE.stateSections = function () {
    var st = C.st, v = document.getElementById('view'), esc = C.esc;
    if (st.stateSection === undefined || st.stateSection === 'interpret') st.stateSection = 'cards';
    var tab = st.stateSection || null, count = v.querySelectorAll('.wcard:not(.add)').length;
    if (!document.getElementById('state-sections-css')) {
      var css = document.createElement('style'); css.id = 'state-sections-css';
      css.textContent = LIVE.GRAPH_CSS + '#state-sections .state-dot{display:inline-block;width:7px;height:7px;border-radius:50%;background:#e55050;margin-left:6px}#state-cards-panel{position:relative;padding-top:16px}#state-sections .state-arrow{justify-self:end;display:inline-flex;transition:opacity var(--ptds-fade-duration,180ms) ease-in-out}#state-sections .xh-t[aria-expanded="true"]{border-color:var(--theme-text-primary);background:var(--component-sidebar-selBg)}@media(max-width:700px){#state-sections .xh-tabs{grid-template-columns:1fr}}';
      document.head.appendChild(css);
    }
    var snap = C.S(), projected = Object.prototype.hasOwnProperty.call(snap, 'offset_refs');
    var refs = projected ? snap.offset_refs : stateSectionRefs(globalThis.PTDS_TRIAL_UI&&!PTDS_TRIAL_UI.can('offset')?null:LIVE.blGet()), key = 'ptds-state-offset-seen:' + snap.instance.instance_id;
    var seen = null;
    try { seen = JSON.parse(localStorage.getItem(key) || 'null'); } catch (e) { if(e&&(e.viewPending||e.code==='VIEW_CHANGED'))throw e; /* local read preference only */ }
    if (!Array.isArray(seen)) seen = null;
    if(projected&&seen&&seen.some(function(r){return String(r).indexOf('offset:')!==0;}))seen=null; // One-time local preference upgrade.
    // First opening of the feature establishes the existing-data watermark.
    if (refs !== null && (seen === null || tab === 'offset')) {
      seen = refs;
      try { localStorage.setItem(key, JSON.stringify(refs)); } catch (e) { if(e&&(e.viewPending||e.code==='VIEW_CHANGED'))throw e; /* storage unavailable */ }
    }
    var unread = stateSectionUnread(refs, seen);
    var defs = [
      ['cards', '状态卡片', count, '根据我的需求定制我主要关注和次要关注的状态卡片'],
      ['offset', '状态偏移', '', '从设定一个基线起，再推到下一个状态，再计算偏移'],
      ['push', '状态推送', '', '定期推送我关注的状态，让我定期了解我自己。']
    ];
    var panel = document.createElement('div'); panel.id = tab === 'cards' ? 'state-cards-panel' : 'state-section-panel';
    panel.setAttribute('role', 'region'); panel.setAttribute('aria-labelledby', 'state-tab-' + tab);
    if (tab === 'cards') { while (v.firstChild) panel.appendChild(v.firstChild); }
    else {
      v.innerHTML = '';
      panel.innerHTML = !tab ? '' : tab === 'offset' ? LIVE.baselineHtml() : LIVE.readingHtml('compact');
    }
    var bar = document.createElement('section'); bar.className = 'box'; bar.id = 'state-sections';
    bar.innerHTML = '<div class="xh-tabs" role="group" aria-label="我的状态分类" data-ptds-ui-aria-label="sc82174957ddf">' + defs.map(function (d) {
      return '<button class="xh-t" id="state-tab-' + d[0] + '" data-state-section="' + d[0] + '" aria-expanded="' + (tab === d[0]) + '"><b>' + d[1] + '</b><span class="n">' + d[2] + (d[0] === 'offset' && unread ? '<span class="state-dot" aria-label="相关数据有更新" title="相关数据有更新" data-ptds-ui-aria-label="sea6621cd4dd6" data-ptds-ui-title="sea6621cd4dd6"></span>' : '') + '</span><span class="state-arrow" style="transform:rotate(' + (tab === d[0] ? 180 : 0) + 'deg)">' + C.ic('chevron-down') + '</span><span class="sub2">' + esc(d[3]) + '</span></button>';
    }).join('') + '</div>';
    v.appendChild(bar);
    if (tab) { panel.classList.add('xh-body'); bar.appendChild(panel); }
    if (tab === 'offset') LIVE.bindBaseline();
    if (tab === 'push' && window.PTDS_STATE_PUSH && (!globalThis.PTDS_TRIAL_UI || PTDS_TRIAL_UI.can('push'))) window.PTDS_STATE_PUSH.mount(panel, C, LIVE);
    bar.querySelectorAll('[data-state-section]').forEach(function (button) { button.onclick = function () {
      if (button.disabled) return;
      var next = button.dataset.stateSection, closing = st.stateSection === next;
      var reduce = document.documentElement.dataset.motion === 'reduced' || window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      var finish = function () {
        st.stateSection = closing ? null : next; C.render();
        if (!closing && !reduce) {
          var body = document.querySelector('#state-sections .xh-body'), arrow = document.querySelector('#state-tab-' + next + ' .state-arrow');
          if (body) body.animate([{opacity:0},{opacity:1}],{duration:180,easing:'ease-in-out'});
        }
      };
      if (closing && !reduce && panel.animate) {
        panel.animate([{opacity:1},{opacity:0}],{duration:180,easing:'ease-in-out'}).finished.then(finish);
      } else finish();
    }; });
  };
  (function () { var wall = LIVE.renderWall; LIVE.renderWall = function () {
    wall.apply(this, arguments); LIVE.stateSections();
  }; })();

  LIVE.renderRules = function () {
    engCss();
    var esc = C.esc, st = C.st, R = loadRules(true), f = st.ruleSet || '';
    var sets = R.sets.filter(function (s) { return R.rules.some(function (r) { return r.set === s.id; }); });
    var list = R.rules.filter(function (r) { return !f || r.set === f; });
    var h =       '<div class="chips" role="group" aria-label="规则集" data-ptds-ui-aria-label="sdd373f784880"><button class="chip" data-rset="" aria-pressed="' + !f + '">全部 ' + R.rules.length + '</button>' + sets.map(function (s) {
        return '<button class="chip" data-rset="' + esc(s.id) + '" aria-pressed="' + (f === s.id) + '">' + esc(s.zh) + ' ' + R.rules.filter(function (r) { return r.set === s.id; }).length + '</button>'; }).join('') +
      (C.isReplay() ? '' : '<span class="grow" style="flex:1"></span><button class="btn2" id="rule-new">' + C.ic('plus') + '新建规则引擎</button>') + '</div>' +
      '<section class="box"><table class="rtab"><thead><tr><th data-ptds-ui="s18dba51b47c8">规则名称</th><th data-ptds-ui="sdd373f784880">规则集</th><th data-ptds-ui="s6320b4a8722a">状态</th></tr></thead><tbody>' + list.map(function (r) {
        return '<tr class="r" data-rule="' + esc(r.id) + '" tabindex="0"><td class="nm">' + esc(r.name) + '</td><td class="dim">' + esc(r.set_zh) + '</td><td class="dim">' + (r.used_by.length ? '在用' : esc(r.maturity)) + '</td></tr>';
      }).join('') + '</tbody></table></section>';
    document.getElementById('view').innerHTML = C.pgh('状态规则库') + h;
    document.querySelectorAll('[data-rset]').forEach(function (b) { b.onclick = function () { st.ruleSet = b.dataset.rset; LIVE.renderRules(); }; });
    var rn = document.getElementById('rule-new'); if (rn) rn.onclick = function () { st.eng = { step: 1, tpl: 'CUSTOM', sel: {} }; C.goTrack('eng'); }; /* 新建规则引擎 = 自定义阈值卡（真实可用的那条路） */
    document.querySelectorAll('tr[data-rule]').forEach(function (tr) {
      tr.onclick = function () { LIVE.openRule(tr.dataset.rule); };
      tr.onkeydown = function (ev) { if (ev.key === 'Enter') LIVE.openRule(tr.dataset.rule); };
    });
  };
  /* 规则弹层：一句话 → 用哪些数据 → 原文 → 展开看完整定义（编号、版本、指纹……） */
  LIVE.openRule = function (id) {
    engCss();
    var esc = C.esc, ic = C.ic, R = loadRules(), r = R.rules.filter(function (x) { return x.id === id; })[0];
    if (!r) return;
    var old = document.getElementById('rule-pop'); if (old) old.remove();
    var kv = [['编号', r.id], ['版本', r.version], ['指纹', r.fingerprint || '—'], ['规则集', r.set_zh], ['算法类型', r.kind], ['输出', r.output], ['参数来源', r.param_source],
      ['适用人群', r.population], ['复核状态', r.review], ['成熟度', r.maturity], ['在用', r.used_by.length ? r.used_by.join('；') : '没有卡在用']];
    var box = document.createElement('div');
    box.id = 'rule-pop';
    box.innerHTML = '<div class="scrim" data-close="1"></div><aside class="drawer" role="dialog" aria-label="' + esc(r.name) + '"><div class="dh"><span>' + esc(r.name) + '</span><button class="ibtn" data-close="1" aria-label="关闭">' + ic('x') + '</button></div><div class="db">' +
      '<div>' + esc(r.summary) + '</div>' +
      '<h3 data-ptds-ui="sfed147356f0c">用哪些数据</h3><div class="sub2">' + esc(r.inputs_zh.join('、') || '—') + '</div>' +
      '<h3 data-ptds-ui="s354b28c85333">原文</h3><div>' + srcLink(r.source, false) + '</div>' +
      '<div class="sub2">v' + esc(r.version) + ' · ' + esc(r.set_zh) + (r.used_by.length ? ' · 在用' : '') + '</div>' +
      '<details><summary class="sub2">完整定义</summary><div class="rkv" style="margin-top:var(--primitive-space-3)">' + kv.map(function (p) { return '<span>' + esc(p[0]) + '</span><span>' + esc(p[1]) + '</span>'; }).join('') + '</div>' +
      (r.fidelity ? '<h3 data-ptds-ui="sf7ff577c46e0">与原文的差异</h3><div class="sub2">' + esc(r.fidelity) + '</div>' : '') +
      (r.method ? '<h3 data-ptds-ui="sc415ff895dbc">参与指纹计算的内容</h3><pre class="sub2" style="white-space:pre-wrap;word-break:break-all">' + esc(JSON.stringify(r.method, null, 1)).slice(0, 4000) + '</pre>' : '') +
      '<div class="sub2">规则库只读。改规则 = 发新版本，由 产品负责人 或专家确认。</div></details></div></aside>';
    document.body.appendChild(box);
    box.querySelectorAll('[data-close]').forEach(function (b) { b.onclick = function () { box.remove(); }; });
    document.addEventListener('keydown', function esc1(ev) { if (ev.key === 'Escape') { box.remove(); document.removeEventListener('keydown', esc1); } });
  };
  /* ---------- 数据导航（R07/R08）：一行概览 + 三栏各 8 条单行、底部“查看全部”；同一来源同一天的更新合成一行，同类留痕合并 ---------- */
  function todayLocal() { try { return new Date().toLocaleDateString('sv-SE', { timeZone: 'Asia/Shanghai' }); } catch (err) { if(err&&(err.viewPending||err.code==='VIEW_CHANGED'))throw err; return new Date().toISOString().slice(0, 10); } }
  var GZH = { wearable: '穿戴设备', file: '文件报告', phone: '手机健康', manual: '手动录入' };
  /* GUARD_ASYNC_R05: overview history is a read-only view, never an authorization decision. */
  var guardHistoryReads={};
  LIVE.guardHistory = function () { if(globalThis.PTDS_TRIAL_UI&&!PTDS_TRIAL_UI.can('cluster'))return {rows:[],error:false,dirty:false};
    var key=C.st.key,e=guardHistoryReads[key]||(guardHistoryReads[key]={at:0,rows:null,error:false,busy:false,dirty:false});
    if(!e.busy&&Date.now()-e.at>10000){
      e.busy=true;var epoch=readEpoch;
      readView('/api/cluster/records?egress=1&key='+encodeURIComponent(key)).then(function(rows){
        if(epoch!==readEpoch)return;
        if(!Array.isArray(rows))throw Error('RECORDS_INVALID');
        e.dirty=e.dirty||e.error||JSON.stringify(e.rows)!==JSON.stringify(rows);
        e.rows=rows;e.error=false;e.at=Date.now();
      }).catch(function(){
        if(epoch!==readEpoch)return;
        e.dirty=e.dirty||!e.error;e.error=true;e.at=Date.now();
      }).finally(function(){e.busy=false;LIVE.flushGuardHistory();});
    }
    return e;
  };
  LIVE.flushGuardHistory = function () {
    if(C.st.app!=='torch'||C.st.tview!=='guard'||C.st.foot)return;
    var e=LIVE.guardHistory();
    if(e.dirty&&LIVE.canAutoPaint()){e.dirty=false;var y=window.scrollY;C.renderMainOnly();window.scrollTo(0,y);}
  };
  /* GUARD_ASYNC_R05_END */
  LIVE.renderGuard = function () {
    wall3Css();
    var esc = C.esc, ic = C.ic, rows = C.torchRows(), today = todayLocal(), groups = {}, order = [];
    var shortWhen = function (t) { var m = /(\d{4})-(\d\d-\d\d)(?:[ T](\d\d:\d\d))?/.exec(String(t || '')); return m ? (m[1] === today.slice(0, 4) ? '' : m[1] + '-') + m[2] + (m[3] ? ' ' + m[3] : '') : String(t || '—'); };
    var when = function (r) { return r.ts ? '<span data-ts="' + r.ts + '">' + C.ago(r.ts) + '</span>' : esc(shortWhen(r.when)); };
    rows.forEach(function (r) {
      var src = String(r.src || '').split(' · ')[0], day = String(r.when || '').slice(0, 10), k = src + '|' + day;
      if (!groups[k]) { groups[k] = { src: src, day: day, g: r.g, sourceKind:r.sourceKind, names: [], metricCodes: [] }; order.push(k); }
      if (groups[k].names.indexOf(r.name) < 0) { groups[k].names.push(humanLabel(r.name).replace(/（[^（）]*）$/, '')); groups[k].metricCodes.push(r.code || ''); }
      groups[k].n = (groups[k].n || 0) + 1;
    });
    var upd = order.map(function (k) { return groups[k]; }).sort(function (a, b) { return a.day < b.day ? 1 : a.day > b.day ? -1 : 0; }).slice(0, 8);
    var nsrc = {}; rows.forEach(function (r) { nsrc[String(r.src || '').split(' · ')[0]] = 1; });
    var lastDay = rows.map(function (r) { return String(r.when || '').slice(0, 10); }).filter(function (d) { return /^\d{4}-/.test(d); }).sort().pop() || '';
    var nLast = rows.filter(function (r) { return String(r.when || '').slice(0, 10) === lastDay; }).length;
    var srcs = C.recentSources().slice(0, 8);
    var ev = [], seen = {}, LANE = { source: '数据源', data: '数据', auth: '授权' };
    var history=LIVE.guardHistory();
    LIVE.byTime(C.graphEvents(history.rows||[])).forEach(function (e) {
      var m = e.lane === 'data' && /^(保存|更正) (.+?)( · 第 \d+ 版)?$/.exec(e.text), src = m && /（([^（）]+)）$/.exec(m[2]);
      if (!m) { ev.push(e); return; }
      if (src) src[1] = src[1].split('，')[0];
      var k = m[1] + '|' + (src ? src[1] : '') + '|' + e.when;
      if (seen[k]) { seen[k].n++; return; }
      seen[k] = { lane: 'data', verb: m[1], src: src ? src[1] : '', when: e.when, n: 1 }; ev.push(seen[k]);
    });
    ev = ev.slice(0, 8).map(function (e) { return e.verb ? { lane: 'data', groupedCount:true, text: e.verb + ' ' + (e.src ? e.src + ' 数据 ' + e.n + ' 条' : e.n + ' 条数据'), when: e.when } : e; });
    document.getElementById('view').innerHTML =
      '<div class="gsum"><span><b>' + rows.length + '</b>条数据</span>' + (lastDay ? '<span><b>' + nLast + '</b>条' + (lastDay === today ? '今天' : shortWhen(lastDay) + ' ') + '新到</span>' : '') + '<span><b>' + Object.keys(nsrc).filter(Boolean).length + '</b>个来源</span></div><div class="grid3eq">' +
      '<section class="box" data-cmp="T14"><h3>' + ic('inbox') + '近期数据接入</h3>' +
        (srcs.length ? srcs.map(function (r) { return '<div class="l1"><span' + (r.sourceKind === 'SYNTHETIC' ? ' data-synthetic-date' : '') + '>' + esc(r.name) + '</span><span class="sub2">' + esc(String(r.note || '').split(/[，。；]/)[0]) + '</span><span class="sub2">' + when(r) + '</span></div>'; }).join('') : '<div class="sub2" data-ptds-ui="sbe6d74b0cfa2">还没有接入任何数源。</div>') +
        '<button class="link gall" id="g-src" data-ptds-ui="s57a3022d4eb2">查看全部 · 我的数源</button></section>' +
      '<section class="box" data-cmp="T14" data-sem="SEM-33"><h3>' + ic('file-text') + '近期数据更新</h3>' +
        (upd.length ? upd.map(function (u) { var auto = u.g === 'wearable' || u.g === 'phone';
          return '<div class="l1" data-overview-codes="' + esc(JSON.stringify(u.metricCodes)) + '" title="' + esc(u.names.join('、')) + '"><span data-overview-items' + (u.sourceKind === 'SYNTHETIC' ? ' data-synthetic-source' : '') + '>' + esc(u.src || '其他') + ' · ' + u.n + ' 项</span><span class="sub2">' + esc(shortWhen(u.day)) + '</span><span class="mode' + (auto ? '' : ' manual') + '">' + (auto ? '自动' : '手动') + '</span></div>'; }).join('') : '<div class="sub2">还没有数据。</div>') +
        '<button class="link gall" id="g-all" data-ptds-ui="s0d3b79fd2ec8">查看全部 · 我的数据</button></section>' +
      '<section class="box" data-cmp="T14"><h3>' + ic('waypoints') + '最近数据留痕</h3>' +
        (history.error?'<div class="sub2" role="status" data-ptds-inline><!--ptds-ui:s098dd9d13554-->授权记录暂未更新<!--/ptds-ui-->'+(history.rows?'，显示上次读取结果。':'，稍后自动重试。')+'</div>':history.rows===null?LIVE.readingHtml('inline'):'') +
        (ev.length ? ev.map(function (e) { return '<div class="l1"' + (e.lane === 'auth' ? ' data-sem="SEM-30"' : '') + '><span' + (e.groupedCount?' data-summary-count':'') + '>' + esc(e.text) + '</span><span class="sub2">' + LANE[e.lane] + '</span><span class="sub2">' + esc(shortWhen(e.when)) + '</span></div>'; }).join('') : '<div class="sub2">还没有留痕。</div>') +
        '<button class="link gall" id="g-trail" data-ptds-ui="sa6039e504c5d">查看全部 · 数据日记</button></section></div>';
    var g = function (id, fn) { var el = document.getElementById(id); if (el) el.onclick = LIVE.action(fn); };
    g('g-all', function () { C.st.dataView = 'time'; C.st.dataCode = null; C.st.dataPage = 0; C.st._dataPages=null; C.st.dataFrom=''; C.st.dataTo=''; C.goTorch('data'); });
    g('g-src', function () { C.goTorch('sources'); });
    g('g-trail', function () { C.st.graphLane = 'ALL'; C.st.graphJump = 'eg-diary'; C.goTorch('graph'); });
  };
  /* METRIC_UX_R02_BEGIN: read-only presentation; no reference-range inference. */
  function metricValueHtml(o, fallback) {
    if (!o) return C.esc(fallback == null ? '无值' : fallback);
    var text = human(o.code, o.value_raw, o.unit_raw, o.comparator), raw = o.value_raw;
    if (raw == null || String(raw).trim() === '' || typeof raw === 'boolean' || /^(true|false)$/.test(String(raw)) ||
        /_BEDTIME_(START|END)$/.test(o.code || '') || (o.unit_raw === 'min' && /(SLEEP|IN_BED)/.test(o.code || '')))
      return '<span class="mx-value">' + C.esc(text) + '</span>';
    return '<span class="mx-value">' + C.esc((o.comparator ? (OPS[o.comparator] || o.comparator) : '') + String(raw)) + '</span>' +
      (o.unit_raw ? ' <span class="mx-unit">' + C.esc(UNIT_ZH[o.unit_raw] || o.unit_raw) + '</span>' : '');
  }
  function metricSequence(rows, tl, pointLimit) {
    // Stable same-day order is kept. This order also drives the micro-chart; list selection is unchanged.
    var ordered = rows.slice().sort(function (a, b) { return a.when < b.when ? -1 : a.when > b.when ? 1 : 0; });
    var points = ordered.map(function (r) {
      var o = tl[r.ref], raw = o && o.value_raw, def = o && C.FULL[o.code], text = raw == null ? '' : String(raw);
      var missing = raw == null || text.trim() === '', cmp = o && o.comparator;
      var numeric = !!(o && def && def.type === 'DECIMAL' && !/_BEDTIME_(START|END)$/.test(o.code));
      var exact = numeric && !missing && !cmp && /^[-+]?\d+(?:\.\d+)?$/.test(text.trim()) && isFinite(Number(text));
      // Preserve text precision; decline coordinates whose significant digits exceed reliable JS precision.
      if (exact && text.replace(/^[+-]?0*/, '').replace('.', '').replace(/^0+/, '').length > 15) exact = false;
      return { ref: r.ref, tp: String(r.when || ''), raw: text, unit: o && o.unit_raw || '',
        display: o ? human(o.code, raw, o.unit_raw, cmp) : text, v: exact ? Number(text) : null, exact: exact, missing: missing, comparator: cmp, numeric: numeric, typed: !!def,
        method: o && (o.method || o.method_id || o.detection_method) || null,
        instant: o && o.temporal && o.temporal.observed_at || null,
        // Only for preserving the old chart's occupied geometry, never for displayed coordinates.
        oldNumeric: !!o && isFinite(+o.value_raw) };
    });
    var decision = resolveChartPresentation(points, { kind: 'observations' });
    // Comparability and occupied geometry still use the complete history. The
    // list only draws the last 30 points; do not retain every expanded point
    // across all metric rows. Detail callers keep the complete sequence.
    var oldPlot = points.filter(function (p) { return p.oldNumeric; }).length > 1;
    if (Number.isInteger(pointLimit) && pointLimit > 0) points = points.slice(-pointLimit);
    return Object.assign({ points: points, oldPlot: oldPlot }, decision);
  }
  /* CHART_GRAMMAR_R03_BEGIN: display-only decisions; no clinical thresholds or business calculations. */
  var CHART_REASON = {
    zero_observations: '暂无历史观测', single_numeric_observation: '单次观测',
    qualified_numeric_result: '结果为范围表达', missing_values: '含缺失记录',
    no_numeric_values: '暂无有效数值', unknown_type: '记录类型未提供',
    unsupported_precision: '暂不比较，保留原值', mixed_units: '单位不同，暂不比较',
    unknown_unit: '单位未提供，暂不比较', unknown_method: '检测方法未提供', changed_method: '检测方法不同',
    ambiguous_order: '同日顺序未确认', missing_time: '观测时间未提供',
    categorical_observation: '非数值记录', count_unit_required: '计数单位未提供',
    invalid_count: '数量缺失或无效', independent_groups: '各组独立计数，不合计',
    no_delta_slot: '保留各版本原始记录', unsupported: '保留原始记录'
  };
  function resolveChartPresentation(observations, context) {
    var p = observations || [], c = context || {}, reasons = [], kind = 'unsupported', grammar = null;
    var exact = p.filter(function (x) { return x.exact; }), units = [], ambiguous = false;
    exact.forEach(function (x) { if (units.indexOf(x.unit) < 0) units.push(x.unit); });
    p.forEach(function (x, i) {
      var prev = p[i - 1];
      if (prev && String(prev.tp).slice(0, 10) === String(x.tp).slice(0, 10) &&
          (!prev.instant || !x.instant || !isFinite(Date.parse(prev.instant)) || !isFinite(Date.parse(x.instant)) || Date.parse(prev.instant) >= Date.parse(x.instant))) ambiguous = true;
    });
    var mixed = units.length > 1, missingTime = p.some(function (x) { return !x.tp; });
    var unknownMethod = exact.some(function (x) { return !x.method; });
    var knownMethods = [];
    exact.forEach(function (x) { if (x.method && knownMethods.indexOf(x.method) < 0) knownMethods.push(x.method); });
    var changedMethod = knownMethods.length > 1;
    var unknownUnit = exact.length > 1 && exact.some(function (x) { return !x.unit; });
    // Sequence connectors do not assert method comparability or continuous monitoring.
    // Missing method metadata keeps its warning; explicit method conflicts remain disconnected.
    var connect = exact.length > 1 && !mixed && !unknownUnit && !ambiguous && !missingTime && !changedMethod;
    if (c.kind === 'counts') {
      grammar = 'G03'; kind = 'count_distribution'; connect = false;
      if (!c.countUnit) reasons.push('count_unit_required');
      if (!p.length || p.some(function (x) { return !Number.isSafeInteger(x.count) || x.count < 0 || !x.label; })) reasons.push('invalid_count');
      if (reasons.length) kind = 'unsupported';
      else if (c.additive !== true) reasons.push('independent_groups');
    } else if (c.kind === 'versions') {
      grammar = 'G04'; kind = 'version_comparison'; connect = false; reasons.push('no_delta_slot');
    } else if (c.kind && c.kind !== 'observations') { reasons.push('unsupported'); connect = false;
    } else if (!p.length) { kind = 'zero_observations'; reasons.push(kind);
    } else {
      grammar = 'G01';
      if (mixed) reasons.push('mixed_units');
      if (unknownUnit) reasons.push('unknown_unit');
      if (ambiguous) reasons.push('ambiguous_order');
      if (missingTime) reasons.push('missing_time');
      if (!exact.length) {
        kind = 'unsupported';
        if (p.some(function (x) { return x.numeric && x.comparator; })) { kind = 'qualified_numeric_result'; reasons.push(kind); }
        else if (p.every(function (x) { return x.missing; })) reasons.push('no_numeric_values');
        else if (p.some(function (x) { return !x.typed; })) reasons.push('unknown_type');
        else if (p.some(function (x) { return x.numeric; })) reasons.push('unsupported_precision');
        else { kind = 'categorical_observation'; grammar = 'G05'; reasons.push(kind); }
      } else {
        kind = p.length === 1 ? 'single_numeric_observation' : connect && !unknownMethod ? 'comparable_numeric_series' : 'non_comparable_series';
        if (p.length === 1) reasons.push('single_numeric_observation');
        else if (changedMethod) reasons.push('changed_method');
        else if (unknownMethod) reasons.push('unknown_method');
        if (p.some(function (x) { return x.numeric && x.comparator; })) { kind = 'qualified_numeric_result'; reasons.push(kind); }
        if (p.some(function (x) { return x.missing; })) reasons.push('missing_values');
      }
    }
    return { kind: kind, grammar: grammar, reasons: reasons, note: reasons.length ? CHART_REASON[reasons[0]] : '',
      explanation: reasons.map(function (r) { return r === 'qualified_numeric_result' ? '结果为范围表达，无法确定精确读数。' : CHART_REASON[r]; }).join('；') + (connect && unknownMethod ? '；连线仅表示观测顺序，方法可比性未确认' : ''),
      connect: connect, mixed: mixed, noNumericScale: mixed || unknownUnit, ambiguous: ambiguous, unit: units.length === 1 ? units[0] : '' };
  }
  // Reserved G02 interface. Caller must supply a confirmed observation-bound range and its existing verdict.
  // Never wired to OCR candidates, notification thresholds or dictionary defaults.
  function chartReferenceView(observation, range) {
    if (!observation || !observation.exact || !range || range.confirmed !== true || !range.source ||
        range.observationRef !== observation.ref || range.unit !== observation.unit ||
        ['within', 'above', 'below'].indexOf(range.status) < 0) return null;
    var bound = function (x) { return typeof x === 'string' && /^[-+]?\d+(?:\.\d+)?$/.test(x) && isFinite(Number(x)); };
    var hasLow = range.low != null, hasHigh = range.high != null;
    if ((!hasLow && !hasHigh) || (hasLow && (!bound(range.low) || typeof range.lowInclusive !== 'boolean')) ||
        (hasHigh && (!bound(range.high) || typeof range.highInclusive !== 'boolean')) ||
        (hasLow && hasHigh && Number(range.low) > Number(range.high))) return null;
    return { value: observation.raw, unit: range.unit, low: range.low, high: range.high,
      lowInclusive: range.lowInclusive, highInclusive: range.highInclusive, status: range.status,
      source: range.source, observationRef: range.observationRef };
  }
  // Reserved G03 primitive: existing counts only, common zero baseline, no inferred totals or percentages.
  function chartCountBars(items, context) {
    var decision = resolveChartPresentation(items, Object.assign({}, context, { kind: 'counts' }));
    if (decision.kind !== 'count_distribution') return { decision: decision, html: '' };
    var max = Math.max.apply(null, items.map(function (x) { return x.count; })), height = items.length * 28 + 20;
    var body = '<line x1="38%" x2="38%" y1="4" y2="' + (height - 20) + '" class="mx-line"/><text x="38%" y="' + (height - 4) + '">0</text>';
    items.forEach(function (x, i) {
      body += '<text x="0" y="' + (i * 28 + 18) + '">' + C.esc(x.label) + '</text>' +
        '<rect class="mx-count-bar" x="38%" y="' + (i * 28 + 7) + '" width="' + (max ? x.count / max * 42 : 0) + '%" height="12"/>' +
        '<text x="84%" y="' + (i * 28 + 18) + '">' + x.count + ' ' + C.esc(context.countUnit) + '</text>';
    });
    return { decision: decision, html: '<svg class="mx-plot" width="100%" height="' + height + '" role="img" aria-label="' + C.esc(items.map(function (x) { return x.label + ' ' + x.count + ' ' + context.countUnit; }).join('；') + '；零基线' + (decision.note ? '；' + decision.note : '')) + '">' + body + '</svg>' };
  }
  /* CHART_GRAMMAR_R03_END */
  function metricPlot(seq, detail) {
    var all = seq.points, points = detail ? all : all.slice(-30), valid = (seq.mixed || seq.noNumericScale) ? [] : points.filter(function (p) { return p.exact; });
    if (seq.kind === 'categorical_observation') {
      var events = points.map(function (p, i) {
        if (p.missing) return '';
        return '<circle class="mx-event' + (i === points.length - 1 ? ' mx-latest' : '') + '" cx="' + (points.length < 2 ? 50 : 4 + i * 92 / (points.length - 1)) + '%" cy="14" r="' + (i === points.length - 1 ? 2.7 : 1.65) + '"/>';
      }).join('');
      return '<svg class="spk mx-plot" height="28" role="img" data-chart-kind="categorical_observation" aria-label="' + C.esc('按记录顺序，间距不代表天数；' + points.map(function (p) { return p.tp + '：' + (p.missing ? '未记录' : p.display); }).join('；')) + '">' + events + '</svg>';
    }
    var H = detail ? 120 : 28, pad = detail ? 4 : 3, lo = valid.length ? Infinity : 0, hi = valid.length ? -Infinity : 0;
    // Do not pass the entire history as function arguments. Pairwise min/max
    // retains the original numeric semantics, including NaN and signed zero.
    for (var vi = 0; vi < valid.length; vi++) {
      lo = Math.min(lo, valid[vi].v); hi = Math.max(hi, valid[vi].v);
    }
    if(detail&&seq.extent&&seq.extent.length===2&&valid.length){lo=seq.extent[0];hi=seq.extent[1];}
    var x = function (i) { return points.length < 2 ? 50 : pad + i * (100 - 2 * pad) / (points.length - 1); };
    var y = function (v) { return hi === lo ? (detail ? 70 : 14) : (detail ? 104 : 23) - (v - lo) / (hi - lo) * (detail ? 66 : 18); };
    var body = '', last = points[points.length - 1], first = points[0];
    points.forEach(function (p, i) {
      if (!p.exact || seq.mixed || seq.noNumericScale) return;
      var prev = points[i - 1];
      if (seq.connect && prev && prev.exact) body += '<line class="mx-line" x1="' + x(i - 1) + '%" y1="' + y(prev.v) + '" x2="' + x(i) + '%" y2="' + y(p.v) + '"/>';
      body += '<circle class="mx-dot' + (i === points.length - 1 ? ' mx-latest' : '') + '" cx="' + x(i) + '%" cy="' + y(p.v) + '" r="' + (detail ? (p === last ? 3.5 : 2.5) : (p === last ? 2.7 : 1.65)) + '"/>';
      if (seq.selectedRef && seq.selectedRef === p.ref) body += '<circle class="mx-selected" cx="' + x(i) + '%" cy="' + y(p.v) + '" r="6"/>';
    });
    if (detail && valid.length) {
      // Fixed-size text in the existing 120px plot, not text stretched by an SVG viewBox.
      body += '<text class="mx-scale" x="1%" y="16">' + C.esc(seq.unit) + '</text>';
      if (first && first.exact && first !== last) body += '<text class="mx-first-label" x="' + x(0) + '%" y="' + (y(first.v) - 10) + '">' + C.esc(first.raw) + '</text>';
      if (last && last.exact) body += '<text class="mx-last-label" x="' + x(points.length - 1) + '%" y="' + (y(last.v) - 10) + '" text-anchor="end">' + C.esc(last.raw) + '</text>';
    }
    var label = (seq.explanation ? seq.explanation.replace(/[。；]+$/, '') + '；' : '') + '按观测顺序，间距不代表天数' + (last && last.exact && !seq.mixed && !seq.noNumericScale ? '；最后一条 ' + last.raw + ' ' + seq.unit : '');
    if (!body) body = '<text class="mx-empty" x="' + (detail ? '50' : '0') + '%" y="' + (detail ? '64' : '18') + '"' + (detail ? ' text-anchor="middle"' : '') + '>' + C.esc(seq.note) + '</text>';
    return '<svg class="spk mx-plot" height="' + H + '" role="img" data-chart-kind="' + C.esc(seq.kind) + '" data-chart-reasons="' + C.esc((seq.reasons || []).join(' ')) + '" aria-label="' + C.esc(label) + '">' + body + '</svg>';
  }
  function metricMini(seq) {
    return '<span class="mx-mini' + (seq.oldPlot ? '' : ' mx-no-slot') + '" title="' + C.esc(seq.explanation || '按观测顺序，间距不代表天数') + '">' + metricPlot(seq, false) + '</span>';
  }
  function metricCss() {
    if (document.getElementById('metric-ux-r02-css')) return;
    var el = document.createElement('style'); el.id = 'metric-ux-r02-css'; el.textContent =
      '.chips .mx-filter{padding-inline:calc(12px - .5em);gap:0}.mx-filter .mx-count-unit{font:inherit;pointer-events:none}' +
      '[data-metric-ux] .mx-name{font-weight:600;overflow-wrap:anywhere}' +
      '[data-metric-ux] .mx-value,.mx-versions .mx-value{font-weight:650;font-variant-numeric:tabular-nums;font-size:1.12em;line-height:1}' +
      '[data-metric-ux] .mx-unit,.mx-versions .mx-unit{font-size:var(--scale-type-meta);font-weight:400;color:var(--theme-text-secondary)}' +
      '[data-metric-ux] .mx-count{font-weight:500;color:var(--theme-text-secondary)}[data-metric-ux] .mx-date{color:var(--theme-text-tertiary)}' +
      '[data-metric-ux] .mx-mini{display:block;position:relative;line-height:inherit}[data-metric-ux] .mx-mini.mx-no-slot{height:0}' +
      '[data-metric-ux] .mx-no-slot .mx-plot{position:absolute;left:0;top:-14px}' +
      '[data-metric-ux] .mx-event{fill:none;stroke:var(--theme-text-secondary);stroke-width:1.2}[data-metric-ux] .mx-event.mx-latest{fill:var(--theme-text-primary)}' +
      '[data-metric-ux] .mx-selected{fill:none;stroke:var(--theme-text-primary);stroke-width:1.2}[data-metric-ux] .mx-count-bar{fill:var(--theme-text-secondary);opacity:.65}' +
      '[data-metric-ux] .mx-plot{width:100%;overflow:visible;pointer-events:none;color:var(--theme-text-primary)}' +
      '[data-metric-ux] .mx-line{stroke:var(--theme-text-tertiary);stroke-width:1;opacity:.5}' +
      '[data-metric-ux] .mx-plot .mx-line{stroke:var(--theme-text-secondary);stroke-width:1.2;opacity:.65}' +
      '[data-metric-ux] .mx-dot{fill:var(--theme-text-secondary);opacity:.55}[data-metric-ux] .mx-latest{fill:var(--theme-text-primary);opacity:1}' +
      '[data-metric-ux] .mx-plot text{font-variant-numeric:tabular-nums;font-family:inherit;font-size:12px;fill:var(--theme-text-secondary)}' +
      '[data-metric-ux] .mx-plot .mx-last-label{font-size:15px;font-weight:650;fill:var(--theme-text-primary)}' +
      '[data-metric-ux] .mx-plot .mx-first-label{font-size:13px;fill:var(--theme-text-secondary)}' +
      '[data-metric-ux] .mx-inline{float:right;font-size:var(--scale-type-meta);font-weight:400;line-height:inherit;color:var(--theme-text-secondary)}' +
      '[data-metric-ux] .mx-inline i{display:inline-block;width:5px;height:5px;border-radius:50%;background:var(--theme-text-primary);vertical-align:middle;margin-right:6px}' +
      '[data-metric-ux] .mx-order{font-size:var(--scale-type-min);color:var(--theme-text-tertiary)}' +
      '[data-metric-ux] button.dcode:focus-visible,[data-metric-ux] button.lrow:focus-visible{outline:1px solid var(--theme-line-control);outline-offset:2px}' +
      '[data-metric-ux] button.dcode:hover{background:var(--theme-action-icon-bgHover)}' +
      '.mx-versions .mx-vrow{display:grid;grid-template-columns:minmax(0,1.2fr) minmax(0,.8fr) minmax(0,2fr) minmax(0,.65fr) minmax(0,1.5fr);align-items:baseline}' +
      '.mx-versions .mx-vrow>span{min-width:0!important}.mx-versions .mx-vrow span{min-width:0}' +
      '.mx-versions .mx-version{font-weight:600;color:var(--theme-text-primary)!important}.mx-versions .mx-meta{font-size:var(--scale-type-meta);color:var(--theme-text-secondary)}';
    document.head.appendChild(el);
    var resizeFrame;
    window.addEventListener('resize', function () {
      cancelAnimationFrame(resizeFrame);
      resizeFrame = requestAnimationFrame(function () {
        document.querySelectorAll('.mx-versions [data-mx-version]').forEach(function (row) {
          if (row._mxOriginal) { row.innerHTML = row._mxOriginal; row.classList.remove('mx-vrow'); delete row.dataset.mxDone; }
        });
        metricVersionLayout();
      });
    });
  }
  function metricVersionLayout() {
    document.querySelectorAll('.mx-versions [data-mx-version]').forEach(function (row) {
      if (row.dataset.mxDone) return;
      row.dataset.mxDone = '1';
      var v = JSON.parse(row.dataset.mxVersion), previous = row.innerHTML, height = row.getBoundingClientRect().height;
      row._mxOriginal = previous;
      var used = v.runs.length ? '被 ' + ((v.cards && v.cards.length) ? v.cards.join('、') : v.runs.map(function (n) { return '计算 #' + n; }).join('、')) + ' 用过' : '当前状态卡暂未包含该数据';
      var tag = v.tag === '当前' ? '当前记录版本' : v.tag;
      row.classList.add('mx-vrow');
      row.innerHTML = '<span class="mx-version">第 ' + v.revision + ' 版 · ' + C.esc(tag) + '</span><span>' + (v.status !== 'ACTIVE' ? '—' : metricValueHtml({value_raw:LIVE.yn(v.value),unit_raw:v.unit,comparator:v.comparator})) + '</span>' +
        '<span class="mx-meta">' + (v.saved_at ? '版本入库：' + C.esc(C.tzTime(v.saved_at, true)) : '') + '</span><span class="mx-meta">' + (v.source ? '来源：' + C.esc(v.source) : '') + '</span><span class="mx-meta">' + C.esc(used) + '</span>';
      // Do not grow the panel or move its actions for a narrower viewport / longer source.
      if (Math.abs(row.getBoundingClientRect().height - height) > .5) {
        row.classList.remove('mx-vrow'); row.innerHTML = previous;
        // Compact widths keep the original two-column wrapping, but make the version/value anchors explicit.
        var identity = row.firstElementChild, value = row.lastElementChild;
        if (identity && identity.firstChild && identity.firstChild.nodeType === 3) {
          var anchor = document.createElement('strong'); anchor.textContent = identity.firstChild.textContent;
          identity.replaceChild(anchor, identity.firstChild);
        }
        if (value) value.innerHTML = v.status !== 'ACTIVE' ? '—' : metricValueHtml({value_raw:LIVE.yn(v.value),unit_raw:v.unit,comparator:v.comparator});
        if (Math.abs(row.getBoundingClientRect().height - height) > .5) row.innerHTML = previous;
      }
    });
  }
  /* METRIC_UX_R02_END */

  /* ---------- 我的数据（R07）：默认“按指标”一项一行，点进去看这一项的全部历史；“按时间”是全部明细，分页 ---------- */
  /* WRITE_RECEIPT_R01: a confirmed write is not a full read projection. */
  var confirmedWriteReceipts=new WeakMap();
  LIVE.writeBody=function(body){return C.DATA&&C.DATA.ptds_live&&C.DATA.ptds_live.write_receipt_version>=1?Object.assign({},body,{response_view:'receipt-v1'},window.PTDS_COMPUTE&&window.PTDS_COMPUTE.enabled()?{compute_mode:'background-v1'}:{}):body;};
  LIVE.validateWriteReceipt=function(r,body,path,identity){
    var operation={'/api/torch/save':'save','/api/torch/correct':'correct','/api/torch/retract':'retract'}[path];
    var valid=operation&&typeof identity==='string'&&!Object.prototype.hasOwnProperty.call(r,'snapshot')&&!Object.prototype.hasOwnProperty.call(r,'timeline')&&r.instance_id===identity&&r.operation===operation&&r.target&&r.sync&&typeof r.sync.ok==='boolean'&&JSON.stringify(r.invalidates)===JSON.stringify(['home','data','graph','versions']);
    if(operation==='retract')valid=valid&&r.target.observation_id===body.observation_id&&['RETRACTED','UNCHANGED'].includes(r.outcome);
    else{
      valid=valid&&typeof r.request_id==='string'&&typeof r.batch_id==='string'&&r.export==='WRITTEN'&&Array.isArray(r.results)&&r.results.every(function(x){return x&&['CREATED','REVISED','UNCHANGED'].includes(x.outcome)&&typeof x.observation_id==='string'&&Number.isInteger(x.revision)&&x.revision>0;});
      if(operation==='save')valid=valid&&r.target.request_id===body.request_id&&r.request_id===body.request_id&&Array.isArray(body.rows)&&r.results.length===body.rows.length;
      if(operation==='correct')valid=valid&&r.target.observation_id===body.observation_id&&r.results.length===1&&r.results[0].observation_id===body.observation_id;
    }
    if(!valid){var e=Error('WRITE_CONFIRMATION_INVALID');e.code='WRITE_CONFIRMATION_INVALID';e.detail='未收到匹配的保存回执，请核对；不会自动重复提交';throw e;}
  };
  LIVE.invalidateAfterWrite=function(key){
    if(C.SNAPS[key])C.SNAPS[key]=Object.assign({},C.SNAPS[key],{_pending:true});
    delete LIVE.homeReads[key];delete LIVE.fullHydrations['/api/state?key='+encodeURIComponent(key)];
    if(C.st.key===key){LIVE.invalidateData();LIVE._bl=null;C.st.cpAi=null;}
  };
  LIVE.rememberWriteReceipt=function(key,r){confirmedWriteReceipts.set(r,key);LIVE.invalidateAfterWrite(key);};
  LIVE.isConfirmedWrite=function(key,r){return !!r&&confirmedWriteReceipts.get(r)===key;};
  /* WRITE_RECEIPT_R01_END */
  /* DATA_READ_R01: pages never replace SNAPS or pretend to be a timeline. */
  LIVE.dataReadEnabled=function(){return !!(C&&C.DATA&&C.DATA.ptds_live&&C.DATA.ptds_live.data_read_version>=1);};
  LIVE.dataRoute=function(){return LIVE.dataReadEnabled()&&!C.isReplay()&&!C.st.foot&&C.st.app==='torch'&&['data','detail'].includes(C.st.tview);};
  LIVE.invalidateData=function(){if(LIVE._dataReadSession)LIVE._dataReadSession.invalidate();
    if(C.st._dataPages)C.st._dataPages.slots={};
    viewReads.forEach(function(e,path){if(path.indexOf('/api/data/read?')===0&&!e.promise)viewReads.delete(path);});
  };
  var dataPreviewBodies=new Map(),dataPreviewNext=0;
  LIVE.dataPath=function(view,args){
    var params=Object.assign({key:C.st.key,view:view},args||{});
    if(!['observation','versions'].includes(view)&&LIVE.realBridge&&!LIVE.realBridge()){
      var identity=C.S().instance.instance_id,text=JSON.stringify(C.MockBridge.receipts(identity).map(function(r){return {created:r.created,when:r.when,phone:r.phone};})),memo=dataPreviewBodies.get(C.st.key);
      if(!memo||memo.identity!==identity||memo.text!==text){memo={identity:identity,text:text,id:++dataPreviewNext};dataPreviewBodies.set(C.st.key,memo);}
      // Cache keys retain the exact content identity, not 128 copies of the body.
      params.preview_read=memo.id;
    }
    return '/api/data/read?'+Object.keys(params).filter(function(k){return params[k]!==null&&params[k]!==undefined&&params[k]!=='';}).sort().map(function(k){return encodeURIComponent(k)+'='+encodeURIComponent(params[k]);}).join('&');
  };
  LIVE.validateDataRead=function(r,path){
    var fail=function(code){
      var e=new Error(code);e.code=code;e.detail='读取结果不完整，请重新读取。';e.viewPending=true;e.path=path;
      viewReads.set(path,{error:e,epoch:readEpoch});throw e;
    };
    if(!r||r.projection!=='data-read/1'||!r.scope||r.scope.instance_id!==C.S().instance.instance_id)fail('DATA_INSTANCE_INVALID');
    var q=new URLSearchParams(path.split('?')[1]||''),view=q.get('view');
    var obj=function(x){return !!x&&typeof x==='object'&&!Array.isArray(x);},str=function(x){return typeof x==='string';};
    var nat=function(x){return Number.isSafeInteger(x)&&x>=0;},positive=function(x){return nat(x)&&x>0;};
    var strings=function(x){return Array.isArray(x)&&x.every(str);};
    var observation=function(o){return obj(o)&&str(o.ref)&&/^.+@[1-9][0-9]*$/.test(o.ref)&&str(o.code)&&str(o.label_zh)&&
      (o.tp===null||str(o.tp))&&(o.value_raw===null||str(o.value_raw))&&(o.unit_raw===null||str(o.unit_raw));};
    var asset=function(a){return obj(a)&&(a.observation?observation(a.observation):obj(a.row)&&['name','when','src','val'].every(function(k){return str(a.row[k]);}));};
    var point=function(p){return obj(p)&&str(p.tp)&&str(p.raw)&&str(p.unit)&&
      ['exact','missing','numeric','typed','oldNumeric'].every(function(k){return typeof p[k]==='boolean';})&&
      (p.v===null||Number.isFinite(p.v))&&(!p.exact||Number.isFinite(p.v));};
    var presentation=function(s){return obj(s)&&strings(s.reasons)&&str(s.kind)&&str(s.unit)&&
      ['connect','mixed','noNumericScale','ambiguous','oldPlot'].every(function(k){return typeof s[k]==='boolean';})&&
      Array.isArray(s.extent)&&s.extent.length===2&&s.extent.every(function(v){return v===null||Number.isFinite(v);});};
    var historical=['observation','versions'].includes(view);
    if(r.view!==view||!['summary','rows','metrics','series','observation','versions'].includes(view)||!str(r.version)||!r.version||
       !nat(r.scope.source_seq)||r.scope.kind!==(historical?'exact-formal-history':'committed-current-visible'))fail('DATA_RESPONSE_INVALID');
    if(view==='observation'){
      var m=r.metadata,oid=q.get('oid'),revision=q.get('revision');
      if(typeof r.found!=='boolean'||!obj(m)||m.found!==r.found||m.observation_id!==oid||
         (revision&&m.revision!==Number(revision)))fail('DATA_RESPONSE_INVALID');
      if(r.found){
        if(!positive(m.revision)||!positive(m.latest_revision)||m.latest_revision<m.revision||
           !['ACTIVE','RETRACTED'].includes(m.latest_status)||typeof m.superseded!=='boolean'||
           m.superseded!==(m.revision!==m.latest_revision)||!observation(r.observation)||
           r.observation.ref!==oid+'@'+m.revision)fail('DATA_RESPONSE_INVALID');
      }else if(r.observation!==null||!str(m.reason))fail('DATA_RESPONSE_INVALID');
      return;
    }
    if(!nat(r.total))fail('DATA_RESPONSE_INVALID');
    if(view==='summary'){
      if(!obj(r.counts)||!Object.values(r.counts).every(nat)||Object.values(r.counts).reduce(function(a,b){return a+b;},0)!==r.total)fail('DATA_RESPONSE_INVALID');
      return;
    }
    if(!nat(r.offset)||!positive(r.limit)||r.limit>200||!Array.isArray(r.items)||
       r.items.length!==Math.max(0,Math.min(r.limit,r.total-r.offset))||typeof r.has_more!=='boolean'||r.has_more!==(r.offset+r.limit<r.total)||
       (r.has_more?!(str(r.next_cursor)&&r.next_cursor):r.next_cursor!==null)||
       (r.offset?!(str(r.previous_cursor)&&r.previous_cursor):r.previous_cursor!==null))fail('DATA_RESPONSE_INVALID');
    if(view==='rows'&&!r.items.every(asset))fail('DATA_RESPONSE_INVALID');
    if(view==='metrics'&&!r.items.every(function(m){return obj(m)&&str(m.code)&&positive(m.count)&&asset(m.last)&&presentation(m.series)&&Array.isArray(m.series.points)&&m.series.points.length<=30&&m.series.points.every(point);}))fail('DATA_RESPONSE_INVALID');
    if(view==='series'&&(!presentation(r.presentation)||!r.items.every(point)))fail('DATA_RESPONSE_INVALID');
    if(view==='versions'&&((r.total? !positive(r.current_revision):r.current_revision!==null)||!r.items.every(function(v){return obj(v)&&positive(v.revision)&&v.revision<=r.current_revision&&['ACTIVE','RETRACTED'].includes(v.status)&&Array.isArray(v.runs)&&strings(v.cards)&&str(v.saved_at);})))fail('DATA_RESPONSE_INVALID');
  };
  LIVE.dataObservation=function(t){
    if(t.mode==='receipt'&&t.obs)return t.obs;
    var ref=String(t.ref||''),split=ref.lastIndexOf('@');
    var r=readCached(LIVE.dataPath('observation',{oid:ref.slice(0,split),revision:ref.slice(split+1)}));
    LIVE.validateDataRead(r,LIVE.dataPath('observation',{oid:ref.slice(0,split),revision:ref.slice(split+1)}));
    t._dataMetadata=r.metadata;
    return r.observation;
  };
  function dataAsset(item){
    var o=item.observation;
    return o?{name:o.label_zh,when:o.tp||'时间未知',src:C.srcText(o),ref:o.ref,ver:+o.ref.split('@')[1],observation:o,
      val:human(o.code,o.value_raw,o.unit_raw,o.comparator)}:item.row;
  }
  function dataSequence(presentation,points,code){
    var s=Object.assign({},presentation,{points:points});
    s.note=s.reasons.length?CHART_REASON[s.reasons[0]]:'';
    s.explanation=s.reasons.map(function(r){return r==='qualified_numeric_result'?'结果为范围表达，无法确定精确读数。':CHART_REASON[r];}).join('；')+(s.connect&&s.reasons.includes('unknown_method')?'；连线仅表示观测顺序，方法可比性未确认':'');
    s.points=points.map(function(p){return Object.assign({},p,{display:human(code,p.raw,p.unit,p.comparator)});});
    return s;
  }
  LIVE.renderDataPage=function(){
    wall3Css();metricCss();
    var st=C.st,esc=C.esc,ic=C.ic,category=st.assetF||'ALL',mode=st.dataView||'code';
    var scope=JSON.stringify([st.key,category,st.dataSources||[],st.dataFrom||'',st.dataTo||'']);
    var state=st._dataPages;
    if(!state||state.scope!==scope)state=st._dataPages={scope:scope,slots:{}};
    if(state.code!==st.dataCode){state.code=st.dataCode;delete state.slots.rows;delete state.slots.series;}
    var filters={category:category,sources:(st.dataSources||[]).join(','),code:st.dataCode,from:st.dataFrom,to:st.dataTo};
    var session=LIVE._dataReadSession||(LIVE._dataReadSession=new window.PTDSDataReadSession());
    var read=session.reader(LIVE.dataPath,LIVE.validateDataRead,readCached);
    return session.present({key:JSON.stringify([C.S().instance.instance_id,scope,mode,st.dataCode||'',session.paths(LIVE.dataPath,state,filters,st.dataCode,mode)]),route:LIVE.refreshRoute(),epoch:readEpoch,blocked:pendingWrites,host:document.getElementById('view'),entry:function(p){return viewReads.get(p);},current:function(c){return c.epoch===readEpoch&&!pendingWrites&&c.route===LIVE.refreshRoute()&&LIVE.dataRoute();},retry:function(){C.render();}},session.paths(LIVE.dataPath,state,filters,st.dataCode,mode),readCached,LIVE.validateDataRead,function(){
    var summary=read('summary');
    var page=function(view,slot,limit){
      var p=state.slots[slot]||(state.slots[slot]={cursor:null});
      var result=read(view,Object.assign({},filters,{limit:limit,cursor:p.cursor}));
      if(result.version!==summary.version){var e=new Error('DATA_VIEW_CHANGED');e.code='DATA_VIEW_CHANGED';e.viewPending=true;e.path=LIVE.dataPath(view,Object.assign({},filters,{limit:limit,cursor:p.cursor}));throw e;}
      p.result=result;return result;
    };
    var rows,series,metrics,body='',head=C.pgh('我的数据','')+'<div class="chips" role="group" aria-label="怎么看" data-ptds-ui-aria-label="scd6224591fad">'+
      '<button class="chip" data-dv="code" aria-pressed="'+(mode==='code')+'">按指标</button><button class="chip" data-dv="time" aria-pressed="'+(mode==='time')+'">按时间</button><span class="sub2">·</span>'+
      '<button class="chip" data-af="ALL" aria-pressed="'+(category==='ALL')+'">全部 '+summary.total+'条</button>'+
      ['wearable','file','phone','manual'].filter(function(g){return summary.counts[g];}).map(function(g){return '<button class="chip" data-af="'+g+'" aria-pressed="'+(category===g)+'">'+GZH[g]+' '+summary.counts[g]+'条</button>';}).join('')+
      '<button class="chip" id="data-muse" data-ptds-ui="sdd4a36e5ad4d">Muse 会话</button><button class="link" id="data-reload" data-ptds-ui="reread">重新读取</button></div>';
    if(st.dataSources&&st.dataSources.length)head+='<p class="sub2" data-ptds-inline><!--ptds-ui:s6181ed6f9734-->来源：<!--/ptds-ui-->'+st.dataSources.map(esc).join('、')+' <button class="link" id="data-source-clear" data-ptds-ui="sae65e7db20c7">显示所有来源</button></p>';
    if(st.dataFrom||st.dataTo)head+='<p class="sub2">日期范围：'+esc(st.dataFrom||'不限')+' 至 '+esc(st.dataTo||'不限')+' <button class="link" id="data-range-clear" data-ptds-ui="s2328f69c3f74">显示全部日期</button></p>';
    var pager=function(r,slot){return r.total>r.limit?'<div class="opts"><button class="chip" data-page-prev="'+slot+'"'+(!r.previous_cursor?' disabled':'')+'>较新</button><span class="sub2">第 '+(Math.floor(r.offset/r.limit)+1)+' / '+Math.ceil(r.total/r.limit)+' 页</span><button class="chip" data-page-next="'+slot+'"'+(!r.has_more?' disabled':'')+'>较早</button></div>':'';};
    var rowHtml=function(item,detail){var r=dataAsset(item),isGene=!r.ref&&r.g==='file'&&r.name==='基因测序数据',geneName=isGene?' data-gene-row-name':'',sourceMark=isGene?' data-gene-row-source':(r.observation?.source_kind==='SYNTHETIC'?' data-gene-row-synthetic':''),tag=r.ver>1?' <span class="tag">第 '+r.ver+' 版</span>':'';
      if(detail)return r.ref?'<button class="lrow c6" data-ref="'+esc(r.ref)+'"><span>'+metricValueHtml(r.observation,r.val)+tag+'</span><span>'+esc(r.when)+'</span><span class="sub2"'+sourceMark+'>'+esc(r.src)+'</span><span class="sub2">'+ic('chevron-right')+'</span></button>':'<div class="lrow c6"><span>'+esc(r.val)+'</span><span>'+esc(r.when)+'</span><span class="sub2"'+sourceMark+'>'+esc(r.src)+'</span><span></span></div>';
      return r.ref?'<button class="lrow c6" data-ref="'+esc(r.ref)+'"><span data-ui-metric="'+esc(r.observation.code)+'">'+esc(humanLabel(r.name))+tag+'</span><span>'+esc(r.val)+'</span><span>'+esc(r.when)+'</span><span class="sub2"'+sourceMark+'>'+esc(r.src)+'</span><span class="sub2">'+ic('chevron-right')+'</span></button>':'<div class="lrow c6"><span'+geneName+'>'+esc(r.name)+'</span><span>'+esc(r.val)+'</span><span>'+esc(r.when)+'</span><span class="sub2"'+sourceMark+(r.sem?' data-sem="'+esc(r.sem)+'"':'')+'>'+esc(r.src)+'</span><span></span></div>';};
    if(st.dataCode){
      rows=page('rows','rows',50);series=page('series','series',200);
      var seq=dataSequence(series.presentation,series.items,st.dataCode),pts=seq.points;
      var name=C.DICT[st.dataCode]&&C.DICT[st.dataCode].zh||st.dataCode;
      body='<section class="box ebox" data-metric-ux="history" data-cmp="T16" data-sem="SEM-03"><h3><button class="link" id="dc-back">'+ic('chevron-left')+'全部指标</button><span class="grow"></span><span class="sub2">'+rows.total+' 条</span></h3><div class="hv">'+esc(humanLabel(name))+(!seq.oldPlot?'<span class="mx-inline">'+(pts.length===1&&pts[0].exact?'<i></i>':'')+esc(seq.note)+'</span>':'')+'</div>'+
        '<div class="opts"><label>起始日期 <input class="inp" type="date" id="data-from" value="'+esc(st.dataFrom||'')+'"></label><label>结束日期 <input class="inp" type="date" id="data-to" value="'+esc(st.dataTo||'')+'"></label><button class="chip" id="data-range" data-ptds-ui="sa9c1deca85be">查看范围</button><button class="link" id="data-range-all" data-ptds-ui="s2e2479f8f842">浏览全部历史</button></div>'+
        (seq.oldPlot?metricPlot(seq,true):'')+
        '<div class="sub2 ends"><span>'+esc(pts.length?String(pts[0].tp).slice(0,10):'')+'</span><span>当前第 '+(series.total?Math.max(1,series.total-series.offset-series.items.length+1):0)+'–'+Math.max(0,series.total-series.offset)+' 条／共 '+series.total+' 条 · 分段完整展示</span><span>'+esc(pts.length?String(pts[pts.length-1].tp).slice(0,10):'')+'</span></div>'+pager(series,'series')+
        '<div class="lrow c6 hd"><span data-ptds-ui="scda1d55c5231">值</span><span data-ptds-ui="s9b6e85289091">时点</span><span data-ptds-ui="sa488e93d69cc">来源</span><span></span></div>'+rows.items.map(function(r){return rowHtml(r,true);}).join('')+pager(rows,'rows')+'</section>';
    }else if(mode==='code'){
      metrics=page('metrics','metrics',50);
      body='<section class="box" data-metric-ux="list" data-cmp="T16" data-sem="SEM-03"><div class="dcode hd"><span>指标 '+metrics.total+' 项</span><span data-ptds-ui="s569af1a47dbd">最新</span><span class="hs" data-ptds-ui="s95163cedc319">趋势 · 按观测顺序</span><span class="hs" data-ptds-ui="s327ba0c4a42b">条数 · 最近</span><span></span></div>'+
        metrics.items.map(function(m){var r=dataAsset(m.last),seq=dataSequence(m.series,m.series.points,m.code);return '<button class="dcode" data-dcode="'+esc(m.code)+'"><span class="mx-name">'+esc(humanLabel(r.name))+'</span><span>'+metricValueHtml(r.observation,r.val)+'</span><span class="hs">'+metricMini(seq)+'</span><span class="sub2 hs" data-partner-row-count>'+m.count+' 条 · '+esc(String(r.when).slice(0,10))+'</span><span>'+ic('chevron-right')+'</span></button>';}).join('')+
        (!metrics.total?'<p class="sub2" data-ptds-ui="s4a5a256833d0">还没有数据。</p>':'')+pager(metrics,'metrics')+'</section>';
    }else{
      rows=page('rows','rows',50);
      body='<section class="box"><div class="lrow c6 hd"><span data-ptds-ui="sd44e9b3d3b31">名称</span><span data-ptds-ui="scda1d55c5231">值</span><span data-ptds-ui="s9b6e85289091">时点</span><span data-ptds-ui="sa488e93d69cc">来源</span><span></span></div>'+rows.items.map(function(r){return rowHtml(r,false);}).join('')+(!rows.total?'<p class="sub2" data-ptds-ui="s4a5a256833d0">还没有数据。</p>':'')+pager(rows,'rows')+'</section>';
    }
    var host=document.getElementById('view');
    host.innerHTML='<div data-data-root data-owner="'+esc(st.key)+'" data-instance="'+esc(C.S().instance.instance_id)+'">'+head+body+'<p class="sub2" data-ptds-ui="s3d21d3e46192">每条都可以更正或删除，历史版本保留。</p></div>';
    host.dataset.dataOwner=st.key;host.dataset.dataScope=scope;host.dataset.dataCode=st.dataCode||'';host.dataset.dataView=mode;
    var redraw=function(){C.render();};
    host.querySelectorAll('[data-dv]').forEach(function(b){b.onclick=function(){st.dataView=b.dataset.dv;st.dataCode=null;redraw();};});
    host.querySelectorAll('[data-af]').forEach(function(b){b.onclick=function(){st.assetF=b.dataset.af;redraw();};});
    host.querySelectorAll('[data-dcode]').forEach(function(b){b.onclick=function(){state.catalogScroll=window.scrollY;st.dataCode=b.dataset.dcode;redraw();window.scrollTo(0,0);};});
    host.querySelectorAll('[data-ref]').forEach(function(b){b.onclick=function(){state.scroll=window.scrollY;C.openTorchDetail(b.dataset.ref,'data');};});
    host.querySelectorAll('[data-page-prev],[data-page-next]').forEach(function(b){b.onclick=function(){var next=b.hasAttribute('data-page-next'),slot=next?b.dataset.pageNext:b.dataset.pagePrev,p=state.slots[slot];p.cursor=next?p.result.next_cursor:p.result.previous_cursor;redraw();};});
    var bind=function(id,fn){var b=document.getElementById(id);if(b)b.onclick=fn;};
    bind('data-reload',function(){LIVE.invalidateData();redraw();});
    bind('dc-back',function(){st.dataCode=null;var active=st._dataPages||state;active.restoreCatalog=true;active.catalogScroll=state.catalogScroll;redraw();});
    bind('data-source-clear',function(){st.dataSources=null;redraw();});
    bind('data-muse',function(){st.srcGroup='wearable';st.museOpen=true;C.goTorch('srcgroup');});
    bind('data-range',function(){st.dataFrom=document.getElementById('data-from').value;st.dataTo=document.getElementById('data-to').value;redraw();});
    bind('data-range-all',function(){st.dataFrom='';st.dataTo='';redraw();});
    bind('data-range-clear',function(){st.dataFrom='';st.dataTo='';redraw();});
    if(state.restoreCatalog){state.restoreCatalog=false;window.scrollTo(0,state.catalogScroll||0);}
    if(state.restoreScroll){state.restoreScroll=false;window.scrollTo(0,state.scroll||0);}
    });};
  /* DATA_READ_R01_END */

  LIVE.renderAssets = function () {
    if(LIVE.dataReadEnabled&&LIVE.dataReadEnabled()&&!C.isReplay())return LIVE.renderDataPage();
    wall3Css(); metricCss();
    var esc = C.esc, ic = C.ic, st = C.st, S = C.S(), rows = C.torchRows(), f = st.assetF || 'ALL', view = st.dataView || 'code', PAGE = 50;
    var cnt = { wearable: 0, file: 0, phone: 0, manual: 0 }; rows.forEach(function (r) { cnt[r.g] = (cnt[r.g] || 0) + 1; });
    var shown = rows.filter(function (r) { return f === 'ALL' || r.g === f; }), tl = {};
    (S.timeline || []).forEach(function (o) { tl[o.ref] = o; });
    if(st.dataSources&&st.dataSources.length)shown=shown.filter(function(r){var o=tl[r.ref];return o&&st.dataSources.includes(o.source_kind);});
    var val = function (r) { var o = r.ref && tl[r.ref]; return o ? human(o.code, o.value_raw, o.unit_raw, o.comparator) : r.val; };
    var valueHtml = function (r) { return metricValueHtml(r.ref && tl[r.ref], r.val); };
    var verTag = function (r) { return r.ver > 1 ? ' <span class="tag">第 ' + r.ver + ' 版</span>' : ''; };
    var head = C.pgh('我的数据', '') + '<div class="chips" role="group" aria-label="怎么看" data-ptds-ui-aria-label="scd6224591fad"><button class="chip" data-dv="code" aria-pressed="' + (view === 'code') + '">按指标</button><button class="chip" data-dv="time" aria-pressed="' + (view === 'time') + '">按时间</button>' +
      '<span class="sub2" style="margin:0 var(--primitive-space-2)">·</span><button class="chip mx-filter" data-af="ALL" aria-pressed="' + (f === 'ALL') + '">全部 ' + rows.length + '<span class="mx-count-unit" data-ptds-ui="sf004f1d84cf9">条</span></button>' +
      ['wearable', 'file', 'phone', 'manual'].filter(function (g) { return cnt[g]; }).map(function (g) { return '<button class="chip mx-filter" data-af="' + g + '" aria-pressed="' + (f === g) + '">' + GZH[g] + ' ' + cnt[g] + '<span class="mx-count-unit" data-ptds-ui="sf004f1d84cf9">条</span></button>'; }).join('') + '<button class="chip" id="data-muse" data-ptds-ui="sdd4a36e5ad4d">Muse 会话</button></div>';
    if(st.dataSources&&st.dataSources.length)head+='<p class="sub2" data-ptds-inline><!--ptds-ui:s6181ed6f9734-->来源：<!--/ptds-ui-->'+st.dataSources.map(esc).join('、')+' <button class="link" id="data-source-clear" data-ptds-ui="sae65e7db20c7">显示所有来源</button></p>';
    var body = '';
    if (st.dataCode) {  /* 一个指标的全部历史 */
      var mine = shown.filter(function (r) { var o = r.ref && tl[r.ref]; return o ? o.code === st.dataCode : r.name === st.dataCode; }).sort(function (a, b) { return a.when < b.when ? 1 : a.when > b.when ? -1 : 0; });
      var nm = mine[0] ? humanLabel(mine[0].name) : st.dataCode;
      var seq = metricSequence(mine, tl), pts = seq.points;
      var cut = st.dataAll ? mine.length : 10;
      body = '<section class="box ebox" data-metric-ux="history" data-cmp="T16" data-sem="SEM-03"><h3><button class="link" id="dc-back">' + ic('chevron-left') + '全部指标</button><span class="grow"></span><span class="sub2">' + mine.length + ' 条</span></h3><div class="hv">' + esc(nm) + (!seq.oldPlot ? '<span class="mx-inline">' + (pts.length === 1 && pts[0].exact ? '<i></i>' : '') + esc(seq.note) + '</span>' : '') + '</div>' + (seq.oldPlot ? metricPlot(seq, true) : '') +
        (pts.length > 1 ? '<div class="sub2 ends"><span>' + esc(String(pts[0].tp).slice(0, 10)) + '</span><span class="mx-order" data-ptds-inline><!--ptds-ui:sc8b019c0f724-->按观测顺序<!--/ptds-ui-->' + (seq.note ? ' · ' + esc(seq.note) : '') + '</span><span>' + esc(String(pts[pts.length - 1].tp).slice(0, 10)) + '</span></div>' : '') +
        '<div class="lrow c6 hd"><span data-ptds-ui="scda1d55c5231">值</span><span data-ptds-ui="s9b6e85289091">时点</span><span data-ptds-ui="sa488e93d69cc">来源</span><span></span></div>' + mine.slice(0, cut).map(function (r) {
          return r.ref ? '<button class="lrow c6" data-ref="' + esc(r.ref) + '"><span>' + valueHtml(r) + verTag(r) + '</span><span>' + esc(r.when) + '</span><span class="sub2">' + esc(r.src) + '</span><span class="sub2">' + ic('chevron-right') + '</span></button>'
            : '<div class="lrow c6"><span>' + esc(r.val) + '</span><span>' + esc(r.when) + '</span><span class="sub2">' + esc(r.src) + '</span><span></span></div>'; }).join('') +
        (mine.length > 10 ? '<div class="opts"><button class="chip" id="dc-all">' + (st.dataAll ? '只看最近 10 条' : '查看全部 ' + mine.length + ' 条') + '</button></div>' : '') + '</section>';
    } else if (view === 'code') {
      var by = {}, keys = [];
      shown.forEach(function (r) { var o = r.ref && tl[r.ref], k = o ? o.code : r.name; if (!by[k]) { by[k] = []; keys.push(k); } by[k].push(r); });
      var lines = keys.map(function (k) {
        var list = by[k].slice().sort(function (a, b) { return a.when < b.when ? -1 : a.when > b.when ? 1 : 0; }), last = list[list.length - 1];
        return { k: k, last: last, n: list.length, seq: metricSequence(list, tl, 30) };
      }).sort(function (a, b) { return a.last.when < b.last.when ? 1 : a.last.when > b.last.when ? -1 : humanLabel(a.last.name) < humanLabel(b.last.name) ? -1 : 1; });
      body = '<section class="box" data-metric-ux="list" data-cmp="T16" data-sem="SEM-03"><div class="dcode hd"><span data-ptds-inline><!--ptds-ui:sb87e67c7dae0-->指标 <!--/ptds-ui--><span class="mx-order">' + lines.length + ' 项</span></span><span data-ptds-ui="s569af1a47dbd">最新</span><span class="hs" data-ptds-inline><!--ptds-ui:s9b59e637c838-->趋势 <!--/ptds-ui--><span class="mx-order" data-ptds-ui="s26afb2226e94">· 按观测顺序</span></span><span class="hs" data-ptds-ui="s327ba0c4a42b">条数 · 最近</span><span></span></div>' +
        (lines.length ? lines.map(function (l) {
          return '<button class="dcode" data-dcode="' + esc(l.k) + '"><span class="mx-name">' + esc(humanLabel(l.last.name)) + '</span><span>' + valueHtml(l.last) + '</span><span class="hs">' + metricMini(l.seq) + '</span><span class="sub2 hs"><span class="mx-count">' + l.n + ' 条</span> · <span class="mx-date">' + esc(String(l.last.when).slice(0, 10)) + '</span>' + '</span><span class="sub2">' + ic('chevron-right') + '</span></button>'; }).join('')
          : '<div class="sub2" data-ptds-ui="s4a5a256833d0">还没有数据。</div>') + '</section>';
    } else {
      var all = shown.slice().sort(function (a, b) { return a.when < b.when ? 1 : a.when > b.when ? -1 : 0; }), pages = Math.max(1, Math.ceil(all.length / PAGE)), pg = Math.min(st.dataPage || 0, pages - 1);
      body = '<section class="box" data-cmp="T16" data-sem="SEM-03"><div class="lrow c6 hd"><span data-ptds-ui="sd44e9b3d3b31">名称</span><span data-ptds-ui="scda1d55c5231">值</span><span data-ptds-ui="s9b6e85289091">时点</span><span data-ptds-ui="sa488e93d69cc">来源</span><span></span></div>' +
        all.slice(pg * PAGE, pg * PAGE + PAGE).map(function (r) {
          return r.ref ? '<button class="lrow c6" data-ref="' + esc(r.ref) + '"><span>' + esc(humanLabel(r.name)) + verTag(r) + '</span><span>' + esc(val(r)) + '</span><span>' + esc(r.when) + '</span><span class="sub2">' + esc(r.src) + '</span><span class="sub2">' + ic('chevron-right') + '</span></button>'
            : '<div class="lrow c6"><span>' + esc(r.name) + '</span><span>' + esc(r.val) + '</span><span>' + esc(r.when) + '</span><span class="sub2"' + (r.sem ? ' data-sem="' + r.sem + '"' : '') + '>' + esc(r.src) + '</span><span></span></div>'; }).join('') +
        (pages > 1 ? '<div class="opts"><button class="chip" id="dp-prev"' + (pg ? '' : ' disabled') + '>' + ic('chevron-left') + '较新</button><span class="sub2">第 ' + (pg + 1) + ' / ' + pages + ' 页</span><button class="chip" id="dp-next"' + (pg < pages - 1 ? '' : ' disabled') + '>较早' + ic('chevron-right') + '</button></div>' : '') + '</section>';
    }
    var assetHtml = head + body + '<div class="sub2" style="display: flex; gap: var(--primitive-space-2); align-items: center; flex-wrap: wrap" data-ptds-inline><!--ptds-ui:s4562fa26745e-->每条都可以更正或删除，历史版本保留。多版本历史 <!--/ptds-ui-->' + C.mtag('dev') + '</div>';
    if(!LIVE._incrementalMain||!LIVE.patchDataList(document.getElementById('view'),assetHtml))document.getElementById('view').innerHTML=assetHtml;
    var rr = function () { C.render(); };
    document.querySelectorAll('[data-dv]').forEach(function (b) { b.onclick = function () { st.dataView = b.dataset.dv; st.dataCode = null; st.dataPage = 0; rr(); }; });
    document.querySelectorAll('[data-af]').forEach(function (b) { b.onclick = function () { st.assetF = b.dataset.af; st.dataPage = 0; rr(); }; });
    document.querySelectorAll('[data-dcode]').forEach(function (b) { b.onclick = function () { st.dataCode = b.dataset.dcode; st.dataAll = false; rr(); window.scrollTo(0, 0); }; });
    document.querySelectorAll('[data-ref]').forEach(function (b) { b.onclick = function () { C.openTorchDetail(b.dataset.ref, 'data'); }; });
    var g = function (id, fn) { var el = document.getElementById(id); if (el) el.onclick = LIVE.action(fn); };
    g('data-muse', function () { st.srcGroup = 'wearable'; st.museOpen = true; C.goTorch('srcgroup'); });
    g('data-source-clear',function(){st.dataSources=null;rr();});
    g('dc-back', function () { st.dataCode = null; st.dataAll = false; rr(); });
    g('dc-all', function () { st.dataAll = !st.dataAll; rr(); });
    g('dp-prev', function () { st.dataPage = Math.max(0, (st.dataPage || 0) - 1); rr(); window.scrollTo(0, 0); });
    g('dp-next', function () { st.dataPage = (st.dataPage || 0) + 1; rr(); window.scrollTo(0, 0); });
  };
  LIVE.pageState = function () { return C && C.st; };
  /* 启动页两张卡（产品负责人 界面批注 2026-10-13）：结构完全一样；sJIA 卡只有真有真实数据时才写"真实数据" */
  var LAUNCH = {
    REAL: { tag: '个人可信数据基座', name: '个人可信数据基座专项演示',
      note: '个人数据的处理加工分析都在本机完成，原始数据未经授权绝不出域。',
      star: [['卡点', '人们对健康、长寿和自身状态越来越关注，而个人健康数据散落在设备、报告和各类 App 里，自己难以掌握，也难以被可信地使用。'],
        ['目标', '让个人掌握自己的数据：提供一个完全本地化的选项，从归集、清洗、加工到分析解释都在本机完成，用于关注自身状态。'],
        ['行动', '纳管作者本人完全真实的部分生理数据，包括可穿戴设备、基因测序数据、体检报告等；数据的来源、版本和授权全程留痕。'],
        ['结果', '在个人端实现生理与健康数据的“大一统”，形成可用于长寿、恢复、睡眠、运动、炎症等状态参考的专项状态矩阵与解释分析。']] }
  };
  /* r66（产品负责人 2026-10-15）：首页文字从本机进程取（默认 + 齿轮改过的），取不到用上面写死的默认 */
  LIVE.home = function (fresh) {
    var fixed = window.PTDS_TRIAL_UI && window.PTDS_TRIAL_UI.defaultHome(); if (fixed) return fixed; if (!fresh && LIVE._home) return LIVE._home;
    try { LIVE._home = readCached('/api/home'); } catch (err) { if(err&&(err.viewPending||err.code==='VIEW_CHANGED'))throw err; LIVE._home = LIVE._home || { title: '从关注一个状态，到关注人的一生', cards: {} }; }
    return LIVE._home;
  };
  LIVE.homeTitle = function () { return LIVE.home().title; };
  LIVE.launchText = function (k, kind) {
    var h = (LIVE.home().cards || {})[k]; if (h) return { tag: h.tag, name: h.name, note: h.note, star: h.rows };
    return LAUNCH[kind] || {};
  };
  LIVE.instTag = function (k) { var i = (C.SNAPS[k] || {}).instance || {}; return LIVE.launchText(k, i.kind).tag || i.display_name; };
  LIVE.launchName = function (inst) { var k = Object.keys(C.SNAPS).filter(function (x) { return C.SNAPS[x].instance && C.SNAPS[x].instance.instance_id === inst.instance_id; })[0]; return LIVE.launchText(k, inst.kind).name || inst.display_name; };
  LIVE.launchCard = function (k, snap) {
    var i = snap.instance, real = i.kind === 'REAL', L = LIVE.launchText(k, i.kind), esc = C.esc;
    var hasReal = (snap.timeline || []).some(function (o) { return o.nature === 'REAL'; });
    var data = real ? '' : hasReal ? '基于罕见病黑客松真实数据。' : '';
    return '<div class="icard' + (real ? ' real' : '') + '" data-cmp="B02" data-sem="SEM-09"><span class="inst' + (real ? ' real' : '') + '" style="justify-self: start">' +
      (real ? '<span class="solid-dot"></span>' : C.ic('eye')) + esc(L.tag) + '</span><div class="nm">' + esc(L.name) + '</div>' +
      '<div class="sub2">' + esc(data + L.note) + '</div><dl class="star">' + L.star.map(function (x) { return '<dt>' + esc(x[0]) + '</dt><dd>' + esc(x[1]) + '</dd>'; }).join('') + '</dl>' +
      '<div><button class="chip" data-launch="' + esc(k) + '" aria-label="打开' + esc(L.name) + '">' + C.ic('external-link') + '打开</button></div>' +
      '<button class="hgear" data-hedit="' + esc(k) + '" title="编辑这张卡的文字" aria-label="编辑这张卡的文字">' + C.ic('settings') + '</button></div>';
  };
  /* 首页齿轮：大标题、每张卡都能改；保存 = 本机追加一条，恢复默认也是追加一条（home_texts.jsonl） */
  var HOME_CSS = '.icards{display:grid!important;grid-template-columns:repeat(3,minmax(0,1fr));gap:24px!important;width:min(1760px,calc(100vw - 96px));margin:0 auto}@media (max-width:1100px){.icards{grid-template-columns:minmax(0,1fr)}}' +
    '.icard{width:auto!important;position:relative;padding:30px 32px!important}.icard .nm{font-size:30px!important}.icard .sub2{font-size:16px!important;line-height:1.7}.icard dl.star{font-size:16px!important;line-height:1.7}' +
    '.hgear,.tgear{background:none;border:0;color:var(--theme-text-tertiary);display:inline-flex;align-items:center;justify-content:center;width:32px;height:32px;border-radius:8px;cursor:pointer;font-size:17px}.hgear{position:absolute;top:16px;right:16px}.tgear{vertical-align:middle;margin-left:10px;font-size:18px}.hgear:hover,.tgear:hover{color:var(--theme-text-primary);background:color-mix(in srgb,var(--theme-text-primary) 8%,transparent)}' +
    '.hed{position:fixed;inset:0;background:rgba(0,0,0,.35);display:flex;align-items:center;justify-content:center;z-index:3000}.hed .bx{width:620px;max-width:calc(100vw - 32px);max-height:88vh;overflow:auto;background:var(--theme-surface-raised);color:var(--theme-text-primary);border-radius:14px;padding:22px 24px;border:var(--primitive-border-hairline) solid var(--theme-line-control);box-shadow:0 20px 50px rgba(0,0,0,.3)}' +
    '.hed h3{margin:0 0 4px}.hed label{display:block;font-size:var(--scale-type-meta);color:var(--theme-text-secondary);margin:12px 0 4px}.hed .inp{width:100%;box-sizing:border-box}.hed textarea.inp{min-height:58px;padding:8px 10px;font:inherit;resize:vertical}.hed .row{display:flex;gap:10px;margin-top:18px;align-items:center}.hed .err{color:#E5675F;margin-top:8px}' +
    '#inst .ret{color:var(--theme-text-tertiary);font-weight:400}' +
    /* r67（产品负责人 2026-10-15）：三个模块那行放大；英文 / 中文口号挪到卡片下方居中、放大，颜色沿用页面原来的文字色 */
    /* r68（产品负责人 2026-10-15 批准）：首页上下间距均匀；卡片正文行高 1.7，四行之间留白，三张卡等高、“打开”对齐在底部 */
    '.launch .slogan{margin:0 0 6px!important}.launch .subname{margin:0}.launch .modules{margin:18px 0 22px!important}.launch .icards{margin-top:0!important;align-items:stretch}' +
    '.icard{display:flex!important;flex-direction:column;gap:10px}.icard>.inst{align-self:flex-start}.icard .nm{margin:2px 0 0}.icard dl.star{line-height:1.7!important;row-gap:8px;margin:2px 0 0}.icard dl.star dt,.icard dl.star dd{margin-top:0;margin-bottom:0}.icard>div:last-of-type{margin-top:auto}' +
    '.launch .modules{font-size:20px;gap:32px}.launch .modules .mi{width:1.25em;height:1.25em;font-size:inherit}' +
    '.launch .tagline.below{margin:32px auto 0;text-align:center;line-height:1.5}.launch .tagline.below .en{display:block;font-size:26px}.launch .tagline.below .zh{display:block;font-size:24px}';
  LIVE.homeMount = function () {
    if (!document.getElementById('home-css')) { var s0 = document.createElement('style'); s0.id = 'home-css'; s0.textContent = HOME_CSS; document.head.appendChild(s0); }
    var tg = document.querySelector('.launch .tagline'), cards = document.querySelector('.launch .icards'); if(window.PTDS_HOME_LAYOUT)window.PTDS_HOME_LAYOUT.filter(cards,C.st.key);
    if (tg && cards && !tg.classList.contains('below')) {
      var parts = tg.innerHTML.split(/<br\s*\/?>/i);
      tg.innerHTML = '<span class="en">' + (parts[0] || '') + '</span><span class="zh">' + (parts[1] || '') + '</span>';
      tg.classList.add('below'); cards.parentNode.insertBefore(tg, cards.nextSibling);
    }
    var t = document.getElementById('home-title');
    if (t && !document.getElementById('home-tgear')) { var g = document.createElement('button'); g.className = 'tgear'; g.id = 'home-tgear'; g.title = '编辑首页大标题'; g.setAttribute('aria-label', '编辑首页大标题'); g.innerHTML = C.ic('settings'); t.parentNode.insertBefore(g, t.nextSibling); g.onclick = function (e) { e.stopPropagation(); LIVE.homeEdit('title'); }; }
    document.querySelectorAll('[data-hedit]').forEach(function (b) { b.onclick = function (e) { e.stopPropagation(); LIVE.homeEdit(b.dataset.hedit); }; });
  };
  LIVE.homeEdit = function (target) {
    var esc = C.esc, H = LIVE.home(true), old = document.querySelector('.hed'); if (old) old.remove();
    var f = function (id, l, v, ta) { return '<label for="he-' + id + '">' + esc(l) + '</label>' + (ta ? '<textarea class="inp" id="he-' + id + '">' + esc(v) + '</textarea>' : '<input class="inp" id="he-' + id + '" value="' + esc(v) + '">'); };
    var c = target === 'title' ? null : H.cards[target], body;
    if (target === 'title') body = '<h3 data-ptds-ui="s5f8d72fc97c2">编辑首页大标题</h3><div class="sub2" data-ptds-ui="s5060e4cd315d">保存在本机，旧版本都留着，随时可以恢复默认。</div>' + f('title', '大标题', H.title);
    else if (c) body = '<h3 data-ptds-inline><!--ptds-ui:s2a0bdf217648-->编辑「<!--/ptds-ui-->' + esc(c.name) + '」卡片</h3><div class="sub2" data-ptds-ui="s2b7b1dd17e4d">只改首页这张卡上的文字；保存在本机，旧版本都留着，随时可以恢复默认。</div>' +
      f('tag', '顶部标签（也是进入后页面右上角的实例名）', c.tag) + f('name', '卡名', c.name) + f('note', '说明', c.note, 1) + c.rows.map(function (r, i) { return f('r' + i, r[0], r[1], 1); }).join('');
    else return;
    var el = document.createElement('div'); el.className = 'hed'; el.setAttribute('role', 'dialog'); el.setAttribute('aria-modal', 'true');
    el.innerHTML = '<div class="bx">' + body + '<div class="err" id="he-err"></div><div class="row"><button class="btn" id="he-save" data-ptds-ui="sa3030bf8f16d">保存</button><button class="btn2" id="he-cancel" data-ptds-ui="s2cd0f3be8738">取消</button><span style="flex:1"></span><button class="link" id="he-reset" data-ptds-ui="sba2e93e73037">恢复默认</button></div></div>';
    document.body.appendChild(el);
    var close = function () { el.remove(); }, v = function (id) { return document.getElementById('he-' + id).value; };
    var send = async function (b) {
      try { LIVE._home = (await call('POST', '/api/home', b)); close(); C.render(); C.toast('已保存（本机）'); }
      catch (err) { if(err&&(err.viewPending||err.code==='VIEW_CHANGED'))throw err; document.getElementById('he-err').textContent = '没存上：' + (err.detail || LIVE.saveErr(err)); }
    };
    el.onclick = function (e) { if (e.target === el) close(); };
    document.getElementById('he-cancel').onclick = LIVE.action(close);
    document.getElementById('he-reset').onclick = LIVE.action(async function () { (await send({ target: target, reset: true })); });
    document.getElementById('he-save').onclick = LIVE.action(async function () {
      if (target === 'title') return (await send({ target: 'title', text: v('title') }));
      (await send({ target: target, fields: { tag: v('tag'), name: v('name'), note: v('note'), rows: [v('r0'), v('r1'), v('r2'), v('r3')] } }));
    });
    var first = el.querySelector('.inp'); if (first) first.focus();
  };
  /* 按真实时间由近及远排（数字毫秒、ISO 时间、"2026-10-13 10:29"、只有日期的按当天中午，东八区）；排不出时间的放最后 */
  LIVE.byTime = function (rows) {
    var t = function (r) {
      if (typeof r.ts === 'number') return r.ts;
      if (r.ts) { var x = Date.parse(r.ts); if (!isNaN(x)) return x; }
      var m = /(\d{4}-\d{2}-\d{2})(?:[ T](\d{2}:\d{2}))?/.exec(String(r.when || ''));
      return m ? Date.parse(m[1] + 'T' + (m[2] || '12:00') + ':00+08:00') : -Infinity;
    };
    return rows.map(function (r, i) { return [t(r), i, r]; }).sort(function (a, b) { return b[0] - a[0] || a[1] - b[1]; }).map(function (x) { return x[2]; });
  };
  /* ---------- R08 侧栏说明（产品负责人 2026-10-14 定稿原话）和子页面切换动效 ---------- */
  var NAV_DESC = {
    'torch|guard': '最近进来了哪些数据、从哪来，每一步处理都为我留了痕',
    'torch|sources': '在这里查看我接入的可穿戴设备、体检报告、手机健康等来源',
    'torch|data': '我的每一条数据都在这里，可以查看、更正或删除，历史版本保留',
    'track|wall': '我的各项状态一眼就能看全，新数据一到自动更新',
    'track|eng': '选一个模板、绑上我的数据，搭出一组我的状态卡',
    'track|alerts': '状态有变化或有新结果时提醒我，发到哪里由我决定',
    'track|adv': '用不同的规则、不同的假设把同一份数据再算一遍，对照着看',
    'track|rules': '每个算法的出处、版本和原文链接，改规则只能发新版本',
    'cluster|overview': '我的数据现在给了谁、能看什么，一页看清',
    'cluster|objects': '我授权过的人、智能体和通道，可以随时收回',
    'cluster|records': '每一次数据离开本机都有记录：谁、什么时候、拿了什么',
    'cluster|rules': '默认怎么授权：给谁、给多少、多久失效',
    'cluster|space': '和家人、医生或研究者一起使用数据，范围由我定'
  };
  LIVE.pageDesc = function (app, id, foot) {
    if (!foot && app === 'torch' && id === 'graph' && !C.isReplay() && !document.getElementById('xh-sp')) {  /* 星痕不写子标题；「星灵解读」放页头右上 */
      var inst0 = document.getElementById('inst'); if (inst0) { var sp0 = document.createElement('span'); sp0.id = 'xh-sp'; sp0.innerHTML = LIVE.spBtn('data-sp-page="graph"'); inst0.parentNode.insertBefore(sp0, inst0); LIVE.spBind(); }
    }
    if (!foot && app === 'torch' && id === 'graph') { var title = document.querySelector('#appbar .crumb .t'); if (title) title.textContent = C.st.xhView === 'records' ? '操作记录' : '证据图谱'; }
    var w = document.querySelector('#appbar .crumbwrap'), d = !foot && NAV_DESC[app + '|' + id];
    if (!w || !d || w.querySelector('.pdesc')) return;
    var el = document.createElement('div'); el.className = 'pdesc'; el.textContent = d; w.appendChild(el);
    if (app === 'torch' && LIVE.SP_PAGES[id] && !C.isReplay()) { var sp = document.createElement('span'); sp.innerHTML = ' ' + LIVE.spBtn('data-sp-page="' + id + '"'); el.appendChild(sp.firstChild.nextSibling || sp.lastChild); LIVE.spBind(); }
  };
  /* 定时刷新会重画顶栏：把页面说明和返回补回去（产品负责人 08:47：说明文字会消失，固化下来） */
  LIVE.barAgain = function () { if (!navLast || navLast.indexOf('foot|') === 0) return; var p = navLast.split('|'); LIVE.pageDesc(p[0], p[1]); LIVE.subBack(p[0]); };
  LIVE.navDesc = function (app, id) { var d = NAV_DESC[app + '|' + id]; return d ? '<small class="nd">' + C.esc(d) + '</small>' : ''; };
  var navLast = null, barTop = null;
  /* renderSide 之后调用：同一模块内换子页面时内容轻入场（A），左侧竖条从旧位置滑到新位置（B）；换模块用原有过渡 */
  /* 产品负责人 2026-10-14 08:30：二级、三级页面统一在页头补一个“返回”，回到上一级（页面自己已有返回的不重复加） */
  /* 产品负责人 2026-10-14 09:02：右上角一个图标切换深色 / 浅色（浅色就是原有的“档案浅色”主题），记在本机浏览器 */
  var SUN = '<svg class="ic" aria-hidden="true" width="1em" height="1em" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>';
  var MOON = '<svg class="ic" aria-hidden="true" width="1em" height="1em" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9z"/></svg>';
  LIVE.themeBtn = function () {
    try { LIVE.bellMount(); } catch (err) { if(err&&(err.viewPending||err.code==='VIEW_CHANGED'))throw err; /* 铃铛只是入口，失败不影响页面 */ }
    try { LIVE.addStateMount(); } catch (err) { if(err&&(err.viewPending||err.code==='VIEW_CHANGED'))throw err; /* 「增加我的状态」入口，失败不影响卡片 */ }
    var bell = document.getElementById('bell') || document.getElementById('gear'); if (!bell || document.getElementById('theme-tog')) { if(window.PTDS_LANGUAGE)window.PTDS_LANGUAGE.mount(C); return; }  /* 没有铃铛的实例（如「我的老人」）放在齿轮前 */
    var light = document.documentElement.getAttribute('data-theme') === 'light';
    var bt = document.createElement('button'); bt.className = 'ibtn'; bt.id = 'theme-tog';
    bt.title = bt.ariaLabel = light ? '换成深色' : '换成浅色'; bt.setAttribute('aria-label', bt.title); bt.innerHTML = light ? MOON : SUN;
    bt.onclick = function () { var v = document.documentElement.getAttribute('data-theme') === 'light' ? 'dark' : 'light'; (C.setSeg || window.__ptds.setSeg)('data-theme', v); try { localStorage.setItem('ptds-theme', v); } catch (e) { if(e&&(e.viewPending||e.code==='VIEW_CHANGED'))throw e; /* 只是偏好 */ } bt.remove(); LIVE.themeBtn(); };
    bell.parentNode.insertBefore(bt, bell); if(window.PTDS_LANGUAGE)window.PTDS_LANGUAGE.mount(C);
  };
  LIVE.subBack = function (app, foot) {
    LIVE.themeBtn();
    var old = document.getElementById('sub-back-row') || document.getElementById('sub-back'); if (old) old.remove();
    if(app==='track'&&C.st.view==='vitals-card')return; // Collection already provides its own back action.
    var st = C.st, go = null;
    if (foot) return;
    if (app === 'torch') {
      if (st.tview === 'detail') go = function () { C.goTorch('data'); };
      else if (['entry', 'connect', 'gene', 'apple'].indexOf(st.tview) >= 0) go = function () { if (st.srcGroup) C.goTorch('srcgroup'); else C.goTorch('sources'); };
    } else if (app === 'cluster') {
      if (st.cview === 'edit') go = function () { window.__ptds.goCluster('objects'); };
      else if (st.cview === 'grant') go = function () { window.__ptds.goCluster('rules'); };
    } else if (['wall', 'eng', 'alerts', 'adv', 'rules'].indexOf(st.view) < 0) {
      var inCard = st.view !== 'group' && String(st.view).indexOf('ph:') !== 0;
      go = function () { if (inCard && st.group) { st.view = 'group'; C.render(); } else C.goTrack('wall'); window.scrollTo(0, 0); };
    }
    if (!go) return;
    var own = [].some.call(document.querySelectorAll('#view button'), function (x) { return x.textContent.trim() === '返回'; });
    var view = document.getElementById('view'); if (own || !view) return;
    var bt = document.createElement('button'); bt.className = 'btn2'; bt.id = 'sub-back'; bt.innerHTML = C.ic('chevron-left') + '返回';
    bt.onclick = LIVE.action(go);
    var row = document.createElement('div'); row.id = 'sub-back-row'; row.style.cssText = 'display:flex;justify-content:flex-end;width:100%;grid-column:1/-1;margin-bottom:16px';
    row.appendChild(bt); view.insertBefore(row, view.firstChild);
  };
  /* r62（产品负责人 2026-10-15 批准 r61）：侧栏全展开。一级 星炬 / 星轨 / 星簇 / 星痕，下面直接列二级，不用先点一级；星痕下设操作记录与证据图谱两个二级入口 */
  var XH_ICON = '<svg class="mi" viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M3.2 20.4c2.4-.6 4-2.2 5.2-4.4" fill="none" stroke-dasharray="1.4 2.4"/><path d="M10.2 13.2c1.4-2.2 3-3.8 5-4.8" fill="none"/><circle cx="3.2" cy="20.4" r="1.3"/><circle cx="9.2" cy="14.6" r="1.6" fill="none"/><path class="acc" d="M18.6 2.6l1.1 2.9 2.9 1.1-2.9 1.1-1.1 2.9-1.1-2.9-2.9-1.1 2.9-1.1z"/></svg>';
  var TREE_CSS = '#side .xtree{display:grid;gap:2px}#side .xtree .xmod{display:grid;grid-template-columns:auto minmax(0,1fr) auto;gap:var(--primitive-space-2);align-items:center;text-align:left;width:100%;border:0;background:transparent;padding:var(--primitive-space-2);margin-top:6px;color:var(--theme-text-primary);font:inherit;font-weight:var(--primitive-font-weight-medium);border-radius:var(--primitive-radius-control);cursor:pointer}' +
    '#side .xtree .xmod:first-child{margin-top:0}#side .xtree .xmod .ms{font-size:var(--scale-type-min);color:var(--theme-text-tertiary);font-weight:400}#side .xtree .mi{width:1em;height:1em;font-size:calc(var(--scale-size-icon) * 1.35);overflow:visible}' +
    '#side .xtree .xmod.act .mi .acc{fill:var(--theme-trail-line);stroke:var(--theme-trail-line)}#side .xtree .xmod.xhm{margin-top:12px}' +
    '#side .xtree .xmod{font-size:17px;padding:11px 10px;margin-top:12px}#side .xtree .xmod .mi{font-size:26px}#side .xtree .xmod .ms{font-size:13px}' +
    /* r71（产品负责人 2026-10-15）：四个一级按钮也加和方形子按钮一样的细描边圆角框；激活只是浅底色 */
    '#side .xtree .xmod{border:var(--primitive-border-hairline) solid var(--component-sidebar-line);border-radius:12px;padding:12px 12px}#side .xtree .xmod:hover{border-color:var(--theme-line-control)}' +
    '#side .xtree .xmod[aria-current="page"],#side .xtree .xmod.act{border-color:var(--component-sidebar-line)}#side .xtiles{margin-left:0!important}' +
    '#side .xtiles{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:6px 0 4px 4px}' +
    '#side .xtree .xtile{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:8px;height:84px;padding:0;border-radius:12px;border:var(--primitive-border-hairline) solid var(--component-sidebar-line);background:transparent;color:var(--theme-text-secondary);font:inherit;font-size:14px;cursor:pointer}' +
    '#side .xtree .xtile > svg{width:34px;height:34px;flex:none}#side .xtree .xtile:hover{color:var(--theme-text-primary);border-color:var(--theme-line-control)}' +
    '#side .xtree .xtile[aria-current="page"]{color:var(--theme-text-primary);background:var(--component-sidebar-selBg);border-color:var(--theme-trail-line);box-shadow:none}#side .xtree .xmod{margin-top:14px}' +
    '#side .xtree button[aria-current="page"]{background:var(--component-sidebar-selBg);color:var(--theme-text-primary);box-shadow:none!important}#side .xtree .sbar{display:none!important}#side .stag{display:none}' +
    '@media (max-height:720px){#side{overflow-y:auto}}';
  /* r68（产品负责人 2026-10-15 批准）：子模块做成“上图标、下文字”的方形按钮，每个一级下面两个并排；六个图标各不相同（不再两把钥匙） */
  var TS = function (d) { return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + d + '</svg>'; };
  var TILE_IC = {
    'track:adv': TS('<path d="M9 3h6"/><path d="M10 3v6.2L4.6 18.4A1.8 1.8 0 0 0 6.2 21h11.6a1.8 1.8 0 0 0 1.6-2.6L14 9.2V3"/><path d="M7.2 15h9.6"/><circle cx="10.5" cy="17.6" r=".6" fill="currentColor"/><circle cx="13.6" cy="18.4" r=".5" fill="currentColor"/>'),
    'track:rules': TS('<path d="M5 4.5A1.5 1.5 0 0 1 6.5 3H19v15H6.5A1.5 1.5 0 0 0 5 19.5z"/><path d="M5 19.5A1.5 1.5 0 0 0 6.5 21H19v-3"/><path d="M9 7.5h6"/><path d="M9 11h6"/><path d="M9 14.5h3.5"/>'),
    'track:alerts': TS('<path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/>'),
    'torch:sources': TS('<path d="M8 3v4"/><path d="M16 3v4"/><path d="M6 7h12v4a6 6 0 0 1-12 0z"/><path d="M12 17v4"/><path d="M9.5 21h5"/>'),
    'torch:data': TS('<ellipse cx="12" cy="5.5" rx="7" ry="2.5"/><path d="M5 5.5v6c0 1.4 3.1 2.5 7 2.5s7-1.1 7-2.5v-6"/><path d="M5 11.5v6c0 1.4 3.1 2.5 7 2.5s7-1.1 7-2.5v-6"/>'),
    'cluster:objects': TS('<path d="M12 3l7 3v5.5c0 4.3-3 7.8-7 9.5-4-1.7-7-5.2-7-9.5V6z"/><path d="M8.8 12.2l2.2 2.2 4.2-4.6"/>'),
    'cluster:rules': TS('<path d="M12 4v16"/><path d="M7 20h10"/><path d="M5 7h14"/><path d="M5 7l-2.5 6a2.5 2.5 0 0 0 5 0z"/><path d="M19 7l-2.5 6a2.5 2.5 0 0 0 5 0z"/><circle cx="12" cy="4" r="1"/>')
  };
  LIVE.sideTree = function (app, cur, foot) {
    var side = document.getElementById('side'), sw = side && side.querySelector('.modsw'), nav = side && side.querySelector('.snav:not(.sfoot)'); if (!sw || !nav) return;
    if (!document.getElementById('tree-css')) { var s0 = document.createElement('style'); s0.id = 'tree-css'; s0.textContent = TREE_CSS; document.head.appendChild(s0); }
    var esc = C.esc, icons = {}, xh = !foot && app === 'torch' && cur === 'graph';
    sw.querySelectorAll('[data-mod]').forEach(function (b) { var sv = b.querySelector('svg'); icons[b.dataset.mod] = sv ? sv.outerHTML : ''; });
    /* r66（产品负责人 2026-10-15）：一级标题就是它的第一项（我的状态 / 数据导航 / 授权协作），下面不再重复列；在那一页时一级标题高亮 */
    nav.innerHTML = C.PROD.modules.map(function (m) {
      var home = !foot && !xh && m.id === app && m.nav[0] && cur === m.nav[0].id;
      return '<button class="xmod' + (!foot && !xh && m.id === app ? ' act' : '') + '" data-xmod="' + m.id + '"' + (home ? ' aria-current="page"' : '') + '>' + (icons[m.id] || '') + '<span class="mn">' + esc(({torch: '星炬', track: '星轨', cluster: '星簇'})[m.id] || m.zh) + '</span><span class="ms">' + esc(({track: '我的状态', torch: '我的数据', cluster: '我的协作'})[m.id] || m.sub) + '</span></button>' +
        '<div class="xtiles">' + m.nav.slice(1).filter(function (n) { return n.id !== 'alerts'; }).map(function (n) { return '<button class="xsub xtile" data-xapp="' + m.id + '" data-nav2="' + n.id + '"' + (!foot && !xh && m.id === app && n.id === cur ? ' aria-current="page"' : '') + '>' + (TILE_IC[m.id + ':' + n.id] || C.ic(String(n.icon || '').replace(/^icon:/, ''))) + '<span>' + esc(n.zh) + '</span></button>'; }).join('') + '</div>';
    }).join('') + '<button class="xmod xhm' + (xh ? ' act' : '') + '" data-xmod="xh"' + (xh ? ' aria-current="page"' : '') + '>' + XH_ICON + '<span class="mn" data-ptds-ui="sb97408c4375f">星痕</span><span class="ms" data-ptds-ui="s2c518b70b181">我的证据</span></button>' +
      '<div class="xtiles">' + [['records', '操作记录', 'scroll-text'], ['map', '证据图谱', 'network']].map(function (n) { return '<button class="xsub xtile" data-xh-view="' + n[0] + '"' + (xh && (C.st.xhView || 'map') === n[0] ? ' aria-current="page"' : '') + '>' + C.ic(n[2]) + '<span>' + n[1] + '</span></button>'; }).join('') + '</div>';
    nav.classList.add('xtree'); nav.setAttribute('aria-label', '导航'); sw.remove();
    var version = document.createElement('div'); version.id = 'sidebar-version'; version.textContent = '0.3.0-alpha.1'; version.style.cssText = 'text-align:center;color:var(--theme-text-tertiary);font-size:14px;padding:10px 0 4px;letter-spacing:.04em'; side.appendChild(version);
    var P = window.__ptds, st = C.st;
    var go = function (a, id) {
      st.foot = null; C.closeDrawer();
      if (a === 'torch') { st.entry = null; st.tdetail = null; C.goTorch(id); }
      else if (a === 'cluster') { st.gform = null; P.goCluster(id); }
      else { if (id === 'wall') st.card = null; C.goTrack(id); }
      window.scrollTo(0, 0);
    };
    nav.querySelectorAll('[data-xmod]').forEach(function (b) { b.onclick = function () {
      if (b.dataset.xmod === 'xh') { st.foot = null; C.closeDrawer(); C.goTorch('graph'); window.scrollTo(0, 0); return; }
      var m = C.PROD.modules.filter(function (x) { return x.id === b.dataset.xmod; })[0]; if (m && m.nav[0]) go(m.id, m.nav[0].id); }; });
    nav.querySelectorAll('[data-xh-view]').forEach(function (b) { b.onclick = function () { st.xhView = b.dataset.xhView; go('torch', 'graph'); }; });
    nav.querySelectorAll('[data-xapp]').forEach(function (b) { b.onclick = function () { go(b.dataset.xapp, b.dataset.nav2); }; });
  };
  LIVE.navMoved = function (app, cur, foot) {
    try { LIVE.sideTree(app, cur, foot); } catch (err) { if(err&&(err.viewPending||err.code==='VIEW_CHANGED'))throw err; /* 展开的侧栏失败时保留原侧栏 */ }
    LIVE.askFab();
    if (!foot && (app === 'cluster' || app === 'torch' && cur === 'data' || app === 'track' && (cur === 'eng' || cur === 'adv' || cur === 'rules'))) { var mb = document.getElementById('mbar'); if (mb) mb.innerHTML = ''; } /* 产品负责人 08:30：这三页的成熟度条删掉 */
    setTimeout(function () { LIVE.subBack(app, foot); }, 0);
    var key = foot ? 'foot|' + foot : app + '|' + cur, prev = navLast, side = document.getElementById('side');
    navLast = key;
    var nav = side && side.querySelector('.snav:not(.sfoot)'), btn = nav && nav.querySelector('button.xmod[aria-current="page"], button:not(.xtile)[aria-current="page"]');
    if (nav && btn) {
      nav.classList.add('hasbar');
      var bar = document.createElement('span'); bar.className = 'sbar'; nav.appendChild(bar);
      var top = btn.offsetTop, h = btn.offsetHeight, same = prev && prev.split('|')[0] === app && prev !== key;
      bar.style.height = h + 'px';
      bar.style.transform = 'translateY(' + (same && barTop !== null ? barTop : top) + 'px)';
      if (same && barTop !== null && barTop !== top) { void bar.offsetWidth; bar.classList.add('mv'); bar.style.transform = 'translateY(' + top + 'px)'; }
      barTop = top;
    } else barTop = null;
    if (prev && prev !== key && prev.split('|')[0] === key.split('|')[0]) {
      ['view', 'mbar'].forEach(function (id) { var el = document.getElementById(id); if (!el) return; el.classList.remove('subin'); void el.offsetWidth; el.classList.add('subin'); });
    }
  };
  document.addEventListener('animationend', function (e) { if (e.animationName === 'subin') e.target.classList.remove('subin'); });
  /* 授权协作 · 授权图片（产品负责人 2026-10-14 00:37 / 00:42 / 00:45；2026-10-15 r57 改版）：自选状态卡，
     填授权对象、用途、开始和结束日期（空着按回车填入示例）；四项齐了按钮才能点，不齐时写明还差什么。
     “附上变化”“竞争性解释”这次不放；撤销这次也不放（只在后台保留接口）。本机画一张带水印的图片，星簇同时记一条授权。图片内容由本机进程按当前数据拼好，这里照着画。
     水印是声明，不是加密；发出去收不回。页面上写明。 */
  LIVE.SHARE_FONT = '"PingFang SC","Noto Sans CJK SC","Microsoft YaHei",sans-serif';
  LIVE.renderShare = function () {
    var esc = C.esc, ic = C.ic, st = C.st, v = document.getElementById('view'); if (!v) return;
    var today = String(C.tzTime(new Date().toISOString())).slice(0, 10);
    var plus = function (d, n) { var t = new Date(d + 'T00:00:00Z'); t.setUTCDate(t.getUTCDate() + n); return t.toISOString().slice(0, 10); };
    var sh = st.share && st.share.key === st.key ? st.share : (st.share = { key: st.key, sel: {}, to: '', purpose: '', from: today, until: plus(today, 7), res: null });
    var D; try { D = readCached('/api/cluster/shares?key=' + encodeURIComponent(st.key)); } catch (err) { if(err&&(err.viewPending||err.code==='VIEW_CHANGED'))throw err; v.innerHTML = '<section class="box"><div class="sub2" data-ptds-inline><!--ptds-ui:s4647c71692df-->读不到星簇记录（<!--/ptds-ui-->' + esc(LIVE.saveErr(err)) + '）</div></section>'; return; }
    if (D.replay) { v.innerHTML = '<section class="box"><h3 data-ptds-ui="s1d6c0c883e5d">授权图片</h3><div class="sub2" data-ptds-ui="s5014a8120c6a">回放实例只用来回看，不能生成授权图片。</div></section>'; return; }
    var groups = D.options.groups, comp = D.options.compete, nSel = Object.keys(sh.sel).filter(function (k) { return sh.sel[k]; }).length;
    var miss = function () {
      var m = []; if (!nSel) m.push('至少勾一项授权内容'); if (!sh.to.trim()) m.push('授权对象'); if (!sh.purpose.trim()) m.push('授权用途');
      var okD = /^\d{4}-\d{2}-\d{2}$/; if (!okD.test(sh.from) || !okD.test(sh.until) || sh.from < today || sh.until < sh.from || sh.until > plus(sh.from, 90)) m.push('授权时效（开始不早于今天，结束不早于开始，最长 90 天）');
      return m; };
    var item = function (it) { return '<label class="sh-it"><input type="checkbox" data-sh-sel="' + esc(it.id) + '"' + (sh.sel[it.id] ? ' checked' : '') + '><span class="sh-n">' + esc(it.name) + '</span><span class="sub2">' + esc(it.value) + (it.tp ? ' · ' + esc(String(it.tp).slice(5)) : '') + '</span></label>'; };
    var left = '<section class="box sh-form"><h3>' + ic('send') + ' 数据授权给他人？点这里细化</h3>' +
      '<h4 data-ptds-ui="sb55039dd311e">1、授权内容</h4>' + (groups.length ? groups.map(function (g) { return '<div class="sh-g"><div class="sub2">' + esc(g.zh) + '</div><div class="sh-its">' + g.items.map(item).join('') + '</div></div>'; }).join('') : '<div class="sub2" data-ptds-ui="s292e2f49d01a">还没有算出结果的状态卡。</div>') +
      '<h4 data-ptds-ui="sefc4a4c0df8e">2、授权对象</h4><input class="inp sh-in" id="sh-to" maxlength="20" placeholder="例如 医生（回车直接填入）" data-eg="医生" value="' + esc(sh.to) + '">' +
      '<h4 data-ptds-ui="sc0343333c4ab">3、授权用途</h4><input class="inp sh-in" id="sh-pu" maxlength="30" placeholder="例如 复诊前沟通（回车直接填入）" data-eg="复诊前沟通" value="' + esc(sh.purpose) + '">' +
      '<h4 data-ptds-ui="s929df25cadf1">4、授权时效</h4><div class="sh-dt"><span data-ptds-ui="sd2bb025a2e51">开始</span><input class="inp" id="sh-fr" type="date" min="' + today + '" max="' + plus(today, 90) + '" value="' + esc(sh.from) + '"><span data-ptds-ui="sc7b24e7997e9">结束</span><input class="inp" id="sh-un" type="date" min="' + today + '" max="' + plus(today, 180) + '" value="' + esc(sh.until) + '"></div>' +
      '<div class="sub2 sh-why" data-ptds-ui="s4b41b529369d">最长 90 天；开始和结束日期都写进授权记录和图片水印</div>' +
      '<div class="opts sh-gor"><button class="btn" id="sh-go">' + ic('shield-check') + ' 生成图片并记授权' + (nSel ? '（' + nSel + ' 项）' : '') + '</button></div><div class="sub2 sh-why" id="sh-miss"></div>' +
      '<div class="sub2 sh-lim" data-ptds-ui="sd4840b2de49d">水印写明给谁、范围、用途、有效期。它是声明，不是加密：图片可以被裁剪，AI 也能读出里面的内容；发出去就收不回。</div></section>';
    var r = sh.res;
    var right = '<section class="box sh-prev"><h3>' + ic('file-image') + ' 图片</h3>' + (r ? '<canvas id="sh-c" class="sh-c"></canvas><div class="opts"><button class="btn" id="sh-copy">' + ic('copy') + ' 复制图片</button><button class="btn2" id="sh-save">' + ic('download') + ' 保存 PNG</button></div>' +
      '<div class="sub2" data-ptds-inline><!--ptds-ui:s65c0e71f66a0-->授权号 <!--/ptds-ui-->' + esc(r.meta.share_id) + ' · 内容指纹 ' + esc(r.meta.content_sha.slice(0, 12)) + '… · 已记进星簇授权记录</div>' :
      '<div class="sh-empty sub2" data-ptds-ui="s42752bf8a0e4">选好授权内容、填好对象、用途和时效后，点“生成图片并记授权”，图片画在这里。</div>') +
      (D.shares.length ? '<details class="more"><summary data-ptds-inline><!--ptds-ui:s2c89c20531d7-->记过的授权图片（<!--/ptds-ui-->' + D.shares.length + '）</summary>' + D.shares.map(function (s) {
        return '<div class="sh-row"><span><b>' + esc(s.to) + '</b> · ' + esc(s.purpose) + '<br><span class="sub2">' + esc(s.scope) + '</span></span><span class="sub2">' + esc(C.tzTime(s.at, true).slice(5, 16)) + ' · ' + (s.from ? esc(s.from) + ' 至 ' : '至 ') + esc(s.until) + ' · ' + esc(s.share_id) + '</span>' +
          (s.revoked ? '<span class="sub2" data-ptds-ui="sfef96e34f77b">已撤销</span>' : '') + '</div>';
      }).join('') + (D.verify.ok ? '' : '<div class="sub2" data-ptds-inline><!--ptds-ui:s8f6e16b9cd16-->记录的指纹链在第 <!--/ptds-ui-->' + esc(D.verify.line) + ' 行对不上。</div>') + '</details>' : '') + '</section>';
    v.innerHTML = '<div class="sh-wrap">' + left + right + '</div>';
    if (!document.getElementById('sh-css')) { var s0 = document.createElement('style'); s0.id = 'sh-css'; s0.textContent = LIVE.SHARE_CSS; document.head.appendChild(s0); }
    var gate = function () { var m = miss(), go = document.getElementById('sh-go'); go.disabled = !!m.length; document.getElementById('sh-miss').textContent = m.length ? '还差：' + m.join('、') : ''; };
    var keep = function () { sh.to = document.getElementById('sh-to').value; sh.purpose = document.getElementById('sh-pu').value; sh.from = document.getElementById('sh-fr').value; sh.until = document.getElementById('sh-un').value; gate(); };
    v.querySelectorAll('[data-sh-sel]').forEach(function (b) { b.onchange = function () { keep(); sh.sel[b.dataset.shSel] = b.checked; LIVE.renderShare(); }; });
    ['sh-to', 'sh-pu', 'sh-fr', 'sh-un'].forEach(function (id) { var el = document.getElementById(id); el.oninput = el.onchange = keep; });
    v.querySelectorAll('.sh-in').forEach(function (el) { el.onkeydown = function (e) { if (e.key === 'Enter' && !e.isComposing) { e.preventDefault(); if (!el.value.trim()) { el.value = el.dataset.eg; keep(); } } }; });
    gate();
    document.getElementById('sh-go').onclick = LIVE.action(async function () {
      keep();
      if (miss().length) return;
      var items = Object.keys(sh.sel).filter(function (k) { return sh.sel[k]; });
      try { sh.res = (await call('POST', '/api/cluster/share', { key: st.key, items: items, with_change: false, to: sh.to.trim(), purpose: sh.purpose.trim(), from: sh.from, until: sh.until })); C.toast('已生成，并在星簇记了一条授权'); }
      catch (err) { if(err&&(err.viewPending||err.code==='VIEW_CHANGED'))throw err; C.toast('没有生成（' + (err.detail || LIVE.saveErr(err)) + '）'); return; }
      LIVE.renderShare();
    });
    if (!r) return;
    var cv = document.getElementById('sh-c'); LIVE.drawShare(cv, r);
    document.getElementById('sh-save').onclick = function () { var a = document.createElement('a'); a.href = cv.toDataURL('image/png'); a.download = 'PTDS-授权图片-' + r.meta.share_id + '.png'; document.body.appendChild(a); a.click(); a.remove(); };
    document.getElementById('sh-copy').onclick = function () {
      if (!navigator.clipboard || !window.ClipboardItem) { C.toast('这个浏览器不能直接复制图片，请用“保存 PNG”'); return; }
      cv.toBlob(function (b) { navigator.clipboard.write([new ClipboardItem({ 'image/png': b })]).then(function () { C.toast('图片已复制，可以直接粘贴发送'); }, function () { C.toast('没能复制，请用“保存 PNG”'); }); }, 'image/png');
    };
  };
  /* 画图：上面是所选状态卡（两列）和竞争性解释（四路并排），斜铺水印，底部金色授权条 */
  LIVE.drawShare = function (cv, r) {
    var P = r.payload, M = r.meta, F = LIVE.SHARE_FONT, X = P.compete, W = X ? 1440 : 1080, pad = 40;
    var pretty = function (t) { return String(t || '').replace(/×10\^9\/L/g, '×10⁹/L').replace(/×10\^12\/L/g, '×10¹²/L'); };
    var g0 = document.createElement('canvas').getContext('2d');
    var wrap = function (g, t, w) { var out = [], line = ''; String(t).split('').forEach(function (ch) { if (g.measureText(line + ch).width > w && line) { out.push(line); line = ch; } else line += ch; }); if (line) out.push(line); return out; };
    /* 先量高度 */
    var cw = (W - pad * 2 - 20) / 2, rows = Math.ceil(P.cards.length / 2), ch = P.with_change ? 132 : 108, laneH = 0, colW = (W - pad * 2 - 3 * 14) / 4;
    var cardH = function (c) { g0.font = '14px ' + F; return 96 + (c.note ? 22 : 0) + (c.change ? wrap(g0, c.change, cw - 40).length * 20 : 0); };
    var rowH = []; for (var i = 0; i < rows; i++) rowH.push(Math.max(cardH(P.cards[2 * i]), P.cards[2 * i + 1] ? cardH(P.cards[2 * i + 1]) : 0));
    var lanes = [];
    if (X) {
      lanes = X.columns.map(function (c) {
        var ls = []; g0.font = '13px ' + F;
        c.rows.forEach(function (rw) {
          if (rw.head) { ls.push({ t: rw.head, k: 'h' }); return; }
          wrap(g0, (rw.deep ? '· ' : '') + pretty(rw.need) + (rw.got ? '' : '（' + rw.outcome + '）'), colW - 28 - rw.deep * 10).forEach(function (t) { ls.push({ t: t, k: rw.got ? 'n' : 'h2', d: rw.deep }); });
          if (rw.got) wrap(g0, '实际 ' + pretty(rw.got) + ' · ' + rw.outcome, colW - 28 - rw.deep * 10).forEach(function (t) { ls.push({ t: t, k: 'g', d: rw.deep, o: rw.outcome }); });
        });
        if (c.missing.length) wrap(g0, '缺：' + c.missing.join('、'), colW - 28).forEach(function (t) { ls.push({ t: t, k: 'm' }); });
        return ls;
      });
      g0.font = '14px ' + F;
      var sum = wrap(g0, X.summary.join(''), W - pad * 2 - 32);
      laneH = 70 + Math.max.apply(null, lanes.map(function (ls) { return ls.length; })) * 18 + 70 + sum.length * 22 + 40;
    }
    var H = 120 + rowH.reduce(function (a, b) { return a + b + 16; }, 0) + (X ? laneH + 20 : 0) + 110;
    var dpr = 2; cv.width = W * dpr; cv.height = H * dpr; cv.style.aspectRatio = W + ' / ' + H;
    var g = cv.getContext('2d'); g.scale(dpr, dpr);
    g.fillStyle = '#0d1530'; g.fillRect(0, 0, W, H);
    g.fillStyle = '#E8B65A'; g.font = '600 26px ' + F; g.fillText('我的状态' + (P.cards.length ? ' · ' + P.cards.length + ' 张卡' : '') + (X ? ' · 竞争性解释' : ''), pad, 58);
    g.fillStyle = '#9aa6c8'; g.font = '15px ' + F; g.fillText('来自 PTDS 本机 · ' + String(M.at).slice(0, 16).replace('T', ' ') + ' 生成' + (P.with_change ? ' · 含和上次比的变化' : ''), pad, 88);
    var y = 116;
    P.cards.forEach(function (c, k) {
      var col = k % 2, x = pad + col * (cw + 20), h = rowH[Math.floor(k / 2)];
      g.fillStyle = '#16204a'; g.beginPath(); g.roundRect(x, y, cw, h, 14); g.fill();
      g.fillStyle = '#9aa6c8'; g.font = '14px ' + F; g.fillText(c.group + (c.tp ? ' · ' + c.tp : ''), x + 20, y + 28);
      g.fillStyle = '#e6ebf7'; g.font = '17px ' + F; g.fillText(c.name, x + 20, y + 54);
      g.fillStyle = '#ffffff'; g.font = '600 26px ' + F; g.fillText(pretty(c.value), x + 20, y + 86);
      var yy = y + 86;
      g.font = '14px ' + F; g.fillStyle = '#9aa6c8';
      if (c.note) { yy += 22; g.fillText(c.note, x + 20, yy); }
      if (c.change) wrap(g, c.change, cw - 40).forEach(function (t) { yy += 20; g.fillStyle = '#E8B65A'; g.fillText(t, x + 20, yy); });
      if (col === 1 || k === P.cards.length - 1) y += h + 16;
    });
    if (X) {
      y += 4; g.fillStyle = '#e6ebf7'; g.font = '600 20px ' + F; g.fillText('竞争性解释 · ' + X.tp + ' · 合起来的关注等级：' + X.level_zh, pad, y + 24);
      g.fillStyle = '#9aa6c8'; g.font = '13px ' + F; g.fillText('同一组数据按四种算法各算一遍，只说各自成立与否；只用于测试，不是结论。', pad, y + 48);
      var top = y + 64, lh = 0;
      X.columns.forEach(function (c, k) {
        var x = pad + k * (colW + 14), ls = lanes[k], h = 46 + ls.length * 18 + 14; lh = Math.max(lh, h);
        g.fillStyle = '#16204a'; g.beginPath(); g.roundRect(x, top, colW, Math.max(h, 10), 12); g.fill();
        g.fillStyle = '#e6ebf7'; g.font = '600 15px ' + F; g.fillText(c.name, x + 14, top + 24);
        g.fillStyle = c.result === 'MET' || c.result === 'ALERT' ? '#E8B65A' : '#9aa6c8'; g.font = '600 14px ' + F; g.fillText(c.result_zh, x + 14, top + 42);
        var yy = top + 46;
        ls.forEach(function (l) {
          yy += 18; g.font = (l.k === 'h' ? '600 ' : '') + '13px ' + F;
          g.fillStyle = l.k === 'h' ? '#c9d2ee' : l.k === 'g' ? (l.o === '满足' || l.o === '超过变化阈值' ? '#E8B65A' : '#8a93b2') : l.k === 'm' ? '#8a93b2' : '#d5dbec';
          g.fillText(l.t, x + 14 + (l.d || 0) * 10, yy);
        });
      });
      y = top + lh + 24;
      g.fillStyle = '#e6ebf7'; g.font = '600 15px ' + F; g.fillText('小结', pad, y); g.font = '14px ' + F; g.fillStyle = '#c9d2ee';
      wrap(g, X.summary.join(''), W - pad * 2 - 32).forEach(function (t) { y += 22; g.fillText(t, pad, y); });
    }
    /* 斜铺水印：给谁 · 用途 · 有效到 */
    g.save(); g.translate(W / 2, (H - 84) / 2); g.rotate(-Math.PI / 9); g.fillStyle = 'rgba(232,182,90,.11)'; g.font = '600 22px ' + F;
    var wm = '仅授权给 ' + M.to + ' · ' + M.purpose + ' · ' + (M.from ? M.from + ' 至 ' : '至 ') + M.until;
    for (var yy = -H; yy < H; yy += 80) for (var xx = -W; xx < W; xx += g.measureText(wm).width + 120) g.fillText(wm, xx + (yy / 80 % 2 ? 160 : 0), yy);
    g.restore();
    g.fillStyle = '#E8B65A'; g.fillRect(0, H - 84, W, 84); g.fillStyle = '#0b1226';
    g.font = '600 16px ' + F; var l1 = '授权给：' + M.to + '　用途：' + M.purpose + '　范围：' + M.scope;
    g.fillText(wrap(g, l1, W - 56)[0] + (wrap(g, l1, W - 56).length > 1 ? '…' : ''), 28, H - 52);
    g.font = '14px ' + F; g.fillText(String(M.at).slice(0, 16).replace('T', ' ') + ' 生成，' + (M.from ? M.from + ' 至 ' : '至 ') + M.until + ' 有效 · 授权号 ' + M.share_id + ' · 内容指纹 ' + M.content_sha.slice(0, 12) + ' · ' + M.note, 28, H - 24);
  };
  LIVE.SHARE_CSS = '.sh-dt{display:grid;grid-template-columns:auto 1fr auto 1fr;gap:8px;align-items:center}.sh-dt span{color:var(--theme-text-secondary)}.sh-why{margin-top:6px}.sh-gor{margin-top:var(--primitive-space-5)}' + '.sh-wrap{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.35fr);gap:var(--primitive-space-5);align-items:start}@media (max-width:1100px){.sh-wrap{grid-template-columns:minmax(0,1fr)}}' +
    '.sh-form h4{margin:var(--primitive-space-5) 0 var(--primitive-space-2)}.sh-g{margin:var(--primitive-space-2) 0}.sh-its{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:6px;margin-top:4px}' +
    '.sh-it{display:flex;align-items:baseline;gap:6px;padding:6px 10px;border:var(--primitive-border-hairline) solid var(--theme-line-hairline);border-radius:10px;cursor:pointer;min-width:0}.sh-it:hover{border-color:var(--theme-line-control)}.sh-it .sh-n{white-space:nowrap}.sh-it .sub2{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}' +
    '.sh-chg{display:block;margin:var(--primitive-space-3) 0}.sh-x{display:flex;flex-wrap:wrap;gap:14px;margin-top:4px}.sh-kv{display:grid;grid-template-columns:4em minmax(0,1fr);gap:8px 12px;align-items:center}.sh-kv .inp{width:100%}' +
    '.sh-lim{margin-top:var(--primitive-space-4);line-height:1.7}.sh-c{width:100%;height:auto;border-radius:12px;display:block;margin-bottom:var(--primitive-space-3)}.sh-empty{padding:48px 16px;text-align:center;border:var(--primitive-border-hairline) dashed var(--theme-line-control);border-radius:12px}' +
    '.sh-row{display:grid;grid-template-columns:minmax(0,1fr) auto auto;gap:12px;align-items:center;padding:8px 0;border-bottom:var(--primitive-border-hairline) solid var(--theme-line-hairline)}';
  /* DEVICE_TABLES_R01_BEGIN: read-only source-isolated presentation. */
  function deviceMetricGroup(code) {
    if (/^(OURA|GARMIN|SOMALOOP|QKEER)_(HR(?:_|$)|RESTING_HR|LOWEST_HR|HIGHEST_HR)/.test(code)) return 'hr';
    if (/HRV/.test(code)) return 'hrv';
    if (/TEMP/.test(code)) return 'temp';
    if (/SPO2/.test(code)) return 'spo2';
    return 'other';
  }
  function deviceTableGroups(snap, family, metric) {
    var groups = {};
    ((snap.vitals_all || snap.vitals || {}).items || []).forEach(function (item) {
      if (DEVICE_FAMILIES.indexOf(item.family) < 0 || (family && item.family !== family)) return;
      if (metric && metric !== 'all' && deviceMetricGroup(item.code) !== metric) return;
      if (!groups[item.family]) groups[item.family] = [];
      groups[item.family].push(item);
    });
    return Object.keys(groups).map(function (f) { return { family: f, items: groups[f].slice().sort(function (a,b) { return rank(a.code)-rank(b.code); }) }; });
  }
  function deviceScope(item) {
    if (/RAW/.test(item.code)) return '原始值 · 语义待确认，不视为跨设备等价指标';
    if (/_COUNT$/.test(item.code)) return '样本数量 · 不等同测量值';
    if (/_HR_(MEAN|MIN|MAX)$/.test(item.code)) return '日级心率统计 · 均值、最小值、最大值分别比较';
    if (item.code === 'OURA_TEMP_DEV') return '相对基线的温度偏离 · 日汇总';
    if (/SKIN_TEMP/.test(item.code)) return '皮肤温度 · 不等同核心体温';
    if (/HRV/.test(item.code)) return 'HRV · 算法与统计窗口需核对';
    if (/RESTING_HR/.test(item.code)) return '静息心率 · 独立指标';
    if (/LOWEST_HR|HR_MIN/.test(item.code)) return '最低心率 · 独立指标';
    if (/SPO2_AVG|OURA_SPO2/.test(item.code)) return '血氧平均值 · 日汇总';
    return item.observed_at ? '单次观测' : item.observed_date ? '日记录 · 未提供具体时刻' : '观测时间未提供';
  }
  var deviceTraceCache=null;
  function deviceTrace(snap, item) {
    var timeline=snap.timeline||[];
    if(!deviceTraceCache||deviceTraceCache.timeline!==timeline){
      var groups=new Map();
      timeline.forEach(function(r){
        var sources=groups.get(r.code);if(!sources){sources=new Map();groups.set(r.code,sources);}
        var bucket=sources.get(r.source_kind);if(!bucket){bucket={rows:[],recent:null};sources.set(r.source_kind,bucket);}
        bucket.rows.push(r);
      });
      deviceTraceCache={timeline:timeline,groups:groups};
    }
    var bySource=deviceTraceCache.groups.get(item.code),bucket=bySource&&bySource.get(item.source_kind);
    if(!bucket)return [];
    if(bucket.recent)return bucket.recent;
    bucket.recent=bucket.rows.slice().sort(function (a,b) {
      var ta = a.temporal || {}, tb = b.temporal || {};
      var av=ta.observed_at||ta.observed_date||'',bv=tb.observed_at||tb.observed_date||'';
      return (Date.parse(av)||0)-(Date.parse(bv)||0);
    }).slice(-12);
    return bucket.recent;
  }
  function deviceTraceSvg(rows) {
    var esc=C.esc, W=180,H=38,pad=5;
    if (!rows.length) return '<span class="sub2" data-ptds-ui="s51b0ead8c106">暂无历史观测</span>';
    var valid=rows.map(function(r){var raw=r.value_raw, n=Number(raw);return raw!==null && raw!==undefined && String(raw).trim()!=='' && !r.comparator && isFinite(n) && /^[-+]?\d+(\.\d+)?$/.test(String(raw)) ? n : null;});
    var numbers=valid.filter(function(n){return n!==null;});
    if(!numbers.length)return '<span class="sub2" data-ptds-ui="s163bb01bc939">非精确数值记录</span>';
    var units=rows.filter(function(r,i){return valid[i]!==null;}).map(function(r){return r.unit_raw||'';});
    if(units.some(function(u){return u!==units[0];}))return '<span class="sub2" data-ptds-ui="s0863142e63e6">单位不同 · 分次查看来源</span>';
    var min=Math.min.apply(null,numbers),max=Math.max.apply(null,numbers),paths='',points='',previous=null;
    rows.forEach(function(r,i){var n=valid[i],t=r.temporal||{},x=rows.length===1?W/2:pad+i/(rows.length-1)*(W-pad*2),y=max===min?H/2:H-pad-(n-min)/(max-min)*(H-pad*2);
      if(n===null){previous=null;return;}
      var unit=r.unit_raw, method=r.method||null, time=t.observed_at||t.observed_date;
      if(previous && unit && unit===previous.unit && method===previous.method && time && previous.time && time!==previous.time)paths+='<path d="M'+previous.x+','+previous.y+' L'+x+','+y+'"/>';
      points+='<circle cx="'+x+'" cy="'+y+'" r="'+(i===rows.length-1?3:1.8)+'"><title>'+esc(String(r.value_raw)+' '+(unit||'')+' · '+(time||'时间未知'))+'</title></circle>';
      previous={x:x,y:y,unit:unit,method:method,time:time};
    });
    return '<svg viewBox="0 0 '+W+' '+H+'" role="img" aria-label="本设备最近观测；连线仅表示观测顺序">'+paths+points+'</svg>';
  }
  LIVE.deviceTableGroups=deviceTableGroups;
  LIVE.renderDeviceTables=function(){
    var st=C.st,snap=C.S(),esc=C.esc,metric=st.deviceMetric||'all',family=st.vitalsFamily||null;
    var all=deviceTableGroups(snap,null,'all'),groups=deviceTableGroups(snap,family,metric);
    if(!document.getElementById('device-tables-css')){var style=document.createElement('style');style.id='device-tables-css';style.textContent=
      '.device-tables .dt-toolbar{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:18px}.device-tables .dt-table{width:100%;border-collapse:collapse;table-layout:fixed}.device-tables .dt-table th,.device-tables .dt-table td{text-align:left;padding:12px 8px;border-bottom:1px solid var(--theme-line-hairline);overflow-wrap:anywhere;vertical-align:middle}.device-tables .dt-table th{font-weight:400;color:var(--theme-text-secondary);font-size:var(--scale-type-meta)}.device-tables .dt-value{font-size:20px;font-weight:600;font-variant-numeric:tabular-nums}.device-tables .dt-chart svg{display:block;width:100%;max-width:180px;height:38px;overflow:visible}.device-tables .dt-chart path{stroke:var(--theme-text-secondary);stroke-width:1;fill:none}.device-tables .dt-chart circle{fill:var(--theme-text-primary)}.device-tables .box{margin-bottom:18px}.device-compare-entry{display:flex;justify-content:flex-end;margin:8px 0}.device-tables .dt-table th:nth-child(1){width:27%}.device-tables .dt-table th:nth-child(2){width:19%}.device-tables .dt-table th:nth-child(3){width:22%}.device-tables .dt-table th:nth-child(4){width:22%}.device-tables .dt-table th:nth-child(5){width:10%}@media(max-width:700px){.device-tables .dt-table thead{display:none}.device-tables .dt-table tr{display:grid;grid-template-columns:1fr 1fr;padding:10px 0;border-bottom:1px solid var(--theme-line-hairline)}.device-tables .dt-table td{border:0;padding:6px}.device-tables .dt-table td:first-child{grid-column:1/-1}}';document.head.appendChild(style);}
    var filter='<label data-ptds-inline><!--ptds-ui:sb87e67c7dae0-->指标 <!--/ptds-ui--><select class="inp" id="dt-metric">'+[['all','全部指标'],['hr','心率（按各自口径）'],['spo2','血氧'],['temp','温度'],['hrv','HRV']].map(function(o){return '<option value="'+o[0]+'"'+(metric===o[0]?' selected':'')+'>'+o[1]+'</option>';}).join('')+'</select></label>';
    var title=family?'我的体征（'+(LIVE.SOURCE_ZH[family]||family)+'）':(st.view==='adv'?'多模型比对 · 按指标对比':'按指标对比');
    document.getElementById('view').innerHTML=C.pgh(title)+'<div class="device-tables"><div class="dt-toolbar"><button class="btn2" id="dt-back" title="返回状态卡片" data-ptds-ui-title="s59a3a7ba38ad" data-ptds-ui="s572cf45ba436">返回</button>'+filter+'<span class="sub2" data-ptds-ui="s360449accca9">各设备独立记录，不合并、不判定冲突</span></div><div class="dt-toolbar" role="group" aria-label="设备来源" data-ptds-ui-aria-label="s34ef48de27b6"><button class="chip" data-dt-family="" aria-pressed="'+!family+'">全部设备</button>'+all.map(function(g){return '<button class="chip" data-dt-family="'+esc(g.family)+'" aria-pressed="'+(family===g.family)+'">'+esc(LIVE.SOURCE_ZH[g.family]||g.family)+'</button>';}).join('')+'</div>'+groups.map(function(g){return '<section class="box"><h3>'+esc(LIVE.SOURCE_ZH[g.family]||g.family)+'</h3><table class="dt-table"><caption class="sub2" style="text-align:left">单设备数据表 · '+g.items.length+' 项指标</caption><thead><tr><th data-ptds-ui="s872087f4e6b7">指标／口径</th><th data-ptds-ui="s8f0ef3b2b86d">最近结果</th><th data-ptds-ui="sc8f71fa6ca5b">观测时间</th><th data-ptds-ui="s48baa2899a30">近期观测 · 按顺序</th><th data-ptds-ui="sa488e93d69cc">来源</th></tr></thead><tbody>'+g.items.map(function(i){var when=i.observed_at?C.tzTime(i.observed_at,true):(i.observed_date||'时间未知');return '<tr data-dt-source="'+esc(g.family)+'"><td><strong>'+esc(i.label_zh)+'</strong><div class="sub2">'+esc(deviceScope(i))+'</div></td><td><span class="dt-value">'+esc((i.comparator||'')+String(i.value_raw==null?'—':i.value_raw))+'</span> <span class="sub2">'+esc(i.unit_raw||'')+'</span></td><td>'+esc(when)+'<div class="sub2">'+(i.fresh===true?'近期观测':i.fresh===false?'等待新读数':'时效未判定')+'</div></td><td class="dt-chart">'+deviceTraceSvg(deviceTrace(snap,i))+'</td><td><button class="link" data-dt-code="'+esc(i.code)+'">查看</button></td></tr>';}).join('')+'</tbody></table></section>';}).join('')+(groups.length?'':'<div class="box" data-ptds-ui="s10071c8c0ee2">当前选择暂无观测记录，不以其他设备补齐。</div>')+'<p class="sub2" data-ptds-ui="sa003d34aa498">各设备可能采用不同算法与统计窗口。连线仅表示本设备观测顺序，不代表连续监测；这里不求平均，也不生成跨设备状态等级。</p></div>';
    document.getElementById('dt-back').onclick=function(){st.deviceMetric='all';st.vitalsFamily=null;if(st.view==='adv')st.labTab=null;else st.view='wall';C.render();};
    document.getElementById('dt-metric').onchange=function(){st.deviceMetric=this.value;C.render();};
    document.querySelectorAll('[data-dt-family]').forEach(function(b){b.onclick=function(){st.vitalsFamily=b.dataset.dtFamily||null;C.render();};});
    document.querySelectorAll('[data-dt-code]').forEach(function(b){b.onclick=function(){LIVE.openVitalSource(b.dataset.dtCode);};});
  };
  (function () {
    var previous = LIVE.addStateMount;
    LIVE.addStateMount = function () {
      previous.apply(this, arguments);
      var bar = document.getElementById('add-state');
      if (!bar || document.getElementById('device-compare-go')) return;
      bar.style.gap = '8px';
      var button = document.createElement('button');
      button.id = 'device-compare-go'; button.type = 'button'; button.className = 'btn2';
      button.style.marginTop = '-6px'; button.textContent = '按指标对比';
      bar.insertBefore(button, bar.firstChild);
      button.onclick = function () {
        C.st.card = 'VITALS'; C.st.group = null; C.st.vitalsFamily = null; C.st.deviceMetric = 'hr';
        C.st.labTab = 'compete'; C.goTrack('adv');
      };
    };
  })();
  /* DEVICE_TABLES_R01_END */

  /* ASYNC_REFRESH_R01: presentation only. Device acquisition and server writes are unchanged. */
  // One owner for non-mobile read timers and abortable requests; bfcache resumes once.
  function readLife() {
    if(LIVE._readLife)return LIVE._readLife;
    var life=LIVE._readLife={closed:false,timers:[],requests:new Set()};
    if(window.addEventListener){
      window.addEventListener('pagehide',function(){life.closed=true;readEpoch++;if(LIVE._dataReadSession)LIVE._dataReadSession.invalidate();life.timers.forEach(function(t){clearInterval(t.id);t.id=null;});life.requests.forEach(function(r){clearTimeout(r.timeout);r.controller.abort();});});
      window.addEventListener('pageshow',function(){if(!life.closed)return;life.closed=false;life.timers.forEach(function(t){t.id=setInterval(t.run,t.ms);});});
    }return life;
  }
  function readTimer(fn,ms){var life=readLife(),t={ms:ms,run:function(){if(!life.closed)fn();}};life.timers.push(t);if(!life.closed)t.id=setInterval(t.run,ms);return t;}
  LIVE.readTimer=readTimer;
  LIVE.managedRead=function(path){
    var life=readLife(),key=C.st.key,route=LIVE.refreshRoute(),epoch=readEpoch;
    if(life.closed)return Promise.reject(Error('VIEW_CHANGED'));
    var controller=new AbortController(),r={controller:controller};r.timeout=setTimeout(function(){controller.abort();},20000);life.requests.add(r);
    return fetch(path,{headers:{'X-PTDS':'1'},cache:'no-store',signal:controller.signal}).then(function(x){if(!x.ok)throw Error('STATE_UNAVAILABLE');return x.json();}).then(function(value){if(controller.signal.aborted||life.closed||key!==C.st.key||route!==LIVE.refreshRoute()||epoch!==readEpoch||pendingWrites)throw Error('VIEW_CHANGED');return value;}).finally(function(){clearTimeout(r.timeout);life.requests.delete(r);});
  };
  // HOME_READ_R03: full histories and the bounded home view are separate caches.
  LIVE.homeReads=Object.create(null);
  LIVE.fullHydrations=Object.create(null);
  LIVE.homeReadEnabled=function(){return !!(C&&C.DATA&&C.DATA.ptds_live&&C.DATA.ptds_live.home_read_version>=1);};
  LIVE.homeRoute=function(){var s=C.st;return s.app==='track'&&!s.foot&&(s.view==='vitals-card'||s.view==='wall'&&(!s.stateSection||s.stateSection==='cards'));};
  LIVE.homeEntry=function(key,full){var e=LIVE.homeReads[key];
    // All existing write handlers replace SNAPS. A confirmed write is authoritative.
  if(e&&e.base!==full){delete LIVE.homeReads[key];return null;}return e;};
  LIVE.snapshotFor=function(key,full){if(!LIVE.homeReadEnabled()||!full)return full;var e=LIVE.homeEntry(key,full);if(!e)return full;if(key===C.st.key&&LIVE.homeRoute())return e.value;
    // Shell/tails stay current on detail pages; never merge partial card histories.
  if(!e.chrome){e.chrome=Object.assign({},full);['instance','h1','vitals','vitals_all','vitals_cards','vitals_catalogue','device_latest','device_policy','known_sources','card_setup','wall_prefs','card_thresholds','alerts','banner','notice','device_events'].forEach(function(k){e.chrome[k]=e.value[k];});}return e.chrome;};
  LIVE.acceptHome=function(key,full,next){if(!next||next._scope!=='home'||typeof next._read_version!=='string'||!next.instance||next.instance.instance_id!==full.instance.instance_id||Object.prototype.hasOwnProperty.call(next,'timeline')||!next.vitals||!Array.isArray(next.vitals.items))throw Error('HOME_STATE_INVALID');var old=LIVE.homeEntry(key,full);LIVE.homeReads[key]={base:full,value:next};if(!old||old.value._read_version!==next._read_version){LIVE._bl=null;C.st.cpAi=null;
      // Invalidate completed on-demand reads only. In-flight requests retain their
      // original route/write generation guards; authorization is always server-side.
  if(typeof viewReads!=='undefined')viewReads.forEach(function(e,path){if(!e.promise)viewReads.delete(path);});}return next;};
  LIVE.patchDataList = function (view,html) {
    var draft=document.createElement('div');draft.innerHTML=html;
    var old=view.querySelector('[data-metric-ux="list"]'),next=draft.querySelector('[data-metric-ux="list"]');
    if(!old||!next||view.children.length!==draft.children.length)return false;
    var existing=Object.create(null),key=function(el){return el.hasAttribute('data-dcode')?'row:'+el.dataset.dcode:el.classList.contains('hd')?'heading':'empty';};
    Array.prototype.forEach.call(old.children,function(el){existing[key(el)]=el;});
    // Keep unchanged rows and their focus/selection; replace only changed results or counts.
    Array.prototype.slice.call(next.children).forEach(function(el,index){
      var prev=existing[key(el)],use=prev&&prev.outerHTML===el.outerHTML?prev:el;
      if(prev&&use!==prev)prev.replaceWith(use);
      if(old.children[index]!==use)old.insertBefore(use,old.children[index]||null);
      delete existing[key(el)];
    });
    Object.keys(existing).forEach(function(k){existing[k].remove();});
    Array.prototype.slice.call(draft.children).forEach(function(el,i){
      if(el===next)return;var prev=view.children[i];if(prev.outerHTML!==el.outerHTML)prev.replaceWith(el);
    });return true;
  };
  LIVE.refreshRoute = function () {
    var s=C.st,p=s.graphPage,graph=s.app==='torch'&&s.tview==='graph';
    return JSON.stringify([s.key,s.app,s.view,s.vitalsCardId,s.vitalsCardKey,s.tview,s.cview,s.foot,s.stateSection,s.sourceDevice,s.dataCode,s.dataSources,s.assetF,s.dataView,s.dataPage,s.deviceFamily,s.deviceMetric,s.gid,s.btOpen&&s.btOpen.id,s.btOpen&&s.btOpen.page,s.tdetail&&s.tdetail.ref,s.dataFrom,s.dataTo,s.app==='torch'&&s.tview==='data'?['metrics','rows','series'].map(function(k){return s._dataPages&&s._dataPages.slots[k]&&s._dataPages.slots[k].cursor||null;}):null,
      graph?[s.xhView,s.xhTab,p&&p.index,p&&p.cursors[p.index]]:null]);
  };
  LIVE.refreshProjection = function (snap) {
    var s=C.st;
    if(snap._scope==='home'){var home={};Object.keys(snap).forEach(function(k){if(k!=='_read_version'&&k!=='h1'&&k!=='device_events'&&k!=='notice'&&k!=='device_latest'&&k!=='device_policy')home[k]=k==='vitals'?Object.assign({},snap.vitals,{computed_at:null}):snap[k];});return home;}
    if(s.app==='torch'&&s.tview==='data')return [snap.instance,snap.timeline];
    if(s.app==='torch'&&s.tview==='detail'){
      var t=s.tdetail||{},oid=t.oid||String(t.ref||'').split('@')[0],h=snap.h1||{};
      var observation=(snap.timeline||[]).find(function(o){return o.ref===t.ref||(t.oid&&o.ref.split('@')[0]===oid);});
      return [snap.instance,observation,h.cursor_commit,h.cursor_seq,snap.runs_by_tp];
    }
    // Device connection state is read separately; new observations must not rebuild setup controls.
    if(s.app==='torch'&&s.tview==='srcgroup')return [snap.instance];
    var out={}; Object.keys(snap).forEach(function(k){if(k!=='h1'&&k!=='device_events'&&k!=='notice'&&k!=='device_latest'&&k!=='device_policy')out[k]=snap[k];});return out;
  };
  // Bind the instance before rendering can start requests, including first snapshot reads.
  LIVE.beginMainRender = function () {if(C){var route=LIVE.refreshRoute();if(LIVE._renderedRoute!==route){LIVE._renderedKey=C.st.key;LIVE._renderedRoute=route;readEpoch++;if(LIVE._dataReadSession)LIVE._dataReadSession.cancel();}}};
  LIVE.markMainRendered = function () {if(!C)return;LIVE._paintedMain={key:C.st.key,route:LIVE.refreshRoute(),snapshot:C.S()};if(!LIVE._paintedChrome||LIVE._paintedChrome.key!==C.st.key)LIVE._paintedChrome={key:C.st.key,snapshot:C.S()};};
  LIVE.canAutoPaint = function () {
    return !C.st.drawer&&!C.st.entry&&!LIVE.editing()&&!document.hidden&&!LIVE._pointerDown&&Date.now()>=(LIVE._interactionUntil||0)&&
      !document.querySelector('#view details[open], #fw, #syncpop, #pb-settings, #bd, [role="dialog"]');
  };
  LIVE.paintFreshState = function () {
    var now=C.S(),same=function(a,b){return a===b||JSON.stringify(a)===JSON.stringify(b);};
    // Readout panels keep updating while the main view is protected by an open dialog.
    // Their settings and an active pointer interaction still retain their controls.
    if(!document.hidden&&!LIVE._pointerDown&&!LIVE._tlSet&&!LIVE._desktopOpening&&Date.now()>=(LIVE._interactionUntil||0)){
      var tail=LIVE._paintedTail,src=LIVE._tlSrc;
      if(!tail||tail.key!==C.st.key||!same([tail.snapshot.vitals&&tail.snapshot.vitals.items,tail.snapshot.card_setup,tail.snapshot.device_latest,tail.snapshot.device_policy],[now.vitals&&now.vitals.items,now.card_setup,now.device_latest,now.device_policy])||!src||src.key!==C.st.key||Date.now()-src.at>=60000)LIVE.tailMount();
      LIVE._paintedTail={key:C.st.key,snapshot:now};
    }
    if(!LIVE.canAutoPaint())return; // Keep the previous painted snapshot until editing ends.
    if(LIVE.flushBridgeView)LIVE.flushBridgeView();
    if(LIVE.flushGuardHistory)LIVE.flushGuardHistory();
    var chrome=LIVE._paintedChrome,old=chrome&&chrome.key===C.st.key?chrome.snapshot:null;
    if(old){
      if(!same(old.device_events,now.device_events))LIVE.announceDevice();
      if(!same(old.notice,now.notice))LIVE.noticeMount();
      if(!same(old.alerts,now.alerts))LIVE.bellMount();
      if(C.st.app==='track'&&!same([old.h1,old.instance,old.alerts],[now.h1,now.instance,now.alerts])){C.renderAppbar();LIVE.barAgain();}
    }
    LIVE._paintedChrome={key:C.st.key,snapshot:now};
    if(LIVE.homeReadEnabled()&&!LIVE.homeRoute())return; // Detail pages reload on navigation, not on the timer.
    var p=LIVE._paintedMain;
    if(!p||p.key!==C.st.key||p.route!==LIVE.refreshRoute())return;
    var auxiliary=LIVE._baselinePaint===C.st.key&&C.st.app==='track'&&C.st.view==='wall';
    if(!auxiliary&&same(LIVE.refreshProjection(p.snapshot),LIVE.refreshProjection(now))&&C.st.app!=='cluster')return;
    if(auxiliary)LIVE._baselinePaint=null;
    var y=window.scrollY,focus=document.activeElement;
    var focusId=focus&&focus.id,focusAttr=focus&&['data-af','data-dv','data-dcode','data-ref'].find(function(a){return focus.hasAttribute&&focus.hasAttribute(a);});
    var focusValue=focusAttr&&focus.getAttribute(focusAttr);
    LIVE._incrementalMain=true;try{C.renderMainOnly();if(LIVE.addStateMount)LIVE.addStateMount();}finally{LIVE._incrementalMain=false;}
    var target=focusId&&document.getElementById(focusId);
    if(!target&&focusAttr)target=Array.prototype.find.call(document.querySelectorAll('['+focusAttr+']'),function(el){return el.getAttribute(focusAttr)===focusValue;});
    if(target)target.focus({preventScroll:true});window.scrollTo(0,y);
  };
  LIVE.baselineVersion = function(snap) {
    if(snap._read_version)return snap._read_version;
    var h=snap.h1||{};
    return JSON.stringify([h.cursor_commit,h.cursor_seq,h.inbox_rows,h.last_import_at,snap.runs_by_tp,snap.card_thresholds]);
  };
  LIVE.refreshInBackground = function () {
    if(!C||document.hidden||C.isReplay()||pendingWrites||(C.S()._pending&&!(LIVE.dataRoute&&LIVE.dataRoute()&&LIVE.homeEntry(C.st.key,C.SNAPS[C.st.key])))||(C.st.app==='track'&&C.st.view==='launch'))return Promise.resolve(false);
    if(LIVE._autoRequest)return LIVE._autoRequest;
    var key=C.st.key,start=C.SNAPS[key],epoch=readEpoch;
    var light=LIVE.homeReadEnabled();
    var request=LIVE.managedRead((light?'/api/state/refresh?key=':'/api/state?key=')+encodeURIComponent(key))
      .then(function(next){
        if(key!==C.st.key||epoch!==readEpoch||pendingWrites||C.SNAPS[key]!==start)return false;
        if(light){LIVE.acceptHome(key,start,next);LIVE.paintFreshState();return true;}
        if(!next||!next.instance||next.instance.instance_id!==start.instance.instance_id||!Array.isArray(next.timeline))throw Error('STATE_INVALID');
        C.SNAPS[key]=next; // Full authoritative payload, never a partial merge or sampled history.
        if(LIVE.baselineVersion(start)!==LIVE.baselineVersion(next)){LIVE._bl=null;C.st.cpAi=null;}
        LIVE.paintFreshState();return true;
      }).catch(function(){return false;}) // Retain the last good snapshot; next timer retries.
      .finally(function(){if(LIVE._autoRequest===request)LIVE._autoRequest=null;});
    LIVE._autoRequest=request;return request;
  };
  /* ASYNC_REFRESH_R01_END */

  // DEVICE_CONNECTION_R01: presentation over existing adapters, never implicit pairing.
  LIVE.DEVICE_CONNECTIONS = {
    pillbox: {mode:'状态暂不可用', scope:'本试用版不提供药盒配对。', steps:['本试用版不提供药盒配对。']},
    oura: {mode:'云端授权同步', scope:'按当前授权范围同步 Oura 数据，保留原始观测时间。', steps:['先在 Oura 原配应用完成指环同步。','在本页授权；若本机尚未配置接入，交由 AI 检查配置。','同步后在个人基座查看数据与来源。']},
    somaloop: {mode:'状态暂不可用', scope:'本试用版不提供 SomaLoop 接入。', steps:['本试用版不提供 SomaLoop 接入。']},
    garmin: {mode:'只读检查', scope:'本试用版不提供 Garmin 账号接入。此页只提供只读检查提示词。', steps:['阅读随包 Garmin 能力说明。','复制下方提示，只检查随包文件、版本和依赖。','本试用版不登录账号、不启动同步。']},
    qkeer: {mode:'状态暂不可用', scope:'本试用版不提供 Qkeer 接入。', steps:['本试用版不提供 Qkeer 接入。']},
    muse: {mode:'状态暂不可用', scope:'本试用版不提供 Muse 接入。', steps:['本试用版不提供 Muse 接入。']},
    whoop: {mode:'只读检查', scope:'本试用版只提供 Whoop 只读检查提示词，不提供账号接入。尚未提供连接适配器。', steps:['阅读随包 Whoop 能力说明。','复制下方提示，只检查随包文件、版本和依赖。','可提供设备型号和脱敏样例供评估。']},
    xiaomi_band: {mode:'接入准备', scope:'已加入设备目录，尚未提供小米手环连接适配器。', steps:['确认手环代数、准确型号和原配应用。','准备官方接口资料或脱敏导出样例，列出希望同步的指标。','由 AI 核验数据通路后再实施适配；当前不会采集或入库。']},
    withings_body_scan: {mode:'接入准备', scope:'已加入设备目录，尚未提供 Withings Body Scan 连接适配器。', steps:['确认设备型号、账号地区及所需指标。','准备官方接口资料或脱敏导出样例。','由 AI 核验字段、单位与观测时间后再实施适配；当前不会采集或入库。']},
    withings_body_segment: {mode:'型号核对与接入准备', scope:'按提供的名称预留目录；Body Segment 的准确型号和数据通路仍待核对，尚无连接适配器。', steps:['提供设备包装或原配应用中的准确型号。','用厂商资料核对这个型号的产品名称。','型号明确后再评估接口和字段；当前不会采集或入库。']},
    dexcom_g7: {mode:'接入准备', scope:'Dexcom G7 为连续血糖监测设备，需要置入传感器，不能归为无创设备；本版本尚无连接适配器。', steps:['确认设备使用地区、原配应用及希望导入的数据范围。','准备官方接口资料或脱敏导出样例。','由 AI 核验数据权限、单位及观测时间后再适配；当前不会采集或入库。']},
    polar_h10: {mode:'接入准备', scope:'已加入设备目录，尚未提供 Polar H10 连接适配器。', steps:['确认设备型号与希望保存的数据范围。','准备官方接口或蓝牙协议资料，核对现有连接占用。','由 AI 先核验连接和字段方案；当前不会扫描、连接或入库。']},
    eight_sleep: {mode:'接入准备', scope:'本版本尚无可用的 Eight Sleep 连接适配器。', steps:['确认床垫型号、账号地区及数据需求。','准备可提供的官方接口说明或脱敏导出样例。','由 AI 评估可用通路；未完成前不显示已连接。']},
    more: {mode:'接入评估', scope:'新增设备需先确认数据通路与字段，不能直接复用其他设备连接。', steps:['提供品牌、准确型号和期望同步的指标。','提供接口文档或脱敏文件样例，不提供密码或密钥。','让 AI 核验现有适配器，再给出实施方案。']}
  };
  LIVE.deviceConnectionPrompt = function (item) {
    var d=LIVE.DEVICE_CONNECTIONS[item.id]||LIVE.DEVICE_CONNECTIONS.more;
    return item.id==='oura'?'请协助配置本机 PTDS 的 Oura 接入。目标实例是安装时由本人选定的实例，不使用个人默认键。\n1. 先只读核对随包版本、Oura 适配器、目标实例与配置状态，阅读随包能力说明；不要读取健康数值、凭据内容或钥匙串。\n2. 指导本人在 Oura 开发者后台创建自己的应用，回调使用本机回环地址，端口与当前 PTDS 一致。\n3. 客户端密钥由本人在终端写入钥匙串，账户按目标实例隔离；非 macOS 使用已有私有 secrets 存储。Agent 不读取、不复述、不记录密钥，也不要求本人把密钥贴入聊天。旧共享条目不迁移、不回退读取。\n4. 写前备份配置，只写不含密钥的 oura 段：显式绑定选定实例及公开应用参数，不改其他通道，不自动启动服务。\n5. 由本人在浏览器完成 Oura 授权。Agent 不代替登录、同意或撤权。\n6. 授权后只读核对连接状态与最近同步时间，区分未配置、未登录、连接异常、暂无数据和已同步；不读取健康数值。涉及重启或额外改动，先说明影响并由本人确认。':(item.id==='whoop'||item.id==='garmin')?'请只读检查本机 PTDS 随包的 '+item.zh+' 能力说明、文件版本、适配器和依赖、安装时选定的目标实例及连接诊断。'+(item.id==='garmin'?'Garmin 本试用版不提供账号接入。':'Whoop 尚无连接适配器。')+'明确区分未配置、未登录、连接异常、暂无数据和已同步。不发起 OAuth，不登录账号，不读取或回传密码、令牌、密钥或健康数值，不修改配置启用通道，不启动同步或扫描设备。没有获准适配器时明确报告不支持，不显示已接入。'+(item.id==='whoop'?'可由本人提供型号和脱敏样例供后续评估。':''):'请协助 PTDS 接入 '+item.zh+'。当前产品能力：'+d.mode+'；'+d.scope+'\n请先只读检查现有适配器、账号地区、目标个人基座及连接诊断。明确区分未配置、未登录、连接异常、暂无数据和已同步；不要把其他设备的数据当作本设备。优先复用现有后台任务，避免重复启动。缺少文档或凭据时列出最少准备步骤；密码、验证码和密钥由我在本机输入，不贴入聊天。任何新增真实数据采集、目标实例变更、配置修改或服务重启，先说明具体影响再由我确认。先用虚构数据验证，报告实际完成与尚未验证项。';
  };
  LIVE.mountDeviceRecovery=function(item){
    if(item.id!=='oura')return;
    var key=C.st.key,host=document.querySelector('[data-device-connection]');if(!host)return;
    var panel=document.createElement('section');panel.className='box';panel.id='device-recovery';panel.innerHTML='<h3 data-ptds-ui="safd7bea4fb18">后台连接</h3><p role="status" data-ptds-ui="s278c80d984d4">正在检查连接状态…</p>';host.insertAdjacentElement('afterend',panel);
    var current=function(){return C.st.key===key&&C.st.sourceDevice===item.id&&panel.isConnected;};
    async function draw(){try{
      var response=await callAsync('GET','/api/device-links');if(!current())return;
      var row=response.devices.find(function(r){return r.id===item.id&&r.instance_key===key;});
      if(!row){panel.innerHTML='<h3 data-ptds-ui="safd7bea4fb18">后台连接</h3><p data-ptds-ui="s78f4d3c3f61a">当前基座未绑定此设备的后台接收。</p>';return;}
      var stamp=function(x){return x?(typeof x==='number'?new Date(x*1000).toLocaleString():C.tzTime(x,true)):'暂无';},esc=C.esc;
      panel.innerHTML='<h3>'+esc(row.message)+'</h3><div class="kv2"><span data-ptds-ui="s590b816ea7e0">连接通路</span><span>'+esc(row.transport==='band_bridge'?'Mac 蓝牙直连':row.transport==='phone_agent'?'手机 Agent · 局域网':'厂商云同步')+'</span><span data-ptds-ui="sb65085b1a290">数据保存到</span><span>'+esc(C.S().instance.display_name||key)+'</span><span data-ptds-ui="sa4c95aa09722">最近观测</span><span>'+esc(stamp(row.last_read_at))+'</span><span data-ptds-ui="s2ca565908ea0">最近成功保存 / 同步</span><span>'+esc(stamp(row.last_success_at))+'</span>'+(row.next_retry_at?'<span data-ptds-ui="s9f65912868c5">下次重试</span><span>'+esc(stamp(row.next_retry_at))+'</span>':'')+'</div><p class="sub2">'+esc(row.hint||(row.state==='NEEDS_REAUTH'?'登录或授权已失效，需要在本机更新。':row.state==='PAUSED'?'当前同步已主动暂停。':row.transport==='band_bridge'?'腕带靠近 Mac 并唤醒，手机 App 请断开腕带。Mac 蓝牙直连不依赖网络代理。':row.transport==='phone_agent'?'保持手机 Agent 可用，并与 Mac 连接同一网络；手机地址变化时需要更新地址。':'联网恢复后会从已有进度继续；如仍失败，请查看网络路径或厂商登录状态。'))+'</p><p data-retry-result role="status"></p><div style="display:flex;gap:8px">'+(row.actions.includes('retry')?'<button class="btn" data-retry>'+(row.transport==='band_bridge'?'重新连接腕带':'重试同步')+'</button>':'')+'<button class="btn2" data-status-refresh data-ptds-ui="s802a407c7743">刷新状态</button></div>';
      panel.querySelector('[data-status-refresh]').onclick=draw;var retry=panel.querySelector('[data-retry]');if(retry)retry.onclick=async function(){if(!current()||retry.disabled)return;retry.disabled=true;var result=panel.querySelector('[data-retry-result]');result.textContent='正在请求恢复…';try{var r=await callAsync('POST','/api/device-links/action',{id:item.id,instance_key:key,action:'retry'});if(current()){result.textContent=r.status==='already_running'?'已有同步任务运行中':'已请求恢复，请稍后刷新状态';}}catch(err){if(current())result.textContent=err.detail||'需要检查连接设置，请按下方提示处理';}finally{if(current())retry.disabled=false;}};
    }catch(err){if(current())panel.innerHTML='<h3 data-ptds-ui="safd7bea4fb18">后台连接</h3><p data-ptds-ui="se0f218172ea8">状态暂不可用，不能据此判断设备断开。</p><button class="btn2" data-status-refresh data-ptds-ui="sc25fb86b1e96">重新检查</button>';var b=panel.querySelector('[data-status-refresh]');if(b)b.onclick=draw;}}
    draw();
  };
  LIVE.openDeviceLink=function(){var q=new URLSearchParams(location.search);if(q.get('view')!=='device-connections')return;var key=q.get('key'),id=q.get('device');if(!C.SNAPS[key]||!['oura','garmin','qkeer','somaloop'].includes(id))return;C.st.key=key;C.st.foot=null;LIVE.openDeviceDestination(id);};
  LIVE.renderDeviceConnection = function (item) {
    var esc=C.esc,d=LIVE.DEVICE_CONNECTIONS[item.id]||LIVE.DEVICE_CONNECTIONS.more,src={},failed=false;
    var supported=['oura','pillbox'].indexOf(item.id)>=0;
    try {if(supported)src= item.id==='pillbox' ? {pillbox:readCached('/api/pillbox/status?key='+encodeURIComponent(C.st.key))} : readCached('/api/sources?key='+encodeURIComponent(C.st.key));}catch(e){ if(e&&(e.viewPending||e.code==='VIEW_CHANGED'))throw e;failed=true;}
    var info=src[item.id]||{};if(item.id==='oura'&&src.oura_configured===false)info=Object.assign({},info,{status:'NOT_CONFIGURED',last_error:null,sync_error:null,sync_status:null});
    var state=failed?'状态暂不可用':({CONNECTED:'已连接',NEEDS_REAUTH:'需要重新登录或授权',ERROR:'连接异常',DISCONNECTED:'未连接',NOT_CONNECTED:'未连接'}[info.status]||'尚未配置');
    if(info.status==='CONNECTED'&&(info.sync_error||info.last_error))state='已连接 · 同步待重试';
    if(info.sync_status==='SYNCING')state='正在同步';
    if(item.id==='pillbox')state=failed?'状态暂不可用':info.message|| (info.connected?'已连接':'未连接');
    var lastTime=info.last_pull_at;
    if(supported&&item.id==='somaloop'&&info.transport!=='phone_agent'){var band=LIVE.bandGet();state=band?LIVE.bandState(band):'状态暂不可用';
      var times=Object.keys((band||{}).latest||{}).map(function(k){return band.latest[k]&&band.latest[k].at;}).filter(function(t){return typeof t==='number'&&isFinite(t)&&t>0;});
      lastTime=times.length?new Date(Math.max.apply(null,times)*1000).toISOString():null;
    }
    if(item.id==='somaloop'&&info.transport==='phone_agent'){d={mode:'手机 Agent · 局域网缓存同步',scope:'手机缓存样本与每日指标；皮温偏差单列，时间和来源保留。',steps:['手机与 Mac 连接同一 Wi-Fi。','保持 Somaloop 打开，并开启允许 Agent 访问。','每分钟读取缓存；手机离线时自动重试，不触发厂商同步。']};if(info.status==='CONNECTED')state='手机可访问 · 腕带'+(info.device_connected?'已连接':'未连接');}
    if(!supported)state='状态暂不可用';
    var personal=C.S().instance.kind==='REAL' && !C.isReplay(), actions='<button class="btn2" id="dc-refresh" data-ptds-ui="se71c122d0302">刷新连接状态</button>';
    if(item.id==='oura'&&personal){
      actions+=(info.status==='CONNECTED'?'<button class="btn" id="dc-sync"'+(LIVE.ouraBusy?' disabled':'')+'>立即同步</button><button class="btn2" id="dc-disconnect" data-ptds-ui="sa33f3804768e">断开连接</button>':'<button class="btn" id="dc-authorize"'+(src.oura_configured?'':' disabled')+'>前往 Oura 授权</button>');
    }
    if(item.id==='pillbox'&&personal)actions+='<button class="btn" id="dc-pillbox" data-ptds-ui="s8d07216266ae">连接设置</button>';
    if(item.id==='oura'&&!src.oura_configured)actions+='<button class="btn2" id="dc-configure">去配置</button>';
    var note=!personal&&supported?'当前实例仅查看接入说明。请切换到个人数据基座管理连接，避免把个人设备数据写入演示库。':item.id==='oura'&&!src.oura_configured?'首次接入配置尚未完成，可复制 AI 接管提示协助准备。':(item.id==='qkeer'||item.id==='somaloop')?'此页不代替首次登录、蓝牙选择或凭据配置；需要时使用下方 AI 接管提示。':'';
    document.getElementById('view').innerHTML='<section class="box" data-device-connection="'+esc(item.id)+'"><h3>'+esc(item.zh)+'<span class="grow"></span><button class="btn2" id="dc-back">返回</button></h3><p class="sub2">'+esc(d.mode)+'</p><div class="kv2"><span>连接状态</span><strong>'+esc(state)+'</strong><span>当前数据基座</span><span>'+esc(C.S().instance.display_name||C.st.key)+'</span><span>'+ (item.id==='pillbox'?'连接方式':item.id==='somaloop'&&info.transport!=='phone_agent'?'最近观测':'最近成功同步') +'</span><span>'+esc(item.id==='pillbox'?'通过这台 Mac 的蓝牙连接':lastTime?C.tzTime(lastTime,true):(item.id==='somaloop'?'暂无观测记录':'暂无同步记录'))+'</span><span>数据范围</span><span>'+esc(d.scope)+'</span></div>'+(note?'<p class="sub2">'+esc(note)+'</p>':'')+'<div class="acts" style="display:flex;gap:8px;flex-wrap:wrap">'+actions+'</div></section><section class="box"><h3>连接步骤</h3><ol>'+d.steps.map(function(t){return '<li>'+esc(t)+'</li>';}).join('')+'</ol></section><section class="box"><h3>需要 AI 协助接入？</h3><p class="sub2">提示只包含设备名称与排查要求，不包含账号、密钥或健康读数。</p><details><summary>查看接管提示</summary><pre style="white-space:pre-wrap;overflow-wrap:anywhere;font:inherit">'+esc(LIVE.deviceConnectionPrompt(item))+'</pre></details><button class="btn2" id="dc-copy" style="justify-self:start">复制 AI 接管提示</button></section>';
    document.getElementById('dc-back').onclick=function(){C.st.sourceDevice=null;C.render();};
    document.getElementById('dc-refresh').onclick=function(){LIVE._tlSrc=null;C.render();};
    document.getElementById('dc-copy').onclick=function(){var text=LIVE.deviceConnectionPrompt(item),row=globalThis.PTDS_LANGUAGE_RESOURCES?.messages[{"oura": "device_e5c62a05441a", "whoop": "device_d39cd338e316", "garmin": "device_db088d4f7fc1"}[item.id]];if(globalThis.PTDS_LANGUAGE?.current()==='en' && row && row.zh===text)text=row.en;if(navigator.clipboard&&navigator.clipboard.writeText)navigator.clipboard.writeText(text).then(function(){C.toast('已复制接管提示');},function(){C.toast('复制未成功，请展开提示后手动复制');});else C.toast('请展开提示后手动复制');};
    var b=document.getElementById('dc-authorize');if(b)b.onclick=function(){location.href='/oauth/oura/start?key='+encodeURIComponent(C.st.key);};
    b=document.getElementById('dc-sync');if(b)b.onclick=function(){if(LIVE.ouraBusy)return;LIVE.ouraBusy=true;this.disabled=true;this.textContent='正在同步…';callAsync('POST','/api/oura/sync',{key:C.st.key}).then(function(){C.toast('Oura 同步完成');},function(e){C.toast('同步未完成：'+LIVE.ouraErr(e.code));}).then(function(){LIVE.ouraBusy=false;LIVE._tlSrc=null;if(C.st.sourceDevice===item.id)C.render();});};
    b=document.getElementById('dc-disconnect');if(b)b.onclick=LIVE.action(async function(){try{(await call('POST','/api/oura/disconnect',{key:C.st.key}));LIVE._tlSrc=null;C.toast('已断开，已有记录保留');C.render();}catch(e){ if(e&&(e.viewPending||e.code==='VIEW_CHANGED'))throw e;C.toast('断开未完成，请刷新状态后重试');}});
    if(item.id==='oura'&&(!globalThis.PTDS_TRIAL_UI||PTDS_TRIAL_UI.can('erasure'))){var eh=document.querySelector('[data-device-connection="oura"]'),ek=C.st.key;LIVE.ouraErasureModule(function(m){if(C.st.key===ek&&eh&&eh.isConnected)m.mount({host:eh,key:ek,C:C,LIVE:LIVE,call:call,callAsync:callAsync,item:item});});}
    b=document.getElementById('dc-pillbox');if(b)b.onclick=function(){LIVE.pillboxSettings();};
    b=document.getElementById('dc-configure');if(b)b.onclick=function(){var e=document.querySelector('details');if(e)e.open=true;var x=document.getElementById('dc-copy');if(x)x.focus();};
    LIVE.mountDeviceRecovery(item);
  };

  // Read boundaries may retry only rendering. User mutations are never replayed.
  LIVE.renderReadError=function(err,retry,target){
    if(!err||!err.viewPending||!C)return false;
    var path=err.path,e=viewReads.get(path),loading=!!(e&&e.promise),node=document.createElement('section');
    node.className=target?'box':'box ptds-read-screen';node.dataset.readWait='1';
    var timedOut=e&&e.error&&e.error.name==='AbortError';
    node.innerHTML=LIVE.readingHtml(target?'compact':'page',loading?'loading':timedOut?'timeout':'error',timedOut?'本次读取超时，已保存的数据仍然保留。可稍后重新读取。':'内容暂未读取成功，已保存的数据仍然保留。')+
      '<div class="ptds-read-actions"><button class="btn2" data-read-retry'+(loading?' disabled hidden':'')+'>重新读取</button>'+(!target?'<button class="link" data-read-home data-ptds-ui="sd66f4359dae3">返回首页</button>':'')+'</div>';
    var host=target||document.getElementById('view');if(!host)return true;
    var dataRoot=host.querySelector('[data-data-root]');
    var keepData=!target&&path&&path.indexOf('/api/data/read?')===0&&C.st.app==='torch'&&C.st.tview==='data'&&dataRoot&&dataRoot.dataset.owner===C.st.key&&dataRoot.dataset.instance===C.S().instance.instance_id&&
      host.dataset.dataOwner===C.st.key&&host.dataset.dataCode===(C.st.dataCode||'')&&host.dataset.dataView===(C.st.dataView||'code');
    if(keepData){
      var oldWait=host.querySelector('[data-read-wait]');if(oldWait)oldWait.remove();
      node.className='box';
      node.innerHTML='<p role="status">'+(loading?'正在更新，下面保留上次读取的内容。':'更新未完成，下面保留上次读取的内容。')+'</p><button class="btn2" data-read-retry'+(loading?' disabled hidden':'')+'>重新读取</button>';
      host.querySelectorAll('[data-ref],[data-dcode],[data-page-prev],[data-page-next]').forEach(function(b){b.disabled=true;});
      host.prepend(node);
    }else{delete host.dataset.dataOwner;host.replaceChildren(node);}
    if(target){var close=document.createElement('button');close.className='ibtn ptds-read-close';close.textContent='关闭';close.setAttribute('aria-label','关闭加载');close.onclick=function(){if(target.id==='fw')LIVE.closeTrace();else if(target.id==='kg-pop'){C.st.kgSel=null;C.st.kgPopAll=false;LIVE.kgDraw();}else C.closeDrawer();};node.prepend(close);}
    var home=node.querySelector('[data-read-home]');
    if(home)home.onclick=function(){C.closeDrawer();C.st.foot=null;C.setSeg('data-app','track');C.st.view='launch';C.render();};
    var resume=retry||function(){C.render();},key=C.st.key,route=viewRoute();
    if(/^DATA_(VIEW_CHANGED|CURSOR_INVALID)$/.test(err.code||'')){var originalResume=resume;resume=function(){LIVE.invalidateData();originalResume();};}
    node.querySelector('[data-read-retry]').onclick=function(){
      if(C.st.key!==key||viewRoute()!==route)return;
      // A retry must never duplicate an in-flight full-state read.
      var current=viewReads.get(path);if(current&&current.promise)return;
      viewReads.delete(path);resume();
    };
    readWaiters.set(path,{node:node,key:key,route:route,retry:resume});
    if(e&&!e.promise&&e.value!==undefined)flushReadBoundary(path);
    return true;
  };
  LIVE.ensureState=function(){
    if(!C||!C.SNAPS[C.st.key])return true;
    var key=C.st.key,full=C.SNAPS[key],light=LIVE.homeReadEnabled(),entry=light&&LIVE.homeEntry(key,full);
    var receipt=C.st.tview==='detail'&&C.st.tdetail&&C.st.tdetail.mode==='receipt'?C.st.tdetail.res:C.st.tview==='entry'&&C.st.entry&&C.st.entry.step==='receipt'?C.st.entry.result:null;
    if(C.st.app==='torch'&&!C.st.foot&&LIVE.isConfirmedWrite&&LIVE.isConfirmedWrite(key,receipt))return true;
    // Each read model owns its own loading/retry boundary.
    if(C.st.app==='torch'&&C.st.tview==='graph'&&!C.st.foot&&!C.isReplay()&&
        (LIVE.graphReadV2()||(C.st.xhView!=='records'&&C.st.graphJump!=='eg-diary')))return true;
    var home=light&&(LIVE.homeRoute()||(LIVE.dataRoute&&LIVE.dataRoute()))&&!C.isReplay();
    if(home&&(entry||!full._pending))return true;
    if(!home&&!full._pending&&(!entry||full._read_version===entry.value._read_version))return true;
    var path=(home?'/api/state/refresh?key=':'/api/state?key=')+encodeURIComponent(key);
    if(!home&&!LIVE.fullHydrations[path])LIVE.fullHydrations[path]={base:full,version:entry&&entry.value._read_version};
    try{
      var next=readCached(path);
      var binding=LIVE.fullHydrations[path];
      if(!home&&binding&&(binding.base!==full||binding.version!==(entry&&entry.value._read_version))){
        delete LIVE.fullHydrations[path];viewReads.delete(path);return LIVE.ensureState();
      }
      if(home)LIVE.acceptHome(key,full,next);
      else{
        if(!next||!next.instance||next.instance.instance_id!==full.instance.instance_id||!Array.isArray(next.timeline)||next._scope==='home')throw Error('STATE_INVALID');
        C.SNAPS[key]=next;delete LIVE.homeReads[key];
        LIVE.loadGene(key).catch(function(){});
      }
      delete LIVE.fullHydrations[path];viewReads.delete(path);return true;
    }catch(e){if(!e.viewPending){e.viewPending=true;e.path=path;viewReads.set(path,{error:e,epoch:readEpoch});}LIVE.renderReadError(e);return false;}
  };
  LIVE.action=function(fn){
    if(typeof fn!=='function')return fn;
    return function(){
      var self=this,args=arguments;
      if(self&&self._ptdsActionBusy)return;
      var result,disabled=self&&self.disabled;
      try{result=fn.apply(self,args);}catch(err){if(err&&err.viewPending){C.toast('数据正在读取，请稍后再次操作');return;}throw err;}
      if(!result||typeof result.then!=='function')return result;
      if(self){self._ptdsActionBusy=true;if('disabled'in self)self.disabled=true;}
      return result.catch(function(err){if(err&&err.code==='VIEW_CHANGED')return;if(C)C.toast(err.detail||LIVE.saveErr(err));})
        .finally(function(){if(self){self._ptdsActionBusy=false;if('disabled'in self)self.disabled=disabled;}});
    };
  };
  // These render functions can also be called directly by page buttons/timers.
  ['renderFw','renderGraph','kgPop','renderAdvanced','renderBatch','renderBatchOpen','renderBatchTypes','renderBatchMap','renderMeds','renderGene','renderEngCustom','renderRules','renderShare','renderDeviceConnection'].forEach(function(name){
    var render=LIVE[name];if(!render)return;
    LIVE[name]=function(){
      if(name==='renderGraph'&&C.st.graphJump==='eg-diary')C.st.xhView='records';
      var args=arguments,self=this,key=C.st.key,route=viewRoute(),fw=C.st.fw;
      function failed(err){
        if(key!==C.st.key||route!==viewRoute())return;
        var host=null;
        if(name==='renderFw'){
          if(!fw||C.st.fw!==fw)return;
          host=document.getElementById('fw');
          if(!host){host=document.createElement('aside');host.id='fw';host.className='fw';host.setAttribute('role','dialog');document.body.appendChild(host);}
        }
        if(name==='kgPop'){
          if(!args[0]||C.st.kgSel!==args[0].id)return;
          var canvas=document.getElementById('kg-canvas');if(!canvas)return;
          host=document.getElementById('kg-pop');
          if(!host){host=document.createElement('div');host.id='kg-pop';host.className='kg-pop';host.style.top='16px';host.style.left='16px';host.setAttribute('role','dialog');host.setAttribute('aria-label','状态溯源');canvas.appendChild(host);}
        }
        if(!LIVE.renderReadError(err,function(){if((name!=='renderFw'||C.st.fw===fw)&&(name!=='kgPop'||C.st.kgSel===args[0].id))LIVE[name].apply(self,args);},host))throw err;
      }
      try{var out=render.apply(self,args);return out&&typeof out.then==='function'?out.catch(failed):out;}catch(err){return failed(err);}
    };
  });

  window.PTDS_LIVE = LIVE;
  /* 星灵按钮和琥珀框在星炬各页也要用：样式开页就装好，不等进状态实验室 */
  if (!document.getElementById('cp-css')) { var cpStl = document.createElement('style'); cpStl.id = 'cp-css'; cpStl.textContent = LIVE.CP_CSS + SRC_CSS; document.head.appendChild(cpStl); }
})();

// 界面批注模式：网址加 ?note=1 打开。点页面任意处写一句意见，存到本机 ~/PTDS-instances/ui-notes/notes.jsonl
(function () {
  if (!/[?&]note=1\b/.test(location.search)) return;
  var on = true, notes = [], bar, layer;
  function req(m, u, b) {
    return fetch(u, { method: m, headers: { 'Content-Type': 'application/json', 'X-PTDS': '1' }, body: b ? JSON.stringify(b) : undefined })
      .then(function (r) { return r.json(); });
  }
  function esc(t) { return String(t).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function sel(el) {
    var parts = [];
    while (el && el.nodeType === 1 && parts.length < 5 && el !== document.body) {
      var p = el.tagName.toLowerCase();
      if (el.id) { parts.unshift(p + '#' + el.id); break; }
      if (typeof el.className === 'string' && el.className.trim()) p += '.' + el.className.trim().split(/\s+/).slice(0, 2).join('.');
      parts.unshift(p); el = el.parentElement;
    }
    return parts.join(' > ');
  }
  function page() {
    var st = (window.PTDS_LIVE && window.PTDS_LIVE.pageState && window.PTDS_LIVE.pageState()) || {};
    var h = document.querySelector('h1, h2');
    return { page: [st.app, st.view, st.tview, st.key].filter(Boolean).join('/'), page_zh: h ? h.textContent.trim().slice(0, 40) : document.title };
  }
  function draw() {
    bar.querySelector('#pn-n').textContent = notes.length;
    bar.querySelector('#pn-on').textContent = on ? '批注中（点这里暂停）' : '已暂停（点这里继续）';
    bar.style.background = on ? '#b45309' : '#475569';
    var cur = page().page;
    layer.innerHTML = notes.map(function (n, i) {
      if (n.page !== cur) return '';
      return '<div title="' + esc(n.text) + '" data-id="' + n.id + '" style="position:fixed;left:' + (n.x - 11) + 'px;top:' + (n.y - 11) + 'px;width:22px;height:22px;border-radius:11px;background:#dc2626;color:#fff;font:bold 12px/22px sans-serif;text-align:center;pointer-events:auto;cursor:pointer;box-shadow:0 1px 4px rgba(0,0,0,.4)">' + (i + 1) + '</div>';
    }).join('');
  }
  function load(){return window.PTDS_LIVE.managedRead('/api/notes').then(function(r){notes=r.notes||[];draw();}).catch(function(){});}
  function start() {
    if(globalThis.PTDS_TRIAL_UI&&!PTDS_TRIAL_UI.can('notes'))return; layer = document.createElement('div');
    layer.style.cssText = 'position:fixed;inset:0;pointer-events:none;z-index:99998';
    bar = document.createElement('div');
    bar.id = 'ptds-note-bar';
    bar.style.cssText = 'position:fixed;right:12px;bottom:12px;z-index:99999;color:#fff;border-radius:8px;padding:8px 10px;font:13px sans-serif;display:flex;gap:8px;align-items:center;box-shadow:0 2px 8px rgba(0,0,0,.3)';
    var b = 'background:rgba(255,255,255,.2);color:#fff;border:0;border-radius:5px;padding:4px 8px;cursor:pointer;font:13px sans-serif';
    bar.innerHTML = '批注 <b id="pn-n">0</b> 条 <button id="pn-on" style="' + b + '"></button><button id="pn-md" style="' + b + '">导出</button><button id="pn-clr" style="' + b + '">清空</button>';
    document.body.appendChild(layer); document.body.appendChild(bar);
    bar.querySelector('#pn-on').onclick = function () { on = !on; draw(); };
    bar.querySelector('#pn-md').onclick = function () { location.href = '/api/notes?format=md'; };
    bar.querySelector('#pn-clr').onclick = function () {
      if (confirm('清空全部 ' + notes.length + ' 条批注？')) req('POST', '/api/notes', { op: 'clear' }).then(load);
    };
    layer.addEventListener('click', function (e) {
      var id = e.target.getAttribute && e.target.getAttribute('data-id');
      var n = notes.filter(function (x) { return x.id === id; })[0];
      if (!n) return;
      e.stopPropagation();
      if (confirm('批注：' + n.text + '\n\n删除这条？')) req('POST', '/api/notes', { op: 'delete', id: id }).then(load);
    });
    // 捕获阶段拦截点击，产品本身不会响应
    document.addEventListener('click', function (e) {
      if (!on || bar.contains(e.target) || layer.contains(e.target)) return;
      e.preventDefault(); e.stopPropagation();
      var text = prompt('这里要怎么改？');
      if (!text || !text.trim()) return;
      var p = page();
      req('POST', '/api/notes', { text: text, page: p.page, page_zh: p.page_zh, sel: sel(e.target),
        snippet: (e.target.innerText || e.target.value || '').trim().slice(0, 80), x: e.clientX, y: e.clientY,
        vw: innerWidth, vh: innerHeight, url: location.pathname + location.search }).then(load)
        .catch(function () { alert('批注没存上：本机服务没响应'); });
    }, true);
    window.PTDS_LIVE.readTimer(draw,1000);
    load();
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start); else start();
})();
