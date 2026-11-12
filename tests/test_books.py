"""Books persistence, approval isolation, and Hugo rendering regression tests."""
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pydantic import ValidationError
from app.backend.services import books_service as books


class BooksTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        patcher = patch.object(books, 'PROJECT_ROOT', self.root)
        self.original_root = books.PROJECT_ROOT
        patcher.start()
        self.addCleanup(patcher.stop)
        template = self.root / 'deploy/hugo-books'
        template.mkdir(parents=True)
        for filename in ('list.html', 'home.html'):
            shutil.copy(self.original_root / 'deploy/hugo-books' / filename, template / filename)
        posts = self.root / 'site/content/posts'
        posts.mkdir(parents=True)
        (posts / 'first.md').write_text('---\ntitle: Public first\ndraft: false\n---\nFirst body\n')
        (posts / 'second.md').write_text('---\ntitle: Public second\ndraft: false\n---\nSecond body\n')
        (posts / 'private.md').write_text('---\ntitle: Private\ndraft: true\n---\nPrivate body\n')
        self.document = books.BooksDocument(items=[books.Book(slug='learning', title='Learning', chapters=['second', 'private', 'first', 'missing'])])

    def save(self):
        return books.save_books(self.document, {'first', 'second', 'private', 'missing'})

    def test_save_roundtrip_and_dry_run_do_not_publish(self):
        self.save()
        self.assertEqual(books.load_books(), self.document)
        result = books.stage_books()
        self.assertEqual(result['items'][0]['chapters'], ['second', 'first'])
        self.assertEqual(len(result['excluded']), 2)
        self.assertFalse((self.root / 'site/data/books.json').exists())
        with self.assertRaises(ValueError):
            books.stage_books(dry_run=False)
        self.assertFalse((self.root / 'site/data/books.json').exists())

    def test_approved_snapshot_stays_unchanged_until_next_approval(self):
        self.save()
        before = {p.name: p.read_bytes() for p in (self.root / 'site/content/posts').glob('*')}
        books.stage_books(approve=True, dry_run=False)
        target = self.root / 'site/data/books.json'
        self.assertEqual(json.loads(target.read_text())['items'][0]['chapters'], ['second', 'first'])
        books.save_books(books.BooksDocument(), set())
        self.assertEqual(len(json.loads(target.read_text())['items']), 1)
        books.stage_books(approve=True, dry_run=False)
        self.assertEqual(json.loads(target.read_text())['items'], [])
        self.assertEqual(before, {p.name: p.read_bytes() for p in (self.root / 'site/content/posts').glob('*')})

    def test_invalid_and_duplicate_references(self):
        for chapters in (['../private'], ['first', 'first']):
            with self.assertRaises(ValidationError):
                books.Book(slug='book', title='Book', chapters=chapters)
        with self.assertRaises(ValidationError):
            books.BooksDocument(items=[self.document.items[0], self.document.items[0]])
        with self.assertRaises(ValueError):
            books.save_books(self.document, set())
        self.assertFalse((self.root / 'config/books.json').exists())

    def test_sensitive_metadata_blocks_public_snapshot(self):
        for value in ['person@example.com', 'https://secret.internal/path', '010-1234-5678', 'sk-' + 'a' * 30]:
            self.document.items[0].description = value
            self.save()
            with self.assertRaises(ValueError):
                books.stage_books(approve=True, dry_run=False)
        self.assertFalse((self.root / 'site/data/books.json').exists())

    @unittest.skipUnless(shutil.which('hugo'), 'Hugo not installed')
    def test_hugo_renders_order_and_project_base_path(self):
        self.save()
        site = self.root / 'site'
        base = site / 'layouts/_default'
        base.mkdir(parents=True)
        (base / 'baseof.html').write_text('<html><header>Blog</header>{{ block "main" . }}{{ end }}</html>')
        (base / 'single.html').write_text('{{ define "main" }}{{ .Content }}{{ end }}')
        (site / 'hugo.toml').write_text('baseURL = "https://example.org/project/"\n')
        books.stage_books(approve=True, dry_run=False)
        books.stage_books(approve=True, dry_run=False)
        self.assertEqual((base / 'baseof.html').read_text().count('books-navigation'), 1)
        proc = subprocess.run(['hugo', '--source', str(site)], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        html = (site / 'public/books/index.html').read_text()
        self.assertLess(html.index('Public second'), html.index('Public first'))
        self.assertNotIn('Private', html)
        self.assertIn('/project/posts/first/', html)
        self.assertIn('/project/books/', html)
        home = (site / 'public/index.html').read_text()
        self.assertIn('class="book-cover"', home)
        self.assertIn('/project/books/#learning', home)
        self.assertIn('2개 챕터', home)
        self.assertIn('최근 글', home)
        self.assertIn('/project/posts/first/', home)
        self.assertNotIn('Private', home)
        self.assertLess(home.index('home-books-title'), home.index('recent-posts-title'))


if __name__ == '__main__':
    unittest.main()
