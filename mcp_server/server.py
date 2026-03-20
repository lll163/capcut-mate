# AI-GEN-BEGIN
"""从 openapi.yaml 生成 MCP tools，将调用转发到 CapCut Mate REST API。"""

from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests
import yaml
from mcp.server import Server
from mcp.server.lowlevel.server import NotificationOptions
from mcp.server.stdio import stdio_server
from mcp.types import CallToolResult, ListToolsRequest, ListToolsResult, TextContent, Tool

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_OPENAPI = _REPO_ROOT / "openapi.yaml"
_DEFAULT_BASE = "http://127.0.0.1:30000/openapi/capcut-mate/v1"


@dataclass(frozen=True)
class RouteSpec:
    method: str
    path: str


def _strip_openapi_extensions(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {
            k: _strip_openapi_extensions(v)
            for k, v in obj.items()
            if not (isinstance(k, str) and k.startswith("x-"))
        }
    if isinstance(obj, list):
        return [_strip_openapi_extensions(i) for i in obj]
    return obj


def _ensure_object_schema(schema: dict[str, Any]) -> dict[str, Any]:
    if not schema:
        return {"type": "object", "properties": {}}
    s = _strip_openapi_extensions(schema)
    if s.get("type") != "object":
        return {"type": "object", "properties": {"payload": s}}
    return s


def load_tool_registry(
    openapi_path: Path | None = None,
) -> tuple[list[Tool], dict[str, RouteSpec]]:
    path = openapi_path or _DEFAULT_OPENAPI
    with path.open(encoding="utf-8") as f:
        spec = yaml.safe_load(f)

    tools: list[Tool] = []
    routes: dict[str, RouteSpec] = {}

    for raw_path, path_item in (spec.get("paths") or {}).items():
        if not isinstance(path_item, dict):
            continue
        post = path_item.get("post")
        if not isinstance(post, dict):
            continue
        op_id = post.get("operationId") or raw_path.strip("/").replace("/", "_")
        summary = (post.get("summary") or op_id).strip()
        body_schema = (
            (post.get("requestBody") or {})
            .get("content", {})
            .get("application/json", {})
            .get("schema", {})
        )
        input_schema = _ensure_object_schema(body_schema if isinstance(body_schema, dict) else {})
        tools.append(Tool(name=op_id, description=summary, inputSchema=input_schema))
        routes[op_id] = RouteSpec(method="POST", path=raw_path)

    extra: list[tuple[str, str, str, dict[str, Any]]] = [
        (
            "get_draft",
            "获取草稿文件列表",
            "GET",
            {
                "type": "object",
                "properties": {
                    "draft_id": {
                        "type": "string",
                        "description": "草稿 ID，长度 20–32",
                        "minLength": 20,
                        "maxLength": 32,
                    }
                },
                "required": ["draft_id"],
            },
        ),
        (
            "gen_video",
            "根据草稿 URL 提交云端渲染任务",
            "POST",
            {
                "type": "object",
                "properties": {"draft_url": {"type": "string", "description": "草稿 URL"}},
                "required": ["draft_url"],
            },
        ),
        (
            "gen_video_status",
            "查询云端渲染任务状态",
            "POST",
            {
                "type": "object",
                "properties": {"draft_url": {"type": "string", "description": "草稿 URL"}},
                "required": ["draft_url"],
            },
        ),
    ]
    for name, desc, method, schema in extra:
        if name in routes:
            continue
        tools.append(Tool(name=name, description=desc, inputSchema=schema))
        routes[name] = RouteSpec(method=method, path=f"/{name}" if not name.startswith("/") else name)

    for r in routes.values():
        if not r.path.startswith("/"):
            raise ValueError(f"invalid path: {r.path}")

    tools.sort(key=lambda t: t.name)
    return tools, routes


def _call_http(base_url: str, route: RouteSpec, arguments: dict[str, Any] | None) -> CallToolResult:
    args = arguments or {}
    url = base_url.rstrip("/") + route.path
    timeout = float(os.environ.get("CAPCUT_MATE_HTTP_TIMEOUT", "120"))
    try:
        if route.method == "GET":
            r = requests.get(url, params=args, timeout=timeout)
        else:
            r = requests.post(url, json=args, timeout=timeout)
        text = r.text
        try:
            parsed = r.json()
            text = json.dumps(parsed, ensure_ascii=False, indent=2)
        except Exception:
            pass
        if not r.ok:
            return CallToolResult(
                content=[TextContent(type="text", text=text or r.reason)],
                isError=True,
            )
        return CallToolResult(content=[TextContent(type="text", text=text or "{}")])
    except requests.RequestException as e:
        return CallToolResult(
            content=[TextContent(type="text", text=f"HTTP 请求失败: {e}")],
            isError=True,
        )


def create_app(
    openapi_path: Path | None = None,
    base_url: str | None = None,
) -> tuple[Server[Any, Any], dict[str, RouteSpec]]:
    tools, routes = load_tool_registry(openapi_path=openapi_path)
    base = (base_url or os.environ.get("CAPCUT_MATE_BASE_URL") or _DEFAULT_BASE).rstrip("/")

    server = Server("capcut-mate", version="1.0.0")

    @server.list_tools()
    async def _list_tools(_request: ListToolsRequest) -> ListToolsResult:
        return ListToolsResult(tools=tools)

    @server.call_tool()
    async def _call_tool(name: str, arguments: dict[str, Any] | None) -> CallToolResult:
        route = routes.get(name)
        if route is None:
            return CallToolResult(
                content=[TextContent(type="text", text=f"未知 tool: {name}")],
                isError=True,
            )
        return await asyncio.to_thread(_call_http, base, route, arguments)

    return server, routes


async def _run_stdio_async() -> None:
    openapi = os.environ.get("CAPCUT_MATE_OPENAPI_PATH")
    openapi_path = Path(openapi) if openapi else None
    server, _ = create_app(openapi_path=openapi_path)
    async with stdio_server() as (read_stream, write_stream):
        init = server.create_initialization_options()
        await server.run(
            read_stream,
            write_stream,
            init,
            raise_exceptions=False,
        )


def run_stdio() -> None:
    asyncio.run(_run_stdio_async())


# AI-GEN-END
