"""Benchmark framework for GBM Gene Analysis.

The framework distinguishes three modes:

- ``current_behavior_regression``: confirms known present-day scientific/output behavior.
- ``frozen_snapshot``: valid retrospective evaluation using evidence frozen at a declared date.
- ``prospective``: predictions/hypotheses registered before later experimental evaluation.

A live 2026 API query is never labeled retrospective simply because the target
was discovered earlier. True retrospective claims require frozen/date-bounded
evidence inputs.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

DEFAULT_MANIFEST = Path(__file__).resolve().parents[1] / "data" / "benchmark_manifest.json"
VALID_MODES = {"current_behavior_regression", "frozen_snapshot", "prospective"}


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


def load_manifest(path: Path = DEFAULT_MANIFEST) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict) or not isinstance(data.get("cases"), list):
        raise ValueError("Benchmark manifest must contain a cases list.")
    return data


def evaluate_case(profile, case: dict) -> dict:
    mode = case.get("mode")
    if mode not in VALID_MODES:
        raise ValueError(f"Invalid benchmark mode: {mode}")
    if mode == "frozen_snapshot" and not case.get("evidence_freeze_date"):
        raise ValueError("frozen_snapshot benchmark cases require evidence_freeze_date.")
    payload = profile.to_dict() if hasattr(profile, "to_dict") else profile
    checks = []
    for expectation in case.get("expectations", []):
        path = expectation["path"]
        value = _path(payload, path)
        passed = _compare(value, expectation.get("operator", "exists"), expectation.get("value"))
        checks.append({
            "path": path,
            "observed": value,
            "operator": expectation.get("operator", "exists"),
            "expected": expectation.get("value"),
            "passed": passed,
            "rationale": expectation.get("rationale"),
        })
    passed_count = sum(bool(x["passed"]) for x in checks)
    return {
        "id": case.get("id"),
        "gene": case.get("gene"),
        "mode": mode,
        "temporal_validity": (
            "retrospective_valid" if mode == "frozen_snapshot"
            else "prospective_registered" if mode == "prospective"
            else "current_data_only_not_retrospective"
        ),
        "passed": passed_count == len(checks),
        "passed_checks": passed_count,
        "total_checks": len(checks),
        "checks": checks,
    }


def run_benchmark(profile_builder: Callable[[str], Any], manifest_path: Path = DEFAULT_MANIFEST) -> dict:
    manifest = load_manifest(manifest_path)
    results = []
    for case in manifest["cases"]:
        profile = profile_builder(case["gene"])
        results.append(evaluate_case(profile, case))
    total = sum(r["total_checks"] for r in results)
    passed = sum(r["passed_checks"] for r in results)
    retrospective = [r for r in results if r["mode"] == "frozen_snapshot"]
    return {
        "benchmark_version": manifest.get("benchmark_version"),
        "cases": results,
        "n_cases": len(results),
        "check_accuracy": None if total == 0 else round(passed / total, 4),
        "n_retrospective_cases": len(retrospective),
        "retrospective_claim_allowed": bool(retrospective) and all(r["passed"] for r in retrospective),
        "warning": (
            "Current-behavior cases validate scientific safeguards and regression behavior. "
            "They are not evidence that the system would have predicted historical discoveries before publication."
        ),
    }
