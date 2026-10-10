import copy
import json
import tempfile
import unittest
import xml.etree.ElementTree as ET
from dataclasses import replace
from pathlib import Path

from claymanclub.camera import sample_camera
from claymanclub.backends.stickfigure import StickFigureBackend
from claymanclub.pipeline import render_episode
from claymanclub.validation import validate

ROOT = Path(__file__).resolve().parents[1]


class CameraTests(unittest.TestCase):
    def setUp(self):
        self.episode = json.loads((ROOT/'examples/episode-001.json').read_text())
        self.catalog = json.loads((ROOT/'examples/catalog.json').read_text())
        self.shot = self.episode['shots'][0]
        self.camera = self.shot['camera']

    def test_versions_and_legacy(self):
        legacy = json.loads((ROOT/'tests/fixtures/episode-001-v02.json').read_text())
        validate(legacy, self.catalog)
        with tempfile.TemporaryDirectory() as d:
            render_episode(legacy, self.catalog, StickFigureBackend(), Path(d)/'legacy')
        for version in ('0.1', '0.4', None, 0.3, '0.2'):
            with self.subTest(version=version), self.assertRaises(ValueError):
                self.episode['schema_version'] = version
                validate(self.episode, self.catalog)
        self.episode['schema_version'] = '0.3'
        del self.shot['camera']
        validate(self.episode, self.catalog)
        self.assertEqual(sample_camera(None, 12)['zoom'], 1)

    def test_invalid_camera_parameters(self):
        bad = [None, {}, dict(self.camera, space='world'),
               dict(self.camera, interpolation='spline'), dict(self.camera, keyframes=[]),
               dict(self.camera, engine='svg')]
        for field, values in {
            'frame': [-1, 1, True, 0.5, 181],
            'position': [None, [0, 0], [True, 0, 0], [float('nan'), 0, 0], [0, 0, 1], [10**400, 0, 0]],
            'rotation': [[1, 0, 0], [0, 1, 0], [0, 0, float('inf')]],
            'zoom': [0, -1, True, '2', float('inf'), float('nan'), 1e7, 1e-9],
        }.items():
            for value in values:
                camera = copy.deepcopy(self.camera)
                camera['keyframes'][0][field] = value
                bad.append(camera)
        for field in ('frame', 'position', 'rotation', 'zoom'):
            camera = copy.deepcopy(self.camera)
            del camera['keyframes'][0][field]
            bad.append(camera)
        camera = copy.deepcopy(self.camera)
        camera['keyframes'][0]['fov'] = 90
        bad.append(camera)
        for keys in ([0, 0], [0, 90, 80], [0, 181]):
            camera = copy.deepcopy(self.camera)
            camera['keyframes'] = [dict(camera['keyframes'][0], frame=f) for f in keys]
            bad.append(camera)
        for camera in bad:
            with self.subTest(camera=camera), self.assertRaises(ValueError):
                self.shot['camera'] = camera
                validate(self.episode, self.catalog)

    def test_boundaries_interpolation_and_unwrapped_rotation(self):
        validate(self.episode, self.catalog)  # terminal boundary 180 is legal
        for frame, index in ((-1, 0), (0, 0), (90, 1), (180, 2), (300, 2)):
            state = sample_camera(self.camera, frame)
            self.assertEqual(state, {k:v for k,v in self.camera['keyframes'][index].items() if k != 'frame'})
        state = sample_camera(self.camera, 45)
        self.assertEqual(state['position'], [-0.04, 0.025, 0])
        self.assertEqual(state['rotation'], [0, 0, 2.5])
        self.assertAlmostEqual(state['zoom'], 1.1)
        self.camera['keyframes'][1]['rotation'][2] = 360
        self.assertEqual(sample_camera(self.camera, 45)['rotation'][2], 180)
        self.camera['keyframes'] = self.camera['keyframes'][:1]
        validate(self.episode, self.catalog)
        self.assertEqual(sample_camera(self.camera, 179), sample_camera(self.camera, 0))

    def test_single_frame_shot_and_early_final_key(self):
        self.episode['shots'] = [self.shot]
        self.episode['duration_frames'] = self.shot['end_frame'] = 1
        self.camera['keyframes'] = [self.camera['keyframes'][0],
                                   dict(self.camera['keyframes'][1], frame=1)]
        validate(self.episode, self.catalog)
        self.assertEqual(sample_camera(self.camera, 0)['zoom'], 1)
        self.shot['end_frame'] = self.episode['duration_frames'] = 180
        self.assertEqual(sample_camera(self.camera, 179)['zoom'], 1.2)

    def test_capabilities_reject_before_writing(self):
        self.camera['space'] = 'framing_3d'
        self.camera['keyframes'][1]['position'][2] = 1
        self.camera['keyframes'][1]['rotation'] = [10, 20, 30]
        validate(self.episode, self.catalog)  # valid protocol, unsupported backend
        with tempfile.TemporaryDirectory() as d:
            output = Path(d)/'rejected'
            with self.assertRaisesRegex(ValueError, 'unsupported backend space'):
                render_episode(self.episode, self.catalog, StickFigureBackend(), output)
            with self.assertRaisesRegex(ValueError, 'unsupported backend space'):
                StickFigureBackend().render(self.episode, output)
            self.assertFalse(output.exists())
        self.camera['space'] = 'framing_2d'
        self.camera['keyframes'][1]['position'][2] = 0
        self.camera['keyframes'][1]['rotation'] = [0, 0, 0]
        for field in ('camera_spaces', 'camera_interpolations'):
            backend = StickFigureBackend()
            backend.capabilities = replace(backend.capabilities, **{field:frozenset()})
            with self.assertRaisesRegex(ValueError, 'unsupported backend'):
                backend.preflight(self.episode)

    def test_svg_transform_and_overlay_separation(self):
        backend = StickFigureBackend()
        initial = backend.frame(self.episode, self.shot, 0)
        moved = backend.frame(self.episode, self.shot, 90)
        self.assertNotEqual(initial, moved)
        self.assertEqual(moved, backend.frame(self.episode, self.shot, 90))
        root = ET.fromstring(moved)
        world = next(e for e in root if 'data-camera-world' in e.attrib)
        self.assertIn('scale(1.2) rotate(5)', world.attrib['transform'])
        self.assertIn('translate(-193.2 -432.0)', world.attrib['transform'])
        self.assertTrue(any('我的充电器' in (e.text or '') for e in root))
        self.assertFalse(any('我的充电器' in (e.text or '') for e in world.iter()))

    def test_html_script_payload_is_escaped(self):
        self.shot['performances'][0]['line'] = '</script><script>alert(1)</script>'
        with tempfile.TemporaryDirectory() as d:
            result = render_episode(self.episode, self.catalog, StickFigureBackend(), Path(d)/'out')
            html = result.entrypoint.read_text()
            self.assertEqual(html.count('</script>'), 1)
            self.assertNotIn('<script>alert', html)

class PlayerTests(unittest.TestCase):
    def test_generated_player_controls_and_python_parity(self):
        import shutil
        import subprocess
        if not shutil.which('node'):
            self.skipTest('optional player execution test requires Node; Python runtime does not')
        episode = json.loads((ROOT/'examples/episode-001.json').read_text())
        catalog = json.loads((ROOT/'examples/catalog.json').read_text())
        with tempfile.TemporaryDirectory() as d:
            result = render_episode(episode, catalog, StickFigureBackend(), Path(d)/'out')
            expected = []
            for index, shot in enumerate(episode['shots']):
                for frame in [-1, 0.5, *range(shot['end_frame']-shot['start_frame']+2)]:
                    expected.append({'shot':index, 'frame':frame,
                                     'state':sample_camera(shot.get('camera'), frame)})
            path = Path(d)/'samples.json'
            path.write_text(json.dumps(expected))
            subprocess.run(['node', str(ROOT/'tests/player_test.js'), str(result.entrypoint), str(path)], check=True)


if __name__ == '__main__':
    unittest.main()
