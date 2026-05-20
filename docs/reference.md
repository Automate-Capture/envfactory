# EnvFactory API Reference

EnvFactory is a Python package for stateful API environment verification and calibrated trajectory synthesis. It enables systematic testing and validation of API workflows with dependency inference, state management, and trajectory sampling.

---

## `src/envfactory/dependency_inference.py`

Module for inferring dependencies between API endpoints.

### `infer(endpoints: list[EndpointDef]) -> nx.DiGraph`

Analyzes a list of endpoint definitions and infers their dependencies, returning a directed graph where edges represent data flow between endpoints.

**Parameters:**
- `endpoints` (list[EndpointDef]): List of endpoint definitions to analyze

**Returns:**
- `nx.DiGraph`: A directed graph where nodes are endpoint IDs and edges indicate dependencies

**Example:**
```python
from envfactory.dependency_inference import DependencyInference
from envfactory.schema_ingestion import SchemaIngestion

ingester = SchemaIngestion()
spec = ingester.load("api_schema.yaml")

inferrer = DependencyInference()
dependency_graph = inferrer.infer(spec.endpoints)

# Print dependency edges
for source, target in dependency_graph.edges():
    print(f"{source} -> {target}")
```

---

## `src/envfactory/environment_verifier.py`

Module for verifying API environments and managing confirmed/unconfirmed dependencies.

### `confirmed_edges() -> list[tuple[str, str]]`

Returns a list of confirmed dependency edges that have been validated.

**Returns:**
- `list[tuple[str, str]]`: List of tuples representing confirmed edges (source_endpoint, target_endpoint)

**Example:**
```python
from envfactory.environment_verifier import EnvironmentVerifier

verifier = EnvironmentVerifier()
confirmed = verifier.confirmed_edges()
print(f"Confirmed edges: {confirmed}")
```

---

### `unconfirmed_edges() -> list[tuple[str, str]]`

Returns a list of unconfirmed dependency edges pending validation.

**Returns:**
- `list[tuple[str, str]]`: List of tuples representing unconfirmed edges (source_endpoint, target_endpoint)

**Example:**
```python
verifier = EnvironmentVerifier()
unconfirmed = verifier.unconfirmed_edges()
print(f"Unconfirmed edges: {unconfirmed}")
```

---

### `verify(spec: NormalizedSpec) -> VerifiedDAG`

Verifies a normalized API specification and returns a validated directed acyclic graph of dependencies.

**Parameters:**
- `spec` (NormalizedSpec): A normalized API specification

**Returns:**
- `VerifiedDAG`: A verified DAG containing confirmed endpoint dependencies

**Example:**
```python
from envfactory.schema_ingestion import SchemaIngestion
from envfactory.environment_verifier import EnvironmentVerifier

ingester = SchemaIngestion()
spec = ingester.load("api_schema.yaml")

verifier = EnvironmentVerifier()
verified_dag = verifier.verify(spec)

print(f"Verified DAG: {verified_dag}")
```

---

## `src/envfactory/sandbox_server.py`

Module for managing a sandbox server environment with projects and tasks.

### `create_project()`

Creates a new project in the sandbox environment.

**Returns:**
- `str`: Project ID of the newly created project

**Example:**
```python
from envfactory.sandbox_server import SandboxServer

server = SandboxServer()
server.start()

project_id = server.create_project()
print(f"Created project: {project_id}")
```

---

### `create_task(project_id: str)`

Creates a new task within a specified project.

**Parameters:**
- `project_id` (str): ID of the project in which to create the task

**Returns:**
- `str`: Task ID of the newly created task

**Example:**
```python
server = SandboxServer()
server.start()

project_id = server.create_project()
task_id = server.create_task(project_id)
print(f"Created task: {task_id}")
```

---

### `list_tasks(project_id: str)`

Lists all tasks in a specified project.

**Parameters:**
- `project_id` (str): ID of the project

**Returns:**
- `list[str]`: List of task IDs in the project

**Example:**
```python
server = SandboxServer()
server.start()

project_id = server.create_project()
task_ids = server.list_tasks(project_id)
print(f"Tasks in project: {task_ids}")
```

---

### `get_task(task_id: str)`

Retrieves details of a specific task.

**Parameters:**
- `task_id` (str): ID of the task to retrieve

**Returns:**
- `dict`: Task details

**Example:**
```python
server = SandboxServer()
server.start()

project_id = server.create_project()
task_id = server.create_task(project_id)
task_details = server.get_task(task_id)
print(f"Task details: {task_details}")
```

---

### `delete_task(task_id: str)`

Deletes a specific task.

**Parameters:**
- `task_id` (str): ID of the task to delete

**Returns:**
- `None`

**Example:**
```python
server = SandboxServer()
server.start()

project_id = server.create_project()
task_id = server.create_task(project_id)
server.delete_task(task_id)
print(f"Task {task_id} deleted")
```

---

### `start(self) -> str`

Starts the sandbox server.

**Returns:**
- `str`: URL/address of the running server

**Example:**
```python
server = SandboxServer()
url = server.start()
print(f"Server started at: {url}")
```

---

### `stop(self) -> None`

Stops the sandbox server.

**Returns:**
- `None`

**Example:**
```python
server = SandboxServer()
server.start()
# ... do work ...
server.stop()
print("Server stopped")
```

---

## `src/envfactory/schema_ingestion.py`

Module for loading and normalizing API schemas.

### `load(path_or_url: str) -> NormalizedSpec`

Loads an API schema from a file path or URL and returns a normalized specification.

**Parameters:**
- `path_or_url` (str): File path (e.g., `"schema.yaml"`) or URL to the API schema

**Returns:**
- `NormalizedSpec`: A normalized API specification object

**Example:**
```python
from envfactory.schema_ingestion import SchemaIngestion

ingester = SchemaIngestion()

# Load from file
spec = ingester.load("openapi.yaml")
print(f"Loaded {len(spec.endpoints)} endpoints")

# Load from URL
spec = ingester.load("https://example.com/api/spec.json")
```

---

## `src/envfactory/session_state.py`

Module for managing session state across API calls and resolving parameters.

### `UnresolvableParameterError`

Exception raised when a parameter cannot be resolved during execution.

**Example:**
```python
from envfactory.session_state import UnresolvableParameterError, SessionState

state = SessionState()

try:
    params = state.resolve_params(endpoint, dag)
except UnresolvableParameterError as e:
    print(f"Failed to resolve parameters: {e}")
```

---

### `store(endpoint_id: str, field_name: str, value: Any) -> None`

Stores a value in the session state for an endpoint field.

**Parameters:**
- `endpoint_id` (str): ID of the endpoint
- `field_name` (str): Name of the field to store
- `value` (Any): Value to store

**Returns:**
- `None`

**Example:**
```python
from envfactory.session_state import SessionState

state = SessionState()
state.store("list_users", "user_id", 12345)
```

---

###