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
