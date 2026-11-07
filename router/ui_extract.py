"""Extract named top-level declarations (and their dependency closure) from a LuCI view module source.

The approved page (router/ui/) reuses the proven display logic of the legacy pipeline instead of copying it:
freshness, channel health, traffic-channel proof, Auto/manual/monitor models, journal and error catalogue. This
module splits the legacy module's top level into statements, finds which statement declares which names, and returns
the statements needed by the given roots, in their original order. No evaluation; a small JS-aware scanner.
"""
import re

IDENT = re.compile(r'[A-Za-z_$][A-Za-z0-9_$]*')
REGEX_BEFORE = set('(,=:[!&|?{};+-*%<>~^')
REGEX_KEYWORDS = {'return', 'typeof', 'case', 'in', 'of', 'new', 'delete', 'void', 'throw', 'else', 'do', 'instanceof'}


def _skip_string(src, i):
    quote = src[i]; i += 1
    while i < len(src):
        c = src[i]
        if c == '\\':i += 2;continue
        if quote == '`' and c == '$' and src.startswith('${', i):
            i = _skip_braces(src, i + 1)
            continue
        if c == quote:return i + 1
        if c == '\n' and quote != '`':raise ValueError('UI-EXTRACT-STRING at %d' % i)
        i += 1
    raise ValueError('UI-EXTRACT-STRING-END')


def _skip_regex(src, i):
    i += 1; klass = False
    while i < len(src):
        c = src[i]
        if c == '\\':i += 2;continue
        if c == '[':klass = True
        elif c == ']':klass = False
        elif c == '/' and not klass:
            i += 1
            while i < len(src) and src[i].isalpha():i += 1
            return i
        elif c == '\n':raise ValueError('UI-EXTRACT-REGEX at %d' % i)
        i += 1
    raise ValueError('UI-EXTRACT-REGEX-END')


def tokens(src, start=0, end=None):
    """Yield (kind, text, position): kind in ident, punct, string, regex, number; comments skipped."""
    end = len(src) if end is None else end
    i = start; last = None
    while i < end:
        c = src[i]
        if c in ' \t\r\n':i += 1;continue
        if src.startswith('//', i):
            j = src.find('\n', i);i = end if j < 0 else j;continue
        if src.startswith('/*', i):
            j = src.find('*/', i + 2);i = end if j < 0 else j + 2;continue
        if c in '\'"`':
            j = _skip_string(src, i);yield ('string', src[i:j], i);last = ('string', '');i = j;continue
        if c == '/':
            if last is None or (last[0] == 'punct' and last[1] in REGEX_BEFORE) or (last[0] == 'ident' and last[1] in REGEX_KEYWORDS):
                j = _skip_regex(src, i);yield ('regex', src[i:j], i);last = ('regex', '');i = j;continue
        m = IDENT.match(src, i)
        if m:
            yield ('ident', m.group(0), i);last = ('ident', m.group(0));i = m.end();continue
        if c.isdigit() or (c == '.' and i + 1 < end and src[i + 1].isdigit()):
            m = re.compile(r'[0-9.]+(?:[eE][+-]?[0-9]+)?|0[xX][0-9a-fA-F]+').match(src, i)
            yield ('number', m.group(0), i);last = ('number', '');i = m.end();continue
        yield ('punct', c, i);last = ('punct', c);i += 1


def _skip_braces(src, i):
    """src[i] is '{'; return the index after its matching '}'."""
    depth = 0
    for kind, text, pos in tokens(src, i):
        if kind == 'punct':
            if text == '{':depth += 1
            elif text == '}':
                depth -= 1
                if depth == 0:return pos + 1
    raise ValueError('UI-EXTRACT-BRACE')


