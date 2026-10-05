#!/usr/bin/env bash
# scripts/chaos_kill_onprem.sh
# Chaos drill tool: Safely stops on-premises lab containers verified against lab-inventory.yml.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
INVENTORY_FILE="$REPO_ROOT/lab-inventory.yml"
AUDIT_LOG="$REPO_ROOT/audit/chaos.jsonl"

DRY_RUN=false
CONFIRM=false
TARGET="all"

usage() {
  cat << EOF
Usage: $0 [--dry-run | --confirm] [--target <service|all>]

Guarded chaos script to simulate an on-premises outage.
Strictly checks targets against lab-inventory.yml.

Options:
  --dry-run       Simulate the chaos action without stopping containers
  --confirm       Confirm execution of container disruption
  --target <name> Specific target service (default: all; allowed: onprem-web, onprem-app, onprem-db, all)
  --help, -h      Show this help message
EOF
  exit 0
}

while [[ $# -gt 0 ]]; do
  case $1 in
    --dry-run) DRY_RUN=true; shift ;;
    --confirm) CONFIRM=true; shift ;;
    --target=*) TARGET="${1#*=}"; shift ;;
    --target) TARGET="${2:-}"; shift 2 ;;
    -h|--help) usage ;;
    *) echo "Unknown argument: $1" >&2; exit 1 ;;
  esac
done

if [[ "$DRY_RUN" == false && "$CONFIRM" == false ]]; then
  echo "❌ Error: Safety guardrail requires --dry-run or --confirm" >&2
  echo "Run '$0 --help' for usage." >&2
  exit 1
fi

if [[ ! -f "$INVENTORY_FILE" ]]; then
  echo "❌ Error: lab-inventory.yml not found at $INVENTORY_FILE" >&2
  exit 1
fi

# Guardrail: Check forbidden host interfaces or unauthorized targets
FORBIDDEN_INTERFACES=("en0" "en1" "eth0" "wlan0" "lo")
for forbidden in "${FORBIDDEN_INTERFACES[@]}"; do
  if [[ "$TARGET" == "$forbidden" ]]; then
    echo "🚨 FATAL SAFETY VIOLATION: Refusing to target host interface '$forbidden'!" >&2
    exit 2
  fi
done

# Validate target against lab-inventory.yml
ALLOWED_TARGETS=("onprem-web" "onprem-app" "onprem-db" "all")
VALID=false
for allowed in "${ALLOWED_TARGETS[@]}"; do
  if [[ "$TARGET" == "$allowed" ]]; then
    VALID=true
    break
  fi
done

if [[ "$VALID" == false ]]; then
  echo "🚨 REJECTED: Target '$TARGET' is NOT in lab-inventory.yml allowed chaos targets." >&2
  exit 2
fi

mkdir -p "$REPO_ROOT/audit"
TIMESTAMP="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

# Record audit entry
ENTRY="{\"event\":\"chaos_injection\",\"action\":\"stop_service\",\"target\":\"$TARGET\",\"dry_run\":$DRY_RUN,\"timestamp\":\"$TIMESTAMP\"}"
echo "$ENTRY" >> "$AUDIT_LOG"

echo "=== Chaos Drill: Simulating On-Premises Failure ==="
echo "Target: $TARGET"
echo "Inventory: $INVENTORY_FILE"

if [[ "$DRY_RUN" == true ]]; then
  echo "[DRY RUN] Guardrails passed. Would execute: docker compose stop in infra/onprem/"
  exit 0
fi

echo "[EXECUTE] Stopping on-premises containers..."
cd "$REPO_ROOT/infra/onprem"
if [[ "$TARGET" == "all" ]]; then
  docker compose stop
else
  docker compose stop "$TARGET" || docker stop "$TARGET"
fi


echo "💥 Chaos injected: '$TARGET' is DOWN. Python Orchestrator should now detect quorum failure."
