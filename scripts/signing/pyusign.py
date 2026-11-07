"""A usign-compatible command line (the subset 02-install.sh and homensai-vpn-trust-key use) for offline tests and PCs
without OpenWrt tools:  -V [-q] -m <file> [-x <sig>] -p <pubkey> | -P <dir>,  -F -p|-s|-x <file>,
-S -m <file> -s <seckey> [-x <sig>],  -G -p <pubkey> -s <seckey> [-c <comment>].
Exit codes and messages follow usign 2020 (the OpenWrt 21.02 router build); interoperability with the real binary is
proven in docs/architecture/SIGNING-2026-11-03.ru.md."""
import getopt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import usign_format  # noqa: E402


def main(argv):
    try:
        options, rest = getopt.getopt(argv, 'VSFGqm:x:p:P:s:c:')
    except getopt.GetoptError as error:
        print(error, file=sys.stderr)
        return 1
    opts = {}
    for name, value in options:
        opts[name] = value
    quiet = '-q' in opts
    try:
        if '-V' in opts:
            message = Path(opts['-m']).read_bytes()
            signature = Path(opts.get('-x', opts['-m']+'.sig')).read_bytes()
            key_id = usign_format.signature_key_id(signature).hex()
            if '-P' in opts:
                path = Path(opts['-P'])/key_id
            else:
                path = Path(opts['-p'])
            try:
                key = usign_format.PublicKey.from_file(path.read_bytes())
            except OSError:
                print("Cannot open file '%s' for reading" % path, file=sys.stderr)
                return 1
            try:
                usign_format.verify_file({key.key_id.hex(): key}, message, signature)
            except ValueError:
                if not quiet:
                    print('verification failed', file=sys.stderr)
                return 1
            if not quiet:
                print('OK', file=sys.stderr)
            return 0
        if '-F' in opts:
            if '-p' in opts:
                key_id = usign_format.PublicKey.from_file(Path(opts['-p']).read_bytes()).key_id
            elif '-s' in opts:
                key_id = usign_format.SecretKey.from_file(Path(opts['-s']).read_bytes()).key_id
            else:
                key_id = usign_format.signature_key_id(Path(opts['-x']).read_bytes())
            print(key_id.hex())
            return 0
        if '-S' in opts:
            secret = usign_format.SecretKey.from_file(Path(opts['-s']).read_bytes())
            Path(opts.get('-x', opts['-m']+'.sig')).write_bytes(secret.sign_file(Path(opts['-m']).read_bytes()))
            return 0
        if '-G' in opts:
            secret = usign_format.SecretKey.generate()
            comment = opts.get('-c', 'usign key')
            Path(opts['-s']).write_bytes(secret.to_file(comment))
            Path(opts['-p']).write_bytes(secret.public_file(comment))
            return 0
    except (OSError, ValueError, KeyError) as error:
        print('usign: %s' % error, file=sys.stderr)
        return 1
    print('usage: usign -V|-S|-F|-G ...', file=sys.stderr)
    return 1


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
