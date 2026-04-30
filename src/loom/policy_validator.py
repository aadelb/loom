"""Policy validator for testing which specific model policies a prompt would violate.

Tests prompts against multiple AI safety and compliance policies including:
- OpenAI Usage Policy
- Anthropic Acceptable Use Policy
- Google AI Principles
- Meta Llama Use Policy
- EU AI Act Prohibited Practices
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class PolicyViolation:
    """A detected policy violation."""

    policy: str
    category: str
    severity: Literal["low", "medium", "high", "critical"]
    explanation: str


@dataclass(frozen=True)
class ValidationResult:
    """Result of policy validation."""

    violations: list[PolicyViolation]
    compliant_policies: list[str]
    overall_risk: Literal["compliant", "minor_violation", "major_violation", "prohibited"]
    reframe_suggestions: list[str]
    safe_alternatives: list[str]


class PolicyValidator:
    """Test which specific model policies a prompt would violate."""

    POLICIES = {
        "openai_usage": {
            "description": "OpenAI Usage Policy",
            "categories": ["violence", "sexual", "harassment", "self-harm", "illegal", "deceptive", "political"],
        },
        "anthropic_aup": {
            "description": "Anthropic Acceptable Use Policy",
            "categories": ["weapons", "surveillance", "deception", "manipulation", "illegal_activity"],
        },
        "google_ai": {
            "description": "Google AI Principles",
            "categories": ["dangerous", "harassment", "hate_speech", "sexually_explicit", "medical_advice"],
        },
        "meta_llama": {
            "description": "Meta Llama Use Policy",
            "categories": ["violence", "criminal", "privacy", "deception", "discrimination"],
        },
        "eu_ai_act": {
            "description": "EU AI Act Prohibited Practices (Article 5)",
            "categories": ["biometric", "social_scoring", "manipulation", "law_enforcement", "critical_infrastructure"],
        },
    }

    # Pattern-based detectors for different violation categories
    PATTERNS = {
        # Violence patterns
        "violence": [
            r"\b(kill|murder|stab|shoot|bomb|explode|destroy|hurt|injure|harm|attack|assault|violence|violent)\b",
            r"\b(how to|guide|tutorial|instructions? for) .*? (kill|murder|harm|injure)\b",
            r"instructions? (?:for|to) (?:commit|perform) (?:violence|murder|killing)",
        ],
        # Sexual content patterns
        "sexual": [
            r"\b(sex|porn|nude|naked|xxx|sexual|erotic|adult content|explicit)\b",
            r"(?:create|generate|make|produce) .*? (?:porn|sexual|nude)",
            r"\b(child|minor|underage) .*? (?:sexual|porn|abuse)\b",
        ],
        # Self-harm patterns
        "self-harm": [
            r"\b(suicide|self-harm|self-hurt|cutting|eating disorder)\b",
            r"how to (?:commit|perform) (?:suicide|self-harm)",
            r"(?:instructions?|guide) .*? (?:suicide|overdose|self-injury)",
        ],
        # Harassment patterns
        "harassment": [
            r"\b(harass|cyberbully|bully|stalk|threaten|blackmail|dox|doxing)\b",
            r"(?:how to|help (?:me|us)) (?:harass|dox|stalk|threaten) (?:someone|people)",
            r"(?:expose|leak|release) (?:personal|private|doxxing|identity) (?:information|data|address)",
        ],
        # Illegal activity patterns
        "illegal": [
            r"\b(illegal|crime|criminal|unlawful|against the law)\b",
            r"(?:how to|instructions? (?:for|to)) (?:commit|perform) (?:illegal|crime|theft|fraud)",
            r"(?:make|create|produce|manufacture|extract) .{0,20}?(cocaine|heroin|meth|methamphetamine|fentanyl|drug)",
            r"(?:cocaine|heroin|meth|methamphetamine|fentanyl|drug) (?:production|manufacturing|synthesis|extraction)",
        ],
        # Deceptive practices
        "deceptive": [
            r"\b(deepfake|phishing|scam|fraud|misinformation|disinformation|fake)\b",
            r"(?:create|generate|make) .*? (?:fake|forged|fraudulent) (?:document|evidence|credential)",
            r"(?:how to|help (?:me|us)) (?:phish|scam|defraud|manipulate|deceive)",
        ],
        # Weapons patterns
        "weapons": [
            r"\b(weapon|gun|firearm|explosive|bomb|IED|WMD|nuclear)\b",
            r"(?:how to|instructions? (?:for|to)) (?:make|build|create) (?:weapon|bomb|explosive)",
            r"\b(3D print|manufacture|produce) .*? (?:gun|weapon|explosive)\b",
        ],
        # Surveillance patterns
        "surveillance": [
            r"\b(surveillance|wiretap|spy|tracking|monitoring|stalking) (?:device|tool|system)\b",
            r"(?:how to|instructions? (?:for|to)) (?:spy on|track|surveil|wiretap)",
            r"\b(hidden camera|audio bug|tracking device|spyware)\b",
        ],
        # Manipulation patterns
        "manipulation": [
            r"\b(manipulate|exploit|coerce|pressure|psychological manipulation|brainwashing)\b",
            r"(?:how to|help (?:me|us)) (?:manipulate|exploit|coerce) (?:people|person)",
        ],
        # Hate speech patterns
        "hate_speech": [
            r"\b(hate|slur|racist|sexist|xenophobic|homophobic|transphobic|bigot|hateful)\b",
            r"(?:create|generate) .*? (?:slur|racist|sexist|hateful) (?:content|speech|message|joke)",
        ],
        # Discrimination patterns
        "discrimination": [
            r"(?:discriminat|bias|prejudice|stereotype) .{0,20}?(?:against|toward|based on)",
            r"(?:based on|because of|due to) (?:race|gender|religion|ethnicity|sexual orientation|disability)",
        ],
        # Dangerous/hazardous patterns
        "dangerous": [
            r"\b(dangerous|hazardous|harmful|toxic|poison|corrosive|radioactive)\b",
            r"(?:how to|instructions? (?:for|to)) (?:create|make|produce) (?:dangerous|hazardous|poison)",
        ],
        # Medical advice patterns
        "medical_advice": [
            r"(?:should I|can I|will I) (?:take|use|inject|consume) .{0,30}?(?:instead of|without) (?:doctor|prescription|treatment|professional)",
            r"(?:how to|instructions?) .{0,20}?(?:cure|treat|heal) .{0,20}?(?:cancer|diabetes|heart disease|covid|serious illness|disease)",
            r"(?:diagnose|treat|cure|medication|medicine) (?:myself|yourself|patient|someone) (?:without|instead of) (?:doctor|professional|healthcare)",
            r"(?:without|instead of) (?:seeing|visiting|consulting) .*?(?:doctor|healthcare|professional)",
        ],
        # Privacy violations
        "privacy": [
            r"(?:expose|leak|release|publish) (?:private|personal|confidential) (?:data|information|documents|details)",
            r"\b(doxxing|doxing|expose identity|reveal address)\b",
            r"(?:how to|help (?:me|us)) (?:expose|leak|dox) .*? (?:information|identity|address)",
        ],
        # Criminal activity
        "criminal": [
            r"\b(criminal|crime|felony|misdemeanor|conviction|arrest|heist|robbery|theft)\b",
            r"(?:how to|help (?:me|us)) (?:commit|plan) (?:crime|theft|robbery|murder|heist|fraud)",
            r"(?:how to|instructions? (?:for|to)) (?:steal|rob|shoplift|embezzle)",
        ],
        # Biometric surveillance (EU AI Act)
        "biometric": [
            r"\b(facial recognition|biometric identification|real-time biometric) (?:in|on) (?:public|street|crowd)",
            r"(?:mass|large-scale) (?:facial recognition|biometric identification)",
            r"\b(remote biometric identification) (?:in public space|in public|in streets)\b",
        ],
        # Social scoring (EU AI Act)
        "social_scoring": [
            r"\b(social credit|social score|reputation score) (?:system|mechanism)\b",
            r"(?:rate|score|rank) .{0,30}?(?:based on|using) .{0,30}?(?:behavior|conduct|compliance)",
        ],
        # Law enforcement discrimination (EU AI Act)
        "law_enforcement": [
            r"(?:police|law enforcement) (?:profiling|targeting|surveillance) (?:based on|using) (?:race|gender|ethnicity|protected characteristic)",
            r"\b(predictive policing) .*? (?:race|ethnicity|protected)\b",
        ],
        # Critical infrastructure attacks
        "critical_infrastructure": [
            r"(?:attack|compromise|disrupt|sabotage) .{0,30}?(?:power|water|energy|hospital|emergency|transportation|communication) .{0,20}?(?:system|infrastructure)",
            r"(?:how to|instructions? (?:for|to)) (?:hack|breach|attack) (?:power grid|hospital|emergency system)",
        ],
        # Sexually explicit content
        "sexually_explicit": [
            r"\b(pornography|pornographic|sexually explicit|adult content)\b",
            r"(?:generate|create|produce) .*? (?:sexually explicit|pornographic|nude) (?:image|video|content)",
        ],
        # Political bias (OpenAI)
        "political": [
            r"(?:write|create|generate) .*? (?:propaganda|campaign material|political attack) (?:for|against) (?:candidate|party|politician)",
            r"(?:manipulate|influence) (?:election|voters|public opinion) (?:in favor of|against) (?:candidate|party)",
        ],
        # Deception (Meta)
        "deception": [
            r"\b(deepfake|phishing|scam|fraud|misinformation|disinformation|fake)\b",
            r"(?:create|generate|make) .*? (?:fake|forged|fraudulent) (?:document|evidence|credential)",
            r"(?:how to|help (?:me|us)) (?:phish|scam|defraud|manipulate|deceive)",
        ],
        # Illegal activity (Anthropic)
        "illegal_activity": [
            r"(illegal|crime|criminal|unlawful|against the law|robbery|theft)",
            r"(?:how to|instructions? (?:for|to)) (?:commit|perform) (?:illegal|crime|theft|fraud|robbery|rob)",
            r"(?:make|create|produce|manufacture|extract) .{0,20}?(cocaine|heroin|meth|methamphetamine|fentanyl|drug)",
            r"(?:help (?:me|us)) (?:rob|steal|shoplift|embezzle)",
        ],
    }

    def validate(
        self, prompt: str, policies: list[str] | None = None
    ) -> ValidationResult:
        """Check prompt against specified policies (or all).

        Args:
            prompt: The prompt text to validate
            policies: List of policy names to check (None = all policies)

        Returns:
            ValidationResult with violations, compliant policies, risk level, and suggestions
        """
        if not policies:
            policies = list(self.POLICIES.keys())

        # Validate requested policies exist
        invalid_policies = set(policies) - set(self.POLICIES.keys())
        if invalid_policies:
            raise ValueError(f"Unknown policies: {invalid_policies}")

        violations: list[PolicyViolation] = []
        compliant_policies: list[str] = []

        # Check each policy
        for policy_key in policies:
            policy = self.POLICIES[policy_key]
            categories = policy["categories"]

            policy_violations = self._check_policy(prompt, policy_key, categories)

            if policy_violations:
                violations.extend(policy_violations)
            else:
                compliant_policies.append(policy_key)

        # Calculate overall risk
        if not violations:
            overall_risk: Literal["compliant", "minor_violation", "major_violation", "prohibited"] = "compliant"
        else:
            severity_counts = {}
            for v in violations:
                severity_counts[v.severity] = severity_counts.get(v.severity, 0) + 1

            if severity_counts.get("critical", 0) > 0:
                overall_risk = "prohibited"
            elif severity_counts.get("high", 0) > 0 or severity_counts.get("critical", 0) > 0:
                overall_risk = "major_violation"
            else:
                overall_risk = "minor_violation"

        # Generate reframing suggestions and safe alternatives
        reframe_suggestions = self._generate_reframes(prompt, violations)
        safe_alternatives = self._generate_alternatives(prompt, violations)

        return ValidationResult(
            violations=violations,
            compliant_policies=compliant_policies,
            overall_risk=overall_risk,
            reframe_suggestions=reframe_suggestions,
            safe_alternatives=safe_alternatives,
        )

    def _check_policy(self, prompt: str, policy_key: str, categories: list[str]) -> list[PolicyViolation]:
        """Check prompt against specific policy categories."""
        violations = []
        prompt_lower = prompt.lower()

        for category in categories:
            if category in self.PATTERNS:
                patterns = self.PATTERNS[category]
                for pattern in patterns:
                    if re.search(pattern, prompt_lower, re.IGNORECASE):
                        # Determine severity
                        severity = self._assess_severity(prompt, category, policy_key)

                        violation = PolicyViolation(
                            policy=policy_key,
                            category=category,
                            severity=severity,
                            explanation=self._explain_violation(category, policy_key),
                        )
                        violations.append(violation)
                        break  # One violation per category per policy

        return violations

    def _assess_severity(self, prompt: str, category: str, policy_key: str) -> Literal["low", "medium", "high", "critical"]:
        """Assess violation severity based on category and context."""
        prompt_lower = prompt.lower()

        # Critical severity indicators
        critical_indicators = [
            # Direct instructions for harm
            r"(?:step by step|detailed|complete|full) (?:instructions?|guide|tutorial)",
            # Imminent/specific threat
            r"(?:right now|immediately|today|this week|soon)",
            # Scale/systematic
            r"(?:mass|large scale|widespread|systematic)",
            # EU AI Act violations are inherently critical
            policy_key == "eu_ai_act",
        ]

        # High severity indicators
        high_indicators = [
            # Clear intent to harm
            r"(?:how to|help (?:me|us)) (?:do|perform|create|make)",
            # Academic framing doesn't mitigate some violations
            category in ["violence", "weapons", "biometric"],
        ]

        # Check critical indicators
        if any(
            (isinstance(ind, str) and re.search(ind, prompt_lower, re.IGNORECASE))
            or (isinstance(ind, bool) and ind)
            for ind in critical_indicators
        ):
            return "critical"

        # Check high indicators
        if any(
            (isinstance(ind, str) and re.search(ind, prompt_lower, re.IGNORECASE))
            or (isinstance(ind, bool) and ind)
            for ind in high_indicators
        ):
            return "high"

        # Default severity based on category type
        if category in ["violence", "self-harm", "weapons", "surveillance", "biometric", "social_scoring"]:
            return "high"
        elif category in ["harassment", "illegal", "illegal_activity", "hate_speech", "criminal"]:
            return "medium"
        else:
            return "low"

    def _explain_violation(self, category: str, policy_key: str) -> str:
        """Generate explanation for a specific violation."""
        explanations = {
            # OpenAI
            "violence": "OpenAI Usage Policy prohibits violent content and instructions for causing harm",
            "sexual": "OpenAI Usage Policy prohibits sexual content, especially involving minors",
            "self-harm": "OpenAI Usage Policy prohibits content that could encourage self-harm or suicide",
            "harassment": "OpenAI Usage Policy prohibits harassment, bullying, and threatening content",
            "illegal": "OpenAI Usage Policy prohibits instructions for illegal activities",
            "deceptive": "OpenAI Usage Policy prohibits deceptive content including deepfakes and fraud",
            "political": "OpenAI Usage Policy restricts generation of political campaign materials",
            # Anthropic
            "weapons": "Anthropic AUP prohibits weapons creation, acquisition, and usage instructions",
            "surveillance": "Anthropic AUP prohibits unauthorized surveillance tools and techniques",
            "manipulation": "Anthropic AUP prohibits content designed to manipulate or deceive people",
            "illegal_activity": "Anthropic AUP prohibits instructions for illegal activities",
            # Google
            "dangerous": "Google AI Principles prohibit content that could cause widespread harm",
            "medical_advice": "Google AI Principles prohibit providing medical diagnosis/treatment advice",
            # Meta Llama
            "discrimination": "Meta Llama Use Policy prohibits discriminatory content based on protected characteristics",
            "privacy": "Meta Llama Use Policy prohibits exposing or leaking private personal information",
            "criminal": "Meta Llama Use Policy prohibits instructions for criminal activity",
            "deception": "Meta Llama Use Policy prohibits deceptive content and fraud",
            # EU AI Act
            "biometric": "EU AI Act Article 5 prohibits real-time remote biometric identification in public spaces",
            "social_scoring": "EU AI Act Article 5 prohibits social credit/scoring systems targeting individuals",
            "law_enforcement": "EU AI Act Article 5 prohibits discriminatory law enforcement AI systems",
            "critical_infrastructure": "EU AI Act Article 5 prohibits attacks or sabotage of critical infrastructure",
            # Google again
            "hate_speech": "Google AI Principles prohibit hateful content targeting protected groups",
            "sexually_explicit": "Google AI Principles prohibit sexually explicit content",
        }

        return explanations.get(category, f"Violates {policy_key} policy in {category} category")

    def _generate_reframes(self, prompt: str, violations: list[PolicyViolation]) -> list[str]:
        """Generate potential reframing strategies (for research/educational purposes)."""
        if not violations:
            return []

        suggestions = []

        # Check what violations exist to suggest relevant reframes
        violation_categories = {v.category for v in violations}

        # Academic/research framing
        if violation_categories & {"violence", "weapons", "illegal", "illegal_activity"}:
            suggestions.append(
                "Frame as academic research: 'In academic studies on security vulnerabilities, how is...'"
            )
            suggestions.append("Use historical/hypothetical language: 'Historically, how was...' or 'In a fictional scenario...'")

        # Educational framing
        if violation_categories & {"harmful", "dangerous"}:
            suggestions.append("Reframe as defensive security knowledge: 'To defend against X, one should understand...'")

        # Policy/legal analysis
        if violation_categories & {"surveillance", "discrimination"}:
            suggestions.append(
                "Reframe as policy analysis: 'For compliance purposes, organizations should understand...'"
            )

        # Harm reduction
        if violation_categories & {"self-harm", "harassment"}:
            suggestions.append("Reframe as harm reduction: 'To help someone in crisis, what are...'")

        # Informational framing
        if violation_categories & {"deceptive", "deception", "misinformation"}:
            suggestions.append("Reframe as fact-checking: 'To detect disinformation, what are the techniques...'")

        return suggestions[:3]  # Return top 3 suggestions

    def _generate_alternatives(self, prompt: str, violations: list[PolicyViolation]) -> list[str]:
        """Generate safe alternative ways to achieve the same goal."""
        if not violations:
            return []

        alternatives = []
        violation_categories = {v.category for v in violations}

        # Violence → Conflict resolution
        if "violence" in violation_categories:
            alternatives.append(
                "Rephrase: Ask about conflict resolution, negotiation, or peaceful problem-solving methods"
            )

        # Weapons → Security research
        if "weapons" in violation_categories:
            alternatives.append("Rephrase: Ask about defensive security measures or vulnerability disclosure")

        # Illegal activity → Legal alternatives
        if "illegal" in violation_categories or "illegal_activity" in violation_categories:
            alternatives.append("Rephrase: Ask about legal alternatives or legitimate business practices")

        # Surveillance → Privacy-preserving monitoring
        if "surveillance" in violation_categories:
            alternatives.append("Rephrase: Ask about privacy-preserving security monitoring or consent-based analytics")

        # Deception → Transparency
        if "deceptive" in violation_categories or "deception" in violation_categories:
            alternatives.append("Rephrase: Ask about transparent communication or authentic engagement strategies")

        # Self-harm → Mental health support
        if "self-harm" in violation_categories:
            alternatives.append("Rephrase: Ask about mental health resources, crisis support, or evidence-based treatments")

        # Harassment → Healthy communication
        if "harassment" in violation_categories:
            alternatives.append("Rephrase: Ask about assertive communication, conflict resolution, or setting boundaries")

        # Discrimination → Inclusive practices
        if "discrimination" in violation_categories:
            alternatives.append("Rephrase: Ask about inclusive hiring, diversity initiatives, or anti-bias training")

        # Medical advice → Professional consultation
        if "medical_advice" in violation_categories:
            alternatives.append("Rephrase: Ask about finding qualified healthcare providers or understanding treatment options")

        # Criminal → Legal → Legal alternatives
        if "criminal" in violation_categories:
            alternatives.append("Rephrase: Ask about legal paths to your goal or legitimate business practices")

        # Privacy → Data protection
        if "privacy" in violation_categories:
            alternatives.append("Rephrase: Ask about data protection best practices or privacy-preserving methods")

        return alternatives[:3]  # Return top 3 alternatives


# Convenience function for quick validation
def validate_prompt(
    prompt: str, policies: list[str] | None = None
) -> ValidationResult:
    """Quick validation function.

    Args:
        prompt: The prompt text to validate
        policies: List of policy names to check (None = all policies)

    Returns:
        ValidationResult with violations and risk assessment
    """
    validator = PolicyValidator()
    return validator.validate(prompt, policies)
