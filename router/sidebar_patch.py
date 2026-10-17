"""Replaces the old one-line sidebar state with the always-visible Auto/monitor/version block."""
import re
from pathlib import Path


def apply(source):
    inc = (Path(__file__).parent / 'sidebar_status.inc.js').read_text(encoding='utf8')
    assert source.count('return view.extend({') >= 1
    source = source.replace('return view.extend({', inc + '\nreturn view.extend({', 1)
    prompt = (Path(__file__).parent / 'ai_prompt.inc.js').read_text(encoding='utf8')
    source = source.replace('return view.extend({', prompt + '\nreturn view.extend({', 1)
    # Every update of the old one-line text becomes a full redraw of the block.
    source, n1 = re.subn(r"if\(sideState\)sideState\.textContent=[^;]*;", "if(sideState)fillSideStatus(sideState,status,inventory);", source)
    assert n1 >= 1, 'sideState update'
    source, n2 = re.subn(r"sideState=E\('p',\{'class':'hv-side-state'\},[^;]*\);",
                         "sideState=E('div',{'class':'hv-side-status'});fillSideStatus(sideState,data[1],inventory);", source)
    assert n2 == 1, 'sideState creation'
    return source
