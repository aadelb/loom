# Credential Vault Documentation

## Overview

The Credential Vault is a secure, encrypted storage system for managing API keys, authentication tokens, passwords, and other sensitive credentials. It provides three core operations:

- **Store**: Encrypt and persist credentials
- **Retrieve**: Decrypt and access stored credentials
- **List**: View stored credential metadata without exposing values

## Security Features

1. **XOR Encryption**: Uses XOR cipher with a machine-specific derived key
   - Key derived from hostname + username via SHA-256
   - Deterministic (same machine produces same key)
   - Not cryptographically-grade but suitable for obfuscation

2. **File Permissions**: Vault file stored with `600` permissions (rw-------)
   - Only owner can read/write
   - No group or world access

3. **Base64 Encoding**: Encrypted values encoded as base64 for safe JSON storage

4. **No Plaintext Logging**: Credentials never logged; only prefixes shown in list operations

## Tools

### 1. research_vault_store

Store a credential securely in the vault.

**Parameters:**
- `name` (str, required): Credential identifier (alphanumeric with underscores/dashes)
- `value` (str, required): Secret value to encrypt
- `category` (str, optional): Classification of the credential (default: "api_key")
  - Common categories: `api_key`, `token`, `password`, `oauth`, `secret`, `key`

**Returns:**
```json
{
  "stored": true,
  "name": "github_token",
  "category": "token",
  "value_prefix": "ghp_"
}
```

**Example:**
```python
result = await research_vault_store(
    name="openai_key",
    value="sk_live_123456789abcdefghijklmnop",
    category="api_key"
)
```

### 2. research_vault_retrieve

Retrieve and decrypt a stored credential.

**Parameters:**
- `name` (str, required): Credential name to retrieve

**Returns:**
```json
{
  "name": "openai_key",
  "value": "sk_live_123456789abcdefghijklmnop",
  "category": "api_key",
  "last_accessed": "2026-05-02T15:30:45.123456+00:00"
}
```

**Example:**
```python
cred = await research_vault_retrieve(name="openai_key")
api_key = cred["value"]
```

### 3. research_vault_list

List all stored credentials without exposing values.

**Parameters:** None

**Returns:**
```json
{
  "total": 3,
  "credentials": [
    {
      "name": "github_token",
      "category": "token",
      "stored_at": "2026-05-02T14:00:00.000000+00:00",
      "value_prefix": "****"
    },
    {
      "name": "openai_key",
      "category": "api_key",
      "stored_at": "2026-05-02T15:00:00.000000+00:00",
      "value_prefix": "****"
    }
  ]
}
```

**Example:**
```python
vault_status = await research_vault_list()
print(f"Stored {vault_status['total']} credentials")
for cred in vault_status["credentials"]:
    print(f"  - {cred['name']} ({cred['category']})")
```

## Storage Location

Credentials are stored at: `~/.loom/vault.json`

### File Format

```json
{
  "credential_name": {
    "encrypted": "base64_encoded_xor_cipher_text",
    "category": "api_key",
    "stored_at": "2026-05-02T15:30:45.123456+00:00",
    "accessed_at": "2026-05-02T15:30:45.123456+00:00"
  }
}
```

## Usage Patterns

### Initialize a credential vault

```python
# Store your API keys on first use
await research_vault_store(
    name="stripe_key",
    value="sk_live_abc123...",
    category="api_key"
)

await research_vault_store(
    name="github_token",
    value="ghp_abc123...",
    category="token"
)
```

### Retrieve credentials for use

```python
# Get a credential when needed
stripe_key_result = await research_vault_retrieve(name="stripe_key")
if "error" not in stripe_key_result:
    stripe_key = stripe_key_result["value"]
    # Use stripe_key in API calls
```

### Rotate credentials

```python
# Update a credential by storing with the same name
await research_vault_store(
    name="stripe_key",
    value="sk_live_new_abc123...",
    category="api_key"
)
# Old value is overwritten
```

### Audit stored credentials

```python
# List all credentials without exposing values
vault = await research_vault_list()
print(f"Total credentials stored: {vault['total']}")
for cred in vault["credentials"]:
    print(f"{cred['name']} - {cred['category']}")
```

## Limitations

1. **Machine-Specific**: The vault is machine-specific due to hostname + username in key derivation
   - Moving vault.json to another machine requires re-encrypting with the same key

2. **Not Cryptographically Secure**: XOR cipher is not suitable for high-security scenarios
   - Use for API key obfuscation, not classified data
   - Add additional encryption layer if needed

3. **Single-Key Design**: All credentials encrypted with same key
   - Loss of key exposes all credentials
   - Protect ~/.loom/vault.json with system security

## Best Practices

1. **Backup vault.json**: Store encrypted backups of `~/.loom/vault.json`
   - Credentials remain encrypted in backups

2. **Restrict File Access**: Ensure `~/.loom/` directory is user-only
   - File permissions set to `600` automatically
   - Directory permissions set to `700` automatically

3. **Rotate Secrets**: Periodically update stored credentials
   - Use `research_vault_store` with same `name` to overwrite

4. **Never Log Values**: Always retrieve via `research_vault_retrieve`
   - Never hardcode credentials in code
   - Never print retrieved values to logs

5. **Name Consistently**: Use clear, consistent naming conventions
   - Example: `{service}_{type}` like `github_token`, `stripe_key`, `openai_api_key`

## Error Handling

### Credential Not Found

```python
result = await research_vault_retrieve(name="nonexistent")
if "error" in result:
    print(f"Error: {result['error']}")  # "credential not found: nonexistent"
```

### Invalid Parameters

The vault validates input parameters:
- `name` must be alphanumeric with underscores/dashes
- `value` cannot be empty
- `category` is flexible (custom categories allowed)

Example error response:
```json
{
  "stored": false,
  "error": "name and value required"
}
```

## Integration Example

```python
from loom.tools import credential_vault

async def setup_api_clients(config_dict: dict) -> dict:
    """Initialize API clients using vault-stored credentials."""
    clients = {}
    
    # For each service, retrieve credential and init client
    for service in ["openai", "stripe", "github"]:
        cred_name = f"{service}_key"
        result = await credential_vault.research_vault_retrieve(name=cred_name)
        
        if "error" in result:
            logger.warning(f"Credential not found: {cred_name}")
            continue
        
        api_key = result["value"]
        clients[service] = init_client(service, api_key)
    
    return clients
```

## Security Considerations

1. **Key Derivation**: The vault derives encryption keys from machine identity
   - Hostname changes require re-encryption
   - User changes require re-encryption

2. **Memory Safety**: Decrypted values held in memory
   - Python doesn't guarantee memory cleanup
   - Decrypted values may persist in memory after use

3. **Filesystem Security**: Vault file on disk is only protected by file permissions
   - Depends on OS security (no additional encryption)
   - Physical disk access bypasses file permissions

4. **Audit Trail**: Vault tracks `stored_at` and `accessed_at` timestamps
   - Useful for compliance and rotation tracking
   - Accessible via `research_vault_list()`

## Future Enhancements

1. **Master Password**: Optional master password for additional security layer
2. **Hardware Tokens**: Support for TPM/secure enclave integration
3. **Audit Logging**: Detailed access logs with user context
4. **Credential Expiry**: Automatic expiration of stored credentials
5. **Multi-Key Rotation**: Separate keys for different credential categories
6. **Remote Vault**: HTTP endpoint for centralized credential management
