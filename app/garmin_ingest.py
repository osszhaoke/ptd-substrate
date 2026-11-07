"""Garmin CN personal admission: immutable raw evidence + formal observations.

No login, token storage, remote requests or direct database writes in this module.
Caller holds app.lock. The receiving target is explicitly configured by the host.
"""
from __future__ import annotations
import hashlib
import json
import os
import re
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from zoneinfo import ZoneInfo
from h1_common import H1Error
from startorch_outbox import ObservationInput
import input_guard, device_targets

SINCE = '2026-10-18'
CATEGORIES = frozenset({'daily','heart_rate','sleep','hrv','oxygen','respiration','stress','body_battery','steps','floors','intensity','events','activities'})
# Paths are explicit and provenance-bound; no guessing unknown fields or units.
FIELDS = {
 'daily': [('totalSteps','STEPS','步数','steps'),('totalKilocalories','CAL_TOTAL','总消耗','kcal'),('activeKilocalories','CAL_ACTIVE','活动消耗','kcal'),('restingHeartRate','RESTING_HR','静息心率','bpm'),('minHeartRate','HR_MIN','日最低心率','bpm'),('maxHeartRate','HR_MAX','日最高心率','bpm'),('averageStressLevel','STRESS_AVG','日平均压力','score'),('bodyBatteryHighestValue','BATTERY_MAX','身体电量最高值','score'),('bodyBatteryLowestValue','BATTERY_MIN','身体电量最低值','score')],
 'hrv': [('hrvSummary.lastNightAvg','HRV_NIGHT','夜间平均 HRV','ms')],
 'sleep': [('dailySleepDTO.sleepTimeSeconds','SLEEP_SECONDS','睡眠时长','s'),('dailySleepDTO.deepSleepSeconds','SLEEP_DEEP','深睡时长','s'),('dailySleepDTO.lightSleepSeconds','SLEEP_LIGHT','浅睡时长','s'),('dailySleepDTO.remSleepSeconds','SLEEP_REM','REM 睡眠时长','s'),('dailySleepDTO.awakeSleepSeconds','SLEEP_AWAKE','清醒时长','s')],
 'oxygen': [('averageSpO2','SPO2_AVG','日平均血氧','%'),('lowestSpO2','SPO2_MIN','日最低血氧','%')],
 'respiration': [('avgWakingRespirationValue','RESP_AWAKE','清醒平均呼吸率','brpm'),('avgSleepRespirationValue','RESP_SLEEP','睡眠平均呼吸率','brpm')],
}
EXTRA_CODES = [('HR','心率','bpm')]


def number(value):
    if isinstance(value, bool) or value is None or not isinstance(value,(int,Decimal)):
        return None
    d = Decimal(value)
    if not d.is_finite() or d < 0:  # Garmin uses negative values as missing sentinels for these fields.
        return None
    text = format(d,'f')
    return text if len(text) <= 32 else None


