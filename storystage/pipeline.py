from pathlib import Path
from .backend import PresentationBackend, RenderResult
from .validation import validate


def render_episode(episode: dict, catalog: dict, backend: PresentationBackend,
                   output: Path) -> RenderResult:
    validate(episode, catalog)
    backend.preflight(episode)
    if output.exists():
        raise ValueError(f'Output already exists: {output}')
    return backend.render(episode, output)
