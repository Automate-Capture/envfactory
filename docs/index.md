# EnvFactory

## Hero Section

<div align="center" markdown>

# EnvFactory

### Synthetic environments for training robust tool-use agents via trajectory synthesis

Build intelligent agents that master tool use through calibrated synthetic data generation and stateful API verification.

[Get Started](getting-started.md){ .md-button .md-button--primary }
[View on GitHub](https://github.com){ .md-button }

</div>

---

## Key Features

<div class="grid cards" markdown>

-   :material-puzzle-outline: **Stateful API Environments**

    Create realistic, interactive API environments with full state management. Verify agent interactions against specification constraints and catch errors before production deployment.

-   :material-chart-line: **Calibrated Trajectory Synthesis**

    Generate diverse, high-quality training trajectories with automatic calibration. Balance exploration coverage with task complexity to optimize agent learning efficiency.

-   :material-tools: **Tool-Use Agent Training**

    Purpose-built tooling for agentic systems that need to master complex multi-step tool interactions. Includes trajectory validation and performance metrics.

-   :material-network: **Network-Aware Simulation**

    Model real-world dependencies and service interactions. Built on NetworkX for flexible topology definition and graph-based environment composition.

</div>

---

## Quick Install

```bash
pip install envfactory
```

---

## What You Can Build

EnvFactory enables you to:

- **Generate synthetic API interactions** with calibrated difficulty and state complexity
- **Verify agent behavior** against formal specifications before deployment
- **Create diverse training datasets** for tool-use agents without manual annotation
- **Simulate realistic failure modes** to train robust error-handling strategies
- **Benchmark agent performance** across standardized environment scenarios

---

## Getting Started

Ready to train your first agent? Head to our [Getting Started guide](getting-started.md) to:

- Set up your environment
- Create your first synthetic API environment
- Generate training trajectories
- Train an agent on tool-use tasks

[Start Building →](getting-started.md){ .md-button .md-button--primary }

---

## Core Components

**envfactory.core**
: Environment specification and stateful API simulation

**envfactory.synthesis**
: Calibrated trajectory generation and synthesis algorithms

**envfactory.agents**
: Training loops and agent interaction protocols

**envfactory.validation**
: Specification verification and constraint checking

---

## Example Usage

```python
from envfactory import Environment, Agent, TrajectoryConfig

# Create a synthetic API environment
env = Environment.from_spec("payment_api.yaml")

# Configure trajectory synthesis
config = TrajectoryConfig(
    num_trajectories=1000,
    complexity_range=(0.3, 0.9),
    error_injection_rate=0.15
)

# Generate training data
trajectories = env.synthesize_trajectories(config)

# Train your agent
agent = Agent(model="gpt-4")
agent.train(trajectories)
```

---

## Community

Have questions? Ideas for improvements? Join our community:

- :material-github: [GitHub Issues](https://github.com/envfactory/envfactory/issues)
- :material-chat: [Discussions](https://github.com/envfactory/envfactory/discussions)
- :material-email: [Email us](mailto:team@envfactory.dev)