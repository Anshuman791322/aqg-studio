"""Fast deterministic non-LLM validation and rule-checking engine for questions."""

import re
import uuid

from app.evaluation.schemas import DeterministicCheckResult
from app.models.entities import Question, QuestionBlueprint

# Prohibited lazy distractor patterns
BANNED_MCQ_PHRASES: list[re.Pattern[str]] = [
    re.compile(r"\ball\s+of\s+the\s+above\b", re.IGNORECASE),
    re.compile(r"\bnone\s+of\s+the\s+above\b", re.IGNORECASE),
    re.compile(r"\ball\s+of\s+these\b", re.IGNORECASE),
    re.compile(r"\bnone\s+of\s+these\b", re.IGNORECASE),
    re.compile(r"\bboth\s+[a-d]\s+and\s+[a-d]\b", re.IGNORECASE),
    re.compile(r"\ball\s+of\s+the\s+choices\b", re.IGNORECASE),
    re.compile(r"\bnone\s+of\s+the\s+choices\b", re.IGNORECASE),
    re.compile(r"\bneither\s+[a-d]\s+nor\s+[a-d]\b", re.IGNORECASE),
]

NORMALIZE_REGEX = re.compile(r"[^\w\s]", re.UNICODE)


def normalize_stem(text: str) -> str:
    """Normalize question stem for exact duplicate comparison."""
    no_punct = NORMALIZE_REGEX.sub(" ", text.lower())
    return " ".join(no_punct.split())


