/* Explicit presentation bindings: never translate data rows or user-supplied text. */
(function (root) {
  'use strict';
  var groups = {'全部':'All', '穿戴设备':'Wearables', '文件报告':'Files and reports', '手机健康':'Phone health', '手动录入':'Manual entry'};
  var plural = new Intl.PluralRules('en');
  function noun(n, one, many){return plural.select(Number(n)) === 'one' ? one : many;}
  function numeric(source) {
    var m;
    if ((m = /^(全部|穿戴设备|文件报告|手机健康|手动录入) (\d+)条$/.exec(source))) return groups[m[1]] + ' · ' + m[2] + ' ' + noun(m[2], 'record', 'records');
    if ((m = /^第 (\d+) \/ (\d+) 页$/.exec(source))) return 'Page ' + m[1] + ' of ' + m[2];
    if ((m = /^指标 (\d+) 项$/.exec(source))) return m[1] + ' ' + noun(m[1], 'metric', 'metrics');
    if ((m = /^(\d+) 条$/.exec(source))) return m[1] + ' ' + noun(m[1], 'record', 'records');
    if ((m = /^当前第 (\d+)–(\d+) 条／共 (\d+) 条 · 分段完整展示$/.exec(source))) return m[1] === '0' && m[2] === '0' ? 'No records' : (m[1] === m[2] ? 'Record ' + m[1] : 'Records ' + m[1] + '–' + m[2]) + ' of ' + m[3] + ' · Shown in sections';
    return null;
  }
  // Each rule is a fixed UI callsite, never a data-row heuristic.
  var rules = [];
  function rule(selector,ids,format,attribute){rules.push({selector:selector,ids:ids,format:format,attribute:attribute});}
  function data(selector,ids,format){rule('[data-data-root] '+selector,ids,format);}
  data('[data-dv]',['by_metric','by_time']);data('[data-af]',[],numeric);
  var controls={'#data-muse':['muse_sessions'],'#data-reload':['reread'],'#data-source-clear':['all_sources'],'#data-range-clear':['all_dates'],'[data-page-prev]':['newer'],'[data-page-next]':['older'],'#dc-back':['all_metrics'],'#data-range':['view_range'],'#data-range-all':['all_history']};
  Object.keys(controls).forEach(function(s){data(s,controls[s]);});
  rule('[data-data-root] .chips',['view_mode'],null,'aria-label');
  data('.opts > label',['from_date','to_date']);data('.opts > .sub2',[],numeric);
  data('.ends > span',[],numeric);data('h3 > .sub2',[],numeric);
  ['.lrow.hd > span','.dcode.hd > span'].forEach(function(s){data(s,['metric_name','value','timepoint','source','latest','trend_order','count_recent'],numeric);});
  data('section.box > p.sub2',['no_data']);rule('[data-data-root] > p',['history_kept']);
  rule('[data-star-read] .ptds-read-kicker',['loading_kicker']);
  rule('[data-star-read] .ptds-read-title',['loading_content','read_timeout','read_unavailable']);
  rule('[data-star-read]',['loading_content'],null,'aria-label');
  rule('[data-read-retry]',['read_retry']);rule('[data-read-home]',['home_return']);
  rule('[data-read-wait] > p',['updating_kept','update_failed_kept']);
  rule('.ptds-read-close',['close','close_loading']);rule('.ptds-read-close',['close','close_loading'],null,'aria-label');
  rule('.ptds-read-screen .ptds-read-detail',['read_timeout_detail','read_error_detail']);
  rule('#state-sections .xh-tabs button > b',['cards','offset','push']);
  rule('#state-sections .xh-tabs button > .sub2',['cards_desc','offset_desc','push_desc']);
  rule('#state-sections .xh-tabs',['categories'],null,'aria-label');
  rule('#state-sections .xh-tabs .state-dot',['updated'],null,'aria-label');
  rule('#state-sections .xh-tabs .state-dot',['updated'],null,'title');

  const fixedSlots = {"我的关注": "s9dccba0eafbb", "全部": "s5c55a67935af", "每天变化（设备）": "s822799569cc7", "化验与报告": "sd4660c5075d4", "近期数据接入": "s53e8ea63c06d", "近期数据更新": "se990128f4255", "最近数据留痕": "s313a340bf348", "查看全部 · 我的数源": "s57a3022d4eb2", "查看全部 · 我的数据": "s0d3b79fd2ec8", "查看全部 · 数据日记": "sa6039e504c5d", "数据导航": "sfb4d602bd99f", " · 返回首页": "sf7e9b3566372", "来自穿戴设备": "sd6dc3f787dd5", "来自文件报告": "s3d262416fecd", "来自手动录入": "s2cdcdf7b93a0", "来自手机健康": "s323bc9b48725", "手环": "s83a14687d620", "指环": "s58243c3e75f5", "智能床垫": "s1ed24c2e1ab4", "智能体重秤": "s0ffe5f13c518", "其他": "sd2909f1647e7", "脑机接口": "s1846176c488b", "智能药盒": "sf672b098fefa", "心率带": "sad648812b300", "连续血糖监测": "s3524855ca02a", "连续血糖监测仪": "sde17b8ff187b", "数据记录": "sd46482186b17", "状态记录": "s64a158789357", "授权记录": "s26a66a3a4cd0", "数据从哪来、哪天入库、哪个版本": "s2b7ed1c05f57", "每次计算用了哪些数据、按哪版规则": "s8c342febe644", "给了谁、怎么给、给了什么、结果": "s35b84cd6ac52", "条数据": "s2a090e4ccc29", "个来源": "s68450f43fd47", "我的数源": "sb55368237d57", "证据图谱": "se6051b9b8965", "三类记录": "sbe1b7b96085c", "读取最新记录": "s0d5f2d169fae", "按类别显示": "s3096c565c4c5", "返回": "s572cf45ba436", "还没有数据。": "s4a5a256833d0", "还没有接入任何数源。": "sbe6d74b0cfa2", "还没有留痕。": "s01e676307d8e", "选择设备，查看接入方式、连接状态与准备步骤。": "s6480b2dc5bce", "更多设备": "s0b17bb7df4d9", "更多手环、指环、手表": "s13d6f0e9ef71", "CIRQA · Garmin Connect 同步": "s52fa49255fbc", "化验单识别": "s547a5beaaaa9", "拖入一份化验单，在这台电脑上识别成指标，逐项确认后保存": "s3596635daf3f", "CSV 表格": "sb03159187c77", "按模板整理好的表格，逐行检查后整份保存": "sdc6fa9014f95", "Excel、XML 表格": "s7505e37be2a1", "表头与 CSV 模板相同": "s84e7745d5509", "基因测序数据": "s8d548e77958d", "纳入星炬管理（纳管），目前没有卡片使用": "s347bcd907570", "苹果健康": "s6675bf417df5", "iPhone 上的健康 App。在 iPhone 上点一下，把里面的数据同步到星炬": "sf8444325d4f5", "谷歌健康": "sc3986a455bd9", "Android 手机上的 Health Connect": "s383db06e5401", "小米健康": "sb6b8a238f626", "经 Health Connect 中转，兼容性待验证": "sa593620e87f0", "华为健康": "sf8a5d4aa0f36", "独立生态，接入条件待验证": "sf3c7c57ac64a", "手工录入": "s05fd0cca0594", "逐项填写数值和单位，星炬按字典换算": "s590bcf6f9b5c", "指环、手环接入后，读数自动进入我的数据": "s804f9cd19221", "化验单、表格、基因测序数据": "s8d34a5a366b5", "手机健康 App 里已经汇总的数据": "sb5820e13af2f", "自己填写的观察值": "s9326ab917c06", "规划中": "s1a462d56add8", "可用": "s4d99c976beb8", "开发中": "s78c33fbf0e2a", "已适配": "s4b523c685246", "早期测试": "s974af7a1b55d", "下一页": "s8a8542f69648", "我的体征": "sd1cf5de0c8e7", "状态卡片": "sf809c22a7f16", "我的状态": "s43f6b291ab80", "还没有钉住的卡片。点任意一张卡左上角的图钉，它就会放到这里；再点一次放回原来那一栏。": "sb22ebb44a0d4"};
  function owned(selector, words, attribute) {
    rule(selector,words.map(word=>fixedSlots[word]).filter(Boolean),null,attribute);
  }
  owned('#w-pins .wsec, #view > .wsec, .wall > .wsec', ["我的关注", "全部", "每天变化（设备）", "化验与报告"]);
  owned('#w-pins > .sub2', ["还没有钉住的卡片。点任意一张卡左上角的图钉，它就会放到这里；再点一次放回原来那一栏。"]);
  owned('.grid3eq > section > h3', ["近期数据接入", "近期数据更新", "最近数据留痕"]);
  owned('#g-all,#g-src,#g-trail', ["查看全部 · 我的数源", "查看全部 · 我的数据", "查看全部 · 数据日记"]);
  owned('.grid3eq > section > .sub2, .gsum > span', ['条数据','个来源','还没有数据。','还没有接入任何数源。','还没有留痕。']);
  owned('[data-grp] .ttl,[data-device-kind] .nm,.srcard[data-go] .nm,section.box:has(#src-back) > h3', ["来自穿戴设备", "来自文件报告", "来自手机健康", "来自手动录入", "手环", "指环", "智能床垫", "智能体重秤", "其他", "脑机接口", "智能药盒", "心率带", "连续血糖监测", "连续血糖监测仪", "更多设备", "化验单识别", "CSV 表格", "Excel、XML 表格", "基因测序数据", "苹果健康", "谷歌健康", "小米健康", "华为健康", "手工录入"]);
  owned('[data-grp] .sub2,.srcard[data-go] .sub2,section.box:has(#src-back) > .sub2,.srcard .mtag',[...["指环、手环接入后，读数自动进入我的数据", "化验单、表格、基因测序数据", "手机健康 App 里已经汇总的数据", "自己填写的观察值", "指环", "手环", "指环", "手环", "脑机接口", "更多手环、指环、手表", "CIRQA · Garmin Connect 同步", "智能床垫", "拖入一份化验单，在这台电脑上识别成指标，逐项确认后保存", "按模板整理好的表格，逐行检查后整份保存", "表头与 CSV 模板相同", "纳入星炬管理（纳管），目前没有卡片使用", "iPhone 上的健康 App。在 iPhone 上点一下，把里面的数据同步到星炬", "Android 手机上的 Health Connect", "经 Health Connect 中转，兼容性待验证", "独立生态，接入条件待验证", "逐项填写数值和单位，星炬按字典换算", "选择设备，查看接入方式、连接状态与准备步骤。"]]);
  owned('[data-grp] .stat .k',['条数据']);
  owned('#src-back',['返回']);
  rule('[data-device-kind] .sub2',[],function(v){const m=/^(\d+) 款设备$/.exec(v);return m ? m[1]+(m[1]==='1'?' device':' devices'):null;});
  owned('[data-xh-tab] b,[data-xh-tab] .sub2,#graph-history-refresh,#graph-page-prev,#graph-page-next', ["数据记录", "状态记录", "授权记录", "数据从哪来、哪天入库、哪个版本", "每次计算用了哪些数据、按哪版规则", "给了谁、怎么给、给了什么、结果", "读取最新记录", "上一页", "下一页"]);
  owned('#eg-diary .xh-tabs',['三类记录'],'aria-label');
  ['text','title','aria-label','placeholder'].forEach(function(kind){
    const attr='data-ptds-ui'+(kind==='text'?'':'-'+kind);
    rules.push({selector:'['+attr+']',marker:attr,attribute:kind==='text'?null:kind});
  });
  rules.push({selector:'[data-ptds-inline]', inline:true});
  const tailIds = {"全部": "partner_5c55a67935af", "证据图谱": "partner_e6051b9b8965", "数据源": "partner_186be2232e2c", "原件": "partner_c8d7aa3a3745", "指标": "partner_b87e67c7dae0", "位点库": "partner_a59a3ee49670", "状态卡": "partner_9c17110fa620", "结论": "partner_14163a5df29f", "提醒": "partner_8f29b3132ccf", "通道": "partner_0c04098e48ab", "授权": "partner_6cf2531ab111", "对象": "partner_53f92c063963", "我自己": "partner_1ab21cbd9c87", "颜色：": "partner_87a3a198a41c", "知识图谱": "partner_60dd357bbdf2", "点图里的任意一个点，这里列出它是什么、和谁有关系、依据是哪本账。": "partner_705def27e839", "小米手环": "partner_09de9b14e706", "更多设备": "partner_0b17bb7df4d9", "智能药盒 · 电量与响铃寻找": "partner_7f37548c8c2a", "开发中": "partner_78c33fbf0e2a", "可用": "partner_4d99c976beb8", "早期测试": "partner_974af7a1b55d", "规划中": "partner_1a462d56add8", "已适配": "partner_4b523c685246", "近期数据接入": "partner_53e8ea63c06d", "给": "partner_6e55fb9d8a3d", "记录了": "partner_9a7b4b451f46", "提供": "partner_9e9470471ff0", "用于计算": "partner_a3ea877a5cbd", "最新结论": "partner_8c33ebff5708", "显示读数": "partner_b02a852847cc", "发出提醒": "partner_e36fc896908b", "已送达": "partner_1fb12e48bde3", "未送达": "partner_0421e4dbe3ac", "授权给出": "partner_17f30f15c115", "按类别显示": "partner_3096c565c4c5", "去我的数据看": "partner_ba33354c30da", "手环 · 接入待适配": "partner_f3cfae122e1c", "智能体重秤 · 接入待适配": "partner_bf337b8502b7", "连续血糖监测 · 接入待适配": "partner_e654b21c7e9c", "心率带 · 接入待适配": "partner_e699e1005261", "智能体重秤 · 型号待核对 · 接入待适配": "partner_52b903e3b63c"};
  const resources = root.PTDS_LANGUAGE_RESOURCES.messages;
  const tail = v => resources[tailIds[v]]?.en;
  const literalPart = value => {
    const parts=value.split(' · ');let changed=false;
    const result=parts.map(s=>{const e=tail(s);if(e)changed=true;return e||s;});
    return changed?result.join(' · '):null;
  };
  rule('.wsec', [tailIds['全部']]);
  rule('#kg-box > h3', [tailIds['证据图谱']]);
  rule('#kg-box > h3 > .sub2',[],v=>{const m=/^(\d+) 个点 · (\d+) 条关系$/.exec(v);return m?m[1]+' '+noun(m[1],'node','nodes')+' · '+m[2]+' '+noun(m[2],'connection','connections'):null;});
  rule('#kg-svg',[tailIds['知识图谱']],null,'aria-label');
  rule('.kg-leg',[tailIds['按类别显示']],null,'aria-label');
  rule('#kg-side > .sub2,#kg-side > div:first-child > .sub2,#kg-svg .kg-el',Object.values(tailIds));
  rule('[data-device-kind] .sub2,.srcard[data-go] .nm,.srcard[data-go] .sub2,.srcard .mt',[],v=>tail(v)||literalPart(v));
  rule('[data-grp] .sub2',[],v=>{
    const parts=v.split(' · ').map(s=>/^(\d+) 项(可用|开发中|规划中|早期测试)$/.exec(s));
    return parts.every(Boolean)?parts.map(m=>m[1]+' '+tail(m[2]).toLowerCase()).join(' · '):null;
  });
  rule('#appbar .crumb .t',[],v=>{const k=fixedSlots[v];return k && ['来自穿戴设备','来自文件报告','来自手动录入','来自手机健康'].includes(v)?resources[k].en:null;});
  const graphKinds = {source:['数据源','Data source'],document:['原件','Original file'],indicator:['指标','Metric'],store:['位点库','Variant store'],card:['状态卡','State card'],conclusion:['结论','Conclusion'],alert:['提醒','Reminder'],channel:['通道','Channel'],grant:['授权','Permission'],party:['对象','Recipient']};
  function metric(id, original) {
    if (!id || !id.startsWith('code:')) return null;
    const row = root.PTDS_LANGUAGE_RESOURCES.messages['metric_'+id.slice(5)];
    return row && root.PTDS_LANGUAGE_RESOURCES.matchesSource('metric_'+id.slice(5),original) ? row.en : null;
  }
  // Server-generated labels may resemble personal names. Call only with a typed owner.
  const metricNames=new Map();
  for(const [key,row] of Object.entries(resources)) if(key.startsWith('metric_') && key!=='metric_name'){
    const original=root.PTDS_PARTNER_CATALOG?.[key]?.[2]==='legacy-brand'?row.zh.replace('Qkeer','QKeer'):row.zh;
    metricNames.set(original,metricNames.has(original) && metricNames.get(original)!==row.en?null:row.en);
  }
  function template(owner,value){
    if (!owner) return null;
    let m;
    if(owner==='observation' && (m=/^(保存|更正|撤回) (.+?) ((?:[<>≤≥-]?[0-9]+(?:[.][0-9]+)?)(?: [^·]+)?) · 第 ([0-9]+) 版 · (合成|手动录入|表格导入|Oura|Garmin|Qkeer)$/.exec(value))){
      const names={保存:'Saved',更正:'Corrected',撤回:'Retracted',合成:resources.source_synthetic.en,手动录入:'Manual entry',表格导入:'Table import'};
      return names[m[1]]+' '+(metricNames.get(m[2])||m[2])+' '+m[3]+' · Version '+m[4]+' · '+(names[m[5]]||m[5]);
    }
    if(owner==='gene-file' && value.startsWith('纳管基因数据 '))return 'Imported genetic file '+value.slice('纳管基因数据 '.length);
    if(owner==='commit' && (m=/^交给星轨 · ([0-9]+) 条$/.exec(value)))return 'Sent to StarTrack · '+m[1]+' '+noun(m[1],'record','records');
    if(owner==='table-file' && (m=/^表格导入 (\d{2}-\d{2} \d{2}:\d{2})$/.exec(value)))return 'Table import '+m[1];
    if(owner==='G-001'||owner==='G-002'){
      const fixed=owner==='G-001'?{'我自己':'Myself','系统预置授权 · 全部状态卡':'Preset access · All state cards','新建授权 · 本机通道：Mac 通知、手环':'Permission created · Local channels: Mac notifications and wristband'}:{'主治医生（示例）':'Treating doctor (example)','系统预置授权 · sJIA 关注卡':'Preset access · sJIA focus card'};
      return fixed[value]||null;
    }
    return null;
  }
  function graphText(el, value) {
    const n=el.closest('[data-kg]');
    if(n){
      const kind=n.getAttribute('data-kg-type'), name=n.getAttribute('data-kg-label');
      const pair=graphKinds[kind], id=n.getAttribute('data-kg');
      let en=kind==='indicator'?metric(id,name):null;
      if(kind==='source' && id==='src:SYNTHETIC' && name===resources.source_synthetic.zh)en=resources.source_synthetic.en;
      if(kind==='document' && /^doc:TABLE:/.test(id))en=template('table-file',name);
      if(id==='src:GENE' && name==='基因测序数据')en=resources.s8d548e77958d.en;
      if(id==='store:gene' && name==='基因位点库')en=resources.gene_store_name.en;
      if(kind==='document' && id.startsWith('gene:G-') && name.startsWith('基因文件 '))en='Genetic file '+name.slice(5);
      if(kind==='party' && id==='party:self' && name==='我自己')en=tail(name);
      if(kind==='grant' && id.startsWith('grant:')){
        const gid=id.slice(6);
        if(name==='授权 '+gid+' · 推送')en='Permission '+gid+' · Push';
        if(name==='授权 '+gid+' · 读取')en='Permission '+gid+' · Read';
      }
      if(el.localName==='title') return pair && value===pair[0]+'：'+name ? pair[1]+': '+(en||name) : null;
      return en ? (en.length>20 ? en.slice(0,20)+'…' : en) : null;
    }
    const id=el.getAttribute('data-kg-go') || el.getAttribute('data-kg-detail');
    if(id) return /^doc:TABLE:/.test(id)?template('table-file',value):metric(id,value);
    const pair=graphKinds[el.getAttribute('data-kg-kind')];
    if(pair && value.startsWith(pair[0]+' '))return pair[1]+value.slice(pair[0].length);
    return null;
  }
  rules.push({selector:'g[data-kg] > title,g[data-kg] > text,[data-kg-go],[data-kg-detail],[data-kg-kind]',graph:true});
  const deviceCopy = ["device_995c8bad9efe", "device_984ba272fb1a", "device_68ca9afc4a41", "device_6363d6ecb5c3", "device_e3724929414c", "device_1eeee8d390ed", "device_32559941e647", "device_f68014f2b164", "device_e5f4577dc27c", "device_5171fac32c0c", "device_a1c8e03c9f0c", "device_f7659d494778", "device_6fbb0d1a8946", "device_a4a82f5ad4d4", "device_5fc968550650", "device_fd26d2fa22b0", "device_f3548ada1cb4", "device_e0e30f9f06e1", "device_751f410cad9f", "device_b6f3303d0714", "device_942bd2b9db4f", "device_1e743d200048", "device_17edaabbad12", "device_4a53f603261e", "device_2788a13a7777", "device_c7617fa73e20", "device_051e3f172e6b", "device_996064035b3a", "device_97fe751d31af", "device_d2c5dd609a38", "device_3d466b044ab8", "device_21dec63bc36c", "device_88d2f93efc57", "device_0d16eb92da0e", "device_1e643339e026", "device_d85b09d6c43e", "device_87036102bfbb", "device_00f6e264edf9", "device_4343ad757e92", "device_cae949d9ccd1", "device_81002ff82cfd", "device_2cebdddd360e", "device_bb540a99b58f", "device_d494071290a1", "device_43cef0a68c2e", "device_cbd59b967e79", "device_9dec64f7e511", "device_5aa26160e9de", "device_48fcc61c3c35", "device_b48696b38986", "device_6f4ed66ab503", "device_ba98c1c17a54", "device_ace421ab9edf", "device_0c0379b7a815", "device_1bd7b5ee9127", "device_0e28c9bfa4f5", "device_0308ff3f2f1c", "device_7e12b343d9bb", "device_f6f85999e4b9", "device_038e362d878e", "device_0e2067b674ba", "device_d28090ba080a", "device_4040149dda64", "device_572cf45ba436", "device_b8f945ea49ff", "device_b47b72ee1664", "device_3afbb05dc459", "device_2ccd68f256d5", "device_9bf79639ee77", "device_e983a7b097c6", "device_12532dbccf5f", "device_f51bc1439591", "device_c4791f28d54f", "device_d1f1cdef6a47", "device_9b39a38ff63e", "device_707e3cbd0abd", "device_c6afacac4d20", "device_50f703856d78", "device_4913c0ebf67b", "device_bc11ba8e5a04", "device_beb902fddf1a", "device_7dbc4d81020f", "device_e3a33cb53ef3", "device_f91af23d4d5a", "device_c9b9ae7a6144", "device_8a8542f69648", "device_4f8cf23dd84d", "device_a30216d4003e", "device_d2342efd86fa", "device_521e65ffc7d0", "device_4a98d9b2e395", "device_21c04b2eeeb4", "device_91ead424189d", "device_2ba3eaf59636", "device_f88dc65910c7", "device_e5c62a05441a", "device_d39cd338e316", "device_db088d4f7fc1"];
  rule('[data-device-connection] h3,[data-device-connection] > p,[data-device-connection] .kv2 > :not(:nth-child(4)),[data-device-connection] button,[data-device-connection] ~ section > h3,[data-device-connection] ~ section li,[data-device-connection] ~ section > p,[data-device-connection] ~ section summary,[data-device-connection] ~ section pre,[data-device-connection] ~ section #dc-copy',deviceCopy);
  rule('#graph-page-prev,#graph-page-next',deviceCopy);
  rule('#graph-page-count',[],v=>{const m=/^第 (\d+) 页 · 本页 (\d+) 条 \/ 本次共 (\d+|—) 条$/.exec(v);return m?'Page '+m[1]+' · '+m[2]+' on this page / '+m[3]+' total':null;});
  rule('#graph-history-body > .sub2',[],v=>({'还没有':'No ','数据记录。':'data records yet.','计算记录。':'calculation records yet.'})[v]||null);
  rule('#graph-history-body .xh-r > span:nth-child(4),#graph-history-body .xh-r > span:nth-child(6)',deviceCopy);
  rule('.steps > span,[data-method],[data-tm],[data-flag],#flagsbox > div > .sub2,#sub-back',["entry_fixed_0", "entry_fixed_1", "entry_fixed_2", "entry_fixed_3", "entry_fixed_4", "entry_fixed_5", "entry_fixed_6", "entry_fixed_7", "entry_fixed_8", "entry_fixed_9", "entry_fixed_10", "entry_fixed_11", "entry_fixed_12", "entry_fixed_13", "entry_fixed_14", "entry_fixed_15", "entry_fixed_16"]);
  rules.push({selector:'[data-ui-metric]',metric:true});
  rule('#to-review',['entry_fixed_1']);
  rule('#graph-history-body summary.xh-r > span:nth-child(3)',[],value=>{
    const split=value.indexOf(' · ');if(split<0)return null;
    const id={"读取": "activity_534cb3fa8fbf", "新建授权": "activity_a58bf29aab70", "撤销授权": "activity_fdbab2900fcf"}[value.slice(0,split)];return id?resources[id].en+value.slice(split):null;
  });
  rules.push({selector:'button[data-dcode] > .mx-name', metricList:true});
  rule('.gsum > span',[],v=>{const m=/^条(今天|\d{2}-\d{2}) 新到$/.exec(v);return m?' new '+(m[1]==='今天'?'today':'on '+m[1]):null;});
  rule('.grid3eq .mode,.grid3eq .l1 > .sub2,.ev > .ln,[data-eg-obs],[data-eg-go]',[],v=>({手动:'Manual',自动:'Automatic',数据:'Data',数据源:'Source',授权:'Permission',状态:'State',查看:'View'})[v]||null);
  rule('.grid3eq .l1 > .sub2',[],v=>{const m=/^(\d+) 项$/.exec(v);return m?m[1]+' '+noun(m[1],'item','items'):null;});
  rule('.grid3eq [data-summary-count]',[],v=>{const m=/^保存 (\d+) 条数据$/.exec(v);return m?'Saved '+m[1]+' '+noun(m[1],'record','records'):null;});
  rule('details.dy > summary',[],v=>{const m=/^(.+) (\d+) 条数据。$/.exec(v);return m?(m[1]==='合成'?resources.source_synthetic.en:m[1])+': '+m[2]+' '+noun(m[2],'record','records')+'.':null;});
  function sourceLabel(original) {
    if (original === resources.source_synthetic.zh || original.startsWith(resources.source_synthetic.zh + ' · ')) {
      return resources.source_synthetic.en + original.slice(2);
    }
    return original;
  }
  rule('[data-synthetic-date]',[],sourceLabel);
  rules.push({selector:'[data-overview-items]',overviewItems:true});
  rules.push({selector:'[data-overview-codes]',overviewCodes:true});
  const chartLabels = {"单次观测": "Single observation", "暂无历史观测": "No previous observations", "结果为范围表达，无法确定精确读数。": "The result is a range and has no exact value", "含缺失记录": "Some records are missing", "暂无有效数值": "No valid numbers", "记录类型未提供": "Record type unavailable", "暂不比较，保留原值": "Original value retained without comparison", "单位不同，暂不比较": "Different units; comparison unavailable", "单位未提供，暂不比较": "Unit unavailable; comparison unavailable", "检测方法未提供": "Test method unavailable", "检测方法不同": "Different test methods", "同日顺序未确认": "Order within the day is unconfirmed", "观测时间未提供": "Observation time unavailable", "非数值记录": "Non-numeric record", "计数单位未提供": "Count unit unavailable", "数量缺失或无效": "Count missing or invalid", "各组独立计数，不合计": "Groups counted separately", "保留各版本原始记录": "Original record versions retained", "保留原始记录": "Original record retained", "连线仅表示观测顺序，方法可比性未确认": "The line shows observation order; method comparability is unconfirmed", "按观测顺序，间距不代表天数": "In recorded order, spacing does not represent days"};
  function chartLabel(value) {
    return value.split('；').map((part,i) => {
      if (part.startsWith('最后一条 ')) return 'latest ' + part.slice(5);
      const word = chartLabels[part];
      if (!word) return part;
      return i ? word[0].toLowerCase()+word.slice(1) : word;
    }).join('; ');
  }
  rule('svg.mx-plot[aria-label]',[],chartLabel,'aria-label');
  rule('.mx-mini[title]',[],chartLabel,'title');
  for (const attribute of ['title','aria-label']) {
    rule('.sp-icon-only,#sq-fab,#sq,#sq-q',['a11y_starling','s67f4bfd60c66'],null,attribute);
    rule('#tl-pillbox,#tl-pillbox-card,#pb-settings',['a11y_pillbox'],null,attribute);
  }
  const entryAttributeIds = ["entry_accessible_0", "entry_accessible_1", "sc5500a58e0c5", "entry_accessible_3", "s80b19d68b149", "entry_accessible_5", "entry_accessible_6", "s8b6ff498515b", "entry_accessible_8", "entry_accessible_9", "entry_accessible_10", "entry_accessible_11"];
  for (const attribute of ['title','aria-label','placeholder']) {
    rule('#f-date,#f-time,[data-r][data-f],[data-del],.mt.m-dev',entryAttributeIds,null,attribute);
  }
  rules.push({selector:'[data-ui-aria-metric]',metricAria:true});
  rule('#appbar .crumb .up',[fixedSlots['我的数源']]);
  rule('#kg-svg .kg-el',[],v=>{
    const m=/^提供 (\d+) 条$/.exec(v);
    return m?'Provides '+m[1]+' '+noun(m[1],'record','records'):null;
  });
  rules.push({selector:'[data-event-template],[data-access-template] summary.xh-r > span',generated:true});
  rule('[data-csv-status]',[],v=>{
    let m=/^请确认下列 (\d+) 行的指标、数值、单位和日期。当前尚未入库；点击“确认保存到当前实例”才会保存。$/.exec(v);
    if(m)return 'Check the metrics, values, units and dates in these '+m[1]+' rows. Nothing has been saved. Select Confirm save to the current instance to save.';
    m=/^全部 (\d+) 行都能读懂，下一步核对。$/.exec(v);return m?'All '+m[1]+' rows can be read. Review them next.':null;
  });
  rule('[data-csv-row-count]',[],v=>{const m=/^(.*) · (\d+) 行$/.exec(v);return m?m[1]+' · '+m[2]+' '+noun(m[2],'row','rows'):null;});
  rule('.tgrid > span:nth-child(5n)',[],v=>v.trim()==='可以保存'?' Ready to save':null);
  rule('#go-track,#t-go',[],value=>({'去星炬看我的数据':'Go to My data in StarTorch','去星轨看我的状态':'Go to My state in StarTrack','回星轨看我的状态':'Return to My state in StarTrack','返回我的数据':'Return to My data'})[value]||null);
  rule('#appbar .crumb .up',[fixedSlots['来自文件报告']]);
  rule('#appbar .crumb .t',['s8d548e77958d']);
  rule('[data-data-root] .dcode .mx-name',['s8d548e77958d']);
  rule('[data-data-root] .mx-empty',['gene_empty_plot','gene_ambiguous_plot']);
  rule('#kg-svg .kg-el',[],v=>{const m=/^装入 (\d+) 个位点$/.exec(v);return m?'Indexed '+m[1]+' '+noun(m[1],'locus','loci'):null;});
  rules.push({selector:'[data-gene-day]',geneDay:true});
  rule('[data-gene-row-name]',['s8d548e77958d']);
  rule('[data-gene-row-source]',['gene_row_source','gene_row_real','gene_row_synthetic']);
  rule('[data-gene-row-synthetic]',['source_synthetic']);
  rule('#c-val',['audit_new_value'],null,'aria-label');
  rule('#c-cancel',['gene_cancel'],null,'aria-label');rule('#c-cancel',['gene_cancel'],null,'title');
  rule('#t-edit',['audit_edit']);rule('#t-retract',['s2f9daa828907']);rule('#r-ok',['gene_confirm_delete']);
  rule('#ptds-compute-status > span',['audit_pending','audit_failed']);rule('#ptds-compute-status button',['audit_retry']);
  rule('[data-sem="csv-import-result"]',[],v=>{
    const m=/^已导入 (\d+) 行：新增 (\d+)，更正 (\d+)，无变化 (\d+)。([\s\S]*)$/.exec(v);
    if(!m)return null;
    const suffix={'数据已保存，状态更新中':'Data saved. Updating state.','数据已保存，状态更新失败，可重试':'Data saved. The state update failed. You can try again.','已保存到我的数据':'Saved to My data','已保存到我的数据，并已交给星轨。目前没有状态卡用到这些指标。':'Saved to My data and sent to StarTrack. No current state card uses these metrics.'}[m[5]];
    return suffix?'Imported '+m[1]+' '+noun(m[1],'row','rows')+'. New: '+m[2]+'. Corrected: '+m[3]+'. Unchanged: '+m[4]+'. '+suffix:null;
  });
  rule('[data-data-root] [data-partner-row-count]',[],v=>{
    const m=/^(\d+) 条 · (.*)$/.exec(v);
    if(!m || !resources.audit_unit_one)return null;
    return m[1]+' '+resources[plural.select(Number(m[1]))==='one'?'audit_unit_one':'audit_unit_many'].en+' · '+m[2];
  });
  rule('#kg-svg .kg-el',[],v=>{const m=/^原件 (\d+) 条$/.exec(v);return m?m[1]+' '+noun(m[1],'original file','original files'):null;});
  const sourceName=v=>({'合成':'Synthetic','手动录入':'Manual entry','表格导入':'Table import','真实':'Real'}[v]||v);
  rule('[data-detail-source]',[],v=>{const m=/^([^·]+?)( · .*)?$/.exec(v);return m?sourceName(m[1])+(m[2]||''):null;});
  rule('[data-cmp="T08"] .confirm > .sub2',[],v=>{const m=/^保存后，星轨里 (.+) 会先标"来源已更新"，随后自动按新数据更新。$/.exec(v);return m?'After you save, StarTrack marks '+m[1]+' as updated and recalculates its state.':null;});
  rule('[data-mx-version] strong,[data-mx-version] > span,[data-mx-version] .mx-version',[],v=>{
    const m=/^第 (\d+) 版 · (当前记录版本|当前|旧版，保留|已删除（历史保留）)$/.exec(v);
    return m?'Version '+m[1]+' · '+({'当前记录版本':'Current','当前':'Current','旧版，保留':'Earlier version, retained','已删除（历史保留）':'Deleted, history retained'}[m[2]]):null;
  });
  rule('[data-mx-version] .sub2',[],v=>{
    const m=/^( · .+?) · ([^·]+) · (现有状态卡暂未包含该数据|当前状态卡暂未包含该数据|被 (.+) 用过)$/.exec(v);
    return m?m[1]+' · '+sourceName(m[2])+' · '+(m[4]?'Used by '+m[4]:'No current state card uses this record'):null;
  });
  rule('[data-receipt-status]',["receipt_states_updated", "receipt_removed_updated", "receipt_removed_unsynced"]);
  rules.push({selector:'[data-receipt-kind]',receipt:true});
  rules.push({selector:'[data-detail-code],[data-retract-code]',detailMetric:true});
  var selector=rules.map(function(r){return r.selector;}).join(',');
  function apply(scope,api){
    var base=scope && (scope.documentElement || scope);
    if(!base || !base.isConnected)return;
    var candidates=Array.prototype.slice.call(base.querySelectorAll(selector));
    if(base.matches(selector))candidates.unshift(base);
    candidates.forEach(function(el){rules.forEach(function(r){
      if(el.matches(r.selector)){
        if(r.receipt){
          const kind=el.getAttribute('data-receipt-kind');
          const code=el.getAttribute('data-receipt-code');
          const label=el.getAttribute('data-receipt-label');
          api.label(el,value=>{
            if(!label || !['revise','retract'].includes(kind))return null;
            const prefix=(kind==='revise'?'已更正 · ':'已删除 · ')+label+' ';
            if(!value.startsWith(prefix))return null;
            const name=metric('code:'+code,label)||label;
            if(kind==='revise')return 'Corrected · '+name+' '+value.slice(prefix.length);
            const suffix='（历史版本保留）';
            return value.endsWith(suffix)?'Deleted · '+name+' '+value.slice(prefix.length,-suffix.length)+' (history retained)':null;
          },[]);
          return;
        }
        if(r.detailMetric){
          const code=el.getAttribute('data-detail-code')||el.getAttribute('data-retract-code');
          api.label(el,v=>{
            const head=/^(.+) · ([0-9]{4}-[0-9]{2}-[0-9]{2}|时间未知)$/.exec(v);
            if(head)return (metric('code:'+code,head[1])||head[1])+' · '+(head[2]==='时间未知'?'Time unknown':head[2]);
            const m=/^确认删除这条“(.+)”（(.+?)，(.+)）？删除后不再显示在“我的数据”中，也不再参与后续计算；旧版本与历史计算记录保留。$/.exec(v);
            return m?'Delete the '+(metric('code:'+code,m[1])||m[1])+' record ('+m[2]+', '+m[3]+')? It will be removed from My data and excluded from future calculations. Earlier versions and calculation history are retained.':null;
          },[]);return;
        }
        if(r.geneDay){
          const labels=JSON.parse(el.getAttribute('data-gene-day'));
          const end=labels.join('、')+'。';
          api.label(el,value=>{
            if(!labels.length || !value.endsWith(end) || !labels.every(v=>v.startsWith('纳管基因数据 ')))return null;
            const beginning=value.slice(0,value.length-end.length);
            const count=/^合成 (\d+) 条数据；$/.exec(beginning);
            if(beginning && !count)return null;
            const intro=count?'Synthetic: '+count[1]+' '+noun(count[1],'record','records')+'. ':'';
            return intro+labels.map(v=>'Imported genetic file '+v.slice('纳管基因数据 '.length)).join(', ')+'.';
          },[]);
          return;
        }
        if(r.generated){
          const owner=el.getAttribute('data-event-template') || el.closest('[data-access-template]')?.getAttribute('data-access-template');
          api.label(el,v=>template(owner,v),[]);return;
        }
        if(r.overviewItems){
          api.label(el,original=>{
            const m=/^(.*) · (\d+) 项$/.exec(original);
            return m?(el.hasAttribute('data-synthetic-source')?sourceLabel(m[1]):m[1])+' · '+m[2]+' '+noun(m[2],'item','items'):null;
          },[]);return;
        }
        if(r.overviewCodes){
          const codes=JSON.parse(el.getAttribute('data-overview-codes'));
          api.attr(el,'title',[],original=>original.split('、').map((name,i)=>metric('code:'+codes[i],name)||name).join(', '));return;
        }
        if(r.metricAria){api.attr(el,'aria-label',['metric_'+el.getAttribute('data-ui-aria-metric')]);return;}
        if(r.metricList){api.label(el,null,['metric_'+el.parentNode.getAttribute('data-dcode')]);return;}
        if(r.metric){api.label(el,null,['metric_'+el.getAttribute('data-ui-metric')]);return;}
        if(r.graph){api.label(el,v=>graphText(el,v),[]);return;}
        if(r.marker){const id=el.getAttribute(r.marker);if(r.attribute)api.attr(el,r.attribute,[id]);else api.label(el,null,[id]);return;}
        if(r.inline){if(api.node) for(const n of el.childNodes){const prev=n.previousSibling,next=n.nextSibling;if(n.nodeType===3 && prev?.nodeType===8 && next?.nodeType===8 && next.nodeValue==='/ptds-ui' && prev.nodeValue.startsWith('ptds-ui:'))api.node(n,v=>{const pair=root.PTDS_LANGUAGE_RESOURCES.messages[prev.nodeValue.slice(8)];return pair && pair.zh===v ? pair.en : null;},[prev.nodeValue.slice(8)]);}return;}
        if(r.attribute)api.attr(el,r.attribute,r.ids,r.format);else api.label(el,r.format,r.ids);
      }
    });});
  }
  root.PTDS_LANGUAGE_PAGES=Object.freeze({apply:apply,formatTemplate:template});
})(window);
