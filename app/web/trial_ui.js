/* Distribution display only. The HTTP policy still checks the target on every request.
 * A single stylesheet covers later renders, without listeners, timers or DOM scans. */
(function (root) {
  'use strict';
  const entries = Object.freeze({
    homeEdit: ['POST /api/home', '#home-tgear,[data-hedit]'],
    cluster: ['GET /api/cluster/list', '[data-mod="cluster"],[data-v="cluster"],[data-xmod="cluster"],[data-xapp="cluster"],[data-xmod="cluster"] + .xtiles,[data-sqgo="cluster"],#to-cluster-obj,#eng-cluster'],
    laboratory: ['GET /api/track/compete_ai', '[data-nav2="adv"],[data-nt-rule],#bl-adjust,#bl-rec'],
    cards: ['POST /api/track/card', '[data-nav2="eng"],#w-new,#add-state,#eng-hidden,#act-recompute,#pull-sync,#retry-sync'],
    rules: ['GET /api/rules', '[data-nav2="rules"],#gcov-rule,.rl-ic'],
    wall: ['POST /api/track/wall', '.wpin,.wgear,[data-wm],#w-pins>.sub2'],
    thresholds: ['GET /api/track/thresholds', '[data-bd-threshold],#cc-thr,#th-open'],
    batch: ['GET /api/batch/list', '[data-method="batch"],[data-go="entry:batch"],#go-batch'],
    recognition: ['POST /api/torch/recognize', '[data-method="ocr"],[data-go="entry:ocr"],#sp-ocr'],
    medication: ['GET /api/meds', '[data-method="meds"],[data-go="entry:meds"]'],
    genes: ['GET /api/gene', '[data-go="gene"],[data-nav2="gene"]'],
    geneImport: ['POST /api/gene', '#gene-pick'],
    geneLookup: ['GET /api/gene/lookup', '#gene-go'],
    geneCoverage: ['GET /api/gene/coverage', '#gene-coverage'],
    geneDelete: ['POST /api/gene/delete', '[data-gene-delete]'],
    pack: ['POST /api/evidence/pack', '.eg-sc,#ev-go'],
    notes: ['GET /api/notes', '#ptds-note-bar'],
    muse: ['GET /api/muse/status', '#data-muse,[data-go="muse"],[data-go="device:muse"],[data-device-kind="bci"]'],
    phone: ['GET /api/phone-tail/status', '[data-grp="phone"],[data-go="apple"],#phone-start,#phone-invite,[data-phone-setup]'],
    band: ['GET /api/band', '[data-go="device:somaloop"],[data-go="device:qkeer"],#band-tail,#btail'],
    bridge: ['GET /api/bridge/state', '[data-go="bridge"],[data-bridge],[data-action="start_band_bridge"]'],
    finder: ['POST /api/graph/reveal', '[data-reveal],[data-reveal-status]'],
    calendar: ['POST /api/alerts/calendar', '[data-bd-cal],[data-nt-cal]'],
    profile: ['POST /api/profile', '#et-prof,#g-prof'],
    tails: ['POST /api/sources/tail', '[data-tl-set],[data-desktop-pin],[data-tl-share],#tl-set'],
    push: ['GET /api/state-push/status', '[data-state-push],#sp-reports,#state-tab-push'],
    offset: ['GET /api/track/baseline', '#state-tab-offset,[data-bl-rule]'],
    acknowledgement: ['POST /api/track/ack', '[data-nt-x],[data-bd-ack],[data-cc-ack]'],
    graphMap: ['GET /api/graph/kg', '[data-xh-view="map"]'],
    erasure: ['POST /api/oura/raw/erase', '[data-oura-erasure]'],
    compute: ['POST /api/compute/retry', '#ptds-compute-status button,[data-compute-retry]'],
    starlingActions: ['POST /api/starling/ask', '#sq-fab,#sq,[data-foot="spirit"],[data-sp-page],[data-sp-trace],[data-cp-ask],#weekly-focus-go,[data-nt-sp]'],
    correct: ['POST /api/torch/correct', '#t-edit,#c-save'],
    retract: ['POST /api/torch/retract', '#t-retract,#r-ok'],
    csv: ['POST /api/torch/table', '[data-method="table"],[data-go="entry:table"]'],
    authorize: ['GET /oauth/oura/start', '#dc-authorize'],
    sync: ['POST /api/oura/sync', '#dc-sync'],
    disconnect: ['POST /api/oura/disconnect', '#dc-disconnect']
  });
  let allowed = new Set(), homeDefaults = null;
  function defaultHome() { return homeDefaults; }
  function can(id) { return !!entries[id] && allowed.has(entries[id][0]); }
  function install(doc, caps) {
    allowed = new Set();
    for (const m of ['GET', 'POST']) for (const path of (caps && caps[m]) || []) allowed.add(m + ' ' + path);
    homeDefaults = can('homeEdit') ? null : Object.freeze({
      get title() { return root.PTDS_LANGUAGE_RESOURCES.messages.launch_motto.zh; },
      edited_title: false, cards: Object.freeze({})
    });
    let style = doc.getElementById('trial-availability');
    if (!style) { style = doc.createElement('style'); style.id = 'trial-availability'; doc.head.appendChild(style); }
    const denied = Object.keys(entries).filter(id => !can(id)).map(id => entries[id][1]);
    style.textContent = (denied.length ? denied.join(',') + '{display:none!important}' : '') +
      '[lang="en"] .trial-only-zh,html:not([lang="en"]) .trial-only-en{display:none!important}';
  }
  function blocked(st) {
    if (st.foot === 'spirit') return !can('starlingActions');
    let entry;
    if (st.app === 'cluster') entry = 'cluster';
    if (st.app === 'track') entry = ({adv:'laboratory',eng:'cards',rules:'rules'})[st.view];
    if (st.app === 'track' && st.view === 'wall' && ['push','offset'].includes(st.stateSection)) entry = st.stateSection;
    if (st.app === 'torch') {
      entry = ({gene:'genes',apple:'bridge'})[st.tview];
      if (st.tview === 'graph' && st.xhView !== 'records' && st.graphJump !== 'eg-diary') entry = 'graphMap';
      if (st.tview === 'entry' && st.entry) entry = ({batch:'batch',ocr:'recognition',meds:'medication'})[st.entry.method];
      if (st.tview === 'srcgroup') {
        if (st.srcGroup === 'phone') entry = 'bridge';
        if (st.srcGroup === 'wearable' && (st.museOpen || st.sourceDevice === 'muse' || st.deviceKind === 'bci')) entry = 'muse';
        if (st.srcGroup === 'wearable' && ['somaloop','qkeer'].includes(st.sourceDevice)) entry = 'band';
      }
    }
    return !!entry && !can(entry);
  }
  function showBlocked(st, doc) {
    if (!blocked(st)) return false;
    doc.getElementById('view').innerHTML = '<p><span class="trial-only-zh">伙伴版未提供此功能。</span><span class="trial-only-en">This feature is unavailable in the partner edition.</span></p>';
    return true;
  }
  function renderGene(core, call, invalidate) {
    const view = document.getElementById('view');
    const scope = document.createElement('section');
    scope.className = 'panel';
    scope.id = 'partner-gene';
    view.replaceChildren(scope);
    const key = core.st.key, instance = core.S().instance;
    const current = () => scope.isConnected && core.st.key === key && core.S().instance.instance_id === instance.instance_id;
    function node(parent, tag, text) {
      const el = document.createElement(tag);
      if (text != null) el.textContent = text;
      parent.appendChild(el);
      return el;
    }
    function words(parent, id) {
      const pair = root.PTDS_PARTNER_CATALOG['gene_'+id];
      ['zh','en'].forEach((lang,i) => {node(parent,'span',pair[i]).className = 'trial-only-'+lang;});
    }
    function action(parent, id, handler) {
      const button = node(parent, 'button');
      button.className='btn'; button.type='button'; words(button,id);
      button.onclick = async () => {
        if (!current() || button.disabled) return;
        button.disabled = true;
        try {await handler();} catch(error) {if(current()) feedback(error);}
        finally {button.disabled=false;}
      };
      return button;
    }
    function line(parent, id, value) {
      const el=node(parent,'p'); words(el,id);
      if (value != null) el.append(' · '+value);
      return el;
    }
    const heading=node(scope,'h2'); words(heading,'title');
    const destination=line(scope,'destination'); node(destination,'span',instance.display_name).id='gene-instance-name'; line(scope,'scope'); line(scope,'remove_help');
    const form=node(scope,'section');
    const selection=node(form,'fieldset'); words(node(selection,'legend'),'nature');
    const chosen=(instance.accept || []).filter(v=>v==='SYNTHETIC'||v==='REAL');
    const choices=chosen.map(kind=>{
      const label=node(selection,'label'), radio=node(label,'input');
      radio.type='radio';radio.name='gene-nature';radio.value=kind;
      radio.checked=kind===instance.default_nature || chosen.length===1;
      words(label,kind.toLowerCase());return radio;
    });
    const file=node(form,'input'); file.type='file'; file.hidden=true;
    const notice=node(scope,'p'); notice.setAttribute('role','status');
    function feedback(error) {
      notice.replaceChildren();
      const codes={BODY_TOO_LARGE:'limit',FILE_TOO_LARGE:'limit',NATURE_INVALID:'nature_error',NATURE_NOT_ACCEPTED:'nature_error',QUERY_FORMAT:'query_error'};
      words(notice,codes[error.message]||'failed');
    }
    async function request(path, params={}, init) {
      const query=new URLSearchParams({key,...params});
      const writing=init?.method==='POST', raw=init?.body instanceof Blob;
      const data=await call(writing?'POST':'GET',path+'?'+query,init?.body,raw,init?.headers);
      if(writing) {
        invalidate(key);
        if(core.st.geneFiles) delete core.st.geneFiles[instance.instance_id];
      }
      if (!current()) throw Error('VIEW_CHANGED');
      return data;
    }
    const choose=action(form,'pick',()=>file.click());choose.id='gene-pick';
    choose.hidden=!can('geneImport');
    if (!chosen.length || instance.replay) choose.disabled=true;
    file.onchange=async ()=>{
      const selected=file.files[0]; if(!selected||!current())return;
      const choice=choices.find(input=>input.checked);
      if(!choice){feedback(Error('NATURE_INVALID'));file.value='';return;}
      choose.disabled=true;
      try {
        await request('/api/gene',{nature:choice.value},{method:'POST',headers:{'X-PTDS':'1','X-File-Name':encodeURIComponent(selected.name),'Content-Type':'application/octet-stream'},body:selected});
        notice.replaceChildren(); words(notice,'saved'); await refresh();
      }catch(error){if(current())feedback(error);}
      finally{choose.disabled=false;file.value='';}
    };
    const files=node(scope,'section'), lookup=node(scope,'section'), coverage=node(scope,'section');
    const queryLabel=node(lookup,'label'); words(queryLabel,'locus');
    const term=node(queryLabel,'input'); term.id='gene-q';
    const hits=node(lookup,'div');
    const search=action(lookup,'lookup',async()=>{
      const result=await request('/api/gene/lookup',{q:term.value});
      hits.replaceChildren(); line(hits,'matches',result.rows.length);
      result.rows.forEach(row=>node(hits,'p',[row.rsid,row.chrom,row.pos,row.genotype,row.file_name].join(' · ')));
    });
    search.id='gene-go';search.hidden=!can('geneLookup');
    const summary=node(coverage,'div');
    const assess=action(coverage,'coverage',async()=>{
      const result=await request('/api/gene/coverage');
      summary.replaceChildren();line(summary,'covered_files',result.files.length);
      result.files.forEach(file=>{
        node(summary,'h3',file.file_name);
        line(summary,'rows',file.rows_total); line(summary,'valid',file.valid_genotypes);
        for (const entry of file.matrix || []) {
          const ref=entry.rsid || (entry.position && entry.chromosome+':'+entry.position);
          if(ref) {const p=node(summary,'p',ref+' · ');const id='status_'+entry.direct_observation_status;
            if(root.PTDS_PARTNER_CATALOG['gene_'+id])words(p,id);else words(p,'status_unknown');}
        }
      });
    });
    assess.id='gene-coverage';assess.hidden=!can('geneCoverage');
    let sequence=0;
    async function refresh() {
      const id=++sequence, records=await request('/api/gene');
      if(id!==sequence)return;
      core.st.geneFiles[instance.instance_id]=records.slice().reverse().map(f=>({name:f.file_name,when:core.tzTime(f.received_at),batch:f.receipt_id,nature:f.nature}));
      files.replaceChildren();
      line(files,'files',records.length);
      for(const record of records) {
        const row=node(files,'article');row.className='box';
        node(row,'h3',record.file_name);
        const profile=record.profile||{};
        if(['PROFILE_FAILED','BINARY','UNKNOWN_TEXT'].includes(profile.format_code)) line(row,'unknown');
        else line(row,'format',profile.format_code || '—');
        if(record.nature==='REAL'||record.nature==='SYNTHETIC') words(node(row,'p'),record.nature.toLowerCase());
        line(row,'bytes',record.bytes);if(profile.lines_total!=null)line(row,'lines',profile.lines_total);
        if((profile.snps??profile.variants)!=null)line(row,'sites',profile.snps??profile.variants);
        const remove=action(row,'delete',()=>{
          if(row.querySelector('[data-gene-confirm]'))return;
          const confirmation=node(row,'div');confirmation.dataset.geneConfirm='';
          line(confirmation,'confirm_info',record.file_name);
          action(confirmation,'confirm_delete',async()=>{
            await request('/api/gene/delete',{}, {method:'POST',headers:{'X-PTDS':'1','Content-Type':'application/json'},body:{sha256:record.sha256}});
            hits.replaceChildren();summary.replaceChildren();notice.replaceChildren();words(notice,'deleted');
            await refresh();
          });
          action(confirmation,'cancel',()=>confirmation.remove());
        });
        remove.dataset.geneDelete='';remove.hidden=!can('geneDelete')||instance.replay;
      }
    }
    refresh().catch(error=>{if(current())feedback(error);});
  }

  root.PTDS_TRIAL_UI = Object.freeze({install, can, defaultHome, showBlocked, renderGene, entries});
})(typeof window === 'undefined' ? globalThis : window);
