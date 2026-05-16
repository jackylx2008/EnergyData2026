from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from energy_data_2026.context import AppContext
from energy_data_2026.logging_config import get_logger
from energy_data_2026.modules.excel_cell_sum import (
    SheetSumResult,
    SourceSheet,
    WorkbookSumResult,
    copy_source_sheet_table_into_target_sheet,
    sum_multiple_workbook_numeric_cells,
    sum_source_sheets_into_target_sheet,
)

logger = get_logger(__name__)

CONFIG_SECTION = "huitou_sum"


def run(context: AppContext) -> WorkbookSumResult:
    config = _required_config_section(context)
    target_file = _required_path(context, config, "target_file")
    jobs = _sum_jobs(context, config)
    sheet_results: list[SheetSumResult] = []

    for job in jobs:
        logger.info(
            "Summing %s Huitou workbooks into %s sheet %s",
            len(job.source_files),
            target_file,
            job.sheet_name or "<common sheets>",
        )
        if len(job.source_sheets) == 1:
            if not job.sheet_name:
                raise KeyError("A target sheet_name is required when source sheet names are configured")
            result = copy_source_sheet_table_into_target_sheet(
                source_sheet=job.source_sheets[0],
                target_file=target_file,
                target_sheet_name=job.sheet_name,
                target_year=job.target_year,
            )
        elif job.source_sheets:
            if not job.sheet_name:
                raise KeyError("A target sheet_name is required when source sheet names are configured")
            result = sum_source_sheets_into_target_sheet(
                source_sheets=job.source_sheets,
                target_file=target_file,
                target_sheet_name=job.sheet_name,
                target_year=job.target_year,
            )
        else:
            result = sum_multiple_workbook_numeric_cells(
                source_files=job.source_files,
                target_file=target_file,
                sheet_names=(job.sheet_name,) if job.sheet_name else job.sheet_names,
            )
        logger.info("Wrote %s numeric cells to %s", result.written_cells, result.target_file)
        sheet_results.extend(result.sheet_results)

    return WorkbookSumResult(target_file=target_file, sheet_results=tuple(sheet_results))


@dataclass(frozen=True)
class _SumJob:
    source_files: tuple[Path, ...]
    source_sheets: tuple[SourceSheet, ...] = ()
    sheet_name: str | None = None
    sheet_names: tuple[str, ...] | None = None
    target_year: str = "2026年"


def _required_config_section(context: AppContext) -> dict[str, Any]:
    if not context.config:
        raise KeyError("Missing required YAML config")
    section = context.config.get(CONFIG_SECTION)
    if not isinstance(section, dict):
        raise KeyError(f"Missing required YAML section: {CONFIG_SECTION}")
    return section


def _required_path(context: AppContext, config: dict[str, Any], key: str) -> Path:
    key_value = config.get(f"{key}_key")
    if key_value:
        return _required_env_path(context, str(key_value))

    value = config.get(key)
    if not value:
        raise KeyError(f"Missing required YAML value: {CONFIG_SECTION}.{key} or {CONFIG_SECTION}.{key}_key")
    if not isinstance(value, str):
        raise TypeError(f"YAML value must be a string: {CONFIG_SECTION}.{key}")
    return Path(value)


def _required_env_path(context: AppContext, key: str) -> Path:
    value = context.env.get(key)
    if not value:
        raise KeyError(f"Missing required env value: {key}")
    return Path(value)


def _required_paths(config: dict[str, Any], key: str) -> tuple[Path, ...]:
    values = _optional_strings(config, key)
    if not values:
        raise KeyError(f"Missing required YAML value: {CONFIG_SECTION}.{key}")
    return tuple(Path(value) for value in values)


def _sum_jobs(context: AppContext, config: dict[str, Any]) -> tuple[_SumJob, ...]:
    raw_jobs = config.get("jobs")
    if raw_jobs is None:
        return (
            _SumJob(
                source_files=_required_paths(config, "source_files"),
                sheet_names=_optional_strings(config, "sheet_names"),
            ),
        )
    if not isinstance(raw_jobs, list):
        raise TypeError(f"YAML value must be a list: {CONFIG_SECTION}.jobs")

    jobs: list[_SumJob] = []
    for index, raw_job in enumerate(raw_jobs, start=1):
        if not isinstance(raw_job, dict):
            raise TypeError(f"YAML value must be a mapping: {CONFIG_SECTION}.jobs[{index}]")
        sheet_name = _sheet_name_value(context, raw_job, index)
        source_sheets = _source_sheets(context, raw_job, sheet_name)
        jobs.append(
            _SumJob(
                source_files=tuple(source.file for source in source_sheets),
                source_sheets=source_sheets,
                sheet_name=sheet_name,
                target_year=_target_year(raw_job, config),
            )
        )
    if not jobs:
        raise KeyError(f"Missing required YAML value: {CONFIG_SECTION}.jobs")
    return tuple(jobs)


