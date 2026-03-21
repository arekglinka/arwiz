from pathlib import Path

_ARWIZ_DIR = ".arwiz"
_INPUTS_DIR = "inputs"


def ensure_storage_dir(base_path: Path) -> Path:
    """Create `.arwiz/inputs/` directory if it does not exist. Return the path."""
    storage = base_path / _ARWIZ_DIR / _INPUTS_DIR
    storage.mkdir(parents=True, exist_ok=True)
    return storage


def generate_path(base_path: Path, snapshot_id: str) -> Path:
    """Generate file path for a snapshot."""
    storage = base_path / _ARWIZ_DIR / _INPUTS_DIR
    return storage / f"{snapshot_id}.json"
