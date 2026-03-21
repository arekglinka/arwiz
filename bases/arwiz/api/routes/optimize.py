from pathlib import Path

from arwiz.api.models import OptimizeRequest, OptimizeResponse
from arwiz.template_optimizer import DefaultTemplateOptimizer
from fastapi import APIRouter

router = APIRouter(tags=["optimize"])


@router.post("/optimize", response_model=OptimizeResponse)
async def post_optimize(req: OptimizeRequest):
    source = Path(req.script_path).read_text(encoding="utf-8")
    optimizer = DefaultTemplateOptimizer()

    template_name = req.strategy if req.strategy != "auto" else "numba_jit"
    optimized = optimizer.apply_template(source, template_name)

    try:
        compile(optimized, req.script_path, "exec")
        syntax_valid = True
    except SyntaxError:
        syntax_valid = False

    return OptimizeResponse(
        original_code=source,
        optimized_code=optimized,
        strategy=template_name,
        syntax_valid=syntax_valid,
    )
