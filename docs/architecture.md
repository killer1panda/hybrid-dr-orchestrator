# Architecture Specification: Hybrid Cloud DR Orchestrator

## 1. RTO Budget Allocation (SLA <= 15 minutes)
- Detection & Quorum Confirmation: 1.5 min
- Fencing Lock Acquisition (SSM): 0.5 min
- Terraform Provisioning (VPC, EC2, SG): 3.5 min
- Ansible Configuration & Hardening: 3.0 min
- Database Restore & WAL Catchup Replay: 2.5 min
- Integration Smoke Testing (/healthz): 1.5 min
- Route 53 DNS Record Cutover: 1.0 min
**Total Budgeted RTO: 13.5 minutes**

## 2. RPO Durability Architecture (SLA <= 5 minutes)
- Database: PostgreSQL 16
- Archiving: Continuous WAL shipping with archive_timeout = 60s
- Verification: Monotonic rpo_probe table written every 1,000ms
- Target RPO: < 60 seconds

## 3. Cost Model (ap-southeast-2 Sydney)
- Standing Persistent Layer: Route 53 Hosted Zone ($0.50) + S3 Backups & State ($0.23) + CloudWatch ($0.20) = **~$0.93/month**
- Ephemeral DR Replica (Per 2-Hour Drill): 3x t4g.micro + gp3 storage + Public IPs = **~$0.12/drill**
