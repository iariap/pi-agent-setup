#!/usr/bin/env bash
# Private GitHub bootstrap. Run with gh api ... | bash -s -- [installer options].
set -euo pipefail

pi_setup_main() {
    local dependency setup_ref setup_commit setup_dir setup_cleanup
    for dependency in gh python3 tar mktemp; do
        if ! command -v "$dependency" >/dev/null 2>&1; then
            printf 'Missing prerequisite: %s\n' "$dependency" >&2
            return 1
        fi
    done
    if [[ "${EUID}" -eq 0 ]]; then
        printf 'Run as your normal user, without sudo.\n' >&2
        return 1
    fi
    gh auth status --hostname github.com >/dev/null 2>&1 || {
        printf 'Authenticate first: gh auth login --hostname github.com\n' >&2
        return 1
    }
    setup_ref="${PI_SETUP_REF:-main}"
    # Resolve once so all downloaded files come from the same commit.
    setup_commit="$(gh api --hostname github.com \
        "repos/iariap/pi-agent-setup/commits/${setup_ref}" --jq .sha)"
    if [[ ! "$setup_commit" =~ ^[0-9a-f]{40}$ ]]; then
        printf 'Could not resolve the requested Git revision.\n' >&2
        return 1
    fi
    setup_dir="$(mktemp -d "${TMPDIR:-/tmp}/pi-agent-setup.XXXXXXXX")"
    # Cleanup only the private directory created for this invocation.
    printf -v setup_cleanup 'rm -rf -- %q' "$setup_dir"
    trap "$setup_cleanup" EXIT
    trap 'exit 130' INT
    trap 'exit 143' TERM
    printf 'Downloading pi-agent-setup at %s\n' "$setup_commit"
    gh api --hostname github.com "repos/iariap/pi-agent-setup/tarball/${setup_commit}" \
        > "$setup_dir/source.tar.gz"
    mkdir "$setup_dir/source"
    tar -xzf "$setup_dir/source.tar.gz" -C "$setup_dir/source" --strip-components=1
    # Python resolves the user's home. Do not read the pipe carrying this script.
    python3 "$setup_dir/source/scripts/install.py" "$@" </dev/null
    rm -rf -- "$setup_dir"
    trap - EXIT INT TERM
}

pi_setup_main "$@"
