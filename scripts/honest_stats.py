#!/usr/bin/env python3
"""Honest percentile statistics: distribution-free confidence for a quantile from n samples (Python 3.9+, stdlib only).

The "59-sample rule". A P95 estimated from n samples is a guaranteed upper bound of the true 95th percentile
(with 95 % confidence) only when n >= 59, because the chance that all n samples fall below the true P95 is 0.95**n
and 0.95**59 = 0.0485 < 0.05 (0.95**58 = 0.0510 is not). With fewer samples the printed "P95" is just a point
estimate - for n <= 19 it is simply the sample maximum - and must not be presented as a bound.

What can be said honestly about a small sample (n < 59):
  * the sample maximum is above the true q-quantile with probability 1 - q**n (n=4: 18.5 %, n=14: 51.2 %);
  * with confidence C, at least a fraction p = (1 - C)**(1/n) of all future cases is not slower than the sample
    maximum (derivation below). n=4, C=95 %: >= 47.3 %; n=14: >= 80.7 %; n=59: >= 95.0 %.

Derivation. Let F be the (continuous) distribution function and M the sample maximum. Then F(M) is Beta(n, 1), so
P(F(M) < p) = p**n. Setting p**n = 1 - C gives: with confidence C, F(M) >= (1 - C)**(1/n), i.e. at least that
fraction of cases is <= M. Order statistics in general: with B ~ Binomial(n, q) = number of samples below the true
q-quantile Q, P(X_(r) <= Q) = P(B >= r) and P(X_(s) >= Q) = P(B <= s-1), so [X_(l), X_(u)] covers Q with
probability P(l <= B <= u-1) = F_B(u-1) - F_B(l-1). No distribution assumption is needed (samples are treated as
independent and identically distributed; repeated cycles on one bench are an approximation).

Public API: quantile_summary(), max_coverage(), max_confidence(), min_n(), format_p95(), format_max_claim(),
cell_text(). Everything is exact binomial arithmetic on fractions where it matters for the tests.
"""
import math
from fractions import Fraction
from functools import lru_cache

Q = 0.95
CONF = 0.95
LANGS = ('ru', 'en')


def _frac(x):
    """Exact fraction of a probability given as a float or a string like 0.95 (via its shortest repr)."""
    return x if isinstance(x, Fraction) else Fraction(repr(x)) if isinstance(x, float) else Fraction(x)


def binom_cdf(k, n, p):
    """P(B <= k) for B ~ Binomial(n, p), exact (returns a Fraction). k < 0 -> 0, k >= n -> 1."""
    p = _frac(p)
    if k < 0:
        return Fraction(0)
    if k >= n:
        return Fraction(1)
    return sum(math.comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k + 1))


def min_n(q=Q, conf=CONF):
    """Smallest n for which q**n <= 1 - conf: 59 for the P95 at 95 % confidence."""
    q, alpha = _frac(q), 1 - _frac(conf)
    n = 1
    while q ** n > alpha:
        n += 1
    return n


MIN_N = min_n()  # 59


def max_confidence(n, q=Q):
    """Probability that the sample maximum of n samples is >= the true q-quantile: 1 - q**n."""
    return float(1 - _frac(q) ** n) if n > 0 else 0.0


def max_coverage(n, conf=CONF):
    """With confidence `conf`, at least this fraction of cases is not slower than the sample maximum: (1-conf)**(1/n)."""
    if n < 1:
        return 0.0
    return float((1 - _frac(conf))) ** (1.0 / n)


@lru_cache(maxsize=512)
def _cdf_table(n, q):
    """[P(B <= 0), ..., P(B <= n)] for B ~ Binomial(n, q), exact, one pass."""
    out, acc = [], Fraction(0)
    for i in range(n + 1):
        acc += math.comb(n, i) * q ** i * (1 - q) ** (n - i)
        out.append(acc)
    return tuple(out)


@lru_cache(maxsize=512)
def _ranks(n, q, conf):
    """1-based ranks (low, high, upper) that do not depend on the data, only on n, q and conf."""
    cdf = _cdf_table(n, q)
    half = (1 - conf) / 2
    low = high = up = None
    for r in range(n, 0, -1):            # largest l with P(B <= l-1) <= alpha/2  <=>  P(X_(l) <= Q) >= 1 - alpha/2
        if cdf[r - 1] <= half:
            low = r
            break
    for s in range(1, n + 1):            # smallest u with P(B <= u-1) >= 1 - alpha/2
        if cdf[s - 1] >= 1 - half:
            high = s
            break
    for s in range(1, n + 1):            # smallest s with P(B <= s-1) >= conf: X_(s) is a one-sided upper bound
        if cdf[s - 1] >= conf:
            up = s
            break
    return low, high, up


