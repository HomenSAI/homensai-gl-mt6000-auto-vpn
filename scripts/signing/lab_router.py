"""A simulated router for the signing drills: the real 02-install.sh and the real homensai-vpn-trust-key on a throwaway
file tree, in a local container (never a device; no network inside). Where the drills run them, best first:

  alpine + real usign  BusyBox ash/sed/sha256sum as on the router, usign from the pinned OpenWrt SDK (private/signing-lab-tools)
  python-slim + twin   the same scripts under dash with scripts/signing/pyusign.py when the real binary cannot be had
  host sh + twin       POSIX hosts without docker, like the offline CI containers

opkg, uci and nft are shell functions that only record their calls, exactly as qa/test_signing_install.py does: the signature
and chain logic under test is the unmodified script, only EXPECTED_* are set to the fake package. Containers run with
--rm --network none --pull=never and are the only ones this module ever touches.
"""
import hashlib
import io
import os
import shlex
import shutil
import subprocess
import sys
import tarfile
import tempfile
import types
from pathlib import Path

import lab_mode

ALPINE = 'alpine:3.20'
SLIM = 'python:3.12-slim'
PYUSIGN = Path(__file__).resolve().parent/'pyusign.py'
SIGNING_DIR = Path(__file__).resolve().parent
USIGN_SHA256 = 'b301aed2b315f86c7828b90b86df73cdac7b73bd72344c51b7b3dae828facb2a'
LOADER, LIBC = 'ld-linux-x86-64.so.2', 'libc.so.6'
FUNCTIONS = r'''
opkg() { printf 'opkg %s\n' "$*" >> "$SIM/calls"; case "$1" in status) if [ -s "$SIM/installed" ]; then printf 'Package: homensai-auto-vpn\nVersion: %s\n' "$(cat "$SIM/installed")"; fi; return 0;; install) printf '%s\n' "$SIM_NEW" > "$SIM/installed"; return 0;; *) return 71;; esac; }
uci() { printf 'uci %s\n' "$*" >> "$SIM/calls"; return 1; }
nft() { return 1; }
id() { [ "$1" = -u ] && echo 0; }
'''


def _docker(*args, timeout=120, input_text=None):
    """Bytes on stdin: text mode on Windows would turn the answer's \n into \r\n."""
    process = subprocess.run(('docker',)+args, capture_output=True, timeout=timeout, input=None if input_text is None else input_text.encode('utf-8'))
    process.stdout, process.stderr = process.stdout.decode('utf-8', 'replace'), process.stderr.decode('utf-8', 'replace')
    return process


def docker_ready():
    try:
        return _docker('version', '--format', '{{.Server.Version}}', timeout=20).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def image_ready(image):
    try:
        return _docker('image', 'inspect', image, '--format', '{{.Id}}', timeout=20).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def mount(path):
    return Path(path).resolve().as_posix()


def tools_root():
    value = os.environ.get('HOMENSAI_LAB_TOOLS')
    if value:
        return Path(value)
    try:
        return lab_mode.default_lab_root().parent/'signing-lab-tools'
    except lab_mode.LabRefused:
        return Path(tempfile.gettempdir())/'homensai-signing-lab-tools'


def sdk_archives(tools):
    return sorted(tools.parent.glob('sdk-*/openwrt-sdk-*x86-64*.tar.xz'))


def real_usign(tools, say=lambda text: None):
    """The real usign host binary, extracted once from the pinned SDK archive with a throwaway container. Returns its path."""
    target = tools/'usign'/'.usign.bin'
    if not target.is_file():
        archives = sdk_archives(tools)
        if not archives or not image_ready(SLIM):
            return None
        say('extracting the real usign from %s (about a minute, once)' % archives[0].name)
        target.parent.mkdir(parents=True, exist_ok=True)
        code = ("import tarfile\n"
                "with tarfile.open('/in/%s','r|xz') as t:\n"
                "    for m in t:\n"
                "        if m.name.endswith('staging_dir/host/bin/.usign.bin'):\n"
                "            open('/out/.usign.bin','wb').write(t.extractfile(m).read());break\n" % archives[0].name)
        _docker('run', '--rm', '--pull=never', '--network', 'none', '--mount', 'type=bind,source=%s,target=/in,readonly' % mount(archives[0].parent),
                '--mount', 'type=bind,source=%s,target=/out' % mount(target.parent), SLIM, 'python3', '-c', code, timeout=400)
    return target if target.is_file() else None


def glibc(tools):
    """The SDK host binary needs glibc; alpine has none, so its loader and libc come from the slim image, once."""
    folder = tools/'glibc'
    if (folder/LOADER).is_file() and (folder/LIBC).is_file():
        return folder
    if not image_ready(SLIM):
        return None
    folder.mkdir(parents=True, exist_ok=True)
    created = _docker('create', '--pull=never', '--network', 'none', SLIM, 'true', timeout=60)
    if created.returncode:
        return None
    name = created.stdout.strip()
    try:
        for source, target in (('/usr/lib/x86_64-linux-gnu/'+LOADER, LOADER), ('/usr/lib/x86_64-linux-gnu/'+LIBC, LIBC)):
            _docker('cp', '-L', '%s:%s' % (name, source), str(folder/target), timeout=60)
    finally:
        _docker('rm', name, timeout=60)
    return folder if (folder/LOADER).is_file() and (folder/LIBC).is_file() else None


