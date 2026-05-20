"""Weighted random walk trajectory sampling over verified DAGs."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any

import networkx as nx
import requests

from envfactory.environment_verifier import (
    VerifiedDAG,
    _generate_request_body,
    _store_response_fields,
    _substitute_path_params,
)
from envfactory.schema_ingestion import EndpointDef
from envfactory.session_state import SessionState


@dataclass
class ExecutionStep:
    endpoint_id: str
    method: str
    path: str
    resolved_url: str
    request_body: dict[str, Any] | None
    status_code: int | None
    response_data: Any
    resolved_params: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionTrace:
    steps: list[ExecutionStep] = field(default_factory=list)
    success: bool = True

    @property
    def depth(self) -> int:
        return len(self.steps)


class TrajectorySampler:
    def __init__(self, base_url: str):
        self._base_url = base_url

    def sample(
        self,
        dag: VerifiedDAG,
        min_depth: int = 2,
        max_depth: int = 5,
        n_trajectories: int = 5,
    ) -> list[ExecutionTrace]:
        ep_map: dict[str, EndpointDef] = {}
        for node_id, data in dag.graph.nodes(data=True):
            if "endpoint" in data:
                ep_map[node_id] = data["endpoint"]

        roots = [n for n in dag.graph.nodes if dag.graph.in_degree(n) == 0]
        if not roots:
            roots = list(dag.graph.nodes)

        traces: list[ExecutionTrace] = []
        for _ in range(n_trajectories):
            trace = self._random_walk(dag, ep_map, roots, min_depth, max_depth)
            traces.append(trace)
        return traces

    def _random_walk(
        self,
        dag: VerifiedDAG,
        ep_map: dict[str, EndpointDef],
        roots: list[str],
        min_depth: int,
        max_depth: int,
    ) -> ExecutionTrace:
        trace = ExecutionTrace()
        state = SessionState()
        target_depth = random.randint(min_depth, max_depth)

        current = random.choice(roots)
        visited: set[str] = set()

        for _ in range(target_depth):
            ep = ep_map.get(current)
            if not ep:
                break

            step = self._execute_step(ep, dag, state)
            trace.steps.append(step)
            visited.add(current)

            if step.status_code and step.status_code >= 400:
                trace.success = False

            successors = list(dag.graph.successors(current))
            confirmed_succs = [
                s for s in successors
                if dag.graph.edges[current, s].get("confirmed", False)
            ]

            candidates = confirmed_succs or successors
            candidates = [c for c in candidates if c not in visited] or candidates

            if not candidates:
                unvisited_roots = [r for r in roots if r not in visited]
                if unvisited_roots:
                    current = random.choice(unvisited_roots)
                else:
                    break
            else:
                weights = []
                for c in candidates:
                    edge = dag.graph.edges[current, c]
                    w = edge.get("score", 0.5)
                    if edge.get("confirmed"):
                        w *= 2.0
                    weights.append(w)
                total = sum(weights)
                if total == 0:
                    current = random.choice(candidates)
                else:
                    current = random.choices(candidates, weights=weights, k=1)[0]

        return trace

    def _execute_step(
        self,
        ep: EndpointDef,
        dag: VerifiedDAG,
        state: SessionState,
    ) -> ExecutionStep:
        path_params: dict[str, Any] = {}
        for param in ep.path_params:
            for pred in dag.graph.predecessors(ep.operation_id):
                edge = dag.graph.edges[pred, ep.operation_id]
                source_field = edge.get("source_field", param.name)
                val = state.get(pred, source_field)
                if val is not None:
                    path_params[param.name] = val
                    break

        path = _substitute_path_params(ep.path, path_params)
        url = f"{self._base_url}{path}"
        body = _generate_request_body(ep.request_body_schema)

        status_code = None
        response_data = None
        try:
            method_fn = getattr(requests, ep.method.lower())
            kwargs: dict[str, Any] = {"timeout": 10}
            if body is not None:
                kwargs["json"] = body
            resp = method_fn(url, **kwargs)
            status_code = resp.status_code
            try:
                response_data = resp.json()
            except Exception:
                pass
            if response_data is not None:
                _store_response_fields(state, ep.operation_id, response_data)
        except Exception:
            pass

        return ExecutionStep(
            endpoint_id=ep.operation_id,
            method=ep.method,
            path=ep.path,
            resolved_url=url,
            request_body=body,
            status_code=status_code,
            response_data=response_data,
            resolved_params=path_params,
        )
