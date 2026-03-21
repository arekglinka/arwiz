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
