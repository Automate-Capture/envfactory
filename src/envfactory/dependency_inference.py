"""Infer inter-endpoint dependencies from schema structure."""

from __future__ import annotations

import re
from typing import Any

import networkx as nx

from envfactory.schema_ingestion import EndpointDef, NormalizedSpec


def _extract_response_field_names(schema: dict[str, Any], prefix: str = "") -> list[str]:
    fields: list[str] = []
    if not isinstance(schema, dict):
        return fields
    schema_type = schema.get("type", "object")
    if schema_type == "object":
        for name, prop in schema.get("properties", {}).items():
            fields.append(name)
            fields.extend(_extract_response_field_names(prop, prefix=f"{name}."))
    elif schema_type == "array":
        items = schema.get("items", {})
        fields.extend(_extract_response_field_names(items, prefix))
    return fields


def _field_name_similarity(param_name: str, field_name: str) -> float:
    if param_name == field_name:
        return 1.0
    pn = param_name.lower().replace("_", "").replace("-", "")
    fn = field_name.lower().replace("_", "").replace("-", "")
    if pn == fn:
        return 0.95
    if pn.endswith("id") and fn.endswith("id") and pn == fn:
        return 0.9
    if pn in fn or fn in pn:
        return 0.6
    return 0.0


def _schema_type_compatible(param_type: str, field_schema: dict[str, Any]) -> bool:
    field_type = field_schema.get("type", "string") if isinstance(field_schema, dict) else "string"
    if param_type == field_type:
        return True
    compatible = {
        ("integer", "number"),
        ("number", "integer"),
        ("string", "integer"),
        ("string", "number"),
    }
    return (param_type, field_type) in compatible


_CREATION_METHODS = {"POST"}
_MUTATION_METHODS = {"PUT", "PATCH", "DELETE"}
_PATH_PARAM_RE = re.compile(r"\{(\w+)\}")


class DependencyInferrer:
    def infer(self, endpoints: list[EndpointDef]) -> nx.DiGraph:
        g = nx.DiGraph()
        for ep in endpoints:
            g.add_node(ep.operation_id, endpoint=ep)

        for consumer in endpoints:
            needed_params = [p.name for p in consumer.path_params]
            if not needed_params:
                continue

            for param_name in needed_params:
                best_score = 0.0
                best_producer = None
                best_field = None

                for producer in endpoints:
                    if producer.operation_id == consumer.operation_id:
                        continue
                    for code, resp_schema in producer.response_schemas.items():
                        if not code.startswith("2"):
                            continue
                        fields = _extract_response_field_names(resp_schema)
                        for fn in fields:
                            score = _field_name_similarity(param_name, fn)
                            if score > best_score:
                                ptype = next(
                                    (p.schema_type for p in consumer.path_params if p.name == param_name),
                                    "string",
                                )
                                prop_schema = resp_schema.get("properties", {}).get(fn, {})
                                items_props = resp_schema.get("items", {}).get("properties", {}).get(fn, {})
                                effective_schema = prop_schema or items_props or {}
                                if _schema_type_compatible(ptype, effective_schema) or score >= 0.9:
                                    best_score = score
                                    best_producer = producer
                                    best_field = fn

                if best_producer and best_score > 0.3:
                    g.add_edge(
                        best_producer.operation_id,
                        consumer.operation_id,
                        param_name=param_name,
                        source_field=best_field,
                        score=best_score,
                        confirmed=False,
                        parameter_bindings={},
                    )

        for ep in endpoints:
            if ep.method in _MUTATION_METHODS:
                params_in_path = _PATH_PARAM_RE.findall(ep.path)
                if not params_in_path:
                    continue
                base_path_pattern = ep.path
                for pname in params_in_path:
                    base_path_pattern = base_path_pattern.replace(f"{{{pname}}}", r"\{[^}]+\}")
                for candidate in endpoints:
                    if candidate.method == "POST" and candidate.operation_id != ep.operation_id:
                        if ep.path.startswith(candidate.path.rstrip("/")):
                            if not g.has_edge(candidate.operation_id, ep.operation_id):
                                for pname in params_in_path:
                                    for code, resp_schema in candidate.response_schemas.items():
                                        if code.startswith("2"):
                                            fields = _extract_response_field_names(resp_schema)
                                            match = next((f for f in fields if _field_name_similarity(pname, f) > 0.3), None)
                                            if match:
                                                g.add_edge(
                                                    candidate.operation_id,
                                                    ep.operation_id,
                                                    param_name=pname,
                                                    source_field=match,
                                                    score=0.7,
                                                    confirmed=False,
                                                    parameter_bindings={},
                                                )
                                                break
        return g
