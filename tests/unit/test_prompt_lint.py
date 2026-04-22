"""Prompt lint tests for Scholarship Discovery Agent prompt templates."""

import json
import re
from pathlib import Path

import pytest

PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"
MAX_ESTIMATED_TOKENS = 2000
CHARS_PER_TOKEN_ESTIMATE = 4


def get_all_prompts():
    return sorted(PROMPTS_DIR.glob("*.json"))


def test_prompt_files_exist():
    assert get_all_prompts(), "No prompt JSON files found in prompts/"


@pytest.mark.parametrize("prompt_file", get_all_prompts())
def test_prompt_is_valid_json(prompt_file):
    """Prompt files must be valid JSON."""
    try:
        json.loads(prompt_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        pytest.fail(f"Invalid JSON in {prompt_file.name}: {exc}")


@pytest.mark.parametrize("prompt_file", get_all_prompts())
def test_prompt_structure_and_limits(prompt_file):
    """Prompt files must follow the expected schema and size limits."""
    content = prompt_file.read_text(encoding="utf-8")
    data = json.loads(content)

    assert "prompt_template" in data, f"Missing 'prompt_template' in {prompt_file.name}"
    assert isinstance(
        data["prompt_template"], dict
    ), f"'prompt_template' must be an object in {prompt_file.name}"

    assert "base" in data["prompt_template"], f"Missing 'base' in {prompt_file.name}"
    base = data["prompt_template"]["base"]
    assert isinstance(base, dict), f"'base' must be an object in {prompt_file.name}"

    assert isinstance(
        base.get("agent_identity"), dict
    ), f"Missing or invalid 'agent_identity' in {prompt_file.name}"
    assert isinstance(
        base.get("task_instructions"), dict
    ), f"Missing or invalid 'task_instructions' in {prompt_file.name}"
    assert isinstance(
        base.get("output_format"), dict
    ), f"Missing or invalid 'output_format' in {prompt_file.name}"

    output_format = base["output_format"]
    assert (
        output_format.get("format") == "json"
    ), f"Output format must be 'json' in {prompt_file.name}"
    assert (
        "schema" in output_format
    ), f"Output format must include a 'schema' in {prompt_file.name}"

    assert "runtime_context" not in base, (
        f"Prompt {prompt_file.name} should not hardcode 'runtime_context'. "
        "This is injected dynamically by prompt_utils.py."
    )

    estimated_tokens = len(content) // CHARS_PER_TOKEN_ESTIMATE
    assert estimated_tokens <= MAX_ESTIMATED_TOKENS, (
        f"Prompt {prompt_file.name} is too long: "
        f"estimated {estimated_tokens} tokens, limit is {MAX_ESTIMATED_TOKENS}"
    )


@pytest.mark.parametrize("prompt_file", get_all_prompts())
def test_prompt_no_legacy_placeholders(prompt_file):
    """
    Validate placeholders.

    This project injects dynamic data structurally through runtime_context JSON
    nodes, so brace-style string interpolation like {source_url} is unsupported.
    """
    data = json.loads(prompt_file.read_text(encoding="utf-8"))

    def check_no_placeholders_in_strings(obj):
        if isinstance(obj, dict):
            for value in obj.values():
                check_no_placeholders_in_strings(value)
        elif isinstance(obj, list):
            for item in obj:
                check_no_placeholders_in_strings(item)
        elif isinstance(obj, str):
            matches = sorted(
                set(re.findall(r"(?<!\{)\{([a-zA-Z_][a-zA-Z0-9_]*)\}(?!\})", obj))
            )
            assert not matches, (
                f"Unsupported placeholder(s) in {prompt_file.name}: {matches}. "
                f"Found in string: {obj!r}. "
                "This project uses structural runtime_context injection, "
                "not brace-style string interpolation."
            )

    check_no_placeholders_in_strings(data)
