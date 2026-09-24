<p align="center">
  <img src="assets/hero.png" alt="EnvFactory" width="900">
</p>

<h1 align="center">EnvFactory</h1>

<p align="center">
  <strong>Synthetic environments for training robust tool-use agents via trajectory synthesis.</strong>
</p>

<p align="center">
  <a href="https://github.com/Automate-Capture/envfactory/blob/master/LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue" alt="License: MIT"></a>
  <a href="https://github.com/Automate-Capture/envfactory"><img src="https://img.shields.io/badge/python->=3.10-brightgreen" alt="Python >= 3.10"></a>
  <a href="https://github.com/Automate-Capture/envfactory"><img src="https://img.shields.io/badge/tests-283-success" alt="Tests: 283"></a>
</p>

---

EnvFactory is a Python package for building and verifying stateful API environments used in agent training. It automatically infers endpoint dependencies, synthesizes realistic request trajectories, and validates execution paths—enabling reproducible training of agentic systems on complex tool-use tasks.

Whether you're building agents that orchestrate microservices, manage cloud APIs, or interact with multi-step business processes, EnvFactory handles the infrastructure for creating safe, observable, and calibrated training environments without modifying your existing API schemas.

---

## Quick Start

```bash
pip install envfactory
```

```python
from envfactory import EnvFactory, EnvironmentVerifier, TrajectorySynthesizer
from envfactory.schema_ingestion import SchemaLoader

# Load your OpenAPI specification
loader = SchemaLoader()
spec = loader.load("path/to/openapi.yaml")

# Infer dependencies between endpoints
verifier = EnvironmentVerifier()
dag = verifier.verify(spec)

# Synthesize training trajectories
sampler = TrajectorySynthesizer(dag)
trajectory = sampler.sample()
```

## What Can You Do?

### Dependency Inference
Automatically discover causal relationships between API endpoints by analyzing parameter types and response schemas.

```python
from envfactory.dependency_inference import DependencyInferrer

inferrer = DependencyInferrer()
dependency_graph = inferrer.infer(endpoints)
```

### Environment Verification
Validate that your API schema is executable and that all parameter dependencies can be resolved.

```python
verified_dag = verifier.verify(spec)
confirmed = verified_dag.confirmed_edges()
unconfirmed = verified_dag.unconfirmed_edges()
```

### Trajectory Synthesis
Generate realistic request sequences grounded in your schema's dependency structure and constrained by parameter resolution.

```python
sampler = TrajectorySynthesizer(verified_dag)
depth = sampler.depth()
trajectory = sampler.sample()
```

### Stateful Session Management
Track parameter values across API calls and resolve dependencies at execution time.

```python
from envfactory.session_state import SessionState

state = SessionState()
state.store("create_user", "user_id", "user_123")
user_id = state.get("create_user", "user_id")
resolved = state.resolve_params(endpoint, dag)
```

### Sandbox Environment
Run a Flask-based server for safe trajectory replay and agent interaction.

```python
from envfactory.sandbox_server import SandboxServer

server = SandboxServer()
base_url = server.start()
server.create_task(project_id="proj_1")
server.stop()
```

## Architecture

EnvFactory connects five core modules:

- **schema_ingestion**: Loads and normalizes OpenAPI specs into internal endpoint definitions
- **dependency_inference**: Builds a directed acyclic graph (DAG) of parameter dependencies
- **environment_verifier**: Validates the DAG and confirms executable paths
- **session_state**: Manages stateful parameter resolution during trajectory execution
- **trajectory_sampler**: Synthesizes realistic request sequences respecting dependencies
- **sandbox_server**: Provides a Flask API for trajectory replay and agent training

The pipeline flows: `OpenAPI YAML → Normalized Schema → Dependency Graph → Verified DAG → Trajectory Sample`.

## API Reference

### DependencyInferrer
```python
def infer(self, endpoints: list[EndpointDef]) -> nx.DiGraph
```
Analyzes endpoint signatures and returns a directed graph of parameter dependencies.

### EnvironmentVerifier
```python
def verify(self, spec: NormalizedSpec) -> VerifiedDAG
def confirmed_edges(self) -> list[tuple[str, str]]
def unconfirmed_edges(self) -> list[tuple[str, str]]
```
Validates schema executability and reports resolved vs. unresolved dependencies.

### SessionState
```python
def store(self, endpoint_id: str, field_name: str, value: Any) -> None
def get(self, endpoint_id: str, field_name: str) -> Any
def resolve_params(self, endpoint: EndpointDef, dag: nx.DiGraph) -> dict[str, Any]
```
Tracks parameter values and resolves dependencies for endpoint execution.

### TrajectorySampler
```python
def depth(self) -> int
def sample(self) -> list[EndpointCall]
```
Generates request trajectories constrained by the verified dependency DAG.

### SandboxServer
```python
def start(self) -> str
def stop(self) -> None
def create_task(project_id: str)
def list_tasks(project_id: str)
```
Flask-based sandbox for safe trajectory replay and agent interaction.

## Research Background

EnvFactory was developed to address the infrastructure gap in agentic AI training. Traditional approaches require manual environment construction or replay-based simulation. This package implements automated dependency inference and trajectory synthesis inspired by work on compositional task learning and stateful API interaction.

The core insight: by treating APIs as dependency graphs, we can synthesize realistic multi-step scenarios without hand-crafted test cases, enabling scalable training of tool-use agents.

## Testing

Run the test suite:

```bash
pytest tests/ -v
```

The package includes 283 tests covering dependency inference, environment verification, trajectory synthesis, and sandbox operations.

## Contributing

Contributions are welcome! Please open issues and pull requests on [GitHub](https://github.com/Automate-Capture/envfactory).

## Citation

```bibtex
@software{envfactory2024,
  title={EnvFactory: Synthetic Environments for Tool-Use Agent Training},
  author={Young, Andrew},
  organization={Automate Capture Research},
  year={2024},
  url={https://github.com/Automate-Capture/envfactory}
}
```

## License

MIT License. See [LICENSE](https://github.com/Automate-Capture/envfactory/blob/master/LICENSE) for details.