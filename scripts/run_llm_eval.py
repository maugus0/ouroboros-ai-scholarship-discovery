"""Run LLM-as-judge golden evaluation for scholarship discovery quality gates."""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.config import settings  # noqa: E402
from app.llm.openai_client import call_openai  # noqa: E402
from app.services.llm_service import LLMService  # noqa: E402

DEFAULT_CASES_PATH = ROOT_DIR / "tests" / "fixtures" / "llm_eval" / "golden_cases.json"
DEFAULT_OUTPUT_PATH = ROOT_DIR / "eval_results.json"

JUDGE_SYSTEM_PROMPT = """You are a strict LLM-as-judge evaluator for a scholarship discovery system.

Evaluate whether the actual extracted scholarship JSON correctly matches the expected JSON and rubric.
Focus on fields that affect downstream matching, eligibility filtering, ranking, and program linking.

Return only valid JSON with this schema:
{
  "score": number,
  "passed": boolean,
  "reasoning": string,
  "strengths": [string],
  "issues": [string]
}

Scoring rules:
- Score from 0 to 10.
- Award high scores for correct extraction of scholarship name, provider, funding, currency, deadline, eligibility criteria, mandatory criteria, optional preferences, degree level, field of study, nationality, and region.
- Penalize invented fields, missing mandatory eligibility details, wrong dates, wrong currency, wrong GPA thresholds, and confusing optional preferences with mandatory criteria.
- Do not require exact JSON formatting if the semantic content is correct.
- A case passes when score is 8.0 or higher.
"""


def _env_float(name: str, default: float) -> float:
    raw_value = os.getenv(name)
    if raw_value in (None, ""):
        return default

    try:
        return float(raw_value)
    except ValueError as exc:
        raise ValueError(f"{name} must be a float, got {raw_value!r}") from exc


