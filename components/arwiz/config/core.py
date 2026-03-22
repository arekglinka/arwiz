import os
import tomllib
from pathlib import Path

import psutil
from arwiz.foundation import ArwizConfig

_ENV_MEMORY = "ARWIZ_MEMORY_LIMIT"
_ENV_TIMEOUT = "ARWIZ_TIMEOUT"
_ENV_SPEEDUP = "ARWIZ_SPEEDUP_THRESHOLD"
_ENV_LLM_PROVIDER = "ARWIZ_LLM_PROVIDER"
_ENV_LLM_MODEL = "ARWIZ_LLM_MODEL"
_ENV_LLM_API_KEY = "ARWIZ_LLM_API_KEY"
_ENV_LLM_BASE_URL = "ARWIZ_LLM_BASE_URL"


class DefaultConfigLoader:
    def get_default_config(self) -> ArwizConfig:
        total_bytes = psutil.virtual_memory().total
        memory_limit_mb = total_bytes // (2 * 1024**2)
        return ArwizConfig(memory_limit_mb=memory_limit_mb)

    def load_config(self, config_path: Path | None = None) -> ArwizConfig:
        config = self.get_default_config()

        file_data: dict = {}
        if config_path and config_path.exists() and config_path.suffix == ".toml":
            file_data = tomllib.loads(config_path.read_text(encoding="utf-8"))

        merged = config.model_dump()

        simple_fields = {
            "memory_limit_mb": int,
            "timeout_seconds": int,
            "speedup_threshold_percent": float,
            "equivalence_tolerance": float,
            "max_optimization_attempts": int,
        }
        for field, _type in simple_fields.items():
            if field in file_data:
                merged[field] = _type(file_data[field])

        llm_from_file = file_data.get("llm", {})
        llm_dict = (
            merged["llm_config"]
            if isinstance(merged["llm_config"], dict)
            else config.llm_config.model_dump()
        )
        for k, v in llm_from_file.items():
            llm_dict[k] = v

        if _ENV_LLM_PROVIDER in os.environ:
            llm_dict["provider"] = os.environ[_ENV_LLM_PROVIDER]
        if _ENV_LLM_MODEL in os.environ:
            llm_dict["model"] = os.environ[_ENV_LLM_MODEL]
        if _ENV_LLM_API_KEY in os.environ:
            llm_dict["api_key"] = os.environ[_ENV_LLM_API_KEY]
        if _ENV_LLM_BASE_URL in os.environ:
            llm_dict["base_url"] = os.environ[_ENV_LLM_BASE_URL]

        merged["llm_config"] = llm_dict

        if _ENV_MEMORY in os.environ:
            merged["memory_limit_mb"] = int(os.environ[_ENV_MEMORY])
        if _ENV_TIMEOUT in os.environ:
            merged["timeout_seconds"] = int(os.environ[_ENV_TIMEOUT])
        if _ENV_SPEEDUP in os.environ:
            merged["speedup_threshold_percent"] = float(os.environ[_ENV_SPEEDUP])

        if merged["memory_limit_mb"] is not None and merged["memory_limit_mb"] <= 0:
            raise ValueError("memory_limit_mb must be > 0")
        if merged["timeout_seconds"] <= 0:
            raise ValueError("timeout_seconds must be > 0")
        if (
            merged["speedup_threshold_percent"] is not None
            and not 0 <= merged["speedup_threshold_percent"] <= 100
        ):
            raise ValueError("speedup_threshold_percent must be between 0 and 100")

        return ArwizConfig(**merged)
