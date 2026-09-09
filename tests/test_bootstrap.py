import os
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]


class BootstrapTests(unittest.TestCase):
    def run_bootstrap(self, fail_download=False):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            tools = root / 'bin'
            tools.mkdir()
            temp = root / 'temp'
            temp.mkdir()
            archive = root / 'source.tar.gz'
            with tarfile.open(archive, 'w:gz') as stream:
                for name in ['scripts', 'config', 'agents']:
                    stream.add(REPO / name, arcname='snapshot/' + name)
            stub = tools / 'gh'
            stub.write_text('''#!/usr/bin/env python3
import os, sys
if sys.argv[1] == 'auth':
    sys.exit(0)
if any('/commits/' in a for a in sys.argv):
    print('a' * 40)
elif any('/tarball/' in a for a in sys.argv):
    if os.environ.get('FAIL_DOWNLOAD') == 'yes':
        sys.exit(22)
    with open(os.environ['TEST_ARCHIVE'], 'rb') as f:
        sys.stdout.buffer.write(f.read())
else:
    sys.exit(2)
''')
            stub.chmod(0o755)
            home = root / 'user home'
            env = dict(os.environ, PATH=str(tools) + os.pathsep + os.environ['PATH'],
                       HOME=str(home), TMPDIR=str(temp), TEST_ARCHIVE=str(archive),
                       FAIL_DOWNLOAD='yes' if fail_download else 'no')
            run = subprocess.run(['bash', '-s', '--', '--dry-run', '--root', str(home)],
                                 input=(REPO / 'install.sh').read_text(), text=True,
                                 capture_output=True, env=env)
            self.assertEqual(list(temp.iterdir()), [], run.stderr)
            self.assertFalse(home.exists())
            return run, home

    def test_pipe_mode_preserves_home_and_forwards_options(self):
        run, home = self.run_bootstrap()
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertIn(str(home / '.pi/agent/settings.json'), run.stdout)

    def test_failed_download_never_runs_installer_and_cleans_up(self):
        run, _ = self.run_bootstrap(fail_download=True)
        self.assertNotEqual(run.returncode, 0)
        self.assertNotIn('Settings:', run.stdout)


if __name__ == '__main__':
    unittest.main()
