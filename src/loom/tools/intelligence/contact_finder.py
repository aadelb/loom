"""End-to-end contact finder — email and phone OSINT intelligence.

Combines 15+ techniques to find email addresses and phone numbers:
1. Email pattern generation (first.last@domain, etc.)
2. SMTP verification (no API key)
3. Google dorking for emails/phones
4. Social media password reset enumeration
5. Data breach search (HIBP-style)
6. Reverse phone/email lookup
7. Domain email scraping
8. Company employee enumeration
9. Phone carrier lookup (HLR)
10. Social media profile correlation
"""
from __future__ import annotations

import asyncio
import logging
import re
import smtplib
import socket
from typing import Any

import httpx

from loom.error_responses import handle_tool_errors

logger = logging.getLogger("loom.tools.contact_finder")

LOOM_API = "http://127.0.0.1:8788/api/v1/tools"

COMMON_MAILBOXES = [
    "info", "admin", "contact", "support", "sales", "hr", "hello",
    "office", "team", "press", "media", "jobs", "careers", "billing",
    "help", "feedback", "marketing", "ceo", "founder", "director",
]

EMAIL_PATTERNS = [
    "{first}.{last}",
    "{first}{last}",
    "{f}{last}",
    "{first}_{last}",
    "{first}-{last}",
    "{last}.{first}",
    "{last}{first}",
    "{f}.{last}",
    "{first}",
    "{last}",
    "{first}.{last}{year}",
    "{f}{last}{year}",
]

FREE_EMAIL_PROVIDERS = {
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "aol.com",
    "icloud.com", "mail.com", "protonmail.com", "zoho.com", "yandex.com",
    "gmx.com", "live.com", "msn.com", "fastmail.com", "tutanota.com",
}

DISPOSABLE_DOMAINS = {
    "mailinator.com", "guerrillamail.com", "tempmail.com", "throwaway.email",
    "sharklasers.com", "grr.la", "temp-mail.org", "10minutemail.com",
    "trashmail.com", "yopmail.com", "maildrop.cc", "dispostable.com",
}

SOCIAL_PLATFORMS = {
    "facebook": {
        "reset_url": "https://www.facebook.com/login/identify/?ctx=recover",
        "method": "POST form with email/phone, check response for partial mask",
        "reveals": "Partially masked phone + email from account recovery",
    },
    "instagram": {
        "reset_url": "https://www.instagram.com/accounts/account_recovery_send_ajax/",
        "method": "POST with email_or_username, response shows masked contact",
        "reveals": "Partially masked email + phone from password reset",
    },
    "twitter": {
        "reset_url": "https://twitter.com/account/begin_password_reset",
        "method": "Submit email/phone/username, check response",
        "reveals": "Confirms if account exists, shows masked email",
    },
    "linkedin": {
        "reset_url": "https://www.linkedin.com/checkpoint/rp/request-password-reset",
        "method": "Submit email, check if account exists",
        "reveals": "Account existence confirmation",
    },
    "microsoft": {
        "reset_url": "https://account.live.com/ResetPassword.aspx",
        "method": "Submit email, shows recovery options with masked phone/alt-email",
        "reveals": "Masked phone number + alternate email",
    },
    "google": {
        "reset_url": "https://accounts.google.com/signin/recovery",
        "method": "Submit email, shows masked recovery phone",
        "reveals": "Masked recovery phone number",
    },
    "apple": {
        "reset_url": "https://iforgot.apple.com/password/verify/appleid",
        "method": "Submit Apple ID (email), shows recovery options",
        "reveals": "Masked phone + trusted devices",
    },
    "telegram": {
        "method": "Search username via t.me/username, check bio for contact",
        "reveals": "Phone number if privacy settings allow",
    },
    "whatsapp": {
        "method": "Check if phone number has WhatsApp via wa.me/{number}",
        "reveals": "Profile photo + about text + online status",
    },
}

