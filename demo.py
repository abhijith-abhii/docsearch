"""Create an offline HTML search report from synthetic documentation."""
import json
from pathlib import Path
import tempfile
from docsearch import render_html, search, sync


def main():
    root = Path(__file__).parent
    with tempfile.TemporaryDirectory() as folder:
        db = Path(folder) / 'demo.db'
        first = sync(root / 'examples/docs', db)
        second = sync(root / 'examples/docs', db)
        results = search(db, 'transaction')
        expected_documents = len(list((root / 'examples/docs').rglob('*.md')))
        assert first['updated'] == expected_documents and second['unchanged'] == expected_documents
        assert len(results) >= 4
        assert any(item['path'] == 'backups.md' for item in results)
        target = root / 'var/demo.html'
        target.parent.mkdir(exist_ok=True)
        target.write_text(render_html('transaction', results), encoding='utf-8')
        print(json.dumps({'indexed_documents': first['updated'], 'unchanged_on_second_run': second['unchanged'],
                          'matching_passages': len(results), 'html': 'var/demo.html'}, indent=2))


if __name__ == '__main__':
    main()
