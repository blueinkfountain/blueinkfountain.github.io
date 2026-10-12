"""Check rendered local links and ensure developer files are not published."""
import argparse
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit, unquote


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if key in ('href', 'src') and value:
                self.links.append(value)


def check_build(root):
    root = Path(root)
    if not (root / 'index.html').exists():
        return ['Built site has no index.html; run Jekyll first.']
    files = {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
    errors = []
    forbidden = ('scripts/', 'tests/', 'maintenance/', 'untexed/', 'ode_lab',
                 'daily_record_note/', 'vendor/', '.archive/', '.venv/')
    for name in files:
        if name.startswith(forbidden) or '.before-' in name:
            errors.append(f'Development file published: {name}')
        if not name.endswith('.html'):
            continue
        parser = Links()
        parser.feed((root / name).read_text(encoding='utf-8'))
        for link in parser.links:
            url = urlsplit(urljoin('/' + name, link))
            if url.scheme not in ('', 'http', 'https') or url.netloc not in ('', 'blueinkfountain.github.io'):
                continue
            target = unquote(url.path).lstrip('/')
            if not target or target.endswith('/'):
                target += 'index.html'
            if target not in files:
                errors.append(f'{name}: missing published target: {target}')
    return sorted(set(errors))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', nargs='?', type=Path, default=Path('_site'))
    args = parser.parse_args()
    errors = check_build(args.directory)
    if errors:
        print('\n'.join(errors))
        return 1
    print('Built-site validation passed: local links and publication boundaries.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
