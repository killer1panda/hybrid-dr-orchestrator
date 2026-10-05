#!/usr/bin/env bash
# infra/onprem/db/archive_wal.sh
# PostgreSQL archive_command: archive_wal.sh %p %f
# Compresses, encrypts and uploads one WAL segment to s3://$DR_BACKUP_BUCKET/backups/wal/<system-id>/.
# Exit 0 only once the segment is in S3; any non-zero exit makes Postgres keep the segment and retry.
set -euo pipefail
. /usr/local/bin/dr_common.sh

wal_path="${1:?usage: archive_wal.sh <%p> <%f>}"
wal_name="${2:?usage: archive_wal.sh <%p> <%f>}"
: "${DR_BACKUP_BUCKET:?DR_BACKUP_BUCKET is not set}"
: "${BACKUP_ENCRYPTION_PASSPHRASE:?BACKUP_ENCRYPTION_PASSPHRASE is not set}"

dr_require_account
sysid="$(dr_system_id)"
key="backups/wal/${sysid}/${wal_name}.gz.enc"

# Postgres retries a segment if it crashed after uploading but before recording success.
if aws s3api head-object --bucket "$DR_BACKUP_BUCKET" --key "$key" >/dev/null 2>&1; then
  echo "archive_wal: $key already in S3; treating as archived" >&2
  exit 0
fi

tmp="$(mktemp)"
trap 'rm -f "$tmp"' EXIT
gzip -c "$wal_path" | dr_encrypt > "$tmp"
aws s3 cp "$tmp" "s3://${DR_BACKUP_BUCKET}/${key}" --only-show-errors
