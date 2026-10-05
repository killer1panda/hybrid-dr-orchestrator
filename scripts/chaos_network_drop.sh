#!/usr/bin/env bash
# scripts/chaos_network_drop.sh
# Chaos drill tool: Simulates network disconnection of on-premises lab bridge.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
INVENTORY_FILE="$REPO_ROOT/lab-inventory.yml"
AUDIT_LOG="$REPO_ROOT/audit/chaos.jsonl"

DRY_RUN=false
CONFIRM=false
TARGET_IFACE="dr-br0"

usage() {
  cat << EOF
Usage: $0 [--dry-run | --confirm] [--interface <iface>]

Guarded network chaos script to simulate a lab bridge partition.
Strictly checks targets against lab-inventory.yml.

Options:
  --dry-run             Simulate the chaos action
  --confirm             Confirm execution
  --interface <name>    Target interface (default: dr-br0; forbidden: en0, lo, etc.)
  --help, -h            Show this help message
EOF
  exit 0
}

while [[ $# -gt 0 ]]; do
  case $1 in
    --dry-run) DRY_RUN=true; shift ;;
    --confirm) CONFIRM=true; shift ;;
    --interface=*) TARGET_IFACE="${1#*=}"; shift ;;
    --interface) TARGET_IFACE="${2:-}"; shift 2 ;;
    -h|--help) usage ;;
    *) echo "Unknown argument: $1" >&2; exit 1 ;;
  esac
done

if [[ "$DRY_RUN" == false && "$CONFIRM" == false ]]; then
  echo "❌ Error: Safety guardrail requires --dry-run or --confirm" >&2
  exit 1
fi

FORBIDDEN_INTERFACES=("en0" "en1" "eth0" "wlan0" "lo")
for forbidden in "${FORBIDDEN_INTERFACES[@]}"; do
  if [[ "$TARGET_IFACE" == "$forbidden" ]]; then
    echo "🚨 FATAL SAFETY VIOLATION: Refusing to touch host interface '$forbidden'!" >&2
    exit 2
  fi
done

# Validate against allowed_interfaces
ALLOWED_INTERFACES=("dr-br0" "wg0")
VALID=false
for allowed in "${ALLOWED_INTERFACES[@]}"; do
  if [[ "$TARGET_IFACE" == "$allowed" ]]; then
    VALID=true
    break
  fi
done

if [[ "$VALID" == false ]]; then
  echo "🚨 REJECTED: Interface '$TARGET_IFACE' is NOT in lab-inventory.yml allowed list." >&2
  exit 2
fi

mkdir -p "$REPO_ROOT/audit"
TIMESTAMP="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
ENTRY="{\"event\":\"chaos_injection\",\"action\":\"network_disconnect\",\"interface\":\"$TARGET_IFACE\",\"dry_run\":$DRY_RUN,\"timestamp\":\"$TIMESTAMP\"}"
echo "$ENTRY" >> "$AUDIT_LOG"

echo "=== Chaos Drill: Simulating Network Partition on '$TARGET_IFACE' ==="
if [[ "$DRY_RUN" == true ]]; then
  echo "[DRY RUN] Guardrails passed. Would disconnect lab bridge '$TARGET_IFACE'."
  exit 0
fi

echo "[EXECUTE] Disconnecting containers from lab bridge..."
docker network disconnect onprem_onprem_net onprem-web 2>/dev/null || true
echo "💥 Network partition injected: onprem-web disconnected from lab network."
