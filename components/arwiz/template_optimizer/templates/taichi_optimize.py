_TAICHI_UNAVAILABLE_COMMENT = (
    "# NOTE: Taichi optimization is unavailable — "
    "Taichi requires Python <=3.10, but this project uses Python 3.12+.\n"
)


def apply_taichi_optimize(source_code: str) -> str:
    return _TAICHI_UNAVAILABLE_COMMENT + source_code