def validate_question_deterministic(
    question: Question,
    blueprint: QuestionBlueprint | None,
    available_chunk_ids: set[uuid.UUID],
    other_questions: list[Question] | None = None,
) -> DeterministicCheckResult:
    """Run rigorous non-generative pedagogical rule checks against a candidate question."""
    issues: list[str] = []
    rule_violations: list[str] = []
    critical_failure = False

    # 1. Stem and Explanation Length & Existence
    stem = (question.question_text or "").strip()
    if not stem:
        issues.append("Question stem text is missing or empty.")
        rule_violations.append("MISSING_STEM")
        critical_failure = True
    elif len(stem) < 10:
        issues.append("Question stem is too short (< 10 characters).")
        rule_violations.append("STEM_TOO_SHORT")
        critical_failure = True
    elif len(stem) > 2000:
        issues.append("Question stem is excessively long (> 2000 characters).")
        rule_violations.append("STEM_TOO_LONG")

    explanation = (question.explanation or "").strip()
    if not explanation:
        issues.append("Pedagogical explanation is missing.")
        rule_violations.append("MISSING_EXPLANATION")

    # 2. Source Chunk Grounding Provenance
    chunk_ids = list(question.source_chunk_ids or [])
    if not chunk_ids:
        issues.append("No source_chunk_ids cited for factual provenance.")
        rule_violations.append("MISSING_SOURCE_CHUNKS")
        critical_failure = True
    elif available_chunk_ids:
        unsupported_ids = [cid for cid in chunk_ids if cid not in available_chunk_ids]
        if unsupported_ids:
            issues.append(
                f"Question cites {len(unsupported_ids)} chunk ID(s) not found in the document: {unsupported_ids}."
            )
            rule_violations.append("HALLUCINATED_CHUNK_IDS")
            critical_failure = True

    # 3. Question Type & Option Rules
    q_type = question.question_type
    options_raw = question.options or []
    correct_ans = question.correct_answer

    if q_type == "mcq_single":
        if not isinstance(options_raw, list):
            issues.append("Options must be a list of option objects.")
            rule_violations.append("INVALID_OPTIONS_FORMAT")
            critical_failure = True
        else:
            if len(options_raw) != 4:
                issues.append(f"Single-select MCQ must have exactly 4 options; got {len(options_raw)}.")
                rule_violations.append("INVALID_OPTION_COUNT")
                critical_failure = True

            keys_found: set[str] = set()
            texts_found: set[str] = set()
            for opt in options_raw:
                if not isinstance(opt, dict):
                    continue
                k = str(opt.get("key", "")).strip().upper()
                t = str(opt.get("text", "")).strip()
                keys_found.add(k)
                norm_text = normalize_stem(t)

                if not t:
                    issues.append(f"Option {k} has empty text.")
                    rule_violations.append("EMPTY_OPTION_TEXT")
                    critical_failure = True

                if norm_text in texts_found:
                    issues.append(f"Duplicate option content detected: '{t}'.")
                    rule_violations.append("DUPLICATE_OPTION_TEXT")
                    critical_failure = True
                texts_found.add(norm_text)

                for pattern in BANNED_MCQ_PHRASES:
                    if pattern.search(t):
                        issues.append(
                            f"Option {k} contains prohibited lazy distractor phrase matching '{pattern.pattern}'."
                        )
                        rule_violations.append("PROHIBITED_MCQ_PHRASE")
                        critical_failure = True

            if keys_found != {"A", "B", "C", "D"}:
                issues.append(f"MCQ option keys must be exactly A, B, C, D; found: {sorted(keys_found)}.")
                rule_violations.append("INVALID_OPTION_KEYS")
                critical_failure = True

            # Verify correct answer matches an option key
            ans_str = str(correct_ans).strip().upper()
            if ans_str not in {"A", "B", "C", "D"}:
                issues.append(f"Correct answer '{correct_ans}' does not match any valid option key (A, B, C, D).")
                rule_violations.append("INVALID_CORRECT_ANSWER")
                critical_failure = True

    elif q_type == "mcq_multi":
        if not isinstance(options_raw, list) or len(options_raw) < 4:
            issues.append(f"Multi-select MCQ must have at least 4 options; got {len(options_raw)}.")
            rule_violations.append("INSUFFICIENT_MULTI_OPTIONS")
            critical_failure = True

        valid_keys = {str(opt.get("key", "")).strip().upper() for opt in options_raw if isinstance(opt, dict)}
        if isinstance(correct_ans, list):
            ans_keys = {str(k).strip().upper() for k in correct_ans}
            if len(ans_keys) < 2:
                issues.append("Multi-select MCQ must have at least 2 correct keys.")
                rule_violations.append("INSUFFICIENT_CORRECT_KEYS")
                critical_failure = True
            invalid_ans_keys = ans_keys - valid_keys
            if invalid_ans_keys:
                issues.append(f"Correct keys contain invalid options: {invalid_ans_keys}.")
                rule_violations.append("INVALID_CORRECT_ANSWER_KEYS")
                critical_failure = True
        else:
            issues.append("Multi-select MCQ correct_answer must be a list of keys.")
            rule_violations.append("INVALID_MULTI_ANSWER_TYPE")
            critical_failure = True

    elif q_type == "true_false":
        if isinstance(correct_ans, bool) or (
            isinstance(correct_ans, str) and correct_ans.strip().lower() in {"true", "false"}
        ):
            pass
        else:
            issues.append(f"True/False question correct_answer must be boolean True/False; got '{correct_ans}'.")
            rule_violations.append("INVALID_BOOLEAN_ANSWER")
            critical_failure = True

    elif q_type == "short_answer":
        ans_text = str(correct_ans or "").strip()
        if not ans_text:
            issues.append("Short answer model answer is empty.")
            rule_violations.append("EMPTY_SHORT_ANSWER")
            critical_failure = True
        elif len(ans_text) > 500:
            issues.append(f"Short answer model answer exceeds 500 characters ({len(ans_text)} chars).")
            rule_violations.append("SHORT_ANSWER_TOO_LONG")

    elif q_type == "descriptive":
        ans_text = str(correct_ans or "").strip()
        if not ans_text:
            issues.append("Descriptive question grading rubric/key answer is empty.")
            rule_violations.append("EMPTY_DESCRIPTIVE_RUBRIC")
            critical_failure = True

    # 4. Blueprint Parity
    if blueprint is not None:
        if question.question_type != blueprint.question_type:
            issues.append(
                f"Question type '{question.question_type}' diverges from blueprint '{blueprint.question_type}'."
            )
            rule_violations.append("QUESTION_TYPE_MISMATCH")
            critical_failure = True

        if question.difficulty != blueprint.difficulty:
            issues.append(
                f"Question difficulty '{question.difficulty}' does not match blueprint '{blueprint.difficulty}'."
            )
            rule_violations.append("DIFFICULTY_MISMATCH")

        if question.bloom_level != blueprint.bloom_level:
            issues.append(
                f"Question bloom_level '{question.bloom_level}' does not match blueprint '{blueprint.bloom_level}'."
            )
            rule_violations.append("BLOOM_LEVEL_MISMATCH")

    # 5. Exact Normalized Duplicate Detection
    if other_questions and stem:
        norm_current = normalize_stem(stem)
        for other_q in other_questions:
            if other_q.id == question.id:
                continue
            norm_other = normalize_stem(other_q.question_text or "")
            if norm_current == norm_other:
                issues.append(f"Exact normalized duplicate of question ID '{other_q.id}'.")
                rule_violations.append("EXACT_DUPLICATE_QUESTION")
                critical_failure = True
                break

    is_valid = len(issues) == 0
    return DeterministicCheckResult(
        is_valid=is_valid,
        critical_failure=critical_failure,
        issues=issues,
        rule_violations=rule_violations,
    )