class Sandbox:
    """How this PC can run the router scripts; kind None means it cannot, and the drills say SKIP, never PASS."""
    def __init__(self, kind, label, image=None, tools=None, real=False):
        self.kind, self.label, self.image, self.tools, self.real = kind, label, image, tools, real

    @classmethod
    def detect(cls, say=lambda text: None):
        tools = tools_root()
        if docker_ready():
            if image_ready(ALPINE):
                usign, libc = real_usign(tools, say), glibc(tools)
                if usign and libc and hashlib.sha256(usign.read_bytes()).hexdigest() == USIGN_SHA256:
                    return cls('alpine', 'alpine:3.20, BusyBox ash/sed + real OpenWrt 21.02.7 usign', ALPINE, tools, True)
            if image_ready(SLIM):
                return cls('slim', 'python:3.12-slim, dash + Python usign twin', SLIM, tools, False)
        if os.name == 'posix' and shutil.which('sh') and shutil.which('sha256sum'):
            return cls('host', 'this host: sh + Python usign twin')
        return cls(None, 'no container and no POSIX shell: router steps are skipped')

    def execute(self, folder, script, input_text=None, timeout=240):
        """Run a shell fragment with SIM pointing at the simulated router tree. A container gets the whole tree as a tar on stdin and
        gives it back the same way: bind mounts of Docker Desktop on Windows cost a quarter of a second per small file."""
        if self.kind == 'host':
            (Path(folder)/'.stdin').write_text(input_text or '', encoding='utf-8')
            environment = dict(os.environ, SIM=str(folder), PATH='/usr/bin:/bin', SIM_PYTHON=sys.executable, SIM_TWIN=str(PYUSIGN))
            return subprocess.run(['sh', '-c', script], cwd=str(folder), capture_output=True, text=True, timeout=timeout,
                                  env=environment, input=input_text, encoding='utf-8', errors='replace')
        outer = ('mkdir -p /tmp/w && tar -xf - -C /tmp/w && cd /tmp/w/sim && SIM=/tmp/w/sim; export SIM\n'
                 'sh -c "$1" run <"$SIM/.stdin" >/tmp/w/out 2>/tmp/w/err; echo $? >/tmp/w/rc\n'
                 'cd /tmp/w && tar -cf - sim out err rc\n')
        process = subprocess.run(('docker', 'run', '-i', '--rm', '--pull=never', '--network', 'none', '--read-only', '--cap-drop=ALL', '--security-opt=no-new-privileges',
                                  '--tmpfs', '/tmp:rw,exec,nosuid,nodev,size=32m', '--env', 'SIM_PYTHON=python3', '--env', 'SIM_TWIN=/tmp/w/signing/pyusign.py',
                                  self.image, 'sh', '-c', outer, 'outer', script), input=self.pack(folder, input_text), capture_output=True, timeout=timeout)
        return self.unpack(folder, process)

    def pack(self, folder, input_text):
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode='w') as tar:
            def add(name, data, mode=0o644):
                info = tarfile.TarInfo(name)
                info.size, info.mode = len(data), mode
                tar.addfile(info, io.BytesIO(data))
            for path in sorted(Path(folder).rglob('*')):
                if path.is_file():
                    add('sim/'+path.relative_to(folder).as_posix(), path.read_bytes())
            add('sim/.stdin', (input_text or '').encode('utf-8'))
            if self.kind == 'alpine':
                add('tools/usign', (self.tools/'usign'/'.usign.bin').read_bytes(), 0o755)
                for name in (LOADER, LIBC):
                    add('tools/'+name, (self.tools/'glibc'/name).read_bytes(), 0o755)
            else:
                for name in ('pyusign.py', 'usign_format.py'):
                    add('signing/'+name, (SIGNING_DIR/name).read_bytes())
        return buffer.getvalue()

    def unpack(self, folder, process):
        """The tree comes back as the script left it; a broken reply is a failed step, never a success."""
        result = types.SimpleNamespace(returncode=125, stdout='', stderr=process.stderr.decode('utf-8', 'replace'))
        if process.returncode:
            return result
        with tarfile.open(fileobj=io.BytesIO(process.stdout)) as tar:
            lab_mode.remove_tree(folder)
            Path(folder).mkdir(parents=True)
            for member in tar:
                if member.isfile():
                    data = tar.extractfile(member).read()
                    if member.name in ('out', 'err', 'rc'):
                        setattr(result, {'out': 'stdout', 'err': 'stderr', 'rc': 'returncode'}[member.name], data.decode('utf-8', 'replace'))
                    elif member.name.startswith('sim/') and '..' not in member.name:
                        target = Path(folder)/member.name[4:]
                        target.parent.mkdir(parents=True, exist_ok=True)
                        target.write_bytes(data)
        result.returncode = int(str(result.returncode).strip())
        return result

    def usign_function(self):
        if self.kind == 'alpine':
            return 'usign() { /tmp/w/tools/%s --library-path /tmp/w/tools /tmp/w/tools/usign "$@"; }\n' % LOADER
        return 'usign() { "$SIM_PYTHON" -I "$SIM_TWIN" "$@"; }\n'


