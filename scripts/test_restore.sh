#!/usr/bin/env bash
# scripts/test_restore.sh
# Restore test for the on-prem backups:
#  1. Reads backups/base/latest.txt and restores that base backup into a throwaway Docker volume.
#  2. Starts Postgres in recovery mode, replaying every archived WAL segment from S3, and waits for promotion.
#  3. Checks the tables are readable and measures backup lag: verification time minus the newest
#     rpo_probe row. This is the data you would lose if the site died at that moment. Fails above the threshold.
#     (Drill RPO against a real failure-injection time is measured in Phase 6.)
#  4. Appends a pass/fail event to audit/restore-tests.jsonl; posts failures to DR_ALERT_WEBHOOK_URL if set.
set -euo pipefail

usage() {
  cat <<USAGE
Usage: $(basename "$0") [--keep]

Options:
  --keep      Leave the restored container running for inspection
              (clean up later: docker rm -f restore-test-db; docker volume rm dr_restore_vol)
  -h, --help  Show this help.

Environment:
  RPO_THRESHOLD_SECONDS     Maximum acceptable backup lag in seconds (default 300)
  RECOVERY_TIMEOUT_SECONDS  Maximum time to wait for WAL replay (default 300)
USAGE
}

KEEP=false
while [[ $# -gt 0 ]]; do
  case "$1" in
    --keep) KEEP=true; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
done

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="$ROOT/infra/onprem/.env"
IMAGE="hybrid-dr/onprem-db:16"
CONTAINER="restore-test-db"
VOLUME="dr_restore_vol"
AUDIT_FILE="$ROOT/audit/restore-tests.jsonl"
RPO_THRESHOLD_SECONDS="${RPO_THRESHOLD_SECONDS:-300}"
RECOVERY_TIMEOUT_SECONDS="${RECOVERY_TIMEOUT_SECONDS:-300}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing $ENV_FILE (copy infra/onprem/.env.example and fill it in)" >&2
  exit 1
fi
env_get() { grep -E "^$1=" "$ENV_FILE" | tail -n1 | cut -d= -f2- || true; }
PG_USER="$(env_get POSTGRES_USER)"
PG_DB="$(env_get POSTGRES_DB)"
WEBHOOK="$(env_get DR_ALERT_WEBHOOK_URL)"
if [[ -z "$PG_USER" || -z "$PG_DB" ]]; then
  echo "POSTGRES_USER and POSTGRES_DB must be set in $ENV_FILE" >&2
  exit 1
fi

started_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
step="init"
status="fail"
base_backup=""
replay_seconds="null"
rpo_seconds="null"
items_count="null"
probe_rows="null"
missing_probe_ids="null"

finish() {
  local failed_step="null"
  [[ "$status" == "pass" ]] || failed_step="\"$step\""
  mkdir -p "$(dirname "$AUDIT_FILE")"
  local event
  event="$(printf '{"event":"restore_test","status":"%s","failed_step":%s,"started_at":"%s","finished_at":"%s","base_backup":"%s","replay_seconds":%s,"backup_lag_seconds":%s,"threshold_seconds":%s,"items":%s,"probe_rows":%s,"missing_probe_ids":%s}' \
    "$status" "$failed_step" "$started_at" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$base_backup" \
    "$replay_seconds" "$rpo_seconds" "$RPO_THRESHOLD_SECONDS" "$items_count" "$probe_rows" "$missing_probe_ids")"
  echo "$event" >> "$AUDIT_FILE"
  echo "==> Audit event: $event"
  if [[ "$status" != "pass" && -n "$WEBHOOK" ]]; then
    local msg="Hybrid DR restore test FAILED at step '$step' (started $started_at). See audit/restore-tests.jsonl."
    curl -fsS -m 10 -X POST -H 'Content-Type: application/json' \
      -d "{\"text\":\"$msg\",\"content\":\"$msg\"}" "$WEBHOOK" >/dev/null || echo "WARN: alert webhook failed" >&2
  fi
  if [[ "$KEEP" != true ]]; then
    docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
    docker volume rm -f "$VOLUME" >/dev/null 2>&1 || true
  fi
}
trap finish EXIT

q() { docker exec "$CONTAINER" psql -U "$PG_USER" -d "$PG_DB" -tAX -v ON_ERROR_STOP=1 -c "$1"; }

step="check_image"
if ! docker image inspect "$IMAGE" >/dev/null 2>&1; then
  echo "Image $IMAGE not found; run 'make lab-up' first" >&2
  exit 1