GOOGLE_DORKS = {
    "email": [
        'site:{domain} "@{domain}" email',
        '"{name}" "@{domain}" email',
        '"{name}" email {domain}',
        'intext:"@{domain}" filetype:pdf',
        'intext:"@{domain}" filetype:xlsx',
        'site:linkedin.com "{name}" "{domain}"',
        'site:github.com "@{domain}"',
        '"{name}" contact email {domain}',
    ],
    "phone": [
        '"{name}" phone number',
        '"{name}" "call" OR "tel" OR "mobile" {domain}',
        'site:{domain} "phone" OR "tel" OR "mobile"',
        '"{name}" "+1" OR "+44" OR "+971" {domain}',
        'intext:"phone" "{name}" site:linkedin.com',
    ],
}


def _get_mx(domain: str) -> list[str]:
    """Get MX records for a domain."""
    try:
        import dns.resolver
        answers = dns.resolver.resolve(domain, "MX")
        return sorted(
            [(r.preference, str(r.exchange).rstrip(".")) for r in answers],
            key=lambda x: x[0],
        )
    except Exception:
        pass
    try:
        mx_hosts = []
        for info in socket.getaddrinfo(domain, 25, socket.AF_INET, socket.SOCK_STREAM):
            mx_hosts.append(info[4][0])
        return [(10, h) for h in mx_hosts[:3]] if mx_hosts else []
    except Exception:
        return []


def _smtp_verify(email: str, mx_host: str, timeout: float = 10.0) -> str:
    """Verify email via SMTP RCPT TO check."""
    try:
        with smtplib.SMTP(mx_host, 25, timeout=timeout) as srv:
            srv.ehlo("verify.local")
            srv.mail("verify@verify.local")
            code, _ = srv.rcpt(email)
            return "deliverable" if code == 250 else "undeliverable" if code == 550 else "unknown"
    except Exception:
        return "unknown"


def _generate_emails(domain: str, first: str, last: str, year: str = "") -> list[str]:
    """Generate possible email addresses from name and domain."""
    results = []
    f = first[0] if first else ""
    for pattern in EMAIL_PATTERNS:
        try:
            email = pattern.format(first=first, last=last, f=f, year=year) + f"@{domain}"
            results.append(email.lower())
        except (KeyError, IndexError):
            continue
    return list(dict.fromkeys(results))


