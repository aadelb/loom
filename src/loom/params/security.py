"""Pydantic parameter models for security tools."""

"""Pydantic v2 parameter models for all MCP tool arguments.

Each tool has a dedicated model with field validators for URLs, headers,
proxies, etc. All models ignore extra fields and use strict mode.
"""

from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from loom.config import CONFIG
from loom.validators import filter_headers, validate_js_script, validate_local_file_path, validate_url

# Default Accept-Language header sourced from config
_DEFAULT_ACCEPT_LANG = CONFIG.get("DEFAULT_ACCEPT_LANGUAGE", "en-US,en;q=0.9,ar;q=0.8")



__all__ = [
    "BreachCheckParams",
    "CVEDetailParams",
    "CVELookupParams",
    "CensysHostParams",
    "CensysSearchParams",
    "CertAnalyzeParams",
    "DNSLookupParams",
    "DefiSecurityAuditParams",
    "ModelIntegrityParams",
    "ModelVulnerabilityProfileParams",
    "NmapScanParams",
    "PackageAuditParams",
    "PasswordCheckParams",
    "SecurityHeadersParams",
    "ShodanHostParams",
    "ShodanSearchParams",
    "URLhausSearchParams",
    "WhoisParams",
]


class BreachCheckParams(BaseModel):
    """Parameters for research_breach_check tool."""

    email: str

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", v):
            raise ValueError("email format invalid")
        return v




class CVEDetailParams(BaseModel):
    """Parameters for research_cve_detail tool."""

    cve_id: str = Field(
        description="CVE ID in format CVE-YYYY-NNNNN+",
        pattern=r"^CVE-\d{4}-\d{5,}$",
    )

    model_config = {"extra": "ignore", "strict": True}




class CVELookupParams(BaseModel):
    """Parameters for research_cve_lookup tool."""

    query: str = Field(
        description="Keyword or phrase to search CVE database",
        max_length=256,
    )
    max_results: int = Field(
        default=10,
        description="Max number of results (1-100)",
        ge=1,
        le=100,
        alias="limit",
    )

    model_config = {"extra": "ignore", "strict": True, "populate_by_name": True}

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("query cannot be empty")
        return v.strip()




class CensysHostParams(BaseModel):
    """Parameters for research_censys_host tool."""

    ip: str = Field(
        ...,
        description="IPv4 or IPv6 address to look up",
        min_length=3,
        max_length=45,
    )

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("ip")
    @classmethod
    def validate_ip(cls, v: str) -> str:
        """IP must be a valid IPv4 or IPv6 address."""
        v = v.strip()
        if not v:
            raise ValueError("ip cannot be empty")
        # Basic validation: IPv4 has dots, IPv6 has colons
        if ":" not in v and "." not in v:
            raise ValueError("ip must be IPv4 (with dots) or IPv6 (with colons)")
        return v




class CensysSearchParams(BaseModel):
    """Parameters for research_censys_search tool."""

    query: str = Field(
        ...,
        description="Censys query string (e.g., 'services.service_name: HTTP AND location.country: US')",
        min_length=1,
        max_length=1000,
    )
    max_results: int = Field(
        10,
        description="Maximum results to return (1-1000)",
        ge=1,
        le=1000,
    )

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        """Query must be non-empty and reasonably short."""
        v = v.strip()
        if not v:
            raise ValueError("query cannot be empty")
        return v

    @field_validator("max_results")
    @classmethod
    def validate_max_results(cls, v: int) -> int:
        """max_results must be between 1 and 1000."""
        if v < 1 or v > 1000:
            raise ValueError("max_results must be 1-1000")
        return v




class CertAnalyzeParams(BaseModel):
    """Parameters for research_cert_analyze tool."""

    domain: str

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, v: str) -> str:
        v = v.strip().lower()
        if not re.match(r"^[a-z0-9]([a-z0-9-]*\.)+[a-z]{2,}$", v):
            raise ValueError("domain format invalid")
        return v




class DNSLookupParams(BaseModel):
    """Parameters for research_dns_lookup tool."""

    domain: str
    record_types: list[str] | None = None

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, v: str) -> str:
        v = v.strip().lower()
        if not re.match(r"^[a-z0-9]([a-z0-9-]*\.)+[a-z]{2,}$", v):
            raise ValueError("domain format invalid")
        return v

    @field_validator("record_types")
    @classmethod
    def validate_record_types(cls, v: list[str] | None) -> list[str] | None:
        if v:
            valid_types = {"A", "AAAA", "MX", "NS", "TXT", "CNAME", "SOA", "SRV"}
            for rt in v:
                if rt.upper() not in valid_types:
                    raise ValueError(f"invalid record type: {rt}")
            return [rt.upper() for rt in v]
        return v




