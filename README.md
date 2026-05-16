# EnergyData2026

EnergyData2026 是一个用于能源数据处理和对比分析的 Python 项目。当前包含两个主要入口：

- `b23_sum.py`：汇总 B23 相关 Excel 工作簿中的数值单元格。
- `huitou_sum.py`：汇总本地回投相关 Excel 工作簿中的对应数值单元格。
- `quarter_compare.py`：对比不同对象在指定季度的能源成本、综合能耗和二氧化碳排放。

## 项目结构

```text
.
├── b23_sum.py
├── huitou_sum.py
├── quarter_compare.py
├── config.yaml
├── huitou_sum.config.yaml
├── src/
│   └── energy_data_2026/
│       ├── flows/
│       └── modules/
└── tests/
```

## 本地配置

运行依赖本地 env 文件提供输入、输出和日志等配置。env 文件不进入版本库。

常用文件名：

- `common.b23.env`
- `common.b25b26.env`

`config.yaml` 保存通用折算系数和排放因子等配置。
`huitou_sum.config.yaml` 保存回投汇总的源 Excel 和结果 Excel 文件位置。

## 使用方式

汇总 B23 Excel 数据：

```powershell
python b23_sum.py --env-file common.b23.env
```

汇总回投 Excel 数据：

```powershell
python huitou_sum.py
```

`huitou_sum.config.yaml` 示例：

```yaml
logging:
  level: INFO
  file: ./logs/huitou_sum.log

huitou_sum:
  target_file: D:/path/target.xlsx
  jobs:
    - sheet_name: Sheet1
      source_files:
        - file: D:/path/sheet1_source_a.xlsx
          sheet_name: SourceSheetA
        - file: D:/path/sheet1_source_b.xlsx
          sheet_name: SourceSheetB
    - sheet_name: Sheet2
      source_files:
        - file: D:/path/sheet2_source_a.xlsx
          sheet_name: SourceSheetA
        - file: D:/path/sheet2_source_b.xlsx
          sheet_name: SourceSheetB
```

`jobs` 中每一项对应结果 Excel 的一个工作表。job 的 `sheet_name` 是结果文件里的目标工作表；`source_files` 每一项的 `sheet_name` 是对应源 Excel 文件里的源工作表。

回投汇总按源表和目标表的能源类别、指标、月份匹配数据：

- `source_files` 只有一个文件时，拷贝匹配到的数值单元格。
- `source_files` 有两个或更多文件时，先把匹配到的数值单元格求和，再写入目标工作表。
- 默认写入目标表 `2026年` 区域；如需调整，可在 `huitou_sum` 或单个 job 下配置 `target_year`。

季度能耗对比：

```powershell
python quarter_compare.py --profile B23 --quarter 1
python quarter_compare.py --profile B25B26 --quarter 1
```

支持的 `profile`：

- `B23`
- `B23_EXCLUDING_RENT`
- `B23_TENANT`
- `B25B26`

输出结果写入 `output/`，日志写入 `logs/`。

## 测试

```powershell
python -m pytest
```

## Git 同步注意

- `README.md` 必须随项目功能变化保持更新。
- `COMMON_PROJECT_SKILLS.md` 是本地项目技能文件，不同步到 Git。
- `output/`、`logs/`、`*.env` 等运行产物和本地配置不提交。
