import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


def copy_package(destination):
    """Copy the installable package, excluding evaluation history and local skills."""
    for name in ['tools', 'skills', 'voice', '.claude-plugin']:
        shutil.copytree(ROOT / name, destination / name,
                        ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    for name in ['ytstack.json', 'provenance.json', 'LICENSE']:
        shutil.copy2(ROOT / name, destination / name)


class PackageTests(unittest.TestCase):
    def setUp(self):
        self.actions = []
        self.scratch_paths = []

    def temporary_directory(self):
        directory = tempfile.TemporaryDirectory(prefix='ytstack-test-')
        self.scratch_paths.append(directory.name)
        return directory

    def run_command(self, command):
        result = subprocess.run(command, capture_output=True, text=True,
                                cwd=ROOT, timeout=15)
        self.actions.append({'command': [str(arg) for arg in command],
                             'cwd': str(ROOT), 'stdout': result.stdout,
                             'stderr': result.stderr, 'exit_status': result.returncode})
        return result

    def tearDown(self):
        for path in self.scratch_paths:
            self.assertFalse(Path(path).exists(), f'Scratch directory remains: {path}')

    def run_installer(self, project, *args):
        return self.run_command([sys.executable, str(ROOT / 'tools/install.py'), '--project', str(project),
                                 '--harness', 'codex', *args])

    def test_package_integrity(self):
        result = self.run_command([sys.executable, str(ROOT / 'tools/validate.py')])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['status'], 'PASS')

    def test_dependency_is_installed_and_repeat_is_harmless(self):
        with self.temporary_directory() as temp:
            first = self.run_installer(temp, '--skill', 'technical-bro')
            self.assertEqual(first.returncode, 0, first.stderr)
            installed = Path(temp) / '.agents/skills'
            self.assertEqual({p.name for p in installed.iterdir()}, {'technical-bro', 'unslop'})
            dependency = installed / 'technical-bro/../unslop/SKILL.md'
            self.assertTrue(dependency.is_file())
            second = self.run_installer(temp, '--skill', 'technical-bro')
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertEqual(json.loads(second.stdout)['installed'], [])
            self.assertEqual(len(json.loads(second.stdout)['unchanged']), 2)

    def test_conflict_is_preserved_without_partial_installation(self):
        with self.temporary_directory() as temp:
            conflict = Path(temp) / '.agents/skills/technical-bro'
            conflict.mkdir(parents=True)
            sentinel = conflict / 'SKILL.md'
            sentinel.write_text('my existing skill\n')
            result = self.run_installer(temp, '--skill', 'technical-bro')
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('preserved', result.stderr)
            self.assertEqual(sentinel.read_text(), 'my existing skill\n')
            self.assertFalse((conflict.parent / 'unslop').exists())

    def test_dry_run_changes_nothing(self):
        with self.temporary_directory() as temp:
            result = self.run_installer(temp, '--dry-run')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(len(json.loads(result.stdout)['planned']), 5)
            self.assertFalse((Path(temp) / '.agents').exists())

    def test_copied_claude_skills_are_standalone(self):
        with self.temporary_directory() as temp:
            package = Path(temp) / 'package'
            package.mkdir()
            copy_package(package)
            expected = {str(p.relative_to(package / 'skills')): p.read_bytes()
                        for p in (package / 'skills').rglob('*') if p.is_file()}
            project = Path(temp) / 'project'
            project.mkdir()
            command = [sys.executable, str(package / 'tools/install.py'), '--project', str(project),
                       '--harness', 'claude', '--method', 'copy']
            result = self.run_command(command)
            self.assertEqual(result.returncode, 0, result.stderr)
            installed = project / '.claude/skills'
            self.assertEqual(len(list(installed.iterdir())), 5)
            self.assertFalse((installed / 'technical-bro').is_symlink())
            self.assertTrue((installed / 'technical-bro/../unslop/SKILL.md').is_file())
            for name in ['technical-bro', 'unslop']:
                notice = (installed / name / 'LICENSE').read_text()
                self.assertIn('Copyright (c) 2026 Lauren Tan', notice)
                self.assertIn('Permission is hereby granted', notice)
            repeated = self.run_command(command)
            self.assertEqual(repeated.returncode, 0, repeated.stderr)
            self.assertEqual(json.loads(repeated.stdout)['installed'], [])
            package.rename(Path(temp) / 'source-unavailable')
            self.assertFalse(package.exists())
            self.assertEqual({str(p.relative_to(installed)): p.read_bytes()
                              for p in installed.rglob('*') if p.is_file()}, expected)
            self.assertIn('name: unslop', (installed / 'technical-bro/../unslop/SKILL.md').read_text())

    def test_copy_does_not_claim_a_link_is_standalone(self):
        with self.temporary_directory() as temp:
            linked = self.run_installer(temp, '--skill', 'bro')
            self.assertEqual(linked.returncode, 0, linked.stderr)
            copied = self.run_installer(temp, '--skill', 'bro', '--method', 'copy')
            self.assertNotEqual(copied.returncode, 0)
            self.assertTrue((Path(temp) / '.agents/skills/bro').is_symlink())

    def test_voice_block_keeps_user_content_and_repeat_is_harmless(self):
        with self.temporary_directory() as temp:
            agents = Path(temp) / 'AGENTS.md'
            agents.write_text('# My rules\n\nKeep me.\n')
            first = self.run_installer(temp, '--skill', 'bro', '--voice')
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(json.loads(first.stdout)['voice']['action'], 'written')
            written = agents.read_text()
            self.assertTrue(written.startswith('# My rules\n\nKeep me.\n'))
            self.assertIn('跟我说话的方式', written)
            second = self.run_installer(temp, '--skill', 'bro', '--voice')
            self.assertEqual(json.loads(second.stdout)['voice']['action'], 'unchanged')
            self.assertEqual(agents.read_text(), written)

    def test_voice_dry_run_and_stale_block_update(self):
        with self.temporary_directory() as temp:
            agents = Path(temp) / 'AGENTS.md'
            dry = self.run_installer(temp, '--dry-run', '--voice')
            self.assertEqual(json.loads(dry.stdout)['voice']['action'], 'planned')
            self.assertFalse(agents.exists())
            agents.write_text('before\n<!-- ytstack:plain-talk:begin -->\nold\n<!-- ytstack:plain-talk:end -->\nafter\n')
            result = self.run_installer(temp, '--skill', 'bro', '--voice')
            self.assertEqual(result.returncode, 0, result.stderr)
            text = agents.read_text()
            self.assertNotIn('old', text)
            self.assertTrue(text.startswith('before\n') and text.endswith('after\n'))

    def test_project_install_does_not_follow_discovery_outside_project(self):
        with self.temporary_directory() as temp:
            project = Path(temp) / 'project'
            shared = Path(temp) / 'shared'
            project.mkdir()
            shared.mkdir()
            (project / '.agents').symlink_to(shared, target_is_directory=True)
            result = self.run_installer(project)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(list(shared.iterdir()), [])

    def test_default_links_survive_bundle_move_for_both_hosts(self):
        expected_names = {'acceptance-criteria', 'create-test-skill', 'bro', 'technical-bro', 'unslop'}
        for harness, discovery in [('codex', '.agents'), ('claude', '.claude')]:
            with self.subTest(harness=harness), self.temporary_directory() as temp:
                bundle = Path(temp) / 'bundle'
                package = bundle / 'package'
                project = bundle / 'project'
                package.mkdir(parents=True)
                project.mkdir()
                copy_package(package)
                result = self.run_command([sys.executable, str(package / 'tools/install.py'),
                                           '--project', str(project), '--harness', harness])
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(len(json.loads(result.stdout)['installed']), 5)
                moved = Path(temp) / 'moved bundle'
                bundle.rename(moved)
                installed = moved / 'project' / discovery / 'skills'
                self.assertEqual({p.name for p in installed.iterdir()}, expected_names)
                for name in expected_names:
                    entry = installed / name
                    self.assertTrue(entry.is_symlink())
                    self.assertFalse(os.path.isabs(os.readlink(entry)))
                    self.assertEqual(entry.resolve(), moved / 'package/skills' / name)
                    self.assertIn(f'name: {name}', (entry / 'SKILL.md').read_text())
                self.assertIn('name: unslop',
                              (installed / 'technical-bro/../unslop/SKILL.md').read_text())


if __name__ == '__main__':
    unittest.main()