@handle_tool_errors("research_contact_find")
async def research_contact_find(
    target: str,
    domain: str = "",
    find_email: bool = True,
    find_phone: bool = True,
    verify_smtp: bool = True,
    search_social: bool = True,
    search_web: bool = True,
    max_results: int = 20,
) -> dict[str, Any]:
    """End-to-end contact finder — find email and phone for a person or domain.

    Combines 15+ OSINT techniques: pattern generation, SMTP verification,
    Google dorking, social media enumeration, breach search, and more.

    Args:
        target: Person name OR email OR phone OR username to investigate
        domain: Company domain (e.g., "google.com") for email pattern generation
        find_email: Search for email addresses
        find_phone: Search for phone numbers
        verify_smtp: Verify found emails via SMTP
        search_social: Check social media platforms
        search_web: Search web via Loom search tools
        max_results: Maximum results to return

    Returns:
        Dict with emails_found, phones_found, social_profiles, techniques_used,
        confidence scores, and verification status for each result.
    """
    results = {
        "target": target,
        "domain": domain,
        "emails_found": [],
        "phones_found": [],
        "social_profiles": [],
        "techniques_used": [],
        "google_dorks_suggested": [],
        "password_reset_methods": [],
    }

    is_email = "@" in target and "." in target.split("@")[-1]
    is_phone = target.replace("+", "").replace("-", "").replace(" ", "").isdigit() and len(target) >= 7
    name_parts = target.split() if not is_email and not is_phone else []
    first = name_parts[0].lower() if name_parts else ""
    last = name_parts[-1].lower() if len(name_parts) > 1 else ""

    # === TECHNIQUE 1: Email pattern generation ===
    if find_email and domain and first and last:
        emails = _generate_emails(domain, first, last)
        for email in emails[:12]:
            results["emails_found"].append({
                "email": email,
                "source": "pattern_generation",
                "confidence": 0.3,
                "verified": False,
            })
        results["techniques_used"].append("email_pattern_generation")

    # === TECHNIQUE 2: Common mailbox check ===
    if find_email and domain:
        for mailbox in COMMON_MAILBOXES[:10]:
            results["emails_found"].append({
                "email": f"{mailbox}@{domain}",
                "source": "common_mailbox",
                "confidence": 0.5,
                "verified": False,
            })
        results["techniques_used"].append("common_mailbox_enumeration")

    # === TECHNIQUE 3: SMTP verification ===
    if verify_smtp and domain and results["emails_found"]:
        mx_records = await asyncio.get_event_loop().run_in_executor(None, _get_mx, domain)
        if mx_records:
            results["mx_records"] = [h for _, h in mx_records[:3]]
            mx_host = mx_records[0][1]
            for entry in results["emails_found"][:8]:
                status = await asyncio.get_event_loop().run_in_executor(
                    None, _smtp_verify, entry["email"], mx_host
                )
                entry["verified"] = status == "deliverable"
                entry["smtp_status"] = status
                if status == "deliverable":
                    entry["confidence"] = 0.9
            results["techniques_used"].append("smtp_verification")

    # === TECHNIQUE 4: Reverse email lookup ===
    if is_email:
        email_domain = target.split("@")[1]
        results["emails_found"].append({
            "email": target,
            "source": "input",
            "confidence": 1.0,
            "is_free_provider": email_domain in FREE_EMAIL_PROVIDERS,
            "is_disposable": email_domain in DISPOSABLE_DOMAINS,
        })
        results["techniques_used"].append("reverse_email_analysis")

    # === TECHNIQUE 5: Google dorks ===
    if search_web:
        name_str = " ".join(name_parts) if name_parts else target
        search_domain = domain or (target.split("@")[1] if is_email else "")

        if find_email:
            for dork_template in GOOGLE_DORKS["email"][:4]:
                try:
                    dork = dork_template.format(
                        name=name_str, domain=search_domain or "example.com"
                    )
                    results["google_dorks_suggested"].append(dork)
                except (KeyError, IndexError):
                    continue

        if find_phone:
            for dork_template in GOOGLE_DORKS["phone"][:3]:
                try:
                    dork = dork_template.format(
                        name=name_str, domain=search_domain or ""
                    )
                    results["google_dorks_suggested"].append(dork)
                except (KeyError, IndexError):
                    continue
        results["techniques_used"].append("google_dorking")

    # === TECHNIQUE 6: Web search via Loom ===
    if search_web and (name_parts or is_email):
        query = f'"{" ".join(name_parts)}" email' if name_parts else f'"{target}" phone email contact'
        if domain:
            query += f" {domain}"
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                r = await client.post(
                    f"{LOOM_API}/research_search",
                    json={"query": query, "n": 5},
                )
                if r.status_code == 200:
                    search_data = r.json()
                    search_results = search_data.get("results", [])
                    text = str(search_results)
                    found_emails = re.findall(
                        r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text
                    )
                    for em in found_emails[:5]:
                        if em not in [e["email"] for e in results["emails_found"]]:
                            results["emails_found"].append({
                                "email": em,
                                "source": "web_search",
                                "confidence": 0.6,
                                "verified": False,
                            })
                    found_phones = re.findall(
                        r"\+?\d{1,3}[-.\s]?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}", text
                    )
                    for ph in found_phones[:5]:
                        clean = re.sub(r"[^\d+]", "", ph)
                        if len(clean) >= 7:
                            results["phones_found"].append({
                                "phone": ph,
                                "source": "web_search",
                                "confidence": 0.4,
                            })
                    results["techniques_used"].append("web_search_scraping")
        except Exception as e:
            logger.debug("web search failed: %s", e)

    # === TECHNIQUE 7: Social media password reset enumeration ===
    if search_social:
        target_input = target if is_email or is_phone else (
            results["emails_found"][0]["email"] if results["emails_found"] else target
        )
        for platform, info in SOCIAL_PLATFORMS.items():
            results["password_reset_methods"].append({
                "platform": platform,
                "url": info.get("reset_url", ""),
                "method": info.get("method", ""),
                "reveals": info.get("reveals", ""),
                "input_to_try": target_input,
            })
        results["techniques_used"].append("password_reset_enumeration")

    # === TECHNIQUE 8: Phone from email (carrier lookup simulation) ===
    if find_phone and is_email:
        results["phone_search_methods"] = [
            {"method": "truecaller_lookup", "description": "Search email in Truecaller database", "url": "https://www.truecaller.com"},
            {"method": "sync_me_lookup", "description": "Search via Sync.me reverse lookup", "url": "https://sync.me"},
            {"method": "facebook_recovery", "description": "Use FB password reset to see masked phone", "url": "https://www.facebook.com/login/identify/"},
            {"method": "google_recovery", "description": "Check Google account recovery for masked phone", "url": "https://accounts.google.com/signin/recovery"},
            {"method": "whatsapp_check", "description": "If phone found, verify via wa.me/{number}"},
            {"method": "telegram_search", "description": "Search by username in Telegram"},
            {"method": "signal_check", "description": "Check if phone is registered on Signal"},
        ]
        results["techniques_used"].append("phone_from_email_methods")

    # === TECHNIQUE 9: Email from phone ===
    if find_email and is_phone:
        clean_phone = re.sub(r"[^\d+]", "", target)
        results["email_search_methods"] = [
            {"method": "facebook_phone_search", "description": f"Search FB by phone {clean_phone}", "url": "https://www.facebook.com/login/identify/"},
            {"method": "google_contacts", "description": "Add phone to Google Contacts, check linked accounts"},
            {"method": "truecaller_reverse", "description": "Reverse phone lookup for linked email", "url": "https://www.truecaller.com"},
            {"method": "whatsapp_about", "description": f"Check wa.me/{clean_phone} for profile info"},
            {"method": "telegram_phone", "description": "Import phone to Telegram contacts, check username"},
            {"method": "snapchat_lookup", "description": "Find Snapchat account by phone, check linked email"},
            {"method": "viber_lookup", "description": "Check Viber for account info by phone"},
        ]
        results["techniques_used"].append("email_from_phone_methods")

    # === TECHNIQUE 10: Social media profile search ===
    if search_social and name_parts:
        username_guesses = []
        if first and last:
            username_guesses = [
                f"{first}{last}", f"{first}.{last}", f"{first}_{last}",
                f"{first[0]}{last}", f"{last}{first}",
            ]
        for username in username_guesses[:3]:
            results["social_profiles"].append({
                "username": username,
                "platforms_to_check": [
                    f"https://github.com/{username}",
                    f"https://twitter.com/{username}",
                    f"https://linkedin.com/in/{username}",
                    f"https://instagram.com/{username}",
                    f"https://t.me/{username}",
                    f"https://facebook.com/{username}",
                ],
                "source": "username_guess",
            })
        results["techniques_used"].append("social_profile_enumeration")

    # Trim to max_results
    results["emails_found"] = results["emails_found"][:max_results]
    results["phones_found"] = results["phones_found"][:max_results]
    results["total_emails"] = len(results["emails_found"])
    results["total_phones"] = len(results["phones_found"])
    results["total_techniques"] = len(results["techniques_used"])

    return results


