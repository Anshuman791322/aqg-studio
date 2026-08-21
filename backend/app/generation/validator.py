"""Validation rules and guards for AI-generated assessment questions."""

import re
import uuid
from typing import Any

from app.generation.schemas import GeneratedQuestionItem
from app.models.entities import QuestionBlueprint

BANNED_MCQ_PHRASES: list[re.Pattern[str]] = [
    re.compile(r"\ball of the above\b", re.IGNORECASE),
    re.compile(r"\ball of these\b", re.IGNORECASE),
    re.compile(r"\ball the above\b", re.IGNORECASE),
    re.compile(r"\bnone of the above\b", re.IGNORECASE),
    re.compile(r"\bnone of these\b", re.IGNORECASE),
    re.compile(r"\bnone the above\b", re.IGNORECASE),
    re.compile(r"\bboth a and b\b", re.IGNORECASE),
    re.compile(r"\bboth b and c\b", re.IGNORECASE),
    re.compile(r"\ball options are correct\b", re.IGNORECASE),
    re.compile(r"\bnone are correct\b", re.IGNORECASE),
]


def normalize_type(q_type: str) -> str:
    """Normalize question type alias."""
    t = q_type.lower().strip()
    return "mcq_single" if t == "mcq" else t


def validate_generated_question(
    item: GeneratedQuestionItem,
    blueprint: QuestionBlueprint,
    available_chunk_ids: set[uuid.UUID],
) -> tuple[bool, str | None]:
    """Validate a generated question against pedagogical requirements and blueprint constraints.

    Returns:
        (is_valid, error_reason)
    """
    # 1. Blueprint Match Verification
    if item.blueprint_id != blueprint.id:
        return False, f"Blueprint ID mismatch: expected {blueprint.id}, got {item.blueprint_id}"

    canonical_item_type = normalize_type(item.question_type)
    canonical_bp_type = normalize_type(blueprint.question_type)
    if canonical_item_type != canonical_bp_type:
        return (
            False,
            f"Question type mismatch: blueprint specifies '{canonical_bp_type}', got '{canonical_item_type}'",
        )

    if item.difficulty.lower() != blueprint.difficulty.lower():
        return (
            False,
            f"Difficulty mismatch: blueprint specifies '{blueprint.difficulty}', got '{item.difficulty}'",
        )

    if item.bloom_level.lower() != blueprint.bloom_level.lower():
        return (
            False,
            f"Bloom level mismatch: blueprint specifies '{blueprint.bloom_level}', got '{item.bloom_level}'",
        )

    # 2. Text & Explanation Cleanliness
    if not item.question_text or len(item.question_text.strip()) < 10:
        return False, "Question stem is too short or empty (minimum 10 characters required)."

    if not item.explanation or len(item.explanation.strip()) < 10:
        return False, "Explanation is too short or empty (minimum 10 characters required)."

    # 3. Grounding & Source Chunk Citations
    if not item.supporting_evidence or not item.supporting_evidence.source_chunk_ids:
        return False, "Supporting evidence must cite at least one valid source_chunk_id."

    for cid in item.supporting_evidence.source_chunk_ids:
        if cid not in available_chunk_ids:
            return (
                False,
                f"Cited source_chunk_id '{cid}' was not provided in the prompt context.",
            )

    if (
        not item.supporting_evidence.verbatim_excerpt
        or len(item.supporting_evidence.verbatim_excerpt.strip()) < 5
    ):
        return False, "Supporting evidence must include a non-empty verbatim excerpt from the source chunk."

    # 4. Type-Specific Validation Rules
    if canonical_item_type == "mcq_single":
        return _validate_mcq_single(item)
    elif canonical_item_type == "mcq_multi":
        return _validate_mcq_multi(item)
    elif canonical_item_type == "true_false":
        return _validate_true_false(item)
    elif canonical_item_type == "short_answer":
        return _validate_short_answer(item)
    elif canonical_item_type == "descriptive":
        return _validate_descriptive(item)

    return True, None


