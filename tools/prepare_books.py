#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""The book texts (BOOK-READER-58): what the reader shows when a book, scroll or letter is read where it lies.

Every live BOOK record of the base master WITHOUT an enchantment (a magic scroll is taken, never read; the focus
table marks it, tools/prepare_focus.py ACT_MAGIC_SCROLL): its display name and its TEXT. The game's HTML-like markup
is reduced to plain text: <BR> ends a line, <P> and </P> start a paragraph (a blank line), <DIV> starts a line,
<FONT> and other tags are dropped, character references are decoded, and a picture (<IMG>) becomes the line
"[picture]". Runs of blank lines are cut to one and spaces inside a line to one. The engine lays the text out into
pages (aw_reader.c); a form feed (12) in the text would start a new page (not written by this stage today).

The output is private game text: id1/books.awb, read on demand by record id; only the open book is held in memory.

Format AWB1 (little-endian):
  "AWB1" u32 books
  char take[16], char close[16]   the reader's button words, GMST sTake and sClose (NUL-padded printable ASCII;
                                  empty when the game data has none: the engine then says "Take" and "Close")
  books x { char id[32] (the record id, folded, NUL-padded), u32 offset (from the file start), u32 length }
          ascending id (byte order)
  the texts: cp1252, each "title\\n" then the body; no NUL; a text define the engine knows is written as byte 1 and
  1 + its number (tools/text_defines.py, engine/aga/src/aw_textdef.c), the rest as written
A book whose id does not fit 32 printable bytes, or whose text is longer than MAX_TEXT, is left out (reported).
A stage of its own, depending on nothing: no other stage's input or cache key changes.
"""
import argparse, hashlib, html, json, re, struct, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from mwad.esm import records, subrecords, string, first
from mwad.paths import resolve_data_files, child_ci
sys.path.insert(0, str(ROOT / 'tools'))
import text_defines   # tools/text_defines.py

IDENT = 32
MAX_TEXT = 40000        # bytes per book: the engine's bound (aw_reader.c BOOK_TEXT; the longest is about 39 KB)
TITLE = 95              # the reader's title line (aw_reader.c title[96])
PICTURE = '[picture]'

_TAG = re.compile(r'<\s*(/?)\s*([a-zA-Z]+)[^>]*>')


def reduce_markup(source):
    """The book's markup as plain text with line breaks; returns (text, pictures)."""
    parts, pictures, at = [], 0, 0
    source = source.replace('\r\n', '\n').replace('\r', '\n').replace('\n', ' ')
    for match in _TAG.finditer(source):
        parts.append(html.unescape(source[at:match.start()]))
        at = match.end()
        tag = match.group(2).lower()
        if tag == 'br':
            parts.append('\n')
        elif tag == 'p':
            parts.append('\n\n')
        elif tag == 'div' and not match.group(1):
            parts.append('\n')
        elif tag == 'img':
            pictures += 1
            parts.append('\n' + PICTURE + '\n')
    parts.append(html.unescape(source[at:]))
    lines = [re.sub(r'[ \t\xa0]+', ' ', line).strip() for line in ''.join(parts).split('\n')]
    text = re.sub(r'\n{3,}', '\n\n', '\n'.join(lines)).strip('\n')
    text = ''.join(c for c in text if c == '\n' or ord(c) >= 32)
    return text, pictures


LABEL = 16
LABELS = ('sTake', 'sClose')


def label(word):
    """A button word as the header keeps it: printable ASCII that fits, else empty (the engine's own word)."""
    raw = word.encode('ascii', 'replace') if isinstance(word, str) else b''
    if len(raw) >= LABEL or any(b < 32 or b > 126 for b in raw):
        raw = b''
    return raw + b'\0' * (LABEL - len(raw))


