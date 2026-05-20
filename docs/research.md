# Research Background

## The Problem: Training Robust Tool-Use Agents at Scale

Recent advances in large language models (LLMs) have demonstrated remarkable capabilities in instruction following and reasoning. However, deploying these models as autonomous agents that reliably interact with external tools—APIs, databases, file systems, and software interfaces—remains a critical challenge. The core difficulties are:

1. **Specification Gap**: Real-world APIs are complex, stateful, and often poorly documented. Agents must learn not just *how* to call tools, but *when* they can be called, what preconditions must hold, and how to recover from failures.

2. **Trajectory Quality**: Existing agent training datasets (webshop interactions, tool-use benchmarks) are either hand-crafted at small scale or generated with insufficient fidelity to real API semantics. This leads to agents that memorize patterns but fail to generalize to novel tool configurations.

3. **Verification Bottleneck**: There is no systematic way to validate whether a synthetic trajectory (agent action sequence) is actually executable against a real or simulated API. Most work assumes ground-truth oracle feedback, which is infeasible for diverse, evolving tool ecosystems.

4. **Reproducibility and Calibration**: Training robust agents requires calibrated, reproducible environments. Current approaches either use brittle hand-coded simulators or expensive live API interaction, making iteration slow and sample-inefficient.

EnvFactory addresses this gap by providing infrastructure to *automatically synthesize and verify stateful executable environments from API specifications*, enabling large-scale trajectory generation with formal correctness guarantees.

## Related Work

### Agent Training and In-Context Learning

The foundational work on tool-use agents built on chain-of-thought prompting (Wei et al., 2022) and reinforcement learning from human feedback (Christiano et al., 2023). Subsequent work explored structured reasoning for tool selection and parameter binding:

- **ReAct** (Yao et al., 2023) introduced interleaving reasoning and action to improve tool-use trajectories, but still relied on online interaction.
- **ToolFormer** (Schick et al., 2023) fine-tuned language models to call tools, but required oracle-annotated training data.
- **Gorilla** (Patil et al., 2023) trained specialized models on curated API call sequences, but did not address state management or constraint verification.

These works assume access to ground-truth feedback about whether actions succeed or fail. EnvFactory automates and scales the generation of this feedback signal.

### Executable Environment Simulation

Prior work on simulating interactive environments for RL falls into several categories:

- **Hand-coded Simulators** (e.g., TextWorld, ALFWorld) provide rich but inflexible environments. Extending them to new APIs requires manual engineering.
- **OpenAPI/Swagger Interpretation** (Hao et al., 2023; Patil et al., 2023) parse API specifications to generate basic call graphs, but do not enforce stateful preconditions or handle API state evolution.
- **Schema-Guided Semantic Parsing** (Iyer et al., 2019) extracts structured representations of tool calls from text, but without runtime verification.

EnvFactory differs by treating API specifications as *executable contracts*: each endpoint is compiled into a verifiable constraint system with state tracking, enabling trajectory validation without manual oracle annotation.

### Trajectory Synthesis and Data Generation

Several recent efforts focus on generating synthetic training data for agents:

- **Generative Agent Simulation** (Park et al., 2023) creates believable agent behaviors in constrained spaces but does not address deterministic API contracts.
- **Self-Play RL** (Silver et al., 2017; Team et al., 2023) improves agent robustness but requires a well-defined reward function, which is difficult to specify for tool-use without executable verification.
- **Trajectory Stitching** (Nakano et al., 2022) combines fragments of trajectories, but assumes fragments are valid in isolation—fails for stateful APIs.

EnvFactory provides the missing piece: a systematic way to generate *valid*, *diverse*, *reproducible* trajectories by coupling specification-driven simulation with lightweight RL feedback.

### API Specification and Formal Verification

The formal methods and programming languages communities have extensive work on API contracts:

- **Design by Contract** (Meyer, 1988) established precondition and postcondition reasoning. JSON Schema (Wright & Andrews, 2020) operationalizes this for REST APIs.
- **Model-Based Testing** (Utting & Legeard, 2006) uses state machines to generate test sequences. SMT solvers (de Moura & Bjørner, 2008) can verify constraint satisfaction.

EnvFactory applies these techniques specifically to the agent training domain: it interprets OpenAPI specifications as state machines with constraints, generates trajectories that respect those constraints, and verifies executable correctness.

## How EnvFactory Advances the Field

### 1. Specification-Driven Synthesis

Rather than hand-coding simulators or relying on fragile oracle feedback, EnvFactory parses OpenAPI/YAML specifications into executable state machines. Each API endpoint becomes a verifiable transition with:
- **Input schema validation** (JSONSchema)
- **Precondition checking** (e.g., "resource must exist")
- **State mutation** (e.g., "mark resource as deleted")
- **Output generation** (realistic, reproducible fake data via Faker)

This allows training on new APIs with zero additional engineering.

### 2. Robust Trajectory Calibration

Trajectories are generated via a feedback loop:
1. **Sample** candidate action sequences from an agent policy or random walk
2. **Simulate** each sequence in the executable environment, tracking state
3. **Verify** whether the sequence is valid (all preconditions met, no constraint violations)
4. **Reweight** or filter trajectories based on validity, enabling RL objectives that optimize for both success *and* robustness

This replaces ad-hoc oracle annotation with systematic, reproducible verification.

### 3. Scalability Through Stateless Decoupling

Most API simulators maintain a single shared global state, limiting parallelism. EnvFactory uses **immutable environment snapshots**: each trajectory is evaluated in an isolated state context, enabling:
- Parallel environment rollouts
- Efficient batch trajectory generation
- Deterministic reproducibility (same seed → same trajectory)

### 4. Integration with Existing Tools

Rather than reinventing the agent training pipeline, EnvFactory is designed as a composable building block:
- **Specification Input**: OpenAPI 3.0 YAML/JSON
- **Environment Output**: Gym-compatible step interface (observation, reward, done, info)
- **Trajectory Format**: Standard JSON compatible with HuggingFace Datasets, LangChain, and custom RL frameworks

This allows seamless integration with existing agent training stacks.

## References

Christiano, P., Shlegeris, B., & Amodei, D. (2023). Reinforcement learning from human feedback. *arXiv preprint arXiv:1909.08383*.

de Moura, L., & Bjørner, N. (2008). Z3: An efficient SMT solver. In *International conference on tools and algorithms for the construction and analysis of systems* (pp. 337-340). Springer, Berlin, Heidelberg.

Hao, S., Tan, T., Bansal, G., Zhang, T., Rohrbach, M., & Sun, Y. (2023). ToolLLM: Facilitating large language models to master 16000+ real-world APIs. *arXiv preprint arXiv:2307.16789*.

Iyer, S., Konstas, I., Cheung, A., & Zettlemoyer, L. (2019). Learning a neural semantic parser from user feedback. *arXiv preprint arXiv:1906.04284*.

Meyer, B. (1988). Object-oriented software construction. *Prentice Hall*.

Nakano, R., Hilton, J., Balaji, S., Wu, J., Ouyang, L., Kim, C., ... & Henighan, T. (2022). Webgpt: Browser-assisted question-answering with human feedback. *arXiv preprint arXiv:2112.09332*.

Park, J. S., O'Brien, J., Cai, C. J., Morris, M. R., Liang, P., & Bernstein, M. S. (2023). Generative agents: Interactive simulacra of human behavior. *arXiv pre