# Zero-Cost Interview Playbook: Instant Spin-Up, Live Demo & Spin-Down to $0.00

**Document Version:** 1.0.0  
**Target Roles:** DevOps Engineer, Site Reliability Engineer (SRE), Cloud Infrastructure Architect  
**Author:** Ajay  
**Repository:** [killer1panda/hybrid-dr-orchestrator](https://github.com/killer1panda/hybrid-dr-orchestrator)  
**Monthly Standing Cost Between Interviews:** **$0.0000 / month (Guaranteed)**  

---

## 💡 The Philosophy: 100% On-Demand Interview Demos

Why pay standing cloud fees—even \$0.50/month for a Route 53 hosted zone—when an interview only lasts 45 minutes?

This project provides an automated, one-command lifecycle:
1. **Before the Interview (90 seconds):** Run `make interview-up` to spin up the local lab, observability stack, Route 53 zone, and launch Mission Control.
2. **During the Interview (5–10 minutes):** Showcase the live Web Dashboard, trigger automated quorum failover, demonstrate encrypted S3 WAL recovery, and execute reverse failback.
3. **After the Interview (30 seconds):** Run `make zero-cost` to terminate all cloud resources, purge the hosted zone, stop local containers, and verify **$0.000 / month** standing cost.

---

## ⚡ 1. Pre-Interview Spin-Up (Run 5 Minutes Before Your Call)

Execute one command from the project root:

```bash
make interview-up
```

### What Happens Automatically:
1. **AWS Identity Check:** Confirms active AWS credentials for `dr-sandbox` against allowed Account `758579869433`.
2. **Route 53 Provisioning:** Verifies or creates the private hosted zone `dr-lab.internal`.
3. **Local Lab Boot:** Starts the 3-tier on-premises container cluster (Nginx at `:8080`, FastAPI at `:8000`, PostgreSQL 16 at `:5432`).
4. **Observability Stack:** Boots Prometheus (`:9090`), Alertmanager (`:9093`), and Grafana (`:3000`).
5. **Data Seeding & Probing:** Injects a test order and starts the continuous 1-second monotonic RPO probe.
6. **Cost Guard Audit:** Verifies standing resource count and outputs access URLs.

### Open Your Browser Tabs:
* 🌐 **Mission Control Web Dashboard:** `http://localhost:8500` *(Run: `make dashboard`)*
* 📊 **Grafana SRE Dashboard:** `http://localhost:3000` *(admin / admin)*
* 🩺 **Primary App Healthz:** `http://localhost:8080/healthz`

---

## 🎬 2. The Live Interview Demonstration Flow

### Stage 1: The Baseline Health Check (1 Minute)
* Open the **Mission Control Web Dashboard** (`http://localhost:8500`).
* Point out:
  - **Active Primary Site:** `ON-PREMISES (192.168.10.0/24)`
  - **Quorum Engine:** `0 / 3` consecutive failures; multi-signal monitoring across L7 HTTP, L4 TCP, and SSM push heartbeats.
  - **FinOps Meter:** `$0.00` active compute standing spend.
  - **RPO / RTO SLA Budgets:** Measured RPO (290s / 300s SLA), RTO benchmark (21m cold / 6m 45s Golden AMI).

### Stage 2: Inject Chaos & Trigger Failover (3 Minutes)
* Click **"💥 Inject Blackout"** in the Web Dashboard (or run `make drill` in terminal).
* Walk the interviewer through the **7-Stage State Machine Lifecycle**:
  1. `FENCING`: Quorum consensus detected unanimous failure across $\ge 2$ domains; SSM parameter `/hybrid-dr/active-site` is set to `aws`; on-premises database enters read-only fencing.
  2. `PROVISIONING`: Terraform provisions on-demand EC2 `t3.small` and VPC in Sydney.
  3. `RESTORING`: Ansible decrypts S3 PBKDF2 AES-256 base backup and replays WAL archives.
  4. `TESTING`: Automated smoke tests assert API health and database write capability.
  5. `CUTOVER`: Route 53 DNS record `app.dr-lab.internal` cuts over to AWS Elastic IP.
  6. `COMPLETED`: Dashboard turns green; show measured ground-truth RTO and RPO metrics!

### Stage 3: Zero-Data-Loss Reverse Failback (2 Minutes)
* Click **"🔄 Execute Failback"** in the Web Dashboard (or run `make failback` in terminal).
* Explain the safety guardrails:
  - Establishes encrypted SSH tunnel to the live AWS replica.
  - Exports post-failover transaction deltas via `pg_dump`.
  - Restores to on-premises PostgreSQL and verifies probe sequence continuity.
  - Switches Route 53 DNS back to on-premises.
  - Tears down AWS compute replica via `make dr-down` to eliminate billing.

---

## 🛑 3. Post-Interview Spin-Down (Return to TRUE $0.00)

Once your interview concludes, choose your desired teardown mode:

### Option A: TRUE ZERO STANDING COST ($0.000 / month) — Recommended
If you have no more interviews today, completely wipe all cloud resources and local containers:

```bash
make zero-cost
```

**What this does:**
1. Tears down ephemeral AWS replica compute (if still running).
2. Purges the Route 53 hosted zone `dr-lab.internal` (saves $0.50/mo).
3. Stops all local Docker containers (`make lab-down`, `make monitoring-down`) to free Mac memory and CPU.
4. Resets state machine state to `IDLE`.
5. Runs `cost-guard` to verify:
   ```
   =================================================================
    FINOPS STANDING COST SUMMARY
   =================================================================
    🟢 TRUE ZERO STANDING COST: $0.000 / month across all services!
   =================================================================
   ```

---

### Option B: Pilot Light Mode (~$0.50 / month)
If you have another interview later today or tomorrow and want to preserve the Route 53 zone for an even faster 30-second restart:

```bash
make interview-down
```
*Tears down all compute resources ($0.00 EC2) and stops local containers, while keeping the persistent Route 53 zone ready.*

---

## 📋 Quick Reference Command Cheat Sheet

| Intent | Command | Duration | Cost Impact |
|---|---|---|---|
| **Spin Up Before Interview** | `make interview-up` | ~90 seconds | Provisions lab, monitoring & DNS |
| **Launch Web Dashboard** | `make dashboard` | Instant | Serves UI on `http://localhost:8500` |
| **Run Simulated DR Drill** | `make drill` | ~2 minutes | Dry-run simulated failover ($0.00) |
| **Run Live Cloud Failover** | `make drill-live` | ~21 minutes | Spins up real AWS EC2 replica |
| **Reverse Sync Failback** | `make failback` | ~45 seconds | Delta syncs data & destroys AWS compute |
| **Verify AWS Spend** | `make cost-audit` | ~5 seconds | Audits EC2, EIP, EBS, NAT, Route 53, S3 |
| **Spin Down to TRUE $0.00** | `make zero-cost` | ~30 seconds | **Guaranteed $0.000 / month** |
