"""Freeze only public synthetic-preview inputs so a long browser run never mixes builds."""
import hashlib
import json
import mimetypes
from pathlib import Path
import subprocess


def freeze_preview(repo):
    repo=Path(repo)
    app=json.loads((repo/'VERSION.json').read_text(encoding='utf-8-sig'))['application']
    menu=json.loads((repo/'router/files/usr/share/luci/menu.d/luci-app-homensai-vpn.json').read_text(encoding='utf-8'))
    module=menu['admin/services/homensai-vpn']['action']['path'].split('/')[-1]
    if module!=app['ui_module'] or not __import__('re').fullmatch(r'dashboard[0-9]+',module):raise ValueError('PREVIEW-MODULE-MISMATCH')
    base=repo/'router/files/www/luci-static/resources/view/homensai-vpn'
    prefix='/router/files/www/luci-static/resources/view/homensai-vpn/'
    files={prefix+p.relative_to(base).as_posix():p.read_bytes() for p in base.rglob('*') if p.is_file() and p.suffix.lower() in ('.js','.css','.svg','.png','.woff','.woff2','.ttf')}
    files['/']=files['/qa/ui-preview/index.html']=(repo/'qa/ui-preview/index.html').read_bytes()
    files['/qa/ui-preview/stub.js']=(repo/'qa/ui-preview/stub.js').read_bytes().replace(b"version:'0.8.0-alpha2'",('version:'+json.dumps(app['version'])).encode())
    # Capture app-load failures before the persona can attach to a fully rendered document.
    files['/qa/ui-preview/stub.js']=br'''window.fixtureErrors=[];window.fixtureErrorDetails=[];window.addEventListener('error',function(e){window.fixtureErrors.push(String(e.message||e).slice(0,160));window.fixtureErrorDetails.push({message:String(e.message||e).slice(0,160),source:String(e.filename||'').split('?')[0],line:e.lineno,column:e.colno,stack:String(e.error&&e.error.stack||'').replace(/\?[^\s)]+/g,'').slice(0,1200)});});window.addEventListener('unhandledrejection',function(e){window.fixtureErrors.push('REJECTION '+String(e.reason&&e.reason.message||e.reason).slice(0,160));});
'''+files['/qa/ui-preview/stub.js']
    files['/preview-module.js']=files[prefix+module+'.js']
    files['/preview-router.js']=b'window.HOMENSAI_PREVIEW_ROUTER_ORIGIN=null;'
    hashes={path:hashlib.sha256(data).hexdigest() for path,data in sorted(files.items())}
    frozen_id=hashlib.sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest()
    try:
        result=subprocess.run(['git','rev-parse','HEAD'],cwd=repo,capture_output=True,text=True,timeout=10)
        git=result.stdout.strip() if result.returncode==0 else None
        state=subprocess.run(['git','diff','--quiet','HEAD','--'],cwd=repo,capture_output=True,timeout=10)
        dirty=state.returncode==1 if state.returncode in (0,1) else None
    except (OSError,subprocess.TimeoutExpired):git=None;dirty=None
    harness={p.relative_to(repo).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in (repo/'qa/ui-probe').glob('*') if p.is_file() and p.suffix in ('.js','.py')}
    identity={'git_head':git,'git_tracked_dirty':dirty,'version':app['version'],'recorded_source_fingerprint':app['source_fingerprint'],'recorded_package_sha256':app.get('sha256'),'preview_snapshot_sha256':frozen_id,'ui_module_sha256':hashes['/preview-module.js'],'ui_stylesheet_sha256':hashes[prefix+app['ui_stylesheet']],'harness_sha256':hashlib.sha256(json.dumps(harness,sort_keys=True).encode()).hexdigest()}
    return files,identity,{'identity':identity,'served_assets':hashes,'harness_files':harness}


def content_type(path):
    kind='text/html' if path=='/' else mimetypes.guess_type(path)[0] or 'application/octet-stream'
    return kind+'; charset=utf-8' if kind.startswith(('text/','application/javascript')) else kind
