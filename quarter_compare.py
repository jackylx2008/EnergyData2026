from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from energy_data_2026.config_loader import load_env_file, load_yaml_config
from energy_data_2026.context import AppContext
from energy_data_2026.flows.quarter_compare import get_profile, run
from energy_data_2026.logging_config import setup_logger


USAGE = """季度能耗对比工具

用途：
  对比 2026 年与 2025 年指定对象、指定季度的能源成本、综合能耗（标准煤）和二氧化碳排放。

必填参数：
  --profile   对比对象，可选：B23、B23_EXCLUDING_RENT、B23_TENANT、B25B26
  --quarter   对比季度，可选：1、2、3、4

可选参数：
  --env-file      指定 env 文件；不填时按 profile 自动选择
                  B23、B23_EXCLUDING_RENT、B23_TENANT 使用 common.b23.env
                  B25B26 使用 common.b25b26.env
  --config-file   指定配置文件；默认 config.yaml

示例：
  python quarter_compare.py --profile B23 --quarter 1
  python quarter_compare.py --profile B23 --quarter 2
  python quarter_compare.py --profile B23_EXCLUDING_RENT --quarter 1
  python quarter_compare.py --profile B23_TENANT --quarter 1
  python quarter_compare.py --profile B25B26 --quarter 1
  python quarter_compare.py --profile b25b26 --quarter 4

输出：
  结果会写入 output/ 目录，文件名格式为：
  output/{profile}_q{quarter}_comparison.csv
  output/{profile}_q{quarter}_comparison.json
"""


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        print(USAGE)
        return 0

    parser = argparse.ArgumentParser(
        description="季度能耗对比工具",
        usage="python quarter_compare.py --profile {B23,B23_EXCLUDING_RENT,B23_TENANT,B25B26} --quarter {1,2,3,4}",
    )
    parser.add_argument(
        "--profile",
        required=True,
        type=str.upper,
        choices=["B23", "B23_EXCLUDING_RENT", "B23_TENANT", "B25B26"],
        help="对比对象：B23、B23_EXCLUDING_RENT、B23_TENANT 或 B25B26",
    )
    parser.add_argument("--quarter", required=True, type=int, choices=[1, 2, 3, 4], help="对比季度：1、2、3、4")
    parser.add_argument("--env-file", default=None, help="env 文件路径；默认按 profile 自动选择")
    parser.add_argument("--config-file", default="config.yaml", help="YAML 配置文件路径，默认 config.yaml")
    args = parser.parse_args(argv)

    profile = get_profile(args.profile)
    env_file = args.env_file or profile.default_env_file
    env = load_env_file(PROJECT_ROOT / env_file)
    config = load_yaml_config(PROJECT_ROOT / args.config_file)
    setup_logger(log_level=env.get("LOG_LEVEL", "INFO"), log_file=env.get("LOG_FILE"))

    current, previous, comparison, csv_path, json_path = run(
        AppContext(project_root=PROJECT_ROOT, env=env, config=config),
        profile_name=profile.name,
        quarter=args.quarter,
    )

    print(f"对比对象: {profile.name}")
    print(f"对比季度: Q{args.quarter}")
    print(f"对比月份: {','.join(str(month) for month in current.months)}")
    print(f"输出 CSV: {csv_path}")
    print(f"输出 JSON: {json_path}")
    for item in comparison:
        rate_text = "NA" if item.change_rate is None else f"{item.change_rate:.2%}"
        print(
            f"{item.metric}: {previous.year}={item.previous_value}, "
            f"{current.year}={item.current_value}, 增减={item.change_value}, 增减率={rate_text}"
        )
    summary_parts = [
        f"综合能耗{_format_signed_percent(_change_rate(current.total_standard_coal_tce, previous.total_standard_coal_tce))}",
        f"能源成本{_format_signed_percent(_change_rate(current.total_cost_yuan, previous.total_cost_yuan))}",
        f"二氧化碳排放{_format_signed_percent(_change_rate(current.total_co2_ton, previous.total_co2_ton))}",
    ]
    energy_per_revenue_rate = _energy_per_revenue_change_rate(
        env,
        profile.name,
        args.quarter,
        current.total_standard_coal_tce,
        previous.total_standard_coal_tce,
    )
    if energy_per_revenue_rate is not None:
        summary_parts.append(f"万元产值能耗同比{_format_signed_percent(energy_per_revenue_rate)}")
    print(f"总结: {profile.name} {'；'.join(summary_parts)}。")
    return 0


def _change_rate(current_value: float, previous_value: float) -> float | None:
    if previous_value == 0:
        return 0.0 if current_value == 0 else None
    return (current_value - previous_value) / previous_value


def _format_signed_percent(value: float | None) -> str:
    if value is None:
        return "NA"
    return f"{value:+.2%}"


def _energy_per_revenue_change_rate(
    env: dict[str, str],
    profile_name: str,
    quarter: int,
    current_standard_coal_tce: float,
    previous_standard_coal_tce: float,
) -> float | None:
    current_revenue = _quarter_revenue(env, profile_name, 2026, quarter)
    previous_revenue = _quarter_revenue(env, profile_name, 2025, quarter)
    if current_revenue in (None, 0) or previous_revenue in (None, 0):
        return None

    current_intensity = current_standard_coal_tce / current_revenue
    previous_intensity = previous_standard_coal_tce / previous_revenue
    return _change_rate(current_intensity, previous_intensity)


def _quarter_revenue(env: dict[str, str], profile_name: str, year: int, quarter: int) -> float | None:
    key = f"YEAR_{profile_name}_REVENUE_{year}_WAN_YUAN_BY_QUARTER"
    raw_value = env.get(key)
    if not raw_value:
        return None

    values = json.loads(raw_value)
    value = values[quarter - 1]
    if value is None:
        return None
    return float(value)


if __name__ == "__main__":
    raise SystemExit(main())
