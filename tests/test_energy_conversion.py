from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from energy_data_2026.config_loader import load_yaml_config
from energy_data_2026.modules.energy_conversion import EnergyConversionCalculator


class EnergyConversionTests(unittest.TestCase):
    def test_calculates_standard_coal_from_config(self) -> None:
        config = load_yaml_config(Path(__file__).resolve().parents[1] / "config.yaml")
        calculator = EnergyConversionCalculator.from_config(config)

        self.assertEqual(calculator.calc_standard_coal_tce("电", 10000), 1.229)
        self.assertEqual(calculator.calc_standard_coal_tce("燃气", 500), 0.665)
        self.assertEqual(calculator.calc_standard_coal_tce("自来水", 10000), 0)

    def test_adds_record_columns(self) -> None:
        calculator = EnergyConversionCalculator(
            coal_conversion={"电": 0.1229},
            co2_conversion={"电": 0.5},
        )
        records = [{"能源类型": "电", "实际消耗": 10000}]

        calculator.add_record_columns(records)

        self.assertEqual(records[0]["标准煤(吨标准煤)"], 1.229)
        self.assertEqual(records[0]["二氧化碳排放量(吨CO2)"], 5.0)


if __name__ == "__main__":
    unittest.main()
