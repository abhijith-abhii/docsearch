"""Incrementally index local documentation and return source-linked search results."""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
from pathlib import Path
import re
import sqlite3


EXCLUDED = {'.git', '.venv', 'venv', 'node_modules', '__pycache__', 'var', '.next', 'dist', 'build'}
SUFFIXES = {'.md', '.txt', '.rst'}
MAX_BYTES = 1024 * 1024
DDL = """
CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS documents (
    path TEXT PRIMARY KEY, digest TEXT NOT NULL, lines INTEGER NOT NULL
);
CREATE VIRTUAL TABLE IF NOT EXISTS passages USING fts5(
    path UNINDEXED, heading, body, start_line UNINDEXED, end_line UNINDEXED,
    tokenize='unicode61'
);
"""


def chunks(text, max_lines=60):
    lines = text.splitlines()
    title, section, start = 'Document', [], 1
    for number, line in enumerate(lines, 1):
        heading = re.match(r'^#{1,6}\s+(.+?)\s*#*$', line)
        if heading or len(section) >= max_lines:
            if section and any(s.strip() for s in section):
                yield title, '\n'.join(section), start, number - 1
            section, start = [], number
            if heading:
                title = heading.group(1)
        section.append(line)
    if section and any(s.strip() for s in section):
        yield title, '\n'.join(section), start, len(lines)


def walk_docs(root):
    def fail_on_walk_error(error):
        raise error
    for parent, dirs, files in os.walk(root, followlinks=False, onerror=fail_on_walk_error):
        dirs[:] = sorted(d for d in dirs if d not in EXCLUDED and not d.startswith('.')
                         and not (Path(parent) / d).is_symlink())
        for name in sorted(files):
            file = Path(parent) / name
            if file.suffix.lower() in SUFFIXES and not name.startswith('.') and not file.is_symlink():
                yield file


def sync(root, database):
    root = Path(root).resolve()
    if not root.is_dir():
        raise ValueError('documentation root must be a directory')
    Path(database).parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(database, timeout=10)
    try:
        db.executescript(DDL)
        db.execute('BEGIN IMMEDIATE')
        existing_root = db.execute("SELECT value FROM metadata WHERE key='root'").fetchone()
        if existing_root and existing_root[0] != str(root):
            raise ValueError('index belongs to another root; use a separate database')
        db.execute("INSERT OR IGNORE INTO metadata VALUES ('root',?)", (str(root),))
        old = dict(db.execute('SELECT path,digest FROM documents'))
        seen, excluded = set(), []
        result = {'updated': 0, 'unchanged': 0, 'deleted': 0, 'excluded': excluded}
        for file in walk_docs(root):
            path = file.relative_to(root).as_posix()
            # Stop indexing files that no longer meet policy, even if indexed before.
            if file.stat().st_size > MAX_BYTES:
                excluded.append({'path': path, 'reason': 'larger than 1 MiB'})
                continue
            raw = file.read_bytes()
            try:
                text = raw.decode('utf-8')
            except UnicodeDecodeError:
                excluded.append({'path': path, 'reason': 'not UTF-8'})
                continue
            if '\x00' in text:
                excluded.append({'path': path, 'reason': 'contains null bytes'})
                continue
            digest = hashlib.sha256(raw).hexdigest()
            seen.add(path)
            if old.get(path) == digest:
                result['unchanged'] += 1
                continue
            db.execute('DELETE FROM passages WHERE path=?', (path,))
            db.execute('''INSERT INTO documents VALUES (?,?,?) ON CONFLICT(path)
                DO UPDATE SET digest=excluded.digest, lines=excluded.lines''',
                       (path, digest, len(text.splitlines())))
            db.executemany('INSERT INTO passages VALUES (?,?,?,?,?)', [
                (path, heading, body, first, last) for heading, body, first, last in chunks(text)
            ])
            result['updated'] += 1
        for removed in old.keys() - seen:
            db.execute('DELETE FROM documents WHERE path=?', (removed,))
            db.execute('DELETE FROM passages WHERE path=?', (removed,))
            result['deleted'] += 1
        db.commit()
        return result
    except BaseException:
        db.rollback()
        raise
    finally:
        db.close()


