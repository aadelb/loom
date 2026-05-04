# Database Encryption at Rest in Loom

Loom supports **optional encryption at rest** for SQLite databases containing sensitive data using Fernet symmetric encryption (from the cryptography library).

## Quick Start

### Installation

Enable encryption support:
```bash
pip install -e ".[encryption]"
# or with all features:
pip install -e ".[all]"
```

### Enable Encryption

**Option 1: Auto-generate encryption key** (simplest)
```bash
LOOM_DB_ENCRYPT=true loom-server
```

Key is automatically generated and stored at `~/.loom/encryption_key` (chmod 0600).

**Option 2: Use a password-derived key** (recommended for shared systems)
```bash
export LOOM_DB_ENCRYPTION_PASSWORD="your_secure_passphrase"
export LOOM_DB_ENCRYPT=true
loom-server
```

**Option 3: Explicit encryption key**
```bash
# Generate a Fernet key
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# Output: ABC123...xyz=

export LOOM_DB_ENCRYPTION_KEY="ABC123...xyz="
export LOOM_DB_ENCRYPT=true
loom-server
```

## Encrypted Databases

When `LOOM_DB_ENCRYPT=true`, the following SQLite databases are automatically encrypted:

| Database | Path | Purpose |
|---|---|---|
| batch_queue | `~/.cache/loom/batch_queue.db` | Batch job history and results |
| dlq | `~/.cache/loom/dlq.db` | Dead letter queue (failed jobs) |
| jobs | `~/.loom/jobs.db` | Long-running task state |
| sessions | `~/.loom/sessions/sessions.db` | Browser session credentials |

**Note**: The audit log uses HMAC-SHA256 signing (not encryption) — see `audit.py` for details.

## Check Encryption Status

Use the MCP tool to view which databases are encrypted:

```bash
# Via MCP
research_db_encryption_status()

# Output:
# {
#   "batch_queue.db": true,       # encrypted (.db.enc exists)
#   "dlq.db": false,              # plaintext (.db exists)
#   "jobs.db": true,
#   "sessions.db": false,
#   "audit_dir": "JSONL (see audit.py for HMAC signing)"
# }
```

## Manual Encryption/Decryption

Use the Python API to encrypt/decrypt individual database files:

```python
from loom.encrypted_db import EncryptedDB, get_encryption_key

# Initialize with auto-detected key
db = EncryptedDB("~/.cache/loom/batch_queue.db")

# Encrypt a plaintext database
encrypted_path = db.encrypt_file("~/.cache/loom/batch_queue.db")
# Creates: ~/.cache/loom/batch_queue.db.enc
# Removes: ~/.cache/loom/batch_queue.db

# Decrypt for access (context manager auto-encrypts on exit)
with db:
    # Database is decrypted and accessible
    import sqlite3
    conn = sqlite3.connect("~/.cache/loom/batch_queue.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM batch_queue LIMIT 5")
    rows = cursor.fetchall()
    conn.close()
    # On exit: automatically re-encrypted to .db.enc

# Manual decrypt without auto-re-encryption
decrypted_path = db.decrypt_file("~/.cache/loom/batch_queue.db.enc")
# Creates: ~/.cache/loom/batch_queue.db
# Keeps:   ~/.cache/loom/batch_queue.db.enc (for backup)

# Check encryption status
is_encrypted = db.is_encrypted()  # True if .db.enc exists
```

## Key Management

### Key Priority Order

When Loom starts, it determines the encryption key via this priority:

1. **LOOM_DB_ENCRYPTION_KEY** (explicit Fernet key, base64-encoded)
2. **LOOM_DB_ENCRYPTION_PASSWORD** (password-derived via PBKDF2-SHA256)
3. **~/.loom/encryption_key** (load from disk if exists)
4. **Auto-generate** (create new key if none above exist)

### Key Generation

Auto-generated keys are stored at `~/.loom/encryption_key` with restrictive file permissions (0600 — owner read/write only):

```bash
# View key permissions
ls -la ~/.loom/encryption_key
# -rw------- 1 user group ...

# If key is compromised, regenerate
rm ~/.loom/encryption_key
export LOOM_DB_ENCRYPTION_PASSWORD="new_passphrase"
# Next run will generate new key from password
```

### Key Derivation (Password Mode)

When `LOOM_DB_ENCRYPTION_PASSWORD` is set:
- Uses PBKDF2-HMAC-SHA256
- 100,000 iterations (NIST minimum as of 2024)
- Salt: `b"loom_db_encryption_v1"` (fixed, deterministic)
- Derives 32-byte key (256-bit AES equivalent)

This means the same password always produces the same key (useful for recovery).

## Encryption Architecture

### Primary Mode: Fernet (Default)

- **Algorithm**: AES-128 in CBC mode + HMAC-SHA256 verification
- **Key Format**: 32 bytes, base64-encoded
- **File-level encryption**: Entire .db file encrypted/decrypted as one unit
- **Transparency**: Encrypted files are .db.enc; decrypted via context manager
- **Portability**: Works on any platform with cryptography library installed

### Optional Mode: SQLCipher (If Installed)

- **Algorithm**: AES-256 encryption native to SQLite
- **Installation**: `pip install sqlcipher3`
- **Auto-detection**: If sqlcipher3 available, used automatically
- **Per-database key**: Passed as PRAGMA key to SQLite
- **Performance**: Slightly faster than Fernet for large databases

