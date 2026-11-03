"""Verify immutable inputs and collect completed anonymous bodies, without scoring."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil

BASE = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('labels', nargs='+')
    args = parser.parse_args()
    assignment = json.loads((BASE / 'control/assignment.json').read_text())
    runs = {row['label']: row for row in assignment['runs']}
    diagnostic_dir = BASE / 'diagnostics'
    diagnostic_dir.mkdir(exist_ok=True)
    (BASE / 'blind').mkdir(exist_ok=True)
    if not (BASE / 'blind/inputs').exists():
        shutil.copytree(BASE / 'inputs', BASE / 'blind/inputs')
    rows = []
    for label in args.labels:
        run = runs[label]
        project = BASE / run['project']
        output = project / 'output.md'
        assert output.is_file() and output.read_text().strip(), label
        assert digest(BASE / run['prompt']) == run['prompt_sha256']
        expected = set()
        for name, value in assignment['materials'][run['material']]['input_sha256'].items():
            assert digest(project / name) == value, (label, name)
            expected.add(name)
        if run['arm'] == 'with':
            for name, value in assignment['skill_sha256'].items():
                relative = '.agents/skills/unslop/' + name
                assert digest(project / relative) == value
                expected.add(relative)
        actual = {str(path.relative_to(project)) for path in project.rglob('*') if path.is_file()}
        assert actual - expected == {'output.md'}, (label, actual - expected)
        assert expected <= actual
        destination = BASE / 'blind' / run['material'] / (label + '.md')
        destination.parent.mkdir(exist_ok=True)
        if destination.exists():
            assert destination.read_bytes() == output.read_bytes(), 'Previously collected output changed'
        else:
            shutil.copy2(output, destination)
        text = output.read_text()
        row = {'label': label, 'material': run['material'], 'source_inputs_unchanged': True,
               'skill_inputs_match_if_present': True, 'only_new_file': 'output.md',
               'output_sha256': digest(output), 'anonymous_bytes_match': True,
               'characters': len(text), 'non_whitespace_characters': len(re.sub(r'\s', '', text)),
               'draft_characters': len((project / 'draft.md').read_text()),
               'exactly_matches_draft': output.read_bytes() == (project / 'draft.md').read_bytes(),
               'collected_at': datetime.now(timezone.utc).isoformat(),
               'note': 'Character and unchanged-text measures are descriptive only, not quality scores.'}
        (diagnostic_dir / (label + '.json')).write_text(json.dumps(row, ensure_ascii=False, indent=2) + '\n')
        rows.append({key: row[key] for key in ['label', 'material', 'characters', 'exactly_matches_draft']})
    print(json.dumps(rows, ensure_ascii=False))


if __name__ == '__main__':
    main()
