"""Regex sanitization, stable-sequence, and incident-index functions."""
import re

# Email first, so an address such as "abcd1234567@x.se" is replaced as one
# email and not partly matched as a container identifier.
EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
SEAL_PATTERN = re.compile(r"\bSEAL-\d{6}\b", re.IGNORECASE)
CONTAINER_PATTERN = re.compile(r"\b[A-Za-z]{4}\d{7}\b")


def sanitize_text(text):
    """Replace container IDs, seal numbers and emails with placeholders.

    Everything else (punctuation, line breaks) is preserved. Returns
    (sanitized_text, number_of_substitutions); the text counts as changed
    when the number is greater than zero.
    """
    text, emails = EMAIL_PATTERN.subn("[EMAIL]", text)
    text, seals = SEAL_PATTERN.subn("[SEAL]", text)
    text, containers = CONTAINER_PATTERN.subn("[CONTAINER]", text)
    return text, emails + seals + containers