def labels_of(raw):
    """{GMST name: string value} of the reader's button words (sTake, sClose)."""
    want, out = {name.casefold(): name for name in LABELS}, {}
    for tag, flags, payload in records(raw):
        if tag != 'GMST' or flags & 0x20:
            continue
        fields = list(subrecords(payload))
        name = string(first(fields, 'NAME'), 'NAME', errors='replace').casefold()
        if name in want and first(fields, 'STRV'):
            out[want[name]] = string(first(fields, 'STRV'), 'STRV', errors='replace').strip()
    return out


def books_of(raw):
    """[(folded id, title, text, pictures)] of every readable book (no enchantment), and the magic scroll count."""
    out, scrolls = [], 0
    for tag, flags, payload in records(raw):
        if tag != 'BOOK':
            continue
        fields = list(subrecords(payload))
        if flags & 0x20 or any(k == 'DELE' for k, _ in fields):
            continue
        if first(fields, 'ENAM'):
            scrolls += 1
            continue
        ident = string(first(fields, 'NAME'), 'NAME', errors='replace').casefold()
        title = string(first(fields, 'FNAM'), 'FNAM', errors='replace') if first(fields, 'FNAM') else ''
        source = string(first(fields, 'TEXT'), 'TEXT', errors='replace') if first(fields, 'TEXT') else ''
        text, pictures = reduce_markup(source)
        text, _ = text_defines.encode(text)     # %PCName ... as the engine's codes (BOOK-TEXT-MACROS-58)
        out.append((ident, title.strip(), text, pictures))
    return out, scrolls


def encode(books, words=None):
    """The AWB1 file and what was left out: {id: reason}. WORDS: {GMST name: value} for the button words."""
    words = words or {}
    rows, left = [], {}
    for ident, title, text, _ in books:
        key = ident.encode('ascii', 'replace')
        if not key or len(key) > IDENT or any(b < 32 or b > 126 for b in key):
            left[ident] = 'id'
            continue
        body = (title.encode('cp1252', 'replace')[:TITLE] + b'\n' + text.encode('cp1252', 'replace'))
        if len(body) > MAX_TEXT:
            left[ident] = 'length %d' % len(body)
            continue
        rows.append((key, body))
    rows.sort()
    head = 8 + 2 * LABEL + len(rows) * (IDENT + 8)
    index, blobs, offset = [], [], head
    for key, body in rows:
        index.append(key + b'\0' * (IDENT - len(key)) + struct.pack('<II', offset, len(body)))
        blobs.append(body)
        offset += len(body)
    return (b'AWB1' + struct.pack('<I', len(rows)) + label(words.get('sTake')) + label(words.get('sClose')) +
            b''.join(index) + b''.join(blobs)), left


def build(data_files):
    data = resolve_data_files(Path(data_files))
    master = child_ci(data, 'Morrowind.esm').read_bytes()
    books, scrolls = books_of(master)
    words = labels_of(master)
    payload, left = encode(books, words)
    longest = max((len(t.encode('cp1252', 'replace')) for _, _, t, _ in books), default=0)
    report = {'format': 'AWB1', 'books': len(books) - len(left), 'left_out': left,
              'magic_scrolls_not_read': scrolls, 'words': words,
              'books_with_pictures': sum(1 for b in books if b[3]),
              'pictures': sum(b[3] for b in books), 'longest_text': longest,
              'bytes': len(payload), 'sha256': hashlib.sha256(payload).hexdigest(),
              'master_sha256': hashlib.sha256(master).hexdigest()}
    return payload, report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data-files', required=True, type=Path)
    p.add_argument('--out', required=True, type=Path)
    a = p.parse_args()
    payload, report = build(a.data_files)
    (a.out / 'id1').mkdir(parents=True, exist_ok=True)
    (a.out / 'id1/books.awb').write_bytes(payload)
    (a.out / 'books-receipt.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8', newline='\n')
    print('[books] %d readable books (%d with pictures, %d left out), %d bytes' %
          (report['books'], report['books_with_pictures'], len(report['left_out']), report['bytes']), flush=True)


if __name__ == '__main__':
    main()
