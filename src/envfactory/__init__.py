"""EnvFactory — stateful API environment verification and trajectory synthesis."""

__version__ = "0.1.0"

from envfactory.environment_verifier import EnvironmentVerifier, VerifiedDAG
from envfactory.trajectory_sampler import TrajectorySampler as TrajectorySynthesizer

EnvFactory = EnvironmentVerifier

__all__ = ["EnvFactory", "EnvironmentVerifier", "TrajectorySynthesizer"]
