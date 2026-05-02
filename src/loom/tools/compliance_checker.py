"""research_compliance_check & research_pii_scan — Regulatory compliance validation."""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger("loom.tools.compliance_checker")

# PII patterns (email, phone, SSN, credit_card, IP)
_PII = {
    "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
    "phone": r"\b(?:\+1|1)?[-.\s]?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b",
    "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
    "credit_card": r"\b(?:\d{4}[-\s]?){3}\d{4}\b",
    "ip_address": r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
}


def research_compliance_check(
    text: str, frameworks: list[str] | None = None
) -> dict[str, Any]:
    """Check text against compliance frameworks (EU AI Act, GDPR, OWASP, NIST, HIPAA)."""
    if not text or len(text) > 50000:
        return {
            "error": "Invalid text",
            "frameworks_checked": [],
            "violations": [],
            "compliant": True,
            "risk_score": 0,
        }

    if frameworks is None:
        frameworks = ["eu_ai_act", "gdpr", "owasp", "nist", "hipaa"]
    valid = {"eu_ai_act", "gdpr", "owasp", "nist", "hipaa"}
    frameworks = [f.lower() for f in frameworks if f.lower() in valid]

    logger.info("compliance_check frameworks=%s", frameworks)
    text_lower, violations = text.lower(), []
    pii_count = sum(len(re.findall(p, text, re.IGNORECASE)) for p in _PII.values())

    for fw in frameworks:
        if fw == "eu_ai_act":
            if pii_count > 0:
                violations.append(
                    {
                        "framework": "eu_ai_act",
                        "severity": "critical",
                        "description": "PII exposure",
                        "check_type": "pii_exposure",
                    }
                )
            if any(k in text_lower for k in ["exploit", "bypass", "malware"]):
                violations.append(
                    {
                        "framework": "eu_ai_act",
                        "severity": "high",
                        "description": "Unsafe recommendation",
                        "check_type": "unsafe",
                    }
                )
            if not any(
                k in text_lower for k in ["disclaimer", "limitation", "use at own risk"]
            ):
                violations.append(
                    {
                        "framework": "eu_ai_act",
                        "severity": "medium",
                        "description": "Missing disclaimer",
                        "check_type": "missing_disclaimer",
                    }
                )
        elif fw == "gdpr":
            if pii_count > 0:
                violations.append(
                    {
                        "framework": "gdpr",
                        "severity": "critical",
                        "description": "PII exposure",
                        "check_type": "pii_exposure",
                    }
                )
            if not any(k in text_lower for k in ["consent", "agreed", "opt-in"]):
                violations.append(
                    {
                        "framework": "gdpr",
                        "severity": "medium",
                        "description": "No consent",
                        "check_type": "consent_missing",
                    }
                )
            if not any(k in text_lower for k in ["retention", "delete", "purge"]):
                violations.append(
                    {
                        "framework": "gdpr",
                        "severity": "medium",
                        "description": "Unclear retention",
                        "check_type": "retention_missing",
                    }
                )
        elif fw == "owasp":
            if re.search(
                r"api[_-]?key\s*[=:]\s*['\"]|password\s*[=:]\s*['\"]",
                text,
                re.IGNORECASE,
            ):
                violations.append(
                    {
                        "framework": "owasp",
                        "severity": "critical",
                        "description": "Hardcoded secrets",
                        "check_type": "hardcoded",
                    }
                )
            if any(k in text_lower for k in ["sql", "where 1=1", "' or '"]):
                violations.append(
                    {
                        "framework": "owasp",
                        "severity": "critical",
                        "description": "SQL injection hint",
                        "check_type": "sql_injection",
                    }
                )
        elif fw == "nist":
            if not any(k in text_lower for k in ["encrypt", "tls", "ssl", "aes"]):
                violations.append(
                    {
                        "framework": "nist",
                        "severity": "medium",
                        "description": "Missing encryption",
                        "check_type": "encryption",
                    }
                )
            if not any(k in text_lower for k in ["audit", "logging", "log"]):
                violations.append(
                    {
                        "framework": "nist",
                        "severity": "medium",
                        "description": "No audit trail",
                        "check_type": "audit",
                    }
                )
        elif fw == "hipaa":
            has_phi = any(k in text_lower for k in ["patient", "medical", "diagnosis"])
            if has_phi and pii_count > 0:
                violations.append(
                    {
                        "framework": "hipaa",
                        "severity": "critical",
                        "description": "PHI + PII exposure",
                        "check_type": "phi_pii",
                    }
                )

    return {
        "frameworks_checked": frameworks,
        "violations": violations,
        "compliant": len(violations) == 0,
        "risk_score": min(10, len(violations) + pii_count),
        "total_violations": len(violations),
    }


def research_pii_scan(text: str) -> dict[str, Any]:
    """Scan for PII: email, phone, SSN, credit card, IP address."""
    if not text or len(text) > 50000:
        return {
            "error": "Invalid text",
            "pii_found": [],
            "total_pii": 0,
            "risk_level": "low",
            "recommendation": "Invalid",
        }

    logger.info("pii_scan len=%d", len(text))
    pii_found = []

    for pii_type, pattern in _PII.items():
        for match in re.finditer(pattern, text, re.IGNORECASE):
            start = max(0, match.start() - 20)
            end = min(len(text), match.end() + 20)
            pii_found.append(
                {
                    "type": pii_type,
                    "value_masked": _mask(match.group(), pii_type),
                    "position": match.start(),
                    "context": text[start:end].strip(),
                }
            )

    # Deduplicate
    unique = {(p["type"], p["value_masked"]): p for p in pii_found}
    pii_list = list(unique.values())
    critical = sum(1 for p in pii_list if p["type"] in ["ssn", "credit_card"])
    sensitive = sum(1 for p in pii_list if p["type"] in ["email", "phone"])

    risk = (
        "high"
        if (critical >= 2 or (critical > 0 and sensitive > 2))
        else ("medium" if (critical > 0 or sensitive >= 3) else "low")
    )
    rec = (
        "Critical: Remove before sharing."
        if risk == "high"
        else ("Caution: Review PII." if risk == "medium" else "Info: OK.")
    )

    return {
        "pii_found": pii_list,
        "total_pii": len(pii_list),
        "pii_summary": {"critical": critical, "sensitive": sensitive},
        "risk_level": risk,
        "recommendation": rec,
    }


def _mask(value: str, pii_type: str) -> str:
    """Mask PII for safe display."""
    if pii_type == "email":
        if "@" not in value:
            return "***@***"
        parts = value.split("@")
        return f"{parts[0][:2]}***@***{parts[1][-3:]}"

    return {
        "phone": lambda: value[:3] + "***" + value[-4:] if len(value) >= 10 else "***",
        "ssn": lambda: "***-**-" + value[-4:],
        "credit_card": lambda: "****-****-****-" + value[-4:],
        "ip_address": lambda: (
            value.split(".")[0] + ".***.**.*" if "." in value else "***"
        ),
    }.get(pii_type, lambda: value[0] + "***" if value else "***")()
