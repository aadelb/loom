"""research_massdns_resolve — High-performance DNS resolver for bulk domain resolution."""

from __future__ import annotations

import asyncio
import logging
import os
import shutil
import subprocess
import tempfile
from typing import Any

from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger("loom.tools.massdns_backend")


class MassDNSResolveParams(BaseModel):
    """Parameters for research_massdns_resolve tool."""

    domains: list[str] = Field(
        ..., description="List of domain names to resolve (max 10,000)"
    )
    resolver_file: str = Field(
        default="/tmp/resolvers.txt",
        description="Path to file containing public DNS resolver IPs (one per line)",
    )
    timeout: int = Field(
        default=60,
        ge=10,
        le=300,
        description="Timeout in seconds for the entire operation",
    )
    record_type: str = Field(
        default="A",
        description="DNS record type to query (A, AAAA, MX, CNAME, TXT, SOA, etc.)",
    )
    output_format: str = Field(
        default="simple",
        description="Output format style (simple, full, json)",
    )

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("domains")
    @classmethod
    def validate_domains(cls, v: list[str]) -> list[str]:
        """Validate domain list."""
        if not v:
            raise ValueError("domains list cannot be empty")
        if len(v) > 10000:
            raise ValueError("domains list exceeds max (10,000 items)")
        validated = []
        for domain in v:
            domain = domain.strip().lower()
            if not domain:
                raise ValueError("domain cannot be empty")
            if len(domain) > 255:
                raise ValueError(f"domain exceeds max length: {domain}")
            if " " in domain:
                raise ValueError(f"domain contains spaces: {domain}")
            validated.append(domain)
        return validated

    @field_validator("resolver_file")
    @classmethod
    def validate_resolver_file(cls, v: str) -> str:
        """Validate resolver file path."""
        v = v.strip()
        if not v:
            raise ValueError("resolver_file cannot be empty")
        if len(v) > 512:
            raise ValueError("resolver_file path exceeds max length")
        return v

    @field_validator("record_type")
    @classmethod
    def validate_record_type(cls, v: str) -> str:
        """Validate DNS record type."""
        valid_types = {"A", "AAAA", "MX", "CNAME", "TXT", "SOA", "NS", "PTR", "SRV"}
        v = v.upper().strip()
        if v not in valid_types:
            raise ValueError(f"invalid record type: {v}")
        return v


class MassDNSResult(BaseModel):
    """Result from a massdns resolution operation."""

    resolved: int = 0
    failed: int = 0
    total: int = 0
    results: list[dict[str, Any]] = Field(default_factory=list)
    error: str | None = None
    elapsed_ms: int = 0


async def research_massdns_resolve(
    domains: list[str],
    resolver_file: str = "/tmp/resolvers.txt",
    timeout: int = 60,
    record_type: str = "A",
    output_format: str = "simple",
) -> dict[str, Any]:
    """Resolve domains in bulk using massdns high-performance resolver.

    massdns is capable of resolving millions of domains per second using
    optimized UDP requests and parallel resolution. Requires a file of
    public DNS resolver IP addresses.

    Args:
        domains: List of domain names to resolve (max 10,000)
        resolver_file: Path to file with DNS resolver IPs (one per line)
        timeout: Timeout in seconds (10-300)
        record_type: DNS record type to query (A, AAAA, MX, CNAME, etc.)
        output_format: Output format style (simple, full, json)

    Returns:
        Dict with resolved count, failed count, results list, and error status.

    Example:
        >>> result = await research_massdns_resolve(
        ...     ["example.com", "google.com"],
        ...     resolver_file="/tmp/public_resolvers.txt"
        ... )
        >>> print(result["resolved"])
    """
    # Validate input
    params = MassDNSResolveParams(
        domains=domains,
        resolver_file=resolver_file,
        timeout=timeout,
        record_type=record_type,
        output_format=output_format,
    )

    # Check if massdns is available
    massdns_path = shutil.which("massdns")
    if not massdns_path:
        return {
            "error": "massdns not found in PATH. Install from: https://github.com/blechschmidt/massdns",
            "resolved": 0,
            "failed": 0,
            "total": 0,
            "results": [],
        }

    result = MassDNSResult(total=len(params.domains))

    try:
        # Check if resolver file exists
        if not os.path.isfile(params.resolver_file):
            logger.warning(f"Resolver file not found: {params.resolver_file}")
            result.error = f"Resolver file not found: {params.resolver_file}"
            return result.model_dump()

        # Create temporary domain input file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, prefix="massdns_"
        ) as domain_file:
            domain_file.write("\n".join(params.domains))
            domain_file.flush()
            domain_file_path = domain_file.name

        # Create temporary output file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, prefix="massdns_out_"
        ) as output_file:
            output_file_path = output_file.name

        try:
            # Build massdns command
            cmd = [
                massdns_path,
                "-r",
                params.resolver_file,
                "-t",
                params.record_type,
                "-o",
                "S",  # Simple format output
                "-w",
                output_file_path,
                domain_file_path,
            ]

            proc_result = await asyncio.to_thread(
                subprocess.run,
                cmd,
                timeout=params.timeout,
                capture_output=True,
                text=True,
                check=False,
            )

            if proc_result.returncode != 0 and proc_result.returncode != 1:
                # Return code 1 may indicate some domains didn't resolve (not necessarily an error)
                result.error = f"massdns failed: {proc_result.stderr[:200]}"
                logger.warning(f"massdns execution warning: {proc_result.stderr[:200]}")

            # Parse output file
            if os.path.isfile(output_file_path):
                _parse_massdns_output(output_file_path, result)

        finally:
            # Clean up temporary files
            try:
                os.unlink(domain_file_path)
                os.unlink(output_file_path)
            except OSError:
                pass

    except subprocess.TimeoutExpired:
        result.error = f"massdns operation timed out after {params.timeout}s"
        logger.error(f"massdns timeout: {params.timeout}s")
    except Exception as e:
        result.error = f"massdns resolution failed: {str(e)[:200]}"
        logger.error(f"research_massdns_resolve error: {e}")

    return result.model_dump()


def _parse_massdns_output(output_file: str, result: MassDNSResult) -> None:
    """Parse massdns output file and populate results.

    massdns output format:
    domain. type class TTL rdata1 rdata2 ...

    Example:
    example.com. A 1 IN 300 93.184.216.34
    """
    try:
        with open(output_file, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith(";"):
                    continue

                parts = line.split()
                if len(parts) < 5:
                    continue

                domain = parts[0].rstrip(".")
                record_type = parts[1]
                rdata = " ".join(parts[4:]) if len(parts) > 4 else ""

                if rdata:
                    result.resolved += 1
                    result.results.append({
                        "domain": domain,
                        "type": record_type,
                        "value": rdata,
                    })
                else:
                    result.failed += 1

    except Exception as e:
        logger.error(f"Error parsing massdns output: {e}")
