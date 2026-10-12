"""Validate local content and URLs with Linux-style case sensitivity."""
import argparse
from collections import defaultdict
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit, parse_qs
import yaml


def page_data(path):
    text = path.read_text(encoding='utf-8')
    match = re.match(r'\A---\s*\n(.*?)\n---(?:\n|$)', text, re.S)
    if not match:
        raise ValueError('missing or malformed YAML front matter')
    data = yaml.safe_load(match[1]) or {}
    if not isinstance(data, dict):
        raise ValueError('front matter must be a mapping')
    return data, text[match.end():]


def check_site(root):
    root = Path(root)
    errors, pages = [], []
    paths = sorted([*root.glob('*.md'), *root.glob('docs/**/*.md'), *root.glob('docs/**/*.html')])
    paths = [p for p in paths if p.name != 'README.md']
    files = {p.relative_to(root).as_posix() for directory in ('docs', 'assets', 'untexed-current')
             for p in (root / directory).rglob('*') if p.is_file()}
    files.update(p.name for p in root.iterdir() if p.is_file())
    urls = set('/' + p for p in files)
    titles = defaultdict(list)
    for path in paths:
        label = path.relative_to(root).as_posix()
        if any(ord(c) < 32 or ord(c) == 127 for c in label):
            errors.append(f'{label!r}: control character in filename')
        try:
            data, body = page_data(path)
        except (ValueError, yaml.YAMLError) as exc:
            errors.append(f'{label}: {exc}')
            continue
        titles[data.get('title')].append(data)
        pages.append((label, data, re.sub(r'<!--[\s\S]*?-->', '', body)))
        urls.add('/' + str(Path(label).with_suffix('.html')))
        if data.get('permalink'):
            urls.add(unquote(data['permalink']))
        if label == 'index.md':
            urls.add('/')
    for label, data, body in pages:
        parent = data.get('parent')
        if parent and parent not in titles:
            errors.append(f'{label}: unknown parent {parent!r}')
        if parent in titles and not any(p.get('has_children') for p in titles[parent]):
            errors.append(f'{label}: parent {parent!r} is not a navigation group')
        if data.get('layout') == 'pdf' and not data.get('pdf') and data.get('status') != 'pending':
            errors.append(f'{label}: pdf layout requires pdf or status: pending')
        trail, current = set(), data
        while current.get('parent') in titles:
            name = current['parent']
            if name in trail:
                errors.append(f'{label}: navigation parent cycle at {name!r}')
                break
            trail.add(name)
            current = titles[name][0]
        links = [data['pdf']] if data.get('pdf') else []
        links += [note.get('url', '') for note in data.get('related', [])]
        links += re.findall(r'(?:href|src)=[\"\']([^\"\']+)[\"\']', body)
        links += re.findall(r'\]\((/[^\s)]+)\)', body)
        links += re.findall(r"\{\{\s*['\"]([^'\"]+)['\"]\s*\|\s*relative_url", body)
        for target in links:
            if '{{' in target or '{%' in target:
                continue
            parts = urlsplit(target)
            if parts.netloc == 'docs.google.com' and parts.path == '/viewer':
                target = parse_qs(parts.query).get('url', [''])[0]
                parts = urlsplit(target)
            if parts.netloc and parts.netloc != 'blueinkfountain.github.io':
                continue
            if not parts.path.startswith('/'):
                continue
            local = unquote(parts.path)
            if local not in urls:
                errors.append(f'{label}: missing local target (case-sensitive): {local}')
    return sorted(set(errors))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    errors = check_site(args.root)
    if errors:
        print('\n'.join(errors))
        return 1
    print('Site validation passed: navigation, filenames and local links.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
