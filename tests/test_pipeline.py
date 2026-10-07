import copy
import json
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from storystage.backend import PresentationBackend, Capabilities, RenderResult
from storystage.backends.stickfigure import StickFigureBackend
from storystage.pipeline import render_episode

ROOT = Path(__file__).resolve().parents[1]


class TextBackend(PresentationBackend):
    """Test double proving the pipeline is independent of SVG and Unreal."""
    name, version = 'text-test', '0'
    capabilities = Capabilities(frozenset(), frozenset(), frozenset(), 2, 'text')
    def preflight(self, episode):
        pass
    def render(self, episode, output):
        output.mkdir()
        p = output / 'story.txt'
        p.write_text('\n'.join(p['line'] for s in episode['shots'] for p in s['performances']))
        m = output / 'manifest.json'
        m.write_text('{}')
        return RenderResult(p, m)


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.episode = json.loads((ROOT/'examples/episode-001.json').read_text())
        self.catalog = json.loads((ROOT/'examples/catalog.json').read_text())
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.output = Path(self.temp.name)/'preview'

    def test_swappable_backend_and_valid_svg(self):
        original = copy.deepcopy(self.episode)
        result = render_episode(self.episode, self.catalog, StickFigureBackend(), self.output)
        self.assertTrue(result.entrypoint.exists())
        for p in self.output.glob('*.svg'):
            ET.parse(p)
        other = render_episode(self.episode, self.catalog, TextBackend(), self.output.parent/'text')
        self.assertIn('充电器', other.entrypoint.read_text())
        self.assertEqual(original, self.episode)

    def test_backend_rejects_catalog_valid_action_before_output(self):
        self.catalog['actions']['fly'] = {}
        self.episode['shots'][0]['performances'][0]['action'] = 'fly'
        with self.assertRaisesRegex(ValueError, 'unsupported action'):
            render_episode(self.episode, self.catalog, StickFigureBackend(), self.output)
        self.assertFalse(self.output.exists())

    def test_invalid_timeline(self):
        self.episode['shots'][1]['start_frame'] += 1
        with self.assertRaisesRegex(ValueError, 'contiguous'):
            render_episode(self.episode, self.catalog, StickFigureBackend(), self.output)
        self.assertFalse(self.output.exists())

    def test_repeatable_output_and_no_overwrite(self):
        render_episode(self.episode, self.catalog, StickFigureBackend(), self.output)
        other = self.output.parent/'other'
        render_episode(self.episode, self.catalog, StickFigureBackend(), other)
        for p in self.output.iterdir():
            self.assertEqual(p.read_bytes(), (other/p.name).read_bytes())
        with self.assertRaisesRegex(ValueError, 'already exists'):
            render_episode(self.episode, self.catalog, StickFigureBackend(), self.output)

    def test_escape_dialogue(self):
        self.episode['shots'][0]['performances'][0]['line'] = '<script>&'
        render_episode(self.episode, self.catalog, StickFigureBackend(), self.output)
        text = (self.output/'shot-001.svg').read_text()
        self.assertIn('&lt;script&gt;&amp;', text)
        ET.fromstring(text)


if __name__ == '__main__':
    unittest.main()
