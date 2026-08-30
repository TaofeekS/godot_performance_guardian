from __future__ import annotations

import asyncio
import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

from agents import ModelBehaviorError, ModelSettings

from agent import investigator
from tools import run_agent_evaluation as evaluation


class FrozenPackageTests(unittest.TestCase):
    def test_integrity_and_ten_failure_packets(self) -> None:
        manifest = evaluation.verify_integrity()
        config, cases, prompts = evaluation.load_frozen_evaluation()
        self.assertEqual(manifest["hash_mode"], "sha256_utf8_lf")
        self.assertEqual(len(cases), 10)
        self.assertEqual(config["model_snapshot"], "gpt-4.1-mini-2025-04-14")
        self.assertEqual(config["output_token_split"], [256, 1744])
        self.assertEqual(set(prompts), {"typed", "free_form"})
        self.assertTrue(all(evaluation.failed_rule_ids(case["packet"]) for case in cases))

    def test_alternating_order_is_frozen(self) -> None:
        config, _cases, _prompts = evaluation.load_frozen_evaluation()
        for index, item in enumerate(config["execution_order"], start=1):
            expected = ["free_form", "typed"] if index % 2 else ["typed", "free_form"]
            self.assertEqual(item["variants"], expected)

    def test_integrity_detects_substantive_change(self) -> None:
        original = evaluation._normalized_text_bytes
        with patch.object(evaluation, "_normalized_text_bytes", side_effect=lambda path: original(path) + (b"changed" if path == evaluation.CASES_PATH else b"")):
            with self.assertRaises(evaluation.AgentEvaluationError):
                evaluation.verify_integrity()


class CostAndBoundTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config, self.cases, self.prompts = evaluation.load_frozen_evaluation()
        self.rates = self.config["rate_card_usd_per_million_tokens"]

    def test_observed_cost_handles_cached_tokens(self) -> None:
        cost = evaluation.observed_request_cost(1000, 250, 500, self.rates)
        self.assertAlmostEqual(cost, (750 * .4 + 250 * .1 + 500 * 1.6) / 1_000_000)

    def test_cached_tokens_cannot_exceed_input(self) -> None:
        with self.assertRaises(evaluation.AgentEvaluationError):
            evaluation.observed_request_cost(1, 2, 0, self.rates)

    def test_conservative_bound_prices_all_input_uncached(self) -> None:
        bound = evaluation.conservative_input_bound(
            config=self.config,
            case=self.cases[0],
            prompt=self.prompts["typed"],
            variant="typed",
        )
        self.assertGreater(bound, self.config["protocol_input_margin_tokens"])
        expected = (bound * .4 + 2000 * 1.6) / 1_000_000
        self.assertAlmostEqual(evaluation.conservative_next_cost(bound, self.config), expected)


class GroundingEvaluationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        _config, cls.cases, _prompts = evaluation.load_frozen_evaluation()

    def test_every_fallback_is_grounded_and_actionable(self) -> None:
        for case in self.cases:
            report = investigator.render_deterministic_fallback(case["packet"])
            self.assertEqual(evaluation.evaluation_grade(report, case["packet"]), [])

    def test_missing_failed_fact_and_generic_recommendation_fail(self) -> None:
        case = self.cases[0]
        report = investigator.render_deterministic_fallback(case["packet"])
        failed = evaluation.failed_rule_ids(case["packet"])[0]
        marker = "## Verified facts"
        prefix, facts = report.split(marker, 1)
        report = prefix + marker + facts.replace(f"[{failed}]", "[missing]", 1)
        errors = evaluation.evaluation_grade(report, case["packet"])
        self.assertIn("G02_UNKNOWN_EVIDENCE", errors)
        self.assertIn("E02_FAILED_RULE_FACT_MISSING", errors)

    def test_typed_renderer_is_metric_specific(self) -> None:
        case = self.cases[0]
        failed = evaluation.failed_rule_ids(case["packet"])[0]
        contribution = investigator.InvestigatorContribution.model_validate({
            "hypotheses": [],
            "recommendations": [{"action": "compare", "evidence_ids": [failed]}],
        })
        report = investigator.render_model_contribution(case["packet"], contribution)
        self.assertIn("profile main_scene metric median_p95_process_time", report)
        self.assertEqual(evaluation.evaluation_grade(report, case["packet"]), [])

    def test_typed_schema_accepts_five_recommendations_and_rejects_six(self) -> None:
        valid = {"hypotheses": [], "recommendations": [{"action": "compare", "evidence_ids": ["R1_1"]}] * 5}
        investigator.InvestigatorContribution.model_validate(valid)
        invalid = copy.deepcopy(valid)
        invalid["recommendations"].append({"action": "inspect", "evidence_ids": ["R1_1"]})
        with self.assertRaises(Exception):
            investigator.InvestigatorContribution.model_validate(invalid)


