"""EU AI Act compliant audit logging for Loom MCP server.

Provides append-only JSONL audit logs with tamper-proof HMAC-SHA256 signatures.
All PII is scrubbed from audit entries before logging.

Public API:
    log_invocation()    Log a tool invocation with params, status, duration
    verify_integrity()  Verify audit log HMAC signatures and detect tampering
    export_audit()      Export audit logs for compliance reporting
"""

from __future__ import annotations

import csv
import fcntl
import hashlib
import hmac
import io
import json
import logging
import os
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from loom.pii_scrubber import scrub_dict, scrub_pii

logger = logging.getLogger("loom.audit")

# Default audit directory
DEFAULT_AUDIT_DIR = Path.home() / ".loom" / "audit"


def _get_audit_secret() -> str:
    """Get HMAC secret key from environment variable.

    Returns:
        LOOM_AUDIT_SECRET environment variable value

    Raises:
        ValueError: If LOOM_AUDIT_SECRET is not set or empty
    """
    secret = os.environ.get("LOOM_AUDIT_SECRET", "").strip()
    if not secret:
        raise ValueError(
            "LOOM_AUDIT_SECRET environment variable not set. "
            "Set a strong secret key for audit HMAC signing."
        )
    return secret


@dataclass
class AuditEntry:
    """Single audit log entry for a tool invocation."""

    client_id: str
    tool_name: str
    params_summary: dict[str, Any]
    timestamp: str  # ISO UTC format
    duration_ms: int
    status: str  # "success", "error", "timeout", etc.
    signature: str = ""  # HMAC-SHA256, computed later

    def to_json(self, include_signature: bool = True) -> str:
        """Serialize to JSON string.

        Args:
            include_signature: Include signature field in output (for verification)

        Returns:
            JSON string representation
        """
        entry_dict = asdict(self)
        if not include_signature:
            entry_dict.pop("signature", None)
        return json.dumps(entry_dict, separators=(",", ":"), sort_keys=True)

    def compute_signature(self, secret: str) -> str:
        """Compute HMAC-SHA256 signature of entry without signature field.

        Args:
            secret: HMAC secret key

        Returns:
            32-character hex HMAC-SHA256 signature
        """
        json_str = self.to_json(include_signature=False)
        sig = hmac.new(
            secret.encode(),
            json_str.encode(),
            hashlib.sha256
        ).hexdigest()
        return sig


def _redact_params(params: dict[str, Any]) -> dict[str, Any]:
    """Redact sensitive parameters containing key/token/password/secret.

    Also applies PII scrubbing to remove email addresses, phone numbers, IPs, etc.

    Args:
        params: Original parameters dict

    Returns:
        New dict with sensitive values replaced with "***REDACTED***"
        and PII scrubbed from all string values
    """
    sensitive_keys = {"key", "token", "password", "secret"}
    redacted = {}

    for key, value in params.items():
        key_lower = key.lower()
        if any(sensitive in key_lower for sensitive in sensitive_keys):
            redacted[key] = "***REDACTED***"
        else:
            redacted[key] = value

    # Apply PII scrubbing to all string values
    return scrub_dict(redacted)


