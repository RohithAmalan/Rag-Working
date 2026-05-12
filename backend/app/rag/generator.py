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


def _structured_lookup_answer(question: str, context: str, source_types: set[str]) -> str | None:
    """Return explicit field-value output for ID/phone lookup questions."""
    if not (source_types & {"csv", "excel"}):
        return None

    q = question.lower()
    wants_lookup = any(token in q for token in ["customer id", "id", "phone", "mobile", "number"])
    if not wants_lookup:
        return None

    fields = _parse_structured_row(context)
    if not fields:
        return None

    first_name = fields.get("first name", "unknown")
    last_name = fields.get("last name", "unknown")
    customer_id = fields.get("customer id", "unknown")
    phone_1 = fields.get("phone 1", "unknown")
    phone_2 = fields.get("phone 2", "unknown")

    q_digits = _normalize_digits(question)
    if q_digits:
        p1_digits = _normalize_digits(phone_1)
        p2_digits = _normalize_digits(phone_2)
        matches_phone = (
            (q_digits and p1_digits and q_digits in p1_digits)
            or (q_digits and p2_digits and q_digits in p2_digits)
        )
        if any(t in q for t in ["phone", "mobile", "number"]) and not matches_phone:
            return None

    id_token = re.search(r"\b[0-9A-Za-z]{6,}\b", question)
    if "id" in q and id_token:
        requested_id = id_token.group(0).lower()
        if customer_id != "unknown" and requested_id != customer_id.lower():
            return None

    lines = [
        f"Customer Id: {customer_id}",
        f"First Name: {first_name}",
        f"Last Name: {last_name}",
    ]
    if any(t in q for t in ["phone", "mobile", "number"]):
        if phone_1 != "unknown":
            lines.append(f"Phone 1: {phone_1}")
        if phone_2 != "unknown":
            lines.append(f"Phone 2: {phone_2}")
    return "\n".join(lines)


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
        raise RuntimeError(f"Groq API call failed: {str(e)}") from e
