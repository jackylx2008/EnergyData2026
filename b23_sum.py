"""B23 Excel 汇总工具

用途：
  将 B23 商业部分和 B23 写字楼部分 Excel 工作簿中的数值单元格汇总到 B23 目标工作簿。
  当前会同时处理“包含租区”和“不包含租区”两个口径。

配置文件：
  默认读取 common.b23.env。
  env 文件中配置源 Excel 文件、目标 Excel 文件、日志级别和日志文件。

可选参数：
  --env-file   指定 B23 env 文件；默认 common.b23.env

示例：
  python b23_sum.py
  python b23_sum.py --env-file common.b23.env

输出：
  脚本会直接写入 env 中配置的目标 Excel 文件，并在控制台输出每个任务的写入单元格数量、
  跳过的合并单元格数量和目标文件路径。
"""

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
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
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
