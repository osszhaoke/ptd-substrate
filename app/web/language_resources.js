/* Presentation only. Preserve every numeric character verbatim; no grouping separators. US spelling, no Oxford comma, owner-confirmed trial translation. */
(function(root){
  'use strict';
  var pairs = [
  [
    "brand",
    "个人可信数据基座",
    "Personal Trusted Data Space"
  ],
  [
    "torch",
    "星炬",
    "StarTorch"
  ],
  [
    "track",
    "星轨",
    "StarTrack"
  ],
  [
    "cluster",
    "星簇",
    "StarCluster"
  ],
  [
    "trace",
    "星痕",
    "StarTrace"
  ],
  [
    "status",
    "我的状态",
    "My state"
  ],
  [
    "data",
    "我的数据",
    "My data"
  ],
  [
    "collaboration",
    "我的协作",
    "Sharing"
  ],
  [
    "evidence",
    "我的证据",
    "My evidence"
  ],
  [
    "laboratory",
    "状态实验室",
    "State lab"
  ],
  [
    "rules",
    "状态规则库",
    "State rules"
  ],
  [
    "sources",
    "我的数源",
    "My sources"
  ],
  [
    "grants",
    "我的授权",
    "My permissions"
  ],
  [
    "grant_rules",
    "授权规则",
    "Access rules"
  ],
  [
    "sharing",
    "授权协作",
    "Shared access"
  ],
  [
    "history",
    "操作记录",
    "Activity log"
  ],
  [
    "graph",
    "证据图谱",
    "Evidence graph"
  ],
  [
    "data_nav",
    "数据导航",
    "Data overview"
  ],
  [
    "nav",
    "导航",
    "Navigation"
  ],
  [
    "common",
    "通用",
    "General"
  ],
  [
    "modules",
    "模块",
    "Modules"
  ],
  [
    "settings",
    "设置",
    "Settings"
  ],
  [
    "about",
    "关于",
    "About"
  ],
  [
    "help",
    "帮助",
    "Help"
  ],
  [
    "back",
    "返回",
    "Back"
  ],
  [
    "notifications",
    "状态通知",
    "Notifications"
  ],
  [
    "dark",
    "换成深色",
    "Dark theme"
  ],
  [
    "light",
    "换成浅色",
    "Light theme"
  ],
  [
    "track_eyebrow",
    "星轨 · 理解状态",
    "StarTrack · Understand state"
  ],
  [
    "torch_eyebrow",
    "星炬 · 掌握数据",
    "StarTorch · Manage data"
  ],
  [
    "cluster_eyebrow",
    "星簇 · 可信协作",
    "StarCluster · Trusted sharing"
  ],
  [
    "trace_eyebrow",
    "星痕 · 证据图谱",
    "StarTrace · Evidence graph"
  ],
  [
    "cards",
    "状态卡片",
    "State cards"
  ],
  [
    "offset",
    "状态偏移",
    "State changes"
  ],
  [
    "push",
    "状态推送",
    "State updates"
  ],
  [
    "categories",
    "我的状态分类",
    "State categories"
  ],
  [
    "updated",
    "相关数据有更新",
    "Related data updated"
  ],
  [
    "cards_desc",
    "根据我的需求定制我主要关注和次要关注的状态卡片",
    "Choose the state cards you want to follow."
  ],
  [
    "offset_desc",
    "从设定一个基线起，再推到下一个状态，再计算偏移",
    "Set a baseline and compare it with a later state."
  ],
  [
    "push_desc",
    "定期推送我关注的状态，让我定期了解我自己。",
    "Get regular updates on the states you follow."
  ],
  [
    "status_desc",
    "我的各项状态一眼就能看全，新数据一到自动更新",
    "See all your states in one place. States update when new data arrives."
  ],
  [
    "sources_desc",
    "我的数据从哪里来：设备、报告、文件和手工录入",
    "The data comes from: devices, reports, files and manual entry."
  ],
  [
    "auth_desc",
    "我授权过的人、智能体和通道，可以随时收回",
    "Manage access for people, agents and channels. You can revoke it at any time."
  ],
  [
    "auth_rules_desc",
    "默认怎么授权：给谁、给多少、多久失效",
    "Set default access: who, how much and for how long."
  ],
  [
    "collaboration_desc",
    "和家人、医生或研究者一起使用数据，范围由我定",
    "Share data with family, doctors or researchers. You choose what to share."
  ],
  [
    "source_desc_actual",
    "在这里查看我接入的可穿戴设备、体检报告、手机健康等来源",
    "See sources such as connected wearables, health reports and phone health data."
  ],
  [
    "data_desc",
    "我的每一条数据都在这里，可以查看、更正或删除，历史版本保留",
    "View, correct or remove data here. Earlier versions are kept."
  ],
  [
    "guard_desc",
    "最近进来了哪些数据、从哪来，每一步处理都为我留了痕",
    "See recent data, its sources and a record of each processing step."
  ],
  [
    "eng_desc",
    "选一个模板、绑上我的数据，搭出一组我的状态卡",
    "Choose a template and connect your data to build state cards."
  ],
  [
    "alerts_desc",
    "状态有变化或有新结果时提醒我，发到哪里由我决定",
    "Get alerts when your state changes or new results arrive. You choose where they go."
  ],
  [
    "lab_desc",
    "用不同的规则、不同的假设把同一份数据再算一遍，对照着看",
    "Compare results for the same data using different rules or assumptions."
  ],
  [
    "rules_desc",
    "每个算法的出处、版本和原文链接，改规则只能发新版本",
    "See each method, its version and source. Rule changes are published as new versions."
  ],
  [
    "overview_desc",
    "我的数据现在给了谁、能看什么，一页看清",
    "See who can access your data and what they can view."
  ],
  [
    "records_desc",
    "每一次数据离开本机都有记录：谁、什么时候、拿了什么",
    "Each time data leaves this device, it's logged: who, what and when."
  ],
  [
    "view_mode",
    "怎么看",
    "View by"
  ],
  [
    "by_metric",
    "按指标",
    "By metric"
  ],
  [
    "by_time",
    "按时间",
    "By time"
  ],
  [
    "muse_sessions",
    "Muse 会话",
    "Muse sessions"
  ],
  [
    "reread",
    "重新读取",
    "Reload"
  ],
  [
    "all_sources",
    "显示所有来源",
    "Show all sources"
  ],
  [
    "all_dates",
    "显示全部日期",
    "Show all dates"
  ],
  [
    "newer",
    "较新",
    "Newer"
  ],
  [
    "older",
    "较早",
    "Older"
  ],
  [
    "all_metrics",
    "全部指标",
    "All metrics"
  ],
  [
    "from_date",
    "起始日期",
    "Start date"
  ],
  [
    "to_date",
    "结束日期",
    "End date"
  ],
  [
    "view_range",
    "查看范围",
    "Show range"
  ],
  [
    "all_history",
    "浏览全部历史",
    "Show full history"
  ],
  [
    "value",
    "值",
    "Value"
  ],
  [
    "timepoint",
    "时点",
    "Date & time"
  ],
  [
    "source",
    "来源",
    "Source"
  ],
  [
    "metric_name",
    "名称",
    "Name"
  ],
  [
    "latest",
    "最新",
    "Latest"
  ],
  [
    "trend_order",
    "趋势 · 按观测顺序",
    "Trend (in recorded order)"
  ],
  [
    "count_recent",
    "条数 · 最近",
    "Records · Last recorded"
  ],
  [
    "no_data",
    "还没有数据。",
    "No data yet."
  ],
  [
    "history_kept",
    "每条都可以更正或删除，历史版本保留。",
    "Each record can be corrected or removed. Earlier versions are kept."
  ],
  [
    "home_return",
    "返回首页",
    "Back to Home"
  ],
  [
    "loading_content",
    "内容加载中",
    "Loading content"
  ],
  [
    "loading_kicker",
    "星渐明，影随形",
    "As the stars brighten, shadows follow"
  ],
  [
    "read_timeout",
    "这次读取超时了",
    "Loading timed out"
  ],
  [
    "read_unavailable",
    "暂时无法读取",
    "Can't load right now"
  ],
  [
    "read_timeout_detail",
    "本次读取超时，已保存的数据仍然保留。可稍后重新读取。",
    "Loading took too long. Your saved data is safe. Try again later."
  ],
  [
    "read_error_detail",
    "内容暂未读取成功，已保存的数据仍然保留。",
    "Couldn't load this content. Your saved data is safe."
  ],
  [
    "updating_kept",
    "正在更新，下面保留上次读取的内容。",
    "Updating… Showing the last loaded version below."
  ],
  [
    "update_failed_kept",
    "更新未完成，下面保留上次读取的内容。",
    "Update didn't finish. Showing the last loaded version below."
  ],
  [
    "close",
    "关闭",
    "Close"
  ],
  [
    "close_loading",
    "关闭加载",
    "Close"
  ],
  [
    "read_retry",
    "重新读取",
    "Try again"
  ]
];
  var messages = Object.create(null), byChinese = Object.create(null);
  pairs.forEach(function(p){ messages[p[0]] = Object.freeze({zh:p[1],en:p[2]}); if (!byChinese[p[1]]) byChinese[p[1]]=p[0]; });
  // First-launch resources are looked up by id only, outside the global reverse index.
  [
    ["launch_open", "打开", "Open"],
    ["launch_motto", "从关注一个状态，到关注人的一生", "From a single state to a lifetime of health"],
    ["launch_disclaimer", "关注信号，不构成诊断或治疗建议", "These signals are for your information. They do not provide a diagnosis or treatment advice."],
    ["launch_group", "选择要打开的数据", "Select data to open"],
    ["launch_edit_title", "编辑首页大标题", "Edit home title"],
    ["first_language_title", "选择语言", "Choose your language"],
    ["first_language_en", "英语", "English"],
    ["first_language_zh", "简体中文", "Simplified Chinese"],
    ["first_language_system", "跟随系统语言", "Use system language"],
    ["language_menu_system", "跟随系统", "System"]
  ].forEach(function(p){ messages[p[0]] = Object.freeze({zh:p[1],en:p[2]}); });
  Object.entries(root.PTDS_PARTNER_CATALOG || {}).forEach(function(row){messages[row[0]]=Object.freeze({zh:row[1][0],en:row[1][1]});});
  // Match the exact source spelling for older, explicitly tagged device labels.
  function matchesSource(id, value) {
    const item = messages[id];
    if (!item) return false;
    const legacyBrand = root.PTDS_PARTNER_CATALOG?.[id]?.[2] === 'legacy-brand';
    return value === (legacyBrand ? item.zh.replace('Qkeer', 'QKeer') : item.zh);
  }
  root.PTDS_LANGUAGE_RESOURCES=Object.freeze({matchesSource:matchesSource,messages:Object.freeze(messages),byChinese:Object.freeze(byChinese)});
})(window);
