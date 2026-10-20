# Firmware-owned server failover and application channel coordination

Owner decision, 20 October 2026: observe how the router changes servers within a VPN tunnel; the application diagnoses those changes and coordinates the choice between distinct VPN tunnels, including OpenVPN and WireGuard. This supersedes the earlier proposal to implement a second independent server-selection loop.

The official [GL.iNet VPN Dashboard guide](https://docs.gl-inet.com/router/en/4/interface_guide/vpn_dashboard/) for firmware 4.9 and later describes ordered server profiles within a tunnel and independent routing groups. It does not establish the configuration or compatibility of an unconnected device. Firmware-specific arbitration and independent LAN acceptance remain prerequisites for live application switching.

## Identities and ownership

The application distinguishes three concepts:

| Concept | Meaning | Can authorize channel membership? |
| --- | --- | --- |
| User channel label | Editable application metadata for display and priorities | No |
| Provider profile group | A provider's stored collection of profiles | No |
| Observed vendor tunnel | A protocol and logical network interface with an exact, unambiguous configured profile binding | Only as observed configuration identity; not proof of a live endpoint or routing success |

The authoritative observed identifier is `protocol:logical-interface`. Matching names, country names, provider groups and protocol alone never establish that two profiles share a tunnel. Unbound profiles have unknown tunnel membership. A duplicate or contradictory binding is unknown rather than a last-entry-wins selection.

Saving the primary/reserve preferences derives stable tunnel anchors from the trusted current inventory. The anchors are not editable RPC arguments. They permit read-only planning to find the currently configured member after the firmware selects another profile. Existing configurations without anchors can use only an unambiguous current binding; the application does not guess lost membership after restart.

## Observation and evidence

The monitor compares configured bindings before and after measurements. A changed, ambiguous or rebound identity invalidates that measurement's success and exit evidence. Samples are associated with the observed tunnel generation and profile ID. A previous server's successful samples cannot make its replacement ready.

An identity is pending until repeated consistent observations. A stable identity means only that the configured binding was observed consistently. It does not mean that the vendor completed its retry queue, that the tunnel carries LAN traffic, or that the application caused the change. Firmware retry exhaustion and the cause of an observed change remain unknown without separate evidence. Events are bounded and distinct from application-controlled transition counters.

## Decisions and boundaries

Within one observed tunnel, server selection belongs to the firmware. Application candidate selection considers distinct tunnels with current, fresh DNS/HTTPS evidence and operator priorities. Display-label changes do not change ownership or transition classification. A configured WAN link failure suppresses VPN reserve cycling; missing evidence remains unknown. Candidate readiness is a read-only recommendation and never an authorization to apply routes.

The live controller retains its verified-adapter, worker-coordination, policy-generation, bounded-trial, LAN-witness, Kill Switch, IPv6, protected-rule and rollback checks. Binding changes invalidate relevant evidence/certification. Emergency Stop and recovery remain available while identity or planning is unknown. This work does not enable inactive-profile startup, arbitrary multi-hop, direct WAN fallback or an uncertified GL-MT3000 adapter.

The independent alpha12 endurance run keeps its original installed package and manifest. New code is validated with isolated fixtures and committed-source CI; it must not be installed into that running baseline merely to collect a new-version result.
