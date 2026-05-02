"""research_compliance_check & research_pii_scan — Regulatory compliance validation."""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger("loom.tools.compliance_checker")

# PII detection patterns
_PII_PATTERNS = {
    "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
    "phone": r"\b(?:\+1|1)?[-.\s]?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b",
    "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
    "credit_card": r"\b(?:\d{4}[-\s]?){3}\d{4}\b",
    "ip_address": r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
    "name": r"\b(?:John|Jane|Robert|Michael|Patricia|Mary|James|David|William|Richard|Joseph|Thomas|Charles|Christopher|Daniel|Matthew|Anthony|Donald|Mark|Lisa|Barbara|Jennifer|Jessica|Sarah|Susan|Karen|Nancy|Deborah|Sandra|Ashley|Donna|Emily|Carol|Michelle|Amanda|Melissa|Debra|Stephanie|Rebecca|Sharon|Laura|Cynthia|Kathleen|Amy|Angela|Shirley|Anna|Brenda|Pamela|Emma|Nicole|Helen|Samantha|Katherine|Christine|Debbie|Rachel|Catherine|Carolyn|Janet|Ruth|Maria|Heather|Diane|Virginia|Julie|Joyce|Evelyn|Judith|Megan|Andrea|Cheryl|Hannah|Jacqueline|Martha|Madison|Teresa|Gloria|Ann|Sara|Kathryn|Alice|Abigail|Sophia|Judy|Denise|Marilyn|Beverly|Isabella|Theresa|Diana|Natalie|Brittany|Charlotte|Marie|Kayla|Alexis|Lori)\s+(?:Smith|Johnson|Williams|Jones|Brown|Garcia|Miller|Davis|Rodriguez|Martinez|Hernandez|Lopez|Gonzalez|Wilson|Anderson|Thomas|Taylor|Moore|Jackson|Martin|Lee|Perez|Thompson|White|Harris|Sanchez|Clark|Ramirez|Lewis|Robinson|Young|Stroh|King|Wright|Torres|Peterson|Phillips|Campbell|Parker|Edwards|Collins|Reeves|Morris|Murphy|Cook|Morgan|Peterson|Cooper|Reed|Bell|Gomez|Murray|Freeman|Wells|Webb|Simpson|Stevens|Tucker|Porter|Hunter|Hicks|Crawford|Henry|Boyd|Mason|Moreno|Kennedy|Warren|Dixon|Ramos|Reeves|Burns|Gordon|Shaw|Holmes|Rice|Robertson|Hunt|Black|Daniels|Palmer|Mills|Nicholson|Grant|Knight|Ferguson|Stone|Hawkins|Duffy|Perkins|Hudson|Spencer|Gardner|Stephens|Payne|Pierce|Berry|Matthews|Arnold|Wagner|Willis|Ray|Watkins|Olson|Carroll|Duncan|Snyder|Hart|Cunningham|Knight|Welch|Roth|Dalton|Maddox|Vaughn|Hale|Corbin|Kidd|Waller|Hester|Graves|Hathaway|Ware|Atkinson|Whitley|Mosley|Lowe|Rivas|Metz|Hicks|Prince|Riddle|Beard|Shelton|Smith|Shea|Sheridan|Shields|Shields|Shoemaker|Shore|Short|Showalter|Shropshire|Shuffleu|Shuffler|Shull|Shuman|Shure|Shutt|Shyan|Sibert|Sicard|Sickels|Sickler|Sidwell|Siebert|Siebold|Sieburgh|Siedel|Sieger|Sieh|Siegals|Siefert|Siegal|Sieger|Siehler|Sieling|Siemons|Siems|Sien|Sienal|Siennas|Sienknecht|Sierck|Sievert|Sieverts|Siever|Seward|Sewell)\b",
}

