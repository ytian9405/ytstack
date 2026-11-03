#!/usr/bin/env python3
"""Check this package's structure and recorded upstream-derived bodies."""

import hashlib
import json
from pathlib import Path
import re
import sys


PACKAGE = Path(__file__).resolve().parents[1]


def validate(root=PACKAGE):
    root = Path(root).resolve()
    manifest = json.loads((root / 'ytstack.json').read_text())
    plugin = json.loads((root / '.claude-plugin/plugin.json').read_text())
    assert plugin['name'] == manifest['name'] == 'ytstack'
    assert plugin['version'] == manifest['version']
    names = manifest['primary_skills'] + manifest['support_skills']
    assert len(names) == len(set(names))
    assert set(names) == {p.parent.name for p in (root / 'skills').glob('*/SKILL.md')}
    bodies = {}
    for name in names:
        file = root / 'skills' / name / 'SKILL.md'
        text = file.read_text()
        header, body = text.split('---', 2)[1:]
        bodies[name] = body
        # These package files use simple, single-line name/description scalars.
        assert re.search(rf'^name: {re.escape(name)}$', header, re.M), name
        description = re.search(r'^description: (.+)$', header, re.M)
        assert description and description.group(1).strip(), name
        invocation = re.search(r'^disable-model-invocation: (.+)$', header, re.M)
        if invocation:
            assert invocation.group(1).strip() == 'true', name
        assert 'TODO' not in body, name
        assert (file.parent / 'agents/openai.yaml').is_file(), name
        skill_license = (file.parent / 'LICENSE').read_text()
        assert 'Copyright (c) 2026 Lauren Tan' in skill_license, name
        assert 'Permission is hereby granted' in skill_license, name
        for link in re.findall(r'\]\(([^)]+)\)', body):
            if '://' in link or link.startswith('#'):
                continue
            target = (file.parent / link.split('#', 1)[0]).resolve()
            assert target.is_relative_to(root), f'Link escapes package: {link}'
            assert target.exists(), f'Broken local link: {file}: {link}'
    known = set(names)
    for owner, dependencies in manifest['dependencies'].items():
        assert owner in known, owner
        for dependency in dependencies:
            assert dependency in known, dependency
    for name, body in bodies.items():
        linked = set()
        for link in re.findall(r'\]\(([^)]+)\)', body):
            if '://' in link or link.startswith('#'):
                continue
            parts = link.split('#', 1)[0].split('/')
            if len(parts) >= 2 and parts[0] == '..' and parts[1] in known:
                linked.add(parts[1])
        declared = set(manifest['dependencies'].get(name, []))
        undeclared = sorted(linked - declared)
        assert not undeclared, f'{name} links to undeclared skills: {", ".join(undeclared)}'
        missing = sorted(declared - linked)
        assert not missing, f'{name} does not link declared dependencies: {", ".join(missing)}'
    assert (root / 'voice/plain-talk.md').read_text().strip(), 'voice rules are empty'
    provenance = json.loads((root / 'provenance.json').read_text())
    checked_bodies = []
    for record in provenance['records']:
        adoption = record.get('adoption')
        if not adoption:
            continue
        text = (root / adoption['local_path']).read_text()
        body_hash = hashlib.sha256(text.split('---', 2)[2].encode()).hexdigest()
        assert body_hash == adoption['local_body_sha256'], adoption['local_path']
        if adoption['mode'] == 'body-preserved':
            assert body_hash == adoption['upstream_body_sha256'], adoption['local_path']
        checked_bodies.append(adoption['local_path'])
    license_text = (root / 'LICENSE').read_text()
    assert 'Copyright (c) 2026 Lauren Tan' in license_text
    assert 'Permission is hereby granted' in license_text
    return {'package': manifest['name'], 'version': manifest['version'], 'skills': names,
            'copied_bodies_checked': checked_bodies, 'status': 'PASS'}


if __name__ == '__main__':
    try:
        print(json.dumps(validate(), indent=2))
    except (AssertionError, ValueError, OSError, KeyError) as exc:
        print(f'Package validation failed: {exc}', file=sys.stderr)
        raise SystemExit(1)