class Result:
    def __init__(self, process, installed):
        self.code, self.stdout, self.stderr, self.installed = process.returncode, process.stdout or '', process.stderr or '', installed

    @property
    def text(self):
        return (self.stdout+self.stderr).strip()


class SimRouter:
    """One simulated router: its installed keys, admin keys, recorded chain and package version live in `folder`."""
    def __init__(self, sandbox, folder):
        self.sandbox = sandbox
        self.folder = Path(folder)
        (self.folder/'kit').mkdir(parents=True, exist_ok=True)
        (self.folder/'etc'/'keys').mkdir(parents=True, exist_ok=True)
        (self.folder/'pkg').mkdir(exist_ok=True)
        (self.folder/'kit/fingerprint.before').write_text('baseline\n', encoding='ascii')
        (self.folder/'functions.sh').write_bytes((FUNCTIONS+sandbox.usign_function()).encode('ascii'))
        (self.folder/'trust-key').write_bytes(lab_mode.TRUST_TOOL.read_bytes().replace(b'\r\n', b'\n'))

    def install_keys(self, repo, names=None):
        """The trust list a previously installed package left on the router."""
        source = repo/'router/files/etc/homensai-vpn/keys'
        for path in source.iterdir():
            if path.name == 'revoked' or names is None or path.name in names:
                shutil.copyfile(path, self.folder/'etc/keys'/path.name)

    def script_for(self, kit, payload, package_version):
        """02-install.sh of the lab tree, with only the EXPECTED_* literals of the fake package filled in."""
        values = {'EXPECTED_SHA': hashlib.sha256(payload).hexdigest(), 'EXPECTED_SIZE': str(len(payload)), 'EXPECTED_VERSION': package_version}
        lines = []
        for line in kit.read_bytes().decode('utf-8').replace('\r\n', '\n').split('\n'):
            name = line.split('=', 1)[0]
            lines.append(name+'='+values[name] if name in values and '=' in line and not line.startswith('#') else line)
        (self.folder/'02-install.sh').write_bytes('\n'.join(lines).encode('utf-8'))

    def install(self, kit, ipk_name, payload, chain_data, signature, package_version, *flags):
        pkg = self.folder/'pkg'
        pkg.mkdir(exist_ok=True)
        for old in pkg.iterdir():
            old.unlink()
        (pkg/ipk_name).write_bytes(payload)
        if chain_data is not None:
            (pkg/'CHAIN.jsonl').write_bytes(chain_data)
        if signature is not None:
            (pkg/(ipk_name+'.sig')).write_bytes(signature)
        self.script_for(kit, payload, package_version)
        calls = self.folder/'calls'
        if calls.exists():
            calls.unlink()
        arguments = ' '.join(('"$SIM/pkg/%s"' % ipk_name,)+tuple(shlex.quote(item) for item in flags))
        script = ('export HOMENSAI_KIT="$SIM/kit" HOMENSAI_KEYS="$SIM/etc/keys" HOMENSAI_LOCAL_KEYS="$SIM/etc/keys.local" '
                  'HOMENSAI_CHAIN="$SIM/etc/chain.jsonl" SIM_NEW=%s\n. "$SIM/functions.sh"\nset -- %s\n. "$SIM/02-install.sh"\n' %
                  (shlex.quote(package_version), arguments))
        process = self.sandbox.execute(self.folder, script)
        installed = calls.is_file() and any(line.startswith('opkg install') for line in calls.read_text(encoding='utf-8').splitlines())
        return Result(process, installed)

    def trust_key(self, *args, input_text=None):
        arguments = ' '.join('"$SIM/%s"' % item[4:] if item.startswith('sim:') else shlex.quote(item) for item in args)
        script = ('export HOMENSAI_KEYS="$SIM/etc/keys" HOMENSAI_LOCAL_KEYS="$SIM/etc/keys.local"\n. "$SIM/functions.sh"\nset -- %s\n'
                  '. "$SIM/trust-key"\n' % arguments)
        return Result(self.sandbox.execute(self.folder, script, input_text), False)

    def put_file(self, name, data):
        (self.folder/name).write_bytes(data)

    def usign(self, *args):
        arguments = ' '.join('"$SIM/%s"' % item[4:] if item.startswith('sim:') else shlex.quote(item) for item in args)
        return Result(self.sandbox.execute(self.folder, '. "$SIM/functions.sh"\nusign %s\n' % arguments), False)