# Compliance frameworks and their violation checks
_COMPLIANCE_FRAMEWORKS = {
    "eu_ai_act": {
        "description": "EU AI Act - Regulation on AI transparency and safety",
        "checks": [
            ("pii_exposure", "Exposed personally identifiable information"),
            ("unsafe_recommendation", "Unsafe or harmful recommendations"),
            ("missing_disclaimer", "Missing risk/limitation disclaimer"),
            ("bias_indicator", "Potential bias or discrimination indicators"),
        ],
    },
    "gdpr": {
        "description": "GDPR - Data protection and privacy",
        "checks": [
            ("pii_exposure", "Exposed personally identifiable information"),
            ("data_location", "Mention of specific data storage locations"),
            ("consent_missing", "No mention of user consent"),
            ("retention_policy", "Unclear data retention policy"),
        ],
    },
    "owasp": {
        "description": "OWASP - Web application security",
        "checks": [
            ("hardcoded_secrets", "Hardcoded API keys or passwords"),
            ("sql_injection_hint", "SQL injection vulnerability hints"),
            ("xss_hint", "Cross-site scripting vulnerability hints"),
            ("auth_bypass", "Authentication bypass suggestions"),
        ],
    },
    "nist": {
        "description": "NIST - Cybersecurity framework",
        "checks": [
            ("access_control", "Incomplete access control documentation"),
            ("encryption_missing", "Missing encryption requirements"),
            ("audit_trail", "No audit trail or logging mentioned"),
            ("incident_response", "No incident response plan mentioned"),
        ],
    },
    "hipaa": {
        "description": "HIPAA - Healthcare data protection",
        "checks": [
            ("phi_exposure", "Protected health information exposed"),
            ("pii_exposure", "Patient PII exposed"),
            ("encryption_missing", "Missing encryption for PHI"),
            ("audit_control", "No audit controls mentioned"),
        ],
    },
}


def research_compliance_check(
    text: str,
    frameworks: list[str] | None = None,
) -> dict[str, Any]:
    """Check text against compliance frameworks for violations.

    Args:
        text: Text content to validate
        frameworks: List of frameworks to check against.
                   Options: eu_ai_act, gdpr, owasp, nist, hipaa.
                   If None, checks all frameworks.

    Returns:
        Dict with:
          - frameworks_checked: list of framework names
          - violations: list of {framework, severity, description, location}
          - compliant: bool (no violations found)
          - risk_score: 0-10 (higher = more risky)
    """
    if not text or not isinstance(text, str):
        return {
            "error": "Text must be a non-empty string",
            "frameworks_checked": [],
            "violations": [],
            "compliant": True,
            "risk_score": 0,
        }

    if len(text) > 50000:
        return {
            "error": "Text exceeds 50,000 characters",
            "frameworks_checked": [],
            "violations": [],
            "compliant": True,
            "risk_score": 0,
        }

    # Determine which frameworks to check
    if frameworks is None:
        frameworks = list(_COMPLIANCE_FRAMEWORKS.keys())
    else:
        frameworks = [f.lower() for f in frameworks if f.lower() in _COMPLIANCE_FRAMEWORKS]

    logger.info("compliance_check frameworks=%s text_length=%d", frameworks, len(text))

    violations = []
    text_lower = text.lower()

    for framework in frameworks:
        framework_config = _COMPLIANCE_FRAMEWORKS[framework]
        for check_type, check_desc in framework_config["checks"]:
            # Run framework-specific checks
            if _check_violation(text_lower, text, framework, check_type):
                violations.append({
                    "framework": framework,
                    "check_type": check_type,
                    "severity": _get_severity(framework, check_type),
                    "description": check_desc,
                    "location": _find_location(text, framework, check_type),
                })

    # Calculate risk score (0-10)
    risk_score = min(10, len(violations) + _count_pii_findings(text))

    return {
        "frameworks_checked": frameworks,
        "violations": violations,
        "compliant": len(violations) == 0,
        "risk_score": risk_score,
        "total_violations": len(violations),
    }


