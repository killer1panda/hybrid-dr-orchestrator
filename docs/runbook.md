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
