#!/usr/bin/env bash
# scripts/backup_base.sh
# Generates a full pg_basebackup snapshot and uploads it to S3.

set -euo pipefail

BUCKET_NAME="${DR_BACKUP_BUCKET:-hybrid-dr-backups-758579869433-ap-southeast-2}"
AWS_PROFILE="${AWS_PROFILE:-dr-sandbox}"
AWS_REGION="ap-southeast-2"
TIMESTAMP=$(date -u +"%Y%m%dT%H%M%SZ")
BACKUP_TAR="/tmp/basebackup_${TIMESTAMP}.tar.gz"

echo "==> [$(date -u)] Initiating full PostgreSQL base backup..."

docker exec onprem-db pg_basebackup \
    -U dr_user \
    -D - \
    -Ft \
    -z \
    -X fetch \
    -c fast > "$BACKUP_TAR"

echo "==> Base backup archive created: $(du -h "$BACKUP_TAR" | cut -f1)"

echo "==> Uploading base backup to s3://${BUCKET_NAME}/backups/base/..."
aws s3 cp "$BACKUP_TAR" "s3://${BUCKET_NAME}/backups/base/basebackup_${TIMESTAMP}.tar.gz" \
    --profile "$AWS_PROFILE" \
    --region "$AWS_REGION"

# Write latest manifest pointer
echo "basebackup_${TIMESTAMP}.tar.gz" | aws s3 cp - "s3://${BUCKET_NAME}/backups/base/latest.txt" \
    --profile "$AWS_PROFILE" \
    --region "$AWS_REGION"

rm -f "$BACKUP_TAR"
echo "==> Full base backup completed successfully."