def log_invocation(
    client_id: str,
    tool_name: str,
    params: dict[str, Any],
    result_summary: str,
    duration_ms: int,
    status: str,
    audit_dir: Path = DEFAULT_AUDIT_DIR,
) -> str:
    """Log a tool invocation to append-only audit file.

    Creates daily JSONL files (YYYY-MM-DD.jsonl) in audit directory.
    Each line is a complete JSON entry with HMAC-SHA256 signature.
    All PII is scrubbed before logging.

    Args:
        client_id: Client identifier (e.g., session ID, user ID)
        tool_name: Name of tool invoked
        params: Input parameters (will be redacted for sensitive values and scrubbed for PII)
        result_summary: Summary of result (not full result to save space)
        duration_ms: Execution duration in milliseconds
        status: Status code (e.g., "success", "error", "timeout")
        audit_dir: Directory to store audit logs (default: ~/.loom/audit)

    Returns:
        HMAC signature of the logged entry (64-char hex string)

    Raises:
        OSError: If unable to write audit file
        ValueError: If LOOM_AUDIT_SECRET is not set
    """
    # Get HMAC secret
    try:
        secret = _get_audit_secret()
    except ValueError as e:
        logger.error("Cannot sign audit entry: %s", str(e))
        raise

    # Ensure audit directory exists with secure permissions (0o700)
    audit_dir.mkdir(parents=True, exist_ok=True, mode=0o700)

    # Get current date in UTC
    now_utc = datetime.now(UTC)
    iso_timestamp = now_utc.isoformat()
    date_str = now_utc.strftime("%Y-%m-%d")

    # Create audit entry with redacted and scrubbed params
    redacted_params = _redact_params(params)
    scrubbed_result_summary = scrub_pii(result_summary)
    scrubbed_client_id = scrub_pii(client_id)

    entry = AuditEntry(
        client_id=scrubbed_client_id,
        tool_name=tool_name,
        params_summary=redacted_params,
        timestamp=iso_timestamp,
        duration_ms=duration_ms,
        status=status,
    )

    # Compute HMAC signature
    signature = entry.compute_signature(secret)
    entry.signature = signature

    # Append to daily log file
    log_file = audit_dir / f"{date_str}.jsonl"
    json_line = entry.to_json(include_signature=True)

    try:
        # Append-only mode, create if not exists
        with open(log_file, "a") as f:
            # Acquire exclusive lock for safe concurrent writes
            fcntl.flock(f, fcntl.LOCK_EX)
            try:
                f.write(json_line + "\n")
            finally:
                # Release lock
                fcntl.flock(f, fcntl.LOCK_UN)

        # Set secure file permissions (0o600 = read/write for owner only)
        os.chmod(log_file, 0o600)

        logger.debug("audit_logged tool=%s client=%s signature=%s status=%s", tool_name, scrubbed_client_id, signature, status)
    except OSError as e:
        logger.error("audit_write_failed file=%s error=%s", str(log_file), str(e))
        raise

    return signature


@dataclass
class VerifyResult:
    """Result of audit log verification."""

    entries: int = 0  # Total entries
    valid: int = 0  # Valid signatures
    invalid: int = 0  # Invalid signatures
    tampered: bool = False  # Any tampering detected


def verify_integrity(log_file: Path, secret: str | None = None) -> VerifyResult:
    """Verify integrity of audit log file using HMAC signatures.

    Reads JSONL file and validates HMAC-SHA256 signatures for each entry.
    Detects tampering (signature mismatch) and corruption.

    Args:
        log_file: Path to audit log file (JSONL format)
        secret: HMAC secret key. If None, uses LOOM_AUDIT_SECRET env var.

    Returns:
        VerifyResult with validation counts and tamper flag

    Raises:
        FileNotFoundError: If log file does not exist
        ValueError: If secret is not provided and LOOM_AUDIT_SECRET not set
    """
    result = VerifyResult()

    if not log_file.exists():
        return result

    if log_file.stat().st_size == 0:
        return result

    # Get HMAC secret
    if secret is None:
        try:
            secret = _get_audit_secret()
        except ValueError:
            logger.warning("Cannot verify audit log: LOOM_AUDIT_SECRET not set")
            return result

    try:
        with open(log_file) as f:
            for line_num, line in enumerate(f, start=1):
                line = line.rstrip("\n")
                if not line:
                    continue

                try:
                    entry_dict = json.loads(line)
                    result.entries += 1

                    # Extract and remove signature from entry
                    stored_sig = entry_dict.pop("signature", "")
                    if not stored_sig:
                        result.invalid += 1
                        result.tampered = True
                        logger.warning("audit_missing_signature file=%s line=%d", str(log_file), line_num)
                        continue

                    # Recompute signature on entry without signature field
                    json_str = json.dumps(entry_dict, separators=(",", ":"), sort_keys=True)
                    computed_sig = hmac.new(
                        secret.encode(),
                        json_str.encode(),
                        hashlib.sha256
                    ).hexdigest()

                    if computed_sig != stored_sig:
                        result.invalid += 1
                        result.tampered = True
                        logger.warning(
                            "audit_signature_mismatch file=%s line=%d stored=%s computed=%s",
                            str(log_file),
                            line_num,
                            stored_sig,
                            computed_sig,
                        )
                    else:
                        result.valid += 1

                except json.JSONDecodeError as e:
                    result.invalid += 1
                    result.tampered = True
                    logger.warning("audit_json_error file=%s line=%d error=%s", str(log_file), line_num, str(e))
    except OSError as e:
        logger.error("audit_read_failed file=%s error=%s", str(log_file), str(e))
        raise

    return result


