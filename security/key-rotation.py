"""
Automated Key Rotation Script
==============================
Implements scheduled rotation of API keys using short-lived credentials.
Short-lived keys limit blast radius: even if a key leaks, it expires quickly.

Strategy:
  1. Generate a new key via the provider API.
  2. Update the secret store (Vault / AWS Secrets Manager) with the new key.
  3. Verify the new key works (health check).
  4. Revoke the old key.
  5. Log the rotation event for audit.

Schedule this script via cron, Kubernetes CronJob, or CI/CD pipeline.
Recommended rotation interval: every 24–72 hours for high-sensitivity keys.

Example cron (rotate daily at 02:00 UTC):
  0 2 * * * /usr/bin/python3 /opt/security/key-rotation.py

Example Kubernetes CronJob:
  apiVersion: batch/v1
  kind: CronJob
  metadata:
    name: api-key-rotation
  spec:
    schedule: "0 2 * * *"
    jobTemplate:
      spec:
        template:
          spec:
            containers:
              - name: rotator
                image: my-rotator:latest
                command: ["python3", "key-rotation.py"]
                envFrom:
                  - secretRef:
                      name: vault-credentials
            restartPolicy: OnFailure
"""

import os
import logging
import datetime
import secrets
import hvac

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# Configuration
VAULT_ADDR = os.environ.get("VAULT_ADDR", "https://vault.example.com")
VAULT_ROLE_ID = os.environ["VAULT_ROLE_ID"]
VAULT_SECRET_ID = os.environ["VAULT_SECRET_ID"]
SECRET_PATH = "myapp/production/api-keys"
KEY_LENGTH = 48  # bytes of entropy for new keys


def authenticate_vault() -> hvac.Client:
    """Authenticate to Vault using AppRole."""
    client = hvac.Client(url=VAULT_ADDR)
    client.auth.approle.login(role_id=VAULT_ROLE_ID, secret_id=VAULT_SECRET_ID)
    if not client.is_authenticated():
        raise RuntimeError("Vault authentication failed")
    return client


def generate_new_key() -> str:
    """Generate a cryptographically secure API key."""
    return secrets.token_urlsafe(KEY_LENGTH)


def rotate_key(client: hvac.Client, key_name: str) -> tuple[str, str]:
    """
    Rotate a single key in Vault.

    Returns:
        Tuple of (old_key, new_key) for verification purposes.
    """
    # Read current secrets
    current = client.secrets.kv.v2.read_secret_version(
        path=SECRET_PATH, mount_point="secret"
    )
    current_data = current["data"]["data"]
    old_key = current_data.get(key_name)
    if not old_key:
        raise RuntimeError(
            f"Existing key '{key_name}' not found at secret path '{SECRET_PATH}'"
        )

    # Generate new key
    new_key = generate_new_key()

    # Update Vault with new key
    updated_data = {**current_data, key_name: new_key}
    client.secrets.kv.v2.create_or_update_secret(
        path=SECRET_PATH, secret=updated_data, mount_point="secret"
    )

    logger.info(
        "Rotated key '%s' at %s",
        key_name,
        datetime.datetime.utcnow().isoformat(),
    )
    return old_key, new_key


def verify_new_key(new_key: str) -> bool:
    """
    Verify the new key works by hitting a health-check endpoint.
    Replace this with your actual verification logic.
    """
    # Example: make an authenticated request to your API
    # response = requests.get(
    #     "https://api.example.com/health",
    #     headers={"Authorization": f"******"}
    # )
    # return response.status_code == 200
    raise NotImplementedError(
        "verify_new_key() must be implemented before running key rotation in production"
    )


def revoke_old_key(old_key: str) -> None:
    """
    Revoke the old key via provider API.
    Replace with actual revocation call for your provider.
    """
    if not old_key:
        return
    # Example: requests.delete(
    #     "https://api.example.com/keys",
    #     json={"key": old_key}
    # )
    logger.info("Old key revoked (prefix: %s...)", old_key[:8] if old_key else "N/A")


def main() -> None:
    """Execute full key rotation cycle."""
    logger.info("=== Starting automated key rotation ===")

    client = authenticate_vault()

    for key_name in ("API_KEY", "API_SECRET"):
        old_key, new_key = rotate_key(client, key_name)

        if not verify_new_key(new_key):
            logger.error(
                "Verification FAILED for '%s'. Rolling back.", key_name
            )
            # Rollback: restore old key
            current = client.secrets.kv.v2.read_secret_version(
                path=SECRET_PATH, mount_point="secret"
            )
            rollback_data = {**current["data"]["data"], key_name: old_key}
            client.secrets.kv.v2.create_or_update_secret(
                path=SECRET_PATH, secret=rollback_data, mount_point="secret"
            )
            raise RuntimeError(f"Key rotation failed for {key_name}")

        revoke_old_key(old_key)

    logger.info("=== Key rotation completed successfully ===")


if __name__ == "__main__":
    main()
