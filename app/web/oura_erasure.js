/* Oura-only, same-origin local UI. No token/request persisted in URL or storage. */
(function (global) {
  'use strict';
  var text = {
    changed:'要擦除的内容有变化，请重新预览', expired:'确认已超过 5 分钟，请重新预览',
    pending:'上次的擦除没有完成', delayed:'原始数据已擦除，擦除记录稍后补写',
    revokeFailed:'撤销授权没有完成，原始数据没有删除'
  };
  function mount(o) {
    var host=o.host,key=o.key,C=o.C,LIVE=o.LIVE,doc=host.ownerDocument;
    if(host.dataset.erasureMounted)return;
    host.dataset.erasureMounted='1';
    function active(){return host.isConnected&&C.st.key===key&&C.st.sourceDevice===o.item.id;}
    var section=doc.createElement('section');section.className='box';section.dataset.ouraErasure='1';host.appendChild(section);
    var generation=0,preview=null,busy=false,request=null,dead=false,ready=false,controllers=new Set();
    function el(tag,content){var e=doc.createElement(tag);if(content!==undefined)e.textContent=content;return e;}
    function button(label,fn){var e=el('button',label);e.type='button';e.className='btn2';e.onclick=fn;section.appendChild(e);return e;}
    function clear(){section.replaceChildren(el('h3','擦除'));}
    function note(t){section.appendChild(el('p',t));}
    async function api(action,body){
      var c=new AbortController();controllers.add(c);
      try{
        var r=await global.fetch('/api/oura/raw/erase/'+action,{method:'POST',credentials:'same-origin',headers:{'X-PTDS':'1','Content-Type':'application/json'},body:JSON.stringify(Object.assign({key:key},body||{})),signal:c.signal});
        var v=await r.json();if(!r.ok)throw Object.assign(new Error('erasure request rejected'),{code:v.error});return v;
      }finally{controllers.delete(c);}
    }
    function valid(g){return !dead&&active()&&g===generation;}
    function error(e){note(e.code==='ERASURE_CONFIRMATION_EXPIRED'?text.expired:e.code==='ERASURE_REMOTE_REVOKE_FAILED'?text.revokeFailed:text.changed);}
    function result(v){
      clear();preview=null;
      if(v.status==='PENDING'){note(text.pending);button('继续完成',function(){resume(v.erasure_id);});return;}
      if(v.status==='NOT_STARTED'){note(text.changed);button('擦除 Oura 原始数据…',function(){show(false,false);});return;}
      note(v.evidence_pending?text.delayed:'原始数据已擦除；擦除记录编号：'+v.event_id);
      if(v.missing_sources)note('已擦除 '+v.bodies_deleted+' 个；'+v.missing_sources+' 个来源无法核对，已记录');
      if(v.evidence_pending)button('继续完成',function(){resume(v.erasure_id);});
    }
    async function resume(id){
      if(busy||!active())return;busy=true;var g=++generation;
      try{var v=await api('resume',{erasure_id:id});if(valid(g))result(v);}catch(e){if(valid(g)){clear();note(text.pending);button('继续完成',function(){resume(id);});}}finally{busy=false;}
    }
    async function show(archives,revoke){
      if(busy||!ready||!active())return;busy=true;var g=++generation;preview=null;
      try{
        var v=await api('preview',{include_archives:archives,revoke:revoke});if(!valid(g))return;
        clear();if(v.pending_erasure){note(text.pending);if(v.pending_erasure.resumable)button('继续完成',function(){resume(v.pending_erasure.erasure_id);});return;}
        preview=v;request=v.request_id;note('擦除前请确认范围');
        note('将删除 Oura 原始文件 '+v.files+' 个，共 '+(v.bytes/1048576).toFixed(2)+' MB，日期 '+(v.date_from||'—')+'–'+(v.date_to||'—'));
        ['已导入的正式数据不会删除，仍可查看','会留下一条擦除记录：只有数量、日期和校验码，没有原始内容','系统快照、Time Machine 或其他备份里可能还有副本，本应用无法删除'].forEach(note);
        if(v.missing_sources)note('有 '+v.missing_sources+' 个来源无法核对，将如实记录，不会猜测删除');
        function check(label,value,fn,disabled){var e=el('input');e.type='checkbox';e.checked=value;e.disabled=!!disabled;var l=el('label');l.appendChild(e);l.appendChild(doc.createTextNode(label));section.appendChild(l);if(fn)e.onchange=fn;return e;}
        check('一并删除旧版档案（备份库 '+v.archives.backups+' 个、隔离库 '+v.archives.quarantines+' 个，共 '+(v.archives.bytes/1048576).toFixed(2)+' MB）',archives,function(e){show(e.target.checked,revoke);});
        check('同时断开 Oura 并撤销授权',revoke,function(e){show(archives,e.target.checked);},!v.revoke_available);
        if(!revoke)note('不断开的话，下次同步会重新下载原始数据');
        var checked=check('我了解这一步不可撤回',false),word=el('input');word.type='text';word.placeholder='请输入"擦除"';word.autocomplete='off';section.appendChild(word);
        var cancel=button('取消',async function(){if(busy)return;busy=true;var g=++generation;preview=null;try{await api('cancel');}catch(ignore){}finally{busy=false;if(valid(g))home();}});
        var go=button('确认擦除',async function(){
          if(busy||!active()||!preview||!checked.checked||word.value!=='擦除')return;
          busy=true;go.disabled=true;cancel.disabled=true;var current=preview,attempt=++generation;preview=null;
          try{
            var r=await api('execute',{request_id:current.request_id,preview_digest:current.preview_digest,include_archives:current.include_archives,revoke:current.revoke,confirmation_token:current.confirmation_token,checked:true,word:word.value});
            if(valid(attempt))result(r);
          }catch(e){
            // An ambiguous response never resends a mutation or changes UUID.
            if(valid(attempt)&&e.code==='ERASURE_REMOTE_REVOKE_FAILED'){clear();error(e);button('擦除 Oura 原始数据…',function(){show(false,false);});}
            else if(valid(attempt)){clear();error(e);button('继续完成',async function(){if(busy||!active())return;busy=true;var g=++generation,id=request;try{var q=await api('status',{request_id:id});if(valid(g))result(q);}catch(ignore){if(valid(g))note(text.pending);}finally{busy=false;}});}
          }finally{busy=false;}
        });go.disabled=true;
        function enable(){go.disabled=busy||!checked.checked||word.value!=='擦除';}
        checked.onchange=enable;word.oninput=enable;
      }catch(e){if(valid(g)){clear();error(e);button('擦除 Oura 原始数据…',function(){show(false,false);});}}finally{busy=false;}
    }
    function home(){clear();button('擦除 Oura 原始数据…',function(){show(false,false);});}
    function destroy(){if(dead)return;dead=true;++generation;preview=null;controllers.forEach(function(c){c.abort();});controllers.clear();observer.disconnect();}
    var observer=new MutationObserver(function(){if(!active())destroy();});observer.observe(doc.body,{childList:true,subtree:true});
    home();var g=generation;buttonReady(false);
    function buttonReady(value){var b=section.children[1];if(b&&b.tagName.toLowerCase()==='button')b.disabled=!value;}
    api('inspect').then(function(v){if(!valid(g))return;ready=true;buttonReady(true);if(v.pending_erasure){clear();note(text.pending);if(v.pending_erasure.resumable)button('继续完成',function(){resume(v.pending_erasure.erasure_id);});}else if(v.receipt&&v.receipt.evidence_pending){result(v.receipt);}else if(v.has_erased_sources)note('原件已擦除');},function(){if(valid(g)){ready=true;buttonReady(true);}});
    return {destroy:destroy};
  }
  function markSource(o){
    var controller=new AbortController(),observer=new MutationObserver(function(){if(!o.current())controller.abort();});
    observer.observe(o.host.ownerDocument.body,{childList:true,subtree:true});
    global.fetch('/api/oura/raw/erase/source',{method:'POST',credentials:'same-origin',headers:{'X-PTDS':'1','Content-Type':'application/json'},body:JSON.stringify({key:o.key,source_ref:o.source_ref}),signal:controller.signal}).then(function(r){return r.ok?r.json():null;}).then(function(v){if(v&&v.originals_erased&&o.current()){var p=o.host.ownerDocument.createElement('p');p.textContent='原件已擦除';o.host.appendChild(p);}},function(){}).finally(function(){observer.disconnect();});
    return function(){controller.abort();observer.disconnect();};
  }
  global.PTDS_OURA_ERASURE={mount:mount,markSource:markSource};
})(typeof window!=='undefined'?window:globalThis);
