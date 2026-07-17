# API Security Setup

End-to-end configuration for secure API key management: prevention, runtime handling, rotation, and incident response.

---

## Quick Start

```bash
# 1. Install pre-commit hooks (blocks secrets from entering commits)
pip install pre-commit
pre-commit install

# 2. Copy .env.example to .env and fill in real values
cp .env.example .env

# 3. Verify Gitleaks catches secrets
echo 'API_KEY=sk-live-REAL_KEY_12345678901234' >> test-leak.txt
git add test-leak.txt
git commit -m "test"   # ← Should be BLOCKED by Gitleaks
rm test-leak.txt
```

---

## Components

| File | Purpose |
|------|---------|
| [`.gitignore`](../.gitignore) | Excludes `.env` and credential files from version control |
| [`.env.example`](../.env.example) | Template with placeholder values (safe to commit) |
| [`.pre-commit-config.yaml`](../.pre-commit-config.yaml) | Gitleaks pre-commit hook configuration |
| [`.gitleaks.toml`](../.gitleaks.toml) | Gitleaks custom rules and allowlists |
| [`kubernetes-secrets.yaml`](./kubernetes-secrets.yaml) | Kubernetes Secrets + Deployment manifest |
| [`vault-integration.py`](./vault-integration.py) | HashiCorp Vault runtime secret retrieval |
| [`key-rotation.py`](./key-rotation.py) | Automated key rotation script |
| [`INCIDENT-RESPONSE.md`](./INCIDENT-RESPONSE.md) | Step-by-step runbook for key exposure incidents |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Developer Workflow                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  .env (local only)  ──→  pre-commit hook (Gitleaks)  ──→  Git   │
│        ↓                         ↓                               │
│  Never committed            Blocks secrets                       │
│                                                                   │
├─────────────────────────────────────────────────────────────────┤
│                        Deployment Pipeline                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Vault / AWS SM  ──→  Kubernetes Secret  ──→  Pod env vars      │
│        ↓                                                         │
│  Runtime fetch                                                   │
│  (never in code)                                                 │
│                                                                   │
├─────────────────────────────────────────────────────────────────┤
│                        Operational                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  CronJob (key-rotation.py)  ──→  Vault  ──→  Pods auto-refresh │
│                                                                   │
│  Incident Response Runbook  ──→  Revoke → Rotate → Purge        │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Best Practices Summary

1. **Never commit secrets** — Use `.gitignore` + Gitleaks pre-commit hooks.
2. **Use a secrets manager** — HashiCorp Vault (recommended default), AWS Secrets Manager, or Infisical.
3. **Inject at runtime** — Pass credentials as environment variables via Kubernetes Secrets or Vault agent.
4. **Rotate frequently** — Automate rotation every 24–72 hours for high-sensitivity keys.
5. **Use short-lived credentials** — AWS STS tokens, Vault dynamic secrets, or OAuth2 client credentials with short TTLs.
6. **Enable GitHub secret scanning** — Repository Settings → Code security and analysis.
7. **Have an incident plan** — Know how to revoke, rotate, audit, and purge before an incident occurs.

---

## Alternatives Comparison

| Tool | Best For | Self-Hosted | Cloud-Native |
|------|----------|-------------|--------------|
| **HashiCorp Vault** ★ | Multi-cloud, complex policies | Yes | HCP Vault |
| AWS Secrets Manager | AWS-native stacks | No | Yes |
| GCP Secret Manager | GCP-native stacks | No | Yes |
| Azure Key Vault | Azure-native stacks | No | Yes |
| Infisical | Startups, developer UX | Yes | Yes |
| SOPS | GitOps encrypted secrets | Yes | No |

★ = Recommended default for most teams.
