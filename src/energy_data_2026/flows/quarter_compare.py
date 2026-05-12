from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from energy_data_2026.context import AppContext
from energy_data_2026.logging_config import get_logger
from energy_data_2026.modules.energy_conversion import EnergyConversionCalculator
from energy_data_2026.modules.energy_workbook_metrics import (
    MetricComparison,
    PeriodMetrics,
    compare_period_metrics,
    read_period_metrics,
    subtract_period_metrics,
)

logger = get_logger(__name__)

CURRENT_YEAR = 2026
PREVIOUS_YEAR = 2025


@dataclass(frozen=True)
class ComparisonProfile:
    name: str
    current_file_key: str
    previous_file_key: str
    default_env_file: str
    current_deduct_file_key: str | None = None
    previous_deduct_file_key: str | None = None


PROFILES: dict[str, ComparisonProfile] = {
    "B23": ComparisonProfile(
        name="B23",
        current_file_key="YEAR_B23_SUM_FILE_2026",
        previous_file_key="YEAR_B23_SUM_FILE_2025",
        default_env_file="common.b23.env",
    ),
    "B23_EXCLUDING_RENT": ComparisonProfile(
        name="B23_EXCLUDING_RENT",
        current_file_key="YEAR_B23_SUM_EXCLUDING_RENT_FILE_2026",
        previous_file_key="YEAR_B23_SUM_EXCLUDING_RENT_FILE_2025",
        default_env_file="common.b23.env",
    ),
    "B23_TENANT": ComparisonProfile(
        name="B23_TENANT",
        current_file_key="YEAR_B23_SUM_FILE_2026",
        previous_file_key="YEAR_B23_SUM_FILE_2025",
        default_env_file="common.b23.env",
        current_deduct_file_key="YEAR_B23_SUM_EXCLUDING_RENT_FILE_2026",
        previous_deduct_file_key="YEAR_B23_SUM_EXCLUDING_RENT_FILE_2025",
    ),
    "B25B26": ComparisonProfile(
        name="B25B26",
        current_file_key="YEAR_B25B26_FILE_2026",
        previous_file_key="YEAR_B25B26_FILE_2025",
        default_env_file="common.b25b26.env",
    ),
}


def run(
    context: AppContext,
    profile_name: str,
    quarter: int,
) -> tuple[PeriodMetrics, PeriodMetrics, tuple[MetricComparison, ...], Path, Path]:
    if context.config is None:
        raise ValueError("AppContext.config is required")

    profile = get_profile(profile_name)
    months = quarter_months(quarter)
    calculator = EnergyConversionCalculator.from_config(context.config)

    previous = _read_profile_period_metrics(
        context=context,
        profile=profile,
        year=PREVIOUS_YEAR,
        months=months,
        calculator=calculator,
        file_key=profile.previous_file_key,
        deduct_file_key=profile.previous_deduct_file_key,
        quarter=quarter,
    )
    current = _read_profile_period_metrics(
        context=context,
        profile=profile,
        year=CURRENT_YEAR,
        months=months,
        calculator=calculator,
        file_key=profile.current_file_key,
        deduct_file_key=profile.current_deduct_file_key,
        quarter=quarter,
    )
    comparison = compare_period_metrics(current=current, previous=previous)

    output_dir = context.project_root / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_stem = f"{profile.name.lower()}_q{quarter}_comparison"
    csv_path = output_dir / f"{output_stem}.csv"
    json_path = output_dir / f"{output_stem}.json"
    _write_csv(csv_path, current, previous, comparison, quarter)
    _write_json(json_path, current, previous, comparison, profile, quarter)
    logger.info("Wrote %s Q%s comparison to %s and %s", profile.name, quarter, csv_path, json_path)
    return current, previous, comparison, csv_path, json_path


def get_profile(profile_name: str) -> ComparisonProfile:
    normalized = profile_name.upper()
    if normalized not in PROFILES:
        valid = ", ".join(sorted(PROFILES))
        raise ValueError(f"Unknown profile {profile_name!r}; valid profiles: {valid}")
    return PROFILES[normalized]


def _read_profile_period_metrics(
    context: AppContext,
    profile: ComparisonProfile,
    year: int,
    months: tuple[int, int, int],
    calculator: EnergyConversionCalculator,
    file_key: str,
    deduct_file_key: str | None,
    quarter: int,
) -> PeriodMetrics:
    file_path = _required_path(context, file_key)
    logger.info("Reading %s Q%s %s metrics from %s", profile.name, quarter, year, file_path)
    total = read_period_metrics(
        file_path,
        year=year,
        months=months,
        calculator=calculator,
    )
    if deduct_file_key is None:
        return total

    deduct_file_path = _required_path(context, deduct_file_key)
    logger.info("Reading %s Q%s %s deducted metrics from %s", profile.name, quarter, year, deduct_file_path)
    deducted = read_period_metrics(
        deduct_file_path,
        year=year,
        months=months,
        calculator=calculator,
    )
    return subtract_period_metrics(total=total, deducted=deducted)


def quarter_months(quarter: int) -> tuple[int, int, int]:
    if quarter not in (1, 2, 3, 4):
        raise ValueError(f"Quarter must be between 1 and 4: {quarter}")
    start_month = (quarter - 1) * 3 + 1
    return (start_month, start_month + 1, start_month + 2)


def _required_path(context: AppContext, key: str) -> Path:
    value = context.env.get(key)
    if not value:
        raise KeyError(f"Missing required env value: {key}")
    return Path(value)


def _write_csv(
    path: Path,
    current: PeriodMetrics,
    previous: PeriodMetrics,
    comparison: tuple[MetricComparison, ...],
    quarter: int,
) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["指标", f"{previous.year}年{quarter}季度", f"{current.year}年{quarter}季度", "增减量", "增减率"])
        for item in comparison:
            writer.writerow(
                [
                    item.metric,
                    item.previous_value,
                    item.current_value,
                    item.change_value,
                    "" if item.change_rate is None else item.change_rate,
                ]
            )

        writer.writerow([])
        writer.writerow(["能源类型", "年份", "实物量", "能源成本(元)", "综合能耗(吨标准煤)", "二氧化碳排放(吨CO2)"])
        for period in (previous, current):
            for item in period.energy_metrics:
                writer.writerow(
                    [
                        item.energy_type,
                        period.year,
                        item.usage,
                        item.cost_yuan,
                        item.standard_coal_tce,
                        item.co2_ton,
                    ]
                )


def _write_json(
    path: Path,
    current: PeriodMetrics,
    previous: PeriodMetrics,
    comparison: tuple[MetricComparison, ...],
    profile: ComparisonProfile,
    quarter: int,
) -> None:
    payload = {
        "profile": profile.name,
        "quarter": quarter,
        "previous": asdict(previous),
        "current": asdict(current),
        "comparison": [asdict(item) for item in comparison],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
