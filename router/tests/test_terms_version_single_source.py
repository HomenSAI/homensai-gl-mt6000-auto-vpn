"""License transition (terms version 2): every Auto gate compares the accepted terms with agent.TERMS_VERSION.
1.0.0-beta14 and 2.0.0-alpha13 drafts still compared pair_auto/mt3000 (and the Lua pair/backend) with a literal '1',
so after the owner accepted version 2 the pair Auto would have refused PAIR-MODE-NOT-CONFIGURED forever."""
from pathlib import Path
import re,sys,unittest
LIB=Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'
sys.path.insert(0,str(LIB))


class TermsVersionSingleSource(unittest.TestCase):
    def test_no_literal_terms_version_comparison(self):
        offenders=[]
        for path in sorted(list(LIB.glob('*.py'))+list(LIB.glob('lua/*.lua'))):
            text=path.read_text(encoding='utf-8')
            for match in re.finditer(r"terms_version['\"]?\)?\s*(?:!=|==|~=)\s*['\"][0-9]+['\"]",text):
                offenders.append(path.name+': '+match.group(0))
        self.assertEqual(offenders,[])

    def test_lua_terms_module_equals_agent(self):
        import agent
        terms=LIB/'lua/terms.lua'
        if not terms.exists():self.skipTest('no Lua Auto in this line')
        self.assertEqual(re.search(r"^return '([0-9]+)'",terms.read_text(encoding='utf-8'),re.M).group(1),agent.TERMS_VERSION)


if __name__=='__main__':
    unittest.main()
