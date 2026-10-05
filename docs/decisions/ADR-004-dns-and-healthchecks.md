# ADR-004: DNS Routing and Health Checking Behind Home NAT
- Status: accepted
- Date: 2026-10-05

## Context
On-prem sits behind residential NAT without public static IPs; Route 53 cannot probe RFC1918 IPs directly.

## Decision
We implement **Hybrid Push Heartbeat with Orchestrator-Driven Route 53 API Cutover**:
1. On-prem pushes heartbeat metrics to CloudWatch / WireGuard.
2. Failure declared after 3 missed checks across >=2 independent signal classes.
3. Fencing parameter acquired (`/hybrid-dr/active-site = AWS`) in SSM.
4. Route 53 UPSERT executed only after AWS replica passes HTTP smoke tests (TTL 30s).
