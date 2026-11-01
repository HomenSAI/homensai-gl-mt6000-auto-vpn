# HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
"""Property-based checks (hypothesis) of the Python parsers that read untrusted or possibly corrupt input.

  docker run --rm -v <worktree>:/src:ro homensai-vpn-qa-external:20261101 \
      python3 -I -m pytest -q -p no:cacheprovider /src/qa/external/hypothesis/test_props.py
(pytest is optional: `python3 -I /src/qa/external/hypothesis/test_props.py` runs the same checks.)
A failing property is a finding, not a broken test: see docs/qa/EXTERNAL-TOOLS-2026-11-01.md.
"""
import json
import pathlib
import sys
import tempfile

from hypothesis import HealthCheck, given, settings, strategies as st

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / 'router/files/usr/lib/homensai-vpn'))
import native_history  # noqa: E402
import rpc_input  # noqa: E402

SETTINGS = settings(max_examples=3000, deadline=None, suppress_health_check=list(HealthCheck))
json_values = st.recursive(
    st.none() | st.booleans() | st.integers() | st.floats(allow_nan=False, allow_infinity=False) | st.text(max_size=8),
    lambda inner: st.lists(inner, max_size=4) | st.dictionaries(st.text(max_size=6), inner, max_size=4),
    max_leaves=30)
nested = st.integers(min_value=1, max_value=20000).map(lambda n: '[' * n + ']' * n)
texts = st.text(max_size=300) | json_values.map(json.dumps) | nested


@SETTINGS
@given(texts)
def test_rpc_decode_request_fails_only_with_rpc_codes(text):
    try:
        value = rpc_input.decode_request(text)
    except ValueError as error:
        assert str(error).startswith('RPC-'), str(error)
    else:
        assert isinstance(value, dict)


@SETTINGS
@given(st.binary(max_size=400) | texts.map(lambda t: t.encode('utf8', 'surrogatepass')))
def test_archive_entries_never_raises(raw):
    for sequence, line in native_history.archive_entries(raw):
        assert isinstance(sequence, int) and line.endswith(b'\n')


@SETTINGS
@given(st.lists(st.integers(min_value=0, max_value=2 ** 53 - 1), max_size=20), st.dictionaries(
    st.sampled_from(['a', 'kind', 'zz', 'time']), json_values, max_size=3))
def test_archive_line_round_trip(sequences, extra):
    raw = b''.join(native_history.archive_line(dict(extra, sequence=s)) for s in sequences)
    assert [s for s, _ in native_history.archive_entries(raw)] == sequences


HISTORY_FILES = (texts | json_values.map(lambda d: json.dumps({'schema': 2, 'data': d, 'sha256': '0' * 64}))).map(
    lambda t: t.encode('utf8', 'surrogatepass'))


@SETTINGS
@given(HISTORY_FILES)
def test_history_read_fails_only_with_history_error(raw):
    """A corrupt native-history.json must give HistoryError (the caller's contract), never another exception."""
    with tempfile.TemporaryDirectory() as directory:
        (pathlib.Path(directory) / 'native-history.json').write_bytes(raw)
        history = native_history.History(directory, detail_days=7)
        try:
            history._read()
        except native_history.HistoryError:
            pass


if __name__ == '__main__':
    failed = 0
    for name, test in sorted(globals().items()):
        if name.startswith('test_'):
            try:
                test()
                print('PASS', name)
            except Exception as error:  # report every property, then fail
                failed += 1
                print('FAIL', name, type(error).__name__, str(error).splitlines()[0][:160] if str(error) else '')
    sys.exit(1 if failed else 0)