def decode(raw):
    if not isinstance(raw,str) or len(raw.encode()) > 12*1024*1024:
        raise H1Error('GARMIN_RAW_SIZE','')
    if raw == '': return None
    try:
        return json.loads(raw,parse_float=Decimal,parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    except (ValueError,TypeError,RecursionError):
        raise H1Error('GARMIN_JSON_INVALID','') from None


def project(category, day, raw, sha, tz):
    data=decode(raw);out=[];ignored=[]
    temporal={'role':'DAY','observed_date':day,'tz':tz}
    def add(suffix,value,unit,t,location,identity):
        text=number(value)
        if text is None:
            if value is not None: ignored.append(location)
            return
        code='GARMIN_'+suffix
        out.append(ObservationInput('GARMIN|'+code+'|'+identity,code,text,None,unit,t,
                   'DEVICE_GARMIN','GARMIN:'+sha+'#'+location,'DEVICE_CONSUMER'))
    if isinstance(data,dict):
        for path,code,label,unit in FIELDS.get(category,[]):
            value=data
            for key in path.split('.'):
                value=value.get(key) if isinstance(value,dict) else None
            add(code,value,unit,temporal,path,day)
        if category=='heart_rate':
            # Garmin dailyHeartRate uses UTC epoch milliseconds; never use Local timestamps.
            rows=data.get('heartRateValues',[])
            if isinstance(rows,list):
                for index,row in enumerate(rows):
                    if not isinstance(row,list) or len(row)!=2 or isinstance(row[0],bool) or not isinstance(row[0],int):
                        ignored.append('heartRateValues/'+str(index));continue
                    try: moment=datetime.fromtimestamp(row[0]/1000,timezone.utc)
                    except (OverflowError,ValueError,OSError):
                        ignored.append('heartRateValues/'+str(index));continue
                    if moment > datetime.now(timezone.utc) or moment.astimezone(ZoneInfo(tz)).date().isoformat()!=day:
                        ignored.append('heartRateValues/'+str(index));continue
                    instant=moment.isoformat(timespec='milliseconds')
                    # Preserve duplicate timestamps as separate occurrences, not a silent overwrite.
                    add('HR',row[1],'bpm',{'role':'INSTANT','observed_at':instant},
                        'heartRateValues/'+str(index),instant+'|'+str(index))
    return out,ignored


def immutable(path, content):
    if path.is_symlink(): raise H1Error('GARMIN_UNSAFE_PATH','')
    if path.exists():
        if path.read_bytes()!=content: raise H1Error('GARMIN_ARCHIVE_CONFLICT','')
        return
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'wb') as f:
        f.write(content);f.flush();os.fsync(f.fileno())


def admit(inst, body):
    device_targets.require(inst, 'garmin', body)
    input_guard.require_writable(inst)
    if set(body) != {'key','day','category','raw_json_text','request_id'}:
        raise H1Error('GARMIN_BODY_INVALID','')
    day=body['day'];kind=body['category'];raw=body['raw_json_text'];request_id=body['request_id']
    if not isinstance(day,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}',day): raise H1Error('GARMIN_DATE_INVALID','')
    try: date.fromisoformat(day)
    except ValueError: raise H1Error('GARMIN_DATE_INVALID','') from None
    if not SINCE<=day<=datetime.now(ZoneInfo(inst.ctx.tz)).date().isoformat():
        raise H1Error('GARMIN_DATE_OUT_OF_SCOPE','')
    if kind not in CATEGORIES: raise H1Error('GARMIN_CATEGORY_INVALID','')
    if not isinstance(request_id,str) or not re.fullmatch(r'GARMIN-[a-f0-9]{32}',request_id):
        raise H1Error('GARMIN_REQUEST_INVALID','')
    decode(raw)
    sha=hashlib.sha256(raw.encode()).hexdigest()
    items,ignored=project(kind,day,raw,sha,inst.ctx.tz)
    root=inst.ctx.root/'startorch'/'garmin'
    for path in (root,root/'raw',root/'receipts'):
        if path.is_symlink(): raise H1Error('GARMIN_UNSAFE_PATH','')
        path.mkdir(mode=0o700,exist_ok=True)
    digest=hashlib.sha256(json.dumps(body,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    receipt_path=root/'receipts'/(request_id+'.json')
    if receipt_path.is_symlink(): raise H1Error('GARMIN_UNSAFE_PATH','')
    if receipt_path.exists():
        receipt=json.loads(receipt_path.read_text())
        if receipt['request_digest']!=digest: raise H1Error('GARMIN_REQUEST_CONFLICT','')
        return receipt
    immutable(root/'raw'/(sha+'.json'),raw.encode())
    result=inst.save_items(items,batch_id='GARMIN-'+day,request_id=request_id) if items else {'results':[]}
    counts={}
    for row in result['results']: counts[row['outcome']]=counts.get(row['outcome'],0)+1
    receipt={'schema':'ptds-garmin-admission/1','instance_id':inst.ctx.instance_id,'request_id':request_id,
             'request_digest':digest,'day':day,'category':kind,'raw_sha256':sha,
             'raw_archived':True,'formal_counts':counts,'projected':len(items),
             'skipped_field_count':len(ignored),'all_fields_projected':False,
             'status':'SAVED' if items else ('EMPTY' if not decode(raw) else 'ARCHIVED_ONLY'),
             'saved_at':inst.now()}
    immutable(receipt_path,json.dumps(receipt,ensure_ascii=False,indent=2).encode())
    return receipt
