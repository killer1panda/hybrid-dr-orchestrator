# Runbook: AWS Foundation Setup (Phase 2)

## 1. Prerequisites & Safety Guardrails
Before interacting with AWS, ensure:
1. The AWS CLI is installed (`brew install awscli`).
2. The named profile `dr-sandbox` is configured in `~/.aws/credentials`:
   ```ini
   [dr-sandbox]
   aws_access_key_id = <YOUR_KEY_ID>
   aws_secret_access_key = <YOUR_SECRET_KEY>
   ```
3. Export the required safety guardrail environment variable:
   ```bash
   export DR_ALLOWED_ACCOUNT_ID="758579869433"
   export AWS_PROFILE="dr-sandbox"
   ```
4. Confirm identity before running any cloud operations:
   ```bash
   aws sts get-caller-identity
   ```
   **Invariant Check**: If the account ID returned does not match `$DR_ALLOWED_ACCOUNT_ID`, STOP immediately.

---

## 2. Bootstrapping Persistent Layer & Remote State

### Step 1: Local State First Apply
Because the S3 bucket is created by Terraform itself (bootstrap chicken-and-egg), start with local state:
```bash
cd infra/aws/persistent
terraform init -backend=false
terraform plan
```
Inspect the plan output:
- Verify 8 resources to add, 0 to change, 0 to destroy.
- Verify monthly standing cost is estimated at ~$0.93 USD.
- Require human approval before running `terraform apply`.

```bash
terraform apply
```

### Step 2: Migrate to S3 Remote State with Native S3 Locking
Modern Terraform (v1.10+) supports native state locking directly on S3 without requiring a DynamoDB table via `use_lockfile = true` (utilizing S3 conditional writes). This saves costs and removes unnecessary infrastructure.

Add the backend block to `infra/aws/persistent/main.tf`:
```hcl
terraform {
  backend "s3" {
    bucket       = "<bucket_name_from_outputs>"
    key          = "persistent/terraform.tfstate"
    region       = "ap-southeast-2"
    profile      = "dr-sandbox"
    use_lockfile = true
  }
}
```

Migrate local state into the bucket:
```bash
terraform init -migrate-state
```

---

## 3. Negative Security Testing for IAM Backup Writer

Verify that `dr-onprem-backup-writer` has least-privilege permissions and that destructive actions are blocked:

### Test 1: Write to Allowed Prefix (Should Succeed)
```bash
aws s3 cp test-dump.sql s3://<bucket_name>/backups/test-dump.sql --profile dr-onprem-backup-writer
```

### Test 2: Negative Test - Write Outside Prefix (Should Fail with AccessDenied)
```bash
aws s3 cp test-dump.sql s3://<bucket_name>/root-dump.sql --profile dr-onprem-backup-writer
```

### Test 3: Negative Test - Delete Object (Should Fail with AccessDenied)
```bash
aws s3 rm s3://<bucket_name>/backups/test-dump.sql --profile dr-onprem-backup-writer
```

---

## 4. Cost Guard Verification

Run the cost audit script to verify only persistent resources exist and no rogue compute or NAT gateways were provisioned:
```bash
make cost-audit
```
