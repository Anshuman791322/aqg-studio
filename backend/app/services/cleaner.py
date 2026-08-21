"""Deterministic text normalization, dehyphenation, language detection, and token estimation."""

import hashlib
import math
import re

import tiktoken

# Cached tiktoken encoding
_tokenizer: tiktoken.Encoding | None = None
try:
    _tokenizer = tiktoken.get_encoding("cl100k_base")
except Exception:
    _tokenizer = None

# Common stopword profiles for lightweight fast language detection
STOPWORDS_BY_LANG: dict[str, set[str]] = {
    "en": {
        "the", "and", "is", "in", "to", "of", "that", "it", "with", "as", "for", "on", "are"
    },
    "es": {
        "el", "la", "de", "que", "y", "en", "un", "ser", "se", "no", "haber", "por", "con", "para"
    },
    "fr": {
        "le", "la", "de", "un", "les", "du", "en", "des", "est", "et", "dans", "pour", "par", "une"
    },
    "de": {
        "der", "die", "und", "in", "den", "von", "zu", "das", "mit", "sich", "des", "auf", "für"
    },
    "it": {
        "il", "la", "di", "che", "e", "in", "un", "per", "del", "non", "da", "con", "le", "si"
    },
    "pt": {
        "de", "a", "o", "que", "e", "do", "da", "em", "um", "para", "com", "não", "uma", "os", "no"
    },
}


def calculate_sha256(content: bytes | str) -> str:
    """Calculate SHA-256 hash of string or raw bytes."""
    if isinstance(content, str):
        content = content.encode("utf-8")
    return hashlib.sha256(content).hexdigest()


def normalize_whitespace(text: str) -> str:
    """Clean control characters, collapse redundant spaces, and normalize newlines."""
    if not text:
        return ""

    # Remove non-printable control characters except newline and tab
    cleaned = "".join(
        ch for ch in text
        if ch in ("\n", "\t", "\r") or (ord(ch) >= 32 and ord(ch) != 127)
    )

    # Normalize CRLF to LF
    cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n")

    # Collapse horizontal whitespace (multiple spaces/tabs to single space)
    cleaned = re.sub(r"[^\S\n]+", " ", cleaned)

    # Collapse excessive vertical whitespace (more than 2 consecutive newlines)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

    return cleaned.strip()


def dehyphenate_text(text: str) -> str:
    """Conservative dehyphenation merging words broken across line breaks."""
    if not text:
        return ""

    # Merge lowercase words hyphenated at line break: e.g. "pedagog-\nical" -> "pedagogical"
    dehyphenated = re.sub(r"(\b[a-zA-Z]{2,})-\n\s*([a-zA-Z]{2,}\b)", r"\1\2", text)

    return dehyphenated


def detect_language(text: str) -> str:
    """Lightweight deterministic language detector based on word frequency heuristics."""
    if not text or len(text.strip()) < 10:
        return "en"

    # Check for Devanagari script (Hindi, Sanskrit, Marathi)
    if any("\u0900" <= ch <= "\u097F" for ch in text[:500]):
        return "hi"

    # Check for CJK characters (Chinese, Japanese, Korean)
    if any("\u4E00" <= ch <= "\u9FFF" for ch in text[:500]):
        return "zh"

    # Tokenize lowercase words
    words = re.findall(r"\b[a-z]{2,}\b", text.lower())[:300]
    if not words:
        return "en"

    word_set = set(words)
    best_lang = "en"
    max_score = 0

    for lang, stopwords in STOPWORDS_BY_LANG.items():
        score = len(word_set.intersection(stopwords))
        if score > max_score:
            max_score = score
            best_lang = lang

    return best_lang if max_score > 0 else "en"


def estimate_tokens(text: str) -> int:
    """Accurately estimate token count using tiktoken (cl100k_base) or char ratio fallback."""
    if not text or not text.strip():
        return 0

    if _tokenizer is not None:
        try:
            return len(_tokenizer.encode(text))
        except Exception:
            pass

    # Fallback heuristic: ~3.8 characters per token in standard English
    char_len = len(text)
    words = len(text.split())
    return max(1, math.ceil(char_len / 3.8), math.ceil(words * 1.3))
