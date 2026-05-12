from __future__ import annotations

from dataclasses import dataclass
from numbers import Number
from pathlib import Path
from typing import Iterable

from openpyxl import load_workbook
from openpyxl.cell.cell import MergedCell


CellKey = tuple[int, int]


@dataclass(frozen=True)
class SheetSumResult:
    sheet_name: str
    written_cells: int
    skipped_merged_cells: int


@dataclass(frozen=True)
class WorkbookSumResult:
    target_file: Path
    sheet_results: tuple[SheetSumResult, ...]

    @property
    def written_cells(self) -> int:
        return sum(item.written_cells for item in self.sheet_results)

    @property
    def skipped_merged_cells(self) -> int:
        return sum(item.skipped_merged_cells for item in self.sheet_results)


def sum_workbook_numeric_cells(
    first_source: str | Path,
    second_source: str | Path,
    target_file: str | Path,
    sheet_names: Iterable[str] | None = None,
) -> WorkbookSumResult:
    first_path = Path(first_source)
    second_path = Path(second_source)
    target_path = Path(target_file)
    _require_existing_files(first_path, second_path, target_path)

    first_wb = load_workbook(first_path, data_only=True, read_only=True)
    second_wb = load_workbook(second_path, data_only=True, read_only=True)
    target_wb = load_workbook(target_path)

    try:
        names = tuple(sheet_names) if sheet_names else _common_sheet_names(first_wb, second_wb, target_wb)
        results: list[SheetSumResult] = []

        for sheet_name in names:
            _require_sheet(first_wb, sheet_name, first_path)
            _require_sheet(second_wb, sheet_name, second_path)
            _require_sheet(target_wb, sheet_name, target_path)

            first_values = _numeric_cells(first_wb[sheet_name])
            second_values = _numeric_cells(second_wb[sheet_name])
            written = 0
            skipped_merged = 0

            for row, column in sorted(first_values.keys() | second_values.keys()):
                target_cell = target_wb[sheet_name].cell(row=row, column=column)
                if isinstance(target_cell, MergedCell):
                    skipped_merged += 1
                    continue
                target_cell.value = first_values.get((row, column), 0) + second_values.get((row, column), 0)
                written += 1

            results.append(
                SheetSumResult(
                    sheet_name=sheet_name,
                    written_cells=written,
                    skipped_merged_cells=skipped_merged,
                )
            )

        target_wb.save(target_path)
        return WorkbookSumResult(target_file=target_path, sheet_results=tuple(results))
    finally:
        first_wb.close()
        second_wb.close()
        target_wb.close()


def _require_existing_files(*paths: Path) -> None:
    missing = [str(path) for path in paths if not path.exists()]
    if missing:
        raise FileNotFoundError("Excel file not found: " + "; ".join(missing))


def _require_sheet(workbook, sheet_name: str, path: Path) -> None:
    if sheet_name not in workbook.sheetnames:
        raise ValueError(f"Sheet {sheet_name!r} not found in {path}")


def _common_sheet_names(*workbooks) -> tuple[str, ...]:
    common = set(workbooks[0].sheetnames)
    for workbook in workbooks[1:]:
        common &= set(workbook.sheetnames)
    return tuple(sheet_name for sheet_name in workbooks[-1].sheetnames if sheet_name in common)


def _numeric_cells(worksheet) -> dict[CellKey, Number]:
    values: dict[CellKey, Number] = {}
    for row in worksheet.iter_rows():
        for cell in row:
            if _is_plain_number(cell.value):
                values[(cell.row, cell.column)] = cell.value
    return values


def _is_plain_number(value: object) -> bool:
    return isinstance(value, Number) and not isinstance(value, bool)
