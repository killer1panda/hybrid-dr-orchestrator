#!/usr/bin/env bash
# scripts/backup_base.sh
# Takes an encrypted full base backup of the on-prem database and uploads it to S3.
# Runs inside onprem-db with the backup-writer identity from infra/onprem/.env.
set -euo pipefail
if [[ "${1:-}" =~ ^(-h|--help)$ ]]; then
  echo "Usage: $(basename "$0")"
  echo "Runs /usr/local/bin/backup_base.sh inside the onprem-db container. Requires 'make lab-up'."
  exit 0
fi
docker exec -u postgres onprem-db /usr/local/bin/backup_base.sh
