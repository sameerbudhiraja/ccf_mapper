"""Pipeline entrypoint for mapping, judging, review, and final output stages."""
import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
load_dotenv(PROJECT_ROOT / ".env")

from src.config import settings


def _mapping_paths() -> tuple[Path, Path, Path]:
	internal_path = PROJECT_ROOT / "data" / "input" / "internal_controls" / "adobe_internal_controls.json"
	external_path = PROJECT_ROOT / "data" / "cache" / "extracted_controls" / "CIS_controls_pi.json"
	mapping_results_dir = PROJECT_ROOT / "src" / "mapping" / "results"
	return internal_path, external_path, mapping_results_dir


def _print_summary(title: str, summary: dict) -> None:
	print(title)
	for key, value in summary.items():
		print(f"  {key}: {value}")


def run_pipeline(args: argparse.Namespace) -> None:
	print("\n=== CCF Mapper Pipeline ===\n")
	
	if args.build_final:
		from src.review.final_output_builder import build_final_output, write_final_output

		final_output = build_final_output(str(settings.REVIEW_QUEUE_DIR))
		write_final_output(final_output, str(settings.FINAL_OUTPUT_DIR))
		_print_summary("Final Output Statistics:", final_output.get("statistics", {}))
		return

	model_name = os.getenv("LLM_MODEL")
	if not model_name:
		print("ERROR: LLM_MODEL is not set in .env")
		sys.exit(1)

	from src.mapping.chat.client import get_llm
	from src.mapping.engine.mapping_loop import run_mapping
	from src.mapping.loader.external_controls import load_and_flatten_safeguards
	from src.mapping.loader.internal_controls import load_internal_controls

	internal_path, external_path, mapping_results_dir = _mapping_paths()

	print("Loading internal controls ...")
	internal_controls = load_internal_controls(internal_path)
	print(f"  {len(internal_controls)} internal controls loaded")

	if args.max_controls is not None and args.max_controls > 0:
		internal_controls = internal_controls[:args.max_controls]
		print(f"  limiting run to first {len(internal_controls)} controls")

	selected_control_ids = {
		control.get("CCF ID") or control.get("internal_control_id") or control.get("id")
		for control in internal_controls
		if control.get("CCF ID") or control.get("internal_control_id") or control.get("id")
	}

	print("Loading and flattening external safeguards ...")
	safeguards = load_and_flatten_safeguards(external_path)
	print(f"  {len(safeguards)} safeguards loaded")

	llm = get_llm()
	print(f"\nStarting mapping with model: {model_name} (via LangChain)")
	print(f"Results directory: {mapping_results_dir}\n")
	run_mapping(internal_controls, safeguards, mapping_results_dir, llm=llm)

	if args.run_judge:
		from src.judge.judge_loop import JudgeLoop
		from src.prompts.system_prompt import MAPPING_SYSTEM_PROMPT

		judge_loop = JudgeLoop(
			mapping_results_dir=mapping_results_dir,
			judge_output_dir=settings.JUDGE_OUTPUT_DIR,
			internal_controls=internal_controls,
			external_catalog=safeguards,
			llm_client=llm,
			system_rules_summary=MAPPING_SYSTEM_PROMPT,
			target_control_ids=selected_control_ids,
		)
		judge_summary = judge_loop.run()
		_print_summary("Judge Summary:", judge_summary)

	if args.run_review:
		from src.judge.judge_reader import load_all_judge_results
		from src.review.human_review_cli import run_review_session
		from src.review.queue_builder import build_review_queue
		from src.review.queue_writer import save_queue

		judge_results = load_all_judge_results(str(settings.JUDGE_OUTPUT_DIR))
		judge_results = [
			result
			for result in judge_results
			if result.get("internal_control_id") in selected_control_ids
		]
		if not judge_results:
			print("ERROR: No judge output found. Run with --run-judge first or provide existing judge results.")
			sys.exit(1)

		queue_data = build_review_queue(
			judge_results=judge_results,
			internal_controls_db=internal_controls,
			external_controls_db=safeguards,
			mapping_results_dir=mapping_results_dir,
		)
		save_queue(queue_data, str(settings.REVIEW_QUEUE_DIR))
		run_review_session(str(settings.REVIEW_QUEUE_DIR), args.reviewer_name)


def build_parser() -> argparse.ArgumentParser:
	parser = argparse.ArgumentParser(description="CCF mapping pipeline")
	parser.add_argument(
		"--max-controls",
		type=int,
		default=317,
		help="Limit execution to first N internal controls (default: 317).",
	)
	parser.add_argument(
		"--run-judge",
		action="store_true",
		default=False,
		help="Run Stage 1 (LLM Judge) after mapping completes.",
	)
	parser.add_argument(
		"--run-review",
		action="store_true",
		default=False,
		help="Run Stage 2 (Human Review CLI) after judge stage.",
	)
	parser.add_argument(
		"--reviewer-name",
		type=str,
		default="reviewer",
		help="Reviewer name stored in audit fields.",
	)
	parser.add_argument(
		"--build-final",
		action="store_true",
		default=False,
		help="Build final output from an existing completed review queue.",
	)
	return parser


def main() -> None:
	parser = build_parser()
	args = parser.parse_args()
	run_pipeline(args)


if __name__ == "__main__":
	main()
