"""Offline exact-hash candidate builder. Never connects to or patches a router."""
import argparse
import hashlib
import json
from pathlib import Path

ORIGINAL_SHA256='a02a43b46c6722b012745fd5f960f35414b34e011379181cc5c52d98135926ce'
BASE=Path(__file__).resolve().parent


def candidate(original,guard=None):
    if hashlib.sha256(original).hexdigest()!=ORIGINAL_SHA256:raise ValueError('HELPER-ORIGINAL-HASH')
    guard=guard if guard is not None else (BASE/'fw3-helper-context.lua').read_bytes()
    if b'\r' in guard:raise ValueError('GUARD-LINE-ENDINGS')
    anchors=(b'local function refresh()\n',b'local cmd = arg[1]\n',
             b'    os.execute("/etc/init.d/firewall reload >/dev/null 2>&1")\n')
    if any(original.count(anchor)!=1 for anchor in anchors):raise ValueError('HELPER-ANCHOR-COUNT')
    value=original.replace(anchors[0],guard+b'\n'+anchors[0],1)
    value=value.replace(anchors[1],anchors[1]+b'''
-- Context is established before up/down declaration commits or refresh writes.
if cmd == "up" or cmd == "down" or cmd == "refresh" then
    if firewall_is_fw4() then
        io.stderr:write("GL-BWA-UNSUPPORTED-FIREWALL\\n")
        os.exit(1)
    end
    local context_ok, context = pcall(hbwa_context)
    hbwa_reload_context = context_ok and context or nil
    if not hbwa_reload_context then
        io.stderr:write("GL-BWA-CONTEXT-UNVERIFIED\\n")
        os.exit(1)
    end
    local snapshot_ok, snapshot = pcall(hbwa_snapshot, c)
    if not snapshot_ok then
        io.stderr:write("GL-BWA-SNAPSHOT-UNVERIFIED\\n")
        os.exit(1)
    end
    hbwa_firewall_before = snapshot
end
''',1)
    return value.replace(anchors[2],b'''    if hbwa_reload_context == "direct" then
        os.execute("/etc/init.d/firewall reload >/dev/null 2>&1")
    else
        local snapshot_ok, snapshot = pcall(hbwa_snapshot, c)
        if not snapshot_ok then
            io.stderr:write("GL-BWA-SNAPSHOT-UNVERIFIED\\n")
            os.exit(1)
        end
        if snapshot ~= hbwa_firewall_before then
            -- Stock procd coalesces this package event; its worker does not
            -- inherit this include's firewall lock. No private worker is added.
            local queued = os.execute("ubus -t 3 call service event '{\\\"type\\\":\\\"config.change\\\",\\\"data\\\":{\\\"package\\\":\\\"firewall\\\"}}' >/dev/null 2>&1")
            if queued ~= 0 then
                io.stderr:write("GL-BWA-RELOAD-NOT-QUEUED\\n")
                os.exit(1)
            end
        end
    end
''',1)


def main():
    raise SystemExit('NOT APPROVED: no hardware acceptance; conditional includeRunsOnReload=true counterexample; generator remains blocked')
    # Retained unreachable historical builder below for review/provenance.
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('original',type=Path)
    parser.add_argument('output',type=Path)
    args=parser.parse_args()
    root=BASE.parents[1];private=(root/'private').resolve();output=args.output.resolve()
    if not output.is_relative_to(private):parser.error('Output must be a fresh directory under private/')
    if output.exists():parser.error('Output already exists; no overwrite')
    raw=args.original.read_bytes()
    # A Windows transport copy is normalized explicitly, never on the device.
    original=raw.replace(b'\r\n',b'\n')
    patched=candidate(original)
    output.mkdir(parents=True)
    (output/'helper-original.lua').write_bytes(original)
    (output/'helper-candidate.lua').write_bytes(patched)
    transaction=(BASE/'apply-helper-candidate.py.in').read_text(encoding='utf8').replace(
        '@@ORIGINAL_SHA256@@',ORIGINAL_SHA256).replace('@@PATCHED_SHA256@@',hashlib.sha256(patched).hexdigest())
    (output/'apply-helper-candidate.py').write_text(transaction,encoding='utf8')
    receipt=dict(schema=1,operation='OFFLINE-CANDIDATE-ONLY',device_path='/usr/bin/gl_block_wan_access_exit',
        transport_sha256=hashlib.sha256(raw).hexdigest(),original_sha256=ORIGINAL_SHA256,
        candidate_sha256=hashlib.sha256(patched).hexdigest(),original_bytes=len(original),candidate_bytes=len(patched),
        transport_normalization='CRLF to LF before exact original hash check',
        guard_sha256=hashlib.sha256((BASE/'fw3-helper-context.lua').read_bytes()).hexdigest(),
        rollback=dict(required_current_sha256=hashlib.sha256(patched).hexdigest(),restored_sha256=ORIGINAL_SHA256,
                      bytes_restored_from='helper-original.lua',tested_on_device=False),
        scope='Same rule generation/commits. Nested changed semantics use stock procd package event; idempotent nested calls emit nothing. ACK is not completion proof.')
    (output/'candidate-receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf8')
    print(json.dumps(receipt,indent=2))


if __name__=='__main__':main()
