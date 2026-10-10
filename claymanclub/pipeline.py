from pathlib import Path
from .backend import PresentationBackend, RenderResult
from .validation import validate
from .camera import preflight_camera


def render_episode(episode: dict, catalog: dict, backend: PresentationBackend,
                   output: Path) -> RenderResult:
    validate(episode, catalog)
    preflight_camera(episode, backend.capabilities)
    backend.preflight(episode)
    if output.exists():
        raise ValueError(f'Output already exists: {output}')
    return backend.render(episode, output)
