import json, os, sys, threading
from pathlib import Path
from urllib.parse import urlsplit
rt=Path(os.environ['ERASE_SYNTHETIC_ROOT']); appdir=Path(os.environ['ERASE_ALLOWED_COPY'])/'app'
sys.path[:0]=[str(appdir),str(appdir/'core')]
import subprocess
def guard(event,args):
 if event in ('socket.connect','socket.bind'):
  addr=args[1]
  if not isinstance(addr,tuple) or addr[0]!='127.0.0.1' or addr[1]==8780:raise PermissionError('loopback only')
 if event=='socket.getaddrinfo' and args[0] not in ('localhost','127.0.0.1',None):raise PermissionError('no external DNS')
 if event=='subprocess.Popen' and Path(args[0]).name in ('security','curl','osascript','open','launchctl','wget'):raise PermissionError('external channel disabled')
sys.addaudithook(guard)
import server
target=os.environ['FIX_TARGET'];reverse=os.environ['FIX_REVERSE']=='1';personal=False
keys=['A','B']
rows=[dict(key=k,id='fictional-'+k.lower(),name='打开',tz='Asia/Shanghai',kind='DEMO',accept=['SYNTHETIC'],default_nature='SYNTHETIC',cards=[],replay=False) for k in keys]
cfg=dict(instances=rows[::-1] if reverse else rows,starling={'enabled':False},band_bridge=False,macos_notify=False)
if not personal:cfg['device_targets']=dict.fromkeys(('garmin','qkeer','somaloop_agent'),target)
app=server.App(rt/'fiction',cfg);lock=threading.Lock()
if os.environ['FIX_DATA']=='1':
 inst=app.inst(target)
 server.GeneStore(inst).write('fictional.csv',b'RSID,CHROMOSOME,POSITION,RESULT\nrs990000001,1,81001,AT\n', 'SYNTHETIC')
 for i,(code,value,unit,day) in enumerate([('PLT','200','×10^9/L','01'),('CRP','2','mg/L','02'),('ESR','6','mm/h','02'),('PLT','201','×10^9/L','03')]):
  obs=server.ObservationInput('TABLE:fictional-typed-'+str(i)+'#row1',code,value,None,unit,{'role':'INSTANT','observed_at':'2026-10-'+day+'T12:00:00+08:00'},'SYNTHETIC','SYNTHETIC:r11','SYNTHETIC')
  saved=inst.save_items([obs],batch_id='r11-'+str(i),request_id='r11-'+str(i))
  assert saved['results'][0]['outcome']=='CREATED',code
class Handler(server.make_handler(app)):
 def send_response(self,code,message=None):
  with lock, (rt/'network.jsonl').open('a') as output:output.write(json.dumps([self.command,urlsplit(self.path).path,code])+'\n')
  return super().send_response(code,message)
http=server.ThreadingHTTPServer(('127.0.0.1',0),Handler);assert http.server_port!=8780;http.timeout=.1;(rt/'port').write_text(str(http.server_port))
try:
 while not (rt/'done').exists():http.handle_request()
finally:
 http.server_close();app.main_stores.close()
