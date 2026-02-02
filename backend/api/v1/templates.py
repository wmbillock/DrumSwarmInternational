"""V1 API — Template routes."""

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/v1")


@router.get("/templates")
def v1_list_templates():
    """List available show templates."""
    from pathlib import Path
    from backend.services.yaml_util import safe_load_yaml_dict
    templates_dir = Path("templates")
    if not templates_dir.exists():
        return []
    results = []
    for t in templates_dir.iterdir():
        if t.is_dir() and (t / "template.yaml").exists():
            with open(t / "template.yaml") as f:
                data = safe_load_yaml_dict(f.read())
            results.append({"id": t.name, **data})
    return results


@router.get("/templates/{template_id}")
def v1_get_template(template_id: str):
    """Get a single template."""
    from pathlib import Path
    from backend.services.yaml_util import safe_load_yaml_dict
    template_path = Path("templates") / template_id / "template.yaml"
    if not template_path.exists():
        raise HTTPException(404, "Template not found")
    with open(template_path) as f:
        data = safe_load_yaml_dict(f.read())
    return {"id": template_id, **data}


@router.post("/templates/{template_id}/instantiate")
def v1_instantiate_template(template_id: str, payload: dict):
    """Create a new show from a template."""
    from pathlib import Path
    import shutil
    from backend.services.yaml_util import safe_dump_yaml, safe_load_yaml_dict
    template_dir = Path("templates") / template_id
    if not template_dir.exists():
        raise HTTPException(404, "Template not found")
    slug = payload.get("slug", template_id + "-instance")
    show_dir = Path("shows") / slug
    if show_dir.exists():
        raise HTTPException(409, "Show already exists")
    shutil.copytree(template_dir, show_dir)
    status_path = show_dir / "status.yaml"
    if status_path.exists():
        with open(status_path) as f:
            status = safe_load_yaml_dict(f.read())
        status["status"] = "draft"
        status["title"] = payload.get("title", slug)
        with open(status_path, "w") as f:
            f.write(safe_dump_yaml(status))
    return {"slug": slug, "status": "created"}
