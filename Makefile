.PHONY: help lab-up lab-down lab-status lab-test cost-audit teardown
help:
	@echo "Hybrid DR Orchestrator Targets:"
	@echo "  make lab-up     - Start the on-premises 3-tier cluster"
	@echo "  make lab-down   - Destroy on-prem lab containers"
	@echo "  make lab-status - Verify healthz status and latest probe"
	@echo "  make lab-test   - Run CRUD and RPO accumulation test"
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
