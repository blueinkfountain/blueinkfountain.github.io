#!/usr/bin/env python3
"""Install Scalar ODE, general dynamical systems, and Cucker-Smale Lab.

Run from the extracted package folder kept inside your blog root:
    python3 ode_lab_second_order_web/install_euler_method.py --repo .

Nothing is committed or pushed automatically. No README is created.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import shutil

FILES = (
    "docs/Math-Programs.md",
    "docs/Works/Euler-Method.html",
    "assets/euler-method/app.mjs",
    "assets/euler-method/math.mjs",
    "assets/euler-method/latex.mjs",
    "assets/euler-method/pixel.mjs",
    "assets/euler-method/style.css",
    "assets/euler-method/dynamics.css",
    "assets/euler-method/dynamics_math.mjs",
    "assets/euler-method/dynamics_ui.mjs",
)
PACKAGE_DIRECTORIES = (
    "euler_method_web",
    "euler_method_pixel_web",
    "euler_method_latex_web",
    "euler_latex_upgrade",
    "ode_lab_rk4_web",
    "ode_lab_second_order_web",
    "ode_lab_timeline_fix",
    "ode_lab_dynamics_upgrade",
)


def updated_config(text: str, package_name: str) -> str:
    """Exclude source/install directories so Jekyll won't duplicate navigation."""
    paths = list(dict.fromkeys((*PACKAGE_DIRECTORIES, package_name)))
    matches = list(re.finditer(r"(?m)^exclude[ \t]*:[ \t]*([^\n]*)$", text))
    if len(matches) > 1:
        raise ValueError("Multiple top-level 'exclude' keys in _config.yml; fix them before installing.")
    if not matches:
        # Explicit Jekyll default exclusions, to avoid changing build behavior.
        paths = ["Gemfile", "Gemfile.lock", "node_modules", "vendor", *paths]
        return text.rstrip() + "\n\n# Keep local Euler source packages out of GitHub Pages navigation.\nexclude:\n" + ''.join(f"  - {p}\n" for p in paths)
    match = matches[0]
    tail = match.group(1).strip()
    if tail and not tail.startswith('#'):
        if tail.startswith('[') and tail.endswith(']'):
            body=tail[1:-1].strip()
            existing={x.strip().strip('\"\'') for x in body.split(',') if x.strip()}
            missing=[p for p in paths if p not in existing]
            if not missing:return text
            insert=', '.join((([body] if body else []) + ['"'+p+'"' for p in missing]))
            return text[:match.start(1)] + '['+insert+']' + text[match.end(1):]
        raise ValueError("An unsupported inline 'exclude' value exists. Please use a YAML list.")
    # Insert list entries after pre-existing entries, before the next YAML root key.
    end=match.end()
    while end < len(text):
        nl=text.find('\n',end+1)
        if nl<0:nl=len(text)
        line=text[end+1:nl]
        if line and not line[0].isspace() and not line.lstrip().startswith('#'):
            break
        end=nl
    existing=set(re.findall(r"(?m)^\s*-\s*['\"]?([A-Za-z0-9_./-]+)",text[match.end():end]))
    missing=[p for p in paths if p not in existing]
    if not missing:return text
    insert=''.join('  - '+p+'\n' for p in missing)
    return text[:end] + ('' if text[end-1:end]=='\n' else '\n') + insert + text[end:]


def install(repo: Path, package: Path) -> None:
    repo=repo.expanduser().resolve()
    package=package.resolve()
    if not (repo/'_config.yml').is_file():
        raise SystemExit('Not a Jekyll blog: missing '+str(repo/'_config.yml'))
    for rel in FILES:
        if not (package/rel).is_file():
            raise SystemExit('Incomplete downloaded package; missing '+rel)
    config=repo/'_config.yml'
    new_config=updated_config(config.read_text(encoding='utf-8'),package.name)
    backup_root=repo/'.ode_lab_backup'
    exclude_file=repo/'.git/info/exclude'
    if exclude_file.is_file():
        existing=exclude_file.read_text(encoding='utf-8')
        if '/.ode_lab_backup/' not in existing:
            with exclude_file.open('a',encoding='utf-8') as f:
                f.write('\n/.ode_lab_backup/\n')
    changes=[(package/rel,repo/rel) for rel in FILES]
    if new_config != config.read_text(encoding='utf-8'):
        changes.append((None,config))
    # Preflight all files before modifying any existing source.
    for src,dst in changes:
        if src is not None and not src.is_file():raise SystemExit('Missing source '+str(src))
        if dst.exists() and not dst.is_file():raise SystemExit('Expected a file: '+str(dst))
    for src,dst in changes:
        new_bytes=src.read_bytes() if src is not None else new_config.encode('utf-8')
        if dst.is_file() and dst.read_bytes()==new_bytes:
            print('Unchanged:',dst.relative_to(repo))
            continue
        if dst.is_file():
            bak=backup_root/dst.relative_to(repo)
            bak.parent.mkdir(parents=True,exist_ok=True)
            if not bak.exists():shutil.copy2(dst,bak)
            print('Backed up:',dst.relative_to(repo))
        dst.parent.mkdir(parents=True,exist_ok=True)
        dst.write_bytes(new_bytes)
        print('Installed:',dst.relative_to(repo))
    print('\nMath Programs → ODE Lab is ready for GitHub Pages.')
    print('No README was created. Source-package folders are excluded from Jekyll.')
    print('Commit & push docs/Math-Programs.md docs/Works/Euler-Method.html assets/euler-method/ _config.yml')


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo',type=Path,default=Path.cwd())
    args=parser.parse_args()
    install(args.repo,Path(__file__).resolve().parent)


if __name__ == '__main__':
    main()
