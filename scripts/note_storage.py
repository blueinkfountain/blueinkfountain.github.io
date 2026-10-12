"""Local metric cache and recoverable publication of PDFs plus their YAML record."""
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import yaml


def file_digest(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_text(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=path.name + '.')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


class MetricCache:
    """Content-addressed values; missing/corrupt entries are safe cache misses."""
    def __init__(self, directory, settings):
        self.directory = Path(directory)
        self.signature = json.dumps(settings, sort_keys=True, ensure_ascii=True)

    def get(self, metric, pdf, compute):
        key = hashlib.sha256((self.signature + metric + file_digest(pdf)).encode()).hexdigest()
        path = self.directory / (key + '.json')
        try:
            item = json.loads(path.read_text())
            value = item['value']
            if item['key'] == key and ((metric == 'visual' and isinstance(value, str) and len(value) == 64)
                                      or (metric == 'total' and type(value) is int and value >= 0)):
                return value
        except (OSError, ValueError, KeyError, TypeError):
            pass
        value = compute()
        atomic_text(path, json.dumps({'key': key, 'value': value}))
        return value


@contextmanager
def build_lock(root):
    """Serialize publication and crash recovery for this local checkout."""
    path = Path(root) / '.cache' / 'notes-build.lock'
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError('Another note update is running. Try again after it finishes.') from exc
        try:
            yield
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def transaction_dir(published):
    return Path(published).parent / '.cache' / 'notes-publication'


def recover_publication(published, output):
    """Roll an interrupted transaction back before reading history. Caller holds lock."""
    published, output = Path(published), Path(output)
    transaction = transaction_dir(published)
    if not transaction.exists():
        return
    state_path = transaction / 'state.json'
    if state_path.exists():
        state = json.loads(state_path.read_text())
        if not state.get('committed'):
            old_pdfs = transaction / 'old-pdfs'
            if old_pdfs.exists():
                if published.exists():
                    shutil.rmtree(published)
                os.replace(old_pdfs, published)
            elif not state['had_pdfs'] and published.exists():
                shutil.rmtree(published)
            old_yaml = transaction / 'old.yml'
            if state['had_yaml'] and old_yaml.exists():
                # Copy instead of consuming the recovery file, so recovery is retryable.
                atomic_text(output, old_yaml.read_text(encoding='utf-8'))
            elif not state['had_yaml'] and output.exists():
                output.unlink()
    shutil.rmtree(transaction)


def publish_snapshot(source, published, output, data):
    """Stage changed PDFs, hard-link unchanged ones, then publish the PDF/YAML pair.

    A journal survives process interruption. recover_publication restores the previous
    pair at next startup. Caught I/O failures roll back immediately. Caller holds lock.
    """
    source, published, output = Path(source), Path(published), Path(output)
    recover_publication(published, output)
    pdfs = sorted(p for p in source.rglob('*') if p.is_file() and p.suffix.lower() == '.pdf')
    if not pdfs:
        raise ValueError('Refusing to publish an empty PDF snapshot')
    transaction = transaction_dir(published)
    transaction.mkdir(parents=True)
    staged = transaction / 'next-pdfs'
    staged.mkdir()
    result = {'reused': 0, 'copied': 0}
    try:
        for src in pdfs:
            relative = src.relative_to(source)
            dst, old = staged / relative, published / relative
            dst.parent.mkdir(parents=True, exist_ok=True)
            if old.is_file() and file_digest(old) == file_digest(src):
                os.link(old, dst)
                result['reused'] += 1
            else:
                shutil.copy2(src, dst)
                if file_digest(dst) != file_digest(src):
                    raise OSError(f'Copy verification failed: {relative}')
                result['copied'] += 1
        text = yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=180)
        if yaml.safe_load(text) != data:
            raise ValueError('YAML round-trip validation failed')
        atomic_text(transaction / 'next.yml', text)
        state = {'had_pdfs': published.exists(), 'had_yaml': output.exists(), 'committed': False}
        if output.exists():
            shutil.copy2(output, transaction / 'old.yml')
        # No live path is touched until the staged files and journal are complete.
        atomic_text(transaction / 'state.json', json.dumps(state))
        output.parent.mkdir(parents=True, exist_ok=True)
        if published.exists():
            os.replace(published, transaction / 'old-pdfs')
        os.replace(staged, published)
        os.replace(transaction / 'next.yml', output)
        state['committed'] = True
        atomic_text(transaction / 'state.json', json.dumps(state))
    except Exception:
        recover_publication(published, output)
        raise
    shutil.rmtree(transaction)
    return result