fi

step="read_latest_pointer"
echo "==> Reading latest base backup pointer from S3..."
pointer="$(docker run --rm --env-file "$ENV_FILE" --entrypoint bash "$IMAGE" -c \
  '. /usr/local/bin/dr_common.sh && dr_require_account && aws s3 cp "s3://${DR_BACKUP_BUCKET}/backups/base/latest.txt" -')"
read -r source_sysid backup_name <<<"$pointer"
if [[ -z "${source_sysid:-}" || -z "${backup_name:-}" ]]; then
  echo "latest.txt is malformed or from the old format: '$pointer' (run 'make backup' first)" >&2
  exit 1
fi
base_backup="backups/base/${source_sysid}/${backup_name}"
echo "    cluster system id: $source_sysid"
echo "    base backup:       $base_backup"

step="extract_base_backup"
echo "==> Restoring base backup into volume $VOLUME..."
docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
docker volume rm -f "$VOLUME" >/dev/null 2>&1 || true
docker volume create "$VOLUME" >/dev/null
docker run --rm --env-file "$ENV_FILE" -e BASE_KEY="$base_backup" -v "$VOLUME":/restore --entrypoint bash "$IMAGE" -c '
  set -euo pipefail
  . /usr/local/bin/dr_common.sh
  aws s3 cp "s3://${DR_BACKUP_BUCKET}/${BASE_KEY}" - | dr_decrypt | tar -xzf - -C /restore
  touch /restore/recovery.signal
  chown -R postgres:postgres /restore
  chmod 0700 /restore'

step="start_recovery"
echo "==> Starting Postgres in recovery mode (replaying WAL from S3)..."
replay_start="$(date +%s)"
# archive_mode=off: the restored copy must never upload its own WAL into the real archive.
docker run -d --name "$CONTAINER" --env-file "$ENV_FILE" -e DR_SOURCE_SYSTEM_ID="$source_sysid" \
  -v "$VOLUME":/var/lib/postgresql/data "$IMAGE" \
  postgres -c archive_mode=off -c "restore_command=/usr/local/bin/restore_wal.sh %f %p" >/dev/null

step="wait_for_promotion"
deadline=$(( replay_start + RECOVERY_TIMEOUT_SECONDS ))
while :; do
  if [[ "$(docker inspect -f '{{.State.Running}}' "$CONTAINER" 2>/dev/null)" != "true" ]]; then
    echo "Restore container stopped unexpectedly. Last log lines:" >&2
    docker logs --tail 30 "$CONTAINER" >&2 || true
    exit 1
  fi
  if in_recovery="$(q 'SELECT pg_is_in_recovery()' 2>/dev/null)" && [[ "$in_recovery" == "f" ]]; then
    break
  fi
  if (( $(date +%s) > deadline )); then
    echo "Timed out after ${RECOVERY_TIMEOUT_SECONDS}s waiting for recovery to finish" >&2
    docker logs --tail 30 "$CONTAINER" >&2 || true
    exit 1
  fi
  sleep 2
done
replay_seconds=$(( $(date +%s) - replay_start ))
echo "    recovery finished and promoted after ${replay_seconds}s"

step="verify_data"
items_count="$(q 'SELECT count(*) FROM items')"
probe_rows="$(q 'SELECT count(*) FROM rpo_probe')"
if (( probe_rows == 0 )); then
  echo "rpo_probe is empty in the restored database" >&2
  exit 1
fi
missing_probe_ids="$(q 'SELECT (max(probe_id) - min(probe_id) + 1) - count(*) FROM rpo_probe')"
newest_probe="$(q 'SELECT max(written_at_utc) FROM rpo_probe')"
rpo_seconds="$(q 'SELECT floor(extract(epoch FROM (clock_timestamp() - max(written_at_utc))))::int FROM rpo_probe')"
echo "    items rows:      $items_count"
echo "    rpo_probe rows:  $probe_rows (ids missing from sequence: $missing_probe_ids)"
echo "    newest probe:    $newest_probe"
echo "    backup lag:      ${rpo_seconds}s (threshold ${RPO_THRESHOLD_SECONDS}s)"

step="check_backup_lag"
if (( rpo_seconds > RPO_THRESHOLD_SECONDS )); then
  echo "Backup lag ${rpo_seconds}s exceeds threshold ${RPO_THRESHOLD_SECONDS}s" >&2
  exit 1
fi
status="pass"
echo "==> [PASS] Restore test passed"
