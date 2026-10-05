SHELL := /bin/bash

.PHONY: help lab-up lab-down lab-status lab-test cost-audit teardown
help:
	@echo "Hybrid DR Orchestrator Targets:"
	@echo "  make lab-up     - Start the on-premises 3-tier cluster"
	@echo "  make lab-down   - Destroy on-prem lab containers"
	@echo "  make lab-status - Verify healthz status and latest probe"
	@echo "  make lab-test   - Run CRUD and RPO accumulation test"
	@echo "  make drill      - Run simulated DR drill (dry-run mode)"
	@echo "  make drill-live - Run live automated DR drill with cloud failover"
	@echo "  make failback   - Reverse-sync data to on-prem, restore DNS, and teardown AWS replica"
	@echo "  make dashboard  - Launch real-time Mission Control Web Dashboard UI (http://localhost:8500)"
	@echo "  make monitoring-up   - Launch Prometheus, Alertmanager, Grafana stack"
	@echo "  make monitoring-down - Stop monitoring stack"
	@echo "  make lint-all   - Run all linters (terraform, ruff, mypy, ansible)"
	@echo "  make security-scan   - Run gitleaks secret detection across repo"
	@echo "  make cost-audit - Audit active AWS resources tagged Project=hybrid-dr"
	@echo "  make teardown   - Teardown ephemeral DR replica resources (preserves persistent foundation)"


lab-up:
	docker compose -f infra/onprem/docker-compose.yml up -d --build
	@for i in {1..30}; do \
		if curl -sf http://localhost:8080/healthz >/dev/null 2>&1; then \
			echo "Cluster is healthy! (200 OK)"; exit 0; \
		fi; sleep 1; \
	done; echo "Timeout waiting for /healthz" >&2; exit 1
lab-down:
	docker compose -f infra/onprem/docker-compose.yml down -v --remove-orphans
lab-status:
	@curl -s -w "\nHTTP Status: %{http_code}\n" http://localhost:8080/healthz
	@docker exec onprem-db psql -U dr_user -d dr_app -c "SELECT probe_id, written_at_utc, cluster_node FROM rpo_probe ORDER BY probe_id DESC LIMIT 3;"
lab-test:
	@curl -s -X POST http://localhost:8080/items -H "Content-Type: application/json" -d '{"name": "order-101", "description": "pre-failover item"}'
	@echo ""
	@curl -s http://localhost:8080/items
	@echo ""
	@docker exec onprem-db psql -U dr_user -d dr_app -c "SELECT COUNT(*) AS probe_ticks_recorded FROM rpo_probe;"
cost-audit:
	@./scripts/cost_guard.sh
teardown:
	@echo "Checking for ephemeral DR resources to teardown..."
	@if [ -d infra/aws/envs/dr ]; then \
		echo "Found ephemeral DR root. Destroying ephemeral AWS resources..."; \
		cd infra/aws/envs/dr && terraform destroy; \
	else \
		echo "No ephemeral DR root deployed yet. Persistent foundation is preserved."; \
	fi

.PHONY: backup restore-test wg-keys-check
backup:
	@./scripts/backup_base.sh

restore-test:
	@./scripts/test_restore.sh

wg-keys-check:
	@./infra/networking/gen_wireguard_keys.sh --check

# --- Phase 4: DR Environment Targets ---

.PHONY: dr-up dr-down dr-configure dr-restore dr-test

dr-up:
	@if [ ! -f ~/.ssh/id_rsa.pub ]; then echo "Generating SSH key for Ansible..."; ssh-keygen -t rsa -b 2048 -f ~/.ssh/id_rsa -q -N ""; fi
	@echo "Deploying AWS DR Environment..."
	cd infra/aws/envs/dr && \
	TF_VAR_ssh_public_key="$$(cat ~/.ssh/id_rsa.pub)" terraform init && \
	TF_VAR_ssh_public_key="$$(cat ~/.ssh/id_rsa.pub)" terraform apply

dr-down:
	@echo "Checking safety before destroying DR environment..."
	@cd infra/aws/envs/dr && if terraform state list | grep -q 'aws_s3_bucket'; then echo "FATAL: Persistent state found in DR env! Aborting."; exit 1; fi
	@echo "Destroying DR Environment..."
	cd infra/aws/envs/dr && TF_VAR_ssh_public_key="$$(cat ~/.ssh/id_rsa.pub)" terraform destroy

dr-configure:
	@echo "Configuring DR instance..."
	set -a; . infra/onprem/.env; set +a; cd ansible && ansible-playbook playbooks/site.yml

dr-restore:
	@echo "Restoring database on DR instance..."
	set -a; . infra/onprem/.env; set +a; cd ansible && ansible-playbook playbooks/restore_db.yml

dr-test:
	@echo "Running smoke tests..."
	set -a; . infra/onprem/.env; set +a; cd ansible && ansible-playbook playbooks/smoke_tests.yml

# --- Phase 5: Orchestrator Targets ---

.PHONY: orch-setup orch-test orch-drill
orch-setup:
	@cd orchestrator && make setup

orch-test:
	@cd orchestrator && make orch-test

orch-drill:
	@cd orchestrator && make run-dry

.PHONY: dashboard
dashboard:
	@echo "Launching Mission Control Web Dashboard on http://localhost:8500 ..."
	@cd orchestrator && PYTHONPATH=src ./venv/bin/python -m hybrid_dr.cli dashboard --host 0.0.0.0 --port 8500

# --- Phase 6: Failback and Chaos Engineering Targets ---

.PHONY: drill drill-live failback chaos-kill chaos-net
drill:
	@./scripts/drill.sh --dry-run

drill-live:
	@./scripts/drill.sh

failback:
	set -a; . infra/onprem/.env; set +a; cd ansible && ansible-playbook playbooks/failback.yml

chaos-kill:
	@./scripts/chaos_kill_onprem.sh --dry-run

chaos-net:
	@./scripts/chaos_network_drop.sh --dry-run

# --- Phase 7: Observability, CI/CD and Security Targets ---

.PHONY: monitoring-up monitoring-down lint-all security-scan
monitoring-up:
	@echo "Starting Prometheus, Alertmanager, and Grafana stack..."
	docker compose -f infra/monitoring/docker-compose.yml up -d
	@echo "Grafana accessible at http://localhost:3000 (admin / admin)"
	@echo "Prometheus accessible at http://localhost:9090"
	@echo "Alertmanager accessible at http://localhost:9093"

monitoring-down:
	@echo "Stopping monitoring stack..."
	docker compose -f infra/monitoring/docker-compose.yml down

lint-all:
	@echo "==> Checking Terraform formatting..."
	terraform fmt -check -recursive
	@echo "==> Running Ruff formatting and linting..."
	cd orchestrator && ./venv/bin/ruff format --check src tests && ./venv/bin/ruff check src tests
	@echo "==> Running Mypy strict type checking..."
	cd orchestrator && ./venv/bin/mypy --strict src tests
	@echo "==> Running Ansible syntax checks..."
	cd ansible && ansible-playbook playbooks/site.yml --syntax-check
	cd ansible && ansible-playbook playbooks/restore_db.yml --syntax-check
	cd ansible && ansible-playbook playbooks/smoke_tests.yml --syntax-check
	cd ansible && ansible-playbook playbooks/failback.yml --syntax-check
	@echo "✅ All codebases passed linting & type checks."

security-scan:
	@echo "==> Running Gitleaks secret detection across repository..."
	gitleaks dir . -v

