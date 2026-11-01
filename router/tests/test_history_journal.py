"""Switch-history journal (schema 2, docs/architecture/HISTORY-JOURNAL-2026-11-01.ru.md), Python side.

The state file holds everything the page needs; the archive holds one verified line per event. These tests record the
same generated events with the journal writer and with the frozen schema-1 writer (native_history_v1_reference.py,
alpha20) and check: the page projection and load() are the schema-1 ones; power cuts at every step (torn line, archive
behind by one or by more than the tail, an old state with a newer archive, a failed append or state write, a migration
interrupted after each step) end in a consistent history; compaction and the detail budget keep the archive bounded.
The Lua writer is compared with this one byte for byte in test_lua_history.JournalDifferential.
"""
import copy
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent/'files/usr/lib/homensai-vpn'))
sys.path.insert(0, str(HERE))
os.environ['TZ'] = 'CET-1CEST,M3.5.0,M10.5.0/3'
import time  # noqa: E402
time.tzset()

import native_history as nh  # noqa: E402
import native_history_v1_reference as v1  # noqa: E402
from history_journal_cases import events  # noqa: E402

WALL = 1761900000.25
START = 1761800000.5


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'))


def fresh(values):
    """Only the values that become events (the generator also repeats publications, which are deduplicated)."""
    with tempfile.TemporaryDirectory() as folder:
        history = nh.History(folder, detail_days=7)
        return [(value, now) for value, now in values if history.record(copy.deepcopy(value), now)]


