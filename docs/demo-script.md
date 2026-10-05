# Screencast Demo Script: Automated Hybrid Cloud DR Orchestrator (5 Minutes)

**Goal:** Record a crisp, technical demonstration of the Hybrid DR Orchestrator for recruiters, portfolio reviewers, and LinkedIn.  
**Target Duration:** 5 Minutes  
**Prerequisites:** Terminal 1 (Orchestrator root), Terminal 2 (Logs/Monitoring), Browser tab with Grafana (`http://localhost:3000`).

---

## ⏱️ Video Timeline & Shot List

```
0:00 ─── Introduction & Architecture Diagram (30s)
0:30 ─── Baseline "Healthy" State & Continuous WAL Archiving (30s)
1:00 ─── Injecting Chaos & Prometheus Alert Trigger (30s)
1:30 ─── Orchestrator Quorum, Fencing & Cloud Provisioning (90s)
3:00 ─── Cloud Validation, RTO/RPO Metrics & Write Test (60s)
4:00 ─── Automated Reverse Sync Failback & Cloud Teardown (60s)
5:00 ─── Conclusion
```

---

### Act 1: Introduction & Architecture (0:00 - 0:30)
* **Visual:** Display `README.md` in the browser or VS Code showing the Mermaid state machine and hybrid topology diagrams.
* **Talk Track:**
  > "Hi everyone, I'm Ajay. Today I'm demonstrating my **Automated Hybrid Cloud Disaster Recovery Orchestrator**.
  > This project simulates an enterprise 3-tier on-premises data center running FastAPI and PostgreSQL 16. When the primary site suffers a catastrophic blackout, the orchestrator autonomously detects the outage using a multi-signal quorum engine, provisions an ephemeral replica in AWS from scratch using Terraform and Ansible, decrypts and replays continuous WAL archives from S3, and cuts over Route 53 DNS—achieving an RTO under 22 minutes and RPO under 5 minutes with **zero standing compute costs**."

---

### Act 2: Baseline Healthy State & S3 WAL Streaming (0:30 - 1:00)
* **Visual:** Terminal 1 showing `make lab-status`. Switch to Grafana showing all green health checks.
* **Command:**
  ```bash
  make lab-status
  ```
* **Talk Track:**
  > "Right now, our on-premises cluster is completely healthy. A dedicated background daemon is inserting timestamped monotonic sequence probes every single second into our PostgreSQL database.
  > Simultaneously, PostgreSQL's `archive_command` is continuously compressing, encrypting with PBKDF2 AES-256, and shipping WAL segments directly to our secure AWS S3 bucket in Sydney."

---

### Act 3: Injecting Chaos & Quorum Detection (1:00 - 1:30)
* **Visual:** Terminal 1 running `make drill`. Split screen with Prometheus alert dashboard turning red.
* **Command:**
  ```bash
  make drill
  ```
* **Talk Track:**
  > "Let's simulate a total catastrophic data center power outage using our inventory-guarded chaos tooling.
  > Instantly, our Layer 7 HTTP health check fails, and our Layer 4 TCP port 80 socket drops.
  > In Prometheus and Alertmanager, the alert fires.
  > Rather than relying on a single flaky check, our Python Orchestrator's Quorum Engine requires concurrent failure across multiple independent signal classes before declaring disaster."

---

### Act 4: The Orchestrator Springs Into Action (1:30 - 3:00)
* **Visual:** Terminal 1 showing live orchestrator logs progressing through the state machine.
* **Talk Track:**
  > "Disaster confirmed! The Orchestrator's finite state machine takes over with zero human intervention:
  > **Stage 1 (Fencing):** It acquires a split-brain fencing lock by setting AWS SSM Parameter `/hybrid-dr/active-site` to `aws`.
  > **Stage 2 (Provisioning):** It invokes Terraform to provision a dedicated VPC, Subnet, Security Group, and a `t3.small` EC2 instance in Sydney in just 81 seconds.
  > **Stage 3 (Configuration):** Ansible SSHs in via a dynamically detected IP guard, installs Docker, and prepares our container runtime.
  > **Stage 4 (Restoration):** It pulls the latest encrypted base backup from S3, decrypts it locally, replays archived WAL segments to point-in-time recovery, and promotes PostgreSQL to primary read/write.
  > **Stage 5 (Validation):** Automated smoke tests verify `/healthz` and commit a write transaction.
  > **Stage 6 (Cutover):** Route 53 cuts over our private DNS record to the new AWS Elastic IP."

---

### Act 5: Empirical Validation & RTO/RPO Metrics (3:00 - 4:00)
* **Visual:** Browser curling the new AWS replica endpoint. Open `docs/rto-rpo-report.md`.
* **Command:**
  ```bash
  curl -s http://15.135.65.200/healthz | jq .
  curl -s http://15.135.65.200/items | jq .
  ```
* **Talk Track:**
  > "The smoke tests passed and the site is officially live in AWS.
  > We query `/items` and confirm both our pre-disaster canary transactions and our newly committed post-failover records are intact.
  > Reviewing our benchmark telemetry: total cold-boot Recovery Time Objective was 1,272 seconds—dropping to under 7 minutes with a pre-baked Golden AMI.
  > Our Recovery Point Objective was measured directly from the ground-truth sequence probes at 290 seconds, comfortably beating our 5-minute SLA."

---

### Act 6: Automated Reverse Failback & Cloud Teardown (4:00 - 5:00)
* **Visual:** Run `make failback` in Terminal 1. Show Terraform destroy outputs.
* **Command:**
  ```bash
  make failback
  make cost-audit
  ```
* **Talk Track:**
  > "In disaster recovery, failover is only half the battle. DR isn't complete until we safely fail back home without losing data.
  > I trigger `make failback`. Our Ansible playbook establishes a secure SSH tunnel to the AWS replica database, dumps the post-failover delta transactions via `pg_dump`, restores them to our local PostgreSQL database, and verifies row counts.
  > Once data continuity is 100% confirmed, Route 53 DNS and the SSM fencing flag are returned to `onprem`, and the playbook triggers `make dr-down`.
  > Terraform cleanly destroys the ephemeral EC2 instance, VPC, and Elastic IP.
  > Running `make cost-audit` confirms zero residual compute instances. Our standing cloud compute spend is back to exactly **$0.00/month**.
  > Thank you for watching!"
