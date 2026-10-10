"""Minimal synchronous presentation port. No engine types cross this boundary."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Capabilities:
    actions: frozenset[str]
    emotions: frozenset[str]
    framing: frozenset[str]
    max_cast: int
    output_format: str
    camera_spaces: frozenset[str] = frozenset()
    camera_interpolations: frozenset[str] = frozenset()
    timed_performances: bool = False
    gaze_targets: bool = False
    animated_actions: frozenset[str] = frozenset()
    actor_spaces: frozenset[str] = frozenset()
    weather: frozenset[str] = frozenset()
    interactions: frozenset[tuple[str, str]] = frozenset()


@dataclass(frozen=True)
class RenderResult:
    entrypoint: Path
    manifest: Path


class PresentationBackend(ABC):
    name: str
    version: str
    capabilities: Capabilities

    @abstractmethod
    def preflight(self, episode: dict) -> None:
        """Raise ValueError before writing output if capabilities/bindings are missing."""

    @abstractmethod
    def render(self, episode: dict, output: Path) -> RenderResult:
        """Render a validated episode; output must not already exist."""