def statements(src, stop):
    """Split src[:stop] at top level. Returns [(start, end, declared_names)]."""
    result = []; toks = list(tokens(src, 0, stop)); n = len(toks); k = 0
    while k < n:
        kind, text, pos = toks[k]
        if kind == 'string' and k + 1 < n and toks[k + 1][1] == ';':  # 'use strict'; 'require x';
            result.append((pos, toks[k + 1][2] + 1, set()));k += 2;continue
        start = pos; depth = 0; names = set(); j = k
        is_function = kind == 'ident' and text == 'function'
        is_var = kind == 'ident' and text in ('var', 'let', 'const')
        if is_function and j + 1 < n and toks[j + 1][0] == 'ident':names.add(toks[j + 1][1])
        expect_name = is_var
        while j < n:
            kd, tx, ps = toks[j]
            if kd == 'punct' and tx in '([{':depth += 1
            elif kd == 'punct' and tx in ')]}':
                depth -= 1
                if depth == 0 and tx == '}' and is_function:
                    j += 1;break
                if depth == 0 and tx == '}' and not is_var:
                    # a block statement (if/for/try/IIFE) may end here without ';'
                    nxt = toks[j + 1] if j + 1 < n else None
                    if nxt is None or (src.count('\n', ps, nxt[2]) and nxt[1] not in ('else', 'catch', 'finally', '.', ')', '(', ',', ';', '?', ':', '&&', '||', '+')):
                        j += 1;break
            elif depth == 0 and kd == 'punct' and tx == ';':
                j += 1;break
            if is_var and depth == 0 and j > k:
                if kd == 'ident' and expect_name:names.add(tx);expect_name = False
                elif kd == 'punct' and tx == ',':expect_name = True
            j += 1
        end = toks[j - 1][2] + len(toks[j - 1][1]) if toks[j - 1][0] != 'string' else toks[j - 1][2] + len(toks[j - 1][1])
        result.append((start, end, names));k = j
    return result


def referenced(src, start, end):
    """Identifiers used in src[start:end] that are not property names (after '.') or object keys."""
    out = set(); prev = None; toks = list(tokens(src, start, end))
    for idx, (kind, text, pos) in enumerate(toks):
        if kind == 'ident' and not (prev and prev[0] == 'punct' and prev[1] == '.'):
            nxt = toks[idx + 1] if idx + 1 < len(toks) else None
            is_key = nxt and nxt[1] == ':' and prev and prev[1] in ('{', ',') and not (prev[1] == ',' and False)
            if not is_key:out.add(text)
        prev = (kind, text)
    return out


def closure(src, roots, stop_marker='return view.extend({', exclude=()):
    """Return the text of every top-level statement needed by roots (declarations plus statements that mutate them)."""
    stop = src.rindex(stop_marker)
    stmts = statements(src, stop)
    declares = {}
    for index, (s, e, names) in enumerate(stmts):
        for name in names:declares.setdefault(name, []).append(index)
    # A non-declaring top-level statement belongs to the declaration it starts with (X.push(...), X[k]=..., if(typeof X...)).
    mutators = {}
    for index, (s, e, names) in enumerate(stmts):
        if names:continue
        first = next(tokens(src, s, e), None)
        if first and first[0] == 'ident' and first[1] in declares:mutators.setdefault(first[1], []).append(index)
    wanted = set(); queue = list(roots); seen = set()
    while queue:
        name = queue.pop()
        if name in seen or name in exclude:continue
        seen.add(name)
        if name not in declares:continue
        for index in declares[name] + mutators.get(name, []):
            if index in wanted:continue
            wanted.add(index); s, e, _ = stmts[index]
            queue.extend(referenced(src, s, e) & set(declares))
    missing = [r for r in roots if r not in declares]
    if missing:raise ValueError('UI-EXTRACT-ROOT-MISSING: ' + ', '.join(missing))
    return '\n'.join(src[stmts[i][0]:stmts[i][1]] for i in sorted(wanted)), {n for i in wanted for n in stmts[i][2]}


def squeeze_indent(src):
    """Drop the leading indentation of every line that starts between tokens (code, not inside a string, template or regex).

    Newlines stay, so automatic semicolon insertion and line numbers are unchanged; only generated artifacts use this.
    """
    toks = list(tokens(src)); out = []; last = 0
    for index, (kind, text, pos) in enumerate(toks + [('end', '', len(src))]):
        gap = src[last:pos]
        if '\n' in gap:
            head, rest = gap.split('\n', 1)  # the text after the previous token on its own line stays as it is
            rest = re.sub(r'(?m)^[ \t]+(?=\S)', '', rest)
            gap = head + '\n' + re.sub(r'(?m)^[ \t]+$', '', rest)
        out.append(gap); out.append(text); last = pos + len(text)
    return ''.join(out)
