from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "how",
    "i",
    "in",
    "is",
    "it",
    "me",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "tell",
    "what",
    "where",
    "who",
    "with",
    "details",
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
    customer_name = (
        fields.get("customername", "").strip()
        or fields.get("customer name", "").strip()
    )

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
    return {
        token for token in re.findall(r"[a-z0-9]+", _humanize_key(key).lower()) if token
    }


def _value_tokens(value: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]+", value.lower()) if token}


def _humanize_key(key: str) -> str:
    key = re.sub(r"([a-z])([A-Z])", r"\1 \2", key)
    key = key.replace("_", " ").replace("-", " ")
    compact_suffixes = [
        "id",
        "name",
        "date",
        "type",
        "method",
        "price",
        "cost",
        "status",
        "number",
        "location",
        "manager",
    ]
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


def _structured_record_answer(
    question: str, context: str, source_types: set[str]
) -> str | None:
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

    task_keys = ["task name", "task", "project management tracker", "project", "ticket"]
    assigned_keys = ["assigned to", "owner", "assignee"]

    def _get_by_key_candidates(row: dict[str, str], candidates: list[str]) -> str:
        for candidate in candidates:
            if candidate in row and row[candidate].strip():
                return row[candidate].strip()
        return ""

    # Relation query: "what task is assigned for Gabriel"
    if (
        "task" in q
        and "assigned" in q
        and any(token in q for token in ["for", "to", "of"])
    ):
        q_tokens = {
            token
            for token in re.findall(r"[a-z0-9]+", q)
            if token and token not in STOPWORDS
        }
        for row in rows:
            assigned_val = _get_by_key_candidates(row, assigned_keys)
            task_val = _get_by_key_candidates(row, task_keys)
            if not assigned_val or not task_val:
                continue
            assigned_tokens = {
                token for token in re.findall(r"[a-z0-9]+", assigned_val.lower())
            }
            if q_tokens & assigned_tokens:
                return f"Task: {task_val}\nAssigned To: {assigned_val}"

    # Relation query: "Ticket Resolution task was assigned to whom"
    if "assigned" in q and any(token in q for token in ["whom", "who"]):
        q_tokens = {
            token
            for token in re.findall(r"[a-z0-9]+", q)
            if token and token not in STOPWORDS
        }
        best_match: tuple[int, str, str] | None = None
        for row in rows:
            task_val = _get_by_key_candidates(row, task_keys)
            assigned_val = _get_by_key_candidates(row, assigned_keys)
            if not task_val or not assigned_val:
                continue
            task_tokens = {
                token for token in re.findall(r"[a-z0-9]+", task_val.lower())
            }
            overlap = len(q_tokens & task_tokens)
            if overlap > 0 and (best_match is None or overlap > best_match[0]):
                best_match = (overlap, task_val, assigned_val)

        if best_match is not None:
            _, task_val, assigned_val = best_match
            return f"Task: {task_val}\nAssigned To: {assigned_val}"

    def _row_numeric(row: dict[str, str], keys: list[str]) -> float | None:
        for key in keys:
            raw = row.get(key)
            if not raw:
                continue
            cleaned = re.sub(r"[^0-9.\-]", "", str(raw))
            if not cleaned:
                continue
            try:
                return float(cleaned)
            except ValueError:
                continue
        return None

    def _to_float(raw: str | None) -> float | None:
        if raw is None:
            return None
        cleaned = re.sub(r"[^0-9.\-]", "", str(raw))
        if not cleaned:
            return None
        try:
            return float(cleaned)
        except ValueError:
            return None

    asks_rank = any(
        token in q for token in ["highest", "max", "top", "lowest", "minimum", "min"]
    )
    metric_candidates: list[tuple[str, list[str]]] = [
        ("Total Price", ["total price", "totalprice", "total revenue", "revenue"]),
        ("Unit Price", ["unit price", "unitprice", "price"]),
        ("Profit", ["profit"]),
        ("Quantity", ["quantity"]),
    ]
    metric = None
    for label, keys in metric_candidates:
        if any(key in q for key in keys):
            metric = (label, keys)
            break

    # Schema-agnostic metric inference: choose the best numeric column by question-key overlap.
    if asks_rank and metric is None:
        query_tokens = _question_tokens(question)
        numeric_keys: dict[str, int] = {}
        for row in rows:
            for key, value in row.items():
                if _to_float(value) is not None:
                    numeric_keys[key] = numeric_keys.get(key, 0) + 1

        if numeric_keys:

            def _metric_score(key: str) -> int:
                key_tokens = _key_tokens(key)
                score = len(query_tokens & key_tokens) * 4

                # Synonym-aware boosts for common business metrics.
                has_price_intent = any(
                    tok in query_tokens
                    for tok in {"price", "cost", "amount", "revenue", "total"}
                )
                has_unit_intent = "unit" in query_tokens
                has_profit_intent = "profit" in query_tokens
                has_qty_intent = any(tok in query_tokens for tok in {"qty", "quantity"})

                if has_price_intent and (
                    "price" in key_tokens
                    or "amount" in key_tokens
                    or "revenue" in key_tokens
                    or "cost" in key_tokens
                ):
                    score += 3
                if has_unit_intent and "unit" in key_tokens:
                    score += 3
                if has_profit_intent and "profit" in key_tokens:
                    score += 4
                if has_qty_intent and "quantity" in key_tokens:
                    score += 4

                # Prefer keys that are numeric in more rows.
                score += min(numeric_keys.get(key, 0), 3)
                return score

            best_key = max(numeric_keys.keys(), key=_metric_score)
            if _metric_score(best_key) > 0:
                metric = (_humanize_key(best_key), [best_key])

    if asks_rank and metric is not None:
        metric_label, metric_keys = metric
        ranked_rows = [(row, _row_numeric(row, metric_keys)) for row in rows]
        ranked_rows = [(row, value) for row, value in ranked_rows if value is not None]
        if ranked_rows:
            wants_lowest = any(token in q for token in ["lowest", "minimum", "min"])
            ranked_rows.sort(key=lambda item: item[1], reverse=not wants_lowest)

            top_n_match = re.search(r"\btop\s+(\d+)\b", q)
            top_n = int(top_n_match.group(1)) if top_n_match else 1
            top_n = max(1, min(top_n, 10))

            if top_n > 1:
                selected = ranked_rows[:top_n]
                lines: list[str] = []
                for idx, (row, value) in enumerate(selected, start=1):
                    name = (
                        _record_display_name(row)
                        or row.get("customer name")
                        or row.get("customername")
                        or "Unknown"
                    )
                    order_id = row.get("order id") or row.get("orderid")
                    product = row.get("product name") or row.get("product")
                    salesperson = row.get("salesperson")
                    detail_parts = [f"{idx}. {name} - {metric_label}: {value:g}"]
                    if order_id:
                        detail_parts.append(f"Order ID: {order_id}")
                    if product:
                        detail_parts.append(f"Product: {product}")
                    if salesperson:
                        detail_parts.append(f"Salesperson: {salesperson}")
                    lines.append(" | ".join(detail_parts))
                return f"Top {metric_label.lower()} records:\n" + "\n".join(lines)

            best_row, best_value = ranked_rows[0]
            best_name = (
                _record_display_name(best_row)
                or best_row.get("customer name")
                or best_row.get("customername")
            )
            order_id = best_row.get("order id") or best_row.get("orderid")
            product = best_row.get("product name") or best_row.get("product")
            salesperson = best_row.get("salesperson")

            detail_lines = [f"{metric_label}: {best_value:g}"]
            if best_name:
                detail_lines.insert(0, f"Customer Name: {best_name}")
            if order_id:
                detail_lines.append(f"Order ID: {order_id}")
            if product:
                detail_lines.append(f"Product Name: {product}")
            if salesperson:
                detail_lines.append(f"Salesperson: {salesperson}")
            return "\n".join(detail_lines)

    asks_who = "who" in q or "name" in q
    asks_plural = any(
        phrase in q for phrase in ["who are all", "which are all", "list all", "all "]
    )

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
        summary = _format_key_value_summary(
            first_row, ["first name", "last name", "email"]
        )
        if summary:
            return summary

    if any(token in q for token in ["phone", "mobile", "number"]):
        summary = _format_key_value_summary(
            first_row, ["first name", "last name", "phone", "phone 1", "phone 2"]
        )
        if summary:
            return summary

    return None


