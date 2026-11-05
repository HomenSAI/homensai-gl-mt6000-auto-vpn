#!/usr/bin/env python3
"""Build the probe trust anchors: router/files/usr/lib/homensai-vpn/probe-anchors/<host>.pem and pins.json.

Python 3.9+, standard library only, offline. Input: a directory of single-certificate PEM files named as in the
GL firmware's /etc/ssl/certs (ca-certificates 20260601-1 of GL 4.11), e.g. the firmware audit's
rootfs-files/etc/ssl/certs. Every anchor is therefore a root the stock firmware already trusts: the pinned set is
a strict subset of the system trust, never wider (docs/architecture/PROBE-AUTHENTICITY-2026-11-03.ru.md).

    python3 scripts/build_probe_anchors.py <certs-dir>            write the PEM files and pins.json
    python3 scripts/build_probe_anchors.py <certs-dir> --check    compare with the committed files, exit 1 on drift

Rotation: edit ANCHORS below (role 'current' = the root the host chains to today, 'backup' = roots the operator
has used or may move to), run the script with the newer firmware bundle, run the tests and ship a package.
"""
import base64
import hashlib
import json
import re
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent/'router/files/usr/lib/homensai-vpn/probe-anchors'
SOURCE = 'ca-certificates 20260601-1 of the GL 4.11 firmware (/etc/ssl/certs)'
OBSERVED = '2026-11-03'

# host -> [(certificate file name without .crt, role)]
ANCHORS = {
    'one.one.one.one': [
        ('SSL.com_Root_Certification_Authority_ECC', 'current'),   # leaf <- SSL.com SSL Intermediate CA ECC R2
        ('SSL.com_Root_Certification_Authority_RSA', 'backup'),
        ('SSL.com_TLS_ECC_Root_CA_2022', 'backup'),
        ('SSL.com_TLS_RSA_Root_CA_2022', 'backup'),
        ('DigiCert_Global_Root_G2', 'backup'),                     # the 1.1.1.1 issuer before SSL.com
        ('DigiCert_Global_Root_G3', 'backup'),
        ('DigiCert_TLS_ECC_P384_Root_G5', 'backup'),
        ('DigiCert_TLS_RSA4096_Root_G5', 'backup'),
        ('GTS_Root_R1', 'backup'),                                 # Cloudflare edge certificates also use GTS
        ('GTS_Root_R3', 'backup'),
        ('GTS_Root_R4', 'backup'),
        ('ISRG_Root_X1', 'backup'),                                # ... and Let's Encrypt
        ('ISRG_Root_X2', 'backup'),
    ],
    'dns.google': [
        ('GTS_Root_R4', 'current'),                                # leaf <- WE2 <- GTS Root R4
        ('GTS_Root_R1', 'backup'),                                 # WR2 <- GTS Root R1
        ('GTS_Root_R3', 'backup'),
        ('GlobalSign_ECC_Root_CA_-_R4', 'backup'),                 # owned by Google Trust Services
    ],
    'dns.quad9.net': [
        ('DigiCert_Global_Root_G3', 'current'),                    # leaf <- DigiCert Global G3 TLS ECC SHA384 2020 CA1
        ('DigiCert_Global_Root_G2', 'backup'),
        ('DigiCert_TLS_ECC_P384_Root_G5', 'backup'),
        ('DigiCert_TLS_RSA4096_Root_G5', 'backup'),
        ('ISRG_Root_X1', 'backup'),
        ('ISRG_Root_X2', 'backup'),
    ],
}

PEM = re.compile(r'-----BEGIN CERTIFICATE-----\s+([A-Za-z0-9+/=\s]+?)-----END CERTIFICATE-----')


def der_items(data, start, end):
    """The (tag, value_start, value_end, item_end) of each DER item between start and end."""
    items = []
    while start < end:
        tag = data[start]
        length = data[start+1]
        offset = start+2
        if length & 0x80:
            count = length & 0x7f
            length = int.from_bytes(data[offset:offset+count], 'big')
            offset += count
        items.append((tag, offset, offset+length, start))
        start = offset+length
    return items


def certificate_facts(der):
    """SPKI sha256 (base64, as curl --pinnedpubkey and HPKP write it), notAfter (YYYY-MM-DD), subject DER sha256."""
    (_, cert_start, cert_end, _), = der_items(der, 0, len(der))
    tbs = der_items(der, cert_start, cert_end)[0]
    fields = der_items(der, tbs[1], tbs[2])
    if fields[0][0] == 0xa0:   # explicit version
        fields = fields[1:]
    validity, spki = fields[3], fields[5]
    not_after = der_items(der, validity[1], validity[2])[1]
    text = der[not_after[1]:not_after[2]].decode('ascii')
    if not_after[0] == 0x17:   # UTCTime YYMMDDhhmmssZ
        year = int(text[:2])
        text = ('19' if year >= 50 else '20')+text
    day = '%s-%s-%s' % (text[:4], text[4:6], text[6:8])
    spki_der = der[spki[3]:spki[2]]
    return base64.b64encode(hashlib.sha256(spki_der).digest()).decode('ascii'), day


def read_pem(path):
    blocks = PEM.findall(Path(path).read_text(encoding='ascii'))
    if len(blocks) != 1:
        raise SystemExit('%s: expected exactly one certificate' % path)
    der = base64.b64decode(''.join(blocks[0].split()))
    return der, '-----BEGIN CERTIFICATE-----\n'+'\n'.join(
        base64.b64encode(der).decode('ascii')[i:i+64] for i in range(0, len(base64.b64encode(der)), 64))+'\n-----END CERTIFICATE-----\n'


def build(certs):
    files, pins = {}, {'version': 1, 'source': SOURCE, 'observed': OBSERVED,
                       'scope': 'trust anchors of the three fixed probe hosts; a probe trusts only these roots',
                       'hosts': {}}
    for host, rows in sorted(ANCHORS.items()):
        text, entries = [], []
        for name, role in rows:
            der, pem = read_pem(Path(certs)/(name+'.crt'))
            spki, not_after = certificate_facts(der)
            text.append('# %s (%s)\n%s' % (name, role, pem))
            entries.append({'name': name, 'role': role, 'spki_sha256': spki, 'not_after': not_after})
        files[host+'.pem'] = ''.join(text)
        pins['hosts'][host] = entries
    files['pins.json'] = json.dumps(pins, indent=1, sort_keys=True)+'\n'
    return files


def main(argv):
    if len(argv) < 2:
        raise SystemExit(__doc__)
    files = build(argv[1])
    if '--check' in argv[2:]:
        drift = [name for name, text in files.items() if not (OUT/name).is_file() or (OUT/name).read_text(encoding='ascii') != text]
        if drift:
            print('drift: '+', '.join(drift))
            return 1
        print('probe anchors match')
        return 0
    OUT.mkdir(parents=True, exist_ok=True)
    for name, text in files.items():
        (OUT/name).write_bytes(text.encode('ascii'))
    print('wrote %d files to %s' % (len(files), OUT))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
