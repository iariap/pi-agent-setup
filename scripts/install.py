#!/usr/bin/env python3
"""Install a portable Pi profile under the current user's home; never copy auth."""
import argparse
import copy
import json
import os
from pathlib import Path
import shutil
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
               if not p.exists() or p.read_text() != content}
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
        print('Mode:', 'configuration only' if args.config_only else 'install Pi, configuration and packages')
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
        launcher = root / '.local/bin/pi'
        binary = prefix / 'node_modules/.bin/pi'
        if os.path.lexists(launcher) and (not launcher.is_symlink() or launcher.resolve() != binary.resolve()):
            parser.error(str(launcher) + ' already exists and belongs to another installation; use --config-only.')
        subprocess.run(['npm', 'install', '--prefix', str(prefix), '--ignore-scripts', '--save-exact',
                        '@earendil-works/pi-coding-agent@' + versions['pi']], check=True)
        launcher.parent.mkdir(parents=True, exist_ok=True)
        if not os.path.lexists(launcher):
            launcher.symlink_to(binary)
    apply_config(root)
    if not args.config_only:
        env = os.environ.copy()
        env['PI_CODING_AGENT_DIR'] = str(root / '.pi/agent')
        for package, version in versions['packages'].items():
            subprocess.run([str(binary), 'install', 'npm:' + package + '@' + version], env=env, check=True)
        print('Add ~/.local/bin to PATH, then run pi and authenticate each provider with /login.')


if __name__ == '__main__':
    main()
