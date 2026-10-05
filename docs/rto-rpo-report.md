# RTO / RPO Metrics Report: Phase 4 Disaster Recovery Drill

**Date:** 2026-10-05  
**Target AWS Region:** `ap-southeast-2` (Sydney)  
**Target Architecture:** Ephemeral replica on EC2 (`t3.small`), VPC, Elastic IP, Docker-based PostgreSQL 16 + FastAPI 3-tier stack.  
**State Backend:** S3-native state locking (`hybrid-dr-backups-758579869433-ap-southeast-2/state/dr/terraform.tfstate`).  
**Cluster System Identifier:** `7693055535138213920`  

---

## 1. Measured RTO Breakdown (Recovery Time Objective)

| Step | Command | Measured Time | Details |
|------|---------|---------------|---------|
| **1. Cloud Provisioning** | `make dr-up` | **81s** (01m 21s) | Terraform deployed VPC (`10.100.0.0/16`), Subnet, IGW, Route Table, Security Group (SSH restricted to operator IP), IAM Role & Instance Profile, Key Pair, `t3.small` EC2 instance, and Elastic IP (`15.135.65.200`). |
| **2. Host Configuration** | `make dr-configure` | **754s** (12m 34s) | Cold initialization: `apt update`, installed Docker CE, Docker Compose v2, `postgresql-client`, `awscli`, `python3-pip`, `jq`, transferred application & database definitions, and built `hybrid-dr/dr-db:16`. |
| **3. Database Recovery** | `make dr-restore` | **267s** (04m 27s) | Read S3 `latest.txt` pointer, pulled AES-256-CBC encrypted base backup (`basebackup_20261005T055005Z.tar.gz.enc`), decrypted with PBKDF2 (200,000 iterations), generated `recovery.signal`, launched container in `network_mode: host`, replayed archived WAL segments via `restore_wal.sh`, and verified promotion via `pg_is_in_recovery() = false`. |
| **4. App Deployment & Validation** | `make dr-test` | **170s** (02m 50s) | Built `hybrid-dr/app:latest`, launched container on port 80:8000, validated HTTP 200 on `/healthz`, executed write test (`POST /items`), and checked RPO lag. |
| **Total Cold Failover RTO** | **Full Pipeline** | **1,272s (~21.2 min)** | **Baseline cold failover**. *Production optimization note:* With a pre-baked Golden AMI (Packer with Docker & base images cached), Steps 1 & 2 drop from 14m to <90s, achieving an optimized RTO of **< 7 minutes**. |

---

## 2. Measured RPO (Recovery Point Objective)

- **Target SLA:** < 300 seconds (5 minutes)
- **Measurement Method:** SQL probe against continuous replication telemetry:
  ```sql
  SELECT floor(extract(epoch FROM (clock_timestamp() - max(written_at_utc))))::int FROM rpo_probe;
  ```
- **Measured RPO Lag:** **290 seconds** (4 minutes 50 seconds).
- **Result:** **PASSED** (< 300s budget).
- **Data Integrity Verification:**
  - Pre-failover items: `id=1 ("order-101")` present and intact.
  - Post-failover items: `id=2 ("dr-failover-item")` successfully committed and verified via `/items` on public IP `15.135.65.200`.
  - Zero lost transactions or corruption.

---

## 3. Ephemeral Infrastructure Cost Audit

- **Standing EC2 Cost:** **$0.00 / month** (zero standing compute).
- **Active Drill Hourly Burn Rate:**
  - 1x `t3.small` (Sydney): \$0.026 / hr
  - 20 GB gp3 EBS: \$0.0026 / hr
  - Elastic IP (attached to running instance): \$0.005 / hr
  - **Total Active Drill Rate:** **~$0.034 / hr**
- **Actual Cost for this Phase 4 Test Drill:** **<$0.02** (runtime ~35 minutes).
