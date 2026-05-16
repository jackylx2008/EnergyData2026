"""会投 Excel 汇总工具

用途：
  按配置将会投相关源 Excel 工作表中的能源数据写入本地目标台账工作簿。
  脚本按能源类别、指标和月份匹配数据，不依赖源表和目标表的单元格坐标完全一致。

配置文件：
  固定读取 huitou_sum.config.yaml 和 common.huitou.env。
  huitou_sum.config.yaml 保存目标工作表、源工作表和数据源的映射 key。
  common.huitou.env 保存本地 Excel 文件路径和真实工作表名称。

处理规则：
  source_files 只有一个文件时，拷贝匹配到的数值单元格。
  source_files 有两个或更多文件时，先把匹配到的数值单元格求和，再写入目标工作表。
  默认写入目标表 2026年 区域；如需调整，可在配置中设置 target_year。

示例：
  python huitou_sum.py

输出：
  脚本会直接写入 common.huitou.env 中配置的目标 Excel 文件，并在控制台输出写入单元格数量、
  跳过的合并单元格数量和目标文件路径。
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from energy_data_2026.config_loader import load_env_file, load_yaml_config
from energy_data_2026.context import AppContext
from energy_data_2026.flows.huitou_sum import run
from energy_data_2026.logging_config import setup_logger


def main() -> int:
    config = load_yaml_config(PROJECT_ROOT / "huitou_sum.config.yaml")
    env = load_env_file(PROJECT_ROOT / "common.huitou.env")
    logging_config = config.get("logging", {})
    setup_logger(
        log_level=str(logging_config.get("level", "INFO")),
        log_file=logging_config.get("file"),
    )

    result = run(AppContext(project_root=PROJECT_ROOT, env=env, config=config))
    print(f"Written cells: {result.written_cells}")
    print(f"Skipped merged cells: {result.skipped_merged_cells}")
    print(f"Target file: {result.target_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
