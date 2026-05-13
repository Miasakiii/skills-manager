"""skillfmt HTTP API Server。

提供 RESTful API 供外部 agent 调用。
"""

from __future__ import annotations

from pathlib import Path

from ..logging import get_logger
from ..store import Store, StoreError

logger = get_logger(__name__)

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import JSONResponse, PlainTextResponse

    _FASTAPI_AVAILABLE = True
except ImportError:
    _FASTAPI_AVAILABLE = False


def create_app(store: Store | None = None) -> FastAPI:
    """创建 FastAPI 应用。"""
    if not _FASTAPI_AVAILABLE:
        raise RuntimeError("需要安装 fastapi：pip install skillfmt[server]")

    from ..adapters import get_adapter, list_formats
    from ..packager import pack

    app = FastAPI(
        title="Skillfmt API",
        description="AI Skill 格式转换与管理 HTTP API",
        version="0.1.0",
    )
    store_instance = store or Store()

    @app.get("/skills")
    def list_skills():
        skills = store_instance.list_all()
        return [
            {
                "name": s.name,
                "version": s.version,
                "category": getattr(s, "category", None),
                "description": getattr(s, "description", ""),
            }
            for s in skills
        ]

    @app.get("/skills/{name}")
    def get_skill(name: str):
        try:
            skill = store_instance.get(name)
            ir = store_instance.get_skill_ir(name)
            return {
                "name": ir.name,
                "version": ir.version,
                "description": ir.description,
                "summary": ir.summary,
                "tags": ir.tags,
                "category": ir.category,
                "author": ir.author,
                "parameters": [
                    {"name": p.name, "type": p.type, "description": p.description, "required": p.required}
                    for p in ir.parameters
                ],
                "installed_at": getattr(skill, "installed_at", ""),
                "source": getattr(skill, "source", ""),
            }
        except StoreError as e:
            raise HTTPException(status_code=404, detail=str(e))

    @app.get("/search")
    def search_skills(query: str, category: str | None = None, tag: str | None = None):
        results = store_instance.search(query, tag=tag, category=category)
        return [
            {
                "name": s.name,
                "version": s.version,
                "category": getattr(s, "category", None),
                "description": getattr(s, "description", ""),
            }
            for s in results
        ]

    @app.post("/skills/install")
    def install_skill(source: str, name: str | None = None, force: bool = False):
        try:
            source_path = Path(source)
            if source.startswith(("http://", "https://")):
                result = store_instance.install_from_url(source)
            elif source_path.suffix == ".skill":
                result = store_instance.install_from_package(source_path)
            else:
                result = store_instance.install(source_path, name=name, force=force)
            return {"name": result.name, "version": result.version}
        except StoreError as e:
            raise HTTPException(status_code=400, detail=str(e))

    @app.delete("/skills/{name}")
    def uninstall_skill(name: str):
        try:
            store_instance.uninstall(name)
            return {"message": f"Uninstalled {name}"}
        except StoreError as e:
            raise HTTPException(status_code=404, detail=str(e))

    @app.get("/skills/{name}/export")
    def export_skill(name: str, format: str = "openai"):
        try:
            ir = store_instance.get_skill_ir(name)
            adapter = get_adapter(format)
            content = adapter.export(ir)
            media_type = "text/x-python" if format == "mcp" else "application/json"
            return PlainTextResponse(content, media_type=media_type)
        except StoreError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    @app.get("/formats")
    def list_formats_endpoint():
        return {"formats": list_formats()}

    @app.get("/health")
    def health():
        skills = store_instance.list_all()
        return {
            "status": "ok",
            "installed_skills": len(skills),
            "store_path": str(store_instance.base_dir),
        }

    return app
