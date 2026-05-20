# EnvFactory Quick Start Guide

EnvFactory is a Python package for building stateful API environment verifiers and generating calibrated trajectories for training agentic systems on tool-use tasks.

## Installation

```bash
pip install envfactory
```

Or install from source:

```bash
git clone <repository>
cd envfactory
pip install -e .
```

## Core Concepts

- **Schema Ingestion**: Load and normalize OpenAPI specifications
- **Dependency Inference**: Automatically detect parameter dependencies between endpoints
- **Environment Verification**: Validate API interactions and resolve stateful parameters
- **Trajectory Sampling**: Generate realistic sequences of API calls for training

## Quick Start Examples

### Example 1: Load and Verify an API Schema

```python
from envfactory.schema_ingestion import SchemaIngestion
from envfactory.environment_verifier import EnvironmentVerifier
from envfactory.dependency_inference import DependencyInference

# Load API specification
ingester = SchemaIngestion()
spec = ingester.load("https://api.example.com/openapi.json")

# Infer parameter dependencies
inferencer = DependencyInference()
dependency_graph = inferencer.infer(spec.endpoints)

# Verify the environment
verifier = EnvironmentVerifier()
verified_dag = verifier.verify(spec)

# Check verification results
print("Confirmed edges:", verifier.confirmed_edges())
print("Unconfirmed edges:", verifier.unconfirmed_edges())
```

### Example 2: Track Session State During API Calls

```python
from envfactory.session_state import SessionState, UnresolvableParameterError
from envfactory.schema_ingestion import SchemaIngestion
import networkx as nx

# Load specification and setup
ingester = SchemaIngestion()
spec = ingester.load("path/to/openapi.yaml")

# Initialize session state tracker
session = SessionState()

# Store values from API responses
session.store("create_user", "user_id", 12345)
session.store("create_user", "email", "user@example.com")

# Retrieve stored values
user_id = session.get("create_user", "user_id")
has_email = session.has("create_user", "email")

# Resolve endpoint parameters using stored state and dependency graph
endpoint = spec.endpoints[0]  # Your target endpoint
dag = nx.DiGraph()  # Your dependency graph

try:
    resolved_params = session.resolve_params(endpoint, dag)
    print("Resolved parameters:", resolved_params)
except UnresolvableParameterError as e:
    print(f"Cannot resolve parameters: {e}")

# View all stored values
all_state = session.all_values()
print("Full session state:", all_state)
```

### Example 3: Run Sandbox Server and Sample Trajectories

```python
from envfactory.sandbox_server import SandboxServer
from envfactory.trajectory_sampler import TrajectorySampler

# Initialize and start sandbox server
sandbox = SandboxServer()
base_url = sandbox.start()
print(f"Sandbox running at: {base_url}")

# Create a project and task
project_id = sandbox.create_project()
task_id = sandbox.create_task(project_id)

# List and retrieve tasks
tasks = sandbox.list_tasks(project_id)
task_info = sandbox.get_task(task_id)

# Sample trajectories for training
sampler = TrajectorySampler()
trajectory_depth = sampler.depth()

# Generate a sample trajectory
trajectory = sampler.sample(
    endpoint_graph=dag,
    session_state=session,
    max_depth=trajectory_depth
)

# Clean up
sandbox.delete_task(task_id)
sandbox.stop()
```

## Common Workflows

### Workflow: End-to-End Environment Setup

```python
from envfactory.schema_ingestion import SchemaIngestion
from envfactory.dependency_inference import DependencyInference
from envfactory.environment_verifier import EnvironmentVerifier
from envfactory.session_state import SessionState

# 1. Load API schema
ingester = SchemaIngestion()
spec = ingester.load("my_api_spec.json")

# 2. Infer dependencies
inferencer = DependencyInference()
graph = inferencer.infer(spec.endpoints)

# 3. Verify environment
verifier = EnvironmentVerifier()
verified = verifier.verify(spec)

# 4. Initialize session for stateful interactions
session = SessionState()

print("✓ Environment ready for trajectory generation")
```

## Error Handling

```python
from envfactory.session_state import UnresolvableParameterError

session = SessionState()

try:
    # Attempt to resolve parameters
    params = session.resolve_params(endpoint, dag)
except UnresolvableParameterError as e:
    # Handle missing dependencies
    print(f"Parameter resolution failed: {e}")
    # Manually populate required state
    session.store("endpoint_id", "required_field", value)
```

## Key Classes and Functions

| Module | Key Items |
|--------|-----------|
| `schema_ingestion` | `SchemaIngestion.load()` - Load OpenAPI specs |
| `dependency_inference` | `DependencyInference.infer()` - Build dependency graphs |
| `environment_verifier` | `EnvironmentVerifier.verify()`, `.confirmed_edges()`, `.unconfirmed_edges()` |
| `session_state` | `SessionState.store()`, `.get()`, `.resolve_params()`, `UnresolvableParameterError` |
| `sandbox_server` | `SandboxServer.start()`, `.stop()`, `.create_project()`, `.create_task()` |
| `trajectory_sampler` | `TrajectorySampler.sample()`, `.depth()` |

## Next Steps

- Review the test suite in `tests/` for additional usage patterns
- Consult module docstrings for detailed parameter descriptions
- Configure sandbox server endpoints for your API environment
- Tune trajectory sampling parameters for your training dataset