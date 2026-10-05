# Disaster Recovery Operational Runbook

## 1. Backup Engine Architecture & Decision

| Tool | Pros | Cons | Decision |
|---|---|---|---|
| **pg_basebackup + S3 WAL Archiving** | Native PostgreSQL tooling; zero third-party agent dependencies; simple shell scripts; transparent `restore_command`. | Manual retention cleanup; no cross-backup block deduplication. | **Selected (Primary)**: Maximum transparency and auditability for DR automation with zero third-party agents. |
| **pgBackRest** | Block-level deduplication; parallel multi-threaded S3 streaming; built-in retention expiration policies. | Complex repository stanza configuration; heavier container image footprint. | Enterprise upgrade path. |
| **WAL-G** | High-performance Go rewrite of WAL-E; fast multi-stream compression. | Separate external binary to maintain; less standard across minimal distros. | Evaluated, deferred. |

### Retention & Archiving Schedule
- **Base Backups**: Weekly full snapshots plus pre-maintenance manual snapshots. Retained for 30 days via S3 lifecycle expiration.
- **WAL Archiving**: Continuous WAL shipping triggered every 60 seconds (`archive_timeout = 60s`) or immediately upon 16 MB segment completion.
- **RPO Trade-Off**: Tuning `archive_timeout` to 60s guarantees that maximum transaction loss is bounded by 60 seconds of unarchived WAL, meeting the $\le$ 5 minute SLA with a 5x margin.

---

## 2. Taking a Manual Database Backup

To trigger an immediate full base backup outside the regular schedule:
```bash
./scripts/backup_base.sh
```

### Verification
Confirm the new snapshot appears in S3:
```bash
aws s3 ls s3://hybrid-dr-backups-758579869433-ap-southeast-2/backups/base/ --profile dr-sandbox
```

---

## 3. Point-in-Time Recovery (PITR) Procedure

To restore the database to an exact point in time (e.g. `2026-10-05 12:00:00 UTC`):

1. **Locate Target Snapshot**:
   Identify the base backup timestamp immediately prior to the recovery target:
   ```bash
   aws s3 cp s3://hybrid-dr-backups-758579869433-ap-southeast-2/backups/base/latest.txt - --profile dr-sandbox
   ```
2. **Download & Extract Base Backup**:
   ```bash
   aws s3 cp s3://hybrid-dr-backups-758579869433-ap-southeast-2/backups/base/<SNAPSHOT_NAME> - --profile dr-sandbox | tar -xz -C /var/lib/postgresql/data
   ```
3. **Configure Recovery Target in `postgresql.conf` / `recovery.signal`**:
   Create the trigger file:
   ```bash
   touch /var/lib/postgresql/data/recovery.signal
   ```
   Add restore settings:
   ```ini
   restore_command = 'aws s3 cp s3://hybrid-dr-backups-758579869433-ap-southeast-2/backups/wal/%f.gz - --profile dr-sandbox | gzip -d > %p'
   recovery_target_time = '2026-10-05 12:00:00 UTC'
   recovery_target_action = 'promote'
   ```
4. **Start PostgreSQL**:
   PostgreSQL starts in recovery mode, replays WAL segments sequentially from S3 up to the target timestamp, removes `recovery.signal`, and promotes the instance to primary read/write.

---

## 4. Backup-Writer Credential Rotation Procedure

To rotate credentials for `dr-onprem-backup-writer` with zero backup downtime:

1. **Generate New IAM Access Key**:
   ```bash
   NEW_KEY=$(aws iam create-access-key --user-name dr-onprem-backup-writer --profile dr-sandbox --output json)
   ```
2. **Update On-Premises Configuration**:
   Update `~/.aws/credentials` or the backup runner environment variables with the new Access Key ID and Secret Access Key.
3. **Validate Backup Functionality**:
   ```bash
   touch /tmp/rotation-check.txt
   aws s3 cp /tmp/rotation-check.txt s3://hybrid-dr-backups-758579869433-ap-southeast-2/backups/rotation-check.txt --profile dr-onprem-backup-writer
   aws s3 rm s3://hybrid-dr-backups-758579869433-ap-southeast-2/backups/rotation-check.txt --profile dr-sandbox
   ```
4. **Deactivate and Delete Old Key**:
   ```bash
   aws iam update-access-key --user-name dr-onprem-backup-writer --access-key-id <OLD_KEY_ID> --status Inactive --profile dr-sandbox
   aws iam delete-access-key --user-name dr-onprem-backup-writer --access-key-id <OLD_KEY_ID> --profile dr-sandbox
   ```

---

## 5. WireGuard Tunnel Diagnostics

### Status Check
```bash
wg show
```
Expected output shows `latest handshake: ... seconds ago` and transfer bytes increasing.

### NAT Keepalive Behavior
The on-premises peer runs `PersistentKeepalive = 25`. If the residential NAT mapping expires or changes, the keepalive packet immediately re-opens the firewall state table and maintains the reverse tunnel without inbound port forwarding.

---

## 6. Runbook: Automated Failback (Return to Primary Site)

### Symptom
Primary on-premises site has recovered and is ready to resume active production traffic; AWS replica is currently serving traffic and incurring hourly compute costs.

### Diagnosis
1. Verify on-premises containers are running and healthy:
   ```bash
   make lab-status
   ```
   *Expected output:* HTTP 200 OK, database healthy, recent probe records visible.
