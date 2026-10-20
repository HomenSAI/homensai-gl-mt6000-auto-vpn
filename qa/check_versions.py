"""Read-only agreement check for application, package, selected UI and handoff versions."""
import argparse,ast,hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def literal(path,name):
    for node in ast.parse(path.read_text(encoding='utf-8')).body:
        if isinstance(node,ast.Assign) and any(isinstance(target,ast.Name) and target.id==name for target in node.targets):return ast.literal_eval(node.value)
    raise ValueError('VERSION-LITERAL-MISSING')

def validate(path):
    if path.stat().st_size>16384:raise ValueError('VERSION-MANIFEST-SIZE')
    data=json.loads(path.read_text(encoding='utf-8-sig'));app=data['application'];review=data['handoff']
    if data.get('schema')!=1 or not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+(?:-(?:alpha|beta)[0-9]+)?',app['version']):raise ValueError('VERSION-APPLICATION')
    if type(app['package_revision']) is not int or app['package_revision']<1:raise ValueError('VERSION-PACKAGE-REVISION')
    package=app['version']+'-'+str(app['package_revision'])
    if app['package_version']!=package or app['release_tag']!='v'+app['version']:raise ValueError('VERSION-PACKAGE')
    make=(ROOT/'router/Makefile').read_text(encoding='utf-8')
    if re.search(r'^PKG_VERSION:=(.+)$',make,re.M).group(1)!=app['version'] or re.search(r'^PKG_RELEASE:=(.+)$',make,re.M).group(1)!=str(app['package_revision']):raise ValueError('VERSION-MAKEFILE')
    if literal(ROOT/'router/build_ipk.py','VERSION')!=package or literal(ROOT/'router/files/usr/lib/homensai-vpn/agent.py','VERSION')!=app['version']:raise ValueError('VERSION-RUNTIME')
    if not re.fullmatch(r'dashboard[0-9]+',app['ui_module']) or not re.fullmatch(r'ui[0-9]+\.css',app['ui_stylesheet']):raise ValueError('VERSION-UI-PATH')
    menu=json.loads((ROOT/'router/files/usr/share/luci/menu.d/luci-app-homensai-vpn.json').read_text())
    if menu['admin/services/homensai-vpn']['action']['path']!='homensai-vpn/'+app['ui_module']:raise ValueError('VERSION-UI-MENU')
    ui=ROOT/'router/files/www/luci-static/resources/view/homensai-vpn';script=(ui/(app['ui_module']+'.js')).read_text(encoding='utf-8')
    if set(re.findall(r'\bui[0-9]+\.css\b',script))!={app['ui_stylesheet']} or not (ui/app['ui_stylesheet']).is_file():raise ValueError('VERSION-UI-CSS')
    if not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+',review['version']) or review['release_tag']!='handoff-v'+review['version']:raise ValueError('VERSION-HANDOFF')
    if review['kind']!='documentation-review-checkpoint' or review['application_changed'] is not False or review['tests_state']!='STOPPED':raise ValueError('VERSION-HANDOFF-SCOPE')
    if app['artifact']!='homensai-auto-vpn_'+package+'_all.ipk' or not re.fullmatch('[a-f0-9]{64}',app['sha256']):raise ValueError('VERSION-ARTIFACT')
    artifact=ROOT/'router/dist'/app['artifact']
    if artifact.exists() and hashlib.sha256(artifact.read_bytes()).hexdigest()!=app['sha256']:raise ValueError('VERSION-ARTIFACT-HASH')
    released=ROOT/'releases'/app['artifact']
    if app['sha256']!='0'*64:
        kit=(ROOT/'router-test-kit/02-install.sh').read_text(encoding='utf-8')
        if re.search(r'^EXPECTED_SHA=(.+)$',kit,re.M).group(1)!=app['sha256'] or re.search(r'^EXPECTED_VERSION=(.+)$',kit,re.M).group(1)!=package:
            raise ValueError('VERSION-INSTALL-KIT')
        if released.exists() and (hashlib.sha256(released.read_bytes()).hexdigest()!=app['sha256'] or int(re.search(r'^EXPECTED_SIZE=(.+)$',kit,re.M).group(1))!=released.stat().st_size):
            raise ValueError('VERSION-RELEASE-ARTIFACT')
    return {'result':'PASS','application':app['version'],'package':package,'ui':app['ui_module']+'/'+app['ui_stylesheet'],'handoff':review['version'],'scope':'read-only metadata agreement; not a product test or device acceptance'}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path,default=ROOT/'VERSION.json');a=p.parse_args()
    try:print(json.dumps(validate(a.manifest),sort_keys=True))
    except (OSError,ValueError,KeyError,TypeError,AttributeError) as error:print('VERSION-CHECK-FAILED:'+str(error) if isinstance(error,ValueError) else 'VERSION-CHECK-FAILED:INVALID-METADATA');raise SystemExit(1)