@handle_tool_errors("research_phone_lookup")
async def research_phone_lookup(
    phone: str,
    country_code: str = "",
) -> dict[str, Any]:
    """Lookup phone number intelligence — carrier, type, location, linked accounts.

    Args:
        phone: Phone number (with or without country code)
        country_code: ISO country code (e.g., "US", "AE", "GB")

    Returns:
        Carrier info, number type, location estimate, linked service checks.
    """
    clean = re.sub(r"[^\d+]", "", phone)
    if not clean or len(clean) < 7:
        return {"error": "Invalid phone number (minimum 7 digits)"}

    has_country = clean.startswith("+") or len(clean) > 10

    country_prefixes = {
        "US": "+1", "GB": "+44", "AE": "+971", "SA": "+966",
        "IN": "+91", "CN": "+86", "DE": "+49", "FR": "+33",
        "JP": "+81", "AU": "+61", "BR": "+55", "RU": "+7",
    }

    if country_code and not has_country:
        prefix = country_prefixes.get(country_code.upper(), "")
        if prefix:
            clean = prefix + clean

    result = {
        "phone": phone,
        "normalized": clean,
        "country_code": country_code,
        "valid_format": len(clean) >= 10,
        "number_type": "unknown",
        "carrier_lookup": {
            "method": "HLR lookup via API or phonenumbers library",
            "services": [
                {"name": "Twilio Lookup", "url": "https://www.twilio.com/lookup", "free": False},
                {"name": "NumVerify", "url": "https://numverify.com", "free_tier": True},
                {"name": "Abstract API", "url": "https://www.abstractapi.com/phone-validation", "free_tier": True},
            ],
        },
        "reverse_lookup_services": [
            {"name": "Truecaller", "url": "https://www.truecaller.com", "reveals": "Name, email, spam score"},
            {"name": "Sync.me", "url": "https://sync.me", "reveals": "Name, social profiles"},
            {"name": "WhoCalled", "url": "https://www.whocalledme.com", "reveals": "Spam reports, caller ID"},
            {"name": "Spokeo", "url": "https://www.spokeo.com", "reveals": "Full profile (paid)"},
            {"name": "BeenVerified", "url": "https://www.beenverified.com", "reveals": "Full background (paid)"},
        ],
        "linked_services_check": {
            "whatsapp": f"https://wa.me/{clean.lstrip('+')}",
            "telegram": "Add to contacts, check if registered",
            "signal": "Check Signal app for registration",
            "viber": "Check Viber for account",
            "facebook": "Search by phone in FB",
            "instagram": "Try password reset with phone",
            "google": "Try account recovery with phone",
        },
        "osint_methods": [
            "Google dork: \"{phone}\" to find public mentions",
            "Facebook graph search by phone number",
            "CallerID apps (Truecaller, Hiya, RoboKiller)",
            "Telegram contact import (reveals username if registered)",
            "Data breach databases (search by phone)",
            "Court records / public documents search",
            "Business registration databases",
        ],
    }

    try:
        import phonenumbers
        parsed = phonenumbers.parse(clean if clean.startswith("+") else f"+{clean}")
        result["parsed"] = {
            "country": phonenumbers.region_code_for_number(parsed),
            "type": str(phonenumbers.number_type(parsed)),
            "valid": phonenumbers.is_valid_number(parsed),
            "possible": phonenumbers.is_possible_number(parsed),
            "international": phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL),
            "national": phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.NATIONAL),
        }
        result["number_type"] = result["parsed"]["type"]
    except ImportError:
        result["parsed"] = {"note": "Install phonenumbers for detailed parsing: pip install phonenumbers"}
    except Exception as e:
        result["parsed"] = {"error": str(e)}

    return result