def _structured_lookup_answer(
    question: str, context: str, source_types: set[str]
) -> str | None:
    """Return dynamic field-value output for any structured row schema."""
    if not (source_types & {"csv", "excel"}):
        return None

    q_lower = question.lower()
    if any(
        token in q_lower
        for token in ["list", "all", "which are all", "who are all", "names of all"]
    ):
        return None
    if "task" in q_lower and "assigned" in q_lower:
        return None
    if ("unit price" in q_lower or "price" in q_lower) and any(
        token in q_lower
        for token in ["highest", "max", "top", "lowest", "minimum", "min"]
    ):
        return None

    skip_fields = {
        "lookup keywords",
        "id lookup",
        "raw row mapping",
        "record details",
        "data row from",
    }

    q_tokens = _question_tokens(question)
    id_candidates = _extract_identifier_candidates(question)
    asks_all = any(
        token in question.lower()
        for token in ["detail", "details", "all", "everything", "full", "extract"]
    )

    # Parse ALL rows and find the specific matching row (not just the first)
    all_rows = _parse_structured_rows(context)
    if not all_rows:
        return None

    if id_candidates:
        # Search every row for the requested ID — return the first match
        matching_row: dict[str, str] | None = None
        for row in all_rows:
            value_norms = [_normalize_alnum(v) for v in row.values()]
            if any(cand in norm for cand in id_candidates for norm in value_norms):
                matching_row = row
                break
        if matching_row is None:
            return None  # ID not in any retrieved chunk
        fields = matching_row
    else:
        fields = all_rows[0]

    display_fields = {
        key: value
        for key, value in fields.items()
        if key not in skip_fields
        and value
        and value.strip()
        and value.strip().lower() != "unknown"
    }

    if not display_fields:
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