def research_pii_scan(text: str) -> dict[str, Any]:
    """Scan text for PII (Personally Identifiable Information).

    Detects: emails, phone numbers, SSNs, credit cards, IP addresses, names.

    Args:
        text: Text to scan for PII

    Returns:
        Dict with:
          - pii_found: list of {type, value_masked, position, context}
          - total_pii: count of PII instances found
          - risk_level: low/medium/high
          - recommendation: mitigation advice
    """
    if not text or not isinstance(text, str):
        return {
            "error": "Text must be a non-empty string",
            "pii_found": [],
            "total_pii": 0,
            "risk_level": "low",
            "recommendation": "No text to scan",
        }

    if len(text) > 50000:
        text = text[:50000]
        truncated = True
    else:
        truncated = False

    logger.info("pii_scan text_length=%d", len(text))

    pii_found = []

    # Scan for each PII type
    for pii_type, pattern in _PII_PATTERNS.items():
        matches = list(re.finditer(pattern, text, re.IGNORECASE))
        for match in matches:
            start = max(0, match.start() - 20)
            end = min(len(text), match.end() + 20)
            context = text[start:end].strip()

            pii_found.append({
                "type": pii_type,
                "value_masked": _mask_pii(match.group(), pii_type),
                "position": match.start(),
                "context": context,
            })

    # Remove duplicates (same PII found multiple times)
    unique_pii = {}
    for item in pii_found:
        key = (item["type"], item["value_masked"])
        if key not in unique_pii:
            unique_pii[key] = item

    pii_list = list(unique_pii.values())

    # Determine risk level based on PII count and types
    critical_pii = sum(1 for p in pii_list if p["type"] in ["ssn", "credit_card"])
    sensitive_pii = sum(1 for p in pii_list if p["type"] in ["email", "phone"])

    if critical_pii >= 2 or (critical_pii > 0 and sensitive_pii > 2):
        risk_level = "high"
    elif critical_pii > 0 or sensitive_pii >= 3:
        risk_level = "medium"
    else:
        risk_level = "low"

    # Generate recommendation
    if risk_level == "high":
        recommendation = "Critical: Remove sensitive data before sharing. Verify GDPR/HIPAA compliance."
    elif risk_level == "medium":
        recommendation = "Caution: Review PII for necessity. Mask or remove before distribution."
    else:
        recommendation = "Info: No critical PII detected. Standard data handling recommended."

    if truncated:
        recommendation += " (Text truncated to 50K chars)"

    return {
        "pii_found": pii_list,
        "total_pii": len(pii_list),
        "pii_summary": {
            "critical_items": critical_pii,
            "sensitive_items": sensitive_pii,
        },
        "risk_level": risk_level,
        "recommendation": recommendation,
    }


