import argparse
import json
from pathlib import Path
from .validation import validate
from .pipeline import render_episode
from .backends.stickfigure import StickFigureBackend

# Explicit registry: adding a backend does not change the story or pipeline.
BACKENDS = {'stickfigure': StickFigureBackend}


def main(argv=None):
    parser = argparse.ArgumentParser(description='StoryStage story validation and presentation')
    parser.add_argument('command', choices=['validate', 'render'])
    parser.add_argument('episode', type=Path)
    parser.add_argument('--catalog', type=Path, default=Path(__file__).resolve().parents[1] / 'examples/catalog.json')
    parser.add_argument('--backend', choices=BACKENDS, default='stickfigure')
    parser.add_argument('--output', type=Path, default=Path('outputs/preview'))
    args = parser.parse_args(argv)
    try:
        episode = json.loads(args.episode.read_text(encoding='utf-8'))
        catalog = json.loads(args.catalog.read_text(encoding='utf-8'))
        if args.command == 'validate':
            validate(episode, catalog)
            print('VALID story plan (backend readiness not checked)')
        else:
            result = render_episode(episode, catalog, BACKENDS[args.backend](), args.output)
            print(result.entrypoint.resolve())
    except (ValueError, OSError, KeyError, TypeError) as exc:
        parser.exit(1, f'ERROR: {exc}\n')
