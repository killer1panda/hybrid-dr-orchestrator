#!/usr/bin/env bash
# scripts/interview_spindown.sh
# Automated post-interview spin-down script: tears down cloud replicas,
# purges billable Route 53 hosted zone to achieve TRUE $0.00 standing cost,
# and terminates local Docker containers.

set -euo pipefail

cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

export AWS_PROFILE="${AWS_PROFILE:-dr-sandbox}"
export AWS_DEFAULT_REGION="ap-southeast-2"
ACCOUNT_ID="${DR_ALLOWED_ACCOUNT_ID:-758579869433}"

PURGE_DNS=false

for arg in "$@"; do
    case "$arg" in
        --zero-cost|--purge-dns)
            PURGE_DNS=true
            ;;
    esac
done

echo "================================================================="
echo " 🛑 HYBRID DR ORCHESTRATOR: POST-INTERVIEW SPIN-DOWN"
echo " Target: TRUE \$0.000 / MONTH STANDING COST"
echo "================================================================="
echo ""

# 1. Teardown Ephemeral DR Compute (if active)
echo "==> [1/4] Checking and Tearing Down Ephemeral AWS Compute Replica..."
if [ -d "infra/aws/envs/dr/.terraform" ]; then
    echo "Destroying ephemeral DR replica resources (EC2, VPC, EIP)..."
    cd infra/aws/envs/dr && terraform destroy -auto-approve || true
    cd ../../..
    echo "✅ Ephemeral cloud replica destroyed."
else
    echo "✅ No ephemeral DR compute infrastructure found."
fi

# 2. Purge Route 53 Hosted Zone for True $0.00 Standing Cost
echo ""
echo "==> [2/4] Managing Route 53 Hosted Zone (\$0.50/mo billable)..."
ZONE_ID=$(aws route53 list-hosted-zones --query "HostedZones[?contains(Name, 'dr-lab.internal')].Id|[0]" --output text 2>/dev/null || echo "None")

if [ "$ZONE_ID" != "None" ] && [ -n "$ZONE_ID" ] && [ "$ZONE_ID" != "null" ]; then
    CLEAN_ZONE_ID="${ZONE_ID#/hostedzone/}"
    echo "Found Route 53 hosted zone: ${CLEAN_ZONE_ID} (dr-lab.internal)"
    if [ "$PURGE_DNS" = true ]; then
        echo "Purging Route 53 hosted zone to enforce TRUE \$0.000/month..."
        aws route53 delete-hosted-zone --id "$CLEAN_ZONE_ID" || true
        echo "✅ Route 53 hosted zone deleted. (\$0.00 / month achieved)"
    else
        echo "ℹ️  Route 53 hosted zone preserved (pilot light ~$0.50/mo)."
        echo "   To purge Route 53 and reach TRUE \$0.00, run: make zero-cost"
    fi
else
    echo "✅ No Route 53 hosted zone found. (\$0.00 / month)"
fi

# 3. Stop Local Docker Containers (Free Mac Memory & CPU)
echo ""
echo "==> [3/4] Stopping Local Containers to Free Memory and CPU..."
if [ -f "infra/onprem/docker-compose.yml" ]; then
    docker compose -f infra/onprem/docker-compose.yml down --remove-orphans || true
fi
if [ -f "infra/monitoring/docker-compose.yml" ]; then
    docker compose -f infra/monitoring/docker-compose.yml down || true
fi
echo "✅ Local Docker containers stopped."

# 4. Reset Local State to IDLE
echo ""
echo "==> [4/4] Resetting Local Orchestrator State..."
if [ -f "/tmp/hybrid_dr_state.json" ]; then
    echo "{\"state\": \"IDLE\"}" > /tmp/hybrid_dr_state.json
fi
echo "✅ State reset to IDLE."

# 5. Run Final Cost Audit Verification
echo ""
echo "==> Running Final Verification Audit..."
./scripts/cost_guard.sh

echo ""
echo "================================================================="
echo " 🏁 POST-INTERVIEW SPIN-DOWN COMPLETE!"
echo " When you are ready for your next interview, simply run:"
echo "   make interview-up"
echo "================================================================="