def _check_violation(text_lower: str, text: str, framework: str, check_type: str) -> bool:
    """Check if a specific compliance violation exists."""
    if framework == "eu_ai_act":
        if check_type == "pii_exposure":
            return _count_pii_findings(text) > 0
        elif check_type == "unsafe_recommendation":
            unsafe_keywords = ["exploit", "bypass", "malware", "ransomware", "hack"]
            return any(kw in text_lower for kw in unsafe_keywords)
        elif check_type == "missing_disclaimer":
            return not any(
                phrase in text_lower
                for phrase in ["disclaimer", "limitation", "not responsible", "use at own risk"]
            )
        elif check_type == "bias_indicator":
            bias_keywords = ["all", "always", "never", "stereotype"]
            return any(kw in text_lower for kw in bias_keywords)

    elif framework == "gdpr":
        if check_type == "pii_exposure":
            return _count_pii_findings(text) > 0
        elif check_type == "data_location":
            locations = ["server", "database", "stored in", "location:", "region:"]
            return any(loc in text_lower for loc in locations)
        elif check_type == "consent_missing":
            consent_keywords = ["consent", "agreed", "opt-in", "permission"]
            return not any(kw in text_lower for kw in consent_keywords)
        elif check_type == "retention_policy":
            retention_keywords = ["retention", "delete", "purge", "expire"]
            return not any(kw in text_lower for kw in retention_keywords)

    elif framework == "owasp":
        if check_type == "hardcoded_secrets":
            secret_patterns = [
                r"api[_-]?key\s*[=:]\s*['\"]",
                r"password\s*[=:]\s*['\"]",
                r"token\s*[=:]\s*['\"]",
            ]
            return any(re.search(p, text, re.IGNORECASE) for p in secret_patterns)
        elif check_type == "sql_injection_hint":
            sql_keywords = ["sql", "injection", "where 1=1", "' or '"]
            return any(kw in text_lower for kw in sql_keywords)
        elif check_type == "xss_hint":
            xss_keywords = ["<script>", "onclick", "onerror", "javascript:"]
            return any(kw in text_lower for kw in xss_keywords)
        elif check_type == "auth_bypass":
            bypass_keywords = ["bypass", "circumvent", "skip authentication", "no auth"]
            return any(kw in text_lower for kw in bypass_keywords)

    elif framework == "nist":
        if check_type == "access_control":
            access_keywords = ["access control", "rbac", "abac", "permission"]
            return not any(kw in text_lower for kw in access_keywords)
        elif check_type == "encryption_missing":
            encryption_keywords = ["encrypt", "tls", "ssl", "aes", "rsa"]
            return not any(kw in text_lower for kw in encryption_keywords)
        elif check_type == "audit_trail":
            audit_keywords = ["audit", "logging", "log", "trace"]
            return not any(kw in text_lower for kw in audit_keywords)
        elif check_type == "incident_response":
            incident_keywords = ["incident", "response", "disaster recovery", "breach"]
            return not any(kw in text_lower for kw in incident_keywords)

    elif framework == "hipaa":
        if check_type == "phi_exposure":
            phi_keywords = ["patient", "medical", "diagnosis", "treatment"]
            return any(kw in text_lower for kw in phi_keywords)
        elif check_type == "pii_exposure":
            return _count_pii_findings(text) > 0
        elif check_type == "encryption_missing":
            encryption_keywords = ["encrypt", "tls", "hipaa compliant"]
            return not any(kw in text_lower for kw in encryption_keywords)
        elif check_type == "audit_control":
            audit_keywords = ["audit", "access log", "compliance audit"]
            return not any(kw in text_lower for kw in audit_keywords)

    return False


def _get_severity(framework: str, check_type: str) -> str:
    """Determine severity level of a violation."""
    critical_checks = {
        "pii_exposure", "phi_exposure", "hardcoded_secrets",
        "sql_injection_hint", "xss_hint",
    }
    if check_type in critical_checks:
        return "critical"
    elif check_type in {"auth_bypass", "unsafe_recommendation"}:
        return "high"
    else:
        return "medium"


def _find_location(text: str, framework: str, check_type: str) -> str:
    """Find location (character position) of violation."""
    # Return a general location description
    if check_type == "pii_exposure":
        match = re.search(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", text)
        if match:
            return f"around position {match.start()}"
    return "see pii_scan for details"


def _count_pii_findings(text: str) -> int:
    """Count total number of PII findings in text."""
    count = 0
    for pii_type, pattern in _PII_PATTERNS.items():
        matches = re.findall(pattern, text, re.IGNORECASE)
        count += len(matches)
    return count


def _mask_pii(value: str, pii_type: str) -> str:
    """Mask PII value for safe display."""
    if pii_type == "email":
        parts = value.split("@")
        return f"{parts[0][:2]}***@***{parts[1][-3:]}" if len(parts) == 2 else "***@***"
    elif pii_type == "phone":
        return value[:3] + "***" + value[-4:] if len(value) >= 10 else "***"
    elif pii_type == "ssn":
        return "***-**-" + value[-4:]
    elif pii_type == "credit_card":
        return "****-****-****-" + value[-4:]
    elif pii_type == "ip_address":
        parts = value.split(".")
        return f"{parts[0]}.***.**.*" if len(parts) == 4 else "***"
    else:  # name
        return value[0] + "***" if value else "***"
