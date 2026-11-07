"""QKeer admission via existing formal store. Caller holds application lock."""
import hashlib,json,re
from datetime import datetime,timezone
from decimal import Decimal
from h1_common import H1Error
from startorch_outbox import ObservationInput
import input_guard, device_targets
from garmin_ingest import immutable
# Existing PTDS QKeer dictionary units. Unmapped values remain in source evidence.
FIELDS={'heart_rate':('QKEER_HR','bpm'),'spo2':('QKEER_SPO2','%')}

def admit(inst,body):
 device_targets.require(inst, 'qkeer', body)
 input_guard.require_writable(inst)
 if set(body)!={'key','record_json','subject'} or body['subject']!='231':raise H1Error('QKEER_BODY_INVALID','')
 raw=body['record_json']
 if not isinstance(raw,str) or len(raw.encode())>1024*1024:raise H1Error('QKEER_SIZE_INVALID','')
 try:
  record=json.loads(raw,parse_float=Decimal,parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
  if not isinstance(record,dict):raise ValueError()
  for k in ('record_id','revision'):
   if not isinstance(record.get(k),str) or not 0<len(record[k])<512:raise ValueError()
  moment=datetime.fromisoformat(record['record_time'].replace('Z','+00:00'))
  if moment.utcoffset() is None or moment>datetime.now(timezone.utc):raise ValueError()
  fields=record['raw_data']
  if not isinstance(fields,dict):raise ValueError()
 except (ValueError,TypeError,KeyError,AttributeError):raise H1Error('QKEER_RECORD_INVALID','') from None
 identity=hashlib.sha256(('231|'+record['record_id']+'|'+record['revision']).encode()).hexdigest()
 request_id='QKEER-'+identity
 sha=hashlib.sha256(raw.encode()).hexdigest()
 root=inst.ctx.root/'startorch/qkeer'
 for p in (root,root/'raw',root/'receipts'):
  if p.is_symlink():raise H1Error('QKEER_UNSAFE_PATH','')
  p.mkdir(mode=0o700,exist_ok=True)
 receipt_path=root/'receipts'/(identity+'.json')
 if receipt_path.exists():
  receipt=json.loads(receipt_path.read_text())
  if receipt['raw_sha256']!=sha:raise H1Error('QKEER_REVISION_CONFLICT','')
  return receipt
 items=[]
 for field,(code,unit) in FIELDS.items():
  value=fields.get(field)
  if value is None:continue
  if isinstance(value,bool) or not isinstance(value,(int,Decimal)) or not Decimal(value).is_finite():raise H1Error('QKEER_NUMBER_INVALID','')
  value=format(Decimal(value),'f')
  if len(value)>32:raise H1Error('QKEER_NUMBER_INVALID','')
  items.append(ObservationInput('QKEER|231|'+record['record_id']+'|'+field,code,value,None,unit,{'role':'INSTANT','observed_at':moment.isoformat()},'DEVICE_QKEER','QKEER:'+sha+'#raw_data.'+field,'DEVICE_CONSUMER'))
 immutable(root/'raw'/(sha+'.json'),raw.encode())
 saved=inst.save_items(items,batch_id='QKEER-'+identity,request_id=request_id) if items else {'results':[]}
 counts={}
 for row in saved['results']:counts[row['outcome']]=counts.get(row['outcome'],0)+1
 receipt={'instance_id':inst.ctx.instance_id,'status':'SAVED' if items else 'ARCHIVED_ONLY','raw_sha256':sha,'projected':len(items),'formal_counts':counts,'request_id':request_id,'saved_at':inst.now()}
 immutable(receipt_path,json.dumps(receipt,ensure_ascii=False,sort_keys=True).encode())
 return receipt