2. Verify AWS replica is online and active:
   ```bash
   aws ssm get-parameter --name "/hybrid-dr/active-site" --profile dr-sandbox --region ap-southeast-2
   ```
   *Expected output:* `"Value": "aws"`.

### Action
Execute automated failback:
```bash
make failback
```
The Ansible playbook will:
1. Establish a secure SSH tunnel to the AWS replica database.
2. Dump all post-failover transaction deltas (`pg_dump`).
3. Restore the delta data to the on-premises database container.
4. Verify table and probe row counts.
5. Reset Route 53 DNS and SSM parameter `/hybrid-dr/active-site` to `onprem`.
6. Destroy the ephemeral AWS replica (`make dr-down`).

### Verify
1. Verify Route 53 points back to on-prem:
   ```bash
   aws route53 list-resource-record-sets --hosted-zone-id Z0157777J80LB1N4CSX2 --profile dr-sandbox
   ```
2. Verify AWS compute is completely torn down:
   ```bash
   make cost-audit
   ```
   *Expected output:* 0 running EC2 instances, 0 unattached Elastic IPs.

### Rollback
If the database delta export or restore fails, the playbook aborts **before** touching DNS or destroying the AWS replica. The AWS replica remains online, active, and healthy. Fix the on-premises connection issue and re-run `make failback`.

---

## 7. Runbook: Manual Emergency Failback Override

### Symptom
Automated failback (`make failback`) fails due to an Ansible configuration error, network timeout, or partial state mismatch, requiring manual operator intervention to return traffic to on-premise and terminate AWS compute spend.

### Diagnosis
Check Ansible error logs or test direct connectivity to the AWS replica:
```bash
AWS_IP=$(cd infra/aws/envs/dr && terraform output -raw dr_public_ip)
ssh -i ~/.ssh/id_rsa ubuntu@$AWS_IP "docker ps"
```

### Action
Execute the manual 5-step override:

1. **Dump Delta from AWS Replica Database:**
   ```bash
   AWS_IP=$(cd infra/aws/envs/dr && terraform output -raw dr_public_ip)
   ssh -i ~/.ssh/id_rsa -L 54321:127.0.0.1:5432 ubuntu@$AWS_IP -N &
   SSH_PID=$!
   sleep 2
   PGPASSWORD="dr_secure_password_2026" pg_dump -h 127.0.0.1 -p 54321 -U dr_user -d dr_app --clean --if-exists > /tmp/manual_delta.sql
   kill $SSH_PID
   ```

2. **Restore Delta to On-Premises PostgreSQL:**
   ```bash
   docker exec -i onprem-db psql -U dr_user -d dr_app < /tmp/manual_delta.sql
   ```

3. **Verify On-Premises Application Health:**
   ```bash
   docker compose -f infra/onprem/docker-compose.yml restart app web
   curl -s http://localhost:8080/healthz
   ```

4. **Reset Active Site Parameter and DNS:**
   ```bash
   aws ssm put-parameter --name "/hybrid-dr/active-site" --value "onprem" --type String --overwrite --profile dr-sandbox --region ap-southeast-2
   ```

5. **Teardown Ephemeral Cloud Replica:**
   ```bash
   make dr-down
   ```

### Verify
```bash
make lab-status
make cost-audit
```

### Rollback
If on-premises database restore encounters corruption, restore the latest verified S3 snapshot via `./scripts/test_restore.sh` before switching DNS.

---

## 8. Runbook: Stuck Orchestrator State Machine Recovery

### Symptom
The Python Orchestrator halts with `FAILED_NEEDS_HUMAN` or leaves a stale leader lock preventing new drill runs.

### Diagnosis
Inspect the persisted state file and leader lock:
```bash
cat /tmp/hybrid_dr_state.json
cat /tmp/hybrid_dr.lock
```

### Action
1. Audit `/tmp/hybrid_dr_audit.jsonl` to diagnose which step failed:
   ```bash
   tail -n 20 /tmp/hybrid_dr_audit.jsonl
   ```
2. Release stale lock and reset state to `IDLE`:
   ```bash
   rm -f /tmp/hybrid_dr.lock
   echo '{"state": "IDLE"}' > /tmp/hybrid_dr_state.json
   ```
3. Verify orchestrator status:
   ```bash
   PYTHONPATH=orchestrator/src orchestrator/venv/bin/python -m hybrid_dr.cli status
   ```

### Verify
`Current State: IDLE` and all signal probes report health status.

### Rollback
N/A (State is reset to clean baseline).

---

## 9. Runbook: Guarded Chaos Drill Execution

### Symptom
Operator desires to execute a simulated disaster drill without touching production cloud resources or host Mac network interfaces.

### Diagnosis
Check allowed targets in `lab-inventory.yml`:
```bash
cat lab-inventory.yml | grep -A 10 allowed_chaos_actions
```

### Action
Run guarded chaos script in dry-run mode:
```bash
./scripts/chaos_kill_onprem.sh --dry-run
./scripts/chaos_network_drop.sh --dry-run
```
Run end-to-end dry-run drill:
```bash
make drill
```

### Verify
Inspect immutable chaos audit trail:
```bash
tail -n 5 audit/chaos.jsonl
tail -n 5 audit/drills.jsonl
```

### Rollback
To restore on-premise containers after an active chaos drill:
```bash
cd infra/onprem && docker compose up -d
curl -sf http://localhost:8080/healthz
```

