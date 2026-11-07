"""Read-only agreement check for application, package, selected UI and handoff versions.

Besides the version literals it checks the release identities that a substitution could change unnoticed (audit
06.11.2026, F-96): the package NAME, the Lua runtime version, the version embedded in the shipped page, the LuCI
controller, the menu/ACL/rpcd identity, the declared optional page modules against the ones the package selects, and the
install kit's version, hash and size (an unbuilt package leaves the kit explicitly unavailable, F-10)."""
import argparse,ast,hashlib,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PACKAGE_NAME='homensai-auto-vpn'
ACL_NAME='luci-app-homensai-vpn'
UBUS_OBJECT='homensai-vpn'
UNBUILT='0'*64

def literal(path,name):
    for node in ast.parse(path.read_text(encoding='utf-8')).body:
        if isinstance(node,ast.Assign) and any(isinstance(target,ast.Name) and target.id==name for target in node.targets):return ast.literal_eval(node.value)
    raise ValueError('VERSION-LITERAL-MISSING')

def single(pattern,text,code):
    found=re.findall(pattern,text,re.M)
    if len(found)!=1:raise ValueError(code)
    return found[0]

def lazy_selection(root):
    """Optional page modules (help<N>.js, pick<N>.js) the package builder selects from root/router/files."""
    sys.dont_write_bytecode=True
    sys.path.insert(0,str(ROOT/'router'))
    try:from build_ipk import selected_source_files
    finally:sys.path.pop(0)
    lazy='www/luci-static/resources/homensai-vpn/'
    return sorted('homensai-vpn/'+name[len(lazy):] for name,_,_ in selected_source_files(root/'router/files')
                  if name.startswith(lazy) and re.fullmatch(r'(?:help|pick)[0-9]+\.js',name[len(lazy):]))

