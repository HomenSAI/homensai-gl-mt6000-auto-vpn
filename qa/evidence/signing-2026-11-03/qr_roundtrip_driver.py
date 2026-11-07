"""Evidence driver (not a unit test): secret -> payload -> QR PNG -> zxing-cpp decode -> import -> same public key,
and the TOTP enrolment URI -> QR -> decode -> same codes. Dummy keys only; run in a throwaway container with
`pip install zxing-cpp pillow`:  python qr_roundtrip_driver.py <repo root>  > qr-roundtrip.json"""
import io
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
sys.path.insert(0, str(root/'scripts/signing'))
import keytool  # noqa: E402
import qr  # noqa: E402
import totp  # noqa: E402
import usign_format  # noqa: E402
from PIL import Image  # noqa: E402
import zxingcpp  # noqa: E402


def decode(text):
    matrix = qr.encode(text, ecc='Q')
    image = Image.open(io.BytesIO(qr.render_png(matrix, scale=6, border=4)))
    found = zxingcpp.read_barcodes(image)
    return (found[0].text if found else None), len(matrix)


rows = {'secret_round_trips': 0, 'secret_failures': 0, 'totp_round_trips': 0, 'totp_failures': 0, 'sizes': set()}
for index in range(60):
    name = ('main', 'reserve')[index % 2]
    key = usign_format.SecretKey.generate()
    text, size = decode(keytool.secret_payload(name, key))
    rows['sizes'].add(size)
    named, again = keytool.parse_payload(text or '')
    # Same key id and public key, and a signature made with the imported secret verifies under the original key.
    ok = (named == name and again.public == key.public and again.key_id == key.key_id
          and usign_format.verify(key.public, b'm', usign_format.sign(again.seed, b'm')))
    rows['secret_round_trips' if ok else 'secret_failures'] += 1
for index in range(20):
    seed = totp.new_seed()
    text, size = decode(totp.otpauth_uri(seed))
    scanned = text.split('secret=')[1].split('&')[0] if text else ''
    ok = totp.totp(totp.seed_bytes(scanned), 1_800_000_000) == totp.totp(totp.seed_bytes(seed), 1_800_000_000)
    rows['totp_round_trips' if ok else 'totp_failures'] += 1
rows['sizes'] = sorted(rows['sizes'])
rows.update(decoder='zxing-cpp 3.1.1 (pinned in the run command)', python=sys.version.split()[0],
            scope='dummy keys only; QR ECC level Q; render_png scale 6, quiet zone 4')
print(json.dumps(rows, indent=2, sort_keys=True))
