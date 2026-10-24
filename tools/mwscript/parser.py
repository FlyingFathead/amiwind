# SPDX-License-Identifier: GPL-3.0-only
"""MWScript statements and expressions to a small tree (tuples), with the language's quirks.

Quirks handled (each seen in the game data or documented by OpenMW's compiler; our own code):
  - declarations (short/long/float) may stand anywhere; a name is a local if the script declares it anywhere;
  - 'if' and 'while' conditions need no parentheses; 'elseif' and 'else' may carry junk after them;
  - a missing 'endif'/'endwhile' at the end of the script closes the block (warning); a stray one is skipped;
  - 'set x to y' tolerates a missing 'to';
  - function arguments follow the function's table entry (functions.py); optional arguments the game ignores
    (x, X, z) are read and dropped; extra words after a complete instruction are junk (warning);
  - an object id may be quoted or bare, an explicit reference is 'id -> function';
  - another object's or script's variable is 'name.variable' (quoted or bare);
  - a comparison chain is one comparison (MWScript has no 'and'/'or');
  - text after 'end' is ignored.
"""
from .lexer import tokenize
from .functions import lookup, KEYWORDS


class ParseError(ValueError):
    pass


TYPES = {'short': 's', 'long': 'l', 'float': 'f'}


def declarations(tokens):
    """{local name (folded): (type letter, order)} from every 'short/long/float name' line start."""
    out, start = {}, True
    for i, t in enumerate(tokens):
        if t.kind == 'nl':
            start = True; continue
        if start and t.kind == 'name' and not t.quoted and t.value.casefold() in TYPES:
            nxt = tokens[i + 1] if i + 1 < len(tokens) else None
            if nxt is not None and nxt.kind == 'name':
                name = nxt.value.casefold()
                if name not in out:
                    out[name] = (TYPES[t.value.casefold()], len(out))
        start = False
    return out


