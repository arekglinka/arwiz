from pathlib import Path
from typing import Protocol

from arwiz.foundation import ArwizConfig


class ConfigLoaderProtocol(Protocol):
    def load_config(self, config_path: Path | None = None) -> ArwizConfig: ...
    def get_default_config(self) -> ArwizConfig: ...
