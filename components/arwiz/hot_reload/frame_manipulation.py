"""CPython 3.13 specific frame variable manipulation.

WARNING: This is CPython-version-specific and fragile. Not guaranteed
to work across Python versions or implementations. Uses internal CPython
APIs via ctypes.
"""

from __future__ import annotations

import ctypes
import sys
from types import FrameType


def is_cpython() -> bool:
    return sys.implementation.name == "cpython"


def inject_variable(frame: FrameType, var_name: str, value: object) -> None:
    """Set a local variable in a frame using PyFrame_LocalsToFast.

    Direct assignment to frame.f_locals does not update fast locals,
    so we use ctypes to call the internal CPython sync function.
    """
    if not is_cpython():
        raise RuntimeError("Frame manipulation requires CPython")

    frame.f_locals[var_name] = value
    try:
        ctypes.pythonapi.PyFrame_LocalsToFast(
            ctypes.py_object(frame),
            ctypes.c_int(0),
        )
    except (AttributeError, OSError) as exc:
        raise RuntimeError(f"Failed to inject variable into frame: {exc}") from exc