def _rank(n, q):
    return max(1, math.ceil(_frac(q) * n))


def quantile_summary(samples, q=Q, conf=CONF):
    """Empirical q-quantile plus distribution-free confidence statements.

    Returns a dict:
      n, q, conf, min_n, honest (n >= min_n), value (empirical quantile = X_(ceil(q n)), None for n = 0), max,
      rank (1-based rank of value), ci = (low, high, coverage) two-sided order-statistic interval at `conf`
      (low/high None when n is too small to bound that side), upper = one-sided upper confidence bound at `conf`
      (the smallest order statistic X_(s) with P(B <= s-1) >= conf; None when even the maximum is not enough),
      max_confidence (P(max >= true quantile)), max_coverage (with `conf`, this fraction of cases <= max).
    """
    vals = sorted(float(v) for v in samples if isinstance(v, (int, float)) and not isinstance(v, bool))
    n = len(vals)
    need = min_n(q, conf)
    out = dict(n=n, q=q, conf=conf, min_n=need, honest=n >= need, value=None, max=None, rank=None,
               ci=(None, None, None), upper=None, max_confidence=max_confidence(n, q), max_coverage=max_coverage(n, conf))
    if not n:
        return out
    k = _rank(n, q)
    out.update(value=vals[k - 1], max=vals[-1], rank=k)
    low, high, up = _ranks(n, _frac(q), _frac(conf))
    cover = None
    if low is not None and high is not None:
        cdf = _cdf_table(n, _frac(q))
        cover = float(cdf[high - 1] - cdf[low - 1] if low > 1 else cdf[high - 1])
    out['ci'] = (vals[low - 1] if low else None, vals[high - 1] if high else None, cover)
    out['upper'] = vals[up - 1] if up else None
    return out


def _num(x):
    return '%.1f' % x if isinstance(x, float) else str(x)


def coverage_percent(n, conf=CONF):
    """Floor (conservative) whole percent of cases covered by the maximum with confidence conf."""
    return int(math.floor(max_coverage(n, conf) * 100 + 1e-9))


def format_p95(value, n, lang='ru', q=Q, conf=CONF):
    """'P95=X (n=N)' when honest, else 'P95≈X (n=N, мало данных: нужно ≥ 59)' / 'P95≈X (n=N, too few: needs ≥59)'."""
    name = 'P%d' % round(q * 100)
    need = min_n(q, conf)
    if n >= need:
        return '%s=%s (n=%d)' % (name, _num(value), n)
    if lang == 'ru':
        return '%s≈%s (n=%d, мало данных: нужно ≥ %d)' % (name, _num(value), n, need)
    return '%s≈%s (n=%d, too few: needs ≥%d)' % (name, _num(value), n, need)


def format_max_claim(max_value, n, lang='ru', conf=CONF):
    """The honest statement for a small sample: the maximum and what it covers with confidence `conf`."""
    pc = coverage_percent(n, conf)
    c = int(round(conf * 100))
    if lang == 'ru':
        return 'max %s: с %d %% уверенностью ≥ %d %% случаев не медленнее max' % (_num(max_value), c, pc)
    return 'max %s: with %d %% confidence ≥ %d %% of cases are no slower than the max' % (_num(max_value), c, pc)


def cell_text(n, median, p95, maximum, conf=CONF):
    """Compact 'n / median / P95 / max' cell for text tables. A small sample gets '≈' and '(≥k %)' after the max."""
    if n >= MIN_N:
        return '%d / %s / %s / %s' % (n, _num(median), _num(p95), _num(maximum))
    return '%d / %s / ≈%s / %s (≥%d %%)' % (n, _num(median), _num(p95), _num(maximum), coverage_percent(n, conf))


LEGEND = {
    'ru': '≈P95 — мало данных (n < %d), это оценка, а не граница; «(≥k %%)» — с 95 %% уверенностью не менее k %% случаев '
          'не медленнее max (k = 100·0,05^(1/n)). Честный P95 только при n ≥ %d.' % (MIN_N, MIN_N),
    'en': '≈P95 — too few samples (n < %d): an estimate, not a bound; "(≥k %%)" — with 95 %% confidence at least k %% of '
          'cases are no slower than the max (k = 100·0.05^(1/n)). An honest P95 needs n ≥ %d.' % (MIN_N, MIN_N),
}


if __name__ == '__main__':
    import sys
    data = [float(x) for x in sys.argv[1:]]
    s = quantile_summary(data)
    print(format_p95(s['value'], s['n'], 'ru') if data else 'no samples')
    if data:
        print(format_max_claim(s['max'], s['n'], 'ru'))
        print(s)
