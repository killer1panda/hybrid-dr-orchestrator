#!/usr/bin/env bash
# infra/networking/gen_wireguard_keys.sh
# Generates WireGuard key pairs for the on-prem and AWS tunnel ends.
# Keys stay on this machine: infra/networking/keys/ is gitignored (*.key). Never print or commit them.
set -euo pipefail

usage() {
  cat <<USAGE
Usage: $(basename "$0") [--check | --force]

  (no flag)  Generate keys; refuses to overwrite existing ones.
  --check    Verify each public key is derived from its private key (prints no key material).
  --force    Regenerate and overwrite existing keys.
  -h, --help Show this help.

Requires the 'wg' tool: brew install wireguard-tools
USAGE
}

MODE=generate
case "${1:-}" in
  "") ;;
  --check) MODE=check ;;
  --force) MODE=force ;;
  -h|--help) usage; exit 0 ;;
  *) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
esac

if ! command -v wg >/dev/null 2>&1; then
  echo "ERROR: 'wg' not found. Install it with: brew install wireguard-tools" >&2
  exit 1
fi

KEY_DIR="$(cd "$(dirname "$0")" && pwd)/keys"
umask 077
mkdir -p "$KEY_DIR"
chmod 700 "$KEY_DIR"

status=0
for side in onprem aws; do
  priv="$KEY_DIR/${side}_private.key"
  pub="$KEY_DIR/${side}_public.key"
  if [[ "$MODE" == check ]]; then
    if [[ ! -f "$priv" || ! -f "$pub" ]]; then
      echo "$side: MISSING"
      status=1
    elif [[ "$(wg pubkey < "$priv")" == "$(cat "$pub")" ]]; then
      echo "$side: OK (public key matches private key)"
    else
      echo "$side: MISMATCH (public key not derived from private key; rerun with --force)"
      status=1
    fi
    continue
  fi
  if [[ -f "$priv" && "$MODE" != force ]]; then
    echo "ERROR: $priv exists; use --check to verify or --force to regenerate" >&2
    exit 1
  fi
  wg genkey > "$priv"
  wg pubkey < "$priv" > "$pub"
  chmod 600 "$priv"
  chmod 644 "$pub"
  echo "$side: generated"
done
exit "$status"
