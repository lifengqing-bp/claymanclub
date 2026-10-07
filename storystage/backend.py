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