def _list_all_records_answer(
    question: str, context: str, source_types: set[str]
) -> str | None:
    """Format 'list all' queries as structured bullet points showing multiple records."""
    if not (source_types & {"csv", "excel"}):
        return None

    q_lower = question.lower()

    # Detect "list all" type queries - must explicitly ask for ALL/multiple items
    # Don't trigger on single record queries like "list details about X" or "show the order X"
    explicit_list_all = any(
        phrase in q_lower
        for phrase in [
            "list all",
            "show all",
            "who are all",
            "which are all",
            "all the ",
            "all ",
        ]
    )
    has_singular_indicators = any(
        word in q_lower
        for word in [
            "detail",
            "details",
            "about",
            "for",
            "of ",
            "id",
            "order",
            "customer",
        ]
    )

    # Only treat as list query if explicitly asks for "all" AND not asking about specific item
    is_list_query = explicit_list_all and not has_singular_indicators

    if not is_list_query:
        return None

    rows = _parse_structured_rows(context)
    if not rows:
        return None

    # Limit to reasonable number of results
    max_records = min(len(rows), 20)
    rows = rows[:max_records]

    # Determine which fields to display based on the question
    q_tokens = _question_tokens(question)

    # Common important fields to prioritize
    priority_fields = [
        "product name",
        "product",
        "customer name",
        "customername",
        "first name",
        "last name",
        "order id",
        "orderid",
        "salesperson",
        "sales person",
        "region",
        "category",
        "unit price",
        "unitprice",
        "total price",
        "totalprice",
        "quantity",
        "date",
    ]

    # Build display for each record
    lines = []
    for idx, row in enumerate(rows, start=1):
        # Skip internal fields
        skip_fields = {
            "lookup keywords",
            "id lookup",
            "raw row mapping",
            "record details",
            "data row from",
        }

        # Get display name if available
        display_name = _record_display_name(row)

        # Collect relevant fields
        record_fields: dict[str, str] = {}
        for key, value in row.items():
            if key in skip_fields or not value or value.strip().lower() == "unknown":
                continue
            record_fields[key] = value.strip()

        if not record_fields:
            continue

        # Score fields by relevance to question
        scored_items: list[tuple[int, str, str]] = []
        for key, value in record_fields.items():
            score = 0

            # Boost if key matches question tokens
            key_tokens = _key_tokens(key)
            if key_tokens & q_tokens:
                score += 5

            # Boost priority fields
            if key.lower() in priority_fields:
                score += 3

            # Boost name-like fields
            if any(
                name_part in key.lower()
                for name_part in ["name", "customer", "product"]
            ):
                score += 2

            scored_items.append((score, key, value))

        # Sort by score and select top fields
        scored_items.sort(key=lambda x: (-x[0], x[1]))
        top_fields = scored_items[:8]  # Show up to 8 most relevant fields

        # Format record as bullet point
        if display_name:
            record_line = f"{idx}. {display_name}"
        elif "product" in record_fields or "product name" in record_fields:
            product = record_fields.get("product name") or record_fields.get(
                "product", "Unknown Product"
            )
            record_line = f"{idx}. {product}"
        else:
            record_line = f"{idx}. Record {idx}"

        # Add key details inline
        detail_parts = []
        for _, key, value in top_fields[:5]:  # Show top 5 inline
            if key.lower() not in [
                "first name",
                "last name",
                "customer name",
                "customername",
                "product",
                "product name",
            ]:
                detail_parts.append(f"{_humanize_key(key)}: {value}")

        if detail_parts:
            record_line += " | " + " | ".join(detail_parts)

        lines.append(record_line)

    if not lines:
        return None

    # Determine what we're listing
    list_subject = "records"
    if "product" in q_lower:
        list_subject = "products"
    elif "customer" in q_lower:
        list_subject = "customers"
    elif "order" in q_lower:
        list_subject = "orders"
    elif "salesperson" in q_lower or "sales" in q_lower:
        list_subject = "sales records"

    header = f"Found {len(lines)} {list_subject}:\n"
    return header + "\n".join(lines)


