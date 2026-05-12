from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from energy_data_2026.context import AppContext
from energy_data_2026.logging_config import get_logger
from energy_data_2026.modules.excel_cell_sum import WorkbookSumResult, sum_workbook_numeric_cells

logger = get_logger(__name__)

SHOP_FILE_KEY = "YEAR_B23_SHOP_FILE_2026"
OFFICE_FILE_KEY = "YEAR_B23_OFFICE_FILE_2026"
SUM_FILE_KEY = "YEAR_B23_SUM_FILE_2026"
SHOP_EXCLUDING_RENT_FILE_KEY = "YEAR_B23_SHOP_EXCLUDING_RENT_FILE_2026"
OFFICE_EXCLUDING_RENT_FILE_KEY = "YEAR_B23_OFFICE_EXCLUDING_RENT_FILE_2026"
SUM_EXCLUDING_RENT_FILE_KEY = "YEAR_B23_SUM_EXCLUDING_RENT_FILE_2026"


@dataclass(frozen=True)
class B23SumJob:
    name: str
    shop_file_key: str
    office_file_key: str
    target_file_key: str


@dataclass(frozen=True)
class B23SumJobResult:
    name: str
    result: WorkbookSumResult


@dataclass(frozen=True)
class B23SumRunResult:
    job_results: tuple[B23SumJobResult, ...]

    @property
    def written_cells(self) -> int:
        return sum(item.result.written_cells for item in self.job_results)

    @property
    def skipped_merged_cells(self) -> int:
        return sum(item.result.skipped_merged_cells for item in self.job_results)


SUM_JOBS = (
    B23SumJob(
        name="包含租区",
        shop_file_key=SHOP_FILE_KEY,
        office_file_key=OFFICE_FILE_KEY,
        target_file_key=SUM_FILE_KEY,
    ),
    B23SumJob(
        name="不包含租区",
        shop_file_key=SHOP_EXCLUDING_RENT_FILE_KEY,
        office_file_key=OFFICE_EXCLUDING_RENT_FILE_KEY,
        target_file_key=SUM_EXCLUDING_RENT_FILE_KEY,
    ),
)


def run(context: AppContext) -> B23SumRunResult:
    job_results: list[B23SumJobResult] = []
    for job in SUM_JOBS:
        shop_file = _required_path(context, job.shop_file_key)
        office_file = _required_path(context, job.office_file_key)
        sum_file = _required_path(context, job.target_file_key)

        logger.info("Summing B23 %s workbooks into %s", job.name, sum_file)
        result = sum_workbook_numeric_cells(
            first_source=shop_file,
            second_source=office_file,
            target_file=sum_file,
        )
        logger.info("Wrote %s numeric cells to %s", result.written_cells, result.target_file)
        job_results.append(B23SumJobResult(name=job.name, result=result))
    return B23SumRunResult(job_results=tuple(job_results))


def _required_path(context: AppContext, key: str) -> Path:
    value = context.env.get(key)
    if not value:
        raise KeyError(f"Missing required env value: {key}")
    return Path(value)
