# Overview route colours - alpha9

The Primary/Reserve diagram shows the controller-selected traffic path for this failover plan. It does not claim only one VPN process is connected or that destination-specific router policies cannot use other tunnels.

| State | Colour | Meaning |
| --- | --- | --- |
| Selected + fresh healthy probes | Green | Active confirmed plan path |
| Healthy but not selected | Neutral grey | Ready for switching; no traffic selection claimed |
| Transition destination | Yellow | Applying/checking; not active until controller confirmation |
| Confirmed probe failure | Red | Connectivity failed, whether selected or not |
| Inactive, stale, unknown or Auto off | Neutral grey | No current active-path confirmation; explicit text distinguishes the cases |

After COMMITTED, the reserve alone can be green. After OBSERVING with fresh certification, the primary alone can be green. During RESTORING, the primary destination is yellow; the reserve is not green merely because its probe succeeds. A failed active reserve does not magically select the healthy primary. The controller must confirm the change.

Test: 200 combinations across eight controller states and five health conditions per side; at most one green path and every green path is the selected side. Existing Auto/acknowledgement/clock/freshness/return tests retained. Synthetic browser preview is not real device evidence. No routing or VPN changes in this UI correction.
