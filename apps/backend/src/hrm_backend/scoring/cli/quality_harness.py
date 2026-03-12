"""CLI entrypoint for the local scoring quality harness."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from hrm_backend.scoring.evaluation import (
    EvaluationMode,
    load_scoring_quality_dataset,
    render_quality_report_json,
    run_quality_harness,
)
from hrm_backend.scoring.infra.ollama.adapter import OllamaMatchScoringAdapter
from hrm_backend.settings import get_settings


def _build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser for the scoring quality harness."""

    parser = argparse.ArgumentParser(description="Run the local scoring quality harness")
    parser.add_argument(
        "--dataset",
        required=True,
        help="Path to a JSON dataset file for the scoring quality harness",
    )
    parser.add_argument(
        "--mode",
        choices=["fixture", "ollama"],
        default="fixture",
        help="Execution mode: deterministic fixture mode or optional Ollama mode",
    )
    parser.add_argument(
        "--format",
        choices=["json"],
        default="json",
        help="Output format for the harness report",
    )
    parser.add_argument(
        "--output",
        help="Optional path where the rendered report should be written",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Execute the scoring quality harness from the command line.

    Args:
        argv: Optional CLI argument list used by tests and module execution.

    Returns:
        int: Process exit code (`0` on success, `1` on failure).
    """

    parser = _build_parser()
    args = parser.parse_args(argv)
    mode: EvaluationMode = args.mode

    try:
        dataset = load_scoring_quality_dataset(args.dataset, mode=mode)
        adapter = None
        if mode == "ollama":
            settings = get_settings()
            adapter = OllamaMatchScoringAdapter(
                base_url=settings.ollama_base_url,
                model_name=settings.match_scoring_model_name,
                timeout_seconds=settings.match_scoring_request_timeout_seconds,
            )

        report = run_quality_harness(dataset=dataset, mode=mode, adapter=adapter)
        rendered_report = render_quality_report_json(report)
        if args.output:
            Path(args.output).write_text(rendered_report, encoding="utf-8")
        else:
            print(rendered_report, end="")
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"Scoring quality harness failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
