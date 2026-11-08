"""macOS release CI: real browser, two languages, empty and populated fictional spaces."""
from pathlib import Path
import json, os, shutil, subprocess, sys, tempfile, time, unittest

HERE=Path(__file__).resolve().parent
APP=HERE.parent if (HERE.parent/'server.py').is_file() else HERE.parent/'app'
TOOLS=HERE/'partner_visible'

def exception_reason(page,hit):
    if hit['value']=='打开' and hit['field']=='text' and (hit['parent']=='inst' or page in ('home','oura','whoop','garmin','garmin-setup')):
        return 'Fictional user-selected instance display name'
    if hit['id']=='gene-instance-name' and hit['field']=='text' and hit['value']=='打开':
        return 'Exact fictional instance name in the gene destination label'
    if hit['id']=='inst' and hit['field']=='aria-label' and hit['value']=='打开, synthetic demo data. Back to home':
        return 'Instance name in accessible action'
    return None

class VisibleLanguage(unittest.TestCase):
    def test_partner_visible_language(self):
        out=os.environ.get('VISIBLE_EVIDENCE_DIR')
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp);report=Path(out) if out else base/'report';report.mkdir(exist_ok=True,parents=True)
            binary=base/'browser'
            env=dict(HOME=str(base),TMPDIR=str(base),PATH='/opt/homebrew/bin:/usr/bin:/bin')
            compiled=subprocess.run(['/usr/bin/swiftc','-module-cache-path',str(base/'swift-cache'),str(TOOLS/'browser.swift'),'-o',str(binary)],env=env,capture_output=True,text=True,timeout=180)
            self.assertEqual(compiled.returncode,0,compiled.stderr)
            for rev,(language,data) in enumerate([('en',False),('en',True),('zh',False),('zh',True)]):
                with self.subTest(language=language,populated=data):
                    rt=base/f'case-{rev}';rt.mkdir()
                    ev=report/f'{language}-{int(data)}';ev.mkdir()
                    target='A' if rev in (0,3) else 'B'
                    e=dict(env,HOME=str(rt),TMPDIR=str(rt),PYTHONDONTWRITEBYTECODE='1',PTDS_SECRETS=str(rt/'empty-secrets'),PTDS_CONFIG=str(rt/'fictional-settings.json'),ERASE_SYNTHETIC_ROOT=str(rt),ERASE_ALLOWED_COPY=str(APP.parent),FIX_TARGET=target,FIX_REVERSE=str(int(rev%2)),FIX_DATA=str(int(data)))
                    with (ev/'server.log').open('wb') as log:
                        server=subprocess.Popen([sys.executable,'-B',str(TOOLS/'fixture.py')],cwd=APP.parent,env=e,stdout=log,stderr=log)
                    try:
                        for _ in range(180):
                            if (rt/'port').exists():break
                            self.assertIsNone(server.poll(),(ev/'server.log').read_text());time.sleep(.1)
                        port=(rt/'port').read_text();self.assertNotEqual(port,'8780')
                        csv=rt/'data/sample-import.csv';csv.parent.mkdir();csv.write_text('code,value,unit,comparator,observed_at,observed_date,tz\n'+'TEMP,36.50,°C,,2026-11-01T08:00:00+08:00,,\n'*2)
                        code=base/f'walk-{rev}.js'
                        code.write_text('window.walkLang='+json.dumps(language)+';window.walkHasData='+json.dumps(bool(data))+';window.keepShots='+json.dumps(bool(out and data))+';\n'+(TOOLS/'scan-screen.js').read_text()+'\n'+(TOOLS/'walk.js').read_text())
                        cp=subprocess.run([str(binary),str(code),port,'walk',str(ev),str(csv)],env=e,capture_output=True,text=True,timeout=135)
                        (ev/'browser.log').write_text(cp.stderr+'\n'+cp.stdout)
                        v=json.loads(cp.stdout);self.assertFalse(v.get('error'),v.get('error'))
                        self.assertEqual(len(v['rows']),33 if data else 30);unknown=[]
                        for row in v['rows']:
                            self.assertNotIn('error',row,row)
                            self.assertEqual(row['starlingFocusable'],0,'STARLING_ENTRY_VISIBLE')
                            if language=='en':
                                for hit in row['cn']:
                                    hit['reason']=exception_reason(row['name'],hit)
                                    if not hit['reason']:unknown.append([row['name'],hit])
                        (ev/'result.json').write_text(json.dumps(v,ensure_ascii=False,indent=1))
                        self.assertFalse(unknown,'VISIBLE_UNTRANSLATED '+str(unknown[:9]))
                    finally:
                        (rt/'done').touch();server.wait(timeout=10)
                        if (rt/'network.jsonl').is_file():shutil.copyfile(rt/'network.jsonl',ev/'network.jsonl')
                    responses=[json.loads(s) for s in (ev/'network.jsonl').read_text().splitlines()]
                    self.assertTrue(responses);self.assertFalse([r for r in responses if r[2]>=400],'PARTNER_HTTP_ERROR')
if __name__=='__main__':unittest.main(verbosity=2)
