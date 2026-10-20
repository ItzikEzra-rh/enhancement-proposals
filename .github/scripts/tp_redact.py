"""Redact credential-shaped substrings before untrusted text is published.

Model responses and provider metadata are untrusted data. Everything
derived from them — verdict fields, plan revisions, error messages — is
redacted before it is written to an artifact, printed, posted as a PR
comment, or published as a check summary. Redaction is a bound, not a
guarantee: it removes common credential shapes so a leaked secret cannot
survive publication.

Scope: internal hostnames and generic "customer data" are deliberately
not redacted. Test plans legitimately cite service hostnames such as
fulfillment-service.osac.svc and cluster API URLs, and there is no
reliable shape for customer data; redacting them would destroy review
feedback.
"""

import re

REDACTED = "<REDACTED>"

# Each rule is (pattern, replacement). Whole-value rules replace the entire
# match; keyed rules keep the key and separator and replace only the value.
# Replacements may be strings (with group references) or callables that
# return the replacement. PEM markers are assembled by concatenation so
# secret scanners do not flag this source file as containing a key.
_PEM_BEGIN = "-----BEGIN " + "[A-Z0-9 ]*PRIVATE KEY-----"
_PEM_END = "-----END " + "[A-Z0-9 ]*PRIVATE KEY-----"


def _luhn(digits):
    """Return True when the digit string passes the Luhn checksum."""
    total = 0
    for index, digit in enumerate(reversed(digits)):
        value = int(digit)
        if index % 2:
            value = value * 2 - 9 if value > 4 else value * 2
        total += value
    return total % 10 == 0


def _redact_card(match):
    """Redact a 13-19 digit group only when it is Luhn-valid.

    Two gates keep identifiers, SHAs, timestamps, dates and other plan
    digit runs readable: every separator-delimited group must hold at
    least three digits (card layouts are 4-4-4-4, 4-6-5, 4-3-3-3;
    dates are 4-2-2), and the checksum must pass — a random number
    rarely does.
    """
    text = match.group(0)
    groups = re.split(r"[ -]", text)
    if any(len(group) < 3 for group in groups):
        return text
    digits = "".join(groups)
    return REDACTED if 13 <= len(digits) <= 19 and _luhn(digits) else text


_RULES = (
    # Private-key PEM blocks of any key type.
    (re.compile(_PEM_BEGIN + r".*?" + _PEM_END, re.DOTALL), REDACTED),
    # Authorization header values, only when credential-shaped: an auth
    # scheme (case-insensitive) followed by an opaque value, or a single
    # opaque token of at least 20 characters. Prose after the key is
    # left readable so review feedback like "Authorization: requires
    # Cloud Provider Admin role" survives.
    (re.compile(
        r"(?i)(\bauthorization\b[\"']?\s*[:=]\s*[\"']?)"
        r"(?:((?:bearer|basic|token|digest|negotiate|aws4-hmac-sha256)\s+)"
        r"[A-Za-z0-9._~+/=-]{8,}"
        r"|[A-Za-z0-9._~+/=-]{20,})"),
     r"\1\2" + REDACTED),
    # Bearer tokens.
    (re.compile(r"(?i)(\bbearer\s+)[A-Za-z0-9._~+/=-]{20,}"),
     r"\1" + REDACTED),
    # GitHub tokens: classic ghp_/gho_/ghu_/ghs_/ghr_ and fine-grained PATs.
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36}\b"), REDACTED),
    (re.compile(r"\bgit" + r"hub_pat_[A-Za-z0-9_]{22,}\b"), REDACTED),
    # AWS access key IDs.
    (re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"), REDACTED),
    # Google API keys.
    (re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"), REDACTED),
    # Slack tokens.
    (re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}\b"), REDACTED),
    # JWTs: two base64url segments starting with the JSON marker, a dot,
    # and a third segment.
    (re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}"
                r"\.[A-Za-z0-9_-]*"), REDACTED),
    # US Social Security Numbers, excluding the invalid area/group/serial
    # combinations. Any 3-2-4 digit group passing those exclusions is
    # redacted even if it could be a phone number: over-redacting that
    # exact format is safer than leaking a real SSN.
    (re.compile(r"\b(?!000|666|9\d\d)\d{3}-(?!00)\d{2}-(?!0000)\d{4}\b"),
     REDACTED),
    # Payment card numbers, 13-19 digits with optional space or dash
    # separators, only when Luhn-valid (see _redact_card).
    (re.compile(r"\b(?:\d[ -]?){12,18}\d\b"), _redact_card),
    # Cookie header values: keep the header name and the first cookie
    # name, redact the value up to the next pair or end of line.
    (re.compile(
        r"(?i)((?:\bset-?cookie\b|\bcookie\b)[\"']?\s*[:=]\s*[\"']?"
        r"[A-Za-z0-9_.-]+=)[^;\r\n]+"),
     r"\1" + REDACTED),
    # Sensitive key/value assignments in YAML, JSON, env or kubeconfig
    # syntax. An optional identifier prefix covers keys like ACCESS_TOKEN,
    # db_password, authToken or session_id; the keyword must remain the
    # final word before the separator, so prose like "the access token is
    # rotated" or "password field is masked" does not match. Only the
    # value is replaced; the key stays readable.
    (re.compile(
        r"(?i)\b([A-Za-z0-9_-]*(?:password|passwd|secret|token|api[_-]?key|"
        r"client[_-]secret|aws[_-]secret[_-]access[_-]key|"
        r"session[_-]?id|sessionid|sid|csrf[_-]?token|"
        r"client[_-]key[_-]data|client[_-]certificate[_-]data|"
        r"certificate[_-]authority[_-]data))"
        r"\b([\"']?\s*[:=]\s*[\"']?)[^\s,;\"'}]+"),
     r"\1\2" + REDACTED),
    # Email addresses.
    (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
     REDACTED),
)


def redact(text):
    """Replace credential-shaped substrings with a fixed marker."""
    text = str(text)
    for pattern, replacement in _RULES:
        text = pattern.sub(replacement, text)
    return text


def redact_json(value):
    """Recursively redact the string values of parsed JSON data.

    Object keys are left untouched: they are structural names validated by
    consumers, and redacting them could break downstream lookups.
    """
    if isinstance(value, str):
        return redact(value)
    if isinstance(value, list):
        return [redact_json(item) for item in value]
    if isinstance(value, dict):
        return {key: redact_json(item) for key, item in value.items()}
    return value
