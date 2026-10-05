#!/usr/bin/env bash
set -euo pipefail

# scripts/test_logical_cdc.sh
# Verifies continuous PostgreSQL Logical Replication (CDC) stream functionality
# using logical replication slots and test_decoding plugin.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "=========================================================="
echo "  PostgreSQL Continuous Logical Replication (CDC) Verification"
echo "=========================================================="

# 1. Check container health
echo "[1/6] Verifying onprem-db container status..."
if [[ "$(docker inspect -f '{{.State.Running}}' onprem-db 2>/dev/null || echo 'false')" != "true" ]]; then
  echo "Error: onprem-db container is not running. Please start it with 'make onprem-up'." >&2
  exit 1
fi
echo "  -> onprem-db is running."

# 2. Check wal_level
echo "[2/6] Verifying PostgreSQL wal_level..."
WAL_LEVEL=$(docker compose -f "${REPO_ROOT}/infra/onprem/docker-compose.yml" exec -T onprem-db psql -U dr_user -d dr_app -t -A -c "SHOW wal_level;")
if [[ "${WAL_LEVEL}" != "logical" ]]; then
  echo "Error: wal_level is '${WAL_LEVEL}', expected 'logical'." >&2
  exit 1
fi
echo "  -> wal_level is set to '${WAL_LEVEL}' (Logical Replication Enabled)."

# 3. Apply CDC setup SQL (Publication & Slot)
echo "[3/6] Configuring CDC Publication and Logical Replication Slot..."
docker compose -f "${REPO_ROOT}/infra/onprem/docker-compose.yml" exec -T onprem-db psql -U dr_user -d dr_app < "${REPO_ROOT}/infra/onprem/cdc/setup_logical_replication.sql"
echo "  -> Publication 'dr_cdc_publication' and Slot 'dr_cdc_slot' verified."

# 4. Flush any historical backlog and insert canary transaction
CANARY_TAG="cdc-canary-$(date +%s)-$RANDOM"
echo "[4/6] Flushing slot backlog and injecting transaction (Tag: ${CANARY_TAG})..."
docker compose -f "${REPO_ROOT}/infra/onprem/docker-compose.yml" exec -T onprem-db psql -U dr_user -d dr_app -c "
SELECT pg_logical_slot_get_changes('dr_cdc_slot', NULL, NULL);
" > /dev/null

docker compose -f "${REPO_ROOT}/infra/onprem/docker-compose.yml" exec -T onprem-db psql -U dr_user -d dr_app -c "
INSERT INTO rpo_probe (cluster_node)
VALUES ('${CANARY_TAG}');
" > /dev/null

# 5. Peek and decode CDC change stream from replication slot
echo "[5/6] Interrogating logical replication slot for change stream events..."
CDC_OUTPUT=$(docker compose -f "${REPO_ROOT}/infra/onprem/docker-compose.yml" exec -T onprem-db psql -U dr_user -d dr_app -t -A -c "
SELECT data FROM pg_logical_slot_peek_changes('dr_cdc_slot', NULL, NULL) WHERE data LIKE '%${CANARY_TAG}%';
")

if [[ -z "${CDC_OUTPUT}" ]]; then
  echo "Error: Canary transaction was not detected in CDC replication slot!" >&2
  exit 1
fi

echo "  -> CDC Event Captured:"
echo "     ${CDC_OUTPUT}"

# 6. Consume slot changes to advance LSN
echo "[6/6] Consuming change stream and advancing replication slot LSN..."
CONSUMED_COUNT=$(docker compose -f "${REPO_ROOT}/infra/onprem/docker-compose.yml" exec -T onprem-db psql -U dr_user -d dr_app -t -A -c "
SELECT COUNT(*) FROM pg_logical_slot_get_changes('dr_cdc_slot', NULL, NULL);
")
echo "  -> Successfully acknowledged and consumed ${CONSUMED_COUNT} LSN delta records."

echo "=========================================================="
echo "✅ Logical Replication CDC test PASSED successfully!"
echo "   Continuous real-time change data capture is verified."
echo "=========================================================="
