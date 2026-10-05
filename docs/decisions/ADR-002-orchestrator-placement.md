# ADR-002: Orchestrator Control-Plane Placement
- Status: accepted
- Date: 2026-10-05

## Context
The orchestrator must never share a failure domain with the site it monitors.

## Options
| Option | Pros | Cons | Cost & Effort |
|---|---|---|---|
| 1. Inside on-prem lab | Direct API access | Fatal flaw: dies with on-prem site | $0.00; Minimal |
| 2. AWS Serverless | Zero idle compute | Complex Step Functions / CodeBuild state chaining | <$0.10/mo; High complexity |
| 3. AWS Witness (t4g.nano in Sydney) | True failure domain isolation, persistent daemon | Standing EC2 cost | ~$3.90/mo; Low effort |
| 4. Local macOS Host | Zero AWS cost, perfect for demo | Shares host power/ISP with lab | $0.00; Minimal |

## Decision
We adopt **Dual-Mode**: Production AWS Witness (`t4g.nano` in ap-southeast-2) with a local host CLI demo runner.
