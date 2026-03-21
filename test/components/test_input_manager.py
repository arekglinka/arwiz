"""Tests for arwiz.input_manager — Input capture, storage, and replay."""

from pathlib import Path

import pytest
from arwiz.input_manager.core import DefaultInputManager


@pytest.fixture
def manager() -> DefaultInputManager:
    return DefaultInputManager()


def add(a: int, b: int) -> int:
    return a + b


def multiply(a: int, b: int) -> int:
    return a * b


class TestCaptureInput:
    def test_capture_basic(self, manager: DefaultInputManager) -> None:
        snapshot = manager.capture_input("add", (1, 2), {})
        assert snapshot.function_name == "add"
        assert snapshot.snapshot_id.startswith("inp_")

    def test_capture_with_kwargs(self, manager: DefaultInputManager) -> None:
        snapshot = manager.capture_input("func", (), {"x": 10, "y": 20})
        assert "x" in snapshot.kwargs_repr
        assert "y" in snapshot.kwargs_repr

    def test_capture_content_hash(self, manager: DefaultInputManager) -> None:
        s1 = manager.capture_input("f", (1,), {})
        s2 = manager.capture_input("f", (1,), {})
        s3 = manager.capture_input("f", (2,), {})
        assert s1.content_hash == s2.content_hash
        assert s1.content_hash != s3.content_hash

    def test_capture_various_types(self, manager: DefaultInputManager) -> None:
        snapshot = manager.capture_input("f", ([1, 2, 3], "hello"), {"flag": True})
        assert snapshot.args_repr is not None
        assert snapshot.kwargs_repr is not None


class TestStoreAndLoad:
    def test_store_creates_file(self, manager: DefaultInputManager, tmp_path: Path) -> None:
        snapshot = manager.capture_input("add", (1, 2), {})
        path = manager.store_input(snapshot, base_path=tmp_path)
        assert path.exists()
        assert path.suffix == ".json"

    def test_load_roundtrip(self, manager: DefaultInputManager, tmp_path: Path) -> None:
        original = manager.capture_input("add", (5, 3), {})
        stored_path = manager.store_input(original, base_path=tmp_path)
        loaded = manager.load_input(stored_path)
        assert loaded.snapshot_id == original.snapshot_id
        assert loaded.function_name == original.function_name
        assert loaded.content_hash == original.content_hash

    def test_store_creates_arwiz_dir(self, manager: DefaultInputManager, tmp_path: Path) -> None:
        snapshot = manager.capture_input("f", (), {})
        manager.store_input(snapshot, base_path=tmp_path)
        assert (tmp_path / ".arwiz" / "inputs").is_dir()


class TestReplayInput:
    def test_replay_produces_same_result(self, manager: DefaultInputManager) -> None:
        snapshot = manager.capture_input("add", (3, 7), {})
        result = manager.replay_input(snapshot, add)
        assert result == 10

    def test_replay_with_kwargs(self, manager: DefaultInputManager) -> None:
        snapshot = manager.capture_input("multiply", (), {"a": 4, "b": 5})
        result = manager.replay_input(snapshot, multiply)
        assert result == 20


class TestListInputs:
    def test_list_empty(self, manager: DefaultInputManager, tmp_path: Path) -> None:
        inputs = manager.list_inputs(base_path=tmp_path)
        assert inputs == []

    def test_list_stored_inputs(self, manager: DefaultInputManager, tmp_path: Path) -> None:
        s1 = manager.capture_input("add", (1, 2), {})
        s2 = manager.capture_input("multiply", (3, 4), {})
        manager.store_input(s1, base_path=tmp_path)
        manager.store_input(s2, base_path=tmp_path)
        inputs = manager.list_inputs(base_path=tmp_path)
        assert len(inputs) == 2
        names = {i.function_name for i in inputs}
        assert names == {"add", "multiply"}


class TestNonSerializableWarning:
    def test_non_serializable_no_crash(self, manager: DefaultInputManager, tmp_path: Path) -> None:
        class NonSerializable:
            pass

        snapshot = manager.capture_input("f", (NonSerializable(),), {})
        import warnings

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            manager.store_input(snapshot, base_path=tmp_path)
            assert len(w) == 0
