from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "how",
    "i", "in", "is", "it", "me", "of", "on", "or", "that", "the", "this",
    "to", "tell", "what", "where", "who", "with", "details",
}


STRICT_SYSTEM_PROMPT = (
    "You are a strict RAG assistant. Answer ONLY using the provided context. "
    "If the answer is not available, say 'I don't know based on the uploaded data.'"
)


def _normalize_digits(text: str) -> str:
    return "".join(ch for ch in text if ch.isdigit())


def _parse_structured_row(context: str) -> dict[str, str]:
    """Parse the first structured CSV/Excel row from context into a field map."""
    match = re.search(
        r"This record shows\s+(.*?)(?:\s+Record details:|\s+Raw row mapping:|$)",
        context,
        re.IGNORECASE | re.DOTALL,
    )
    if not match:
        return {}

    field_map: dict[str, str] = {}
    facts = [part.strip() for part in match.group(1).split(",") if part.strip()]
    for fact in facts:
        if " is " not in fact:
            continue
        key, value = fact.split(" is ", 1)
        field_map[key.strip().lower()] = value.strip().strip(".")
    return field_map


def _parse_structured_rows(context: str) -> list[dict[str, str]]:
    """Parse all structured CSV/Excel rows from context into field maps."""
    matches = re.findall(
        r"This record shows\s+(.*?)(?:\s+Record details:|\s+Raw row mapping:|$)",
        context,
        re.IGNORECASE | re.DOTALL,
    )

    rows: list[dict[str, str]] = []
    for match in matches:
        field_map: dict[str, str] = {}
        facts = [part.strip() for part in match.split(",") if part.strip()]
        for fact in facts:
            if " is " not in fact:
                continue
            key, value = fact.split(" is ", 1)
            field_map[key.strip().lower()] = value.strip().strip(".")
        if field_map:
            rows.append(field_map)
    return rows


def _record_display_name(fields: dict[str, str]) -> str | None:
    first_name = fields.get("first name", "").strip()
    last_name = fields.get("last name", "").strip()
    customer_name = fields.get("customername", "").strip() or fields.get("customer name", "").strip()

    if first_name or last_name:
        return " ".join(part for part in [first_name, last_name] if part).strip()
    if customer_name:
        return customer_name
    return None


def _format_key_value_summary(fields: dict[str, str], keys: list[str]) -> str | None:
    lines: list[str] = []
    for key in keys:
        value = fields.get(key)
        if value and value.lower() != "unknown":
            lines.append(f"{key.title()}: {value}")
    return "\n".join(lines) if lines else None


def _normalize_alnum(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.lower())


def _question_tokens(question: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", question.lower())
        if token not in STOPWORDS and len(token) > 1
    }


def _key_tokens(key: str) -> set[str]:
    # Tokenize after key humanization to support compact keys like paymentmethod.
    return {token for token in re.findall(r"[a-z0-9]+", _humanize_key(key).lower()) if token}


def _value_tokens(value: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]+", value.lower()) if token}


def _humanize_key(key: str) -> str:
    key = re.sub(r"([a-z])([A-Z])", r"\1 \2", key)
    key = key.replace("_", " ").replace("-", " ")
    compact_suffixes = ["id", "name", "date", "type", "method", "price", "cost", "status", "number", "location", "manager"]
    compact = key.replace(" ", "")
    if " " not in key:
        for suffix in compact_suffixes:
            if compact.lower().endswith(suffix) and len(compact) > len(suffix):
                key = compact[: -len(suffix)] + " " + suffix
                break
    return " ".join(part.capitalize() for part in key.split())


def _extract_identifier_candidates(question: str) -> list[str]:
    candidates: list[str] = []
    raw_tokens = re.findall(r"\b[A-Za-z0-9'_-]{4,}\b", question)
    for token in raw_tokens:
        if not any(ch.isdigit() for ch in token):
            continue
        normalized = _normalize_alnum(token)
        if len(normalized) >= 4:
            candidates.append(normalized)
    return list(dict.fromkeys(candidates))


def _structured_record_answer(question: str, context: str, source_types: set[str]) -> str | None:
    """Return concise deterministic answers for structured CSV/Excel queries."""
    if not (source_types & {"csv", "excel"}):
        return None

    rows = _parse_structured_rows(context)
    if not rows:
        return None

    q = question.lower()
    first_row = rows[0]
    display_name = _record_display_name(first_row)
    job_title = first_row.get("job title", "").strip()

    asks_who = "who" in q or "name" in q
    asks_plural = any(phrase in q for phrase in ["who are all", "which are all", "list all", "all "])

    if asks_who and asks_plural:
        names: list[str] = []
        seen: set[str] = set()
        for row in rows:
            name = _record_display_name(row)
            if not name:
                continue
            key = name.lower()
            if key not in seen:
                seen.add(key)
                names.append(name)

        if names:
            if "customer" in q:
                return "Customers: " + ", ".join(names)
            return "Matches: " + ", ".join(names)

    if asks_who and display_name:
        if job_title and any(token in q for token in ["manager", "title", "job"]):
            return f"{display_name} is the {job_title}."
        return display_name

    if "job title" in q or "designation" in q or "role" in q:
        if display_name and job_title:
            return f"{display_name} - {job_title}"

    if any(token in q for token in ["email", "mail"]):
        summary = _format_key_value_summary(first_row, ["first name", "last name", "email"])
        if summary:
            return summary

    if any(token in q for token in ["phone", "mobile", "number"]):
        summary = _format_key_value_summary(first_row, ["first name", "last name", "phone", "phone 1", "phone 2"])
        if summary:
            return summary

    return None


