"""Interoperability of scripts/backupcrypt/age_format.py with the real `age` tool (reference Go implementation) and
the `cryptography` package. Runs INSIDE a throwaway container that has `age`, `age-keygen` and pip:

  docker run --rm -v <repo>:/repo:ro -v <out>:/out python:3.12-slim sh -c \
    "apt-get update -qq && apt-get install -y -qq age >/dev/null && pip install -q cryptography && \
     python3 /repo/qa/evidence/age-tofu-2026-11-04/age_interop.py /out/age-interop.json"

Every key here is a throwaway test key made in the container; nothing of the owner is used.
"""
import hashlib
import json
import os
import subprocess
import sys
import tempfile

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'scripts', 'backupcrypt'))


def run(argv, data=None):
    return subprocess.run(argv, input=data, capture_output=True, check=True).stdout


def main(out_path):
    results = {'checks': [], 'tool': run(['age', '--version']).decode().strip()}
    os.environ['HOMENSAI_AGE_PURE'] = '1'
    import age_format as pure
    work = tempfile.mkdtemp()

    def check(name, ok, **extra):
        results['checks'].append(dict(name=name, ok=bool(ok), **extra))

    ours = pure.Identity.generate()
    ident_path = os.path.join(work, 'ours.txt')
    with open(ident_path, 'w') as stream:
        stream.write(ours.encode()+'\n')
    check('age-keygen -y reads our identity', run(['age-keygen', '-y', ident_path]).decode().strip() == ours.recipient().encode())
    keygen = os.path.join(work, 'theirs.txt')
    run(['age-keygen', '-o', keygen])
    theirs_text = [l for l in open(keygen).read().splitlines() if l.startswith('AGE-SECRET-KEY-1')][0]
    theirs = pure.Identity.parse(theirs_text)
    check('our recipient of an age-keygen identity', theirs.recipient().encode() == run(['age-keygen', '-y', keygen]).decode().strip())
    for size in (0, 1, 65535, 65536, 65537, 3*65536, 200001):
        data = os.urandom(size)
        digest = hashlib.sha256(data).hexdigest()
        for armored in (False, True):
            sealed = pure.encrypt(data, [theirs.recipient(), ours.recipient()], armored=armored)
            path = os.path.join(work, 'ours-%d-%d.age' % (size, armored))
            open(path, 'wb').write(sealed)
            plain = run(['age', '-d', '-i', keygen, path])
            check('age decrypts ours size=%d armored=%s' % (size, armored), hashlib.sha256(plain).hexdigest() == digest)
            source = os.path.join(work, 'plain-%d' % size)
            open(source, 'wb').write(data)
            argv = ['age', '-r', ours.recipient().encode(), '-r', theirs.recipient().encode()] + (['-a'] if armored else []) + [source]
            real = run(argv)
            check('we decrypt age size=%d armored=%s' % (size, armored), pure.decrypt(real, [ours]) == data)
    # the same with the vetted backend
    os.environ['HOMENSAI_AGE_PURE'] = '0'
    import importlib
    vetted = importlib.reload(pure)
    check('cryptography backend loaded', vetted.BACKEND is not None, backend=vetted.backend_name())
    data = os.urandom(150000)
    sealed = vetted.encrypt(data, [vetted.Identity.parse(theirs_text).recipient()])
    open(os.path.join(work, 'vetted.age'), 'wb').write(sealed)
    check('age decrypts the cryptography-backend output', run(['age', '-d', '-i', keygen, os.path.join(work, 'vetted.age')]) == data)
    results['passed'] = sum(c['ok'] for c in results['checks'])
    results['total'] = len(results['checks'])
    results['result'] = 'PASS' if results['passed'] == results['total'] else 'FAIL'
    with open(out_path, 'w') as stream:
        json.dump(results, stream, indent=1, sort_keys=True)
    print(results['result'], results['passed'], '/', results['total'])
    return 0 if results['result'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1]))
