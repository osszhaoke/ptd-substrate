(async()=>{
 const send=obj=>window.webkit.messageHandlers.fixtureResult.postMessage(JSON.stringify(obj));
 const wait=(ms=130)=>new Promise(r=>{window.__ptdsTestWake=r;window.webkit.messageHandlers.fixtureResult.postMessage('delay:'+ms);});
 const writes=[],raw=window.fetch;window.fetch=function(url,opt){if(opt?.method && opt.method!=='GET')writes.push([opt.method,String(url).split('?')[0]]);return raw.apply(this,arguments);};
 const $=s=>document.querySelector(s), all=s=>[...document.querySelectorAll(s)],x=window.__ptds, lang=PTDS_LANGUAGE, rows=[];
 async function until(fn){for(let i=0;i<75;i++){if(fn())return;await wait();}throw Error('route not reached');}
 async function visit(name,start,sel){try{start();await until(()=>$(sel));await wait();const cn=scanEnglishScreen(document);
 if(window.keepShots){for(const a of document.getAnimations())if(Number.isFinite(a.effect?.getComputedTiming().endTime))a.finish();await wait(50);await new Promise(r=>{window.__shotDone=r;window.webkit.messageHandlers.fixtureResult.postMessage('shot:'+name);});}
 
 const footerEn=$('#disc').textContent;
 const snapshot=name==='home'?PTDS_LANGUAGE_RESOURCES.messages.launch_disclaimer.zh:window.__ptds_core.S().disclaimer;
 lang.select('zh');const footerZh=$('#disc').textContent;lang.select(window.walkLang);
 const labels={};for(const selector of ['#side','#tl-pillbox','#sq-fab','.sp-icon-only','#f-date','#f-time']){const el=$(selector);if(el&&el.getClientRects().length)labels[selector]=[el.getAttribute('aria-label'),el.getAttribute('title')];}
 
 for (const el of document.querySelectorAll('#sq-fab,[data-foot="spirit"],[data-sp-page]')) {el.focus();if(document.activeElement===el)throw Error('STARLING_ENTRY_VISIBLE');}
 const starlingFocusable=[...document.querySelectorAll('#sq-fab,[data-foot="spirit"],[data-sp-page]')].filter(el=>el.getClientRects().length && el.tabIndex>=0).length;
 rows.push({name,cn,labels,starlingFocusable,footerEn,footerZh,snapshot,activeKey:x.st.key,footer:$('#disc')?.textContent,lang:document.documentElement.lang,reload:$('#data-reload')?.innerText,summary:all('.dcode .sub2.hs').map(el=>el.innerText),overview:all('[data-overview-codes]').map(el=>[el.title,el.innerText]),plots:all('.mx-plot').map(el=>el.getAttribute('aria-label'))});}catch(e){rows.push({name,error:String(e)});}}
 try{
 if(sessionStorage.r11Walk){
   const prior=JSON.parse(sessionStorage.r11Walk);delete sessionStorage.r11Walk;
   await until(()=>$('[data-launch]'));if($('#first-language')?.open || document.documentElement.lang!==(window.walkLang==='en'?'en':'zh-CN'))throw Error('RELOAD_LANGUAGE_LOST');
   $('[data-launch]').click();await until(()=>$('#inst') && $('#disc').textContent===PTDS_LANGUAGE_RESOURCES.messages.launch_disclaimer[window.walkLang]);
   send({...prior,reloadFooter:$('#disc').textContent});return;
 }
 $('#first-language [data-pick='+window.walkLang+']').click();await visit('home',()=>{},'.launch');$('[data-launch]').click();await until(()=>!$('.launch') && $('#inst')); await wait(600);
 await visit('wall',()=>x.goTrack('wall'),'#w-pins');
 await visit('overview',()=>x.goTorch('guard'),'#g-all');
 await visit('sources',()=>x.goTorch('sources'),'[data-grp]');
 await visit('wearable',()=>$('[data-grp=wearable]').click(),'[data-device-kind]');
 for(const kind of ['ring','band','bed','scale','glucose','chest_strap','pillbox','more']){
  await visit(kind,()=>{x.st.srcGroup='wearable';x.st.deviceKind=kind;x.st.sourceDevice=null;x.goTorch('srcgroup');},'#src-back');
 }
 await visit('file',()=>{x.st.srcGroup='file';x.st.deviceKind=null;x.goTorch('srcgroup');},'#src-back');
 await visit('gene',()=>{const b=$('[data-go="gene"]');if(!b||!b.getClientRects().length)throw Error('GENE_ENTRY_HIDDEN');b.click();},'#partner-gene');
 await visit('gene-lookup',()=>{$('#gene-q').value='rs990000001';$('#gene-go').click();},'#partner-gene');
 await visit('gene-coverage',()=>$('#gene-coverage').click(),'#partner-gene');
 if($('[data-gene-delete]'))await visit('gene-delete-confirm',()=>$('[data-gene-delete]').click(),'[data-gene-confirm]');
 const testFile = new File(['RSID,CHROMOSOME,POSITION,RESULT\nrs990000099,1,81999,AG\n'],'browser-fixture.csv',{type:'text/plain'});
 const dt=new DataTransfer();dt.items.add(testFile);
 const picker=$('#partner-gene input[type=file]');picker.files=dt.files;picker.dispatchEvent(new Event('change'));
 await until(()=>all('#partner-gene article h3').some(el=>el.textContent==='browser-fixture.csv'));
 $('#gene-q').value='rs990000099';$('#gene-go').click();await until(()=>$('#partner-gene').innerText.includes('81999'));
 const row=all('#partner-gene article').find(el=>el.querySelector('h3')?.textContent==='browser-fixture.csv');
 row.querySelector('[data-gene-delete]').click();row.querySelector('[data-gene-confirm] button').click();
 await until(()=>!all('#partner-gene article h3').some(el=>el.textContent==='browser-fixture.csv'));
 await visit('records',()=>{x.st.xhView='records';x.st.graphJump='eg-diary';x.goTorch('graph');},'[data-xh-tab]');
 await visit('map',()=>{x.st.xhView='map';x.st.graphJump=null;x.goTorch('graph');},window.walkHasData?'#kg-box':'[data-ptds-ui="se5b69c643ba6"]');

 for(const [kind,dev] of [['ring','oura'],['band','whoop'],['band','garmin']]){
  await visit(dev,()=>{x.st.srcGroup='wearable';x.st.deviceKind=kind;x.st.sourceDevice=dev;x.goTorch('srcgroup');},'[data-device-connection]');
 }
 const dev=document.querySelector('[data-device-connection] ~ section details');
 if(dev){dev.open=true;await visit('garmin-setup',()=>{},'[data-device-connection]');}
 for(const tab of ['data','state','auth']){
  await visit('log-'+tab,()=>{x.st.xhView='records';x.st.xhTab=tab;x.st.graphJump='eg-diary';x.goTorch('graph');},'#graph-history-body');
 }
 await visit('my-data',()=>x.goTorch('data'),'[data-dv]');
 if($('[data-af=file]')){
   await visit('file-history',()=>{$('[data-dv=time]').click();},'#view .lrow.c6');
   await visit('file-filter',()=>{$('[data-af=file]').click();},'[data-af=file][aria-pressed=true]');
   await until(()=>document.querySelector('[data-gene-row-source]'));
   const geneSource=document.querySelector('[data-gene-row-source]').textContent.trim();
   if(geneSource!==(window.walkLang==='en'?'File · Stored locally · Synthetic':'文件 · 纳管 · 合成示例'))throw Error('GENE_NATURE_LANGUAGE');
 }
 await visit('manual',()=>{x.st.entry=window.__ptds_core.newEntry();x.st.entry.method='manual';x.goTorch('entry');},'[data-method]');
 await visit('csv-import',()=>{x.goTorch('sources');},'[data-grp=file]');
 $('[data-grp=file]').click();await until(()=>$('[data-go="entry:table"]'));$('[data-go="entry:table"]').click();await until(()=>$('#t-pick'));$('#t-pick').click();await until(()=>$('#t-review'));$('#t-review').click();
 await visit('csv-review',()=>{},'#t-confirm');
 const beforeLanguage=writes.length;lang.select('zh');await wait();const zh=$('#inst .ret')?.textContent,discZh=$('#disc').textContent;lang.select('en');await wait();const en=$('#inst .ret')?.textContent;
 lang.select(window.walkLang);sessionStorage.r11Walk=JSON.stringify({discZh,discEn:$('#disc').textContent,rows,back:[zh,en],instance:$('#inst b')?.textContent,writes:window.languageWrites,writeRoutes:writes,languageWrites:writes.length-beforeLanguage});location.reload();
 }catch(e){send({error:String(e),rows});}
})();
