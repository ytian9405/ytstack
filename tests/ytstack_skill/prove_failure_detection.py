#!/usr/bin/env python3
"""Break dependency installation only in a temporary package, then restore it."""
import argparse
import difflib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from run import ROOT, identity, save


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence-dir', type=Path, required=True)
    args = parser.parse_args()
    evidence = args.evidence_dir.resolve()
    if evidence.exists():
        parser.error('Choose a new evidence directory')
    evidence.mkdir(parents=True)
    before = identity(ROOT)
    proof = {'status': 'FAIL', 'case': 'YT02', 'runs': [],
             'mutation': 'Omit dependency inclusion while still installing the requested skill.'}
    with tempfile.TemporaryDirectory(prefix='ytstack-negative-') as temp:
        target = Path(temp) / 'package'
        target.mkdir()
        for name in ['tools', 'skills', '.claude-plugin']:
            shutil.copytree(ROOT / name, target / name,
                            ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        for name in ['ytstack.json', 'provenance.json', 'LICENSE']:
            shutil.copy2(ROOT / name, target / name)
        installer = target / 'tools/install.py'
        original = installer.read_text()
        needle = '            include(dependency, (*ancestors, name))'
        if original.count(needle) != 1:
            raise RuntimeError('Mutation location changed; review this proof before use')
        broken = original.replace(needle, '            pass  # isolated regression: dependency omitted')
        (evidence / 'mutation.patch').write_text(''.join(difflib.unified_diff(
            original.splitlines(keepends=True), broken.splitlines(keepends=True),
            fromfile='a/tools/install.py', tofile='b/tools/install.py')))
        (evidence / 'broken-install.py').write_text(broken)
        command = [sys.executable, str(Path(__file__).with_name('run.py')),
                   '--target', str(target), '--case', 'YT02',
                   '--evidence', str(evidence / 'active.json')]
        proof['command'] = command
        try:
            for label, source in [('baseline', original), ('broken', broken), ('restored', original)]:
                installer.write_text(source)
                result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=45)
                (evidence / f'{label}.stdout.log').write_text(result.stdout)
                (evidence / f'{label}.stderr.log').write_text(result.stderr)
                active = evidence / 'active.json'
                receipt = json.loads(active.read_text())
                active.rename(evidence / f'{label}.json')
                proof['runs'].append({'stage': label, 'exit_status': result.returncode,
                                      'status': receipt['status'], 'receipt': f'{label}.json'})
        finally:
            installer.write_text(original)
        bad = json.loads((evidence / 'broken.json').read_text())
        intended_failure = (bad['status'] == 'FAIL' and
                            len(bad['cases']) == 1 and
                            bad['cases'][0]['id'] == 'YT02' and
                            any('unslop' in failure and 'AssertionError' in failure
                                for failure in bad['cases'][0]['failures']) and
                            bad['cases'][0]['actions'][0]['exit_status'] == 0)
        proof['intended_assertion_detected'] = intended_failure
        proof['scratch'] = temp
        proof['isolated_source_restored'] = installer.read_text() == original
    proof['scratch_removed'] = not Path(temp).exists()
    proof['live_target_unchanged'] = before == identity(ROOT)
    proof['status'] = 'PASS' if (intended_failure and
        [run['exit_status'] for run in proof['runs']] == [0, 1, 0] and
        proof['scratch_removed'] and proof['live_target_unchanged'] and
        proof['isolated_source_restored']) else 'FAIL'
    save(evidence / 'proof.json', proof)
    print(f"{proof['status']}: {evidence / 'proof.json'}")
    return 0 if proof['status'] == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