def _clean_context_for_llm(context: str) -> str:
    """Strip raw chunk metadata markers so the LLM only sees clean field facts."""
    # Extract the semantic 'This record shows ...' sections from each chunk
    record_matches = re.findall(
        r"This record shows\s+(.*?)(?:\s+Record details:|\s+Raw row mapping:|$)",
        context,
        re.IGNORECASE | re.DOTALL,
    )
    if record_matches:
        parts = [m.strip().rstrip(".") for m in record_matches if m.strip()]
        return "\n\n".join(parts)
    # Fallback for PDFs or plain text — strip known metadata prefixes
    cleaned = re.sub(r"Business data row from [^\n.]+\.\s*", "", context)
    cleaned = re.sub(r"Record details:[^\n]*\n?", "", cleaned)
    cleaned = re.sub(r"Raw row mapping:[^\n]*\n?", "", cleaned)
    cleaned = re.sub(r"Lookup keywords:[^\n]*\n?", "", cleaned)
    return cleaned.strip()


def _build_system_prompt(source_types: set[str]) -> str:
    if source_types & {"csv", "excel"}:
        return (
            "You are a strict data analyst assistant. Answer ONLY using the provided context records. "
            "Present facts cleanly — format field names properly (e.g. 'Order ID', 'Customer Name'). "
            "DO NOT reproduce metadata markers such as 'Record details:', 'Business data row from', "
            "'Raw row mapping:', 'Lookup keywords:', or '|' delimiters from the raw data. "
            "If asked about a specific record, answer ONLY about that record. "
            "Use bullet points for multiple items. "
            "If the requested information is not in the context, say 'I don't know based on the uploaded data.'"
        )

    if source_types == {"pdf"}:
        return (
            "You are a helpful RAG assistant working with PDF documents. "
            "Answer questions based on the provided context from the document. "
            "Extract the most relevant information and present it clearly. "
            "If the context contains the answer, provide it directly and concisely. "
            "Only say 'I don't know based on the uploaded data' if the context truly does not contain relevant information."
        )

    return STRICT_SYSTEM_PROMPT + " Prefer structured sources when available."


