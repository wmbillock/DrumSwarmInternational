"""V1 Images API — image generation via ComfyUI."""

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/images", tags=["images"])


class GenerateRequest(BaseModel):
    prompt: str
    negative_prompt: str = ""
    width: int = 1024
    height: int = 1024
    steps: int = 20
    cfg_scale: float = 7.0
    seed: Optional[int] = None
    output_filename: Optional[str] = None


class WorkflowRequest(BaseModel):
    workflow_name: str
    template_vars: Optional[dict] = None
    seed: Optional[int] = None
    output_filename: Optional[str] = None


@router.get("/status")
def image_status():
    """Check if image generation is available."""
    from backend.services.image_service import check_status
    return check_status()


@router.get("/workflows")
def list_workflows():
    """List available workflow templates."""
    from backend.services.image_service import list_workflows
    return list_workflows()


@router.post("/generate")
def generate_image(req: GenerateRequest):
    """Generate an image from a text prompt."""
    from backend.services.image_service import generate_image
    result = generate_image(
        prompt=req.prompt,
        negative_prompt=req.negative_prompt,
        width=req.width,
        height=req.height,
        steps=req.steps,
        cfg_scale=req.cfg_scale,
        seed=req.seed,
        output_filename=req.output_filename,
    )
    if not result["success"]:
        raise HTTPException(503, result["error"])
    return result


@router.post("/generate/workflow")
def generate_from_workflow(req: WorkflowRequest):
    """Generate an image using a named workflow template."""
    from backend.services.image_service import generate_from_workflow
    result = generate_from_workflow(
        workflow_name=req.workflow_name,
        template_vars=req.template_vars,
        seed=req.seed,
        output_filename=req.output_filename,
    )
    if not result["success"]:
        raise HTTPException(503, result["error"])
    return result
