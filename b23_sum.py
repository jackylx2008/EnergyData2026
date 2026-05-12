from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from energy_data_2026.config_loader import load_env_file
from energy_data_2026.context import AppContext
from energy_data_2026.flows.b23_sum import run
from energy_data_2026.logging_config import setup_logger


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sum B23 shop and office numeric Excel cells into the B23 total workbook."
    )
    parser.add_argument("--env-file", default="common.b23.env", help="B23 env file path")
    args = parser.parse_args()

    env = load_env_file(PROJECT_ROOT / args.env_file)
    setup_logger(log_level=env.get("LOG_LEVEL", "INFO"), log_file=env.get("LOG_FILE"))

    result = run(AppContext(project_root=PROJECT_ROOT, env=env))
    for job_result in result.job_results:
        workbook_result = job_result.result
        print(f"Job: {job_result.name}")
        print(f"Written cells: {workbook_result.written_cells}")
        print(f"Skipped merged cells: {workbook_result.skipped_merged_cells}")
        print(f"Target file: {workbook_result.target_file}")
    print(f"Total written cells: {result.written_cells}")
    print(f"Total skipped merged cells: {result.skipped_merged_cells}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