def validate(path,root=ROOT):
    root=Path(root)
    if path.stat().st_size>16384:raise ValueError('VERSION-MANIFEST-SIZE')
    data=json.loads(path.read_text(encoding='utf-8-sig'));app=data['application'];review=data['handoff']
    if data.get('schema')!=1 or not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+(?:-(?:alpha|beta)[0-9]+)?',app['version']):raise ValueError('VERSION-APPLICATION')
    if type(app['package_revision']) is not int or app['package_revision']<1:raise ValueError('VERSION-PACKAGE-REVISION')
    package=app['version']+'-'+str(app['package_revision'])
    if app['package_version']!=package or app['release_tag']!='v'+app['version']:raise ValueError('VERSION-PACKAGE')
    make=(root/'router/Makefile').read_text(encoding='utf-8')
    if re.search(r'^PKG_VERSION:=(.+)$',make,re.M).group(1)!=app['version'] or re.search(r'^PKG_RELEASE:=(.+)$',make,re.M).group(1)!=str(app['package_revision']):raise ValueError('VERSION-MAKEFILE')
    if literal(root/'router/build_ipk.py','VERSION')!=package or literal(root/'router/files/usr/lib/homensai-vpn/agent.py','VERSION')!=app['version']:raise ValueError('VERSION-RUNTIME')
    # Package identity: builder NAME, SDK PKG_NAME and the artifact name agree.
    if literal(root/'router/build_ipk.py','NAME')!=PACKAGE_NAME or single(r'^PKG_NAME:=(.+)$',make,'VERSION-PACKAGE-NAME')!=PACKAGE_NAME:raise ValueError('VERSION-PACKAGE-NAME')
    # The Lua supervisor/monitor reports the same version as the Python agent.
    lua=(root/'router/files/usr/lib/homensai-vpn/lua/version.lua').read_text(encoding='utf-8')
    if single(r"^return '([^']*)'\s*$",lua,'VERSION-LUA')!=app['version']:raise ValueError('VERSION-LUA')
    if not re.fullmatch(r'dashboard[0-9]+',app['ui_module']) or not re.fullmatch(r'ui[0-9]+\.css',app['ui_stylesheet']):raise ValueError('VERSION-UI-PATH')
    menu=json.loads((root/'router/files/usr/share/luci/menu.d/luci-app-homensai-vpn.json').read_text(encoding='utf-8'))
    entry=menu['admin/services/homensai-vpn']
    if entry['action']['path']!='homensai-vpn/'+app['ui_module']:raise ValueError('VERSION-UI-MENU')
    ui=root/'router/files/www/luci-static/resources/view/homensai-vpn';script=(ui/(app['ui_module']+'.js')).read_text(encoding='utf-8')
    if set(re.findall(r'\bui[0-9]+\.css\b',script))!={app['ui_stylesheet']} or not (ui/app['ui_stylesheet']).is_file():raise ValueError('VERSION-UI-CSS')
    # The version the shipped page shows and the stylesheet it names.
    if (single(r"\bHV_AGENT='([^']*)'",script,'VERSION-UI-EMBEDDED')!=app['version']
            or single(r"\bHV_STYLESHEET='([^']*)'",script,'VERSION-UI-EMBEDDED')!=app['ui_stylesheet']):raise ValueError('VERSION-UI-EMBEDDED')
    controller=(root/'router/files/usr/lib/lua/luci/controller/homensai_vpn.lua').read_text(encoding='utf-8')
    if single(r'^-- UI resource for (\S+)$',controller,'VERSION-UI-CONTROLLER')!=app['version'] or "view('homensai-vpn/"+app['ui_module']+"')" not in controller:
        raise ValueError('VERSION-UI-CONTROLLER')
    # ACL identity: the menu depends on this ACL, which grants exactly the package's own ubus object served by its rpcd plugin.
    acl=json.loads((root/'router/files/usr/share/rpcd/acl.d'/(ACL_NAME+'.json')).read_text(encoding='utf-8'))
    if (set(acl)!={ACL_NAME} or entry.get('depends',{}).get('acl')!=[ACL_NAME]
            or any(set(acl[ACL_NAME].get(kind,{}).get('ubus',{}))!={UBUS_OBJECT} for kind in ('read','write'))
            or not (root/'router/files/usr/libexec/rpcd'/UBUS_OBJECT).is_file()):raise ValueError('VERSION-ACL-IDENTITY')
    # Declared optional modules are exactly the ones the package ships.
    declared=app.get('ui_lazy_modules')
    if not isinstance(declared,list) or sorted(declared)!=lazy_selection(root):raise ValueError('VERSION-UI-LAZY')
    if not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+',review['version']) or review['release_tag']!='handoff-v'+review['version']:raise ValueError('VERSION-HANDOFF')
    if review['kind']!='documentation-review-checkpoint' or review['application_changed'] is not False or review['tests_state']!='STOPPED':raise ValueError('VERSION-HANDOFF-SCOPE')
    if app['artifact']!=PACKAGE_NAME+'_'+package+'_all.ipk' or not re.fullmatch('[a-f0-9]{64}',app['sha256']):raise ValueError('VERSION-ARTIFACT')
    artifact=root/'router/dist'/app['artifact']
    if artifact.exists() and hashlib.sha256(artifact.read_bytes()).hexdigest()!=app['sha256']:raise ValueError('VERSION-ARTIFACT-HASH')
    released=root/'releases'/app['artifact']
    # The install kit always names this package version; its hash and size are either the recorded package's or the
    # explicit "not built yet" marker (the kit then refuses with KIT-UNAVAILABLE). Never the previous package's.
    kit=(root/'router-test-kit/02-install.sh').read_text(encoding='utf-8')
    kit_sha=single(r'^EXPECTED_SHA=(.*)$',kit,'VERSION-INSTALL-KIT');kit_size=single(r'^EXPECTED_SIZE=(.*)$',kit,'VERSION-INSTALL-KIT')
    if single(r'^EXPECTED_VERSION=(.*)$',kit,'VERSION-INSTALL-KIT')!=package:raise ValueError('VERSION-INSTALL-KIT')
    verify=(root/'router-test-kit/03-verify.sh').read_text(encoding='utf-8')
    if single(r'^EXPECTED_VERSION=(.*)$',verify,'VERSION-INSTALL-KIT')!=app['version']:raise ValueError('VERSION-INSTALL-KIT')
    if app['sha256']==UNBUILT:
        if kit_sha!=UNBUILT or kit_size!='0' or 'KIT-UNAVAILABLE' not in kit:raise ValueError('VERSION-INSTALL-KIT-UNBUILT')
    else:
        if kit_sha!=app['sha256'] or not re.fullmatch(r'[1-9][0-9]*',kit_size):raise ValueError('VERSION-INSTALL-KIT')
        if released.exists() and (hashlib.sha256(released.read_bytes()).hexdigest()!=app['sha256'] or int(kit_size)!=released.stat().st_size):
            raise ValueError('VERSION-RELEASE-ARTIFACT')
    return {'result':'PASS','application':app['version'],'package':package,'ui':app['ui_module']+'/'+app['ui_stylesheet'],'handoff':review['version'],
            'kit':'recorded' if app['sha256']!=UNBUILT else 'unavailable-until-packaged','scope':'read-only metadata agreement; not a product test or device acceptance'}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path,default=ROOT/'VERSION.json');a=p.parse_args()
    try:print(json.dumps(validate(a.manifest),sort_keys=True))
    except (OSError,ValueError,KeyError,TypeError,AttributeError) as error:print('VERSION-CHECK-FAILED:'+str(error) if isinstance(error,ValueError) else 'VERSION-CHECK-FAILED:INVALID-METADATA');raise SystemExit(1)
