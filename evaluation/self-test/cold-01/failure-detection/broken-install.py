#!/usr/bin/env python3
"""Expose ytstack skills in one project without replacing existing entries."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys


PACKAGE = Path(__file__).resolve().parents[1]


def digest_tree(root):
    return {
        str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in root.rglob('*') if p.is_file()
    }


def install(project, harness, selected=(), method='symlink', dry_run=False):
    project = Path(project).resolve()
    if not project.is_dir():
        raise ValueError(f'Project is not an existing directory: {project}')
    manifest = json.loads((PACKAGE / 'ytstack.json').read_text())
    known = set(manifest['primary_skills'] + manifest['support_skills'])
    names = []

    def include(name, ancestors=()):
        if name not in known:
            raise ValueError(f'Unknown skill: {name}')
        if name in ancestors:
            raise ValueError(f'Cyclic dependency: {name}')
        if name in names:
            return
        for dependency in manifest['dependencies'].get(name, []):
            pass  # isolated regression: dependency omitted
        names.append(name)

    for name in selected or manifest['primary_skills']:
        include(name)
    discovery = project / ('.agents' if harness == 'codex' else '.claude') / 'skills'
    if not discovery.resolve().is_relative_to(project):
        raise ValueError(f'Project discovery path resolves outside the project: {discovery}')
    planned, unchanged = [], []
    for name in names:
        source = PACKAGE / 'skills' / name
        if not (source / 'SKILL.md').is_file():
            raise ValueError(f'Missing source skill: {source}')
        target = discovery / name
        if os.path.lexists(target):
            if target.is_symlink() and target.resolve() == source.resolve() and method == 'symlink':
                unchanged.append(str(target))
            elif not target.is_symlink() and target.is_dir() and digest_tree(target) == digest_tree(source):
                unchanged.append(str(target))
            else:
                raise ValueError(f'Existing entry preserved; resolve the conflict before installing: {target}')
        else:
            planned.append((source, target))
    if not dry_run:
        if planned:
            discovery.mkdir(parents=True, exist_ok=True)
        for source, target in planned:
            if method == 'copy':
                shutil.copytree(source, target)
            else:
                target.symlink_to(os.path.relpath(source, target.parent), target_is_directory=True)
    return {
        'project': str(project), 'harness': harness, 'method': method,
        'planned' if dry_run else 'installed': [str(t) for _, t in planned],
        'unchanged': unchanged,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--harness', choices=('codex', 'claude'), required=True)
    parser.add_argument('--skill', action='append', default=[], help='Repeat to select skills; defaults to all primary skills plus dependencies.')
    parser.add_argument('--method', choices=('symlink', 'copy'), default='symlink')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    try:
        result = install(args.project, args.harness, args.skill, args.method, args.dry_run)
    except (ValueError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
