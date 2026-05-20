"""Typed key-value store for cross-endpoint parameter resolution."""

from __future__ import annotations

from typing import Any

import networkx as nx

from envfactory.schema_ingestion import EndpointDef


class UnresolvableParameterError(Exception):
    def __init__(self, endpoint_id: str, param_name: str):
        self.endpoint_id = endpoint_id
        self.param_name = param_name
        super().__init__(f"Cannot resolve parameter '{param_name}' for endpoint '{endpoint_id}'")


class SessionState:
    def __init__(self):
        self._store: dict[tuple[str, str], Any] = {}

    def store(self, endpoint_id: str, field_name: str, value: Any) -> None:
        self._store[(endpoint_id, field_name)] = value

    def get(self, endpoint_id: str, field_name: str) -> Any:
        return self._store.get((endpoint_id, field_name))

    def has(self, endpoint_id: str, field_name: str) -> bool:
        return (endpoint_id, field_name) in self._store

    def resolve_params(self, endpoint: EndpointDef, dag: nx.DiGraph) -> dict[str, Any]:
        resolved: dict[str, Any] = {}
        for param in endpoint.path_params:
            value = self._resolve_single(endpoint.operation_id, param.name, dag)
            if value is None:
                raise UnresolvableParameterError(endpoint.operation_id, param.name)
            resolved[param.name] = value
        for param in endpoint.query_params:
            try:
                value = self._resolve_single(endpoint.operation_id, param.name, dag)
                if value is not None:
                    resolved[param.name] = value
            except UnresolvableParameterError:
                if param.required:
                    raise
        return resolved

    def _resolve_single(self, consumer_id: str, param_name: str, dag: nx.DiGraph) -> Any | None:
        for pred in dag.predecessors(consumer_id):
            edge = dag.edges[pred, consumer_id]
            if edge.get("param_name") == param_name and edge.get("confirmed", False):
                source_field = edge.get("source_field", param_name)
                bindings = edge.get("parameter_bindings", {})
                actual_field = bindings.get(param_name, source_field)
                val = self.get(pred, actual_field)
                if val is not None:
                    return val
        for pred in dag.predecessors(consumer_id):
            edge = dag.edges[pred, consumer_id]
            source_field = edge.get("source_field", param_name)
            val = self.get(pred, source_field)
            if val is not None:
                return val
        return None

    def all_values(self) -> dict[tuple[str, str], Any]:
        return dict(self._store)
