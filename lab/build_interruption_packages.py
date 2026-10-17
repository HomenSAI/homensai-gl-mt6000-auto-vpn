"""Build private instrumented packages; never release or install on hardware."""
import argparse,hashlib,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--recovery-sha256',required=True);a=p.parse_args()
out=a.out.resolve()
if not out.is_relative_to((ROOT/'private').resolve()) or out.exists() or not re.fullmatch('[a-f0-9]{64}',a.recovery_sha256):raise ValueError('PRIVATE-LAB-OUTPUT-REQUIRED')
sys.path.insert(0,str(ROOT/'router'));import build_ipk
recovery=ROOT/'router/dist'/('homensai-auto-vpn_'+build_ipk.VERSION+'_all.ipk')
if hashlib.sha256(recovery.read_bytes()).hexdigest()!=a.recovery_sha256:raise ValueError('KNOWN-RECOVERY-HASH')
out.mkdir(parents=True);original=build_ipk.lifecycle_scripts
manifest={'package_version':build_ipk.VERSION,'recovery_sha256':a.recovery_sha256,'stages':[]}
try:
    for stage in ('preinst','postinst','before_rpc_reload'):
        hooks=original();gate="\nprintf '%s' "+stage+" > /tmp/homensai-upgrade-interruption/ready\ni=0; while [ ! -f /tmp/homensai-upgrade-interruption/release ] && [ $i -lt 240 ]; do sleep 0.25; i=$((i+1)); done\n"
        if stage in ('preinst','postinst'):
            anchor='[ -n "${IPKG_INSTROOT:-}" ] && exit 0\n';assert anchor in hooks[stage];hooks[stage]=hooks[stage].replace(anchor,anchor+gate,1)
        else:hooks['postinst']=hooks['postinst'].replace('/etc/init.d/rpcd reload',gate+'/etc/init.d/rpcd reload',1)
        build_ipk.lifecycle_scripts=lambda hooks=hooks:hooks
        target=build_ipk.build(out/stage);final=out/('lab-gated-'+stage+'.ipk');target.rename(final)
        manifest['stages'].append({'stage':stage,'filename':final.name,'sha256':hashlib.sha256(final.read_bytes()).hexdigest()})
finally:build_ipk.lifecycle_scripts=original
(out/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print('Private instrumented packages only; never release these artifacts')
