#!/usr/bin/env bash
# infra/onprem/db/dr_common.sh
# Shared helpers for backup scripts that run inside the onprem-db container. Sourced, not executed.

# Refuse to touch AWS unless the credentials belong to DR_ALLOWED_ACCOUNT_ID (safety rule).
dr_require_account() {
  if [[ -z "${DR_ALLOWED_ACCOUNT_ID:-}" ]]; then
    echo "dr_common: DR_ALLOWED_ACCOUNT_ID is not set; refusing to call AWS" >&2
    return 1
  fi
  local actual
  if ! actual="$(aws sts get-caller-identity --query Account --output text 2>/dev/null)"; then
    echo "dr_common: could not read caller identity (check AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY)" >&2
    return 1
  fi
  if [[ "$actual" != "$DR_ALLOWED_ACCOUNT_ID" ]]; then
    echo "dr_common: credentials belong to account $actual, expected $DR_ALLOWED_ACCOUNT_ID; refusing" >&2
    return 1
  fi
}

# The system identifier changes whenever the cluster is re-initialised. Prefixing S3 keys with it
# stops a rebuilt lab from overwriting, or being mixed up with, an older cluster's WAL.
dr_system_id() {
  pg_controldata "${PGDATA:?PGDATA is not set}" | awk -F':[[:space:]]*' '/^Database system identifier/ {print $2}'
}

# Repository-level encryption on top of S3 SSE. CBC has no MAC; gzip's CRC detects corruption on restore.
dr_encrypt() {
  openssl enc -aes-256-cbc -pbkdf2 -iter 200000 -salt -pass env:BACKUP_ENCRYPTION_PASSPHRASE
}

dr_decrypt() {
  openssl enc -d -aes-256-cbc -pbkdf2 -iter 200000 -pass env:BACKUP_ENCRYPTION_PASSPHRASE
}
