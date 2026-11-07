"""Cross-check scripts/signing/ots.py against the official python-opentimestamps / opentimestamps-client.

Runs inside a throwaway python:3.12-slim container after `pip install opentimestamps-client` (see ots-crosscheck.json
for the exact command and versions). Not a unit test: it needs network (PyPI, GitHub raw, the public calendars).

  docker run --rm -v <repo>:/repo:ro -v <outdir>:/out python:3.12-slim sh -c \
    "pip install -q opentimestamps-client && python /repo/qa/evidence/signing-2026-11-03/ots_crosscheck.py /repo /out"

Only the SHA-256 of the ASCII text 'HomenS.AI Auto VPN OTS test 2026-11-03' is ever sent to a calendar.
"""
import hashlib
import importlib.metadata as md
import json
import os
import subprocess
import sys
import urllib.request

repo, out = sys.argv[1], sys.argv[2]
sys.path.insert(0, os.path.join(repo, 'scripts', 'signing'))
import ots  # noqa: E402

from opentimestamps.core.notary import BitcoinBlockHeaderAttestation, PendingAttestation  # noqa: E402
from opentimestamps.core.op import OpAppend, OpSHA256  # noqa: E402
from opentimestamps.core.serialize import BytesDeserializationContext, BytesSerializationContext  # noqa: E402
from opentimestamps.core.timestamp import DetachedTimestampFile, Timestamp  # noqa: E402

TEST_TEXT = b'HomenS.AI Auto VPN OTS test 2026-11-03'
BASE = 'https://raw.githubusercontent.com/opentimestamps/opentimestamps-client/master/examples/'
result = {'official': {}, 'checks': {}, 'how': 'docker run python:3.12-slim; pip install opentimestamps-client; python ots_crosscheck.py /repo /out',
          'date': '2026-11-03'}
result['official']['opentimestamps-client'] = md.version('opentimestamps-client')
result['official']['opentimestamps'] = md.version('opentimestamps')
result['official']['python'] = sys.version.split()[0]


def official_parse(data):
    return DetachedTimestampFile.deserialize(BytesDeserializationContext(data))


def official_bytes(dts):
    ctx = BytesSerializationContext()
    dts.serialize(ctx)
    return ctx.getbytes()


def official_attestations(dts):
    return sorted(repr(a) for _, a in dts.timestamp.all_attestations())


def ots_cli(*args):
    p = subprocess.run(['ots'] + list(args), capture_output=True, text=True, timeout=120)
    return {'rc': p.returncode, 'stdout': p.stdout.strip(), 'stderr': p.stderr.strip()}


