import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path('/tmp/ytstack-cold-khzxev_5')
BASE = ROOT / 'evaluation/self-test/cold-01'

def read(name):
    return json.loads((BASE / name).read_text())

names = ['doctor.json', 'suite.json', 'YT02.json',
         'failure-detection/baseline.json', 'failure-detection/broken.json',
         'failure-detection/restored.json']
receipts = {name: read(name) for name in names}
proof = read('failure-detection/proof.json')
expected = ['PASS', 'PASS', 'PASS', 'PASS', 'FAIL', 'PASS']
for (name, data), status in zip(receipts.items(), expected):
    assert data['status'] == status, name
    assert data['cleanup_passed'] and data['target_unchanged'], name
assert [c['id'] for c in receipts['suite.json']['cases']] == [f'YT{i:02d}' for i in range(1, 9)]
assert [c['id'] for c in receipts['YT02.json']['cases']] == ['YT02']
assert [r['exit_status'] for r in proof['runs']] == [0, 1, 0]
assert proof['status'] == 'PASS'
assert all(proof[key] for key in ['intended_assertion_detected', 'isolated_source_restored',
                                  'scratch_removed', 'live_target_unchanged'])
broken = receipts['failure-detection/broken.json']['cases'][0]
assert broken['actions'][0]['exit_status'] == 0
installed = json.loads(broken['actions'][0]['stdout'])['installed']
assert {Path(p).name for p in installed} == {'technical-bro'}
assert any('AssertionError' in f and "'unslop'" in f for f in broken['failures'])
phase_commands = [receipts[f'failure-detection/{stage}.json']['command']
                  for stage in ['baseline', 'broken', 'restored']]
assert phase_commands[0] == phase_commands[1] == phase_commands[2]

scratch_paths = sorted({s['path'] for d in receipts.values() for c in d['cases']
                        for s in c['scratch']} | {proof['scratch']})
scratch_checks = [{'path': p, 'exists': Path(p).exists(), 'is_symlink': Path(p).is_symlink()}
                  for p in scratch_paths]
assert all(not row['exists'] and not row['is_symlink'] for row in scratch_checks)
before = receipts['doctor.json']['target_before']
current = {rel: hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() for rel in before}
assert current == before
assert all(receipts[name]['target_before'] == before == receipts[name]['target_after']
           for name in ['doctor.json', 'suite.json', 'YT02.json'])
artifacts = ['mutation.patch', 'broken-install.py', 'proof.json'] + [
    f'{stage}.{suffix}' for stage in ['baseline', 'broken', 'restored']
    for suffix in ['json', 'stdout.log', 'stderr.log']]
assert all((BASE / 'failure-detection' / name).is_file() for name in artifacts)

commands = []
for name in ['doctor.json', 'suite.json', 'YT02.json']:
    commands.append({'command': receipts[name]['command'], 'cwd': str(ROOT),
                     'exit_status': 0, 'result': receipts[name]['status'], 'evidence': name})
commands.extend([
    {'command': ['python3', 'tests/ytstack_skill/prove_failure_detection.py',
                 '--evidence-dir', 'evaluation/self-test/cold-01/failure-detection'],
     'cwd': str(ROOT), 'exit_status': 0, 'result': 'PASS',
     'evidence': 'failure-detection/proof.json'},
    {'command': ['python3', 'evaluation/self-test/cold-01/verify-cold.py'],
     'cwd': str(ROOT), 'exit_status': 0, 'result': 'PASS',
     'evidence': 'COLD-REVIEW.json'},
])
report = {
    'status': 'PASS',
    'reviewed_at': datetime.now(timezone.utc).isoformat(),
    'scope': 'Independent execution from the generated test skill in the isolated project.',
    'instruction_entrypoint': '.agents/skills/test-ytstack/SKILL.md',
    'additional_instruction_read': ['.agents/skills/test-ytstack/cases/README.md'],
    'independence': {
        'original_workspace_read': False,
        'other_evaluation_records_read': False,
        'generator_instructions_read': False,
        'prior_conversation_used': False,
        'product_skill_or_test_modifications': False,
        'note': 'Only the isolated generated skill, its case index, and this run\'s receipts were read. Product files were hashed as bytes without reading generator instructions.',
    },
    'commands': commands,
    'results': {
        'doctor': 'PASS', 'suite': '8/8 PASS', 'named_case': 'YT02 PASS',
        'failure_detection': {'result': 'PASS', 'stage_results': ['PASS', 'FAIL', 'PASS'],
                              'stage_exit_statuses': [0, 1, 0],
                              'broken_cli_exit_status': 0,
                              'assertion': 'Installed skill names lack unslop while technical-bro is present.',
                              'same_phase_command': True},
        'cleanup': {'result': 'PASS', 'own_scratch_paths_checked': scratch_checks},
        'target_unchanged': {'result': 'PASS', 'product_files_rehashed': len(before),
                             'matches_initial_doctor_snapshot': True},
        'evidence_preserved': True,
    },
    'documentation_defects': [],
    'blockers': [],
    'sufficient_for_independent_use': True,
    'independent_use_reason': 'Relative commands, case index, expected negative-test behavior, exit-code interpretation, evidence locations, and cleanup fields were sufficient to complete the requested run without outside instructions or code changes.',
    'coverage_limits': [
        'Executed only on this Linux filesystem and Python 3.12.3.',
        'Checks installer CLI and package-validator behavior; YT01 reuses the product validator.',
        'Host directory layouts are checked; real Codex/Claude skill discovery and model invocation are not exercised.',
        'Writing quality of bro and technical-bro is not evaluated.',
        'Only missing-dependency mutation was demonstrated; no claim of arbitrary defect detection.',
        'Permission failures, concurrent installation, mid-install disk errors, and other Python versions are not covered.',
        'Final product hashes cover the runner\'s recorded product-file set; they do not assert every repository file is unchanged.',
        'The isolated project is intentionally retained for the parent agent to archive and clean up.',
    ],
}
with (BASE / 'COLD-REVIEW.json').open('x') as output:
    json.dump(report, output, ensure_ascii=False, indent=2)
    output.write('\n')
print(f'PASS: {BASE / "COLD-REVIEW.json"}; {len(scratch_paths)} scratch paths absent; {len(before)} product hashes unchanged')
