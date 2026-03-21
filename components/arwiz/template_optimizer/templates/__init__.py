from arwiz.template_optimizer.templates.add_caching import apply_add_caching
from arwiz.template_optimizer.templates.batch_io import apply_batch_io
from arwiz.template_optimizer.templates.numba_jit import apply_numba_jit
from arwiz.template_optimizer.templates.vectorize_loop import apply_vectorize_loop

__all__ = [
    "apply_vectorize_loop",
    "apply_numba_jit",
    "apply_add_caching",
    "apply_batch_io",
]
