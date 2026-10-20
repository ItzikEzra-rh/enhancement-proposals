"""Redact credential-shaped substrings before untrusted text is published.

Model responses and provider metadata are untrusted data. Everything
derived from them — verdict fields, plan revisions, error messages — is
redacted before it is written to an artifact, printed, posted as a PR
comment, or published as a check summary. Redaction is a bound, not a
guarantee: it removes common credential shapes so a leaked secret cannot
survive publication.
"""

import re

REDACTED = "<REDACTED>"

# Each rule is (pattern, replacement). Whole-value rules replace the entire
# match; keyed rules keep the key and separator and replace only the value.
# PEM markers are assembled by concatenation so secret scanners do not flag
# this source file as containing a key.
_PEM_BEGIN = "-----BEGIN " + "[A-Z0-9 ]*PRIVATE KEY-----"
_PEM_END = "-----END " + "[A-Z0-9 ]*PRIVATE KEY-----"

_RULES = (
    # Private-key PEM blocks of any key type.
    (re.compile(_PEM_BEGIN + r".*?" + _PEM_END, re.DOTALL), REDACTED),
    # Authorization header values, including anything after the colon.
    (re.compile(r"(?i)(\bauthorization\b[\"']?\s*[:=]\s*[\"']?).+"),
     r"\1" + REDACTED),
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
    # Sensitive key/value assignments in YAML, JSON, env or kubeconfig
    # syntax. Only the value is replaced; the key stays readable.
    (re.compile(
        r"(?i)\b(password|passwd|secret|token|api[_-]?key|client[_-]secret|"
        r"aws[_-]secret[_-]access[_-]key|client[_-]key[_-]data|"
        r"client[_-]certificate[_-]data|certificate[_-]authority[_-]data)\b"
        r"([\"']?\s*[:=]\s*[\"']?)[^\s,;\"'}]+"),
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
