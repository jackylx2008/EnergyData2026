from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from energy_data_2026.config_loader import load_yaml_config
from energy_data_2026.context import AppContext
from energy_data_2026.flows.huitou_sum import run
from energy_data_2026.logging_config import setup_logger


def main() -> int:
    config = load_yaml_config(PROJECT_ROOT / "huitou_sum.config.yaml")
    logging_config = config.get("logging", {})
    setup_logger(
        log_level=str(logging_config.get("level", "INFO")),
        log_file=logging_config.get("file"),
    )

    result = run(AppContext(project_root=PROJECT_ROOT, env={}, config=config))
    print(f"Written cells: {result.written_cells}")
    print(f"Skipped merged cells: {result.skipped_merged_cells}")
    print(f"Target file: {result.target_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
