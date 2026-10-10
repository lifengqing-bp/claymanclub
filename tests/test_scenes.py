import copy
import json
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET
from claymanclub.backends.scenes import scene_svg
from claymanclub.backends.stickfigure import StickFigureBackend
from claymanclub.pipeline import render_episode
from claymanclub.validation import validate

ROOT = Path(__file__).resolve().parents[1]


class SceneTests(unittest.TestCase):
    def setUp(self):
        self.episode = json.loads((ROOT/'examples/wireframe-scene.json').read_text())
        self.catalog = json.loads((ROOT/'examples/catalog.json').read_text())

    def test_wireframe_props_share_world_and_keep_overlays_outside(self):
        backend = StickFigureBackend()
        for frame in [0,58,120,179]:
            root = ET.fromstring(backend.frame(self.episode,self.episode['shots'][0],frame))
            world = next(e for e in root if 'data-camera-world' in e.attrib)
            scene = next(e for e in world if 'data-scene' in e.attrib)
            self.assertEqual(scene.get('data-scene'),'wireframe_lounge')
            props = [e for e in scene.iter() if 'data-prop' in e.attrib]
            self.assertEqual({e.get('data-prop-kind') for e in props}, {'window','shelf','table','chair','plant'})
            self.assertEqual(len({e.get('data-prop') for e in props}),5)
            self.assertTrue(any('data-floor-grid' in e.attrib for e in scene.iter()))
            self.assertTrue(all(e.get('fill')=='none' for e in props))
            self.assertFalse(any('data-actor' in e.attrib for e in scene.iter()))
            for head in (e for e in world.iter() if 'data-head' in e.attrib):
                self.assertEqual(list(head)[0].get('fill'),'#1b2940', 'room lines cannot cross faces')
            self.assertLess(list(world).index(scene),next(i for i,e in enumerate(world) if 'data-actor' in e.attrib))
            self.assertTrue(any(e.tag.endswith('text') and 'claymanclub' in (e.text or '') for e in root))

    def test_repeatable_output_and_legacy_scene(self):
        original = copy.deepcopy(self.episode)
        backend = StickFigureBackend()
        with tempfile.TemporaryDirectory() as d:
            a = render_episode(self.episode,self.catalog,backend,Path(d)/'a')
            b = render_episode(self.episode,self.catalog,backend,Path(d)/'b')
            self.assertEqual(a.entrypoint.read_bytes(),b.entrypoint.read_bytes())
            self.assertEqual(json.loads(a.manifest.read_text())['scene'],'wireframe_lounge')
        self.assertEqual(original,self.episode)
        legacy = scene_svg('robot_lounge')
        self.assertIn('M35 660H505',legacy)
        self.assertNotIn('data-prop',legacy)

    def test_unknown_binding_rejected_before_output(self):
        self.episode['scene']='unbound_room'
        self.catalog['scenes']['unbound_room']={}
        validate(self.episode,self.catalog)
        backend = StickFigureBackend()
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'out'
            for call in [lambda:render_episode(self.episode,self.catalog,backend,out),lambda:backend.render(self.episode,out)]:
                with self.assertRaisesRegex(ValueError,'no scene binding'):call()
                self.assertFalse(out.exists())