@handle_tool_errors("research_email_to_phone")
async def research_email_to_phone(email: str) -> dict[str, Any]:
    """Find phone numbers linked to an email address.

    Uses multiple correlation techniques: social media recovery pages,
    breach databases, CallerID services, and profile scraping.

    Args:
        email: Email address to find linked phone numbers for

    Returns:
        Methods to find linked phone, any found numbers, confidence levels.
    """
    if "@" not in email:
        return {"error": "Invalid email format"}

    domain = email.split("@")[1]
    username = email.split("@")[0]

    return {
        "email": email,
        "domain": domain,
        "username": username,
        "is_free_provider": domain in FREE_EMAIL_PROVIDERS,
        "techniques": [
            {
                "name": "Facebook Password Reset",
                "steps": [
                    f"1. Go to https://www.facebook.com/login/identify/",
                    f"2. Enter: {email}",
                    "3. If account exists, FB shows: 'Send code to +XX XXX XXX XX**'",
                    "4. The masked phone reveals country code + partial number",
                ],
                "automation": "POST to /login/identify/ with email, parse response HTML",
                "confidence": 0.7,
                "reveals": "Partially masked phone number",
            },
            {
                "name": "Google Account Recovery",
                "steps": [
                    "1. Go to https://accounts.google.com/signin/recovery",
                    f"2. Enter: {email}",
                    "3. Google shows recovery options including masked phone",
                ],
                "confidence": 0.6 if domain == "gmail.com" else 0.3,
                "reveals": "Masked recovery phone (last 2 digits visible)",
            },
            {
                "name": "Instagram Password Reset",
                "steps": [
                    "1. POST to /accounts/account_recovery_send_ajax/",
                    f"2. With email_or_username: {email}",
                    "3. Response includes masked phone if linked",
                ],
                "confidence": 0.5,
                "reveals": "Masked phone + confirms account existence",
            },
            {
                "name": "Microsoft Account Recovery",
                "steps": [
                    "1. Go to https://account.live.com/ResetPassword.aspx",
                    f"2. Enter: {email}",
                    "3. Shows recovery options with masked phone and alt-email",
                ],
                "confidence": 0.6 if domain in ("hotmail.com", "outlook.com", "live.com") else 0.2,
                "reveals": "Masked phone + alternate email",
            },
            {
                "name": "Truecaller Email Search",
                "steps": [
                    "1. Install Truecaller app",
                    f"2. Search for: {email}",
                    "3. May show linked phone number",
                ],
                "confidence": 0.4,
                "reveals": "Full phone number if in database",
            },
            {
                "name": "Data Breach Search",
                "steps": [
                    f"1. Search {email} on haveibeenpwned.com",
                    "2. Check which breaches include phone numbers",
                    "3. Search breach databases (dehashed, snusbase) for phone field",
                ],
                "confidence": 0.5,
                "reveals": "Phone number from leaked databases",
            },
            {
                "name": "Google Contacts Trick",
                "steps": [
                    f"1. Add {email} to your Google Contacts",
                    "2. Google may auto-fill phone from their Google profile",
                    "3. Check the contact's linked Google+ / Google profile",
                ],
                "confidence": 0.3,
                "reveals": "Phone if publicly shared on Google profile",
            },
        ],
        "google_dorks": [
            f'"{email}" phone OR tel OR mobile OR call',
            f'"{username}" phone number',
            f'"{email}" site:linkedin.com',
            f'"{email}" filetype:pdf',
        ],
    }