class DefiSecurityAuditParams(BaseModel):
    """Parameters for research_defi_security_audit tool."""

    contract_address: str

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("contract_address")
    @classmethod
    def validate_contract_address(cls, v: str) -> str:
        v = v.strip()
        if not v.startswith("0x") or len(v) != 42:
            raise ValueError("contract_address must be 0x + 40 hex chars")
        try:
            int(v, 16)
        except ValueError:
            raise ValueError("contract_address must be valid hex")
        return v




class ModelIntegrityParams(BaseModel):
    """Parameters for research_model_integrity tool."""

    model_name: str
    source: Literal["huggingface", "pytorch", "civitai"] = "huggingface"
    checks: list[str] | None = None

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("model_name")
    @classmethod
    def validate_model_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("model_name must be non-empty")
        if len(v) > 500:
            raise ValueError("model_name max 500 characters")
        return v.strip()

    @field_validator("checks")
    @classmethod
    def validate_checks(cls, v: list[str] | None) -> list[str] | None:
        if v is not None:
            valid_checks = {
                "hash_verify", "size_anomaly", "metadata_tampering",
                "backdoor_indicators", "provenance"
            }
            for check in v:
                if check not in valid_checks:
                    raise ValueError(f"invalid check: {check}")
            if len(v) > 5:
                raise ValueError("checks list max 5 items")
        return v




class ModelVulnerabilityProfileParams(BaseModel):
    model_config = {"extra": "ignore", "strict": True}
    model: str = "auto"




class NmapScanParams(BaseModel):
    """Parameters for research_nmap_scan tool."""

    domain: str = Field(..., alias="target")
    scan_type: Literal["syn", "connect", "ping", "os"] = "syn"
    ports: str | None = None

    model_config = {"extra": "ignore", "strict": True, "populate_by_name": True}

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, v: str) -> str:
        v = v.strip()
        if not re.match(r"^[a-z0-9\-.:/_]+$", v, re.IGNORECASE):
            raise ValueError("domain format invalid")
        return v

    @field_validator("ports")
    @classmethod
    def validate_ports(cls, v: str | None) -> str | None:
        if v:
            v = v.strip()
            if not re.match(r"^[\d,\-\s]+$", v):
                raise ValueError("ports format invalid (use: 80,443 or 1-1000)")
        return v




class PackageAuditParams(BaseModel):
    """Parameters for research_package_audit tool."""

    package_name: str
    ecosystem: Literal["pypi", "npm", "cargo"] = "pypi"
    depth: int = 2

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("package_name")
    @classmethod
    def validate_package_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("package_name must be non-empty")
        if len(v) > 200:
            raise ValueError("package_name max 200 characters")
        return v.strip()

    @field_validator("depth")
    @classmethod
    def validate_depth(cls, v: int) -> int:
        if v < 1 or v > 3:
            raise ValueError("depth must be 1-3")
        return v




class PasswordCheckParams(BaseModel):
    """Parameters for research_password_check tool."""

    password: str

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not v or len(v) > 500:
            raise ValueError("password must be 1-500 characters")
        return v




class SecurityHeadersParams(BaseModel):
    """Parameters for research_security_headers tool."""

    url: str

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("url", mode="before")
    @classmethod
    def validate_url_field(cls, v: str) -> str:
        return validate_url(v)




class ShodanHostParams(BaseModel):
    """Parameters for research_shodan_host tool."""

    ip: str

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("ip")
    @classmethod
    def validate_ip(cls, v: str) -> str:
        v = v.strip()
        # Basic IPv4 validation
        if not re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", v):
            raise ValueError("ip must be valid IPv4 address")
        # Validate each octet is 0-255
        octets = v.split(".")
        for octet in octets:
            num = int(octet)
            if num < 0 or num > 255:
                raise ValueError("ip octets must be 0-255")
        return v




class ShodanSearchParams(BaseModel):
    """Parameters for research_shodan_search tool."""

    query: str
    max_results: int = 10

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("query cannot be empty")
        if len(v) > 500:
            raise ValueError("query too long (max 500 chars)")
        return v

    @field_validator("max_results")
    @classmethod
    def validate_max_results(cls, v: int) -> int:
        if v < 1 or v > 5000:
            raise ValueError("max_results must be 1-5000")
        return v



class URLhausSearchParams(BaseModel):
    """Parameters for research_urlhaus_search tool."""

    query: str = Field(
        description="Search query",
        max_length=256,
    )
    max_results: int = Field(
        default=10,
        description="Max results (1-100)",
        ge=1,
        le=100,
        alias="limit",
    )

    model_config = {"extra": "ignore", "strict": True, "populate_by_name": True}

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("query cannot be empty")
        return v.strip()




class WhoisParams(BaseModel):
    """Parameters for research_whois tool."""

    domain: str

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, v: str) -> str:
        v = v.strip().lower()
        if not re.match(r"^[a-z0-9]([a-z0-9-]*\.)+[a-z]{2,}$", v):
            raise ValueError("domain format invalid")
        return v




