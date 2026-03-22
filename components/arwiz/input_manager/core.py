from __future__ import annotations

import ast
import hashlib
import json
import warnings
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from arwiz.foundation import InputSnapshot
from arwiz.input_manager.storage import ensure_storage_dir


def _safe_repr(obj: Any) -> str:
    """Safely repr an object, returning a fallback for unrepresentable types."""
    try:
        return repr(obj)
    except Exception:
        return "<unrepresentable>"


def _json_safe_serialize(snapshot: InputSnapshot) -> str:
    """Serialize an InputSnapshot to JSON, handling non-serializable fields."""
    data = snapshot.model_dump()
    try:
        return json.dumps(data, indent=2)
    except (TypeError, ValueError) as exc:
        warnings.warn(
            f"Non-serializable data in snapshot {snapshot.snapshot_id}: {exc}",
            stacklevel=2,
        )
        # Fall back: replace problematic values with their repr strings
        safe_data = {}
        for k, v in data.items():
            try:
                json.dumps(v)
                safe_data[k] = v
            except (TypeError, ValueError):
                safe_data[k] = _safe_repr(v)
        return json.dumps(safe_data, indent=2)


class DefaultInputManager:
    def capture_input(self, function_name: str, args: tuple, kwargs: dict) -> InputSnapshot:
        args_repr = _safe_repr(args)
        kwargs_repr = _safe_repr(kwargs)

        raw = f"{function_name}:{args_repr}:{kwargs_repr}"
        content_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
        snapshot_id = f"inp_{content_hash}"

        return InputSnapshot(
            snapshot_id=snapshot_id,
            function_name=function_name,
            args_repr=args_repr,
            kwargs_repr=kwargs_repr,
            timestamp=datetime.now(UTC).isoformat(),
            content_hash=content_hash,
        )

    def store_input(self, snapshot: InputSnapshot, base_path: Path | None = None) -> Path:
        if base_path is None:
            base_path = Path.cwd()

        storage_dir = ensure_storage_dir(base_path)
        file_path = storage_dir / f"{snapshot.snapshot_id}.json"

        json_str = _json_safe_serialize(snapshot)
        file_path.write_text(json_str, encoding="utf-8")

        # Return the updated snapshot path
        return file_path

    def load_input(self, path: Path) -> InputSnapshot:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return InputSnapshot(**raw)

    def replay_input(self, snapshot: InputSnapshot, function: Callable) -> Any:
        try:
            args = ast.literal_eval(snapshot.args_repr)
        except (ValueError, SyntaxError):
            args = ()
        try:
            kwargs = ast.literal_eval(snapshot.kwargs_repr)
        except (ValueError, SyntaxError):
            kwargs = {}
        return function(*args, **kwargs)

    def list_inputs(self, base_path: Path | None = None) -> list[InputSnapshot]:
        if base_path is None:
            base_path = Path.cwd()

        storage_dir = base_path / ".arwiz" / "inputs"
        if not storage_dir.exists():
            return []

        snapshots: list[InputSnapshot] = []
        for json_file in sorted(storage_dir.glob("*.json")):
            try:
                snapshots.append(self.load_input(json_file))
            except (json.JSONDecodeError, ValueError):
                continue

        return snapshots
