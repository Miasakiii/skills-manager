"""skillfmt HTTP API Server。

提供 RESTful API 供外部 agent 调用。
"""

from __future__ import annotations

import hmac
import os
import re
from pathlib import Path

from ..logging import get_logger
from ..security import sanitize_name
from ..store import Store, StoreError

logger = get_logger(__name__)

# 允许的 URL scheme 和 GitHub 域名
_ALLOWED_URL_SCHEMES = ("http://", "https://")
_ALLOWED_GITHUB_DOMAINS = ("github.com", "raw.githubusercontent.com")

# 可选 API 认证：设置此环境变量后，所有请求必须携带匹配的 Bearer token。
# 未设置时保持本地工具的开放行为（不强制认证）。
_API_KEY_ENV = "SKILLFMT_API_KEY"


def _validate_source(source: str) -> str:
    """验证并清理 install 来源，拒绝危险输入。

    Returns:
        清理后的 source 字符串。

    Raises:
        ValueError: source 不合法。
    """
    if not source or not source.strip():
        raise ValueError("source 不能为空")

    source = source.strip()

    # URL 来源：只允许 http(s)，且只允许白名单域名
    if source.startswith(_ALLOWED_URL_SCHEMES):
        # 从 URL 中提取域名
        scheme_end = source.find("://")
        if scheme_end == -1:
            raise ValueError("无效的 URL")
        rest = source[scheme_end + 3 :]
        domain = rest.split("/")[0].split(":")[0].lower()
        # 允许 GitHub 和其 raw 域名
        if not any(
            domain == d or domain.endswith("." + d) for d in _ALLOWED_GITHUB_DOMAINS
        ):
            raise ValueError(f"不允许的 URL 域名: {domain}")
        return source

    # 本地路径：禁止 null 字节和明显的路径遍历
    if "\x00" in source:
        raise ValueError("source 包含非法字符")
    if ".." in source:
        raise ValueError("source 不能包含 .. 路径遍历")

    return source

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import PlainTextResponse

    _FASTAPI_AVAILABLE = True
except ImportError:
    _FASTAPI_AVAILABLE = False


def create_app(store: Store | None = None) -> FastAPI:
    """创建 FastAPI 应用。"""
    if not _FASTAPI_AVAILABLE:
        raise RuntimeError("需要安装 fastapi：pip install skillfmt[server]")

    from ..adapters import get_adapter, list_formats

    app = FastAPI(
        title="Skillfmt API",
        description="AI Skill 格式转换与管理 HTTP API",
        version="0.1.0",
    )
    store_instance = store or Store()

    # 可选认证：设置 SKILLFMT_API_KEY 后强制校验 Bearer token。
    expected_api_key = os.environ.get(_API_KEY_ENV, "").strip()
    if expected_api_key:
        logger.info("API 认证已启用（SKILLFMT_API_KEY 已设置）")

    def _verify_api_key(authorization: str | None = None) -> None:
        """当 SKILLFMT_API_KEY 设置时，校验请求头中的 Bearer token。

        使用 ``hmac.compare_digest`` 做常量时间比较，防止时序攻击。
        """
        if not expected_api_key:
            return  # 未配置 API key，保持开放（本地工具）

        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=401,
                detail="Missing or invalid Authorization header (expected Bearer token)",
                headers={"WWW-Authenticate": "Bearer"},
            )
        token = authorization[len("Bearer ") :].strip()
        if not hmac.compare_digest(token, expected_api_key):
            raise HTTPException(
                status_code=403,
                detail="Invalid API key",
                headers={"WWW-Authenticate": "Bearer"},
            )

    @app.get("/skills")
    def list_skills(authorization: str | None = None):
        _verify_api_key(authorization)
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
    def get_skill(name: str, authorization: str | None = None):
        _verify_api_key(authorization)
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
                    {
                        "name": p.name,
                        "type": p.type,
                        "description": p.description,
                        "required": p.required,
                    }
                    for p in ir.parameters
                ],
                "installed_at": getattr(skill, "installed_at", ""),
                "source": getattr(skill, "source", ""),
            }
        except StoreError as e:
            raise HTTPException(status_code=404, detail=str(e))

    @app.get("/search")
    def search_skills(
        query: str,
        category: str | None = None,
        tag: str | None = None,
        authorization: str | None = None,
    ):
        _verify_api_key(authorization)
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
    def install_skill(
        source: str,
        name: str | None = None,
        force: bool = False,
        authorization: str | None = None,
    ):
        _verify_api_key(authorization)
        try:
            # 验证输入
            source = _validate_source(source)
            if name is not None:
                name = sanitize_name(name)

            source_path = Path(source)
            if source.startswith(("http://", "https://")):
                result = store_instance.install_from_url(source)
            elif source_path.suffix == ".skill":
                result = store_instance.install_from_package(source_path)
            else:
                result = store_instance.install(source_path, name=name, force=force)
            return {"name": result.name, "version": result.version}
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except StoreError as e:
            raise HTTPException(status_code=400, detail=str(e))

    @app.delete("/skills/{name}")
    def uninstall_skill(name: str, authorization: str | None = None):
        _verify_api_key(authorization)
        try:
            store_instance.uninstall(name)
            return {"message": f"Uninstalled {name}"}
        except StoreError as e:
            raise HTTPException(status_code=404, detail=str(e))

    @app.get("/skills/{name}/export")
    def export_skill(
        name: str, format: str = "openai", authorization: str | None = None
    ):
        _verify_api_key(authorization)
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
    def list_formats_endpoint(authorization: str | None = None):
        _verify_api_key(authorization)
        return {"formats": list_formats()}

    @app.get("/health")
    def health(authorization: str | None = None):
        # 健康检查通常不需要认证，便于探活；但若配置了 API key 仍要求认证
        _verify_api_key(authorization)
        skills = store_instance.list_all()
        return {
            "status": "ok",
            "installed_skills": len(skills),
            "store_path": str(store_instance.base_dir),
        }

    return app
