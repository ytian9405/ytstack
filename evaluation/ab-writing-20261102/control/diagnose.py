"""Mechanical integrity and literal diagnostics; never a semantic quality score."""
import hashlib
import json
from pathlib import Path
import re

BASE = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def diagnose(run):
    project = BASE / run['project']
    output = project / 'output.md'
    text = output.read_text()
    source = (project / 'source.md').read_text()
    row = {'label': run['label'], 'task': run['task'],
           'output_sha256': digest(output), 'characters': len(text),
           'non_whitespace_characters': len(re.sub(r'\s', '', text)),
           'description': 'Counts and literal matches are diagnostics, not quality or comprehension scores',
           'source_unchanged': digest(project / 'source.md') == digest(BASE / 'inputs' / run['task'] / 'source.md'),
           'task_unchanged': digest(project / 'task.txt') == digest(BASE / 'inputs' / run['task'] / 'task.txt')}
    if run['task'] == 'bro':
        markers = ['256', 'KiB', '3', '503', '400', '401', '100%', '24']
        row['literal_markers'] = {marker: marker in text for marker in markers}
        row['marker_note'] = 'Chinese numbers or semantically equivalent phrasing require human review; absence is not automatically an error'
    else:
        commands = re.findall(r'`(briefctl[^`]+)`', source)
        normalized = re.sub(r'\\\n\s*', ' ', text)
        row['source_commands'] = commands
        row['literal_commands_present'] = {command: command in text for command in commands}
        row['line_continuation_normalized_commands'] = {command: command in normalized for command in commands}
        markers = ['Python 3.11', '/srv/briefcase', 'REPORT_TOKEN', 'profiles/review.toml',
                   'healthy', 'pending_count', 'valid', 'row_count', 'publish_id']
        row['literal_markers'] = {marker: marker in text for marker in markers}
        row['marker_note'] = 'Presence cannot establish correct negation, order or conditions; scoring requires the frozen semantic fact matrix'
    return row


if __name__ == '__main__':
    assignment = json.loads((BASE / 'control/assignment.json').read_text())
    destination = BASE / 'diagnostics'
    destination.mkdir(exist_ok=True)
    results = []
    for run in assignment['runs']:
        if not (BASE / run['project'] / 'output.md').is_file():
            continue
        row = diagnose(run)
        (destination / f"{run['label']}.json").write_text(json.dumps(row, ensure_ascii=False, indent=2) + '\n')
        results.append({'label': row['label'], 'source_unchanged': row['source_unchanged'],
                        'task_unchanged': row['task_unchanged'], 'characters': row['characters']})
    print(json.dumps(results, ensure_ascii=False))