def _optional_strings(config: dict[str, Any], key: str) -> tuple[str, ...] | None:
    value = config.get(key)
    if not value:
        return None
    if isinstance(value, str):
        separator = ";" if ";" in value else ","
        items = tuple(item.strip() for item in value.split(separator) if item.strip())
        return items or None
    if isinstance(value, list):
        items = tuple(str(item).strip() for item in value if str(item).strip())
        return items or None
    raise TypeError(f"YAML value must be a string or list: {CONFIG_SECTION}.{key}")


def _source_sheets(context: AppContext, config: dict[str, Any], default_sheet_name: str) -> tuple[SourceSheet, ...]:
    value = config.get("source_files")
    if not value:
        raise KeyError(f"Missing required YAML value: {CONFIG_SECTION}.source_files")
    if isinstance(value, str):
        return tuple(SourceSheet(file=Path(path), sheet_name=default_sheet_name) for path in _split_string(value))
    if not isinstance(value, list):
        raise TypeError(f"YAML value must be a string or list: {CONFIG_SECTION}.source_files")

    sources: list[SourceSheet] = []
    for index, item in enumerate(value, start=1):
        if isinstance(item, str):
            sources.append(SourceSheet(file=Path(item), sheet_name=default_sheet_name))
            continue
        if not isinstance(item, dict):
            raise TypeError(f"YAML value must be a string or mapping: {CONFIG_SECTION}.source_files[{index}]")
        file_value = _source_file_value(context, item, index)
        sheet_value = _source_sheet_name_value(context, item, index)
        sources.append(SourceSheet(file=file_value, sheet_name=sheet_value))
    if not sources:
        raise KeyError(f"Missing required YAML value: {CONFIG_SECTION}.source_files")
    return tuple(sources)


def _source_file_value(context: AppContext, item: dict[str, Any], index: int) -> Path:
    file_key = item.get("file_key")
    if file_key:
        return _required_env_path(context, str(file_key))

    file_value = item.get("file")
    if not isinstance(file_value, str) or not file_value.strip():
        raise KeyError(
            f"Missing required YAML value: {CONFIG_SECTION}.source_files[{index}].file "
            f"or {CONFIG_SECTION}.source_files[{index}].file_key"
        )
    return Path(file_value.strip())


def _sheet_name_value(context: AppContext, item: dict[str, Any], index: int) -> str:
    sheet_name_key = item.get("sheet_name_key")
    if sheet_name_key:
        return _required_env_value(context, str(sheet_name_key))

    sheet_name = item.get("sheet_name")
    if not isinstance(sheet_name, str) or not sheet_name.strip():
        raise KeyError(
            f"Missing required YAML value: {CONFIG_SECTION}.jobs[{index}].sheet_name "
            f"or {CONFIG_SECTION}.jobs[{index}].sheet_name_key"
        )
    return sheet_name.strip()


def _source_sheet_name_value(context: AppContext, item: dict[str, Any], index: int) -> str:
    sheet_name_key = item.get("sheet_name_key", item.get("sheet_key"))
    if sheet_name_key:
        return _required_env_value(context, str(sheet_name_key))

    sheet_name = item.get("sheet_name", item.get("sheet"))
    if not isinstance(sheet_name, str) or not sheet_name.strip():
        raise KeyError(
            f"Missing required YAML value: {CONFIG_SECTION}.source_files[{index}].sheet_name "
            f"or {CONFIG_SECTION}.source_files[{index}].sheet_name_key"
        )
    return sheet_name.strip()


def _required_env_value(context: AppContext, key: str) -> str:
    value = context.env.get(key)
    if not value:
        raise KeyError(f"Missing required env value: {key}")
    return value.strip()


def _split_string(value: str) -> tuple[str, ...]:
    separator = ";" if ";" in value else ","
    return tuple(item.strip() for item in value.split(separator) if item.strip())


def _target_year(job_config: dict[str, Any], root_config: dict[str, Any]) -> str:
    value = job_config.get("target_year", root_config.get("target_year", "2026年"))
    if not isinstance(value, str) or not value.strip():
        raise TypeError(f"YAML value must be a string: {CONFIG_SECTION}.target_year")
    return value.strip()
