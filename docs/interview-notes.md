# Master Interview Cheat Sheet & Architecture Defense

**Project:** Automated Hybrid Cloud Disaster Recovery Orchestrator  
**Target Roles:** Senior DevOps Engineer, Site Reliability Engineer (SRE), Cloud Infrastructure Architect  
**Author:** Ajay  
**Repository:** [killer1panda/hybrid-dr-orchestrator](https://github.com/killer1panda/hybrid-dr-orchestrator)  

---

## 🏆 Top Architectural Trade-offs

### 1. Pilot Light vs. Warm Standby
* **Trade-off:** We selected a "Pilot Light" architecture (only database backups and continuous WAL are replicated; compute is \$0.00/month and provisioned on-demand via Terraform and Ansible) over an always-on "Warm Standby" (EC2 replica running 24/7).
* **Rationale:** Reduces standing cloud infrastructure costs by over 98% (from ~\$40.00/month to ~\$0.50/month in Route 53/S3), at the trade-off of a higher cold Recovery Time Objective (~21 minutes vs. ~2 minutes). With pre-baked Golden AMIs, RTO drops to < 7 minutes with zero standing compute.

### 2. Multi-Signal Quorum Engine vs. Single Health Check
* **Trade-off:** We require concurrent sustained failures across $\ge 2$ independent signal classes (Layer 7 HTTP `/healthz`, Layer 4 TCP connect on port 80/5432, and out-of-band push heartbeats) across $N \ge 3$ consecutive ticks before declaring disaster.
* **Rationale:** Prevents catastrophic "false-alarm" failovers caused by single-probe anomalies, transient packet drops, reverse proxy reloads, or residential ISP blips. Oscillating failures are dampened by 60-second flapping cooldowns.

### 3. Client-Side Encryption (PBKDF2 AES-256) vs. Solely SSE-S3
* **Trade-off:** PostgreSQL base backups and continuous WAL segments are encrypted locally before upload using OpenSSL AES-256-CBC with PBKDF2 (200,000 iterations), in addition to S3 server-side encryption.
* **Rationale:** In a zero-trust hybrid cloud architecture, WAN transport and cloud storage are treated as untrusted boundaries. Even if AWS root or backup-writer IAM credentials leak, historical backup blobs remain cryptographically secure.

### 4. OIDC Read-Only CI Pipeline vs. Automated CI Apply
* **Trade-off:** Our GitHub Actions workflow validates and tests IaC (`terraform validate`, `tflint`, `ansible-lint`) using GitHub OIDC with a strictly read-only AWS role (`dr-github-actions-readonly`), explicitly omitting `terraform apply`.
* **Rationale:** Granting automated write permissions to CI creates a massive supply-chain attack vector. Automated `apply` from pull requests risks wallet exhaustion or accidental production teardowns. Cloud provisioning is strictly gated behind the Python Orchestrator state machine.

---

## 🎯 5 Verified Resume Bullets (Empirical Metrics)

* **Engineered an automated hybrid cloud disaster recovery orchestrator** connecting an on-premises 3-tier private cloud to AWS `ap-southeast-2`, achieving an empirical **RTO of 21.2 minutes** (dropping to **< 7 minutes** via pre-baked AMIs) and **RPO of 290 seconds** (< 5m SLA) with **$0.00/month in standing compute spend**.
* **Developed a dual-witness Python 3.11 finite state machine and multi-signal Quorum Engine** requiring concurrent failures across independent fault domains (HTTP L7, TCP L4, SSM heartbeats) to eliminate false failovers, with atomic file replacement guaranteeing idempotent crash recovery.
* **Built a zero-loss automated reverse failback pipeline** using Ansible to tunnel into AWS PostgreSQL, export delta transaction logs via `pg_dump`, verify row counts and continuous probe sequences, and trigger automated Terraform teardowns saving **~$0.034/hour** per drill.
* **Architected a ransomware-resilient hybrid backup pipeline** streaming continuous PostgreSQL WAL segments and base backups with client-side PBKDF2 AES-256 encryption, S3 bucket versioning, and scoped IAM policies enforcing an explicit hard `Deny` on `s3:DeleteObject`.
* **Implemented an enterprise DevSecOps & Observability stack** utilizing Prometheus, Alertmanager, and Grafana as Code alongside GitHub Actions CI (pinned action SHAs, OIDC read-only AWS IAM roles, Dependabot, `mypy --strict`, `ruff`, and `gitleaks` pre-commit scanning).

---

## 💡 10 Deep-Dive Interview Questions & Answers

### Q1: Why did you place the DR Orchestrator outside the on-premises failure domain?
> **Answer:** "A core principle of disaster recovery engineering is avoiding shared failure domains between the control plane and the systems it monitors (ADR-002). If the orchestrator lived inside the on-premises cluster or VM bridge, a total site blackout (power loss, switch failure, or kernel panic) would kill the orchestrator itself, preventing failover. In our production architecture, the orchestrator runs as a lightweight witness in AWS (`t4g.nano`) or on an independent cloud provider, polling the on-premises site across independent transport layers."

### Q2: How does your system prevent split-brain writes during a network partition?
> **Answer:** "Split-brain occurs when both on-premises and AWS believe they are primary and accept concurrent writes. We mitigate this using a multi-layered fencing protocol (ADR-004): before Route 53 DNS is updated, the orchestrator sets AWS SSM Parameter `/hybrid-dr/active-site` to `aws`. The on-premises database node runs a local watchdog that queries this parameter every 10 seconds; if it sees `aws` or loses outbound internet connectivity for 30 seconds, it immediately sets PostgreSQL `default_transaction_read_only = on` to reject local writes. When failing back, delta synchronization is verified before resetting the fencing parameter to `onprem`."

### Q3: How did you measure ground-truth RPO without relying on timestamps from potentially out-of-sync clocks?
> **Answer:** "Clock skew across hybrid environments makes NTP timestamps unreliable for exact data loss calculations. We built an independent continuous RPO probe daemon (`app/rpo_probe.py`) that inserts an incrementing integer `probe_id` alongside a UTC timestamp into `rpo_probe` every second. During chaos drills, we capture the maximum committed probe ID immediately before site destruction. After the AWS replica restores base backups and replays all available WAL segments from S3, we query `SELECT MAX(written_at_utc), MAX(probe_id) FROM rpo_probe`. RPO is computed as the exact wall-clock lag: `clock_timestamp() - MAX(written_at_utc)`. In our empirical tests, this was exactly 290 seconds, satisfying our 300-second budget."

### Q4: Why did cold provisioning take 21 minutes, and how do you reduce it in production?
> **Answer:** "In our baseline tests, deploying on a stock Ubuntu 24.04 LTS AMI took 1,272 seconds (~21.2 minutes). Profiling our audit logs revealed that Terraform infrastructure provisioning took only 81 seconds, but Ansible host configuration took 754 seconds (12.5 minutes) because it ran `apt-get update`, installed Docker CE, compiled Python packages, and pulled container images. In production, we eliminate this software initialization latency by using HashiCorp Packer to pre-bake a Golden AMI containing the Docker daemon, base images, and runtime tools. This reduces the host configuration stage to under 90 seconds, yielding an optimized RTO of under 7 minutes while maintaining $0 standing compute costs."

### Q5: What happens if client DNS resolvers cache the old IP address after Route 53 cutover?
> **Answer:** "Even though Route 53 propagates DNS updates across authoritative nameservers in seconds, downstream recursive resolvers cache responses for the duration of the record's Time-To-Live (TTL). In Drill 2, we tested this: client applications experienced an additional 60-second downtime corresponding to our Route 53 TTL. We mitigate this by keeping DR record TTL at 60 seconds (balancing propagation agility against query resolution costs) and designing client API SDKs with Happy Eyeballs / dual-IP failover logic and exponential retry backoff."

### Q6: How does the orchestrator recover if its own process is killed mid-failover?
> **Answer:** "Disaster recovery orchestrators cannot assume they will run uninterrupted. We designed the state machine as a pure finite state machine with deterministic transitions: `IDLE -> FENCING -> PROVISIONING -> RESTORING -> TESTING -> CUTOVER -> COMPLETED`. State transitions are committed to disk using atomic file replacement (`os.replace` via temporary files) to prevent corrupted JSON writes. In Drill 3, we simulated a `SIGKILL` during `PROVISIONING`. When the supervisor daemon restarted, it loaded `/tmp/hybrid_dr_state.json`, detected state `RESTORING`, and resumed immediately without re-running Terraform or duplicating AWS resources."

### Q7: Why did you use WireGuard instead of IPsec for hybrid transport?
> **Answer:** "WireGuard operates inside the Linux kernel with a minimal codebase (~4,000 lines vs. over 100,000 lines for StrongSwan/IPsec), drastically reducing attack surface and maintenance complexity. It uses modern ChaCha20-Poly1305 authenticated encryption and Curve25519 ECDH. Crucially, WireGuard handles NAT traversal seamlessly via `PersistentKeepalive = 25`, allowing an on-premises residential or private lab behind CGNAT to maintain a persistent reverse tunnel to AWS without requiring inbound port forwarding or a public static IP."

### Q8: What is the security advantage of your S3 backup IAM policy having an explicit Deny?
> **Answer:** "IAM follows an explicit deny model: if an evaluation encounters a single `Deny`, the request is rejected regardless of any other `Allow` policies. Our on-premises backup shipper requires credentials to upload WAL segments and base backups to S3. If an attacker compromises the on-premises host or steals the access key, ransomware adversaries routinely attempt to delete existing S3 backups to prevent recovery. By attaching an explicit `Deny` on `s3:DeleteObject` and `s3:DeleteObjectVersion`, even an attacker holding valid credentials is mathematically prevented from purging historical backup blobs."

### Q9: How does the Quorum Engine avoid flapping during intermittent network brownouts?
> **Answer:** "During network brownouts, connectivity oscillates between healthy and failed states. If an orchestrator responded immediately, it would trigger partial provisioning, tear it down, and trigger it again. Our Quorum Engine enforces three stability controls: (1) multiple independent signal failure domains (L7 application HTTP, L4 TCP socket, and push heartbeats), (2) a threshold requiring $N \ge 3$ consecutive unanimous failure evaluations, and (3) a 60-second cooldown timer following any status change. If a single check passes during the evaluation window, the consecutive failure counter resets to zero."

### Q10: How does your failback process prevent data loss for transactions written in AWS?
> **Answer:** "Failing over to AWS means the cloud replica becomes the authoritative write master. Simply restarting on-premises containers would cause data divergence. Our failback playbook (`ansible/playbooks/failback.yml`) executes a five-stage safety sequence: (1) it opens an encrypted SSH tunnel to the AWS PostgreSQL replica, (2) dumps all post-failover transaction deltas via `pg_dump`, (3) restores the delta to the local database container, (4) verifies row counts and probe sequence continuity, and (5) only after verified data parity does it switch Route 53 DNS and trigger `make dr-down` to terminate AWS resources. If delta extraction or restore fails, the playbook aborts, keeping AWS live and alerting operators."

---

## 📚 Phase-by-Phase Architecture Evolution

* **Phase 0 (Plan):** Defined architecture constraints (RTO $\le$ 15m, RPO $\le$ 5m), accepted ADR-001 through ADR-004, cost model (~$0.50/mo standing, <$0.02/drill).
* **Phase 1 (On-Premises):** Containerized 3-tier lab (FastAPI, Nginx, PostgreSQL 16) with 1s monotonic RPO probe daemon and strict `lab-inventory.yml` chaos boundaries.
* **Phase 2 (AWS Foundation):** Persistent AWS layer in `ap-southeast-2` (S3 backup bucket with versioning & SSE-S3, native S3 state locking via `use_lockfile = true`, private Route 53 zone `dr-lab.internal`, SSM fencing parameter, and $15/mo budget alarm).
* **Phase 3 (Network & Backups):** WireGuard site-to-site VPN, continuous PostgreSQL WAL shipper, PBKDF2 AES-256 client encryption, automated PITR test harness with JSONL audit logging.
* **Phase 4 (DR Environment):** Ephemeral AWS replica root (EC2 `t3.small`, VPC, dynamic IP ingress restriction), Ansible configuration, S3 encrypted restore, and empirical benchmark validation (RTO: 1,272s, RPO: 290s).
* **Phase 5 (Orchestrator):** Python 3.11 deterministic state machine, multi-signal Quorum Engine, atomic disk persistence (`os.replace`), leader locking (`fcntl.flock`), and safe subprocess wrappers.
* **Phase 6 (Failback & Chaos):** Guarded chaos tooling (`scripts/chaos_*.sh` with host interface refusal), 3-scenario benchmark drills, and reverse replication failback playbook (`failback.yml`).
* **Phase 7 (CI & Security):** Prometheus/Grafana observability as code, hardened GitHub Actions CI (pinned action SHAs, OIDC read-only AWS IAM role, Dependabot), and STRIDE threat model in `docs/security.md`.
* **Phase 8 (Portfolio):** Recruiter-ready `README.md`, 5-minute video demo script (`docs/demo-script.md`), and master interview defense guide.
