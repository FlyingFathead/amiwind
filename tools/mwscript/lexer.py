# SPDX-License-Identifier: GPL-3.0-only
"""MWScript tokens, with the tolerances the original editor had and the game data relies on.

Tolerances (learned from OpenMW's scanner, components/compiler/scanner.cpp; our own code):
  - ',' and ':' are whitespace; '\\r' is ignored; ';' starts a comment to the end of the line;
  - '[' and ']' are the same as '(' and ')';
  - names may start with a digit ("1stFloor") and may hold '`' and "'"; a '-' inside a name stays in the name when
    a name character follows it ("Tel-Branora"), so "a-b" is one name, as in the original;
  - a quoted string that reaches the end of its line ends there (a warning), except that an empty one is empty;
  - comparison operators are read leniently: "=" and "= =" mean "==", ">=<" means ">=", each with a warning;
  - junk characters at the start of a line (before its first word) are skipped with a warning;
  - '->' is the explicit reference arrow, '.' between two names is a member access, '.5' is a number.
"""


class Token:
    __slots__ = ('kind', 'value', 'line', 'quoted')

    def __init__(self, kind, value, line, quoted=False):
        self.kind, self.value, self.line, self.quoted = kind, value, line, quoted

    def __repr__(self):
        return 'Token(%s %r @%d%s)' % (self.kind, self.value, self.line, ' q' if self.quoted else '')


class LexError(ValueError):
    pass


def _namechar(c):
    return c.isalnum() or c in "_`'" or (ord(c) > 127 and c.isprintable())


def tokenize(text, warnings=None):
    """[Token]: kinds name, int, float, op (== != < <= > >= + - * / ( ) -> .), nl, eof."""
    warn = warnings.append if warnings is not None else (lambda message: None)
    out, i, n, line = [], 0, len(text), 1
    line_start = True     # no real token on this line yet (junk is skipped here)
    while i < n:
        c = text[i]
        if c == '\n':
            out.append(Token('nl', None, line)); line += 1; i += 1; line_start = True; continue
        if c in ' \t\r,:\x00\x0b\x0c':
            i += 1; continue
        if c == ';':
            while i < n and text[i] != '\n':
                i += 1
            continue
        if c == '"':
            j = i + 1
            while j < n and text[j] not in '"\n':
                j += 1
            value = text[i + 1:j]
            if j >= n or text[j] == '\n':
                stripped = value.split(';', 1)[0].strip()
                warn('line %d: unterminated string %r' % (line, value[:40]))
                value = value if stripped else ''
                i = j
            else:
                i = j + 1
            out.append(Token('name', value, line, quoted=True)); line_start = False; continue
        if c.isdigit() or (c == '.' and i + 1 < n and text[i + 1].isdigit()):
            j = i
            while j < n and text[j].isdigit():
                j += 1
            if j < n and text[j] == '.':
                k = j + 1
                while k < n and text[k].isdigit():
                    k += 1
                if k < n and (text[k].isalpha() or text[k] == '_'):
                    # "1.5a": the original refuses it; read the number and leave the rest
                    warn('line %d: junk after a number' % line)
                out.append(Token('float', float(text[i:k] if k > i + 1 or text[i] != '.' else '0'), line))
                i = k; line_start = False; continue
            if j < n and _namechar(text[j]):
                # a name that starts with digits
                k = j
                while k < n and (_namechar(text[k]) or (text[k] == '-' and k + 1 < n and _namechar(text[k + 1]))):
                    k += 1
                out.append(Token('name', text[i:k], line)); i = k; line_start = False; continue
            out.append(Token('int', int(text[i:j]), line)); i = j; line_start = False; continue
        if _namechar(c):
            j = i
            while j < n and (_namechar(text[j]) or (text[j] == '-' and j + 1 < n and _namechar(text[j + 1]))):
                j += 1
            out.append(Token('name', text[i:j], line)); i = j; line_start = False; continue
        if c in '=<>!':
            j = i
            while j < n and text[j] in '=<>! \t':
                j += 1
            op = text[i:j].rstrip(' \t')
            i = i + len(op)
            if c == '=':
                kind = '=='
            elif c == '!':
                kind = '!='
            elif len(op) > 1 and op[1] == '=':
                kind = c + '='
            else:
                kind = c
            if op != kind:
                warn('line %d: operator %r read as %s' % (line, op, kind))
            out.append(Token('op', kind, line)); line_start = False; continue
        if c == '-':
            if i + 1 < n and text[i + 1] == '>':
                out.append(Token('op', '->', line)); i += 2
            else:
                out.append(Token('op', '-', line)); i += 1
            line_start = False; continue
        if c in '+*/()[].':
            out.append(Token('op', {'[': '(', ']': ')'}.get(c, c), line)); i += 1; line_start = False; continue
        if line_start:
            j = i
            while j < n and not (_namechar(text[j]) or text[j] in '"\n;'):
                j += 1
            warn('line %d: stray characters %r at the start of a line' % (line, text[i:j]))
            i = j; continue
        raise LexError('line %d: unexpected character %r' % (line, c))
    out.append(Token('nl', None, line))
    out.append(Token('eof', None, line))
    return out
