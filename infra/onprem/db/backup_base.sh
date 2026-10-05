#!/usr/bin/env bash
# infra/onprem/db/backup_base.sh
# Full base backup: pg_basebackup -> gzip -> encrypt -> S3, then updates backups/base/latest.txt
# with "<system-id> <file-name>" so restores know which WAL prefix to replay.
set -euo pipefail
. /usr/local/bin/dr_common.sh

: "${DR_BACKUP_BUCKET:?DR_BACKUP_BUCKET is not set}"
: "${BACKUP_ENCRYPTION_PASSPHRASE:?BACKUP_ENCRYPTION_PASSPHRASE is not set}"
: "${POSTGRES_USER:?POSTGRES_USER is not set}"

dr_require_account
sysid="$(dr_system_id)"
ts="$(date -u +%Y%m%dT%H%M%SZ)"
name="basebackup_${ts}.tar.gz.enc"
key="backups/base/${sysid}/${name}"

tmp="$(mktemp)"
trap 'rm -f "$tmp"' EXIT

echo "backup_base: starting base backup of cluster $sysid"
pg_basebackup -U "$POSTGRES_USER" -D - -Ft -z -X fetch -c fast | dr_encrypt > "$tmp"
aws s3 cp "$tmp" "s3://${DR_BACKUP_BUCKET}/${key}" --only-show-errors
printf '%s %s\n' "$sysid" "$name" | aws s3 cp - "s3://${DR_BACKUP_BUCKET}/backups/base/latest.txt" --only-show-errors
echo "backup_base: uploaded s3://${DR_BACKUP_BUCKET}/${key} ($(du -h "$tmp" | cut -f1))"
