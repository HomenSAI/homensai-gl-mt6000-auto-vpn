#!/usr/bin/env python3
"""Honest percentile statistics: distribution-free confidence for a quantile from n samples (Python 3.9+, stdlib only).

The "59-sample rule". The empirical P95 printed from n samples is only an ESTIMATE at every n: it is the sample's own
order statistic X_(ceil(0.95 n)), and it lies above the true 95th percentile in only about 57 % of cases at n = 59, 35 %
at n = 60, 38 % at n = 100 and 43 % at n = 300; over the whole range 59 <= n <= 300 that coverage stays between 35 % and
57 %, so the empirical P95 is never a 95 % upper bound. A one-sided 95 %-confidence UPPER BOUND of the true P95 is a
different, separately computed order statistic X_(s) (see upper_rank): the smallest s with P(Binomial(n, 0.95) <= s-1)
>= 0.95 - the maximum for 59 <= n <= 92, X_(n-1) for 93 <= n <= 123, X_(99) at n = 100, X_(292) at n = 300. It exists
only from n >= 59, where the maximum is enough: the chance that all n samples fall below the true P95 is 0.95**n and
0.95**59 = 0.0485 < 0.05 (0.95**58 = 0.0510 is not). The 95 % holds for independent, identically distributed samples
only; repeated cycles on one bench are autocorrelated, so the effective n is smaller and the real coverage of the bound
is lower than 95 %. With fewer samples the printed "P95" is just a point estimate - for n <= 19 it is simply the sample
maximum - and no bound can be named.

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

Public API: wilson_interval(), format_wilson(), quantile_summary(), max_coverage(), max_confidence(), min_n(), format_p95(), format_max_claim(),
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


Z95 = 1.959964  # two-sided 95 % normal quantile


def wilson_interval(k, n, z=Z95):
    """Wilson score interval (low, high) for a proportion k of n, as fractions in 0..1; None when n < 1 or k is not 0..n.

    p = k/n, d = 1 + z^2/n, centre c = (p + z^2/2n)/d, half-width h = z*sqrt(p(1-p)/n + z^2/4n^2)/d, interval c -/+ h.
    Unlike the plain k/n it never claims certainty from a short run: 3 of 3 gives 43.8..100 %, 59 of 59 gives 93.8..100 %,
    0 of 10 gives 0..27.8 %. The ends are clamped to 0 and 1 (the formula gives exactly 0 / 1 there up to rounding)."""
    if not isinstance(k, int) or not isinstance(n, int) or isinstance(k, bool) or isinstance(n, bool) or n < 1 or not 0 <= k <= n:
        return None
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (0.0 if k == 0 else max(0.0, c - h), 1.0 if k == n else min(1.0, c + h))


def _tenths(x, up):
    """x (0..1) in percent with one decimal, rounded outwards: DOWN for a lower bound, UP for an upper bound. The
    round(..., 6) removes binary noise first, so an exact 43.8 % stays 43.8 and never becomes 43.7 or 43.9."""
    tenths = round(x * 1000, 6)
    return '%.1f' % ((math.ceil(tenths) if up else math.floor(tenths)) / 10)


def format_wilson(k, n, lang='ru'):
    """'43.8–100 %' style text of the 95 % Wilson interval for k of n (one decimal, a trailing .0 dropped); '' when undefined.

    The display is conservative (owner decision 07.11.2026): the lower bound is rounded DOWN and the upper bound UP to one
    decimal, so the printed interval always contains the computed one. 3 of 3: 43.85 % is shown as 43.8 %, not 43.9 %;
    59 of 59: 93.89 % -> 93.8 %; 0 of 10: 27.75 % -> 27.8 %."""
    w = wilson_interval(k, n)
    if w is None:
        return ''
    lo, hi = _tenths(w[0], False), _tenths(w[1], True)
    lo, hi = (t[:-2] if t.endswith('.0') else t for t in (lo, hi))
    if lang == 'ru':
        lo, hi = lo.replace('.', ','), hi.replace('.', ',')
    return '%s–%s %%' % (lo, hi)


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
      n, q, conf, min_n, honest (n >= min_n: only means that an upper bound EXISTS; it does NOT make `value` a bound),
      value (empirical quantile = X_(ceil(q n)), an estimate at every n; None for n = 0), max,
      rank (1-based rank of value), ci = (low, high, coverage) two-sided order-statistic interval at `conf`
      (low/high None when n is too small to bound that side), upper = one-sided upper confidence bound at `conf`
      (the smallest order statistic X_(s) with P(B <= s-1) >= conf; None when even the maximum is not enough),
      max_confidence (P(max >= true quantile)), max_coverage (with `conf`, this fraction of cases <= max).
    """
    # Only finite observations count: NaN or an infinity is not a measurement and must not raise n (review F-58).
    vals = sorted(float(v) for v in samples
                  if isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v))
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
        # P(low <= B <= high-1) = F_B(high-1) - F_B(low-1); the lower tail is subtracted for every finite low rank,
        # also for low = 1 where F_B(0) = (1-q)**n is small but not zero (review F-57: 1..6, q=0.5 -> 62/64).
        cover = float(cdf[high - 1] - cdf[low - 1])
    out['ci'] = (vals[low - 1] if low else None, vals[high - 1] if high else None, cover)
    out['upper'] = vals[up - 1] if up else None
    return out