def export_audit(
    start_date: str | None = None,
    end_date: str | None = None,
    format: str = "json",
    audit_dir: Path = DEFAULT_AUDIT_DIR,
    secret: str | None = None,
) -> dict[str, Any]:
    """Export audit logs for compliance reporting.

    Reads and validates audit logs in specified date range.
    Each entry includes verification status.

    Supports two export formats:
    - "json": Returns list of audit entries as JSON array
    - "csv": Returns CSV string with headers

    Args:
        start_date: Start date (YYYY-MM-DD) or None for earliest
        end_date: End date (YYYY-MM-DD) or None for latest
        format: Export format, "json" or "csv" (default: "json")
        audit_dir: Directory containing audit logs (default: ~/.loom/audit)
        secret: HMAC secret key for verification. If None, uses LOOM_AUDIT_SECRET.

    Returns:
        Dict with keys:
        - format: Export format used
        - data: Exported data (JSON array or CSV string)
        - count: Number of entries exported

    Raises:
        ValueError: If format is invalid
        OSError: If unable to read audit directory
    """
    if format not in ("json", "csv"):
        raise ValueError(f'format must be "json" or "csv", got: {format}')

    if not audit_dir.exists():
        if format == "csv":
            return {"format": "csv", "data": "", "count": 0}
        return {"format": "json", "data": [], "count": 0}

    # Get HMAC secret for verification
    if secret is None:
        try:
            secret = _get_audit_secret()
        except ValueError:
            logger.warning("Cannot verify signatures: LOOM_AUDIT_SECRET not set")
            secret = None

    entries = []

    # Find all JSONL files in date range
    for log_file in sorted(audit_dir.glob("*.jsonl")):
        # Extract date from filename (YYYY-MM-DD.jsonl)
        date_str = log_file.stem

        if start_date and date_str < start_date:
            continue
        if end_date and date_str > end_date:
            continue

        # Read and validate entries from this file
        try:
            with open(log_file) as f:
                for line in f:
                    line = line.rstrip("\n")
                    if not line:
                        continue

                    try:
                        entry_dict = json.loads(line)
                        stored_sig = entry_dict.get("signature", "")

                        # Verify signature if secret is available
                        verified = False
                        if secret and stored_sig:
                            entry_copy = dict(entry_dict)
                            entry_copy.pop("signature", None)
                            json_str = json.dumps(
                                entry_copy, separators=(",", ":"), sort_keys=True
                            )
                            computed_sig = hmac.new(
                                secret.encode(),
                                json_str.encode(),
                                hashlib.sha256
                            ).hexdigest()
                            verified = computed_sig == stored_sig

                        # Add verification status
                        entry_dict["_verified"] = verified
                        entries.append(entry_dict)

                    except json.JSONDecodeError:
                        pass
        except OSError:
            pass

    # Handle empty export
    if not entries:
        if format == "csv":
            return {"format": "csv", "data": "", "count": 0}
        return {"format": "json", "data": [], "count": 0}

    # Format export
    if format == "csv":
        # Convert entries to CSV
        output = io.StringIO()
        fieldnames = list(entries[0].keys())
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()

        for entry in entries:
            # Convert non-string values to strings for CSV
            csv_row = {}
            for key, value in entry.items():
                if isinstance(value, dict):
                    csv_row[key] = json.dumps(value)
                else:
                    csv_row[key] = str(value)
            writer.writerow(csv_row)

        return {
            "format": "csv",
            "data": output.getvalue(),
            "count": len(entries),
        }

    # JSON format (default)
    return {
        "format": "json",
        "data": entries,
        "count": len(entries),
    }
