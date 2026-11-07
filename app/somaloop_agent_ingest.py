"""Phone cache admission only; no BLE commands or manufacturer network calls."""
import hashlib,json,re,os,threading,contextlib
from datetime import date,datetime,timezone
from decimal import Decimal
from zoneinfo import ZoneInfo
from h1_common import H1Error
from startorch_outbox import ObservationInput
from garmin_ingest import immutable
import input_guard, device_targets
ADMISSION_LOCK=threading.Lock()
DAILY={
 'calories':('CAL_DAY','估算热量（日）','千卡','kcal'),
 'distance':('DISTANCE_DAY','估算距离（日）','公里','km'),
 'hrv':('HRV_DAY','HRV（日，算法未提供）','ms','ms'),
 'load':('LOAD_DAY','身体负荷（日）','','1'),
 'oxygen':('SPO2_DAY','血氧（日汇总）','%','%'),
 'steps':('STEPS_DAY','步数（日）','步','steps'),
 'temperature':('TEMP_DEV_DAY','皮温偏差（日）','°C','°C')}
SAMPLES={'heart_rate':('SOMALOOP_HR','bpm'),'hrv':('SOMALOOP_AGENT_HRV_SAMPLE','ms'),'steps':('SOMALOOP_AGENT_STEPS_SAMPLE','steps')}
def digest(b):return hashlib.sha256(b).hexdigest()
def canon(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'),default=str).encode()
def number(v):
 if isinstance(v,bool) or not isinstance(v,(int,Decimal)):return None
 d=Decimal(v)
 if not d.is_finite():return None
 s=format(d,'f')
 return s if len(s)<=32 else None

def project(kind,day,data,sha,tz):
 out=[];skipped=0
 def add(identity,code,value,unit,temporal,location):
  nonlocal skipped
  text=number(value)
  if text is None:
   if value is not None:skipped+=1
   return
  key='SOMALOOP_AGENT|'+identity
  fp=digest(canon([code,text,unit,temporal]))
  out.append((key,fp,ObservationInput(key,code,text,None,unit,temporal,'DEVICE_SOMALOOP','SOMALOOP_AGENT:'+sha+'#'+location,'DEVICE_CONSUMER')))
 if kind=='daily':
  for i,row in enumerate(data.get('days',[])):
   if row.get('day')!=day:continue
   for field,(suffix,label,source_unit,unit) in DAILY.items():
    metric=row.get('metrics',{}).get(field)
    if not isinstance(metric,dict):continue
    if metric.get('unit')!=source_unit:skipped+=1;continue
    add('daily|'+day+'|'+field,'SOMALOOP_AGENT_'+suffix,metric.get('value'),unit,{'role':'DAY','observed_date':day,'tz':tz},f'days/{i}/metrics/{field}')
 elif kind in SAMPLES:
  if data.get('day')!=day:raise H1Error('SOMALOOP_DAY_MISMATCH','')
  occurrences={}
  for si,series in enumerate(data.get('series',[])):
   if series.get('metric')!=kind:raise H1Error('SOMALOOP_METRIC_MISMATCH','')
   device=series.get('device')
   if not isinstance(device,str) or not device:raise H1Error('SOMALOOP_DEVICE_MISSING','')
   for pi,p in enumerate(series.get('points',[])):
    rawtime=p.get('device_time')
    try:
     if not isinstance(rawtime,str) or not re.fullmatch(r'\d{12}',rawtime):raise ValueError()
     moment=datetime.strptime('20'+rawtime,'%Y%m%d%H%M%S').replace(tzinfo=ZoneInfo(tz))
     if moment.date().isoformat()!=day or moment>datetime.now(timezone.utc):raise ValueError()
    except ValueError:skipped+=1;continue
    identity=digest(device.encode())+'|'+kind+'|'+rawtime
    n=occurrences.get(identity,0);occurrences[identity]=n+1
    code,unit=SAMPLES[kind]
    add(identity+'|'+str(n),code,p.get('value'),unit,{'role':'INSTANT','observed_at':moment.isoformat()},f'series/{si}/points/{pi}')
 return out,skipped

def admit(inst,body,lock=None):
 with ADMISSION_LOCK:
  return _admit(inst,body,lock)

def _admit(inst,body,lock):
 device_targets.require(inst, 'somaloop_agent', body)
 input_guard.require_writable(inst)
 if set(body)!={'key','day','kind','raw_json_text','device_timezone'}:raise H1Error('SOMALOOP_BODY_INVALID','')
 day=body['day'];kind=body['kind'];raw=body['raw_json_text'];tz=body['device_timezone']
 if tz!='Asia/Shanghai':raise H1Error('SOMALOOP_TIMEZONE_UNCONFIRMED','')
 if kind not in ('daily','heart_rate','hrv','steps','oxygen','temperature','spo2','skin_temperature','sleep','measurements'):raise H1Error('SOMALOOP_KIND_INVALID','')
 try:
  if date.fromisoformat(day)>datetime.now(ZoneInfo(tz)).date():raise ValueError()
  if not isinstance(raw,str) or len(raw.encode())>8*1024*1024:raise ValueError()
  data=json.loads(raw,parse_float=Decimal,parse_constant=lambda _:(_ for _ in ()).throw(ValueError()))
  if not isinstance(data,dict):raise ValueError()
 except (TypeError,ValueError):raise H1Error('SOMALOOP_RAW_INVALID','') from None
 sha=digest(raw.encode());identity=digest(canon([day,kind,sha,tz]));root=inst.ctx.root/'startorch/somaloop-agent'
 for path in (root,root/'raw',root/'receipts',root/'indices'):
  if path.is_symlink():raise H1Error('SOMALOOP_UNSAFE_PATH','')
  path.mkdir(mode=0o700,exist_ok=True)
 receipt_path=root/'receipts'/(identity+'.json')
 if receipt_path.exists():return json.loads(receipt_path.read_text())
 rows,skipped=project(kind,day,data,sha,tz)
 index_path=root/'indices'/(day+'-'+kind+'.json')
 if index_path.is_symlink() or receipt_path.is_symlink():raise H1Error('SOMALOOP_UNSAFE_PATH','')
 previous=json.loads(index_path.read_text()) if index_path.exists() else {}
 items=[x for key,fp,x in rows if previous.get(key)!=fp]
 immutable(root/'raw'/(sha+'.json'),raw.encode())
 counts={}
 # Bounded formal transactions; retries retain identical IDs and contents.
 for offset in range(0,len(items),500):
  with lock if lock is not None else contextlib.nullcontext():
   result=inst.save_items(items[offset:offset+500],batch_id='SOMALOOP-AGENT-'+day,request_id='SA-'+identity+'-'+str(offset))
  for r in result['results']:counts[r['outcome']]=counts.get(r['outcome'],0)+1
 for key,fp,_ in rows:previous[key]=fp
 tmp=index_path.with_suffix('.tmp');tmp.write_text(json.dumps(previous));os.chmod(tmp,0o600);tmp.replace(index_path)
 receipt={'instance_id':inst.ctx.instance_id,'kind':kind,'day':day,'raw_sha256':sha,'projected':len(rows),'changed':len(items),'skipped':skipped,'formal_counts':counts,'status':'SAVED' if rows else 'ARCHIVED_ONLY','saved_at':inst.now()}
 immutable(receipt_path,canon(receipt));return receipt