def _extractive_fallback_answer(
    question: str, context: str, source_types: set[str] | None = None
) -> str:
    """Return a best-effort answer from retrieved context without external LLM."""
    if not context.strip():
        return "I don't know based on the uploaded data."

    # Split context into simple candidate sentences.
    candidates = [
        s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", context) if s.strip()
    ]
    if not candidates:
        return "I don't know based on the uploaded data."

    source_types = source_types or set()
    tokens = {
        token
        for token in re.findall(r"\w+", question.lower())
        if token not in STOPWORDS
    }
    if not tokens:
        return candidates[0]

    best = ""
    best_score = -1
    for sentence in candidates:
        s_tokens = {
            token
            for token in re.findall(r"\w+", sentence.lower())
            if token not in STOPWORDS
        }
        overlap = tokens & s_tokens
        score = len(overlap)
        if source_types & {"csv", "excel"} and sentence.lower().startswith(
            "this record shows"
        ):
            score += 2
        if score > best_score:
            best_score = score
            best = sentence

    if source_types & {"csv", "excel"}:
        match = re.search(
            r"This record shows\s+(.*?)(?:\s+Record details:|\s+Raw row mapping:|$)",
            context,
            re.IGNORECASE | re.DOTALL,
        )
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

    # Short-circuit for pre-computed aggregate results (avg/sum/count fast path)
    agg_match = re.match(
        r"Computed result:\s+(.+?)\s+=\s+([\d.]+)\s+\(based on (\d+) records\)",
        context.strip(),
    )
    if agg_match:
        label, value, count = agg_match.group(1), agg_match.group(2), agg_match.group(3)
        return f"{label}: {float(value):.2f}  (computed from {count} records)"

    # For PDF-only queries, skip structured parsing and go straight to LLM
    if source_types == {"pdf"}:
        if not groq_api_key:
            raise ValueError("GROQ_API_KEY is required for answer generation.")

        logger.debug("PDF-only query detected, using LLM directly")
        return _llm_generate(question, context, groq_api_key, groq_model, source_types)

    # Try list all records first (for "list all X" queries with CSV/Excel)
    list_answer = _list_all_records_answer(question, context, source_types)
    if list_answer:
        return list_answer

    # Try structured lookup (for single record queries)
    structured_answer = _structured_lookup_answer(question, context, source_types)
    if structured_answer:
        return structured_answer

    # Try record-based answer (for ranking queries)
    record_answer = _structured_record_answer(question, context, source_types)
    if record_answer:
        return record_answer

    # Fall back to LLM for everything else
    if not groq_api_key:
        raise ValueError("GROQ_API_KEY is required for answer generation.")

    return _llm_generate(question, context, groq_api_key, groq_model, source_types)


def _llm_generate(
    question: str,
    context: str,
    groq_api_key: str,
    groq_model: str,
    source_types: set[str],
) -> str:
    """Call Groq LLM to generate answer from context."""
    try:
        from groq import Groq
    except ImportError as e:
        raise ImportError(
            "groq package not installed. Install with: pip install groq"
        ) from e

    try:
        logger.debug(
            f"Calling Groq API: model={groq_model}, source_types={source_types}"
        )
        client = Groq(api_key=groq_api_key, timeout=30.0)

        # Clean context to remove raw chunk metadata before sending to LLM
        clean_ctx = _clean_context_for_llm(context)

        id_candidates = _extract_identifier_candidates(question)
        id_hint = ""
        if id_candidates:
            id_hint = f" Answer ONLY about the record whose identifier matches '{question.strip()}'. Ignore all other records."

        # Build appropriate prompt based on source type
        user_prompt = f"Context:\n{clean_ctx}\n\nQuestion: {question}\n"
        if source_types & {"csv", "excel"}:
            user_prompt += (
                f"{id_hint} "
                "Give a single clean answer — do NOT repeat the same data in multiple formats. "
                "For one record: list each field on its own line as 'Field: Value'. "
                "For multiple records: use a numbered list. "
                "Do NOT echo raw chunk text or metadata markers."
            )
        else:
            user_prompt += "Answer clearly and concisely based on the context provided."

        response: Any = client.chat.completions.create(
            model=groq_model,
            temperature=0,
            timeout=30.0,
            messages=[
                {"role": "system", "content": _build_system_prompt(source_types)},
                {"role": "user", "content": user_prompt},
            ],
        )
        answer = (
            response.choices[0].message.content
            or "I don't know based on the uploaded data."
        )
        logger.debug(f"Groq response: {answer[:100]}...")
        return answer
    except Exception as e:
        logger.error(f"Groq API error: {type(e).__name__}: {str(e)}")
        fallback_answer = _extractive_fallback_answer(question, context, source_types)
        if fallback_answer:
            return fallback_answer
        raise RuntimeError(f"Groq API call failed: {str(e)}") from e