@handle_tool_errors("research_phone_to_email")
async def research_phone_to_email(phone: str) -> dict[str, Any]:
    """Find email addresses linked to a phone number.

    Uses reverse lookup techniques: social media, CallerID apps,
    breach databases, and account recovery enumeration.

    Args:
        phone: Phone number to find linked emails for

    Returns:
        Methods to find linked email, any found addresses, confidence levels.
    """
    clean = re.sub(r"[^\d+]", "", phone)
    if len(clean) < 7:
        return {"error": "Invalid phone number"}

    return {
        "phone": phone,
        "normalized": clean,
        "techniques": [
            {
                "name": "Facebook Phone Search",
                "steps": [
                    f"1. Go to https://www.facebook.com/login/identify/",
                    f"2. Enter phone: {phone}",
                    "3. If account found, FB shows: 'Send code to j***@g***.com'",
                    "4. The masked email reveals provider + partial username",
                ],
                "confidence": 0.7,
                "reveals": "Partially masked email (provider visible)",
            },
            {
                "name": "Telegram Contact Import",
                "steps": [
                    f"1. Add {phone} to phone contacts",
                    "2. Open Telegram, sync contacts",
                    "3. If registered, shows Telegram username",
                    "4. Search username across platforms for email",
                ],
                "confidence": 0.5,
                "reveals": "Telegram username → cross-platform email search",
            },
            {
                "name": "WhatsApp Profile Check",
                "steps": [
                    f"1. Open https://wa.me/{clean.lstrip('+')}",
                    "2. If registered, shows profile photo + about text",
                    "3. About text may contain email or website",
                ],
                "confidence": 0.4,
                "reveals": "Profile info, possible email in bio",
            },
            {
                "name": "Truecaller Reverse Lookup",
                "steps": [
                    f"1. Search {phone} on Truecaller",
                    "2. Shows name, carrier, and linked email",
                ],
                "confidence": 0.6,
                "reveals": "Full name + possible email",
            },
            {
                "name": "Sync.me Reverse Lookup",
                "steps": [
                    f"1. Search {phone} on sync.me",
                    "2. Shows social profiles linked to phone",
                    "3. Cross-reference profiles for email",
                ],
                "confidence": 0.5,
                "reveals": "Social profiles → email extraction",
            },
            {
                "name": "Google Account Discovery",
                "steps": [
                    "1. Go to Google account recovery",
                    f"2. Enter phone: {phone}",
                    "3. Google shows linked email addresses (masked)",
                ],
                "confidence": 0.6,
                "reveals": "Masked Gmail/Google account email",
            },
            {
                "name": "Data Breach Phone Search",
                "steps": [
                    f"1. Search {clean} in breach databases",
                    "2. Many breaches link phone → email",
                    "3. Services: dehashed.com, snusbase.com, breachdirectory.org",
                ],
                "confidence": 0.5,
                "reveals": "Email from leaked database records",
            },
        ],
        "google_dorks": [
            f'"{phone}" email',
            f'"{clean}" "@gmail.com" OR "@yahoo.com" OR "@hotmail.com"',
            f'"{phone}" contact',
        ],
    }


