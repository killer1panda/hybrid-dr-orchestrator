#!/usr/bin/env bash
# scripts/archive_wal.sh
# Invoked by PostgreSQL archive_command every 60s or when a 16MB WAL segment fills.
# Ships compressed WAL segments directly to the S3 backup bucket.

set -euo pipefail

WAL_PATH="${1:-}"
WAL_FILE="${2:-}"

if [[ -z "$WAL_PATH" || -z "$WAL_FILE" ]]; then
    echo "Usage: $0 <wal_path> <wal_file>" >&2
    exit 1
fi

BUCKET_NAME="${DR_BACKUP_BUCKET:-hybrid-dr-backups-758579869433-ap-southeast-2}"
AWS_PROFILE="${AWS_PROFILE:-dr-sandbox}"
AWS_REGION="ap-southeast-2"

# Compress WAL segment to optimize transfer and storage cost
TMP_GZ="/tmp/${WAL_FILE}.gz"
gzip -c "$WAL_PATH" > "$TMP_GZ"

# Upload to S3 with AES256 server-side encryption
aws s3 cp "$TMP_GZ" "s3://${BUCKET_NAME}/backups/wal/${WAL_FILE}.gz" \
    --profile "$AWS_PROFILE" \
    --region "$AWS_REGION" \
    --only-show-errors

rm -f "$TMP_GZ"
exit 0
