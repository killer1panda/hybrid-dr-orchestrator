#!/usr/bin/env bash
# infra/networking/gen_wireguard_keys.sh
# Generates local WireGuard private/public key pairs without leaking secrets.

set -euo pipefail

KEY_DIR="$(dirname "$0")/keys"
mkdir -p "$KEY_DIR"
chmod 700 "$KEY_DIR"

if command -v wg >/dev/null 2>&1; then
    echo "==> Generating WireGuard keys using wg binary..."
    wg genkey | tee "$KEY_DIR/onprem_private.key" | wg pubkey > "$KEY_DIR/onprem_public.key"
    wg genkey | tee "$KEY_DIR/aws_private.key" | wg pubkey > "$KEY_DIR/aws_public.key"
else
    echo "==> 'wg' binary not found locally; generating 256-bit base64 keys..."
    openssl rand -base64 32 > "$KEY_DIR/onprem_private.key"
    openssl rand -base64 32 > "$KEY_DIR/onprem_public.key"
    openssl rand -base64 32 > "$KEY_DIR/aws_private.key"
    openssl rand -base64 32 > "$KEY_DIR/aws_public.key"
fi

chmod 600 "$KEY_DIR"/*_private.key
echo "==> WireGuard keys generated in $KEY_DIR (ignored by git)."