def _load_cases(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Golden cases file not found: {path}")

    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError("Golden cases file must contain a JSON object")

    cases = data.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("Golden cases file must contain a non-empty 'cases' list")

    return data


def _write_results(path: Path, results: dict[str, Any]) -> None:
    path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")


def _build_judge_user_content(case: dict[str, Any], actual_output: dict[str, Any]) -> str:
    payload = {
        "case_id": case["id"],
        "case_description": case.get("description"),
        "input_text": case.get("input_text"),
        "source_url": case.get("source_url"),
        "expected_json": case.get("expected_json"),
        "quality_dimensions": case.get("quality_dimensions", []),
        "rubric": case.get("rubric", []),
        "actual_output": actual_output,
    }
    return json.dumps(payload, indent=2, ensure_ascii=False)


def _normalize_judge_result(raw_result: dict[str, Any], passing_score: float) -> dict[str, Any]:
    try:
        score = float(raw_result.get("score", 0.0))
    except (TypeError, ValueError):
        score = 0.0

    score = max(0.0, min(10.0, score))
    passed = bool(raw_result.get("passed", score >= passing_score))

    reasoning = raw_result.get("reasoning")
    if not isinstance(reasoning, str):
        reasoning = "Judge did not provide reasoning."

    strengths = raw_result.get("strengths")
    if not isinstance(strengths, list):
        strengths = []

    issues = raw_result.get("issues")
    if not isinstance(issues, list):
        issues = []

    return {
        "score": score,
        "passed": passed,
        "reasoning": reasoning,
        "strengths": [str(item) for item in strengths],
        "issues": [str(item) for item in issues],
    }


async def _run_extraction(case: dict[str, Any]) -> dict[str, Any]:
    service = LLMService()
    result = await service.extract_scholarship(
        page_text=case["input_text"],
        source_url=case.get("source_url", ""),
    )
    return result.extracted_data


async def _judge_case(
    case: dict[str, Any],
    actual_output: dict[str, Any],
    judge_model: str,
    passing_score: float,
) -> dict[str, Any]:
    judge_response = await call_openai(
        system_prompt=JUDGE_SYSTEM_PROMPT,
        user_content=_build_judge_user_content(case, actual_output),
        model=judge_model,
        temperature=0.0,
        max_tokens=1200,
    )
    return _normalize_judge_result(judge_response["content"], passing_score)


async def _evaluate_case(
    case: dict[str, Any],
    judge_model: str,
    passing_score: float,
) -> dict[str, Any]:
    started_at = time.perf_counter()

    try:
        actual_output = await _run_extraction(case)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return {
            "id": case.get("id"),
            "type": case.get("type"),
            "score": 0.0,
            "passed": False,
            "reasoning": f"Extraction failed before judge evaluation: {exc}",
            "strengths": [],
            "issues": ["Extraction call failed"],
            "actual_output": None,
            "latency_ms": int((time.perf_counter() - started_at) * 1000),
        }

    try:
        judge_result = await _judge_case(
            case=case,
            actual_output=actual_output,
            judge_model=judge_model,
            passing_score=passing_score,
        )
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return {
            "id": case.get("id"),
            "type": case.get("type"),
            "score": 0.0,
            "passed": False,
            "reasoning": f"Judge evaluation failed: {exc}",
            "strengths": [],
            "issues": ["Judge call failed"],
            "actual_output": actual_output,
            "latency_ms": int((time.perf_counter() - started_at) * 1000),
        }

    return {
        "id": case.get("id"),
        "type": case.get("type"),
        "score": judge_result["score"],
        "passed": judge_result["passed"],
        "reasoning": judge_result["reasoning"],
        "strengths": judge_result["strengths"],
        "issues": judge_result["issues"],
        "actual_output": actual_output,
        "latency_ms": int((time.perf_counter() - started_at) * 1000),
    }


async def run_eval() -> int:
    cases_path = Path(os.getenv("LLM_EVAL_CASES_PATH", str(DEFAULT_CASES_PATH)))
    output_path = Path(os.getenv("LLM_EVAL_OUTPUT_PATH", str(DEFAULT_OUTPUT_PATH)))
    judge_model = os.getenv("LLM_EVAL_MODEL", "gpt-4o-mini")
    baseline_score = _env_float("LLM_EVAL_BASELINE_SCORE", 8.0)
    allowed_drop = _env_float("LLM_EVAL_ALLOWED_DROP", 0.5)

    if not settings.OPENAI_API_KEY:
        results = {
            "task": "scholarship_discovery_quality_eval",
            "model": judge_model,
            "baseline_score": baseline_score,
            "allowed_drop": allowed_drop,
            "minimum_allowed_score": baseline_score - allowed_drop,
            "average_score": 0.0,
            "passed": False,
            "error": "OPENAI_API_KEY is not configured",
            "cases": [],
        }
        _write_results(output_path, results)
        return 1

    fixture = _load_cases(cases_path)
    scoring_scale = fixture.get("scoring_scale", {})
    passing_score = float(scoring_scale.get("passing_score", 8.0))

    case_results = []
    for case in fixture["cases"]:
        print(f"Evaluating {case['id']}...")
        case_results.append(
            await _evaluate_case(
                case=case,
                judge_model=judge_model,
                passing_score=passing_score,
            )
        )

    average_score = (
        sum(case_result["score"] for case_result in case_results) / len(case_results)
        if case_results
        else 0.0
    )
    minimum_allowed_score = baseline_score - allowed_drop
    passed = average_score >= minimum_allowed_score

    results = {
        "task": fixture.get("task", "scholarship_discovery_quality_eval"),
        "model": judge_model,
        "baseline_score": baseline_score,
        "allowed_drop": allowed_drop,
        "minimum_allowed_score": minimum_allowed_score,
        "average_score": round(average_score, 3),
        "passed": passed,
        "case_count": len(case_results),
        "cases": case_results,
    }

    _write_results(output_path, results)

    print(f"Average score: {average_score:.3f}")
    print(f"Minimum allowed score: {minimum_allowed_score:.3f}")
    print(f"Evaluation passed: {passed}")

    return 0 if passed else 1


def main() -> int:
    try:
        return asyncio.run(run_eval())
    except Exception as exc:  # pylint: disable=broad-exception-caught
        output_path = Path(os.getenv("LLM_EVAL_OUTPUT_PATH", str(DEFAULT_OUTPUT_PATH)))
        baseline_score = _env_float("LLM_EVAL_BASELINE_SCORE", 8.0)
        allowed_drop = _env_float("LLM_EVAL_ALLOWED_DROP", 0.5)
        fallback_results = {
            "task": "scholarship_discovery_quality_eval",
            "model": os.getenv("LLM_EVAL_MODEL", "gpt-4o-mini"),
            "baseline_score": baseline_score,
            "allowed_drop": allowed_drop,
            "minimum_allowed_score": baseline_score - allowed_drop,
            "average_score": 0.0,
            "passed": False,
            "error": str(exc),
            "cases": [],
        }
        _write_results(output_path, fallback_results)
        print(f"LLM evaluation failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
