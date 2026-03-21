"""Tests for arwiz.config — Configuration loading, merging, and validation."""

import os
import tomllib
from pathlib import Path
from unittest.mock import patch

import pytest

from arwiz.config.core import DefaultConfigLoader
from arwiz.foundation import ArwizConfig


@pytest.fixture
def loader() -> DefaultConfigLoader:
    return DefaultConfigLoader()


@pytest.fixture
def temp_toml(tmp_path: Path) -> Path:
    """Create a temp TOML config file with known values."""
    config_content = """
memory_limit_mb = 1024
timeout_seconds = 60
speedup_threshold_percent = 25.0
equivalence_tolerance = 1e-8
max_optimization_attempts = 3
[llm]
provider = "anthropic"
model = "claude-3-opus"
"""
    p = tmp_path / "test_config.toml"
    p.write_text(config_content, encoding="utf-8")
    return p


class TestGetDefaultConfig:
    """Test DefaultConfigLoader.get_default_config()."""

    def test_memory_limit_auto_detected(self, loader: DefaultConfigLoader) -> None:
        """memory_limit_mb should be 50% of total system RAM."""
        config = loader.get_default_config()
        assert config.memory_limit_mb is not None
        assert config.memory_limit_mb > 0

    def test_memory_limit_is_half_of_ram(self, loader: DefaultConfigLoader) -> None:
        """memory_limit_mb should equal total RAM bytes // (2 * 1024**2)."""
        with patch("arwiz.config.core.psutil") as mock_psutil:
            mock_psutil.virtual_memory.return_value.total = 16 * 1024**3  # 16 GB
            config = loader.get_default_config()
        assert config.memory_limit_mb == 8192  # 16 GB / 2

    def test_other_defaults_are_sensible(self, loader: DefaultConfigLoader) -> None:
        """Non-auto-detected fields should match ArwizConfig defaults."""
        with patch("arwiz.config.core.psutil") as mock_psutil:
            mock_psutil.virtual_memory.return_value.total = 8 * 1024**3
            config = loader.get_default_config()
        assert config.timeout_seconds == 300
        assert config.speedup_threshold_percent == 50.0
        assert config.equivalence_tolerance == 1e-6
        assert config.max_optimization_attempts == 5

    def test_returns_arwiz_config_instance(self, loader: DefaultConfigLoader) -> None:
        config = loader.get_default_config()
        assert isinstance(config, ArwizConfig)


class TestLoadConfigFromFile:
    """Test loading config from TOML file."""

    def test_load_config_from_file(self, loader: DefaultConfigLoader, temp_toml: Path) -> None:
        """TOML file values should override defaults."""
        with patch("arwiz.config.core.psutil") as mock_psutil:
            mock_psutil.virtual_memory.return_value.total = 16 * 1024**3
            config = loader.load_config(config_path=temp_toml)
        assert config.memory_limit_mb == 1024
        assert config.timeout_seconds == 60
        assert config.speedup_threshold_percent == 25.0

    def test_load_config_missing_file(self, loader: DefaultConfigLoader) -> None:
        """Missing file should return defaults."""
        nonexistent = Path("/tmp/does_not_exist_arwiz.toml")
        with patch("arwiz.config.core.psutil") as mock_psutil:
            mock_psutil.virtual_memory.return_value.total = 16 * 1024**3
            config = loader.load_config(config_path=nonexistent)
        assert config.memory_limit_mb == 8192
        assert config.timeout_seconds == 300

    def test_config_file_overrides_defaults(
        self, loader: DefaultConfigLoader, tmp_path: Path
    ) -> None:
        """Partial TOML overrides only specified fields."""
        config_content = "timeout_seconds = 120\n"
        p = tmp_path / "partial.toml"
        p.write_text(config_content, encoding="utf-8")
        with patch("arwiz.config.core.psutil") as mock_psutil:
            mock_psutil.virtual_memory.return_value.total = 16 * 1024**3
            config = loader.load_config(config_path=p)
        assert config.timeout_seconds == 120
        # Defaults preserved
        assert config.speedup_threshold_percent == 50.0

    def test_non_toml_extension_ignored(self, loader: DefaultConfigLoader, tmp_path: Path) -> None:
        """Non-.toml files should be ignored, defaults returned."""
        p = tmp_path / "config.json"
        p.write_text('{"timeout_seconds": 10}', encoding="utf-8")
        with patch("arwiz.config.core.psutil") as mock_psutil:
            mock_psutil.virtual_memory.return_value.total = 16 * 1024**3
            config = loader.load_config(config_path=p)
        assert config.timeout_seconds == 300  # default


