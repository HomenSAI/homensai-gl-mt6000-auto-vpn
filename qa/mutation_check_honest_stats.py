"""Mutation check for scripts/honest_stats.py: every mutant of the statistics must be killed by qa/test_honest_stats.py.

Not a test_*.py file (it spawns the test suite once per mutant); run it by hand or in review:
  python qa/mutation_check_honest_stats.py          # exit 0 only when all mutants are killed
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / 'scripts' / 'honest_stats.py').read_text(encoding='utf-8')
MUTANTS = [
    ("q ** n > alpha", "q ** n >= alpha"),                                  # 0.95**n boundary
    ("q ** n > alpha", "q ** (n + 1) > alpha"),                             # off by one -> 58
    ("return float(1 - _frac(q) ** n) if n > 0 else 0.0", "return float(_frac(q) ** n) if n > 0 else 0.0"),
    ("return float((1 - _frac(conf))) ** (1.0 / n)", "return float((1 - _frac(conf))) ** (1.0 / (n + 1))"),
    ("return float((1 - _frac(conf))) ** (1.0 / n)", "return float((1 - _frac(conf))) ** n"),
    ("honest=n >= need", "honest=n > need"),
    ("if n >= need:\n        return '%s≈%s (n=%d, %s)'", "if n > need:\n        return '%s≈%s (n=%d, %s)'"),
    ("if n >= need:\n        return '%d / %s / ≈%s / %s'", "if n > need:\n        return '%d / %s / ≈%s / %s'"),
    ("need = min_n(Q, conf)\n    if n >= need:", "need = MIN_N\n    if n >= need:"),                # F-60: fixed 95 % threshold
    ("cover = float(cdf[high - 1] - cdf[low - 1])", "cover = float(cdf[high - 1] - cdf[low - 1] if low > 1 else cdf[high - 1])"),  # F-57
    ("and math.isfinite(v))", "and v == v)"),                                # F-58: infinities would count again
    ("return max(1, math.ceil(_frac(q) * n))", "return max(1, math.floor(_frac(q) * n))"),
    ("if cdf[r - 1] <= half:", "if cdf[r - 1] < half / 2:"),
    ("if cdf[s - 1] >= 1 - half:", "if cdf[s - 1] > 1 - half / 2:"),
    ("if cdf[s - 1] >= conf:", "if cdf[s - 1] >= conf * 0.9:"),
    ("acc += math.comb(n, i) * q ** i * (1 - q) ** (n - i)", "acc += math.comb(n, i) * q ** i * (1 - q) ** (n - i - 1)"),
    ("return sum(math.comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k + 1))",
     "return sum(math.comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k))"),
    ("return int(math.floor(max_coverage(n, conf) * 100 + 1e-9))", "return int(math.ceil(max_coverage(n, conf) * 100))"),
    ("≥ %d %% случаев не медленнее", "≤ %d %% случаев не медленнее"),
    ("(n=%d, too few: needs ≥%d)", "(n=%d, too few: needs >%d)"),
]


def main():
    survived = []
    for i, (old, new) in enumerate(MUTANTS):
        if SOURCE.count(old) != 1:
            print('MUTANT %d does not match exactly once: %r' % (i, old))
            return 2
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / 'honest_stats.py').write_text(SOURCE.replace(old, new), encoding='utf-8')
            env = dict(os.environ, HONEST_STATS_DIR=d, PYTHONDONTWRITEBYTECODE='1')
            r = subprocess.run([sys.executable, '-m', 'unittest', 'qa.test_honest_stats.ExactBinomial', 'qa.test_honest_stats.Wording'],
                               cwd=str(ROOT), env=env, capture_output=True, text=True, timeout=600)
        killed = r.returncode != 0
        print('mutant %2d %s: %s -> %s' % (i, 'KILLED  ' if killed else 'SURVIVED', old[:48].replace('\n', ' '), new[:48].replace('\n', ' ')))
        if not killed:
            survived.append(i)
    print('%d mutants, %d killed, %d survived' % (len(MUTANTS), len(MUTANTS) - len(survived), len(survived)))
    return 1 if survived else 0


if __name__ == '__main__':
    sys.exit(main())
