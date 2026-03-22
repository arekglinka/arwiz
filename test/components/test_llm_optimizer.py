import httpx
import pytest
from arwiz.foundation import HotSpot, LLMConfig
from arwiz.llm_optimizer.core import DefaultLLMOptimizer


@pytest.fixture
def hotspot() -> HotSpot:
    return HotSpot(
        function_name="compute_sum",
        file_path="/tmp/simple_loop.py",
        line_range=(10, 20),
        cumulative_time_ms=321.0,
        self_time_ms=300.0,
        call_count=100,
        potential_speedup=2.0,
    )


class MockProvider:
    def generate(self, _prompt: str, _model: str, **kwargs: object) -> str:  # noqa: ARG002
        return "```python\ndef optimized(x):\n    return x * 2\n```"


class BadMockProvider:
    def generate(self, _prompt: str, _model: str, **kwargs: object) -> str:  # noqa: ARG002
        return "```python\ndef broken(\n```"


def test_parse_llm_response_extracts_from_markdown() -> None:
    optimizer = DefaultLLMOptimizer()
    response = """Some explanation
```python
def compute_sum(data):
    return sum(x * x for x in data)
```
"""
    parsed = optimizer.parse_llm_response(response)
    assert "def compute_sum" in parsed
    assert "```" not in parsed


def test_parse_llm_response_extracts_from_plain() -> None:
    optimizer = DefaultLLMOptimizer()
    response = "Here is optimized code:\n\ndef optimized(x):\n    return x * 2\n"
    parsed = optimizer.parse_llm_response(response)
    assert parsed.startswith("def optimized")


def test_validate_syntax_accepts_valid() -> None:
    optimizer = DefaultLLMOptimizer()
    ok, error = optimizer.validate_syntax("def foo():\n    pass")
    assert ok is True
    assert error == ""


def test_validate_syntax_rejects_invalid() -> None:
    optimizer = DefaultLLMOptimizer()
    ok, error = optimizer.validate_syntax("def broken(")
    assert ok is False
    assert error


def test_generate_prompt_includes_source(hotspot: HotSpot) -> None:
    optimizer = DefaultLLMOptimizer()
    source = "def compute_sum(data):\n    return sum(data)"
    prompt = optimizer.generate_prompt(source, hotspot)
    assert source in prompt


def test_generate_prompt_includes_profiling_data(hotspot: HotSpot) -> None:
    optimizer = DefaultLLMOptimizer()
    source = "def compute_sum(data):\n    return sum(data)"
    prompt = optimizer.generate_prompt(source, hotspot)
    assert hotspot.function_name in prompt
    assert str(hotspot.self_time_ms) in prompt
    assert str(hotspot.call_count) in prompt


def test_optimize_function_with_mock_provider(hotspot: HotSpot) -> None:
    optimizer = DefaultLLMOptimizer()
    optimizer.provider = MockProvider()
    source = (
        "def compute_sum(data):\n"
        "    total = 0\n"
        "    for x in data:\n"
        "        total += x*x\n"
        "    return total"
    )

    attempt = optimizer.optimize_function(
        source,
        hotspot,
        config=LLMConfig(provider="openai", model="gpt-4o", api_key_env_var="OPENAI_API_KEY"),
    )

    assert attempt.original_code == source
    assert "def optimized" in attempt.optimized_code
    assert attempt.syntax_valid is True
    assert attempt.strategy == "llm_generated"
    assert attempt.llm_model == "gpt-4o"


def test_optimize_function_handles_invalid_code(hotspot: HotSpot) -> None:
    optimizer = DefaultLLMOptimizer()
    optimizer.provider = BadMockProvider()
    source = "def compute_sum(data):\n    return sum(data)"

    attempt = optimizer.optimize_function(
        source,
        hotspot,
        config=LLMConfig(provider="openai", model="gpt-4o", api_key_env_var="OPENAI_API_KEY"),
    )

    assert attempt.syntax_valid is False
    assert attempt.error_message


class EmptyMockProvider:
    def generate(self, _prompt: str, _model: str, **kwargs: object) -> str:  # noqa: ARG002
        return ""


class TimeoutMockProvider:
    def generate(self, _prompt: str, _model: str, **kwargs: object) -> str:  # noqa: ARG002
        raise httpx.TimeoutException("request timed out")


class HTTPErrorMockProvider:
    def generate(self, _prompt: str, _model: str, **kwargs: object) -> str:  # noqa: ARG002
        raise httpx.HTTPStatusError(
            "429 Too Many Requests",
            request=httpx.Request("POST", "http://fake"),
            response=httpx.Response(429),
        )


class GenericErrorMockProvider:
    def generate(self, _prompt: str, _model: str, **kwargs: object) -> str:  # noqa: ARG002
        raise RuntimeError("connection refused")


class NoCodeBlockProvider:
    def generate(self, _prompt: str, _model: str, **kwargs: object) -> str:  # noqa: ARG002
        return "I cannot optimize this code. Sorry."


class MultiCodeBlockProvider:
    def generate(self, _prompt: str, _model: str, **kwargs: object) -> str:  # noqa: ARG002
        return (
            "```python\n"
            "def first_optimized(x):\n"
            "    return x * 2\n"
            "```\n"
            "Explanation text\n"
            "```python\n"
            "def second_optimized(x):\n"
            "    return x * 3\n"
            "```\n"
        )