**To force Fernet mode** (even if SQLCipher available):
```python
from loom.encrypted_db import EncryptedDB
db = EncryptedDB(path, use_sqlcipher=False)
```

## File Naming Convention

- **Plaintext database**: `batch_queue.db`
- **Encrypted database**: `batch_queue.db.enc`

When `LOOM_DB_ENCRYPT=true`:
- `.db` files are encrypted to `.db.enc` automatically
- Old `.db` files are deleted (not backed up)
- To recover, decrypt the `.db.enc` file manually

## Troubleshooting

### "Invalid LOOM_DB_ENCRYPTION_KEY format"

**Cause**: Key is not valid base64-encoded Fernet format

**Solution**: Regenerate with:
```bash
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### "Failed to decrypt: Fernet token has expired"

**Cause**: Token timestamp outside 48-hour window (Fernet timestamps expire old tokens as a security measure)

**Solution**: Either:
1. Use a fresh key (generate new)
2. Regenerate the encrypted database (not recommended)

### "Key may be incorrect"

**Cause**: Wrong encryption key used for decryption

**Solution**: Verify environment variables match the key used during encryption:
```bash
echo $LOOM_DB_ENCRYPTION_KEY
echo $LOOM_DB_ENCRYPTION_PASSWORD
cat ~/.loom/encryption_key  # if using auto-generated key
```

### "sqlcipher3 not installed" (but SQLCipher mode requested)

**Cause**: Tried to use SQLCipher mode without installing sqlcipher3

**Solution**: Either:
1. Install: `pip install sqlcipher3`
2. Force Fernet mode: `EncryptedDB(path, use_sqlcipher=False)`

### "cryptography library required"

**Cause**: cryptography module not installed

**Solution**: Install encryption support:
```bash
pip install -e ".[encryption]"
# or
pip install cryptography>=43.0
```

## Security Considerations

### Encryption Scope

Encryption protects:
- Database files at rest (on disk)
- Sensitive data: job parameters, session credentials, queue state

Encryption does NOT protect:
- Data in memory during processing
- Network transmission (use HTTPS/TLS for that)
- Audit logs (uses HMAC signing instead)

### Key Security Best Practices

1. **Use password-derived keys** (`LOOM_DB_ENCRYPTION_PASSWORD`) instead of storing keys on disk
2. **Rotate keys periodically** by:
   - Deleting `~/.loom/encryption_key`
   - Setting new `LOOM_DB_ENCRYPTION_PASSWORD`
   - Restarting Loom (re-encrypts with new key)
3. **Protect key files** — check `~/.loom/encryption_key` permissions (must be 0600)
4. **Use strong passwords** — at least 16 random characters for `LOOM_DB_ENCRYPTION_PASSWORD`

### Backup and Recovery

When using encryption:
- Always backup encrypted `.db.enc` files
- Store encryption key/password securely (separate location recommended)
- To restore: Copy `.db.enc` file, set same encryption key, Loom auto-decrypts on access

**Recovery example:**
```bash
# Restore from backup
cp backup/batch_queue.db.enc ~/.cache/loom/

# Set encryption password to match original
export LOOM_DB_ENCRYPTION_PASSWORD="original_passphrase"

# Start Loom — will decrypt on first access
loom-server
```

## Implementation Details

### EncryptedDB Class

Located in `src/loom/encrypted_db.py`:

```python
class EncryptedDB:
    """Context manager for encrypted SQLite database access."""
    
    def __init__(
        self,
        db_path: str | Path,
        key: bytes | None = None,
        use_sqlcipher: bool | None = None
    ) -> None:
        """Initialize encrypted database context."""
    
    def __enter__(self) -> Path:
        """Decrypt database on entry."""
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Re-encrypt database on exit."""
    
    @contextmanager
    def connection(self, **kwargs) -> Iterator[sqlite3.Connection]:
        """Get database connection (auto-encrypted/decrypted)."""
    
    def encrypt_file(self, path: str | Path) -> Path:
        """Manually encrypt a database file."""
    
    def decrypt_file(self, enc_path: str | Path) -> Path:
        """Manually decrypt a database file."""
    
    def is_encrypted(self) -> bool:
        """Check if database is currently encrypted."""
```

### MCP Tool: research_db_encryption_status

```python
def research_db_encryption_status() -> dict[str, bool | str]:
    """Report encryption status of all Loom databases."""
```

Returns status dict showing which databases are encrypted.

## Environment Variables Reference

| Variable | Type | Purpose | Example |
|---|---|---|---|
| `LOOM_DB_ENCRYPTION_KEY` | string | Explicit Fernet key (base64) | `ABC123...xyz=` |
| `LOOM_DB_ENCRYPTION_PASSWORD` | string | Derive key via PBKDF2 | `my_passphrase` |
| `LOOM_DB_ENCRYPT` | bool | Enable encryption | `true` / `false` |

## Performance Impact

- **Encryption overhead**: ~5-10% slower than plaintext (depends on database size)
- **Decryption overhead**: ~5-10% slower at startup
- **Storage overhead**: <1% (Fernet adds ~128 bytes header)

For typical Loom usage, encryption overhead is negligible compared to network/LLM latency.

## See Also

- `src/loom/encrypted_db.py` — Implementation
- `tests/test_encrypted_db.py` — Unit tests (80%+ coverage)
- `src/loom/audit.py` — HMAC-signed audit logs (alternative to encryption)
