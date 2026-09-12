from pathlib import Path
import sqlite3
import tempfile
import unittest

from docsearch import chunks, render_html, search, sync


class SearchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.docs = self.base / 'docs'
        self.docs.mkdir()
        self.db = self.base / 'search.db'
        (self.docs / 'one.md').write_text('# Worker leases\nA job uses a lease token.\n\n## Recovery\nRetry safely.\n')

    def test_search_returns_source_and_line_range(self):
        sync(self.docs, self.db)
        result = search(self.db, 'lease token')
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['path'], 'one.md')
        self.assertEqual((result[0]['start_line'], result[0]['end_line']), (1, 3))
        self.assertIn('[lease]', result[0]['excerpt'])

    def test_incremental_update_and_delete(self):
        self.assertEqual(sync(self.docs, self.db)['updated'], 1)
        self.assertEqual(sync(self.docs, self.db)['unchanged'], 1)
        (self.docs / 'one.md').write_text('# Database\nAtomic commit.\n')
        self.assertEqual(sync(self.docs, self.db)['updated'], 1)
        self.assertEqual(search(self.db, 'lease'), [])
        self.assertEqual(len(search(self.db, 'commit')), 1)
        (self.docs / 'one.md').unlink()
        self.assertEqual(sync(self.docs, self.db)['deleted'], 1)
        self.assertEqual(search(self.db, 'commit'), [])

    def test_hidden_vendor_and_symlinks_excluded(self):
        for directory in ('.private', 'node_modules'):
            folder = self.docs / directory
            folder.mkdir()
            (folder / 'secret.md').write_text('confidential token')
        (self.base / 'outside.md').write_text('confidential token')
        (self.docs / 'link.md').symlink_to(self.base / 'outside.md')
        (self.docs / '.env.txt').write_text('confidential token')
        sync(self.docs, self.db)
        self.assertEqual(search(self.db, 'confidential'), [])

    def test_changed_root_rejected_preserves_existing_index(self):
        sync(self.docs, self.db)
        with self.assertRaises(ValueError):
            sync(self.base, self.db)
        self.assertEqual(len(search(self.db, 'token')), 1)

    def test_fts_special_characters_are_literal_and_html_is_escaped(self):
        sync(self.docs, self.db)
        self.assertEqual(search(self.db, '" OR *'), [])
        output = render_html('<script>alert(1)</script>', search(self.db, 'lease'))
        self.assertNotIn('<script>', output)
        self.assertIn('&lt;script&gt;', output)

    def test_empty_query_limits_and_unicode(self):
        (self.docs / 'unicode.md').write_text('# Café\nRésumé café.\n', encoding='utf-8')
        sync(self.docs, self.db)
        self.assertEqual(search(self.db, ''), [])
        self.assertEqual(len(search(self.db, 'café')), 1)
        with self.assertRaises(ValueError):
            search(self.db, 'token', 0)

    def test_line_chunks_have_no_gaps(self):
        text = '\n'.join(str(i) for i in range(125))
        parts = list(chunks(text))
        self.assertEqual([(p[2], p[3]) for p in parts], [(1, 60), (61, 120), (121, 125)])

    def test_binary_and_oversized_files_removed_from_index(self):
        sync(self.docs, self.db)
        (self.docs / 'one.md').write_bytes(b'\xff')
        (self.docs / 'huge.md').write_bytes(b'x' * (1024 * 1024 + 1))
        result = sync(self.docs, self.db)
        self.assertEqual(len(result['excluded']), 2)
        self.assertEqual(search(self.db, 'token'), [])

    def test_storage_failure_rolls_back_old_index(self):
        sync(self.docs, self.db)
        with sqlite3.connect(self.db) as db:
            db.execute("""CREATE TRIGGER block_change BEFORE UPDATE ON documents
                BEGIN SELECT RAISE(ABORT, 'simulated storage failure'); END""")
        (self.docs / 'one.md').write_text('# Replacement\nUncommitted text.\n')
        with self.assertRaises(sqlite3.IntegrityError):
            sync(self.docs, self.db)
        self.assertEqual(len(search(self.db, 'token')), 1)
        self.assertEqual(search(self.db, 'uncommitted'), [])


if __name__ == '__main__':
    unittest.main()
