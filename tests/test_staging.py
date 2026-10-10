import copy
import json
import shutil
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET
from dataclasses import replace
from pathlib import Path
from claymanclub.staging import sample_offset
from claymanclub.backends.gestures import walk_swing, walk_leg_points, walk_leg_path
from claymanclub.backends.stickfigure import StickFigureBackend
from claymanclub.pipeline import render_episode
from claymanclub.validation import validate

ROOT = Path(__file__).resolve().parents[1]


class StagingTests(unittest.TestCase):
    def setUp(self):
        self.episode = json.loads((ROOT/'examples/stage-motion.json').read_text())
        self.catalog = json.loads((ROOT/'examples/catalog.json').read_text())

    def test_offsets_endpoints_hold_and_walk(self):
        shot = self.episode['shots'][0]
        track = shot['actor_tracks'][0]
        for frame, x in [(-1, 0), (20, 0), (70, .02), (120, .04), (180, .04)]:
            self.assertAlmostEqual(sample_offset(track, frame)[0], x)
        p = shot['performances'][0]
        for frame in [-1,20,120,121]:
            self.assertEqual(walk_swing(p, frame), 0)
        self.assertGreater(walk_swing(p, 32.5), 0)
        self.assertLess(walk_swing(p, 57.5), 0)

    def test_validation_and_preflight_before_output(self):
        def invalid(change):
            e = copy.deepcopy(self.episode)
            change(e)
            with self.assertRaises(ValueError):
                validate(e, self.catalog)
        for value in [True, float('nan'), float('inf'), 1000001, '0']:
            invalid(lambda e: e['shots'][0]['actor_tracks'][0]['keyframes'][0]['offset'].__setitem__(0,value))
        for version in ['0.2','0.3','0.4','0.5']:
            invalid(lambda e: e.__setitem__('schema_version',version))
        invalid(lambda e: e['shots'][0]['actor_tracks'].append(e['shots'][0]['actor_tracks'][0]))
        invalid(lambda e: e['shots'][0]['actor_tracks'][0].__setitem__('actor','unknown'))
        invalid(lambda e: e['shots'][0]['actor_tracks'][0].__setitem__('interpolation','cubic'))
        invalid(lambda e: e['shots'][0]['actor_tracks'][0].__setitem__('extra',True))
        for frame in [True,-1,1,181]:
            invalid(lambda e: e['shots'][0]['actor_tracks'][0]['keyframes'][0].__setitem__('frame',frame))
        invalid(lambda e: e['shots'][0]['actor_tracks'][0]['keyframes'][1].__setitem__('frame',0))
        invalid(lambda e: e['shots'][0]['actor_tracks'][0]['keyframes'][0]['offset'].__setitem__(2,1))
        invalid(lambda e: e['shots'][0]['performances'][0].__setitem__('end_frame',36))
        for space, capability in [('stage_2d',False),('stage_3d',True)]:
            e=copy.deepcopy(self.episode)
            e['shots'][0]['actor_tracks'][0]['space']=space
            validate(e,self.catalog)
            backend=StickFigureBackend()
            if not capability: backend.capabilities=replace(backend.capabilities,actor_spaces=frozenset())
            with tempfile.TemporaryDirectory() as d:
                out=Path(d)/'out'
                for call in [lambda:render_episode(e,self.catalog,backend,out),lambda:backend.render(e,out)]:
                    with self.assertRaisesRegex(ValueError,'unsupported backend actor space'):call()
                    self.assertFalse(out.exists())

    def test_gaze_crossing_close_and_shot_reset(self):
        e=self.episode
        shot=e['shots'][0]
        shot['actor_tracks'][0]['keyframes'][-1]['offset'][0]=.4
        backend=StickFigureBackend()
        def eye(frame):
            root=ET.fromstring(backend.frame(e,shot,frame))
            return next(x for x in root.iter() if x.get('data-eyes')=='bolt').get('d')
        self.assertEqual(eye(20),'M-9 340h1M21 340h1')
        self.assertEqual(eye(119),'M-21 340h1M9 340h1')
        shot['framing']={'size':'close','subjects':['bolt']}
        self.assertEqual(eye(119),'M-21 340h1M9 340h1')
        shot.pop('actor_tracks')
        root=ET.fromstring(backend.frame(e,shot,70))
        actor=next(x for x in root.iter() if x.get('data-actor')=='bolt')
        self.assertEqual(actor.get('transform'),'translate(270 0)')

    def test_node_sampling_matches_python(self):
        if not shutil.which('node'): self.skipTest('Node unavailable')
        shot=self.episode['shots'][0]
        with tempfile.TemporaryDirectory() as d:
            output=render_episode(self.episode,self.catalog,StickFigureBackend(),Path(d)/'out')
            expected=Path(d)/'samples.json'
            expected.write_text(json.dumps({'track':shot['actor_tracks'][0],'performance':shot['performances'][0],
                'samples':[{'frame':f/2,'offset':sample_offset(shot['actor_tracks'][0],f/2),
                            'swing':walk_swing(shot['performances'][0],f/2),
                            'legs':{side:walk_leg_points(shot['performances'][0],f/2,side) for side in ('left','right')}} for f in range(-2,365)]}))
            subprocess.run(['node',str(ROOT/'tests/staging_test.cjs'),str(output.entrypoint),str(expected)],check=True)

    def test_walk_lifts_alternate_and_reset(self):
        p=self.episode['shots'][0]['performances'][0]
        for frame in [-1,20,120,121]:
            self.assertEqual(walk_leg_points(p,frame,'left'),[-20,580,-40,635])
            self.assertEqual(walk_leg_points(p,frame,'right'),[20,580,40,635])
        for frame, lifted in [(32.5,'right'),(57.5,'left'),(82.5,'right'),(107.5,'left')]:
            for side in ('left','right'):
                kx,ky,fx,fy=walk_leg_points(p,frame,side)
                if side==lifted:
                    self.assertLess(fy,635)
                    self.assertLess(ky,580)
                    self.assertGreater(abs(kx),20)
                else:self.assertEqual(fy,635)
        self.assertEqual(walk_leg_path(None,58,'left'),'M0 525L-40 635')

    def test_story_renders_and_keeps_position_across_cuts(self):
        episode=json.loads((ROOT/'examples/one-more-take.json').read_text())
        validate(episode,self.catalog)
        self.assertEqual(episode['duration_frames']/episode['fps'],36)
        for before,after in zip(episode['shots'],episode['shots'][1:]):
            for track,following in zip(before['actor_tracks'],after['actor_tracks']):
                self.assertEqual(sample_offset(track,179),sample_offset(following,0))
        backend=StickFigureBackend()
        with tempfile.TemporaryDirectory() as d:
            result=render_episode(episode,self.catalog,backend,Path(d)/'out')
            self.assertTrue(result.entrypoint.exists())
