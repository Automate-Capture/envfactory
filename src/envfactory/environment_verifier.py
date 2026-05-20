"""Live verification of inferred endpoint dependency DAGs."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import networkx as nx
import requests
from faker import Faker

from envfactory.dependency_inference import DependencyInferrer
from envfactory.sandbox_server import SandboxServer
from envfactory.schema_ingestion import EndpointDef, NormalizedSpec
from envfactory.session_state import SessionState

logger = logging.getLogger(__name__)
_fake = Faker()


@dataclass
class VerifiedDAG:
    graph: nx.DiGraph
    session_state: SessionState
    failures: list[dict[str, Any]] = field(default_factory=list)

    @property
    def confirmed_edges(self) -> list[tuple[str, str]]:
        return [(u, v) for u, v, d in self.graph.edges(data=True) if d.get("confirmed")]

    @property
    def unconfirmed_edges(self) -> list[tuple[str, str]]:
        return [(u, v) for u, v, d in self.graph.edges(data=True) if not d.get("confirmed")]


def _generate_value_for_schema(schema: dict[str, Any]) -> Any:
    if not isinstance(schema, dict):
        return _fake.word()
    stype = schema.get("type", "string")
    if stype == "string":
        fmt = schema.get("format", "")
        if fmt == "email":
            return _fake.email()
        if fmt == "uri" or fmt == "url":
            return _fake.url()
        if fmt == "date":
            return _fake.date()
        return _fake.word()
    if stype == "integer":
        return _fake.random_int(min=1, max=1000)
    if stype == "number":
        return round(_fake.pyfloat(min_value=0, max_value=1000), 2)
    if stype == "boolean":
        return _fake.boolean()
    if stype == "array":
        item_schema = schema.get("items", {"type": "string"})
        return [_generate_value_for_schema(item_schema)]
    if stype == "object":
        obj = {}
        for prop_name, prop_schema in schema.get("properties", {}).items():
            obj[prop_name] = _generate_value_for_schema(prop_schema)
        return obj
    return _fake.word()


def _generate_request_body(schema: dict[str, Any] | None) -> dict[str, Any] | None:
    if not schema:
        return None
    return _generate_value_for_schema(schema)


def _store_response_fields(state: SessionState, endpoint_id: str, data: Any) -> None:
    if isinstance(data, dict):
        for k, v in data.items():
            state.store(endpoint_id, k, v)
    elif isinstance(data, list) and data and isinstance(data[0], dict):
        for k, v in data[0].items():
            state.store(endpoint_id, k, v)


def _substitute_path_params(path: str, params: dict[str, Any]) -> str:
    result = path
    for name, value in params.items():
        result = result.replace(f"{{{name}}}", str(value))
    return result


class EnvironmentVerifier:
    def __init__(self, sandbox: SandboxServer | None = None):
        self._sandbox = sandbox
        self._owns_sandbox = sandbox is None

    def verify(self, spec: NormalizedSpec) -> VerifiedDAG:
        inferrer = DependencyInferrer()
        candidate_dag = inferrer.infer(spec.endpoints)

        if self._owns_sandbox:
            self._sandbox = SandboxServer()
        base_url = self._sandbox.start()

        state = SessionState()
        failures: list[dict[str, Any]] = []
        ep_map = {ep.operation_id: ep for ep in spec.endpoints}

        try:
            topo_order = list(nx.topological_sort(candidate_dag))
        except nx.NetworkXUnfeasible:
            topo_order = list(candidate_dag.nodes)

        for node_id in topo_order:
            ep = ep_map.get(node_id)
            if not ep:
                continue
            self._execute_and_verify(base_url, ep, candidate_dag, state, failures, ep_map)

        isolated = [n for n in candidate_dag.nodes if candidate_dag.in_degree(n) == 0 and candidate_dag.out_degree(n) == 0]
        for node_id in isolated:
            ep = ep_map.get(node_id)
            if not ep or state.has(node_id, "_executed"):
                continue
            self._execute_endpoint(base_url, ep, {}, state)

        if self._owns_sandbox:
            self._sandbox.stop()

        return VerifiedDAG(graph=candidate_dag, session_state=state, failures=failures)

    def _execute_and_verify(
        self,
        base_url: str,
        ep: EndpointDef,
        dag: nx.DiGraph,
        state: SessionState,
        failures: list[dict],
        ep_map: dict[str, EndpointDef],
    ) -> None:
        path_params = {}
        for param in ep.path_params:
            for pred in dag.predecessors(ep.operation_id):
                edge = dag.edges[pred, ep.operation_id]
                if edge.get("param_name") == param.name:
                    source_field = edge.get("source_field", param.name)
                    val = state.get(pred, source_field)
                    if val is not None:
                        path_params[param.name] = val
                        break

        status, data = self._execute_endpoint(base_url, ep, path_params, state)

        if status is not None and 200 <= status < 300:
            for pred in dag.predecessors(ep.operation_id):
                edge_data = dag.edges[pred, ep.operation_id]
                pname = edge_data.get("param_name", "")
                if pname in path_params:
                    edge_data["confirmed"] = True
                    edge_data["parameter_bindings"] = {pname: edge_data.get("source_field", pname)}
        elif status is not None and status >= 400:
            for pred in dag.predecessors(ep.operation_id):
                edge_data = dag.edges[pred, ep.operation_id]
                pname = edge_data.get("param_name", "")
                failures.append({
                    "consumer": ep.operation_id,
                    "producer": pred,
                    "param": pname,
                    "status": status,
                })
                retry_val = self._try_alternate_source(pname, dag, state, ep.operation_id)
                if retry_val is not None:
                    path_params[pname] = retry_val
                    retry_status, retry_data = self._execute_endpoint(base_url, ep, path_params, state)
                    if retry_status and 200 <= retry_status < 300:
                        edge_data["confirmed"] = True
                        edge_data["parameter_bindings"] = {pname: edge_data.get("source_field", pname)}

    def _execute_endpoint(
        self,
        base_url: str,
        ep: EndpointDef,
        path_params: dict[str, Any],
        state: SessionState,
    ) -> tuple[int | None, Any]:
        path = _substitute_path_params(ep.path, path_params)
        url = f"{base_url}{path}"
        body = _generate_request_body(ep.request_body_schema)
        try:
            method_fn = getattr(requests, ep.method.lower())
            kwargs: dict[str, Any] = {"timeout": 10}
            if body is not None:
                kwargs["json"] = body
            resp = method_fn(url, **kwargs)
            data = None
            try:
                data = resp.json()
            except Exception:
                pass
            if data is not None:
                _store_response_fields(state, ep.operation_id, data)
            state.store(ep.operation_id, "_executed", True)
            state.store(ep.operation_id, "_status", resp.status_code)
            return resp.status_code, data
        except Exception as exc:
            logger.warning("Request to %s failed: %s", url, exc)
            return None, None

    def _try_alternate_source(
        self,
        param_name: str,
        dag: nx.DiGraph,
        state: SessionState,
        consumer_id: str,
    ) -> Any | None:
        for node in dag.nodes:
            if node == consumer_id:
                continue
            val = state.get(node, param_name)
            if val is not None:
                return val
        return None
