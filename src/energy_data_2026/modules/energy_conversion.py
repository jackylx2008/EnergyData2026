from __future__ import annotations

from dataclasses import dataclass
from numbers import Number
from typing import Any, Mapping, MutableMapping, Sequence


DEFAULT_COAL_COLUMN = "标准煤(吨标准煤)"
DEFAULT_CO2_COLUMN = "二氧化碳排放量(吨CO2)"


@dataclass(frozen=True)
class EnergyConversionCalculator:
    coal_conversion: Mapping[str, float]
    co2_conversion: Mapping[str, float]

    @classmethod
    def from_config(cls, config: Mapping[str, Any]) -> "EnergyConversionCalculator":
        return cls(
            coal_conversion=_number_mapping(config.get("coal_conversion", {}), "coal_conversion"),
            co2_conversion=_number_mapping(config.get("co2_conversion", {}), "co2_conversion"),
        )

    def calc_standard_coal_tce(self, energy_type: str, usage: object) -> float:
        factor = self.coal_conversion.get(energy_type, 0.0)
        return round(_to_float(usage) * factor / 1000.0, 4)

    def calc_co2_ton(self, energy_type: str, usage: object) -> float:
        factor = self.co2_conversion.get(energy_type, 0.0)
        return round(_to_float(usage) * factor / 1000.0, 4)

    def calc_total_standard_coal_tce(self, records: Sequence[Mapping[str, Any]]) -> float:
        total = sum(
            self.calc_standard_coal_tce(str(row["能源类型"]), row["实际消耗"])
            for row in records
        )
        return round(total, 4)

    def calc_total_co2_ton(self, records: Sequence[Mapping[str, Any]]) -> float:
        total = sum(
            self.calc_co2_ton(str(row["能源类型"]), row["实际消耗"])
            for row in records
        )
        return round(total, 4)

    def add_record_columns(
        self,
        records: Sequence[MutableMapping[str, Any]],
        energy_type_column: str = "能源类型",
        usage_column: str = "实际消耗",
        coal_column: str = DEFAULT_COAL_COLUMN,
        co2_column: str = DEFAULT_CO2_COLUMN,
    ) -> Sequence[MutableMapping[str, Any]]:
        for row in records:
            energy_type = str(row[energy_type_column])
            usage = row[usage_column]
            row[coal_column] = self.calc_standard_coal_tce(energy_type, usage)
            row[co2_column] = self.calc_co2_ton(energy_type, usage)
        return records

    def add_dataframe_columns(
        self,
        df,
        energy_type_column: str = "能源类型",
        usage_column: str = "实际消耗",
        coal_column: str = DEFAULT_COAL_COLUMN,
        co2_column: str = DEFAULT_CO2_COLUMN,
    ):
        df[coal_column] = df.apply(
            lambda row: self.calc_standard_coal_tce(row[energy_type_column], row[usage_column]),
            axis=1,
        )
        df[co2_column] = df.apply(
            lambda row: self.calc_co2_ton(row[energy_type_column], row[usage_column]),
            axis=1,
        )
        return df


def _number_mapping(value: object, name: str) -> dict[str, float]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be a mapping")

    result: dict[str, float] = {}
    for key, item in value.items():
        result[str(key)] = _to_float(item)
    return result


def _to_float(value: object) -> float:
    if value in (None, ""):
        return 0.0
    if isinstance(value, bool):
        return 0.0
    if isinstance(value, Number):
        return float(value)
    return float(str(value).replace(",", "").strip())