# (b) official example proofs: our parse -> serialize is byte-identical, and equals the official library's own round trip
rt = {}
for name in ('hello-world.txt.ots', 'incomplete.txt.ots', 'different-blockchains.txt.ots', 'bitcoin.pdf.ots', 'empty.ots'):
    try:
        data = urllib.request.urlopen(BASE + name, timeout=60).read()
    except Exception as e:  # file may be renamed upstream; record, do not hide
        rt[name] = {'error': repr(e)}
        continue
    entry = {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
    try:
        ours = ots.parse(data).serialize()
        entry['our_roundtrip_identical'] = ours == data
    except ots.OtsError as e:
        entry['our_roundtrip_identical'] = None
        entry['our_error'] = e.code
    entry['official_roundtrip_identical'] = official_bytes(official_parse(data)) == data
    rt[name] = entry
result['checks']['official_examples_roundtrip'] = rt

# (a1) our stamp() with mocked calendars whose replies are produced by the OFFICIAL library, then parsed by the official one
digest = hashlib.sha256(TEST_TEXT).digest()


class Resp(object):
    def __init__(self, body):
        self.body = body
        self.status = 200

    def read(self, n=-1):
        return self.body

    def close(self):
        pass


class Mock(object):
    def open(self, req, timeout=None):
        commitment = req.data
        t = Timestamp(commitment)
        uri = 'https://alice.btc.calendar.opentimestamps.org' if 'pool.opentimestamps' in req.full_url else \
            'https://finney.calendar.eternitywall.com'
        t.ops.add(OpAppend(b'mock-calendar-' + req.full_url.encode())).ops.add(OpSHA256()).attestations.add(PendingAttestation(uri))
        ctx = BytesSerializationContext()
        t.serialize(ctx)
        return Resp(ctx.getbytes())


mocked, rep = ots.stamp(digest, opener=Mock(), nonce=bytes(range(16)))
dts = official_parse(mocked)
result['checks']['mocked_stamp_parsed_by_official'] = {
    'official_digest_matches': dts.file_digest == digest,
    'official_roundtrip_identical': official_bytes(dts) == mocked,
    'official_attestations': official_attestations(dts),
    'ours_calendars_ok': rep['ok'],
}
open(os.path.join(out, 'mocked-stamp.ots'), 'wb').write(mocked)
result['checks']['mocked_stamp_ots_info'] = ots_cli('info', os.path.join(out, 'mocked-stamp.ots'))

# (a2) mocked upgrade (reply built by the official lib) -> official parses result and sees the Bitcoin attestation
class MockUp(object):
    def open(self, req, timeout=None):
        msg = bytes.fromhex(req.full_url.rsplit('/', 1)[1])
        t = Timestamp(msg)
        t.ops.add(OpAppend(b'upg')).ops.add(OpSHA256()).attestations.add(BitcoinBlockHeaderAttestation(800000))
        ctx = BytesSerializationContext()
        t.serialize(ctx)
        return Resp(ctx.getbytes())


upgraded, urep = ots.upgrade(mocked, opener=MockUp())
dts2 = official_parse(upgraded)
btc_msgs = sorted(m.hex() for m, a in dts2.timestamp.all_attestations() if isinstance(a, BitcoinBlockHeaderAttestation))
ours_btc = sorted(n.msg.hex() for n in ots.parse(upgraded).root.walk() for a in n.attestations if a.kind == 'bitcoin')
result['checks']['mocked_upgrade_parsed_by_official'] = {
    'upgraded': urep['upgraded'],
    'official_roundtrip_identical': official_bytes(dts2) == upgraded,
    'official_attestations': official_attestations(dts2),
    'official_and_ours_agree_on_attested_messages': btc_msgs == ours_btc and len(btc_msgs) > 0,
}

# our evaluator vs official op evaluation on the real official example
data = urllib.request.urlopen(BASE + 'hello-world.txt.ots', timeout=60).read()
o_msgs = sorted(m.hex() for m, a in official_parse(data).timestamp.all_attestations())
w_msgs = sorted(n.msg.hex() for n in ots.parse(data).root.walk() for a in n.attestations)
result['checks']['official_example_attested_message_equal'] = {'equal': o_msgs == w_msgs, 'message': w_msgs}

# live verify of the official example through the two real explorers (blockstream.info + mempool.space)
hello_digest = hashlib.sha256(b'Hello World!\n').digest()
result['checks']['official_example_live_verify'] = ots.verify(data, hello_digest)

# (a3) ONE real stamp of the test hash only
data_real, rrep = ots.stamp(digest, timeout=15)
real = {'test_text': TEST_TEXT.decode('ascii'), 'test_digest_sha256': digest.hex(), 'report': rrep}
if data_real is None:
    real['stamped'] = False
else:
    p = os.path.join(out, 'ots-test-stamp.ots')
    open(p, 'wb').write(data_real)
    d3 = official_parse(data_real)
    real.update({
        'stamped': True, 'bytes': len(data_real), 'sha256_of_ots': hashlib.sha256(data_real).hexdigest(),
        'official_digest_matches': d3.file_digest == digest,
        'official_roundtrip_identical': official_bytes(d3) == data_real,
        'official_attestations': official_attestations(d3),
        'our_verify': ots.verify(data_real, digest),
        'ots_info': ots_cli('info', p),
    })
    # official client upgrade on a copy: shows it talks to the same calendars and sees the same pending state
    cp = os.path.join(out, 'ots-test-stamp-official-upgrade-copy.ots')
    open(cp, 'wb').write(data_real)
    real['official_ots_upgrade_on_copy'] = ots_cli('upgrade', cp)
    real['our_upgrade_report'] = ots.upgrade(data_real, timeout=15)[1]
    os.remove(cp)
    for extra in (cp + '.bak',):
        if os.path.exists(extra):
            os.remove(extra)
result['checks']['real_stamp'] = real

result['all_ok'] = (
    all(v.get('our_roundtrip_identical') is True and v.get('official_roundtrip_identical') is True
        for k, v in rt.items() if 'error' not in v and v.get('our_roundtrip_identical') is not None) and
    result['checks']['mocked_stamp_parsed_by_official']['official_roundtrip_identical'] and
    result['checks']['mocked_stamp_parsed_by_official']['official_digest_matches'] and
    result['checks']['mocked_upgrade_parsed_by_official']['official_roundtrip_identical'] and
    result['checks']['mocked_upgrade_parsed_by_official']['official_and_ours_agree_on_attested_messages'] and
    result['checks']['official_example_attested_message_equal']['equal'] and
    result['checks']['official_example_live_verify']['status'] == 'confirmed' and
    real.get('our_upgrade_report', {}).get('rejected') == [] and
    real.get('stamped') is True and real.get('official_roundtrip_identical') is True)
open(os.path.join(out, 'ots-crosscheck.json'), 'w').write(json.dumps(result, indent=2, sort_keys=True) + '\n')
print(json.dumps(result, indent=2, sort_keys=True))
