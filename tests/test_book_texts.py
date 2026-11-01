"""The book texts stage (BOOK-READER-58): tools/prepare_books.py on hand-made records (no game data), its place in
the build (a stage of its own beside the focus table, depending on nothing, read by the image only) and the engine
side (aw_reader.c reads books.awb by record id; the hook switches "E: Read" on)."""
import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'src'))


def sub(tag, data):
    return tag.encode('ascii') + struct.pack('<I', len(data)) + data


def record(tag, *fields, flags=0):
    body = b''.join(fields)
    return tag.encode('ascii') + struct.pack('<IiI', len(body), 0, flags) + body


def book(ident, name, text, enchant=b''):
    fields = [sub('NAME', ident + b'\0'), sub('FNAM', name + b'\0'), sub('BKDT', struct.pack('<fiiii', 1, 5, 0, -1, 0)),
              sub('TEXT', text)]
    if enchant:
        fields.append(sub('ENAM', enchant + b'\0'))
    return record('BOOK', *fields)


def gmst(name, value):
    return record('GMST', sub('NAME', name + b'\0'), sub('STRV', value))


def entries(payload):
    count = struct.unpack_from('<I', payload, 4)[0]
    out = {}
    for i in range(count):
        e = payload[40 + 40 * i: 80 + 40 * i]
        offset, length = struct.unpack_from('<II', e, 32)
        out[e[:32].rstrip(b'\0').decode()] = payload[offset:offset + length]
    return out


class BookStageTests(unittest.TestCase):
    def test_markup_reduced_to_lines_and_pictures(self):
        import prepare_books
        text, pictures = prepare_books.reduce_markup(
            '<DIV ALIGN="CENTER"><FONT COLOR="000000" SIZE="3" FACE="Magic Cards">Title<BR>by Someone<P>'
            'First  line &amp; more.<BR>\r\n<IMG SRC="tx_menubook_firmament.dds" WIDTH="200" HEIGHT="100"><BR>End</FONT>')
        self.assertEqual(pictures, 1)
        self.assertEqual(text, 'Title\nby Someone\n\nFirst line & more.\n\n[picture]\n\nEnd')
        self.assertNotIn('<', text)

    def test_readable_books_only_sorted_with_words(self):
        import prepare_books
        raw = (record('TES3', sub('HEDR', b'\0' * 300)) + gmst(b'sTake', b'Take') + gmst(b'sClose', b'Close') +
               book(b'bk_Zeta', b'Zeta', b'Z<BR>text') + book(b'bk_alpha', b'Alpha', b'A text') +
               book(b'sc_magic', b'Magic Scroll', b'words', enchant=b'sc_ench'))
        books, scrolls = prepare_books.books_of(raw)
        self.assertEqual(scrolls, 1)
        payload, left = prepare_books.encode(books, prepare_books.labels_of(raw))
        self.assertEqual(left, {})
        self.assertEqual(payload[:4], b'AWB1')
        self.assertEqual(payload[8:24].rstrip(b'\0'), b'Take')
        self.assertEqual(payload[24:40].rstrip(b'\0'), b'Close')
        found = entries(payload)
        self.assertEqual(list(found), ['bk_alpha', 'bk_zeta'])         # folded, byte order (the engine's search)
        self.assertEqual(found['bk_zeta'], b'Zeta\nZ\ntext')
        self.assertNotIn(b'\0', b''.join(found.values()))

    def test_overlong_book_is_left_out(self):
        import prepare_books
        payload, left = prepare_books.encode([('bk_long', 'Long', 'x' * prepare_books.MAX_TEXT, 0)])
        self.assertIn('bk_long', left)
        self.assertEqual(struct.unpack_from('<I', payload, 4)[0], 0)

    def test_a_stage_of_its_own_read_by_the_image_only(self):
        import build_parallel
        self.assertEqual(build_parallel.DEPENDENCIES['books'], ())
        for name, deps in build_parallel.DEPENDENCIES.items():
            if name != 'image':
                self.assertNotIn('books', deps, name)
        source = (ROOT / 'tools/build.py').read_text(encoding='utf-8')
        self.assertIn("('books', tool('prepare_books.py', '--data-files', args.data_files, '--out', run / 'books'))",
                      source)
        self.assertIn("if name == 'image' and 'books' in names:",
                      (ROOT / 'tools/build_parallel.py').read_text(encoding='utf-8'))

    def test_engine_reads_by_id_and_switches_read_on(self):
        reader = (ROOT / 'engine/aga/src/aw_reader.c').read_text(encoding='utf-8')
        self.assertIn('COM_FOpenFile("books.awb",&f)', reader)
        self.assertIn('if(!aw_book_reader)aw_book_reader=book_open;', reader)
        self.assertIn('book=(char *)AW_TryMalloc(size+1)', reader)          # only the open book is held
        self.assertIn('#define BOOK_TEXT 40000', reader)
        inventory = (ROOT / 'engine/aga/src/aw_inventory.c').read_text(encoding='utf-8')
        self.assertIn('(row->action&3)==FOCUS_ACT_READ && aw_book_reader && aw_book_reader(row->reference)', inventory)


if __name__ == '__main__':
    unittest.main()
