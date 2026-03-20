"""Resumable judge loop for per-control mapping result audits."""
import json
import re
from pathlib import Path
from typing import Any

from langchain_core.messages import SystemMessage
from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate

from src.prompts.judge_prompt import JUDGE_SYSTEM_PROMPT
from src.judge.judge_writer import write_judge_result
from src.mapping.chat.client import get_llm
from src.utils.logger import setup_logger


class JudgeLoop:
    """Run LLM QA judging over mapping result files with resumability."""

    def __init__(
        self,
        mapping_results_dir,
        judge_output_dir,
        internal_controls: list,
        external_catalog: list,
        llm_client,
        system_rules_summary: str,
        target_control_ids: set[str] | None = None,
    ) -> None:
        self.mapping_results_dir = Path(mapping_results_dir)
        self.judge_output_dir = Path(judge_output_dir)
        self.internal_controls = internal_controls
        self.external_catalog = external_catalog
        self.llm_client = llm_client or get_llm()
        self.system_rules_summary = system_rules_summary
        self.target_control_ids = target_control_ids
        self.logger = setup_logger("judge")

        self.internal_index = self._build_internal_index(internal_controls)
        self.external_index = self._build_external_index(external_catalog)
        self.external_catalog_summary = self._build_external_catalog_summary(external_catalog)

    @staticmethod
    def _build_internal_index(internal_controls: list[dict]) -> dict[str, dict]:
        index = {}
        for control in internal_controls:
            control_id = control.get("CCF ID") or control.get("internal_control_id") or control.get("id")
            if control_id:
                index[control_id] = control
        return index

    @staticmethod
    def _build_external_index(external_catalog: list[dict]) -> dict[str, dict]:
        index = {}
        for control in external_catalog:
            control_id = control.get("safeguard_id") or control.get("external_id") or control.get("id")
            if control_id:
                index[control_id] = control
        return index

    @staticmethod
    def _build_external_catalog_summary(external_catalog: list[dict]) -> list[dict]:
        summary = []
        for control in external_catalog:
            external_id = control.get("safeguard_id") or control.get("external_id") or control.get("id")
            if not external_id:
                continue
            summary.append({
                "id": external_id,
                "title": control.get("safeguard_title") or control.get("external_title") or control.get("title", ""),
                "description": control.get("safeguard_description") or control.get("external_description") or control.get("description", ""),
            })
        return summary

    @staticmethod
    def _coerce_judge_payload(payload: Any) -> dict | None:
        if isinstance(payload, dict):
            return payload
        return None

    @classmethod
    def _extract_json_object(cls, text: str) -> dict:
        try:
            parsed = cls._coerce_judge_payload(json.loads(text))
            if parsed is not None:
                return parsed
        except json.JSONDecodeError:
            pass

        for block in re.findall(r"```(?:json)?\s*(.*?)\s*```", text, flags=re.DOTALL | re.IGNORECASE):
            try:
                parsed = cls._coerce_judge_payload(json.loads(block))
                if parsed is not None:
                    return parsed
            except json.JSONDecodeError:
                continue

        decoder = json.JSONDecoder()
        for idx, char in enumerate(text):
            if char != "{":
                continue
            try:
                obj, _ = decoder.raw_decode(text[idx:])
                parsed = cls._coerce_judge_payload(obj)
                if parsed is not None:
                    return parsed
            except json.JSONDecodeError:
                continue

        excerpt = text.strip().replace("\n", " ")[:180]
        raise ValueError(f"Unable to extract judge JSON object from model output: {excerpt}")

    @classmethod
    def _parse_judge_response(cls, response: Any) -> dict:
        if isinstance(response, str):
            return cls._extract_json_object(response)

        content = getattr(response, "content", None)
        if isinstance(content, str):
            return cls._extract_json_object(content)

        if isinstance(content, list):
            text_parts = [part for part in content if isinstance(part, str)]
            if text_parts:
                return cls._extract_json_object("\n".join(text_parts))

        raise ValueError(f"Unsupported LLM response type for parsing: {type(response).__name__}")

    def _build_mapped_results(self, mapping_payload: dict) -> list[dict]:
        mapped_results = []
        for mapping in mapping_payload.get("mappings", []):
            external_id = mapping.get("safeguard_id") or mapping.get("external_id") or mapping.get("id")
            external_control = self.external_index.get(external_id, {}) if external_id else {}
            mapped_results.append({
                "external_id": external_id,
                "external_title": external_control.get("safeguard_title") or external_control.get("external_title") or external_control.get("title", ""),
                "external_description": external_control.get("safeguard_description") or external_control.get("external_description") or external_control.get("description", ""),
                "mapping_type": mapping.get("mapping") or mapping.get("mapping_type"),
                "mapper_rationale": mapping.get("reason") or mapping.get("mapper_rationale", ""),
            })
        return mapped_results

    @staticmethod
    def _build_chain(llm):
        user_template = "{judge_payload}"
        judge_prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=JUDGE_SYSTEM_PROMPT),
            HumanMessagePromptTemplate.from_template(user_template),
        ])
        return judge_prompt | llm

    @staticmethod
    def _build_quarantined_fallback(internal_control_id: str, reason: str, recovery_hint: str) -> dict:
        return {
            "internal_control_id": internal_control_id,
            "overall_verdict": "QUARANTINED",
            "overall_confidence": 0.0,
            "overall_summary": "Mapping was quarantined due to judge stage processing failure.",
            "per_mapping_verdicts": [],
            "false_negatives": [],
            "quarantine_reason": reason,
            "recovery_hint": recovery_hint,
        }

    @staticmethod
    def _increment_summary(summary: dict, verdict: str | None) -> None:
        if verdict == "APPROVED":
            summary["approved"] += 1
        elif verdict == "APPROVED_WITH_WARNINGS":
            summary["approved_with_warnings"] += 1
        else:
            summary["quarantined"] += 1

    def run(self) -> dict:
        self.judge_output_dir.mkdir(parents=True, exist_ok=True)
        mapping_files = sorted(self.mapping_results_dir.glob("*.json"))
        if self.target_control_ids is not None:
            mapping_files = [
                file_path
                for file_path in mapping_files
                if file_path.stem in self.target_control_ids
            ]
        summary = {
            "total": len(mapping_files),
            "approved": 0,
            "approved_with_warnings": 0,
            "quarantined": 0,
        }

        chain = self._build_chain(self.llm_client)

        for idx, mapping_file in enumerate(mapping_files, 1):
            with open(mapping_file, "r") as f:
                mapping_payload = json.load(f)

            internal_control_id = mapping_payload.get("internal_control_id") or mapping_file.stem
            judge_path = self.judge_output_dir / f"{internal_control_id}_judge.json"

            if judge_path.exists():
                self.logger.info("[%s/%s] %s — judge result exists, skipping", idx, len(mapping_files), internal_control_id)
                with open(judge_path, "r") as f:
                    existing_result = json.load(f)
                self._increment_summary(summary, existing_result.get("overall_verdict"))
                continue

            internal_control = self.internal_index.get(internal_control_id)
            if not internal_control:
                self.logger.error("[%s/%s] %s — internal control not found", idx, len(mapping_files), internal_control_id)
                fallback = self._build_quarantined_fallback(
                    internal_control_id=internal_control_id,
                    reason="Internal control not found for judge input",
                    recovery_hint="Verify internal controls source and re-run judge for this control.",
                )
                write_judge_result(fallback, str(self.judge_output_dir))
                self._increment_summary(summary, fallback.get("overall_verdict"))
                continue

            user_payload = {
                "internal_control": internal_control,
                "mapped_results": self._build_mapped_results(mapping_payload),
                "system_rules_summary": self.system_rules_summary,
                "full_external_catalog": self.external_catalog_summary,
            }

            self.logger.info("[%s/%s] Judging %s", idx, len(mapping_files), internal_control_id)
            try:
                response = chain.invoke({"judge_payload": json.dumps(user_payload, indent=2)})
                judge_result = self._parse_judge_response(response)
            except Exception as exc:
                self.logger.error("Judge call failed for %s: %s", internal_control_id, exc)
                judge_result = self._build_quarantined_fallback(
                    internal_control_id=internal_control_id,
                    reason="Judge LLM returned unparseable response",
                    recovery_hint="Re-run judge for this control.",
                )

            judge_result.setdefault("internal_control_id", internal_control_id)
            write_judge_result(judge_result, str(self.judge_output_dir))
            self._increment_summary(summary, judge_result.get("overall_verdict"))

        self.logger.info("Judge summary: %s", summary)
        return summary
