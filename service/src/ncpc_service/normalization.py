import re
import unicodedata

_WHITESPACE = re.compile(r"\s+")


def normalize_text(value: str) -> str:
    text = unicodedata.normalize("NFKC", value).casefold().strip()
    return _WHITESPACE.sub(" ", text)


def normalize_barcode(value: str) -> str:
    """Preserve barcode semantics; only trim documented outer whitespace.

    Leading zeroes are significant and must never be removed. Symbology-specific
    canonicalisation requires a future reviewed rule and is intentionally absent.
    """

    normalized = unicodedata.normalize("NFKC", value).strip()
    if not normalized:
        raise ValueError("barcode must not be empty")
    if len(normalized) > 128:
        raise ValueError("barcode is too long")
    return normalized
