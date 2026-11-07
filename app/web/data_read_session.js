/* Owns only the current data-page read group. One bounded rendered-page owner; no writes or new UI copy. */
(function(root){
  'use strict';
  function Session(){this.requests=new Set();this.saved=null;this.observed=new Set();this.generation=0;}
  Session.prototype.track=function(controller,timeout){
    var owner=this,entry={controller:controller,timeout:timeout};owner.requests.add(entry);
    return function(){owner.requests.delete(entry);};
  };
  Session.prototype.cancel=function(){
    this.generation++;this.observed.clear();
    this.requests.forEach(function(r){clearTimeout(r.timeout);r.controller.abort();});
    this.requests.clear();
  };
  Session.prototype.reader=function(path,validate,read){
    return function(view,params){var p=path(view,params),value=read(p);validate(value,p);return value;};
  };
  Session.prototype.prime=function(paths,read){
    var first;
    paths.forEach(function(p){
      try{read(p);}catch(err){
        if(!err.viewPending)throw err;
        if(!first)first=err;
      }
    });
    if(first)throw first;
  };
  Session.prototype.paths=function(path,state,filters,code,mode){
    var views=code?[['rows',50],['series',200]]:[[mode==='code'?'metrics':'rows',50]];
    return [path('summary')].concat(views.map(function(pair){
      var p=state.slots[pair[0]];
      return path(pair[0],Object.assign({},filters,{limit:pair[1],cursor:p&&p.cursor}));
    }));
  };
  Session.prototype.invalidate=function(){this.cancel();var old=this.saved;this.saved=null;if(old&&old.host.childNodes[0]===old.nodes[0]){old.host.replaceChildren();delete old.host.dataset.dataOwner;}};
  Session.prototype.present=function(ctx,paths,read,validate,paint){
    var owner=this,values,version,old=owner.saved;
    if(ctx.blocked){owner.saved=null;old=null;}
    var reusable=old&&old.key===ctx.key&&Date.now()-old.at<60000;
    if(old&&!reusable&&ctx.host.childNodes&&ctx.host.childNodes[0]===old.nodes[0]){ctx.host.replaceChildren();delete ctx.host.dataset.dataOwner;}
    function restore(){
      if(ctx.host.childNodes&&ctx.host.childNodes[0]!==old.nodes[0])ctx.host.replaceChildren.apply(ctx.host,old.nodes);
      Object.assign(ctx.host.dataset,old.dataset);
    }
    try{
      owner.prime(paths,read);
      values=paths.map(function(p){var value=read(p);validate(value,p);return value;});
      version=values[0].version;
      if(values.some(function(v){return v.version!==version;})){
        var mixed=Error('DATA_VIEW_CHANGED');mixed.code='DATA_VIEW_CHANGED';mixed.viewPending=true;mixed.path=paths[0];throw mixed;
      }
    }catch(err){
      if(!err.viewPending||!err.loading||!reusable||!ctx.current(ctx))throw err;
      restore();
      var pending=ctx.entry(err.path),promise=pending&&pending.promise,generation=owner.generation;
      if(promise&&!owner.observed.has(promise)){
        owner.observed.add(promise);
        promise.then(function(){
          owner.observed.delete(promise);
          if(generation===owner.generation&&ctx.current(ctx))ctx.retry();
        });
      }
      return;
    }
    if(reusable&&old.version===version){restore();return;}
    paint();
    owner.saved=null;
    // Match the existing read lifetime; keep only one bounded, fully painted page.
    if(ctx.host.childNodes&&ctx.host.childNodes.length&&new TextEncoder().encode(ctx.host.innerHTML).length<=1048576){
      owner.saved={host:ctx.host,key:ctx.key,version:version,at:Date.now(),nodes:Array.from(ctx.host.childNodes),dataset:Object.assign({},ctx.host.dataset)};
    }
  };
  root.PTDSDataReadSession=Session;
})(typeof window!=='undefined'?window:globalThis);