class TwoTurnModelTests(unittest.TestCase):
    def test_enforces_exact_token_split_and_blocks_third_request(self) -> None:
        responses = [object(), object()]
        delegate = AsyncMock()
        delegate.get_response.side_effect = responses
        model = evaluation.TwoTurnModel(delegate, [256, 1744])

        async def invoke() -> None:
            await model.get_response(None, "first", ModelSettings(), [], None, [], None)
            await model.get_response(None, "second", ModelSettings(), [], None, [], None)
            with self.assertRaises(ModelBehaviorError):
                await model.get_response(None, "third", ModelSettings(), [], None, [], None)

        asyncio.run(invoke())
        self.assertEqual(delegate.get_response.call_args_list[0].args[2].max_tokens, 256)
        self.assertEqual(delegate.get_response.call_args_list[1].args[2].max_tokens, 1744)
        self.assertEqual(model.request_count, 2)

    def test_model_settings_disable_retries_and_storage(self) -> None:
        config, _cases, _prompts = evaluation.load_frozen_evaluation()
        settings = evaluation._model_settings(config)
        self.assertFalse(settings.store)
        self.assertTrue(settings.include_usage)
        self.assertTrue(settings.preserve_raw_usage)
        self.assertEqual(settings.retry.max_retries, 0)
        self.assertEqual(settings.tool_choice, "required")


class ResultTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config, self.cases, _prompts = evaluation.load_frozen_evaluation()

    @staticmethod
    def usage() -> dict[str, object]:
        request = {"input_tokens": 10, "cached_input_tokens": 0, "output_tokens": 10, "total_tokens": 20, "estimated_cost_usd": 0.00002}
        return {"model_requests": 2, "input_tokens": 20, "cached_input_tokens": 0, "output_tokens": 20, "total_tokens": 40, "estimated_cost_usd": 0.00004, "requests": [request, request]}

    def complete_fallback_result(self) -> dict[str, object]:
        integrity = evaluation.verify_integrity()
        result = evaluation._base_result(self.config, integrity)
        for case in self.cases:
            report = investigator.render_deterministic_fallback(case["packet"])
            result["cases"].append({
                "case_id": case["id"],
                "title": case["title"],
                "failed_evidence_ids": evaluation.failed_rule_ids(case["packet"]),
                "runs": [
                    {"variant": variant, "direct_status": "rejected", "grader_rule_ids": ["E08_MODEL_BEHAVIOR"], "direct_report": None, "fallback_status": "grounded", "fallback_report": report, "rejected_report_sha256": "a" * 64, "accepted_actions": [], "agent_runs": 1, "tool_calls": 1, "latency_ms": 1.0, "usage": self.usage()}
                    for variant in ("typed", "free_form")
                ],
            })
        result["status"] = "complete"
        result["summary"] = evaluation.recompute_summary(result, self.config)
        result["headline"] = evaluation._headline(result["summary"])
        return result

    def test_summary_and_paired_outcomes_recompute(self) -> None:
        result = self.complete_fallback_result()
        self.assertEqual(result["summary"]["agent_runs"], 20)
        self.assertEqual(result["summary"]["paired_outcomes"]["both_failed"], 10)
        self.assertFalse(result["summary"]["success_criteria_met"])

    def test_verify_regrades_stored_reports_without_api(self) -> None:
        result = self.complete_fallback_result()
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "result.json"
            path.write_bytes(evaluation._canonical_bytes(result))
            with patch.dict(os.environ, {}, clear=True):
                self.assertEqual(evaluation.verify_result(path), 1)

    def test_atomic_write_refuses_collision_and_cleans_temp(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "result.json"
            evaluation._atomic_write(path, {"ok": True})
            with self.assertRaises(evaluation.AgentEvaluationError):
                evaluation._atomic_write(path, {"ok": False})
            self.assertEqual(list(Path(temporary).glob("*.tmp")), [])

    def test_missing_key_writes_incomplete_result_without_client(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "result.json"
            with patch.dict(os.environ, {}, clear=True), patch.object(evaluation, "AsyncOpenAI") as client:
                self.assertEqual(evaluation.run_live(path), 2)
            client.assert_not_called()
            stored = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(stored["status"], "incomplete")
            self.assertIsNone(stored["headline"])
            self.assertEqual(stored["incomplete_reason"], "missing_api_key")


if __name__ == "__main__":
    unittest.main()
