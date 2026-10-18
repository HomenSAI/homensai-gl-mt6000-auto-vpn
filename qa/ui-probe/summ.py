import json,sys
sys.stdout.reconfigure(encoding='utf-8')
r=[]
for f in sys.argv[1:]:r+=json.load(open(f,encoding='utf-8'))
for x in r:
    c='/'.join(map(str,x['cfg']))
    if x.get('error') or x.get('fatal'):print('ERR',c,x.get('error'),(x.get('fatal') or '')[:40]);continue
    flags=[]
    if x['docOverflow']>0:flags.append('docOverflow=%d'%x['docOverflow'])
    if x['offenderCount']:flags.append('offenders=%d %s'%(x['offenderCount'],x['offenders'][:2]))
    if not(x['attribution'] and x['footer'] and x['badge']):flags.append('ATTR a=%s f=%s b=%s'%(x['attribution'],x['footer'],x['badge']))
    if x['designError']:flags.append('DESIGN-ERROR')
    if x['errors']:flags.append('js:%s'%x['errors'][:2])
    low=[l for l in x['lowContrast'] if 'cbi-button-action' not in l['c']]
    if low:flags.append('lowContrast=%s'%[(l['t'],l['r'],l['c']) for l in low[:5]])
    if flags:print(c,'|',' ; '.join(flags))
print('total',len(r))
