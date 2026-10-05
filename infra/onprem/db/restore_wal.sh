#!/usr/bin/env bash
# infra/onprem/db/restore_wal.sh
# PostgreSQL restore_command: restore_wal.sh %f %p
# Fetches, decrypts and decompresses one WAL segment from S3 for the cluster DR_SOURCE_SYSTEM_ID.
# A missing segment is the normal end of recovery, so it exits non-zero quietly.
set -euo pipefail
. /usr/local/bin/dr_common.sh

wal_name="${1:?usage: restore_wal.sh <%f> <%p>}"
dest="${2:?usage: restore_wal.sh <%f> <%p>}"
: "${DR_BACKUP_BUCKET:?DR_BACKUP_BUCKET is not set}"
: "${BACKUP_ENCRYPTION_PASSPHRASE:?BACKUP_ENCRYPTION_PASSPHRASE is not set}"
: "${DR_SOURCE_SYSTEM_ID:?DR_SOURCE_SYSTEM_ID is not set}"

key="backups/wal/${DR_SOURCE_SYSTEM_ID}/${wal_name}.gz.enc"
tmp="$(mktemp)"
trap 'rm -f "$tmp"' EXIT

if ! aws s3 cp "s3://${DR_BACKUP_BUCKET}/${key}" "$tmp" --only-show-errors 2>/dev/null; then
  exit 1
fi
dr_decrypt < "$tmp" | gunzip -c > "$dest"
