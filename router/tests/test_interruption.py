"""interruption.py: one code per service start (owner request 01.11.2026). The cases are shared with
tests/lua/test_interruption.lua (interruption_cases.json): Python and Lua decide the same."""
import json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[0]/'files/usr/lib/homensai-vpn'))
import interruption as I

CASES=json.loads((HERE/'interruption_cases.json').read_text(encoding='utf-8'))


def state_of(text):
    try:row=json.loads(text or '')
    except ValueError:return None
    return row.get('state') if isinstance(row,dict) else None


class World:
    def __init__(self,case):
        self.files=dict(case.get('files',{}));self.mtimes=dict(case.get('mtimes',{}));self.logs=[];self.records=[]
        self.persist_writes=0;self.stopping=False;uptime=case.get('uptime')
        def write_persist(path,text):
            self.persist_writes+=1;self.files[path]=text
        self.ctx={'runtime':'/run','persist':'/etc','read':self.files.get,'mtime':self.mtimes.get,
                  'write_ram':self.files.__setitem__,'write_persist':write_persist,'now':lambda:1000,'uptime':lambda:uptime,
                  'log':self.logs.append,'record':self.records.append,'stopping':lambda:self.stopping}


class SharedCases(unittest.TestCase):
    def test_start_cases(self):
        for case in CASES['start']:
            with self.subTest(case['name']):
                w=World(case);handle=I.start(w.ctx,case['phase'])
                self.assertEqual(handle['code'],case['expect'])
                self.assertEqual(state_of(w.files.get('/etc/service-run.json')),case['written'])
                self.assertEqual(handle['facts']['auto_on'],case['auto']=='on')
                self.assertEqual(w.records,[case['expect']] if case['recorded'] else [])
                self.assertEqual(len(w.logs),1);self.assertTrue(w.logs[0].startswith(case['expect']+': '),w.logs[0])
                self.assertIn('/run/supervisor-run.json',w.files)

    def test_monitor_cases(self):
        for case in CASES['monitor']:
            with self.subTest(case['name']):
                w=World(case)
                self.assertEqual(I.monitor_start(w.ctx),case['expect'])
                self.assertEqual(len(w.logs),1 if case['logged'] else 0)
                self.assertEqual(w.persist_writes,0);self.assertIn('/run/monitor-run.json',w.files)

    def test_steady_state_written_once_never_over_a_stop(self):
        w=World({'uptime':60});handle=I.start(w.ctx,None)
        self.assertEqual(w.persist_writes,1)
        self.assertTrue(I.mark_running(w.ctx,handle));self.assertEqual(state_of(w.files['/etc/service-run.json']),'running')
        self.assertFalse(I.mark_running(w.ctx,handle));self.assertEqual(w.persist_writes,2)
        again=I.start(w.ctx,None)
        self.assertEqual(again['code'],'RESTART-PROCESS');self.assertFalse(I.mark_running(w.ctx,again));self.assertEqual(w.persist_writes,2)
        s=World({'files':{'/etc/service-run.json':'{"state":"stopped","time":1}'},'uptime':60})
        h=I.start(s.ctx,None);s.stopping=True;s.files['/etc/service-run.json']='{"state":"stopped","time":2}'
        self.assertFalse(I.mark_running(s.ctx,h));self.assertEqual(state_of(s.files['/etc/service-run.json']),'stopped')

    def test_init_script_marker_and_texts(self):
        self.assertEqual(I.previous('{"state":"stopped","time":1730000000}'),'stopped')
        self.assertIsNone(I.previous(None));self.assertEqual(I.previous('{"state":"other"}'),'invalid')
        for case in CASES['start']:self.assertIn(case['expect'],I.TEXT)

    def test_failures_never_stop_the_start(self):
        w=World({'uptime':None})
        def fail(*_):raise OSError('flash full')
        w.ctx['write_persist']=fail;w.ctx['log']=fail
        handle=I.start(w.ctx,'APPLYING')
        self.assertEqual(handle['code'],'RESTART-FIRST-START');self.assertIsNone(handle['persisted'])

    def test_lua_and_python_log_texts_match(self):
        lua=(HERE.parents[0]/'files/usr/lib/homensai-vpn/lua/interruption.lua').read_text(encoding='utf-8')
        for code,text in I.TEXT.items():self.assertIn("['%s']='%s'"%(code,text),lua)


class RouterContext(unittest.TestCase):
    """The real files: the init script's marker, the RAM markers, the stop flag mtime, the history event."""
    def test_real_files(self):
        with tempfile.TemporaryDirectory() as temp:
            runtime=Path(temp)/'run';persist=Path(temp)/'etc';runtime.mkdir();persist.mkdir()
            (persist/'service-run.json').write_text('{"state":"stopped","time":1730000000}')
            logs=[];records=[]
            import agent
            with patch.object(agent,'RUNTIME',runtime),patch.object(agent,'PERSIST',persist):
                ctx=I.context(runtime,persist,record=records.append,stopping=lambda:False,log=logs.append)
                handle=I.start(ctx,None)
                self.assertEqual(handle['code'],'RESTART-CLEAN');self.assertEqual(records,['RESTART-CLEAN'])
                self.assertEqual(json.loads((persist/'service-run.json').read_text())['state'],'starting')
                self.assertTrue(I.mark_running(ctx,handle))
                self.assertEqual(json.loads((persist/'service-run.json').read_text())['state'],'running')
                self.assertEqual(I.start(ctx,None)['code'],'RESTART-PROCESS')
                (runtime/'service-stop.flag').write_text('');import os;os.utime(runtime/'service-stop.flag',(1e9+7,1e9+7))
                self.assertEqual(I.start(ctx,None)['code'],'RESTART-CLEAN')
                self.assertIsNone(I.monitor_start(ctx));self.assertEqual(I.monitor_start(ctx),'RESTART-PROCESS')

    def test_history_event_is_readable(self):
        from native_history import History
        with tempfile.TemporaryDirectory() as temp:
            History(Path(temp),limit=100).record({'state':'RESTART-INTERRUPTED-SWITCH','reason':'RESTART-INTERRUPTED-SWITCH'})
            events=History(Path(temp),limit=100).load()['events']
            self.assertEqual(events[-1]['state'],'RESTART-INTERRUPTED-SWITCH');self.assertEqual(events[-1]['codes'],['RESTART-INTERRUPTED-SWITCH'])


if __name__=='__main__':unittest.main()
