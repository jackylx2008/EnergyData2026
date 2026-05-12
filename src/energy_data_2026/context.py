from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


@dataclass(frozen=True)
class AppContext:
    project_root: Path
    env: Mapping[str, str]
    config: Mapping[str, Any] | None = None