def _structured_lookup_answer(question: str, context: str, source_types: set[str]) -> str | None:
    """Return dynamic field-value output for any structured row schema."""
    if not (source_types & {"csv", "excel"}):
        return None

    fields = _parse_structured_row(context)
    if not fields:
        return None

    skip_fields = {
        "lookup keywords",
        "id lookup",
        "raw row mapping",
        "record details",
        "data row from",
    }
    display_fields = {
        key: value
        for key, value in fields.items()
        if key not in skip_fields and value and value.strip() and value.strip().lower() != "unknown"
    }

    if not display_fields:
        return None

    q_tokens = _question_tokens(question)
    id_candidates = _extract_identifier_candidates(question)
    asks_all = any(token in question.lower() for token in ["detail", "details", "all", "everything", "full", "extract"])

    if id_candidates:
        value_norms = [_normalize_alnum(value) for value in display_fields.values()]
        if not any(candidate in value_norm for candidate in id_candidates for value_norm in value_norms):
            return None

    scored_fields: list[tuple[int, str, str]] = []
    for key, value in display_fields.items():
        key_match = len(_key_tokens(key) & q_tokens)
        value_match = len(_value_tokens(value) & q_tokens)
        score = (key_match * 3) + value_match

        key_norm = _normalize_alnum(_humanize_key(key))
        score += sum(2 for token in q_tokens if token in key_norm)

        value_norm = _normalize_alnum(value)
        if any(candidate in value_norm for candidate in id_candidates):
            score += 6

        scored_fields.append((score, key, value))

    scored_fields.sort(key=lambda item: (-item[0], item[1]))

    if asks_all:
        selected = scored_fields[:12]
    else:
        selected = [item for item in scored_fields if item[0] > 0][:8]
        if not selected:
            selected = scored_fields[:6]

    lines = [f"{_humanize_key(key)}: {value}" for _, key, value in selected]
    return "\n".join(lines) if lines else None


def _build_system_prompt(source_types: set[str]) -> str:
    if source_types & {"csv", "excel"}:
        return (
            "You are a strict RAG assistant working with structured business records. "
            "Answer ONLY from the provided context. When the context comes from CSV or Excel rows, "
            "present the answer clearly as field-value details and avoid repeating raw row-mapping text. "
            "If the answer is not available, say 'I don't know based on the uploaded data.'"
        )

    if source_types == {"pdf"}:
        return STRICT_SYSTEM_PROMPT + " Prefer the most direct sentence from the document."

    return STRICT_SYSTEM_PROMPT + " Prefer structured sources when available."


def _extractive_fallback_answer(question: str, context: str, source_types: set[str] | None = None) -> str:
    """Return a best-effort answer from retrieved context without external LLM."""
    if not context.strip():
        return "I don't know based on the uploaded data."

    # Split context into simple candidate sentences.
    candidates = [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", context) if s.strip()]
    if not candidates:
        return "I don't know based on the uploaded data."

    source_types = source_types or set()
    tokens = {token for token in re.findall(r"\w+", question.lower()) if token not in STOPWORDS}
    if not tokens:
        return candidates[0]

    best = ""
    best_score = -1
    for sentence in candidates:
        s_tokens = {token for token in re.findall(r"\w+", sentence.lower()) if token not in STOPWORDS}
        overlap = tokens & s_tokens
        score = len(overlap)
        if source_types & {"csv", "excel"} and sentence.lower().startswith("this record shows"):
            score += 2
        if score > best_score:
            best_score = score
            best = sentence

    if source_types & {"csv", "excel"}:
        match = re.search(r"This record shows\s+(.*?)(?:\s+Raw row mapping:|$)", context, re.IGNORECASE | re.DOTALL)
        if match:
            structured_answer = match.group(1).strip().rstrip(".")
            return structured_answer + "."

    return best if best_score > 0 else candidates[0]


def generate_answer(
    question: str,
    context: str,
    groq_api_key: str,
    groq_model: str,
    source_types: set[str] | None = None,
) -> str:
    """Generate answer using Groq API (required). Raises on missing/invalid credentials."""
    source_types = source_types or set()

    structured_answer = _structured_lookup_answer(question, context, source_types)
    if structured_answer:
        return structured_answer

    record_answer = _structured_record_answer(question, context, source_types)
    if record_answer:
        return record_answer

    if not groq_api_key:
        raise ValueError("GROQ_API_KEY is required for answer generation.")

    try:
        from groq import Groq
    except ImportError as e:
        raise ImportError("groq package not installed. Install with: pip install groq") from e

    try:
        logger.debug(f"Calling Groq API: model={groq_model}, source_types={source_types}")
        client = Groq(api_key=groq_api_key, timeout=30.0)
        response: Any = client.chat.completions.create(
            model=groq_model,
            temperature=0,
            timeout=30.0,
            messages=[
                {"role": "system", "content": _build_system_prompt(source_types)},
                {
                    "role": "user",
                    "content": (
                        f"Context:\n{context}\n\nQuestion: {question}\n"
                        "Respond with a direct answer and do not add outside assumptions."
                    ),
                },
            ],
        )
        answer = response.choices[0].message.content or "I don't know based on the uploaded data."
        logger.debug(f"Groq response: {answer[:100]}...")
        return answer
    except Exception as e:
        logger.error(f"Groq API error: {type(e).__name__}: {str(e)}")
        fallback_answer = _extractive_fallback_answer(question, context, source_types)
        if fallback_answer:
            return fallback_answer
        raise RuntimeError(f"Groq API call failed: {str(e)}") from e
