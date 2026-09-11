#!/usr/bin/env python3
"""Install a portable Pi profile under the current user's home; never copy auth."""
import argparse
import copy
import json
import os
from pathlib import Path
import shutil
import shlex
import subprocess
import tempfile
from datetime import datetime, timezone

REPO = Path(__file__).resolve().parents[1]


def merge(base, overlay):
    result = copy.deepcopy(base)
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def atomic_write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=path.parent, prefix='.pi-setup-')
    try:
        with os.fdopen(fd, 'w') as stream:
            stream.write(text)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def configure_runtime(root, binary):
    """Activate the managed installation; preserve replaced launcher and shell files."""
    launcher = root / '.local/bin/pi'
    needs_launcher = not launcher.is_symlink() or launcher.resolve() != binary.resolve()
    if launcher.exists() and launcher.is_dir():
        raise ValueError(str(launcher) + ' is a directory; refusing to replace it.')
    begin = '# >>> pi-agent-setup PATH >>>'
    end = '# <<< pi-agent-setup PATH <<<'
    block = begin + '\nexport PATH=' + shlex.quote(str(root / '.local/bin')) + ':"$PATH"\n' + end
    edits = {}
    for name in ['.profile', '.bashrc', '.zshrc']:
        path = root / name
        if path.is_symlink():
            raise ValueError(str(path) + ' is a symlink. Manage PATH manually and use --no-shell-config.')
        original = path.read_text() if path.exists() else ''
        if begin in original or end in original:
            if original.count(begin) != 1 or original.count(end) != 1 or original.index(begin) > original.index(end):
                raise ValueError('Malformed pi-agent-setup PATH block in ' + str(path))
            start = original.index(begin)
            stop = original.index(end) + len(end)
            updated = original[:start] + block + original[stop:]
        else:
            updated = original + ('\n' if original and not original.endswith('\n') else '') + '\n' + block + '\n'
        if updated != original:
            edits[path] = updated
    return launcher, needs_launcher, edits


def activate_runtime(root, binary, shell_config=True):
    if shell_config:
        launcher, needs_launcher, edits = configure_runtime(root, binary)
    else:
        launcher = root / '.local/bin/pi'
        if launcher.exists() and launcher.is_dir():
            raise ValueError(str(launcher) + ' is a directory.')
        needs_launcher = not launcher.is_symlink() or launcher.resolve() != binary.resolve()
        edits = {}
    paths = list(edits) + ([launcher] if needs_launcher else [])
    if not paths:
        return
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    backup = root / '.pi/agent/backups' / ('pi-runtime-' + stamp)
    backup.mkdir(parents=True, mode=0o700)
    records = []
    for path in paths:
        relative = path.relative_to(root)
        exists = os.path.lexists(path)
        records.append({'path': str(relative), 'existed': exists})
        if exists:
            saved = backup / relative
            saved.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, saved, follow_symlinks=False)
    atomic_write(backup / 'manifest.json', json.dumps({'relative_to': 'user home', 'files': records}, indent=2) + '\n')
    if needs_launcher:
        launcher.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(dir=launcher.parent, prefix='.pi-launcher-')
        os.close(fd)
        os.unlink(temporary)
        try:
            os.symlink(binary, temporary)
            os.replace(temporary, launcher)
        finally:
            if os.path.lexists(temporary):
                os.unlink(temporary)
    for path, text in edits.items():
        atomic_write(path, text)
    print('Runtime/PATH backup:', backup)


