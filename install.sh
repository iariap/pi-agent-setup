#!/usr/bin/env bash
# Public GitHub bootstrap. Run with curl -fsSL URL | bash -s -- [installer options].
set -euo pipefail

pi_setup_main() {
    local dependency setup_ref setup_commit setup_dir setup_cleanup
    for dependency in curl python3 tar mktemp; do
        if ! command -v "$dependency" >/dev/null 2>&1; then
            printf 'Missing prerequisite: %s\n' "$dependency" >&2
            return 1
        fi
    done
    if [[ "${EUID}" -eq 0 ]]; then
        printf 'Run as your normal user, without sudo.\n' >&2
        return 1
    fi
    setup_ref="${PI_SETUP_REF:-main}"
    setup_dir="$(mktemp -d "${TMPDIR:-/tmp}/pi-agent-setup.XXXXXXXX")"
    # Cleanup only the private directory created for this invocation.
    printf -v setup_cleanup 'rm -rf -- %q' "$setup_dir"
    trap "$setup_cleanup" EXIT
    trap 'exit 130' INT
    trap 'exit 143' TERM
    printf 'Downloading pi-agent-setup ref %s\n' "$setup_ref"
    curl --fail --silent --show-error --location \
        "https://codeload.github.com/iariap/pi-agent-setup/tar.gz/${setup_ref}" \
        --output "$setup_dir/source.tar.gz"
    mkdir "$setup_dir/source"
    tar -xzf "$setup_dir/source.tar.gz" -C "$setup_dir/source" --strip-components=1
    # Python resolves the user's home. Do not read the pipe carrying this script.
    python3 "$setup_dir/source/scripts/install.py" "$@" </dev/null
    rm -rf -- "$setup_dir"
    trap - EXIT INT TERM
}

pi_setup_main "$@"
