# Security Architecture & IAM Least Privilege

## 1. Credentials Strategy & Trade-Offs

For on-premises machines communicating with AWS APIs (specifically shipping database backups to S3):

### Options Considered
| Mechanism | Pros | Cons | Decision |
|---|---|---|---|
| **IAM Roles Anywhere** | No long-lived access keys; uses x509 PKI certificates; short-lived STS tokens | Requires operating a private CA (AWS Private CA costs $400/mo, or self-hosted OpenSSL/certbot CA setup); higher initial complexity | Deferred to enterprise hardening |
| **Scoped IAM User (`dr-onprem-backup-writer`) + Rotation Runbook** | Simple, zero standing AWS cost, compatible with standard tools (`aws-cli`, `pgBackRest`, `s3cmd`) | Long-lived credentials risk if leaked | **Accepted (Recommended for Lab)** |

### Security Guardrails for Scoped IAM User
1. **Scope Restriction**: Granted `s3:PutObject` strictly on prefix `backups/*` in the backup bucket.
2. **Negative Security Assertion**: Explicit `Deny` on `s3:DeleteObject` and `s3:DeleteObjectVersion`. Even if the backup shipper credentials are compromised, an adversary cannot delete historical database dumps or WAL files.
3. **Key Rotation Runbook**: Keys are rotated every 90 days or after failover drills via standard CLI rotation scripts, stored only in environment variables / vault, never committed to git.

---

## 2. Orchestrator Execution Role (`dr-orchestrator-role`)

The orchestrator requires minimal, task-specific IAM privileges:
- **Route 53**: `route53:ChangeResourceRecordSets` and `route53:GetChange` scoped strictly to the project's private/internal hosted zone ARN.
- **SSM Parameter Store**: `ssm:GetParameter` and `ssm:PutParameter` scoped strictly to `/hybrid-dr/active-site`.
- **EC2 Visibility**: `ec2:DescribeInstances` to inspect the status of replica instances.

---

## 3. Account & Spend Boundary Enforcement
- Long-lived root keys are strictly forbidden.
- Local administration uses named profile `dr-sandbox` with preflight verification against `DR_ALLOWED_ACCOUNT_ID`.
- An AWS Budget ceiling ($15.00/mo) monitors actual and forecasted spend across all resources, dispatching SNS alerts at 50%, 80%, and 100%.
