# ADR-003: Disaster Recovery Tier Strategy (Pilot Light vs Warm Standby)
- Status: accepted
- Date: 2026-10-05

## Context
Balance RTO <= 15m and RPO <= 5m against a $15/month budget ceiling.

## Options
| Strategy | RPO | RTO | Standing Cost (ap-southeast-2) | Cost per Drill |
|---|---|---|---|---|
| Cold Backup | 1-24h | 30-60m | ~$0.50 | <$0.10 |
| Pilot Light (Chosen) | <= 5m | 10-15m | ~$0.93 - $4.73 | ~$0.12 |
| Warm Standby | <= 10s | 1-3m | ~$35 - $50 | $0.00 extra |

## Decision
We adopt **Pilot Light**: Continuous PostgreSQL WAL archiving + pgBackRest base backups to S3 Standard; EC2 compute is provisioned on demand via Terraform during failover.
