"""The rule of the vendor locks (owner 05.11.2026, docs/ROADMAP.md): deleting a vendor lock is allowed only when its holder is
provably dead and only during recovery; everywhere else locks are never deleted. A source check: a new deletion anywhere fails
here and must be argued against the rule, not added quietly."""
import re
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
LIB=ROOT/'router/files/usr/lib/homensai-vpn'
# a deletion call with a vendor lock in its argument, a shell rm of one, or the constant of the vendor lock
LOCK=r"(?:VENDOR_LOCK|RTP_LOCK|rtp2\.lock|tunnel-switch|fw3\.lock)"
DELETION=re.compile(r"(?:unlink|remove|rmtree)\([^)\n]*"+LOCK+r"|"+LOCK+r"[^\n]*\.(?:unlink|remove)\(|\brm\b[^\n]*"+LOCK)
ALLOWED={'rollback_recovery.py':'Path(VENDOR_LOCK).unlink()','lua/recovery.lua':'sys.remove(M.VENDOR_LOCK)'}


class Rule(unittest.TestCase):
    def test_a_vendor_lock_is_deleted_only_in_recovery(self):
        found={}
        for path in sorted(LIB.rglob('*')):
            if path.is_file() and path.suffix in ('.py','.lua','.sh','') and '__pycache__' not in path.parts:
                for line in path.read_text(encoding='utf-8',errors='replace').splitlines():
                    if DELETION.search(line) and not line.lstrip().startswith(('#','--')):
                        found.setdefault(path.relative_to(LIB).as_posix(),[]).append(line.strip())
        self.assertEqual(sorted(found),sorted(ALLOWED))
        for name,call in ALLOWED.items():
            self.assertEqual(len(found[name]),1,name);self.assertIn(call,found[name][0])

    def test_both_deletions_stand_behind_the_proof_of_a_dead_holder(self):
        python=(LIB/'rollback_recovery.py').read_text(encoding='utf-8')
        self.assertIn("if not same:refuse('VENDOR-WORKER-BUSY')\n                try:Path(VENDOR_LOCK).unlink()",python)
        lua=(LIB/'lua/recovery.lua').read_text(encoding='utf-8').replace('\r\n','\n')
        self.assertRegex(lua,r"if not ok or pid~=lock then deny\('VENDOR-WORKER-BUSY'\) end\n(?: *--[^\n]*\n)* *sys\.remove\(M\.VENDOR_LOCK\)")

    def test_the_rule_is_written_down(self):
        roadmap=(ROOT/'docs/ROADMAP.md').read_text(encoding='utf-8')
        self.assertIn('only when its holder is provably dead and only during recovery',roadmap)
        for name in ALLOWED:
            self.assertIn('The rule (owner 05.11.2026, docs/ROADMAP.md)',(LIB/name).read_text(encoding='utf-8'))


if __name__=='__main__':
    unittest.main()
