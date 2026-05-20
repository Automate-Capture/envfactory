"""Tests for envfactory package."""

from pathlib import Path

import pytest

from envfactory.schema_ingestion import SchemaIngester, NormalizedSpec, EndpointDef
from envfactory.dependency_inference import DependencyInferrer
from envfactory.sandbox_server import SandboxServer
from envfactory.session_state import SessionState, UnresolvableParameterError
from envfactory.environment_verifier import EnvironmentVerifier, VerifiedDAG
from envfactory.trajectory_sampler import TrajectorySampler

FIXTURE_DIR = Path(__file__).parent / "fixtures"
SPEC_PATH = str(FIXTURE_DIR / "task_api.yaml")


class TestSchemaIngestion:
    def test_load_openapi3(self):
        ingester = SchemaIngester()
        spec = ingester.load(SPEC_PATH)
        assert isinstance(spec, NormalizedSpec)
        assert spec.title == "Task Management API"
        assert len(spec.endpoints) == 5

    def test_endpoints_have_correct_methods(self):
        spec = SchemaIngester().load(SPEC_PATH)
        methods = {ep.operation_id: ep.method for ep in spec.endpoints}
        assert methods["createProject"] == "POST"
        assert methods["createTask"] == "POST"
        assert methods["listTasks"] == "GET"
        assert methods["getTask"] == "GET"
        assert methods["deleteTask"] == "DELETE"

    def test_path_params_extracted(self):
        spec = SchemaIngester().load(SPEC_PATH)
        ep_map = {ep.operation_id: ep for ep in spec.endpoints}
        create_task = ep_map["createTask"]
        assert len(create_task.path_params) == 1
        assert create_task.path_params[0].name == "id"
        assert create_task.path_params[0].required is True

    def test_response_schemas_extracted(self):
        spec = SchemaIngester().load(SPEC_PATH)
        ep_map = {ep.operation_id: ep for ep in spec.endpoints}
        create_project = ep_map["createProject"]
        assert "201" in create_project.response_schemas
        schema = create_project.response_schemas["201"]
        assert "id" in schema.get("properties", {})

    def test_request_body_extracted(self):
        spec = SchemaIngester().load(SPEC_PATH)
        ep_map = {ep.operation_id: ep for ep in spec.endpoints}
        create_project = ep_map["createProject"]
        assert create_project.request_body_schema is not None
        assert "name" in create_project.request_body_schema.get("properties", {})


class TestDependencyInference:
    def test_infer_creates_graph(self):
        spec = SchemaIngester().load(SPEC_PATH)
        inferrer = DependencyInferrer()
        dag = inferrer.infer(spec.endpoints)
        assert dag.number_of_nodes() == 5

    def test_create_project_feeds_create_task(self):
        spec = SchemaIngester().load(SPEC_PATH)
        dag = DependencyInferrer().infer(spec.endpoints)
        assert dag.has_edge("createProject", "createTask") or dag.has_edge("createProject", "listTasks")

    def test_edges_have_metadata(self):
        spec = SchemaIngester().load(SPEC_PATH)
        dag = DependencyInferrer().infer(spec.endpoints)
        for u, v, data in dag.edges(data=True):
            assert "param_name" in data
            assert "source_field" in data
            assert "score" in data


class TestSandboxServer:
    def test_start_stop(self):
        server = SandboxServer()
        url = server.start()
        assert url.startswith("http://")
        server.stop()

    def test_create_project(self):
        import requests
        server = SandboxServer()
        url = server.start()
        try:
            resp = requests.post(f"{url}/projects", json={"name": "Test"}, timeout=5)
            assert resp.status_code == 201
            data = resp.json()
            assert "id" in data
            assert data["name"] == "Test"
        finally:
            server.stop()

    def test_full_crud_flow(self):
        import requests
        server = SandboxServer()
        url = server.start()
        try:
            proj = requests.post(f"{url}/projects", json={"name": "P1"}, timeout=5).json()
            pid = proj["id"]

            task = requests.post(
                f"{url}/projects/{pid}/tasks",
                json={"title": "T1"},
                timeout=5,
            ).json()
            tid = task["id"]
            assert task["project_id"] == pid

            tasks = requests.get(f"{url}/projects/{pid}/tasks", timeout=5).json()
            assert len(tasks) == 1

            fetched = requests.get(f"{url}/tasks/{tid}", timeout=5)
            assert fetched.status_code == 200

            deleted = requests.delete(f"{url}/tasks/{tid}", timeout=5)
            assert deleted.status_code == 200

            tasks_after = requests.get(f"{url}/projects/{pid}/tasks", timeout=5).json()
            assert len(tasks_after) == 0
        finally:
            server.stop()

    def test_404_on_missing(self):
        import requests
        server = SandboxServer()
        url = server.start()
        try:
            resp = requests.get(f"{url}/tasks/nonexistent", timeout=5)
            assert resp.status_code == 404
        finally:
            server.stop()