class TestEnvVarOverrides:
    """Test environment variable overrides."""

    def test_env_var_timeout(self, loader: DefaultConfigLoader) -> None:
        """ARWIZ_TIMEOUT_SECONDS env var should override config."""
        with patch.dict(os.environ, {"ARWIZ_TIMEOUT_SECONDS": "60"}, clear=False):
            with patch("arwiz.config.core.psutil") as mock_psutil:
                mock_psutil.virtual_memory.return_value.total = 16 * 1024**3
                config = loader.load_config()
        assert config.timeout_seconds == 60

    def test_env_var_memory_limit(self, loader: DefaultConfigLoader) -> None:
        """ARWIZ_MEMORY_LIMIT_MB should override auto-detected value."""
        with patch.dict(os.environ, {"ARWIZ_MEMORY_LIMIT_MB": "4096"}, clear=False):
            with patch("arwiz.config.core.psutil") as mock_psutil:
                mock_psutil.virtual_memory.return_value.total = 16 * 1024**3
                config = loader.load_config()
        assert config.memory_limit_mb == 4096

    def test_env_var_speedup_threshold(self, loader: DefaultConfigLoader) -> None:
        """ARWIZ_SPEEDUP_THRESHOLD should override default."""
        with patch.dict(os.environ, {"ARWIZ_SPEEDUP_THRESHOLD": "75.5"}, clear=False):
            with patch("arwiz.config.core.psutil") as mock_psutil:
                mock_psutil.virtual_memory.return_value.total = 16 * 1024**3
                config = loader.load_config()
        assert config.speedup_threshold_percent == 75.5

    def test_env_overrides_file(self, loader: DefaultConfigLoader, temp_toml: Path) -> None:
        """Env vars should override TOML file values."""
        with patch.dict(os.environ, {"ARWIZ_TIMEOUT_SECONDS": "999"}, clear=False):
            with patch("arwiz.config.core.psutil") as mock_psutil:
                mock_psutil.virtual_memory.return_value.total = 16 * 1024**3
                config = loader.load_config(config_path=temp_toml)
        assert config.timeout_seconds == 999  # env overrides file's 60


class TestConfigValidation:
    """Test config validation raises on invalid values."""

    def test_negative_memory_raises(self, loader: DefaultConfigLoader) -> None:
        """memory_limit_mb <= 0 should raise ValueError."""
        with patch.dict(os.environ, {"ARWIZ_MEMORY_LIMIT_MB": "-1"}, clear=False):
            with patch("arwiz.config.core.psutil") as mock_psutil:
                mock_psutil.virtual_memory.return_value.total = 16 * 1024**3
                with pytest.raises(ValueError, match="memory_limit_mb"):
                    loader.load_config()

    def test_zero_timeout_raises(self, loader: DefaultConfigLoader) -> None:
        """timeout_seconds <= 0 should raise ValueError."""
        with patch.dict(os.environ, {"ARWIZ_TIMEOUT_SECONDS": "0"}, clear=False):
            with patch("arwiz.config.core.psutil") as mock_psutil:
                mock_psutil.virtual_memory.return_value.total = 16 * 1024**3
                with pytest.raises(ValueError, match="timeout_seconds"):
                    loader.load_config()

    def test_negative_timeout_raises(self, loader: DefaultConfigLoader) -> None:
        """Negative timeout_seconds should raise ValueError."""
        with patch.dict(os.environ, {"ARWIZ_TIMEOUT_SECONDS": "-10"}, clear=False):
            with patch("arwiz.config.core.psutil") as mock_psutil:
                mock_psutil.virtual_memory.return_value.total = 16 * 1024**3
                with pytest.raises(ValueError, match="timeout_seconds"):
                    loader.load_config()


class TestLlmEnvOverrides:
    """Test LLM-specific env var overrides."""

    def test_llm_provider_env(self, loader: DefaultConfigLoader) -> None:
        """ARWIZ_LLM_PROVIDER should be stored on the config."""
        with patch.dict(os.environ, {"ARWIZ_LLM_PROVIDER": "anthropic"}, clear=False):
            with patch("arwiz.config.core.psutil") as mock_psutil:
                mock_psutil.virtual_memory.return_value.total = 16 * 1024**3
                config = loader.load_config()
        assert config.llm_config.provider == "anthropic"

    def test_llm_model_env(self, loader: DefaultConfigLoader) -> None:
        """ARWIZ_LLM_MODEL should be stored on the config."""
        with patch.dict(os.environ, {"ARWIZ_LLM_MODEL": "claude-3-opus"}, clear=False):
            with patch("arwiz.config.core.psutil") as mock_psutil:
                mock_psutil.virtual_memory.return_value.total = 16 * 1024**3
                config = loader.load_config()
        assert config.llm_config.model == "claude-3-opus"
