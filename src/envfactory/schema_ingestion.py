"""OpenAPI / Swagger schema ingestion and normalization."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class ParamDef:
    name: str
    location: str  # path, query, header, cookie
    schema_type: str  # string, integer, number, boolean, array, object
    required: bool = False
    schema: dict[str, Any] = field(default_factory=dict)


@dataclass
class EndpointDef:
    method: str
    path: str
    operation_id: str
    path_params: list[ParamDef] = field(default_factory=list)
    query_params: list[ParamDef] = field(default_factory=list)
    request_body_schema: dict[str, Any] | None = None
    response_schemas: dict[str, dict[str, Any]] = field(default_factory=dict)


@dataclass
class NormalizedSpec:
    title: str
    version: str
    base_url: str
    endpoints: list[EndpointDef] = field(default_factory=list)


class SchemaIngester:
    def load(self, path_or_url: str) -> NormalizedSpec:
        raw = self._read(path_or_url)
        if "openapi" in raw:
            return self._parse_openapi3(raw)
        if "swagger" in raw:
            return self._parse_swagger2(raw)
        raise ValueError("Unsupported spec format: expected OpenAPI 3.x or Swagger 2.0")

    def _read(self, path_or_url: str) -> dict:
        if path_or_url.startswith(("http://", "https://")):
            import requests
            resp = requests.get(path_or_url, timeout=30)
            resp.raise_for_status()
            text = resp.text
        else:
            text = Path(path_or_url).read_text()
        try:
            return yaml.safe_load(text)
        except yaml.YAMLError:
            return json.loads(text)

    def _resolve_ref(self, root: dict, ref: str, _seen: set[str] | None = None) -> dict:
        if _seen is None:
            _seen = set()
        if ref in _seen:
            return {}
        _seen.add(ref)
        parts = ref.lstrip("#/").split("/")
        node = root
        for p in parts:
            node = node[p]
        if isinstance(node, dict) and "$ref" in node:
            return self._resolve_ref(root, node["$ref"], _seen)
        return node

    def _resolve_deep(self, root: dict, obj: Any) -> Any:
        if isinstance(obj, dict):
            if "$ref" in obj:
                resolved = self._resolve_ref(root, obj["$ref"])
                return self._resolve_deep(root, resolved)
            return {k: self._resolve_deep(root, v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [self._resolve_deep(root, item) for item in obj]
        return obj

    def _parse_openapi3(self, raw: dict) -> NormalizedSpec:
        info = raw.get("info", {})
        servers = raw.get("servers", [{}])
        base_url = servers[0].get("url", "") if servers else ""
        spec = NormalizedSpec(
            title=info.get("title", ""),
            version=info.get("version", ""),
            base_url=base_url,
        )
        for path, path_item in raw.get("paths", {}).items():
            path_item = self._resolve_deep(raw, path_item)
            common_params = path_item.get("parameters", [])
            for method in ("get", "post", "put", "patch", "delete", "head", "options"):
                if method not in path_item:
                    continue
                op = path_item[method]
                op = self._resolve_deep(raw, op)
                all_params = common_params + op.get("parameters", [])
                path_params = []
                query_params = []
                for p in all_params:
                    p = self._resolve_deep(raw, p)
                    pdef = ParamDef(
                        name=p.get("name", ""),
                        location=p.get("in", "query"),
                        schema_type=p.get("schema", {}).get("type", "string"),
                        required=p.get("required", False),
                        schema=p.get("schema", {}),
                    )
                    if pdef.location == "path":
                        pdef.required = True
                        path_params.append(pdef)
                    elif pdef.location == "query":
                        query_params.append(pdef)

                body_schema = None
                rb = op.get("requestBody", {})
                if rb:
                    content = rb.get("content", {})
                    json_ct = content.get("application/json", {})
                    body_schema = self._resolve_deep(raw, json_ct.get("schema")) if json_ct else None

                response_schemas: dict[str, dict] = {}
                for code, resp_obj in op.get("responses", {}).items():
                    resp_obj = self._resolve_deep(raw, resp_obj)
                    content = resp_obj.get("content", {})
                    json_ct = content.get("application/json", {})
                    if json_ct and "schema" in json_ct:
                        response_schemas[str(code)] = self._resolve_deep(raw, json_ct["schema"])

                op_id = op.get("operationId", f"{method}_{path.replace('/', '_').strip('_')}")
                spec.endpoints.append(EndpointDef(
                    method=method.upper(),
                    path=path,
                    operation_id=op_id,
                    path_params=path_params,
                    query_params=query_params,
                    request_body_schema=body_schema,
                    response_schemas=response_schemas,
                ))
        return spec

    def _parse_swagger2(self, raw: dict) -> NormalizedSpec:
        info = raw.get("info", {})
        host = raw.get("host", "")
        base_path = raw.get("basePath", "")
        schemes = raw.get("schemes", ["https"])
        base_url = f"{schemes[0]}://{host}{base_path}" if host else base_path
        spec = NormalizedSpec(
            title=info.get("title", ""),
            version=info.get("version", ""),
            base_url=base_url,
        )
        for path, path_item in raw.get("paths", {}).items():
            path_item = self._resolve_deep(raw, path_item)
            common_params = path_item.get("parameters", [])
            for method in ("get", "post", "put", "patch", "delete", "head", "options"):
                if method not in path_item:
                    continue
                op = path_item[method]
                op = self._resolve_deep(raw, op)
                all_params = common_params + op.get("parameters", [])
                path_params = []
                query_params = []
                body_schema = None
                for p in all_params:
                    p = self._resolve_deep(raw, p)
                    loc = p.get("in", "query")
                    if loc == "body":
                        body_schema = p.get("schema")
                        continue
                    ptype = p.get("type", "string")
                    pdef = ParamDef(
                        name=p.get("name", ""),
                        location=loc,
                        schema_type=ptype,
                        required=p.get("required", False),
                        schema={"type": ptype},
                    )
                    if loc == "path":
                        pdef.required = True
                        path_params.append(pdef)
                    elif loc == "query":
                        query_params.append(pdef)

                response_schemas: dict[str, dict] = {}
                for code, resp_obj in op.get("responses", {}).items():
                    resp_obj = self._resolve_deep(raw, resp_obj)
                    if "schema" in resp_obj:
                        response_schemas[str(code)] = self._resolve_deep(raw, resp_obj["schema"])

                op_id = op.get("operationId", f"{method}_{path.replace('/', '_').strip('_')}")
                spec.endpoints.append(EndpointDef(
                    method=method.upper(),
                    path=path,
                    operation_id=op_id,
                    path_params=path_params,
                    query_params=query_params,
                    request_body_schema=body_schema,
                    response_schemas=response_schemas,
                ))
        return spec