class TestProviderErrors:
    def test_empty_provider_response(self, hotspot: HotSpot) -> None:
        optimizer = DefaultLLMOptimizer()
        optimizer.provider = EmptyMockProvider()
        source = "def compute_sum(data):\n    return sum(data)"

        attempt = optimizer.optimize_function(
            source,
            hotspot,
            config=LLMConfig(provider="openai", model="gpt-4o", api_key_env_var="OPENAI_API_KEY"),
        )

        assert attempt.optimized_code == ""
        assert attempt.syntax_valid is True
        assert attempt.strategy == "llm_generated"

    def test_provider_timeout_returns_graceful_error(self, hotspot: HotSpot) -> None:
        optimizer = DefaultLLMOptimizer()
        optimizer.provider = TimeoutMockProvider()
        source = "def compute_sum(data):\n    return sum(data)"

        attempt = optimizer.optimize_function(
            source,
            hotspot,
            config=LLMConfig(provider="openai", model="gpt-4o", api_key_env_var="OPENAI_API_KEY"),
        )

        assert attempt.optimized_code == source
        assert attempt.syntax_valid is False
        assert attempt.error_message is not None
        assert (
            "timeout" in attempt.error_message.lower()
            or "timed out" in attempt.error_message.lower()
        )

    def test_provider_http_error_returns_graceful(self, hotspot: HotSpot) -> None:
        optimizer = DefaultLLMOptimizer()
        optimizer.provider = HTTPErrorMockProvider()
        source = "def compute_sum(data):\n    return sum(data)"

        attempt = optimizer.optimize_function(
            source,
            hotspot,
            config=LLMConfig(provider="openai", model="gpt-4o", api_key_env_var="OPENAI_API_KEY"),
        )

        assert attempt.optimized_code == source
        assert attempt.syntax_valid is False
        assert attempt.error_message is not None
        assert "429" in attempt.error_message

    def test_provider_generic_error_returns_graceful(self, hotspot: HotSpot) -> None:
        optimizer = DefaultLLMOptimizer()
        optimizer.provider = GenericErrorMockProvider()
        source = "def compute_sum(data):\n    return sum(data)"

        attempt = optimizer.optimize_function(
            source,
            hotspot,
            config=LLMConfig(provider="openai", model="gpt-4o", api_key_env_var="OPENAI_API_KEY"),
        )

        assert attempt.optimized_code == source
        assert attempt.syntax_valid is False
        assert attempt.error_message is not None
        assert "connection refused" in attempt.error_message

    def test_parse_empty_python_code_block(self) -> None:
        optimizer = DefaultLLMOptimizer()
        parsed = optimizer.parse_llm_response("```python\n```")

        assert parsed == ""

    def test_no_code_block_yields_error(self, hotspot: HotSpot) -> None:
        optimizer = DefaultLLMOptimizer()
        optimizer.provider = NoCodeBlockProvider()
        source = "def compute_sum(data):\n    return sum(data)"

        attempt = optimizer.optimize_function(
            source,
            hotspot,
            config=LLMConfig(provider="openai", model="gpt-4o", api_key_env_var="OPENAI_API_KEY"),
        )

        assert attempt.syntax_valid is False
        assert attempt.error_message is not None

    def test_multiple_code_blocks_uses_first(self) -> None:
        optimizer = DefaultLLMOptimizer()
        response = (
            "```python\ndef first_optimized(x):\n    return x * 2\n```\n"
            "Explanation\n"
            "```python\ndef second_optimized(x):\n    return x * 3\n```"
        )
        parsed = optimizer.parse_llm_response(response)

        assert "def first_optimized" in parsed
        assert "def second_optimized" not in parsed

    def test_prompt_includes_full_hotspot_info(self, hotspot: HotSpot) -> None:
        optimizer = DefaultLLMOptimizer()
        source = "def compute_sum(data):\n    return sum(data)"
        prompt = optimizer.generate_prompt(source, hotspot, strategy="caching")

        assert hotspot.function_name in prompt
        assert str(hotspot.self_time_ms) in prompt
        assert str(hotspot.call_count) in prompt
        assert str(hotspot.cumulative_time_ms) in prompt
        assert hotspot.file_path in prompt
        assert source in prompt


class TestApiKeyValidation:
    def test_openai_empty_key_raises(self) -> None:
        from arwiz.llm_optimizer.providers import OpenAIProvider

        provider = OpenAIProvider(api_key="")
        with pytest.raises(ValueError, match="API key is required"):
            provider.generate("test prompt", "gpt-4o")

    def test_anthropic_empty_key_raises(self) -> None:
        from arwiz.llm_optimizer.providers import AnthropicProvider

        provider = AnthropicProvider(api_key="")
        with pytest.raises(ValueError, match="API key is required"):
            provider.generate("test prompt", "claude-3-opus")

    def test_openai_whitespace_key_raises(self) -> None:
        from arwiz.llm_optimizer.providers import OpenAIProvider

        provider = OpenAIProvider(api_key="   ")
        with pytest.raises(ValueError, match="API key is required"):
            provider.generate("test prompt", "gpt-4o")

    def test_ollama_no_key_needed(self) -> None:
        from arwiz.llm_optimizer.providers import OllamaProvider

        provider = OllamaProvider()
        # Should NOT raise — Ollama has no API key validation
        # (it will fail on connection, but that's different)
        assert provider.base_url == "http://localhost:11434"
