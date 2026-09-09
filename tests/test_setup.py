import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[1]


def load_script(name):
    spec = importlib.util.spec_from_file_location(name, REPO / 'scripts' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SetupTests(unittest.TestCase):
    def test_full_install_routes_packages_into_selected_root(self):
        installer = load_script('install')
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with patch.object(sys, 'argv', ['install.py', '--root', str(root)]), \
                 patch.object(installer.shutil, 'which', return_value='/tools/node'), \
                 patch.object(installer.subprocess, 'check_output', return_value='v22.19.0\n'), \
                 patch.object(installer.subprocess, 'run') as run:
                installer.main()
            self.assertEqual(run.call_count, 4)
            self.assertIn(str(root / '.local/share/pi-dev'), run.call_args_list[0].args[0])
            for call in run.call_args_list[1:3]:
                self.assertEqual(call.kwargs['env']['PI_CODING_AGENT_DIR'], str(root / '.pi/agent'))
                self.assertEqual(call.args[0][1], 'install')
            self.assertTrue((root / '.local/bin/pi').is_symlink())
            self.assertTrue((root / '.pi/agent/settings.json').exists())
            self.assertIn('pi-agent-setup PATH', (root / '.bashrc').read_text())

    def test_update_preserves_old_launcher_shell_content_and_is_idempotent(self):
        installer = load_script('install')
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            launcher = root / '.local/bin/pi'
            launcher.parent.mkdir(parents=True)
            launcher.write_text('old Pi launcher')
            (root / '.bashrc').write_text('export MY_SETTING=original\n')
            binary = root / '.local/share/pi-dev/node_modules/.bin/pi'
            installer.activate_runtime(root, binary)
            backups = list((root / '.pi/agent/backups').iterdir())
            self.assertEqual(len(backups), 1)
            self.assertEqual((backups[0] / '.local/bin/pi').read_text(), 'old Pi launcher')
            self.assertEqual((backups[0] / '.bashrc').read_text(), 'export MY_SETTING=original\n')
            self.assertEqual(launcher.resolve(), binary.resolve())
            self.assertIn('export MY_SETTING=original', (root / '.bashrc').read_text())
            installer.activate_runtime(root, binary)
            self.assertEqual(len(list((root / '.pi/agent/backups').iterdir())), 1)
            self.assertEqual((root / '.bashrc').read_text().count('# >>> pi-agent-setup PATH >>>'), 1)

    def test_shell_symlink_is_not_overwritten(self):
        installer = load_script('install')
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / 'managed-dotfile'
            source.write_text('custom shell settings')
            (root / '.bashrc').symlink_to(source)
            with self.assertRaises(ValueError):
                installer.activate_runtime(root, root / 'binary')
            self.assertEqual(source.read_text(), 'custom shell settings')
            self.assertFalse((root / '.local/bin/pi').exists())

    def test_merge_backup_auth_and_idempotence(self):
        installer = load_script('install')
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            agent = root / '.pi/agent'
            (agent / 'agents').mkdir(parents=True)
            old = {'theme': 'custom', 'packages': ['npm:unrelated', 'npm:pi-subagents@0.1.0'],
                   'subagents': {'agentOverrides': {'custom': {'thinking': 'low'}},
                                 'agentOverridesByProvider': {'openrouter': {'worker': {'model': 'old', 'thinking': 'low', 'tools': 'read'}}}}}
            (agent / 'settings.json').write_text(json.dumps(old))
            (agent / 'auth.json').write_text('sentinel-do-not-read-or-copy')
            (agent / 'agents/coder.md').write_text('original coder')
            backup = installer.apply_config(root)
            result = json.loads((agent / 'settings.json').read_text())
            self.assertEqual(result['theme'], 'custom')
            self.assertIn('npm:unrelated', result['packages'])
            self.assertNotIn('npm:pi-subagents@0.1.0', result['packages'])
            self.assertEqual(result['subagents']['agentOverrides']['worker']['thinking'], 'high')
            self.assertEqual(result['subagents']['agentOverridesByProvider']['openrouter']['worker'], {'tools': 'read'})
            self.assertEqual(json.loads((backup / 'settings.json').read_text()), old)
            self.assertEqual((backup / 'agents/coder.md').read_text(), 'original coder')
            self.assertEqual((agent / 'auth.json').read_text(), 'sentinel-do-not-read-or-copy')
            self.assertFalse((backup / 'auth.json').exists())
            self.assertIsNone(installer.apply_config(root))

    def test_default_root_is_current_home_and_dry_run_does_not_write(self):
        with tempfile.TemporaryDirectory() as folder:
            env = dict(os.environ, HOME=folder)
            run = subprocess.run([sys.executable, str(REPO / 'scripts/install.py'), '--dry-run'],
                                 env=env, text=True, capture_output=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertIn(str(Path(folder) / '.pi/agent/settings.json'), run.stdout)
            self.assertFalse((Path(folder) / '.pi').exists())

    def test_invalid_existing_json_does_not_replace_files(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            path = root / '.pi/agent/settings.json'
            path.parent.mkdir(parents=True)
            path.write_text('{broken')
            with self.assertRaises(json.JSONDecodeError):
                load_script('install').apply_config(root)
            self.assertEqual(path.read_text(), '{broken')

    def test_costs_and_retries_include_repeated_reviews(self):
        costs = load_script('costs')
        one = costs.estimate()
        self.assertAlmostEqual(one['hybrid_api_reference_usd'], 0.397)
        self.assertAlmostEqual(one['all_sol_api_reference_usd'], 1.48)
        self.assertAlmostEqual(one['all_glm_api_reference_usd'], 0.049)
        two = costs.estimate(2)
        self.assertAlmostEqual(two['hybrid_api_reference_usd'], 0.654)
        self.assertEqual(two['configured_hybrid_sol_quota_tokens']['input'], 100000)


if __name__ == '__main__':
    unittest.main()
