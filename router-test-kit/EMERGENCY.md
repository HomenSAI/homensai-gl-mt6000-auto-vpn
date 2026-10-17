# Emergency: LAN clients have no internet after the application ran

Use another internet path (phone/second router) to reach this page. Router management (SSH/LuCI over LAN) is not blocked
by the application's guard: it only drops **forwarded** traffic from `br-lan`.

0. **First try the button.** Since alpha5, if the router is held on the reserve (state "still on the reserve"), open the Overview and press **Return to primary**. The router checks the primary first and reports the result there. If you changed the VPN rules yourself, Auto now releases its own block automatically; check the rule order in GL.iNet.
1. `ssh root@ROUTER "sh /tmp/05-emergency.sh show"` (copy the kit scripts again if /tmp was cleared by a reboot).
   Look at: owned guard table present? native phase? current VPN rule order vs the journal `before` list.
2. `sh /tmp/05-emergency.sh stop-auto` (and later `sh /tmp/05-emergency.sh start` to start the monitor again) : stops the application's services and sets `native_enabled=0`. No network changes.
3. If the current rule order equals `before` in the journal (or you only ran the monitor, which never reorders),
   run `sh /tmp/05-emergency.sh remove-guard` and test a LAN client.
4. If the order equals `after` (a switch is still applied and you want the original route):
   the original order is the journal `before` list. Restore it through the GL.iNet VPN dashboard (router UI -> VPN ->
   VPN Dashboard / policy order) or, if you know the section names, `uci reorder route_policy.<section>=<index>`
   for each, `uci commit route_policy`, then `/usr/bin/rtp2.sh not_reload_network`. This is what the controller does itself;
   do it by hand only if you understand the sections. Then `remove-guard`.
5. Last resort: restore `/etc/config/route_policy` (and only the files you need) from your private backup, reboot the router.
   The guard is a runtime nft table; a reboot clears it, but the supervisor will recreate it if a journal is still active
   (so do step 2 first).

Never: factory reset, flash firmware, delete the VPN profiles, or disable the vendor Kill Switch to "fix" connectivity.
Report: the output of `show` (it contains no keys) and what you did.
