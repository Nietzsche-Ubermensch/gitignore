"""
Secret Management Platform Integration — HashiCorp Vault
=========================================================
Recommended default: HashiCorp Vault (widely adopted, open-source, cloud-agnostic).
Alternatives:
  - AWS Secrets Manager (best for AWS-native stacks)
  - Google Cloud Secret Manager (best for GCP-native stacks)
  - Azure Key Vault (best for Azure-native stacks)
  - Infisical (developer-friendly, open-source, good for startups)

This module retrieves secrets from Vault at runtime so that credentials
are never stored statically in the codebase or environment files.

Prerequisites:
  pip install hvac  (HashiCorp Vault Python client)
"""

import os
import hvac


def get_vault_client() -> hvac.Client:
    """Authenticate with Vault using AppRole (recommended for services)."""
    vault_addr = os.environ.get("VAULT_ADDR", "https://vault.example.com")
    role_id = os.environ["VAULT_ROLE_ID"]
    secret_id = os.environ["VAULT_SECRET_ID"]

    client = hvac.Client(url=vault_addr)
    client.auth.approle.login(role_id=role_id, secret_id=secret_id)

    if not client.is_authenticated():
        raise RuntimeError("Vault authentication failed")
    return client


def get_secret(path: str, key: str, mount_point: str = "secret") -> str:
    """
    Retrieve a single secret value from Vault KV v2 engine.

    Args:
        path: Secret path (e.g., "myapp/production/api-keys")
        key: Key within the secret (e.g., "API_KEY")
        mount_point: KV engine mount point (default: "secret")

    Returns:
        The secret value as a string.
    """
    client = get_vault_client()
    response = client.secrets.kv.v2.read_secret_version(
        path=path, mount_point=mount_point
    )
    return response["data"]["data"][key]


# ---------------------------------------------------------------------------
# Example usage
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # At application startup, pull secrets from Vault:
    api_key = get_secret("myapp/production/api-keys", "API_KEY")
    api_secret = get_secret("myapp/production/api-keys", "API_SECRET")

    print("API_KEY loaded from Vault")
    print("API_SECRET loaded from Vault")


# ---------------------------------------------------------------------------
# Alternative: AWS Secrets Manager (uncomment to use)
# ---------------------------------------------------------------------------
# import boto3, json
#
# def get_aws_secret(secret_name: str, region: str = "us-east-1") -> dict:
#     """Retrieve a secret from AWS Secrets Manager."""
#     client = boto3.client("secretsmanager", region_name=region)
#     response = client.get_secret_value(SecretId=secret_name)
#     return json.loads(response["SecretString"])
#
# secrets = get_aws_secret("myapp/production/api-keys")
# api_key = secrets["API_KEY"]


# ---------------------------------------------------------------------------
# Alternative: Infisical (uncomment to use)
# ---------------------------------------------------------------------------
# from infisical_client import ClientSettings, InfisicalClient, GetSecretOptions
#
# def get_infisical_secret(key: str) -> str:
#     """Retrieve a secret from Infisical."""
#     client = InfisicalClient(ClientSettings(
#         client_id=os.environ["INFISICAL_CLIENT_ID"],
#         client_secret=os.environ["INFISICAL_CLIENT_SECRET"],
#         site_url="https://app.infisical.com",
#     ))
#     secret = client.getSecret(options=GetSecretOptions(
#         environment="prod",
#         project_id=os.environ["INFISICAL_PROJECT_ID"],
#         secret_name=key,
#     ))
#     return secret.secret_value