class Journal(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)
        self.addCleanup(nh._WRITER_CACHE.clear)
        patcher = patch('time.time', return_value=WALL)
        patcher.start()
        self.addCleanup(patcher.stop)

    def record(self, folder, values, writer=nh, days=7, **kwargs):
        history = writer.History(folder, detail_days=days, **kwargs)
        return [history.record(copy.deepcopy(value), now) for value, now in values]

    def state(self, folder):
        return json.loads((folder/'native-history.json').read_text())['data']

    def archive(self, folder):
        return (folder/nh.ARCHIVE).read_bytes()

    def assert_consistent(self, folder):
        """The archive is exactly what the state says: sizes, one verified line per retained event, in order."""
        state = self.state(folder)
        raw = self.archive(folder)
        entries = nh.archive_entries(raw)
        self.assertEqual(len(raw), state['archive_bytes'])
        self.assertEqual(len(entries), state['archive_lines'])
        self.assertEqual(sum(len(line) for _, line in entries), len(raw), 'every line verifies')
        sequences = [sequence for sequence, _ in entries]
        self.assertEqual(len(sequences), len(set(sequences)), 'no sequence twice')
        retained = [row[0] for row in state['index']]
        self.assertTrue(set(retained) <= set(sequences), 'every retained event is in the archive')
        self.assertEqual([row['sequence'] for row in state['tail']], retained[-len(state['tail']):] if state['tail'] else [])
        for row in state['index']:
            line = dict(entries)[row[0]]
            self.assertEqual(len(line), row[3])
        return state

    # ---------------------------------------------------------------- the page and load() equal schema 1
    def test_projection_and_load_equal_the_schema_1_writer(self):
        values = events(3, 700, START, spacing=465.0)
        self.record(self.root/'v2', values)
        self.record(self.root/'v1', values, writer=v1)
        now = values[-1][1]
        # (a page clock behind the newest events is the one case where the tail can show fewer rows: not compared)
        for days, at in ((7, now + 5.0), (7, now + 2*86400), (3, now + 60.0), (1, now + 6*86400)):
            with self.subTest(days=days, at=at):
                self.assertEqual(encoded(nh.History(self.root/'v2', detail_days=days).public(now=at)),
                                 encoded(v1.History(self.root/'v1', detail_days=days).public(now=at)))
        self.assertEqual(encoded(nh.History(self.root/'v2', detail_days=7).load()), encoded(v1.History(self.root/'v1', detail_days=7).load()))
        # read_public (the agent's cached reader) and the statistics export path (public(data=load()))
        with patch('retention_settings.configured_days', return_value=7):
            self.assertEqual(nh.read_public(self.root/'v2')['retained_events'], v1.read_public(self.root/'v1')['retained_events'])
        h = nh.History(self.root/'v2', detail_days=7)
        self.assertEqual(encoded(h.public(data=h.load(), now=now)), encoded(h.public(now=now)))
        state = self.assert_consistent(self.root/'v2')
        self.assertLess((self.root/'v2'/'native-history.json').stat().st_size, (self.root/'v1'/'native-history.json').stat().st_size/4)
        self.assertEqual(len(state['tail']), nh.TAIL)

    def test_state_round_trip_equals_the_schema_1_data(self):
        values = events(4, 250, START, spacing=300.0)
        self.record(self.root/'v1', values, writer=v1)
        data = v1.History(self.root/'v1', detail_days=7).load()
        state, lines = nh.state_of(json.loads(encoded(data)))
        self.assertNotIn('events', state)
        self.assertEqual(state['archive_bytes'], sum(map(len, lines)))
        folder = self.root/'v2'
        folder.mkdir()
        nh.atomic_bytes(folder/nh.ARCHIVE, b''.join(lines))
        nh.atomic_bytes(folder/'native-history.json', nh.state_bytes(state))
        self.assertEqual(encoded(nh.History(folder, detail_days=7).load()), encoded(data))

    # ---------------------------------------------------------------- migration
    def test_migration_keeps_v1_and_is_idempotent(self):
        values = fresh(events(5, 100, START, spacing=300.0))[:81]
        folder = self.root/'h'
        self.record(folder, values[:80], writer=v1)
        original = (folder/'native-history.json').read_bytes()
        before = v1.History(folder, detail_days=7).load()
        self.assertEqual(nh.History(folder, detail_days=7).load(), before, 'a reader converts in memory only')
        self.assertFalse((folder/nh.ARCHIVE).exists())
        self.record(folder, values[80:81])
        self.assertEqual((folder/nh.V1).read_bytes(), original, 'the schema-1 file is kept for analysis and downgrade')
        state = self.assert_consistent(folder)
        self.assertEqual(json.loads((folder/'native-history.backup.json').read_text())['schema'], 2)
        after = nh.History(folder, detail_days=7).load()
        self.assertEqual(after['events'][:-1], before['events'])
        self.assertEqual(state['sequence'], before['sequence'] + 1)

    def test_migration_interrupted_at_every_step_ends_like_an_uninterrupted_one(self):
        values = events(6, 70, START, spacing=300.0)
        seed = self.root/'seed'
        self.record(seed, values[:60], writer=v1)
        clean = self.root/'clean'
        shutil.copytree(seed, clean)
        self.record(clean, values[60:62])
        for after in range(1, 4):  # after the archive, after the v1 copy, after the backup state
            with self.subTest(after=after):
                work = self.root/('cut%d' % after)
                shutil.copytree(seed, work)
                calls = []
                real = nh.atomic_bytes

                def fail(target, raw):
                    if len(calls) == after:
                        raise OSError('power cut')
                    calls.append(target)
                    real(target, raw)
                with patch.object(nh, 'atomic_bytes', fail), self.assertRaises(OSError):
                    self.record(work, values[60:61])
                self.assertEqual(json.loads((work/'native-history.json').read_text())['schema'], 1, 'main is still schema 1')
                self.assertEqual(nh.History(work, detail_days=7).load(), v1.History(seed, detail_days=7).load())
                self.record(work, values[60:62])
                for name in ('native-history.json', 'native-history.backup.json', nh.ARCHIVE, nh.V1):
                    self.assertEqual((work/name).read_bytes(), (clean/name).read_bytes(), name)

    # ---------------------------------------------------------------- power cuts on a schema-2 history
    def seeded(self, count=40, tail=5):
        values = fresh(events(8, count + 6, START, spacing=300.0))
        folder = self.root/'seed'
        with patch.object(nh, 'TAIL', tail):
            self.record(folder, values[:count])
        return folder, values[count:]

    def lines(self, folder):
        return self.archive(folder).split(b'\n')[:-1]

    def test_torn_last_line_and_archive_behind_by_one(self):
        for label in ('torn', 'behind'):
            with self.subTest(case=label), patch.object(nh, 'TAIL', 5):
                folder, more = self.seeded()
                full = nh.History(folder, detail_days=7).load()
                if label == 'torn':
                    (folder/nh.ARCHIVE).write_bytes(self.archive(folder)[:-20])
                else:
                    (folder/nh.ARCHIVE).write_bytes(b''.join(row + b'\n' for row in self.lines(folder)[:-1]))
                self.assertEqual(nh.History(folder, detail_days=7).load(), full, 'the last event comes from the tail')
                self.record(folder, more[:1])
                state = self.assert_consistent(folder)
                self.assertNotIn('archive_gap', state)
                self.assertEqual(nh.History(folder, detail_days=7).load()['events'][:-1], full['events'])
                self.assertEqual(self.state(folder)['sequence'], full['sequence'] + 1)
                shutil.rmtree(folder)

    def test_archive_behind_by_more_than_the_tail_is_recorded_as_a_gap(self):
        with patch.object(nh, 'TAIL', 5):
            folder, more = self.seeded()
            full = nh.History(folder, detail_days=7).load()
            (folder/nh.ARCHIVE).write_bytes(b''.join(row + b'\n' for row in self.lines(folder)[:-8]))
            partial = nh.History(folder, detail_days=7).load()
            self.assertEqual(len(partial['events']), len(full['events']) - 3, '8 lines lost, the tail of 5 restores 5')
            self.record(folder, more[:1])
            state = self.assert_consistent(folder)
            self.assertEqual(state['archive_gap'], 3)
            self.assertEqual(state['totals'], nh.History(folder, detail_days=7).load()['totals'], 'counters are in the state')
            public = nh.History(folder, detail_days=7).public(now=more[0][1])
            self.assertIsNone(public['weekly'], 'weekly detail is incomplete')
            self.assertFalse(public['weekly_detail_complete'])
            self.assertEqual(public['retained_events'], len(full['events']) - 3 + 1)

    def test_old_state_with_a_newer_archive(self):
        """Impossible by the write order, but a restored backup state meets an archive one event ahead."""
        with patch.object(nh, 'TAIL', 5):
            folder, more = self.seeded()
            shutil.copyfile(folder/'native-history.backup.json', folder/'native-history.json')
            old = self.state(folder)['sequence']
            self.assertEqual(len(nh.archive_entries(self.archive(folder))), old + 1, 'the archive is one event ahead')
            added = sum(self.record(folder, more[:2]))
            state = self.assert_consistent(folder)
            self.assertEqual(state['sequence'], old + added)
            loaded = [row['sequence'] for row in nh.History(folder, detail_days=7).load()['events']]
            self.assertEqual(loaded, list(range(1, old + added + 1)), 'the lost event left; the new ones follow without a duplicate')

    def test_failed_append_or_state_write(self):
        values = fresh(events(9, 40, START, spacing=300.0))[:30]
        clean = self.root/'clean'
        self.record(clean, values)
        folder = self.root/'append'
        self.record(folder, values[:20])
        with patch.object(nh, 'append_bytes', side_effect=OSError('power cut')), self.assertRaises(OSError):
            self.record(folder, values[20:21])
        self.assertEqual(self.state(folder)['sequence'], 21, 'the state was written first')
        self.record(folder, values[21:])
        for name in ('native-history.json', 'native-history.backup.json', nh.ARCHIVE):
            self.assertEqual((folder/name).read_bytes(), (clean/name).read_bytes(), name)
        folder = self.root/'state'
        self.record(folder, values[:20])
        real = nh.atomic_bytes

        def fail(target, raw):
            if target.name == 'native-history.json':
                raise OSError('power cut')
            real(target, raw)
        with patch.object(nh, 'atomic_bytes', fail), self.assertRaises(OSError):
            self.record(folder, values[20:21])
        history = nh.History(folder, detail_days=7)
        self.assertEqual(history.load()['sequence'], 20)
        self.assertTrue(history.restored, 'main renamed to backup; the backup is complete')
        self.record(folder, values[20:])
        self.assert_consistent(folder)
        self.assertEqual([row['sequence'] for row in nh.History(folder, detail_days=7).load()['events']], list(range(1, 31)))

    # ---------------------------------------------------------------- compaction and the budget
    def test_compaction_keeps_only_retained_events(self):
        values = events(10, 900, START, spacing=465.0)
        folder = self.root/'h'
        history = nh.History(folder, detail_days=1)
        sizes = []
        for value, now in values:
            if not history.record(copy.deepcopy(value), now):
                continue  # a repeated publication prunes but never compacts
            state = self.state(folder)
            sizes.append((state['archive_lines'], len(state['index'])))
            self.assertLessEqual((state['archive_lines'] - len(state['index']))*4, state['archive_lines'])
        self.assertTrue(any(after < before for (before, _), (after, _) in zip(sizes, sizes[1:])), 'compacted at least once')
        state = self.assert_consistent(folder)
        self.record(self.root/'v1', values, writer=v1, days=1)
        self.assertEqual(encoded(nh.History(folder, detail_days=1).load()), encoded(v1.History(self.root/'v1', detail_days=1).load()))
        self.assertEqual(state['detail_budget_dropped'], 0)

    def test_budget_drops_the_oldest_detail_and_keeps_counters(self):
        values = events(13, 200, START, spacing=60.0)
        folder = self.root/'h'
        with patch.object(nh.History, 'RETENTION_BYTES', 40000), patch.object(nh.History, 'COMPACT_BYTES', 50000):
            self.record(folder, values)
        state = self.assert_consistent(folder)
        self.assertGreater(state['detail_budget_dropped'], 0)
        self.assertLessEqual(sum(row[3] for row in state['index']), 40000)
        self.assertLessEqual(len(self.archive(folder)), 50000 + max(row[3] for row in state['index']))
        self.record(self.root/'v1', values, writer=v1)
        self.assertEqual(state['totals'], v1.History(self.root/'v1', detail_days=7).load()['totals'], 'counters do not depend on detail')
        self.assertIsNone(nh.History(folder, detail_days=7).public(now=values[-1][1])['weekly'])

    # ---------------------------------------------------------------- reset and storage accounting
    def test_statistics_reset_empties_state_and_archive(self):
        import stats_reset
        values = events(14, 60, START, spacing=300.0)
        folder = self.root/'h'
        self.record(folder, values)
        seen = []
        retained = len(nh.History(folder, detail_days=7).load()['events'])
        with patch('retention_settings.configured_days', return_value=7):
            old = stats_reset.reset_native_history(folder, None, WALL, before=seen.append)
        self.assertEqual(len(old['events']), retained)
        self.assertEqual(seen, [old])
        self.assertEqual(nh.History(folder, detail_days=7).load()['events'], [])
        self.assertEqual(self.archive(folder), b'')
        state = self.assert_consistent(folder)
        self.assertEqual((state['index'], state['tail'], state['counter_accuracy']), ([], [], 'reset by the owner'))
        self.assertEqual((folder/'native-history.backup.json').read_bytes(), (folder/'native-history.json').read_bytes())
        self.record(folder, [(dict(values[0][0]), WALL + 10)])
        self.assertEqual(self.state(folder)['index'][0][0], old['sequence'] + 1)

    def test_storage_counts_the_archive(self):
        import stats_mode
        values = events(15, 20, START, spacing=300.0)
        self.record(self.root, values)
        total = sum((self.root/name).stat().st_size for name in ('native-history.json', 'native-history.backup.json', nh.ARCHIVE))
        self.assertEqual(stats_mode.storage(self.root, self.root)['flash:native-history.json'], total)


if __name__ == '__main__':
    unittest.main()