def search(database, query, limit=10):
    if not 1 <= limit <= 100:
        raise ValueError('limit must be between 1 and 100')
    terms = re.findall(r'[^\W_]+', query, flags=re.UNICODE)
    if not terms:
        return []
    if len(terms) > 32 or len(query) > 1000:
        raise ValueError('query exceeds 32 terms or 1000 characters')
    # Quoted literal terms prevent user text from becoming FTS query syntax.
    match = ' AND '.join('"' + term + '"' for term in terms)
    db = sqlite3.connect(Path(database).resolve().as_uri() + '?mode=ro', uri=True)
    db.row_factory = sqlite3.Row
    try:
        root_row = db.execute("SELECT value FROM metadata WHERE key='root'").fetchone()
        if root_row is None:
            raise ValueError('index has no source root; run index first')
        root = Path(root_row[0])
        rows = db.execute('''SELECT path,heading,start_line,end_line,
            snippet(passages,2,'[',']',' … ',24) AS excerpt,
            bm25(passages,0,4,1,0,0) AS rank
            FROM passages WHERE passages MATCH ? ORDER BY rank,path,start_line LIMIT ?''',
            (match, limit)).fetchall()
        output = []
        for row in rows:
            item = dict(row)
            item['start_line'], item['end_line'] = int(item['start_line']), int(item['end_line'])
            item['source_uri'] = (root / item['path']).as_uri()
            output.append(item)
        return output
    finally:
        db.close()


def render_html(query, results):
    escape = html.escape
    cards = []
    for item in results:
        cards.append(f'''<article><h2>{escape(item['heading'])}</h2>
          <p class="source"><a href="{escape(item['source_uri'], quote=True)}">{escape(item['path'])}</a>
          · lines {item['start_line']}–{item['end_line']}</p>
          <p class="excerpt">{escape(item['excerpt'])}</p></article>''')
    return f'''<!doctype html><html lang="en"><meta charset="utf-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>DocSearch results</title><style>
    :root{{font-family:system-ui,sans-serif;color:#162235;background:#f4f7fb}}
    body{{max-width:820px;margin:48px auto;padding:0 24px}}
    header{{border-top:5px solid #2866c7;padding-top:24px;margin-bottom:32px}}
    h1{{font-size:36px;letter-spacing:-1px;margin:10px 0}}h2{{font-size:21px;margin:0 0 8px}}
    .label{{color:#2866c7;font-weight:650;font-size:13px;letter-spacing:2px}}
    article{{background:white;border:1px solid #d8e1ec;border-radius:10px;padding:24px;margin:18px 0}}
    .source{{font-size:13px;color:#55667b}}a{{color:#245eb5}}.excerpt{{line-height:1.65;white-space:pre-wrap}}
    footer{{color:#55667b;font-size:13px;line-height:1.6}}
    </style><header><div class="label">DOCSEARCH / LOCAL KNOWLEDGE</div>
    <h1>{escape(query)}</h1><p>{len(results)} matching passages from your local index</p></header>
    <main>{''.join(cards) or '<p>No matching passages. Try fewer terms.</p>'}</main>
    <footer>Keyword search ranked with SQLite FTS5 BM25. Brackets mark matches.
    Source lines refer to the indexed snapshot; reindex after editing files.
    Source links open local files and do not navigate to a specific line.
    This export contains local file paths and excerpts; review before sharing.</footer></html>'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', default='var/search.db')
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('index').add_argument('directory')
    query = commands.add_parser('search')
    query.add_argument('query')
    query.add_argument('--limit', type=int, default=10)
    query.add_argument('--html', help='also save an offline HTML report')
    args = parser.parse_args()
    try:
        if args.command == 'index':
            result = sync(args.directory, args.db)
        else:
            result = search(args.db, args.query, args.limit)
            if args.html:
                Path(args.html).parent.mkdir(parents=True, exist_ok=True)
                Path(args.html).write_text(render_html(args.query, result), encoding='utf-8')
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except (ValueError, OSError, sqlite3.Error) as error:
        parser.exit(2, f'Error: {error}\n')


if __name__ == '__main__':
    main()