def _validate_mcq_single(item: GeneratedQuestionItem) -> tuple[bool, str | None]:
    """Validate Single-Select MCQ constraints."""
    if not item.options or len(item.options) != 4:
        return (
            False,
            f"Single-select MCQ must contain exactly 4 options, got {len(item.options) if item.options else 0}.",
        )

    # Option keys and texts
    keys: set[str] = set()
    texts: set[str] = set()

    for opt in item.options:
        k_clean = opt.key.strip().upper()
        t_clean = opt.text.strip().lower()

        if not t_clean:
            return False, f"Option '{opt.key}' text cannot be empty."

        # Check banned lazy distractor phrases
        for pattern in BANNED_MCQ_PHRASES:
            if pattern.search(t_clean):
                return (
                    False,
                    f"Option '{opt.key}' contains prohibited lazy phrase ('{pattern.pattern}').",
                )

        if k_clean in keys:
            return False, f"Duplicate option key '{opt.key}'."
        if t_clean in texts:
            return False, f"Duplicate option text: '{opt.text}'."

        keys.add(k_clean)
        texts.add(t_clean)

    # Validate Correct Answer Key
    ans_str = str(item.correct_answer).strip()
    ans_key_upper = ans_str.upper()
    valid_option_keys = {opt.key.strip().upper() for opt in item.options}
    valid_option_texts = {opt.text.strip().lower() for opt in item.options}

    if ans_key_upper in valid_option_keys:
        return True, None
    if ans_str.lower() in valid_option_texts:
        return True, None

    return (
        False,
        f"Correct answer '{item.correct_answer}' does not match any valid option key ({valid_option_keys}) or option text.",
    )


def _validate_mcq_multi(item: GeneratedQuestionItem) -> tuple[bool, str | None]:
    """Validate Multi-Select MCQ constraints."""
    if not item.options or len(item.options) < 4:
        return False, "Multi-select MCQ must contain at least 4 options."

    texts: set[str] = set()
    for opt in item.options:
        t_clean = opt.text.strip().lower()
        if not t_clean:
            return False, f"Option '{opt.key}' text cannot be empty."
        for pattern in BANNED_MCQ_PHRASES:
            if pattern.search(t_clean):
                return False, f"Option '{opt.key}' contains prohibited lazy phrase."
        if t_clean in texts:
            return False, f"Duplicate option text: '{opt.text}'."
        texts.add(t_clean)

    # Correct answer should contain 2 or more options
    ans = item.correct_answer
    if isinstance(ans, list) and len(ans) >= 2:
        return True, None
    if isinstance(ans, str) and ("," in ans or len(ans.split()) >= 2):
        return True, None

    return False, "Multi-select MCQ must specify 2 or more correct options."


def _validate_true_false(item: GeneratedQuestionItem) -> tuple[bool, str | None]:
    """Validate True/False constraints."""
    ans = item.correct_answer
    if isinstance(ans, bool):
        return True, None
    if isinstance(ans, str) and ans.strip().lower() in ("true", "false"):
        return True, None

    return False, f"True/False question correct_answer must be a boolean (True/False), got '{ans}'."


def _validate_short_answer(item: GeneratedQuestionItem) -> tuple[bool, str | None]:
    """Validate Short Answer constraints."""
    if item.correct_answer is None:
        return False, "Short answer question must provide a correct answer."

    ans_str = str(item.correct_answer).strip()
    if not ans_str or len(ans_str) < 1:
        return False, "Short answer correct_answer cannot be empty."

    if len(ans_str) > 500:
        return False, "Short answer expected response is too long (maximum 500 characters, avoid essays)."

    return True, None


def _validate_descriptive(item: GeneratedQuestionItem) -> tuple[bool, str | None]:
    """Validate Descriptive / Long Answer constraints."""
    if item.correct_answer is None:
        return False, "Descriptive question must provide a grading rubric or key concept points in correct_answer."

    ans_str = str(item.correct_answer).strip()
    if len(ans_str) < 10:
        return False, "Descriptive correct_answer rubric is too short (minimum 10 characters required)."

    return True, None


def format_options_for_db(item: GeneratedQuestionItem) -> list[dict[str, Any]] | None:
    """Format MCQ options into standard JSONB serializable format."""
    if not item.options:
        return None
    return [{"key": opt.key.strip().upper(), "text": opt.text.strip()} for opt in item.options]
