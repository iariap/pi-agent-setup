#!/usr/bin/env python3
"""Aplica el perfil de enrutamiento de OpenCode (config + agentes).

Fusiona opencode/opencode.json del repo sobre ~/.config/opencode/opencode.json
(preservando campos ajenos al perfil, p. ej. proveedores locales) y copia los
agentes de opencode/agents/ a ~/.config/opencode/agents/. Hace backup de todo
lo que reemplaza. Con --dry-run muestra los destinos sin escribir.
"""

import argparse
import copy
import json
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


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
    fd, name = tempfile.mkstemp(dir=path.parent, prefix='.opencode-setup-')
    try:
        import os
        with os.fdopen(fd, 'w') as stream:
            stream.write(text)
        shutil.move(name, path)
    except BaseException:
        Path(name).unlink(missing_ok=True)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run', action='store_true', help='Show destinations without writing')
    args = parser.parse_args()

    config_dir = Path.home() / '.config' / 'opencode'
    settings_file = config_dir / 'opencode.json'
    original = {}
    if settings_file.exists():
        try:
            original = json.loads(settings_file.read_text())
        except json.JSONDecodeError as exc:
            sys.exit(f'{settings_file} no es JSON válido: {exc}')

    overlay = json.loads((REPO / 'opencode/opencode.json').read_text())
    merged = merge(original, overlay)

    changes = {settings_file: json.dumps(merged, indent=2) + '\n'}
    agents_source = REPO / 'opencode/agents'
    for source in sorted(agents_source.glob('*.md')):
        changes[config_dir / 'agents' / source.name] = source.read_text()

    changed = {p: content for p, content in changes.items()
               if not p.exists() or p.read_bytes() != content.encode('utf-8')}

    print('Destinos:')
    print('  Config:', settings_file)
    print('  Agentes:', config_dir / 'agents')
    if not changed:
        print('La configuración ya coincide; no hay cambios.')
        return

    if args.dry_run:
        print('Cambios pendientes:')
        for path in sorted(changed):
            print('  *', path)
        return

    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    backup = config_dir / 'backups' / ('opencode-setup-' + stamp)
    backup.mkdir(parents=True, mode=0o700)
    manifest = []
    for path, content in changed.items():
        relative = path.relative_to(config_dir)
        existed = path.exists()
        manifest.append({'path': str(relative), 'existed': existed})
        if existed:
            saved = backup / relative
            saved.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, saved)
            saved.chmod(0o600)
    (backup / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')

    for path, content in changed.items():
        atomic_write(path, content)
    print('Configuración aplicada:', config_dir)
    print('Backup:', backup)


if __name__ == '__main__':
    main()