def apply_config(root):
    destination = root / '.pi' / 'agent'
    settings_file = destination / 'settings.json'
    original = json.loads(settings_file.read_text()) if settings_file.exists() else {}
    overlay = json.loads((REPO / 'config/settings.json').read_text())
    versions = json.loads((REPO / 'config/versions.json').read_text())
    merged = merge(original, overlay)
    # Preserve unrelated extensions; replace matching package versions, not append duplicates.
    package_names = versions['packages']
    def managed(entry):
        source = entry if isinstance(entry, str) else entry.get('source', '')
        return any(source == 'npm:' + name or source.startswith('npm:' + name + '@')
                   for name in package_names)
    merged['packages'] = [p for p in original.get('packages', []) if not managed(p)]
    merged['packages'] += ['npm:' + name + '@' + version for name, version in package_names.items()]
    # Existing provider-scoped overrides take precedence. Remove only profile-owned fields
    # for these roles, otherwise the promised model mapping might silently be overridden.
    scoped = merged['subagents'].get('agentOverridesByProvider', {})
    for entries in scoped.values():
        for role, profile in overlay['subagents']['agentOverrides'].items():
            if role in entries:
                for field in profile:
                    entries[role].pop(field, None)
    changes = {settings_file: json.dumps(merged, indent=2) + '\n'}
    changes.update({destination / 'agents' / f.name: f.read_text()
                    for f in sorted((REPO / 'agents').glob('*.md'))})
    changed = {p: content for p, content in changes.items()
               if not p.exists() or p.read_bytes() != content.encode('utf-8')}
    if not changed:
        print('Configuration already matches; no files changed.')
        return None
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    backup = destination / 'backups' / ('pi-agent-setup-' + stamp)
    backup.mkdir(parents=True, mode=0o700)
    manifest = []
    for path in changed:
        relative = path.relative_to(destination)
        existed = path.exists()
        manifest.append({'path': str(relative), 'existed': existed})
        if existed:
            saved = backup / relative
            saved.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, saved)
            saved.chmod(0o600)
    atomic_write(backup / 'manifest.json', json.dumps(manifest, indent=2) + '\n')
    for path, content in changed.items():
        atomic_write(path, content)
    print('Configuration:', destination)
    print('Backup:', backup)
    return backup


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path.home(), help='Home root; defaults to current user home')
    parser.add_argument('--config-only', action='store_true', help='Only apply files; do not download Pi or packages')
    parser.add_argument('--dry-run', action='store_true', help='Show destinations without writing or downloading')
    parser.add_argument('--no-shell-config', action='store_true', help='Do not manage PATH in shell startup files')
    args = parser.parse_args()
    root = args.root.expanduser().resolve()
    if hasattr(os, 'geteuid') and os.geteuid() == 0:
        parser.error('Run as your normal user, without sudo.')
    versions = json.loads((REPO / 'config/versions.json').read_text())
    if args.dry_run:
        print('Root:', root)
        print('Settings:', root / '.pi/agent/settings.json')
        print('Pi version:', versions['pi'])
        print('Packages:', json.dumps(versions['packages']))
        print('Mode:', 'configuration only' if args.config_only else 'install/update Pi, configuration and packages')
        print('Shell PATH:', 'unchanged' if args.config_only or args.no_shell_config else '.profile, .bashrc, .zshrc')
        return
    if not args.config_only:
        if os.name != 'posix':
            parser.error('Automatic installation supports Linux/macOS. Use WSL on Windows.')
        if not shutil.which('node') or not shutil.which('npm'):
            parser.error('Install Node.js >=22.19.0 and npm first.')
        version = subprocess.check_output(['node', '--version'], text=True).strip().lstrip('v')
        if tuple(map(int, version.split('.')[:3])) < (22, 19, 0):
            parser.error('Node.js >=22.19.0 is required.')
        prefix = root / '.local/share/pi-dev'
        binary = prefix / 'node_modules/.bin/pi'
        # Validate shell files before downloads or configuration changes.
        if not args.no_shell_config:
            configure_runtime(root, binary)
        subprocess.run(['npm', 'install', '--prefix', str(prefix), '--ignore-scripts', '--save-exact',
                        '@earendil-works/pi-coding-agent@' + versions['pi']], check=True)
    apply_config(root)
    if not args.config_only:
        env = os.environ.copy()
        env['PI_CODING_AGENT_DIR'] = str(root / '.pi/agent')
        for package, version in versions['packages'].items():
            subprocess.run([str(binary), 'install', 'npm:' + package + '@' + version], env=env, check=True)
        activate_runtime(root, binary, shell_config=not args.no_shell_config)
        subprocess.run([str(binary), '--version'], env=env, check=True)
        print('Pi installed/updated to the pinned profile. Existing credentials are preserved.')
        print('Open a new terminal, or run ' + str(root / '.local/bin/pi') + ' in this one.')
        print('If this is a new account, authenticate each provider with /login.')


if __name__ == '__main__':
    main()