def upper_rank(n, q=Q, conf=CONF):
    """1-based rank s of the one-sided upper confidence bound X_(s) of the true q-quantile; None when n is too small.

    This is a different order statistic from the empirical quantile X_(ceil(q n)): at n = 59 the empirical P95 is X_(57)
    (only ~57 % confidence of bounding the true P95), while the 95 % upper bound is X_(59), the maximum (review F-59).
    Further: the maximum up to n = 92, X_(92) at n = 93, X_(99) at n = 100, X_(292) at n = 300."""
    if not isinstance(n, int) or isinstance(n, bool) or n < 1:
        return None
    return _ranks(n, _frac(q), _frac(conf))[2]


def format_upper(n, max_value, lang='ru', q=Q, conf=CONF):
    """Text of the separately computed upper confidence bound for a summary row that keeps only n / median / P95 / max:
    the value is known when the bound is the maximum, otherwise the rank of the bounding order statistic is named."""
    name = 'P%d' % round(q * 100)
    c = int(round(conf * 100))
    s = upper_rank(n, q, conf)
    if s is None:
        return ('верхней границы %s с %d %% уверенностью нет (нужно n ≥ %d)' % (name, c, min_n(q, conf)) if lang == 'ru' else
                'no %d %%-confidence upper bound of the %s (needs n ≥ %d)' % (c, name, min_n(q, conf)))
    if s == n and max_value is not None:
        return ('верхняя граница %s с %d %% уверенностью: %s (максимум)' % (name, c, _num(max_value)) if lang == 'ru' else
                '%d %%-confidence upper bound of the %s: %s (the maximum)' % (c, name, _num(max_value)))
    return ('верхняя граница %s с %d %% уверенностью: X(%d) из %d' % (name, c, s, n) if lang == 'ru' else
            '%d %%-confidence upper bound of the %s: X(%d) of %d' % (c, name, s, n))


def _num(x):
    return '%.1f' % x if isinstance(x, float) else str(x)


def coverage_percent(n, conf=CONF):
    """Floor (conservative) whole percent of cases covered by the maximum with confidence conf."""
    return int(math.floor(max_coverage(n, conf) * 100 + 1e-9))


def format_p95(value, n, lang='ru', q=Q, conf=CONF):
    """'P95≈X (n=N, оценка)' / 'P95≈X (n=N, estimate)' when n >= 59 (the empirical P95 stays an estimate - at n = 59..300 it
    covers the true P95 in only 35-57 % of cases - and is never called a bound; the upper bound is named separately by
    format_upper), else 'P95≈X (n=N, мало данных: нужно ≥ 59)' / 'P95≈X (n=N, too few: needs ≥59)'."""
    name = 'P%d' % round(q * 100)
    need = min_n(q, conf)
    if n >= need:
        return '%s≈%s (n=%d, %s)' % (name, _num(value), n, 'оценка' if lang == 'ru' else 'estimate')
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
    """Compact 'n / median / P95 / max' cell for text tables. The P95 always carries '≈' (an estimate at every n);
    a small sample also gets '(≥k %)' after the max.

    "Small" depends on the confidence level: min_n(Q, conf), 59 at 95 % but 90 at 99 % (review F-60)."""
    need = min_n(Q, conf)
    if n >= need:
        return '%d / %s / ≈%s / %s' % (n, _num(median), _num(p95), _num(maximum))
    return '%d / %s / ≈%s / %s (≥%d %%)' % (n, _num(median), _num(p95), _num(maximum), coverage_percent(n, conf))


LEGEND = {
    'ru': '≈P95 — оценка (95-й процентиль самой выборки), а не граница, при любом n; «(≥k %%)» — с 95 %% уверенностью не менее k %% '
          'случаев не медленнее max (k = 100·0,05^(1/n)). Верхняя 95 %%-я граница настоящего P95 считается отдельно и есть только '
          'при n ≥ %d (для независимых замеров).' % MIN_N,
    'en': '≈P95 — an estimate (the 95th percentile of the sample itself), not a bound, at every n; "(≥k %%)" — with 95 %% confidence at '
          'least k %% of cases are no slower than the max (k = 100·0.05^(1/n)). The 95 %% upper bound of the true P95 is computed '
          'separately and exists only from n ≥ %d (for independent samples).' % MIN_N,
}


if __name__ == '__main__':
    import sys
    data = [float(x) for x in sys.argv[1:]]
    s = quantile_summary(data)
    print(format_p95(s['value'], s['n'], 'ru') if data else 'no samples')
    if data:
        print(format_max_claim(s['max'], s['n'], 'ru'))
        print(s)