class Parser:
    """One script. CONTEXT: globals {name: type}, scripts {name: {local: type}}, ids (callable(name) -> bool or
    None: whether NAME is an object id of the game data)."""

    def __init__(self, text, globals_=None, scripts=None, warnings=None):
        self.warnings = [] if warnings is None else warnings
        self.tokens = tokenize(text, self.warnings)
        self.pos = 0
        self.locals = declarations(self.tokens)
        self.globals = globals_ or {}
        self.scripts = scripts or {}
        self.name = None
        self.ref = None         # the explicit reference of a bracketed 'id->( ... )' expression
        self.used = []          # function names in use order (with repeats)

    # --- token helpers ---
    def peek(self, k=0):
        return self.tokens[min(self.pos + k, len(self.tokens) - 1)]

    def next(self):
        t = self.tokens[self.pos]
        if t.kind != 'eof':
            self.pos += 1
        return t

    def at_eol(self):
        return self.peek().kind in ('nl', 'eof')

    def warn(self, text):
        self.warnings.append('line %d: %s' % (self.peek().line, text))

    def skip_line(self, why=None):
        junk = []
        while not self.at_eol():
            junk.append(self.next())
        if junk and why:
            self.warnings.append('line %d: %s: %s' % (junk[0].line, why, ' '.join(str(t.value) for t in junk)[:60]))
        if self.peek().kind == 'nl':
            self.next()

    def is_word(self, t, *words):
        return t.kind == 'name' and not t.quoted and t.value.casefold() in words

    # --- script ---
    def script(self):
        # Everything before 'begin' is junk; the original editor needs 'begin name' first.
        while self.peek().kind != 'eof' and not self.is_word(self.peek(), 'begin'):
            self.skip_line('text before begin')
        if self.peek().kind == 'eof':
            raise ParseError('no begin')
        self.next()
        if self.at_eol():
            raise ParseError('begin without a name')
        self.name = self.next().value
        self.skip_line('junk after begin')
        body = self.block(('end',))
        if self.is_word(self.peek(), 'end'):
            self.next()
        else:
            self.warnings.append('no end')
        return ('script', self.name, body)

    def block(self, enders):
        """Statements until a line starting with one of ENDERS (not consumed) or the end of the text."""
        out = []
        while True:
            t = self.peek()
            if t.kind == 'eof':
                return out
            if t.kind == 'nl':
                self.next(); continue
            if self.is_word(t, *enders):
                return out
            stmt = self.statement(enders)
            if stmt is not None:
                out.append(stmt)

    def statement(self, enders):
        t = self.peek()
        line = t.line
        word = t.value.casefold() if t.kind == 'name' and not t.quoted else None
        if word in TYPES:
            self.next()
            if not self.at_eol():
                self.next()
            self.skip_line('junk after a declaration')
            return None
        if word == 'set':
            return self.set_statement()
        if word == 'if':
            return self.if_statement(line)
        if word == 'while':
            self.next()
            cond = self.condition()
            self.skip_line('junk after while')
            body = self.block(('endwhile', 'end'))
            if self.is_word(self.peek(), 'endwhile'):
                self.next(); self.skip_line('junk after endwhile')
            else:
                self.warnings.append('line %d: while without endwhile' % line)
            return ('while', line, cond, body)
        if word in ('endif', 'endwhile', 'else', 'elseif'):
            self.next(); self.skip_line()
            self.warnings.append('line %d: stray %s' % (line, word))
            return None
        if word == 'return':
            self.next(); self.skip_line('junk after return')
            return ('return', line)
        if word == 'messagebox':
            return self.messagebox(line)
        if word == 'begin':
            self.next(); self.skip_line()
            self.warnings.append('line %d: a second begin' % line)
            return None
        if word == 'to':
            self.skip_line('a line starting with to')
            return None
        # explicit reference or a function call (instruction)
        ref = None
        if t.kind == 'name' and self.peek(1).kind == 'op' and self.peek(1).value == '->':
            ref = self.next().value; self.next()
            t = self.peek()
        if t.kind == 'name' and not t.quoted and lookup(t.value):
            call = self.call(ref)
            self.skip_line('junk after %s' % call[2])
            return ('do', line, call)
        if t.kind == 'name' and not t.quoted and t.value.casefold() == 'messagebox':
            return self.messagebox(line)
        # a variable or a number alone on a line, or an unknown word: the original ignores such lines when it can
        if t.kind == 'name' and (t.value.casefold() in self.locals or t.value.casefold() in self.globals):
            self.skip_line('a variable alone on a line')
            return None
        if t.kind == 'name' and not t.quoted:
            raise ParseError('line %d: unknown instruction %r' % (line, t.value))
        self.skip_line('junk line')
        return None

    def if_statement(self, line):
        self.next()
        branches = []
        cond = self.condition()
        self.skip_line('junk after if')
        body = self.block(('elseif', 'else', 'endif', 'end'))
        branches.append((cond, body))
        otherwise = None
        while True:
            t = self.peek()
            if self.is_word(t, 'elseif'):
                self.next()
                cond = self.condition()
                self.skip_line('junk after elseif')
                body = self.block(('elseif', 'else', 'endif', 'end'))
                branches.append((cond, body))
                continue
            if self.is_word(t, 'else'):
                self.next()
                # "else if" on one line is not an elseif in the original: the rest of the line is junk
                self.skip_line('junk after else')
                body = self.block(('elseif', 'else', 'endif', 'end'))
                if otherwise is None:
                    otherwise = body
                else:
                    self.warnings.append('line %d: a second else' % t.line)
                    otherwise += body
                continue
            if self.is_word(t, 'endif'):
                self.next(); self.skip_line('junk after endif')
            else:
                self.warnings.append('line %d: if without endif' % line)
            return ('if', line, branches, otherwise or [])

    def set_statement(self):
        line = self.next().line
        t = self.peek()
        if t.kind == 'name' and not (self.peek(1).kind == 'op' and self.peek(1).value in ('.', '->')) \
                and t.value.casefold() not in self.locals and t.value.casefold() not in self.globals:
            # OpenMW (lineparser.cpp): an unknown variable in 'set' is a warning and the line is skipped
            self.skip_line()
            self.warnings.append('line %d: set of an unknown variable %r: line skipped' % (line, t.value))
            return None
        target = self.lvalue()
        if self.is_word(self.peek(), 'to'):
            self.next()
        else:
            self.warn('set without to')
        value = self.expression()
        self.skip_line('junk after set')
        return ('set', line, target, value)

    def lvalue(self):
        t = self.next()
        if t.kind != 'name':
            raise ParseError('line %d: set needs a variable' % t.line)
        if self.peek().kind == 'op' and self.peek().value in ('.', '->'):
            self.next()
            member = self.next()
            if member.kind != 'name':
                raise ParseError('line %d: member needs a name' % t.line)
            return ('member', t.value, member.value)
        name = t.value.casefold()
        if name in self.locals:
            return ('local', name)
        if name in self.globals:
            return ('global', name)
        raise ParseError('line %d: unknown variable %r' % (t.line, t.value))

    def messagebox(self, line):
        self.next()
        if self.at_eol():
            raise ParseError('line %d: messagebox without text' % line)
        fmt = self.next()
        args, buttons = [], []
        while not self.at_eol():
            t = self.peek()
            if t.kind == 'name' and t.quoted:
                buttons.append(self.next().value); continue
            if t.kind == 'name' and (t.value.casefold() in self.locals or t.value.casefold() in self.globals
                                     or (self.peek(1).kind == 'op' and self.peek(1).value == '.')):
                args.append(self.primary()); continue
            if t.kind in ('int', 'float'):
                args.append(self.primary()); continue
            if t.kind == 'name':   # a bare button word
                buttons.append(self.next().value); continue
            self.next()
            self.warnings.append('line %d: junk in a messagebox' % line)
        self.skip_line()
        self.used.append('messagebox')
        return ('do', line, ('call', None, 'messagebox', [('str', fmt.value)] + args + [('str', b) for b in buttons],
                             {'format': fmt.value, 'nargs': len(args), 'buttons': buttons}))

    # --- expressions ---
    def condition(self):
        return self.expression()

    def expression(self):
        left = self.arith()
        t = self.peek()
        if t.kind == 'op' and t.value in ('==', '!=', '<', '<=', '>', '>='):
            self.next()
            right = self.arith()
            left = ('cmp', t.value, left, right)
            t = self.peek()
            if t.kind == 'op' and t.value in ('==', '!=', '<', '<=', '>', '>='):
                raise ParseError('line %d: chained comparison' % t.line)
        return left

    def arith(self):
        left = self.term()
        while self.peek().kind == 'op' and self.peek().value in ('+', '-'):
            op = self.next().value
            left = ('bin', op, left, self.term())
        return left

    def term(self):
        left = self.factor()
        while self.peek().kind == 'op' and self.peek().value in ('*', '/'):
            op = self.next().value
            left = ('bin', op, left, self.factor())
        return left

    def factor(self):
        t = self.peek()
        if t.kind == 'op' and t.value == '-':
            self.next()
            inner = self.factor()
            if inner[0] in ('int', 'float'):
                return (inner[0], -inner[1])
            return ('neg', inner)
        if t.kind == 'op' and t.value == '+':
            self.next()
            return self.factor()
        return self.primary()

    def primary(self):
        t = self.peek()
        if t.kind == 'int':
            self.next(); return ('int', t.value)
        if t.kind == 'float':
            self.next(); return ('float', t.value)
        if t.kind == 'op' and t.value == '(':
            self.next()
            inner = self.expression()
            if self.peek().kind == 'op' and self.peek().value == ')':
                self.next()
            else:
                self.warn('missing )')
            return inner
        if t.kind == 'name':
            nxt = self.peek(1)
            if nxt.kind == 'op' and nxt.value == '->':
                ref = self.next().value; self.next()
                if self.peek().kind == 'op' and self.peek().value == '(':
                    # 'id->( OnDeath == 1 )': the reference applies to the calls inside the brackets
                    outer, self.ref = getattr(self, 'ref', None), ref
                    try:
                        return self.primary()
                    finally:
                        self.ref = outer
                if self.peek().kind != 'name' or not lookup(self.peek().value):
                    raise ParseError('line %d: -> needs a function' % t.line)
                return self.call(ref)
            if nxt.kind == 'op' and nxt.value == '.':
                self.next(); self.next()
                member = self.peek()
                if member.kind != 'name':
                    self.warnings.append('line %d: a member without a name reads 0' % t.line)
                    return ('int', 0)
                self.next()
                return ('member', t.value, member.value)
            name = t.value.casefold()
            if not t.quoted and name in self.locals:
                self.next(); return ('local', name)
            if not t.quoted and lookup(name) and name not in KEYWORDS:
                return self.call(getattr(self, 'ref', None))
            if name in self.globals:
                self.next(); return ('global', name)
            raise ParseError('line %d: unknown name %r' % (t.line, t.value))
        raise ParseError('line %d: expected a value, found %r' % (t.line, t.value))

    def numeric_argument(self):
        """One numeric argument: a signed number, a variable, a member or a bracketed expression."""
        t = self.peek()
        if t.kind == 'op' and t.value == '-':
            self.next()
            inner = self.numeric_argument()
            return (inner[0], -inner[1]) if inner[0] in ('int', 'float') else ('neg', inner)
        return self.primary()

    def starts_numeric(self, k=0):
        t = self.peek(k)
        if t.kind in ('int', 'float'):
            return True
        if t.kind == 'op' and t.value == '(':
            return True
        if t.kind == 'op' and t.value == '-':
            return self.starts_numeric(k + 1)
        if t.kind == 'name':
            name = t.value.casefold()
            nxt = self.peek(k + 1)
            if nxt.kind == 'op' and nxt.value == '.':
                return True
            return name in self.locals or name in self.globals or (not t.quoted and bool(lookup(name))
                                                                  and not lookup(name).args.split('/')[0])
        return False

    def starts_string(self):
        t = self.peek()
        if t.kind == 'name':
            return t.quoted or not (t.value.casefold() in KEYWORDS)
        if t.kind == 'int':   # a bare id made of digits
            return True
        return False

    def call(self, ref):
        t = self.next()
        fn = lookup(t.value)
        self.used.append(fn.name)
        args = []
        spec = fn.args
        optional = False
        if fn.name == 'positioncell' and self.peek().kind == 'name' and self.peek().quoted \
                and self.peek().value.casefold() not in self.locals:
            # the cell name written first ('PositionCell "Raven Rock, Bar" x y z r', Bloodmoon): read it, then
            # the numbers, as if written in the documented order
            cell = self.next().value
            numbers = [self.numeric_argument() for _ in range(4) if self.starts_numeric()]
            self.warnings.append('line %d: %s with the cell name first' % (t.line, fn.name))
            return ('call', ref, fn.name, numbers + [('str', cell)], None)
        for letter in spec:
            if letter == '/':
                optional = True; continue
            if letter in 'cS':
                if optional and (self.at_eol() or not self.starts_string() or self.peek().kind == 'op'):
                    break
                if self.at_eol():
                    raise ParseError('line %d: %s needs a string argument' % (t.line, fn.name))
                a = self.next()
                if a.kind == 'name' and self.peek().kind == 'op' and self.peek().value == '.' \
                        and self.peek(1).kind == 'name' and letter == 'S' and not a.quoted:
                    # a path written without quotes ("Vo\\x.mp3" never is; ids with dots are)
                    pass
                args.append(('str', str(a.value)))
            elif letter in 'lsf':
                if optional and (self.at_eol() or not self.starts_numeric()):
                    break
                if self.at_eol():
                    raise ParseError('line %d: %s needs a number' % (t.line, fn.name))
                args.append(self.numeric_argument())
            elif letter in 'xXz':
                if self.at_eol():
                    continue
                if letter == 'x' and self.starts_string() and self.peek().kind == 'name' \
                        and not lookup(self.peek().value) and not (self.peek().value.casefold() in KEYWORDS):
                    self.next(); self.warnings.append('line %d: ignored argument to %s' % (t.line, fn.name))
                elif letter == 'X' and self.starts_numeric():
                    self.numeric_argument(); self.warnings.append('line %d: ignored argument to %s' % (t.line, fn.name))
                elif letter == 'z' and (self.starts_numeric() or (self.peek().kind == 'name' and self.peek().quoted)):
                    self.next(); self.warnings.append('line %d: ignored argument to %s' % (t.line, fn.name))
            elif letter == 'j':
                if not self.at_eol() and self.peek().kind == 'op' and self.peek().value == '.':
                    self.next()
        return ('call', ref, fn.name, args, None)


def parse(text, globals_=None, scripts=None):
    """(tree, parser) of one script's text. Raises ParseError/LexError."""
    p = Parser(text, globals_, scripts)
    return p.script(), p