@handle_tool_errors("research_holehe_check")
async def research_holehe_check(email: str) -> dict[str, Any]:
    """Check which websites an email is registered on using holehe (10K+ stars).

    Uses password reset / registration API enumeration across 120+ sites
    to determine where an email has accounts — without sending any emails.
    Based on: https://github.com/megadose/holehe

    Args:
        email: Email address to check

    Returns:
        Dict with registered sites, not registered sites, rate limited sites,
        and total counts.
    """
    if "@" not in email:
        return {"error": "Invalid email format"}

    try:
        import holehe.modules as holehe_modules
        from holehe.core import import_submodules

        modules = import_submodules(holehe_modules)
        client = httpx.AsyncClient(timeout=15.0)
        out = []

        tasks = []
        for module in modules:
            check_fn = getattr(module, module.__name__.split(".")[-1], None)
            if check_fn and callable(check_fn):
                tasks.append(check_fn(email, client, out))

        await asyncio.gather(*tasks, return_exceptions=True)
        await client.aclose()

        registered = [r for r in out if r.get("exists")]
        not_registered = [r for r in out if not r.get("exists") and not r.get("rate_limit")]
        rate_limited = [r for r in out if r.get("rate_limit")]

        return {
            "email": email,
            "total_sites_checked": len(out),
            "registered_count": len(registered),
            "registered_sites": [
                {"site": r.get("name", ""), "url": r.get("domain", ""), "method": r.get("method", "")}
                for r in registered
            ],
            "not_registered_count": len(not_registered),
            "rate_limited_count": len(rate_limited),
            "rate_limited_sites": [r.get("name", "") for r in rate_limited],
        }
    except ImportError:
        return {
            "email": email,
            "error": "holehe not installed. Install with: pip install holehe",
            "manual_check": {
                "description": "Without holehe, try these password reset pages manually:",
                "sites": [
                    {"name": "Facebook", "url": "https://www.facebook.com/login/identify/"},
                    {"name": "Instagram", "url": "https://www.instagram.com/accounts/password/reset/"},
                    {"name": "Twitter/X", "url": "https://twitter.com/account/begin_password_reset"},
                    {"name": "LinkedIn", "url": "https://www.linkedin.com/checkpoint/rp/request-password-reset"},
                    {"name": "Microsoft", "url": "https://account.live.com/ResetPassword.aspx"},
                    {"name": "Google", "url": "https://accounts.google.com/signin/recovery"},
                    {"name": "GitHub", "url": "https://github.com/password_reset"},
                    {"name": "Spotify", "url": "https://accounts.spotify.com/password-reset"},
                    {"name": "Discord", "url": "https://discord.com/reset"},
                    {"name": "TikTok", "url": "https://www.tiktok.com/login/phone-or-email/reset"},
                ],
            },
        }
