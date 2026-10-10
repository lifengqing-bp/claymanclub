import json
import math
import re
import shutil
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from claymanclub.backends.gestures import joint_angles
from claymanclub.backends.stickfigure import StickFigureBackend
from claymanclub.pipeline import render_episode

ROOT=Path(__file__).resolve().parents[1]


class JointTests(unittest.TestCase):
    def setUp(self):
        self.episode=json.loads((ROOT/'examples/stage-motion.json').read_text())
        self.catalog=json.loads((ROOT/'examples/catalog.json').read_text())

    def test_local_hinges_and_rigid_segments(self):
        backend=StickFigureBackend()
        for shot in self.episode['shots'][:2]:
            for frame in [0,20,32,58,70,108,120,121,179]:
                root=ET.fromstring(backend.frame(self.episode,shot,frame))
                actors=[e for e in root.iter() if 'data-actor' in e.attrib]
                for actor in actors:
                    hinges=[e for e in actor.iter() if 'data-bend' in e.attrib]
                    self.assertEqual({(e.get('data-bend'),e.get('data-side')) for e in hinges},
                                     {('elbow','left'),('elbow','right'),('knee','left'),('knee','right')})
                    for limb in (e for e in actor.iter() if 'data-limb' in e.attrib):
                        proximal=next(e for e in limb if 'data-proximal' in e.attrib)
                        hinge=next(e for e in limb if 'data-bend' in e.attrib)
                        distal=next(e for e in hinge if 'data-distal' in e.attrib)
                        a=list(map(float,re.findall(r'-?\d+(?:\.\d+)?(?:e[+-]?\d+)?',proximal.get('d'))))
                        b=list(map(float,re.findall(r'-?\d+(?:\.\d+)?(?:e[+-]?\d+)?',distal.get('d'))))
                        angle,x,y=map(float,re.findall(r'-?\d+(?:\.\d+)?(?:e[+-]?\d+)?',hinge.get('transform')))
                        self.assertEqual(a[2:],b[:2])
                        self.assertEqual(b[:2],[x,y], 'hinge rotates about the shared endpoint')
                        expected=math.hypot(27.5,25) if limb.get('data-limb')=='arm' else math.hypot(20,55)
                        self.assertAlmostEqual(math.dist(a[:2],a[2:]),expected)
                        self.assertAlmostEqual(math.dist(b[:2],b[2:]),expected)
                        self.assertLessEqual(abs(angle),105)

    def test_wave_uses_elbow_and_walk_uses_all_four(self):
        walk=self.episode['shots'][0]['performances'][0]
        wave=self.episode['shots'][1]['performances'][1]
        zero=dict(elbow_left=0,elbow_right=0,knee_left=0,knee_right=0)
        for p in [walk,wave]:
            for frame in [-1,20,120,121]:self.assertEqual(joint_angles(p,frame),zero)
        wave_pose=joint_angles(wave,70)
        self.assertAlmostEqual(wave_pose['elbow_right'],-85)
        self.assertEqual(wave_pose['elbow_left'],0)
        self.assertEqual(wave_pose['knee_left'],0)
        self.assertEqual(wave_pose['knee_right'],0)
        left=joint_angles(walk,58);right=joint_angles(walk,83)
        self.assertGreater(left['elbow_left'],0)
        self.assertLess(left['elbow_right'],0)
        self.assertGreater(left['knee_left'],0)
        self.assertEqual(left['knee_right'],0)
        self.assertEqual(right['knee_left'],0)
        self.assertLess(right['knee_right'],0)

    def test_javascript_joint_sampling_parity(self):
        if not shutil.which('node'):self.skipTest('Node unavailable')
        with tempfile.TemporaryDirectory() as d:
            result=render_episode(self.episode,self.catalog,StickFigureBackend(),Path(d)/'out')
            for p in [self.episode['shots'][0]['performances'][0],self.episode['shots'][1]['performances'][1]]:
                data=Path(d)/'samples.json'
                data.write_text(json.dumps({'performance':p,'joints':True,'samples':[
                    {'frame':f/2,'angles':joint_angles(p,f/2)} for f in range(-2,365)]}))
                subprocess.run(['node',str(ROOT/'tests/motion_test.cjs'),str(result.entrypoint),str(data)],check=True)
