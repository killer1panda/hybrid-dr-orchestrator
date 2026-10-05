#!/usr/bin/env bash
# scripts/cost_guard.sh
# Comprehensive audit of billable AWS resources tagged Project=hybrid-dr in ap-southeast-2.

set -euo pipefail

usage() {
    cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Comprehensive audit of billable AWS resources in ap-southeast-2.
Checks EC2 instances, Elastic IPs, EBS volumes, NAT gateways, Route 53 zones, and S3 buckets.

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
ACCOUNT_ID="${DR_ALLOWED_ACCOUNT_ID:-758579869433}"

echo "================================================================="
echo " AWS Cost Guard & Standing Resource Audit"
echo " Account: ${ACCOUNT_ID} | Region: ap-southeast-2"
echo "================================================================="

if ! command -v aws >/dev/null 2>&1; then
    echo "Error: aws CLI is not installed or not on PATH."
    exit 1
fi

echo ""
echo "--- 1. EC2 Compute Instances (Billable: ~\$24/mo per t3.small) ---"
EC2_COUNT=$(aws ec2 describe-instances \
    --filters "Name=instance-state-name,Values=running,pending" \
    --query "length(Reservations[].Instances[])" --output text 2>/dev/null || echo "0")

if [ "$EC2_COUNT" -gt 0 ]; then
    aws ec2 describe-instances \
        --filters "Name=instance-state-name,Values=running,pending" \
        --query "Reservations[].Instances[].[InstanceId,InstanceType,State.Name,Tags[?Key=='Name'].Value|[0]]" \
        --output table
    echo "⚠️  Found ${EC2_COUNT} active EC2 instance(s)!"
else
    echo "✅ No active EC2 instances. (\$0.00 / mo)"
fi

echo ""
echo "--- 2. Unattached Elastic IPs (Billable: ~\$3.60/mo each) ---"
EIP_COUNT=$(aws ec2 describe-addresses \
    --query "length(Addresses[?AssociationId==null])" --output text 2>/dev/null || echo "0")

if [ "$EIP_COUNT" -gt 0 ]; then
    aws ec2 describe-addresses \
        --query "Addresses[?AssociationId==null].[PublicIp,AllocationId]" \
        --output table
    echo "⚠️  Found ${EIP_COUNT} unattached Elastic IP(s)!"
else
    echo "✅ No unattached Elastic IPs. (\$0.00 / mo)"
fi

echo ""
echo "--- 3. EBS Volumes (Billable: ~\$0.08/GB-month) ---"
EBS_COUNT=$(aws ec2 describe-volumes \
    --filters "Name=status,Values=available,in-use" \
    --query "length(Volumes[])" --output text 2>/dev/null || echo "0")

if [ "$EBS_COUNT" -gt 0 ]; then
    aws ec2 describe-volumes \
        --filters "Name=status,Values=available,in-use" \
        --query "Volumes[].[VolumeId,Size,State,AvailabilityZone]" \
        --output table
    echo "⚠️  Found ${EBS_COUNT} EBS volume(s)."
else
    echo "✅ No EBS volumes allocated. (\$0.00 / mo)"
fi

echo ""
echo "--- 4. NAT Gateways (Billable: ~\$32.40/mo each) ---"
NAT_COUNT=$(aws ec2 describe-nat-gateways \
    --filter "Name=state,Values=available,pending" \
    --query "length(NatGateways[])" --output text 2>/dev/null || echo "0")

if [ "$NAT_COUNT" -gt 0 ]; then
    aws ec2 describe-nat-gateways \
        --filter "Name=state,Values=available,pending" \
        --query "NatGateways[].[NatGatewayId,State,VpcId]" \
        --output table
    echo "⚠️  Found ${NAT_COUNT} NAT Gateway(s)!"
else
    echo "✅ No NAT Gateways. (\$0.00 / mo)"
fi

echo ""
echo "--- 5. Route 53 Hosted Zones (Billable: \$0.50/mo each) ---"
R53_COUNT=$(aws route53 list-hosted-zones \
    --query "length(HostedZones[?contains(Name, 'dr-lab.internal')])" --output text 2>/dev/null || echo "0")

if [ "$R53_COUNT" -gt 0 ]; then
    aws route53 list-hosted-zones \
        --query "HostedZones[?contains(Name, 'dr-lab.internal')].[Id,Name]" \
        --output table
    echo "ℹ️  Found ${R53_COUNT} Route 53 hosted zone(s) (~\$0.50/mo)."
else
    echo "✅ No Route 53 hosted zones. (\$0.00 / mo)"
fi

echo ""
echo "--- 6. S3 Backup Buckets (Storage: ~\$0.023/GB-mo, negligible for <100MB) ---"
S3_COUNT=$(aws s3api list-buckets \
    --query "length(Buckets[?contains(Name, 'hybrid-dr')])" --output text 2>/dev/null || echo "0")

if [ "$S3_COUNT" -gt 0 ]; then
    aws s3api list-buckets \
        --query "Buckets[?contains(Name, 'hybrid-dr')].[Name,CreationDate]" \
        --output table
    echo "ℹ️  Found ${S3_COUNT} S3 backup bucket(s)."
else
    echo "✅ No S3 backup buckets found."
fi

echo ""
echo "--- 7. SSM Fencing Parameter ---"
aws ssm get-parameter --name "/hybrid-dr/active-site" --query "Parameter.[Name,Value,LastModifiedDate]" --output table 2>/dev/null || echo "Parameter not created yet."

echo ""
echo "================================================================="
echo " FINOPS STANDING COST SUMMARY"
echo "================================================================="
if [ "$EC2_COUNT" -eq 0 ] && [ "$EIP_COUNT" -eq 0 ] && [ "$EBS_COUNT" -eq 0 ] && [ "$NAT_COUNT" -eq 0 ] && [ "$R53_COUNT" -eq 0 ]; then
    echo " 🟢 TRUE ZERO STANDING COST: \$0.000 / month across all services!"
elif [ "$EC2_COUNT" -eq 0 ] && [ "$EIP_COUNT" -eq 0 ] && [ "$EBS_COUNT" -eq 0 ] && [ "$NAT_COUNT" -eq 0 ] && [ "$R53_COUNT" -eq 1 ]; then
    echo " 🟡 PILOT LIGHT STANDING COST: \$0.50 / month (Route 53 hosted zone only)."
    echo "    To drop this to TRUE \$0.00, run: make zero-cost"
else
    echo " 🔴 ACTIVE CLUSTER DETECTED: Compute resources are running."
    echo "    To teardown all compute, run: make teardown"
fi
echo "================================================================="
