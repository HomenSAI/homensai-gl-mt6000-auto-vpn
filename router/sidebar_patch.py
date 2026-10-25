"""Replaces the old one-line sidebar state with the always-visible Auto/monitor/version block."""
import re
from pathlib import Path


def apply(source):
    inc = (Path(__file__).parent / 'sidebar_status.inc.js').read_text(encoding='utf8')
    assert source.count('return view.extend({') >= 1
    source = source.replace('return view.extend({', inc + '\nreturn view.extend({', 1)
    prompt = (Path(__file__).parent / 'ai_prompt.inc.js').read_text(encoding='utf8')
    source = source.replace('return view.extend({', prompt + '\nreturn view.extend({', 1)
    chart_inc = (Path(__file__).parent / 'latency_chart.inc.js').read_text(encoding='utf8')
    source = source.replace('return view.extend({', chart_inc + '\nreturn view.extend({', 1)
    for name in ('speed_live.inc.js', 'speed_table.inc.js', 'traffic_chart.inc.js'):
        extra = (Path(__file__).parent / name).read_text(encoding='utf8')
        source = source.replace('return view.extend({', extra + '\nreturn view.extend({', 1)
    live = (Path(__file__).parent / 'live_log.inc.js').read_text(encoding='utf8')
    source = source.replace('return view.extend({', live + '\nreturn view.extend({', 1)
    source, n4 = re.subn(r"var terminal=E\('pre',\{\},\[.*?put\('services',terminal\);", "put('services',renderLiveLog(status,rows,ns,inventory,stateNames));", source, count=1, flags=re.S)
    assert n4 == 1, 'live log terminal'
    links = (Path(__file__).parent / 'error_links.inc.js').read_text(encoding='utf8')
    source = source.replace('return view.extend({', links + '\nreturn view.extend({', 1)
    source = source.replace("sortableTables();showPage(activeTab);", "installErrorLinks(appRoot);sortableTables();showPage(activeTab);", 1)
    assert source.count("initSidebarLayout(appRoot);") == 1, "sidebar init"
    source = source.replace("initSidebarLayout(appRoot);", "initSidebarLayout(appRoot);installErrorLinks(appRoot);", 1)
    # The monitor block sits to the right of "Check the VPNs now" in the header.
    check = "renderConnectivityCheck(data[1],function(){return statusCall().then(draw);})"
    assert source.count(check) == 1, 'connectivity control'
    source = source.replace(check, "E('div',{'class':'hv-tools-row'},[" + check + ",renderMonitorBlock(data[1],inventory)])", 1)
    # The old "Service monitor" menu entry is the live log; say so.
    source, n3 = re.subn(r"bi\('Service monitor','[^']*'\)", "bi('Live log','\u0416\u0438\u0432\u043e\u0439 \u0436\u0443\u0440\u043d\u0430\u043b')", source)
    assert n3 >= 1, 'service monitor label'
    # Every update of the old one-line text becomes a full redraw of the block.
    source, n1 = re.subn(r"if\(sideState\)sideState\.textContent=[^;]*;", "if(sideState)fillSideStatus(sideState,status,inventory);if(monitorBlockHost)fillMonitorBlock(monitorBlockHost,status,inventory);", source)
    assert n1 >= 1, 'sideState update'
    source, n2 = re.subn(r"sideState=E\('p',\{'class':'hv-side-state'\},[^;]*\);",
                         "sideState=E('div',{'class':'hv-side-status'});fillSideStatus(sideState,data[1],inventory);", source)
    assert n2 == 1, 'sideState creation'
    return source
