#!/usr/bin/env bash
# scripts/cost_guard.sh
# Audits billable AWS resources tagged Project=hybrid-dr in ap-southeast-2.

set -euo pipefail

usage() {
    cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Audits active AWS resources tagged Project=hybrid-dr in ap-southeast-2.

Options:
  -h, --help    Show this help message.
EOF
    exit 0
}

if [[ "${1:-}" =~ ^(-h|--help)$ ]]; then
    usage
fi

export AWS_PROFILE="${AWS_PROFILE:-dr-sandbox}"
export AWS_DEFAULT_REGION="ap-southeast-2"

echo "==> Auditing AWS resources for Account ${DR_ALLOWED_ACCOUNT_ID:-758579869433} in ap-southeast-2..."

echo "--- Active EC2 Instances ---"
if command -v aws >/dev/null 2>&1; then
    aws ec2 describe-instances \
        --filters "Name=tag:Project,Values=hybrid-dr" "Name=instance-state-name,Values=running,pending" \
        --query "Reservations[].Instances[].[InstanceId,InstanceType,State.Name,Tags[?Key=='Name'].Value|[0]]" \
        --output table || true

    echo "--- S3 Backup Buckets ---"
    aws s3api list-buckets --query "Buckets[?contains(Name, 'hybrid-dr')].Name" --output table || true

    echo "--- SSM Fencing Parameter ---"
    aws ssm get-parameter --name "/hybrid-dr/active-site" --query "Parameter.[Name,Value,LastModifiedDate]" --output table 2>/dev/null || echo "Parameter not created yet."
else
    echo "Notice: aws CLI is not installed on PATH. Run cost_guard.sh after installing aws CLI."
fi

echo "==> Audit complete."
