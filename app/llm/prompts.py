"""Prompt loading and building with runtime context injection.

Templates live under ``prompts/`` as versioned JSON. These helpers are
used by in-process code (e.g. ``LLMService``), not by HTTP clients.
"""

from typing import Any

from app.utils.prompt_utils import build_prompt_json, build_prompt_text

_VALID_FORMATS: frozenset[str] = frozenset({"json", "text"})


def _require_prompt_format(fmt: str) -> None:
    if fmt not in _VALID_FORMATS:
        raise ValueError(f"Unsupported prompt format {fmt!r}; expected one of {sorted(_VALID_FORMATS)}.")


def get_scholarship_extraction_prompt(
    context: dict[str, Any] | None = None,
    fmt: str = "json",
) -> str:
    """Build the scholarship-extraction system prompt."""
    _require_prompt_format(fmt)
    if fmt == "text":
        return build_prompt_text("scholarship_extraction_v1.json", context)
    return build_prompt_json("scholarship_extraction_v1.json", context)


def get_eligibility_parsing_prompt(
    context: dict[str, Any] | None = None,
    fmt: str = "json",
) -> str:
    """Build the eligibility-parsing system prompt."""
    _require_prompt_format(fmt)
    if fmt == "text":
        return build_prompt_text("eligibility_parsing_v1.json", context)
    return build_prompt_json("eligibility_parsing_v1.json", context)


def get_field_classification_prompt(
    context: dict[str, Any] | None = None,
    fmt: str = "json",
) -> str:
    """Build the field-classification system prompt."""
    _require_prompt_format(fmt)
    if fmt == "text":
        return build_prompt_text("field_classification_v1.json", context)
    return build_prompt_json("field_classification_v1.json", context)
