"""Benchmark framework for GBM Gene Analysis.

The framework distinguishes three temporal modes:

- ``current_behavior_regression``: confirms known present-day scientific/output behavior.
- ``frozen_snapshot``: valid retrospective evaluation using evidence frozen at a declared date.
- ``prospective``: predictions or hypotheses registered before later experimental evaluation.

A live API query is never labeled retrospective simply because the target was
discovered earlier. True retrospective claims require frozen or date-bounded
evidence inputs.

Live-source expectations may include a ``when`` condition. If the prerequisite
source is unavailable, the check is reported as ``not_evaluable`` and excluded
from pass/fail accuracy. This prevents upstream outages from being mislabeled as
scientific regressions while still preserving the biological expectation when
the source is available.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

DEFAULT_MANIFEST = Path(__file__).resolve().parents[1] / "data" / "benchmark_manifest.json"
VALID_MODES = {"current_behavior_regression", "frozen_snapshot", "prospective"}
VALID_CASE_CLASSES = {"known_positive", "known_negative", "context_specific"}


def _path(obj: Any, dotted: str):
    current = obj
    for part in dotted.split("."):
        if isinstance(current, dict):
            current = current.get(part)
        else:
            current = getattr(current, part, None)
        if current is None:
            return None
    return current


def _compare(value, operator: str, expected) -> bool:
    if operator == "exists":
        return value is not None
    if operator == "eq":
        return value == expected
    if operator == "ne":
        return value != expected
    if value is None:
        return False
    try:
        left = float(value)
        right = float(expected)
    except (TypeError, ValueError):
        return False
    if operator == "gte":
        return left >= right
    if operator == "lte":
        return left <= right
    if operator == "gt":
        return left > right
    if operator == "lt":
        return left < right
    raise ValueError(f"Unsupported benchmark operator: {operator}")


def _validate_condition(condition: Any) -> None:
    if condition is None:
        return
    if not isinstance(condition, dict) or not condition.get("path"):
        raise ValueError("Benchmark expectation when condition must be an object with a path.")
    operator = condition.get("operator", "exists")
    if operator not in {"exists", "eq", "ne", "gte", "lte", "gt", "lt"}:
        raise ValueError(f"Unsupported benchmark condition operator: {operator}")


def load_manifest(path: Path = DEFAULT_MANIFEST) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict) or not isinstance(data.get("cases"), list):
        raise ValueError("Benchmark manifest must contain a cases list.")
    for case in data["cases"]:
        mode = case.get("mode")
        case_class = case.get("case_class")
        if mode not in VALID_MODES:
            raise ValueError(f"Invalid benchmark mode: {mode}")
        if case_class not in VALID_CASE_CLASSES:
            raise ValueError(f"Invalid benchmark case_class: {case_class}")
        if mode == "frozen_snapshot" and not case.get("evidence_freeze_date"):
            raise ValueError("frozen_snapshot benchmark cases require evidence_freeze_date.")
        if not isinstance(case.get("expectations"), list) or not case["expectations"]:
            raise ValueError(f"Benchmark case {case.get('id')} must contain expectations.")
        for expectation in case["expectations"]:
            if not expectation.get("path"):
                raise ValueError(f"Benchmark case {case.get('id')} contains an expectation without a path.")
            _validate_condition(expectation.get("when"))
    return data


def evaluate_case(profile, case: dict) -> dict:
    mode = case.get("mode")
    case_class = case.get("case_class")
    if mode not in VALID_MODES:
        raise ValueError(f"Invalid benchmark mode: {mode}")
    if case_class not in VALID_CASE_CLASSES:
        raise ValueError(f"Invalid benchmark case_class: {case_class}")
    if mode == "frozen_snapshot" and not case.get("evidence_freeze_date"):
        raise ValueError("frozen_snapshot benchmark cases require evidence_freeze_date.")

    payload = profile.to_dict() if hasattr(profile, "to_dict") else profile
    checks = []
    for expectation in case.get("expectations", []):
        path = expectation["path"]
        condition = expectation.get("when")
        if condition is not None:
            condition_value = _path(payload, condition["path"])
            condition_met = _compare(
                condition_value,
                condition.get("operator", "exists"),
                condition.get("value"),
            )
            if not condition_met:
                checks.append({
                    "path": path,
                    "observed": _path(payload, path),
                    "operator": expectation.get("operator", "exists"),
                    "expected": expectation.get("value"),
                    "status": "not_evaluable",
                    "passed": None,
                    "rationale": expectation.get("rationale"),
                    "not_evaluable_reason": expectation.get(
                        "not_evaluable_reason",
                        f"Prerequisite {condition['path']} was not satisfied.",
                    ),
                    "prerequisite": {
                        "path": condition["path"],
                        "observed": condition_value,
                        "operator": condition.get("operator", "exists"),
                        "expected": condition.get("value"),
                    },
                })
                continue

        value = _path(payload, path)
        passed = _compare(value, expectation.get("operator", "exists"), expectation.get("value"))
        checks.append({
            "path": path,
            "observed": value,
            "operator": expectation.get("operator", "exists"),
            "expected": expectation.get("value"),
            "status": "passed" if passed else "failed",
            "passed": passed,
            "rationale": expectation.get("rationale"),
        })

    evaluable = [x for x in checks if x["status"] != "not_evaluable"]
    not_evaluable = [x for x in checks if x["status"] == "not_evaluable"]
    passed_count = sum(bool(x["passed"]) for x in evaluable)
    failed_count = sum(x["passed"] is False for x in evaluable)
    case_passed = bool(evaluable) and failed_count == 0
    return {
        "id": case.get("id"),
        "gene": case.get("gene"),
        "case_class": case_class,
        "mode": mode,
        "temporal_validity": (
            "retrospective_valid" if mode == "frozen_snapshot"
            else "prospective_registered" if mode == "prospective"
            else "current_data_only_not_retrospective"
        ),
        "passed": case_passed,
        "fully_evaluable": len(not_evaluable) == 0,
        "passed_checks": passed_count,
        "failed_checks": failed_count,
        "evaluable_checks": len(evaluable),
        "not_evaluable_checks": len(not_evaluable),
        "total_checks": len(checks),
        "checks": checks,
    }


def run_benchmark(profile_builder: Callable[[str], Any], manifest_path: Path = DEFAULT_MANIFEST) -> dict:
    manifest = load_manifest(manifest_path)
    results = []
    profile_cache: dict[str, Any] = {}
    for case in manifest["cases"]:
        gene = str(case["gene"]).strip().upper()
        if gene not in profile_cache:
            profile_cache[gene] = profile_builder(gene)
        results.append(evaluate_case(profile_cache[gene], case))

    evaluable_total = sum(r["evaluable_checks"] for r in results)
    passed = sum(r["passed_checks"] for r in results)
    not_evaluable_total = sum(r["not_evaluable_checks"] for r in results)
    retrospective = [r for r in results if r["mode"] == "frozen_snapshot"]
    class_counts = {
        case_class: sum(r["case_class"] == case_class for r in results)
        for case_class in sorted(VALID_CASE_CLASSES)
    }
    source_limited = [r for r in results if not r["fully_evaluable"]]
    return {
        "benchmark_version": manifest.get("benchmark_version"),
        "cases": results,
        "n_cases": len(results),
        "n_unique_genes": len(profile_cache),
        "case_class_counts": class_counts,
        "check_accuracy": None if evaluable_total == 0 else round(passed / evaluable_total, 4),
        "evaluable_checks": evaluable_total,
        "not_evaluable_checks": not_evaluable_total,
        "fully_evaluable_cases": len(results) - len(source_limited),
        "source_limited_cases": len(source_limited),
        "all_evaluable_cases_passed": all(r["passed"] for r in results),
        "n_retrospective_cases": len(retrospective),
        "retrospective_claim_allowed": bool(retrospective) and all(r["passed"] for r in retrospective),
        "warning": (
            "Current-behavior cases validate scientific safeguards and regression behavior. "
            "Live-source checks whose prerequisites are unavailable are reported as not evaluable, never as passes. "
            "These cases are not evidence that the system would have predicted historical discoveries before publication."
        ),
    }
