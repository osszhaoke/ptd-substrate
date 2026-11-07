/* Home presentation only. This never removes instances or changes access. */
(function(root){
  'use strict';
  var retired='ACC 四海睡眠房演示场景';
  function clean(s){return String(s||'').replace(/\s+/g,' ').trim();}
  function first(card,selector){return card.querySelectorAll(selector)[0];}
  function filter(cards,selectedKey){
    if(!cards)return;
    Array.prototype.slice.call(cards.children).forEach(function(card){
      if(!String(card.className).split(/\s+/).includes('icard'))return;
      var open=first(card,'[data-launch]');
      if(!open||open.getAttribute('data-launch')===selectedKey)return;
      var name=first(card,'.nm'),tag=first(card,'.inst');
      var title=clean(name&&name.textContent),label=clean(tag&&tag.textContent);
      if(title===retired||clean(label+' '+title)===retired)card.remove();
    });
  }
  root.PTDS_HOME_LAYOUT=Object.freeze({filter:filter});
})(window);
