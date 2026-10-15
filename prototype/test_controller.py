import copy
import io
import subprocess
import sys
import unittest
from unittest.mock import patch
from pathlib import Path
from controller import Controller, Policy
from replay import main, unique_object


def sample(t, active="primary", primary=True, backup=True, wan="up"):
    def health(ok):
        return {"interface_up": True, "route_verified": True, "dns_ok": True,
                "https": {"target_a": ok, "target_b": ok, "target_c": ok}}
    return {"time": t, "active": active, "operator_revision": 0, "wan": wan,
            "manual_override": False, "primary": health(primary), "backup": health(backup)}


class FailoverTests(unittest.TestCase):
    def feed(self, controller, samples):
        return [controller.step(s) for s in samples]

    def test_connected_blackhole_switches_after_three_failures(self):
        results = self.feed(Controller(), [sample(t, primary=False) for t in (0, 5, 10)])
        self.assertEqual([r["proposal"] for r in results[:2]], [None, None])
        self.assertEqual(results[-1]["proposal"]["target"], "backup")
        self.assertFalse(results[-1]["proposal"]["applied"])
        self.assertEqual(results[-1]["active"], "primary")

    def test_one_failed_endpoint_does_not_switch(self):
        c = Controller()
        for t in range(0, 30, 5):
            s = sample(t); s["primary"]["https"]["target_a"] = False
            self.assertEqual(c.step(s)["state"], "PRIMARY_OK")

    def test_dns_failure_has_own_reason(self):
        c = Controller()
        for t in (0, 5, 10):
            s = sample(t); s["primary"]["dns_ok"] = False
            r = c.step(s)
        self.assertEqual(r["proposal"]["reason"], "DNS_DEGRADED")

    def test_unverified_active_path_is_not_outage(self):
        c = Controller()
        for t in (0, 5, 10, 15):
            s = sample(t, primary=False); s["primary"]["route_verified"] = False
            r = c.step(s)
            self.assertIsNone(r["proposal"])
            self.assertEqual(r["state"], "UNVERIFIED_ROUTE")

    def test_unverified_backup_never_selected(self):
        c = Controller()
        for t in (0, 5, 10):
            s = sample(t, primary=False); s["backup"]["route_verified"] = False
            self.assertIsNone(c.step(s)["proposal"])

    def test_wan_down_does_not_switch(self):
        c = Controller()
        for t in (0, 5, 10, 15):
            r = c.step(sample(t, wan="down"))
            self.assertEqual(r["state"], "WAN_DOWN")
            self.assertIsNone(r["proposal"])

    def test_wan_unknown_does_not_switch(self):
        self.assertEqual(Controller().step(sample(0, wan="unknown"))["state"], "WAN_UNKNOWN")

    def test_both_down_no_wan_bypass(self):
        results = self.feed(Controller(), [sample(t, primary=False, backup=False) for t in (0, 5, 10)])
        self.assertEqual(results[-1]["state"], "ALL_VPN_DOWN")
        self.assertTrue(all(r["proposal"] is None for r in results))

    def test_backup_requires_consecutive_successes(self):
        c = Controller()
        self.feed(c, [sample(0, primary=False, backup=False), sample(5, primary=False, backup=False)])
        self.assertIsNone(c.step(sample(10, primary=False))["proposal"])
        self.assertEqual(c.step(sample(15, primary=False))["proposal"]["target"], "backup")

    def test_recovery_requires_hold_and_stability(self):
        c = Controller()
        for t in range(0, 300, 5):
            self.assertIsNone(c.step(sample(t, active="backup"))["proposal"])
        self.assertEqual(c.step(sample(300, active="backup"))["proposal"]["reason"], "PRIMARY_RECOVERED")

    def test_intermittent_recovery_resets_timer(self):
        c = Controller()
        for t in range(0, 420, 5):
            s = sample(t, active="backup", primary=t != 295)
            self.assertIsNone(c.step(s)["proposal"])
        self.assertEqual(c.step(sample(420, active="backup"))["proposal"]["target"], "primary")

    def test_manual_return_mode_stays_on_backup(self):
        c = Controller(Policy(auto_return=False))
        for t in range(0, 500, 5):
            self.assertIsNone(c.step(sample(t, active="backup"))["proposal"])

    def test_failed_backup_emergency_return_does_not_wait_hold(self):
        c = Controller()
        results = self.feed(c, [sample(t, active="backup", backup=False) for t in (0, 5, 10)])
        self.assertEqual(results[-1]["proposal"]["target"], "primary")

    def test_stale_gap_resets_evidence(self):
        c = Controller()
        self.feed(c, [sample(0, primary=False), sample(5, primary=False)])
        self.assertIsNone(c.step(sample(100, primary=False))["proposal"])
        self.assertIsNone(c.step(sample(105, primary=False))["proposal"])
        self.assertIsNotNone(c.step(sample(110, primary=False))["proposal"])

    def test_clock_rollback_and_duplicate_rejected(self):
        c = Controller(); c.step(sample(10))
        for t in (9, 10):
            with self.assertRaises(ValueError): c.step(sample(t))

    def test_samples_cannot_accelerate_failure_threshold(self):
        c = Controller(); c.step(sample(0, primary=False))
        with self.assertRaises(ValueError): c.step(sample(0.1, primary=False))

    def test_unannounced_active_change_pauses_observer(self):
        c = Controller(); c.step(sample(0))
        self.assertEqual(c.step(sample(5, active="backup"))["state"], "MANUAL_OVERRIDE")

    def test_operator_change_pauses_until_explicit_restart(self):
        c = Controller(); c.step(sample(0))
        s = sample(5, primary=False); s["operator_revision"] = 1
        self.assertEqual(c.step(s)["state"], "MANUAL_OVERRIDE")
        s["time"] = 10
        self.assertIsNone(c.step(s)["proposal"])

    def test_manual_override_is_latched(self):
        c = Controller(); s = sample(0); s["manual_override"] = True
        c.step(s)
        self.assertEqual(c.step(sample(5))["state"], "MANUAL_OVERRIDE")

    def test_proposal_rate_limited_without_assuming_application(self):
        c = Controller()
        self.feed(c, [sample(0, primary=False), sample(5, primary=False)])
        self.assertIsNotNone(c.step(sample(10, primary=False))["proposal"])
        for t in (15, 20, 25, 30, 35):
            r = c.step(sample(t, primary=False))
            self.assertEqual(r["active"], "primary")
            self.assertIsNone(r["proposal"])
        self.assertIsNotNone(c.step(sample(40, primary=False))["proposal"])

    def test_restarts_reconcile_actual_backup_and_restart_hold(self):
        c = Controller()
        self.assertEqual(c.step(sample(1000, active="backup"))["active"], "backup")
        for t in range(1005, 1300, 5):
            self.assertIsNone(c.step(sample(t, active="backup"))["proposal"])

    def test_no_active_selects_only_ready_vpn(self):
        c = Controller()
        self.assertIsNone(c.step(sample(0, active="none"))["proposal"])
        self.assertEqual(c.step(sample(5, active="none"))["proposal"]["target"], "primary")

    def test_wan_outage_resets_recovery(self):
        c = Controller()
        for t in range(0, 300, 5): c.step(sample(t, active="backup"))
        c.step(sample(300, active="backup", wan="down"))
        self.assertIsNone(c.step(sample(305, active="backup"))["proposal"])

    def test_input_is_not_modified(self):
        s = sample(0); before = copy.deepcopy(s)
        Controller().step(s)
        self.assertEqual(s, before)

    def test_invalid_evidence_rejected(self):
        variants = []
        s = sample(0); s["primary"]["dns_ok"] = "true"; variants.append(s)
        s = sample(0); s["time"] = float("nan"); variants.append(s)
        s = sample(0); s["backup"]["https"] = {"a": True}; variants.append(s)
        s = sample(0); s["password"] = "not-a-real-secret"; variants.append(s)
        for s in variants:
            with self.assertRaises(ValueError): Controller().step(s)

    def test_invalid_policy_rejected(self):
        for kwargs in ({"failures": 0}, {"ready_rounds": True}, {"cooldown_seconds": -1}, {"max_gap_seconds": float("inf")}):
            with self.assertRaises(ValueError): Policy(**kwargs)

    def test_cli_rejects_extra_fields_without_echoing_them(self):
        path = Path(__file__).parent / "fixtures" / "invalid_extra.jsonl"
        r = subprocess.run([sys.executable, str(Path(__file__).with_name("replay.py")), str(path)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 2)
        self.assertNotIn("SENTINEL_DO_NOT_LOG", r.stdout + r.stderr)

    def test_duplicate_json_fields_rejected(self):
        with self.assertRaises(ValueError):
            unique_object([("time", 0), ("time", 5)])

    def test_oversize_stream_stops_without_logging_content(self):
        with patch.object(sys, "argv", ["replay.py", "fixture.jsonl"]), \
             patch.object(Path, "open", return_value=io.StringIO("x" * 16385)), \
             patch("sys.stderr", new_callable=io.StringIO) as stderr:
            with self.assertRaises(SystemExit) as error: main()
            self.assertEqual(error.exception.code, 2)
            self.assertNotIn("xxxxx", stderr.getvalue())

    def test_cli_valid_trace_is_observe_only(self):
        path = Path(__file__).parent / "fixtures" / "blackhole.jsonl"
        r = subprocess.run([sys.executable, str(Path(__file__).with_name("replay.py")), str(path)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout.count('"mode": "observe_only"'), 3)
        self.assertIn('"applied": false', r.stdout)


if __name__ == "__main__":
    unittest.main()