class TestSessionState:
    def test_store_and_get(self):
        state = SessionState()
        state.store("ep1", "id", "abc123")
        assert state.get("ep1", "id") == "abc123"
        assert state.has("ep1", "id")
        assert not state.has("ep1", "other")

    def test_resolve_params_with_confirmed_edge(self):
        import networkx as nx
        from envfactory.schema_ingestion import EndpointDef, ParamDef

        state = SessionState()
        state.store("createProject", "id", "proj-1")

        dag = nx.DiGraph()
        dag.add_edge("createProject", "createTask",
                      param_name="id", source_field="id",
                      confirmed=True, parameter_bindings={"id": "id"})

        ep = EndpointDef(
            method="POST",
            path="/projects/{id}/tasks",
            operation_id="createTask",
            path_params=[ParamDef(name="id", location="path", schema_type="string", required=True)],
        )
        resolved = state.resolve_params(ep, dag)
        assert resolved["id"] == "proj-1"

    def test_unresolvable_raises(self):
        import networkx as nx
        from envfactory.schema_ingestion import EndpointDef, ParamDef

        state = SessionState()
        dag = nx.DiGraph()
        dag.add_node("orphanEndpoint")

        ep = EndpointDef(
            method="GET",
            path="/items/{item_id}",
            operation_id="orphanEndpoint",
            path_params=[ParamDef(name="item_id", location="path", schema_type="string", required=True)],
        )
        with pytest.raises(UnresolvableParameterError):
            state.resolve_params(ep, dag)


class TestEnvironmentVerifier:
    def test_verify_produces_verified_dag(self):
        spec = SchemaIngester().load(SPEC_PATH)
        sandbox = SandboxServer()
        verifier = EnvironmentVerifier(sandbox=sandbox)
        try:
            result = verifier.verify(spec)
            assert isinstance(result, VerifiedDAG)
            assert result.graph.number_of_nodes() == 5
            assert len(result.confirmed_edges) > 0
        finally:
            sandbox.stop()

    def test_confirmed_edges_are_executable(self):
        spec = SchemaIngester().load(SPEC_PATH)
        sandbox = SandboxServer()
        verifier = EnvironmentVerifier(sandbox=sandbox)
        try:
            result = verifier.verify(spec)
            for u, v in result.confirmed_edges:
                edge = result.graph.edges[u, v]
                assert edge.get("parameter_bindings")
        finally:
            sandbox.stop()


class TestTrajectorySampler:
    def test_sample_trajectories(self):
        spec = SchemaIngester().load(SPEC_PATH)
        sandbox = SandboxServer()
        base_url = sandbox.start()
        try:
            verifier = EnvironmentVerifier(sandbox=sandbox)
            dag = verifier.verify(spec)
            sampler = TrajectorySampler(base_url=base_url)
            traces = sampler.sample(dag, min_depth=2, max_depth=3, n_trajectories=3)
            assert len(traces) == 3
            for trace in traces:
                assert trace.depth >= 1
                for step in trace.steps:
                    assert step.endpoint_id
                    assert step.method
        finally:
            sandbox.stop()


class TestTopLevelImports:
    def test_envfactory_exports(self):
        from envfactory import EnvFactory, EnvironmentVerifier, TrajectorySynthesizer
        assert EnvFactory is EnvironmentVerifier
        assert TrajectorySynthesizer is not None
