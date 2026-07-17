# Incident Response Runbook — API Key Exposure

## Overview

When a secret (API key, token, password) is exposed in a Git repository, **removing it from the current commit is NOT sufficient**. The key persists in the Git object graph (reflog, pack files, dangling objects) and remains accessible to anyone who cloned or forked the repository before remediation.

This runbook covers the full incident lifecycle: revocation → rotation → audit → history purge → force push.

---

## Step 1: Immediate Revocation (Time-Critical — Do Within Minutes)

**Goal:** Render the leaked credential useless immediately.

```bash
# Revoke the key via your provider's API or dashboard:
# - AWS: aws iam delete-access-key --access-key-id AKIAEXAMPLE
# - GitHub: Settings → Developer settings → Personal access tokens → Revoke
# - Stripe: Dashboard → API Keys → Roll key
# - GCP: gcloud iam service-accounts keys delete KEY_ID
```

> ⚠️ **Do NOT wait** for the history purge before revoking. Every minute the key remains active is a window for exploitation.

---

## Step 2: Rotate Credentials

**Goal:** Issue a new credential and deploy it to all consumers.

1. Generate a new key via the provider.
2. Update the secrets store (Vault, AWS Secrets Manager, Kubernetes Secret).
3. Deploy the updated secret to all services that depend on it.
4. Verify services are healthy with the new key.

```bash
# Example: update Kubernetes secret
kubectl create secret generic api-credentials \
  --from-literal=API_KEY='new-rotated-key-value' \
  --from-literal=API_SECRET='new-rotated-secret-value' \
  --dry-run=client -o yaml | kubectl apply -f -

# Restart deployments to pick up the new secret
kubectl rollout restart deployment/my-app
```

---

## Step 3: Audit Downstream Impact

**Goal:** Determine if the exposed key was used maliciously.

1. **Check provider audit logs:**
   - AWS CloudTrail: Filter by the compromised access key ID.
   - GCP: Cloud Audit Logs filtered by service account.
   - GitHub: Security log filtered by the token.

2. **Check application logs** for unusual activity during the exposure window.

3. **Identify exposure scope:**
   - Was the repo public or private?
   - How long was the key in the history?
   - Were there forks or clones during the exposure window?

4. **Document findings** in your incident tracking system.

---

## Step 4: Purge the Secret from Git History

**Goal:** Remove all traces of the secret from the Git object graph.

> ⚠️ This rewrites history. All collaborators must re-clone or reset their local copies.

### Option A: git filter-repo (Recommended)

```bash
# Install: pip install git-filter-repo

# Remove a specific file that contained the secret
git filter-repo --invert-paths --path .env

# Or replace a specific string across all history
git filter-repo --replace-text <(echo 'AKIAIOSFODNN7EXAMPLE==>***REDACTED***')
```

### Option B: BFG Repo-Cleaner (Simpler for file removal)

```bash
# Install: download from https://rtyley.github.io/bfg-repo-cleaner/

# Remove a file from history (keeps current commit intact)
java -jar bfg.jar --delete-files .env

# Replace specific text in all history
java -jar bfg.jar --replace-text passwords.txt

# Clean up
git reflog expire --expire=now --all
git gc --prune=now --aggressive
```

### After purging:

```bash
# Force push the cleaned history
git push origin --force --all
git push origin --force --tags

# Notify all collaborators to re-clone:
# git clone <repo-url>  (fresh clone)
# OR for existing clones:
# git fetch origin && git reset --hard origin/main
```

---

## Step 5: Verify Purge Completeness

```bash
# Search the entire history for remnants of the leaked key
git log --all -p | grep -i "AKIAEXAMPLE"

# Check if the secret appears in any ref
git rev-list --all | xargs git grep "AKIAEXAMPLE"

# If found, repeat Step 4 with corrected parameters
```

---

## Step 6: Prevent Recurrence

1. **Enable Gitleaks pre-commit hook** (see `.pre-commit-config.yaml`).
2. **Enable GitHub secret scanning** on the repository (Settings → Code security).
3. **Review `.gitignore`** to ensure `.env` and credential files are excluded.
4. **Rotate keys on a schedule** (see `key-rotation.py`).
5. **Use short-lived credentials** (e.g., AWS STS, Vault dynamic secrets) so leaked keys auto-expire.

---

## Key Reminders

| Myth | Reality |
|------|---------|
| "I deleted the file in a new commit" | The key is still in every prior commit's tree object |
| "I squashed the commit" | The original commit may survive in reflog or forks |
| "The repo is private" | Anyone with past access (or a fork) has the key |
| "It was only exposed briefly" | Bots scan GitHub in real-time for leaked keys |

---

## Contacts & Escalation

| Role | Contact |
|------|---------|
| Security Team Lead | security@example.com |
| Platform/Infra On-Call | #platform-oncall (Slack) |
| Incident Commander | Rotating — see PagerDuty |

---

*Last updated: 2026-07-17*
